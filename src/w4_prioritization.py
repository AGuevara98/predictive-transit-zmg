"""
W4 -- NPP Prioritization Layer
===============================
Repositions the NPP-V framework as a multi-criteria place-characteristics
prioritization index, decoupled from demand estimation.

Vitality dimension (v_ridership_annual_n) is excluded -- it is a
municipality-level proxy with no AGEB-level discrimination power.
Demand signal lives exclusively in W1/W3.

Score formula:
    npp_score    = sum(feature_i * ensemble_weight_i)    [CRITIC+EWM, 14 features]
    equity_score = mean(pe_marginacion_n, pe_rezago_n)
    final_score  = (1 - ALPHA) * npp_score + ALPHA * equity_score
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2.extras
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

PROJECT_ROOT = Path(__file__).parent.parent

ALPHA = 0.20  # equity bonus weight; sensitivity tested at 0.10, 0.20, 0.30

NPP_FEATURES = [
    "n_intersections_n", "n_street_density_n", "n_intersection_density_n",
    "p_poi_density_n", "p_employment_proxy_n", "p_retail_density_n",
    "p_service_density_n", "p_land_use_mix_n",
    "pe_population_n", "pe_pop_density_n", "pe_marginacion_n", "pe_rezago_n",
    "pe_dep_ratio_n", "pe_youth_share_n",
]
EQUITY_FEATURES = ["pe_marginacion_n", "pe_rezago_n"]
DIMENSIONS = {
    "n_intersections_n": "NODE",
    "n_street_density_n": "NODE",
    "n_intersection_density_n": "NODE",
    "p_poi_density_n": "PLACE",
    "p_employment_proxy_n": "PLACE",
    "p_retail_density_n": "PLACE",
    "p_service_density_n": "PLACE",
    "p_land_use_mix_n": "PLACE",
    "pe_population_n": "PEOPLE",
    "pe_pop_density_n": "PEOPLE",
    "pe_marginacion_n": "PEOPLE",
    "pe_rezago_n": "PEOPLE",
    "pe_dep_ratio_n": "PEOPLE",
    "pe_youth_share_n": "PEOPLE",
}


def compute_critic_weights(df: pd.DataFrame) -> dict:
    """CRITIC weights: contrast intensity x conflict across features."""
    std_dev = df.std()
    corr_matrix = df.corr()
    conflict = (1 - corr_matrix).sum()
    c_j = std_dev * conflict
    w = c_j / c_j.sum()
    return w.to_dict()


def compute_ewm_weights(df: pd.DataFrame) -> dict:
    """Entropy Weight Method weights: information dispersion across features."""
    n = len(df)
    shifted = df + 1e-6
    p_ij = shifted / shifted.sum()
    k = 1.0 / np.log(n)
    e_j = -k * (p_ij * np.log(p_ij)).sum()
    d_j = 1 - e_j
    w = d_j / d_j.sum()
    return w.to_dict()


def compute_ensemble_weights(critic_w: dict, ewm_w: dict) -> dict:
    """Average of CRITIC and EWM, re-normalized to sum to 1."""
    features = list(critic_w.keys())
    raw = {f: (critic_w[f] + ewm_w[f]) / 2.0 for f in features}
    total = sum(raw.values())
    return {f: v / total for f, v in raw.items()}


def compute_scores(df: pd.DataFrame, ensemble_w: dict, alpha: float = ALPHA) -> pd.DataFrame:
    """
    Compute npp_score, equity_score, final_score, priority_rank, priority_quintile.

    df must contain 'cve_ageb' plus all NPP_FEATURES columns.
    ensemble_w keys must cover all NPP_FEATURES.
    """
    npp_score = sum(df[f] * w for f, w in ensemble_w.items())
    equity_score = df[EQUITY_FEATURES].mean(axis=1)
    final_score = (1 - alpha) * npp_score + alpha * equity_score

    priority_rank = final_score.rank(ascending=False, method="min").astype(int)
    try:
        priority_quintile = pd.qcut(final_score, q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    except ValueError:
        priority_quintile = pd.cut(final_score, bins=5, labels=[1, 2, 3, 4, 5]).astype(int)

    return pd.DataFrame({
        "cve_ageb": df["cve_ageb"].values,
        "npp_score": npp_score.values,
        "equity_score": equity_score.values,
        "final_score": final_score.values,
        "priority_rank": priority_rank.values,
        "priority_quintile": priority_quintile.values,
    })


_ENGINE = None


def _get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(PG_URI)
    return _ENGINE


# ---------------------------------------------------------------------------
# DB I/O
# ---------------------------------------------------------------------------

def load_npp_features() -> pd.DataFrame:
    print("[Step 1] Loading 14 NPP features from features.nppv_features...")
    engine = _get_engine()
    cols = ", ".join(["cve_ageb"] + NPP_FEATURES)
    with engine.raw_connection() as conn:
        df = pd.read_sql(
            f"SELECT {cols} FROM features.nppv_features",
            conn,
        )
    for col in NPP_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    print(f"  [OK] {len(df):,} AGEBs loaded with {len(NPP_FEATURES)} features")
    return df


def write_weights_to_db(critic_w: dict, ewm_w: dict, ensemble_w: dict):
    print("[Step 5] Writing weights to features.nppv_w4_weights...")
    engine = _get_engine()
    records = [
        (f, DIMENSIONS[f], float(critic_w[f]), float(ewm_w[f]), float(ensemble_w[f]))
        for f in NPP_FEATURES
    ]
    with engine.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE features.nppv_w4_weights")
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO features.nppv_w4_weights "
                "(feature, dimension, critic_weight, ewm_weight, ensemble_weight) VALUES %s",
                records,
            )
        conn.commit()
    print(f"  [OK] {len(records)} feature weights written")


def write_scores_to_db(scores_df: pd.DataFrame):
    print("[Step 6] Writing scores to features.nppv_prioritization...")
    engine = _get_engine()
    cols = ["cve_ageb", "npp_score", "equity_score", "final_score",
            "priority_rank", "priority_quintile"]
    rows = list(scores_df[cols].itertuples(index=False, name=None))
    with engine.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM features.nppv_prioritization")
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO features.nppv_prioritization "
                "(cve_ageb, npp_score, equity_score, final_score, "
                "priority_rank, priority_quintile) VALUES %s",
                rows, page_size=500,
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("ANALYZE features.nppv_prioritization")
        conn.commit()
    print(f"  [OK] {len(rows):,} AGEB rows written")


def export_csvs(weights_df: pd.DataFrame, scores_df: pd.DataFrame, out_dir: Path):
    print("[Step 7] Exporting CSVs...")
    weights_df.to_csv(out_dir / "nppv_w4_weights.csv", index=False)
    scores_df.to_csv(out_dir / "nppv_prioritization.csv", index=False)
    print(f"  [OK] outputs/w4/nppv_w4_weights.csv")
    print(f"  [OK] outputs/w4/nppv_prioritization.csv")


# ---------------------------------------------------------------------------
# Main (Steps 1-7 only; GeoJSON/charts/report added in later tasks)
# ---------------------------------------------------------------------------

def main():
    print("\n" + "="*70)
    print(" W4: NPP PRIORITIZATION LAYER")
    print("="*70)

    out_dir = PROJECT_ROOT / "outputs" / "w4"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load
    features_df = load_npp_features()

    # Compute weights
    print("[Step 2] Computing CRITIC weights...")
    critic_w = compute_critic_weights(features_df[NPP_FEATURES])
    print(f"  [OK] CRITIC computed for {len(critic_w)} features")

    print("[Step 3] Computing EWM weights...")
    ewm_w = compute_ewm_weights(features_df[NPP_FEATURES])
    print(f"  [OK] EWM computed for {len(ewm_w)} features")

    print("[Step 4] Computing NPP + equity scores...")
    ensemble_w = compute_ensemble_weights(critic_w, ewm_w)
    scores_df = compute_scores(features_df, ensemble_w, alpha=ALPHA)
    print(f"  [OK] Scores computed for {len(scores_df):,} AGEBs")
    print(f"    npp_score   : mean={scores_df['npp_score'].mean():.4f}")
    print(f"    equity_score: mean={scores_df['equity_score'].mean():.4f}")
    print(f"    final_score : mean={scores_df['final_score'].mean():.4f}")

    # Build weights DataFrame for CSV/DB
    weights_df = pd.DataFrame([
        {
            "feature": f,
            "dimension": DIMENSIONS[f],
            "critic_weight": critic_w[f],
            "ewm_weight": ewm_w[f],
            "ensemble_weight": ensemble_w[f],
        }
        for f in NPP_FEATURES
    ]).sort_values("ensemble_weight", ascending=False)

    # DB writes
    write_weights_to_db(critic_w, ewm_w, ensemble_w)
    write_scores_to_db(scores_df)

    # CSVs
    export_csvs(weights_df, scores_df, out_dir)

    print("\n" + "="*70)
    print(" W4 STEPS 1-7 COMPLETE -- DB + CSVs written")
    print("="*70)


if __name__ == "__main__":
    main()
