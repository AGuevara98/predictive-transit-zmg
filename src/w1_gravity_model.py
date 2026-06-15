"""
W1.2 -- Doubly-Constrained Gravity Model
=========================================
Distributes trips between AGEBs via a doubly-constrained gravity model
(power-law decay, Furness IPF balancing) using Euclidean centroid distances.

Input:  features.ageb_trip_ends  (productions, attractions)
        base.ageb centroids (EPSG:6372 metres)
Output: features.ageb_od_matrix  (origin, dest, dist_m, modeled_flow)

Distance note: Euclidean proxy is used for this Tier-1 implementation.
W2 may refine with osmnx network travel times after EOD 2022 calibration.
"""
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from sqlalchemy import create_engine
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI, CRS_CANONICAL

ENGINE = create_engine(PG_URI)

BETA           = 2.0
FLOW_THRESHOLD = 0.5
MAX_ITER       = 300
TOL            = 1e-5


def furness_ipf(
    prods: np.ndarray,
    attrs: np.ndarray,
    dist_m: np.ndarray,
    beta: float = BETA,
    max_iter: int = MAX_ITER,
    tol: float = TOL,
) -> np.ndarray:
    """
    Doubly-constrained gravity model via Furness Iterative Proportional Fitting.

    Parameters
    ----------
    prods   : (n,) trip productions per zone
    attrs   : (n,) trip attractions per zone; sum must equal sum(prods)
    dist_m  : (n, n) distance matrix in metres; diagonal = 0 (same zone -> zero flow)
    beta    : power-law decay exponent
    Returns
    -------
    T : (n, n) OD flow matrix; diagonal = 0
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        F = np.where(dist_m == 0, 0.0, dist_m ** (-beta))

    A = np.ones(len(prods))
    B = np.ones(len(attrs))
    row_err = float("inf")

    for iteration in range(max_iter):
        denom_A = F @ (B * attrs)
        A = np.where(denom_A > 0, 1.0 / denom_A, 0.0)

        denom_B = F.T @ (A * prods)
        B = np.where(denom_B > 0, 1.0 / denom_B, 0.0)

        T = (A * prods)[:, None] * F * (B * attrs)[None, :]
        row_err = np.max(np.abs(T.sum(axis=1) - prods) / np.clip(prods, 1, None))
        if row_err < tol:
            print(f"  [OK] Furness converged at iteration {iteration+1}, row error={row_err:.2e}")
            break
    else:
        print(f"  [WARN] Furness did not converge in {max_iter} iterations; row error={row_err:.2e}")

    return T


def load_trip_ends() -> pd.DataFrame:
    print("[Step 1] Loading trip ends...")
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(
            "SELECT cve_ageb, productions, attractions FROM features.ageb_trip_ends ORDER BY cve_ageb",
            conn
        )
    print(f"  [OK] {len(df):,} AGEBs")
    return df


def load_centroids() -> pd.DataFrame:
    print("[Step 2] Loading AGEB centroids...")
    with ENGINE.raw_connection() as conn:
        gdf = gpd.read_postgis(
            "SELECT cvegeo AS cve_ageb, ST_Centroid(geom) AS geom FROM base.ageb ORDER BY cvegeo",
            conn, geom_col="geom", crs=CRS_CANONICAL
        )
    gdf["x"] = gdf.geometry.x
    gdf["y"] = gdf.geometry.y
    print(f"  [OK] {len(gdf):,} centroids loaded")
    return gdf[["cve_ageb", "x", "y"]]


def build_distance_matrix(centroids: pd.DataFrame) -> np.ndarray:
    print("[Step 3] Building distance matrix...")
    from scipy.spatial.distance import cdist
    coords = centroids[["x", "y"]].values
    D = cdist(coords, coords, metric="euclidean")
    np.fill_diagonal(D, 0.0)
    mean_dist = D[D > 0].mean()
    print(f"  [OK] Distance matrix {D.shape}, mean non-zero dist = {mean_dist:.0f} m")
    return D


def write_od_matrix(cve_list: list, T: np.ndarray, D: np.ndarray):
    print("[Step 5] Writing OD matrix to database...")
    n = len(cve_list)
    rows = [
        (cve_list[i], cve_list[j], float(D[i, j]), float(T[i, j]))
        for i in range(n) for j in range(n)
        if i != j and T[i, j] >= FLOW_THRESHOLD
    ]
    print(f"  [OK] {len(rows):,} pairs with flow >= {FLOW_THRESHOLD}")

    with ENGINE.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM features.ageb_od_matrix")
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO features.ageb_od_matrix
                       (origin_cve_ageb, dest_cve_ageb, dist_m, modeled_flow)
                   VALUES %s""",
                rows,
                page_size=5000
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("ANALYZE features.ageb_od_matrix")
        conn.commit()
    print(f"  [OK] OD matrix written")


def main():
    print("\n" + "="*70)
    print("W1.2 -- DOUBLY-CONSTRAINED GRAVITY MODEL")
    print("="*70)

    trip_ends = load_trip_ends()
    centroids = load_centroids()
    merged    = trip_ends.merge(centroids, on="cve_ageb", how="inner")
    print(f"  [OK] {len(merged):,} AGEBs in both trip_ends and centroids")
    if len(merged) < len(centroids):
        missing = len(centroids) - len(merged)
        print(f"  [WARN] {missing} AGEBs in base.ageb have no trip_ends -- run w1_trip_generation.py first.")
        if len(merged) < 0.95 * len(centroids):
            raise RuntimeError(f"Too many missing AGEBs ({missing}); aborting to prevent partial OD matrix.")

    D     = build_distance_matrix(merged)
    prods = merged["productions"].values.astype(float)
    attrs = merged["attractions"].values.astype(float)

    print(f"[Step 4] Running Furness IPF (beta={BETA}, max_iter={MAX_ITER})...")
    T = furness_ipf(prods, attrs, D, beta=BETA, max_iter=MAX_ITER, tol=TOL)

    write_od_matrix(merged["cve_ageb"].tolist(), T, D)

    out_path = Path(__file__).parent.parent / "outputs" / "w1"
    out_path.mkdir(parents=True, exist_ok=True)
    stored   = int((T >= FLOW_THRESHOLD).sum())
    pd.DataFrame([{
        "total_flow"         : float(T.sum()),
        "mean_flow_filtered" : float(T[T >= FLOW_THRESHOLD].mean()) if stored else 0,
        "mean_dist_m_filtered": float(D[T >= FLOW_THRESHOLD].mean()) if stored else 0,
        "n_pairs_stored"     : stored,
        "beta"               : BETA,
        "flow_threshold"     : FLOW_THRESHOLD,
    }]).to_csv(out_path / "od_matrix_summary.csv", index=False)
    print(f"  [OK] Summary -> outputs/w1/od_matrix_summary.csv")

    print("\n" + "="*70)
    print("W1.2 GRAVITY MODEL COMPLETE")
    print("="*70)
    print(f"  Total flow       : {T.sum():,.0f}")
    print(f"  OD pairs stored  : {stored:,} of {len(merged)**2:,}")


if __name__ == "__main__":
    main()
