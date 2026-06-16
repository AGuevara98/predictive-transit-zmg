"""
W9.5 -- Tier-1 Pipeline Orchestrator for Monterrey
====================================================
Runs the W1-equivalent demand estimation pipeline for ZM Monterrey using
Tier-1 data only (INEGI CPV2020 census, DENUE, OSM).

Steps:
  1. Check for Monterrey census data; print download instructions if absent
  2. Load and validate AGEB-level census data
  3. Compute trip productions and attractions
  4. Run doubly-constrained gravity model
  5. Apply vehicle-ownership transit-propensity weighting
  6. Write outputs to outputs/w9/
  7. Print transfer comparison: ZMG vs Monterrey mean transit demand

Usage:
    python src/w9_run_tier1.py

If census data is not available locally, the script exits with code 0 (not
an error) after printing clear download instructions.
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import EMPLOYMENT_PROXY_MAP, SCIAN_SECTORS
from src.w9_city_config import (
    CITY_NAME, CVE_ENT, ZM_MUNICIPALITIES,
    BBOX_LON_MIN, BBOX_LON_MAX, BBOX_LAT_MIN, BBOX_LAT_MAX,
    TRIPS_PER_PERSON_DAY, YOUTH_MULTIPLIER,
    EMPLOY_WEIGHT, POI_WEIGHT, RETAIL_WEIGHT,
    GRAVITY_BETA, GRAVITY_MAX_ITER, GRAVITY_TOL, GRAVITY_FLOW_THRESHOLD,
    CENSUS_ZIP_URL, CENSUS_DIR_NAME, CENSUS_CSV_NAME,
    POP_COL, YOUTH_COL_LOW, YOUTH_COL_HIGH, YOUTH_COL_COMBINED,
    VEHICLES_COL, OCCUPIED_HOUSING_COL,
    COL_ENTIDAD, COL_MUN, COL_LOC, COL_AGEB, COL_MZA,
)


# =============================================================================
# Paths
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "outputs" / "w9"
DATA_DIR     = PROJECT_ROOT / "data"

# Expected census data locations (two common layouts)
CENSUS_PATHS = [
    DATA_DIR / CENSUS_DIR_NAME / "conjunto_de_datos" / CENSUS_CSV_NAME,
    DATA_DIR / CENSUS_CSV_NAME,  # flat layout fallback
]

# DENUE data location (glob fallback handles other date suffixes)
DENUE_PATHS = [
    DATA_DIR / "denue_19_0420_csv" / "conjunto_de_datos" / "denue_inegi_19_.csv",
]

# INEGI Marco Geoestadistico AGEB shapefile for Nuevo Leon
AGEB_SHP_PATHS = [
    DATA_DIR / "2020_1_19_A" / "2020_1_19_A.shp",
]


# =============================================================================
# Step 1: Census data check
# =============================================================================
def find_census_file():
    """Return the first existing census CSV path, or None if not found."""
    for p in CENSUS_PATHS:
        if p.exists():
            return p
    return None


def find_denue_file():
    """Return the DENUE CSV path, or None if not found."""
    for p in DENUE_PATHS:
        if p.exists():
            return p
    matches = sorted(DATA_DIR.glob("denue_19_*/conjunto_de_datos/denue_inegi_19_.csv"))
    return matches[0] if matches else None


def find_ageb_shp():
    """Return the INEGI AGEB shapefile path, or None if not found."""
    for p in AGEB_SHP_PATHS:
        if p.exists():
            return p
    matches = sorted(DATA_DIR.glob("2020_1_19_*/*.shp"))
    return matches[0] if matches else None


def print_census_download_instructions() -> None:
    print("\n" + "=" * 70)
    print("  CENSUS DATA NOT FOUND -- DOWNLOAD REQUIRED")
    print("=" * 70)
    print(f"\n  The Monterrey (Nuevo Leon) CPV2020 census file was not found.")
    print(f"  Expected locations:")
    for p in CENSUS_PATHS:
        print(f"    {p}")
    print(f"\n  Download steps:")
    print(f"  1. Download the ZIP archive from INEGI:")
    print(f"     {CENSUS_ZIP_URL}")
    print(f"  2. Extract to: {DATA_DIR / CENSUS_DIR_NAME}/")
    print(f"     The CSV should be at:")
    print(f"     {CENSUS_PATHS[0]}")
    print(f"  3. Re-run this script.")
    print(f"\n  Note: The file is approximately 50-100 MB compressed.")
    print(f"        The column schema is identical to the ZMG (Jalisco) census.")
    print()


# =============================================================================
# Step 2: Load census data
# =============================================================================
def load_census(census_path: Path) -> pd.DataFrame:
    print(f"[Step 2] Loading census: {census_path.name}...")
    census = pd.read_csv(census_path, dtype=str, encoding="utf-8-sig")

    # Keep only AGEB-level rows (MZA == "000")
    census = census[census[COL_MZA] == "000"].copy()

    # Build 15-character cvegeo
    census["cve_ageb"] = (
        census[COL_ENTIDAD].str.zfill(2)
        + census[COL_MUN].str.zfill(3)
        + census[COL_LOC].str.zfill(4)
        + census[COL_AGEB].str.zfill(4)
    )

    # Filter to ZM municipalities
    census = census[census[COL_MUN].isin(ZM_MUNICIPALITIES)].copy()
    print(f"  [OK] {len(census):,} AGEB rows in {len(ZM_MUNICIPALITIES)} municipalities")

    # Parse numeric columns
    numeric_cols = [POP_COL, VEHICLES_COL, OCCUPIED_HOUSING_COL]
    for col in numeric_cols:
        if col in census.columns:
            census[col] = pd.to_numeric(census[col], errors="coerce").fillna(0)
        else:
            print(f"  [WARN] Column '{col}' not found; defaulting to 0")
            census[col] = 0.0

    # Youth population: try combined column, fall back to sum of age bands
    if YOUTH_COL_COMBINED in census.columns:
        census["youth_pop"] = pd.to_numeric(
            census[YOUTH_COL_COMBINED], errors="coerce"
        ).fillna(0)
    else:
        for c in [YOUTH_COL_LOW, YOUTH_COL_HIGH]:
            if c not in census.columns:
                census[c] = 0
            census[c] = pd.to_numeric(census[c], errors="coerce").fillna(0)
        census["youth_pop"] = census[YOUTH_COL_LOW] + census[YOUTH_COL_HIGH]

    census["pe_youth_share"] = census["youth_pop"] / census[POP_COL].clip(lower=1)
    census["pe_population"]  = census[POP_COL]
    census["vehicle_rate"]   = (
        census[VEHICLES_COL] / census[OCCUPIED_HOUSING_COL].clip(lower=1)
    ).clip(0, 1)

    print(f"  [OK] Mean population  : {census['pe_population'].mean():,.0f}")
    print(f"  [OK] Mean vehicle_rate: {census['vehicle_rate'].mean():.3f}")
    return census[["cve_ageb", "pe_population", "pe_youth_share", "vehicle_rate"]]


def load_denue_features(denue_path: Path) -> pd.DataFrame:
    """Load DENUE establishments and aggregate place features per AGEB.

    Uses the AGEB code columns already present in the DENUE file (no spatial join needed).
    Returns a DataFrame with columns: cve_ageb, employment_proxy, poi_count, retail_count.
    """
    print(f"[Step 2b] Loading DENUE: {denue_path.name}...")
    usecols = ["cve_ent", "cve_mun", "cve_loc", "ageb", "codigo_act", "per_ocu"]
    denue = pd.read_csv(denue_path, dtype=str, encoding="latin-1", usecols=usecols)

    denue = denue[denue["cve_ent"].str.strip() == CVE_ENT].copy()
    denue["cve_mun_z"] = denue["cve_mun"].str.strip().str.zfill(3)
    denue = denue[denue["cve_mun_z"].isin(ZM_MUNICIPALITIES)].copy()

    denue["cve_ageb"] = (
        denue["cve_ent"].str.strip().str.zfill(2)
        + denue["cve_mun_z"]
        + denue["cve_loc"].str.strip().str.zfill(4)
        + denue["ageb"].str.strip().str.zfill(4)
    )

    denue["emp_proxy"] = denue["per_ocu"].str.strip().map(EMPLOYMENT_PROXY_MAP).fillna(0)

    retail_prefixes = tuple(SCIAN_SECTORS.get("retail", ["46"]))
    denue["is_retail"] = denue["codigo_act"].str.strip().str.startswith(retail_prefixes)

    agg = denue.groupby("cve_ageb").agg(
        employment_proxy=("emp_proxy", "sum"),
        poi_count=("cve_ageb", "count"),
        retail_count=("is_retail", "sum"),
    ).reset_index()

    print(f"  [OK] {len(denue):,} establishments -> {len(agg):,} AGEBs")
    print(f"  [OK] Mean employment_proxy: {agg['employment_proxy'].mean():.1f}")
    print(f"  [OK] Mean poi_count       : {agg['poi_count'].mean():.1f}")
    return agg


# =============================================================================
# Step 3: Trip productions and attractions
# =============================================================================
def compute_trip_ends(census_df: pd.DataFrame,
                       place_df: pd.DataFrame = None) -> pd.DataFrame:
    print("[Step 3] Computing trip productions and attractions...")

    # Productions: same formula as ZMG W1.1
    rate = TRIPS_PER_PERSON_DAY * (1 + YOUTH_MULTIPLIER * census_df["pe_youth_share"])
    census_df = census_df.copy()
    census_df["productions"] = (census_df["pe_population"] * rate).clip(lower=0)

    if place_df is not None:
        merged = census_df.merge(place_df, on="cve_ageb", how="left")
        for col in ["employment_proxy", "poi_count", "retail_count"]:
            merged[col] = merged[col].fillna(0)
        merged["attractions"] = (
            EMPLOY_WEIGHT  * merged["employment_proxy"]
            + POI_WEIGHT   * merged["poi_count"]
            + RETAIL_WEIGHT * merged["retail_count"]
        ).clip(lower=0)
        census_df = merged.drop(columns=["employment_proxy", "poi_count", "retail_count"])
        print("  [OK] Attractions from DENUE employment + POI + retail")
    else:
        census_df["attractions"] = census_df["productions"].copy()
        print("  [NOTE] Attractions = population proxy (DENUE not loaded)")

    # Scale so sum(A) == sum(P)
    total_prod = census_df["productions"].sum()
    total_attr = census_df["attractions"].sum()
    if total_attr > 0:
        census_df["attractions"] *= total_prod / total_attr

    print(f"  [OK] Total productions : {total_prod:,.0f}")
    print(f"  [OK] Mean productions  : {census_df['productions'].mean():,.1f}")
    return census_df


# =============================================================================
# Step 4: Gravity model
# =============================================================================
def load_ageb_centroids(shp_path: Path, cve_agebs: list) -> pd.DataFrame:
    """Load AGEB polygon centroids from INEGI shapefile, reprojected to EPSG:6372.

    Returns a DataFrame with columns: cve_ageb, x, y (projected metres).
    AGEBs not matched in the shapefile are dropped (they will be absent from trip_df).
    """
    import geopandas as gpd
    print(f"[Step 4a] Loading AGEB centroids from shapefile: {shp_path.name}...")
    gdf = gpd.read_file(shp_path)
    gdf = gdf.to_crs("EPSG:6372")

    # INEGI Marco Geoestadistico: try CVEGEO first (13-char), then build from parts
    if "CVEGEO" in gdf.columns:
        gdf["cve_ageb"] = gdf["CVEGEO"].astype(str).str.strip()
    else:
        # Build from individual code columns (CVE_ENT, CVE_MUN, CVE_LOC, CVE_AGEB)
        parts = {"CVE_ENT": 2, "CVE_MUN": 3, "CVE_LOC": 4, "CVE_AGEB": 4}
        for col, width in parts.items():
            if col not in gdf.columns:
                raise KeyError(f"Shapefile missing expected column: {col}")
        gdf["cve_ageb"] = (
            gdf["CVE_ENT"].astype(str).str.zfill(2)
            + gdf["CVE_MUN"].astype(str).str.zfill(3)
            + gdf["CVE_LOC"].astype(str).str.zfill(4)
            + gdf["CVE_AGEB"].astype(str).str.zfill(4)
        )

    centroids = gdf.copy()
    centroids["x"] = gdf.geometry.centroid.x
    centroids["y"] = gdf.geometry.centroid.y
    centroids = centroids[["cve_ageb", "x", "y"]].copy()

    # Keep only AGEBs that appear in the census
    cve_set = set(cve_agebs)
    matched = centroids[centroids["cve_ageb"].isin(cve_set)]
    n_total = len(cve_agebs)
    n_matched = len(matched)
    print(f"  [OK] {n_matched:,} / {n_total:,} AGEBs matched to shapefile")
    if n_matched < n_total * 0.90:
        print(f"  [WARN] Less than 90% match rate -- check CVEGEO format in shapefile")
    return matched


def _random_centroids_fallback(census_df: pd.DataFrame) -> pd.DataFrame:
    """Random proxy centroids within MTY bbox (used only when shapefile is absent)."""
    print("[Step 4a] No AGEB shapefile found -- using random proxy centroids")
    print("  [WARN] Gravity model distances are meaningless with random centroids.")
    rng = np.random.default_rng(42)
    n = len(census_df)
    x_range = (BBOX_LON_MAX - BBOX_LON_MIN) * 100_173
    y_range = (BBOX_LAT_MAX - BBOX_LAT_MIN) * 110_574
    census_df = census_df.copy()
    census_df["x"] = rng.uniform(0, x_range, n)
    census_df["y"] = rng.uniform(0, y_range, n)
    return census_df


def run_gravity_model(trip_df: pd.DataFrame) -> np.ndarray:
    print("[Step 4] Running doubly-constrained gravity model...")
    from scipy.spatial.distance import cdist
    from src.w1_gravity_model import furness_ipf

    coords = trip_df[["x", "y"]].values
    D = cdist(coords, coords, metric="euclidean")
    np.fill_diagonal(D, 0.0)

    prods = trip_df["productions"].values.astype(float)
    attrs = trip_df["attractions"].values.astype(float)

    print(f"  [OK] Distance matrix: {D.shape}, mean non-zero dist = {D[D>0].mean():.0f} m")
    T = furness_ipf(prods, attrs, D, beta=GRAVITY_BETA,
                    max_iter=GRAVITY_MAX_ITER, tol=GRAVITY_TOL)
    return T, D


# =============================================================================
# Step 5: Transit demand surface
# =============================================================================
def compute_transit_demand(trip_df: pd.DataFrame, T: np.ndarray) -> pd.DataFrame:
    print("[Step 5] Computing transit demand surface...")

    # Total OD demand per AGEB (produced + attracted)
    n = len(trip_df)
    produced_flow  = T.sum(axis=1)
    attracted_flow = T.sum(axis=0)
    total_demand   = produced_flow + attracted_flow

    result = trip_df[["cve_ageb", "vehicle_rate"]].copy()
    result["total_demand"]       = total_demand
    result["transit_propensity"] = (1.0 - result["vehicle_rate"]).clip(0, 1)
    result["transit_demand"]     = result["total_demand"] * result["transit_propensity"]

    print(f"  [OK] Mean transit_propensity : {result['transit_propensity'].mean():.3f}")
    print(f"  [OK] Mean transit_demand     : {result['transit_demand'].mean():,.1f}")
    return result


# =============================================================================
# Step 6: Write outputs
# =============================================================================
def write_outputs(result: pd.DataFrame, T: np.ndarray, cve_list: list) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[Step 6] Writing outputs to outputs/w9/...")

    result.to_csv(OUTPUT_DIR / "mty_demand_surface.csv", index=False)
    print("  [OK] CSV -> outputs/w9/mty_demand_surface.csv")

    # OD matrix summary
    n_pairs = int((T >= GRAVITY_FLOW_THRESHOLD).sum()) - len(cve_list)  # minus diagonal
    pd.DataFrame([{
        "city"                : CITY_NAME,
        "n_agebs"             : len(cve_list),
        "beta"                : GRAVITY_BETA,
        "flow_threshold"      : GRAVITY_FLOW_THRESHOLD,
        "n_od_pairs_stored"   : max(0, n_pairs),
        "total_flow"          : float(T.sum()),
        "mean_transit_demand" : result["transit_demand"].mean(),
        "mean_vehicle_rate"   : result["vehicle_rate"].mean(),
        "mean_transit_prop"   : result["transit_propensity"].mean(),
    }]).to_csv(OUTPUT_DIR / "mty_tier1_summary.csv", index=False)
    print("  [OK] CSV -> outputs/w9/mty_tier1_summary.csv")


# =============================================================================
# Step 7: Transfer comparison
# =============================================================================
def print_transfer_comparison(mty_result: pd.DataFrame) -> None:
    print("\n" + "=" * 70)
    print("TRANSFER COMPARISON: ZMG vs Monterrey")
    print("=" * 70)

    # ZMG reference values (from W1 run, documented in CLAUDE.md)
    zmg_stats = {
        "city"                : "ZMG (Guadalajara)",
        "n_agebs"             : 2068,
        "mean_vehicle_rate"   : 0.577,
        "mean_transit_prop"   : 0.423,
        "cve_ent"             : "14",
        "n_municipalities"    : 10,
    }

    mty_stats = {
        "city"                : f"{CITY_NAME} (W9 run)",
        "n_agebs"             : len(mty_result),
        "mean_vehicle_rate"   : mty_result["vehicle_rate"].mean(),
        "mean_transit_prop"   : mty_result["transit_propensity"].mean(),
        "cve_ent"             : CVE_ENT,
        "n_municipalities"    : len(ZM_MUNICIPALITIES),
    }

    print(f"  {'Metric':<30} {'ZMG':>15} {'Monterrey':>15}")
    print(f"  {'-'*30} {'-'*15} {'-'*15}")
    for key in ["n_agebs", "n_municipalities", "mean_vehicle_rate", "mean_transit_prop"]:
        zmg_val = zmg_stats.get(key, "N/A")
        mty_val = mty_stats.get(key, "N/A")
        if isinstance(zmg_val, float):
            print(f"  {key:<30} {zmg_val:>15.3f} {mty_val:>15.3f}")
        else:
            print(f"  {key:<30} {zmg_val!s:>15} {mty_val!s:>15}")

    vr_diff = mty_stats["mean_vehicle_rate"] - zmg_stats["mean_vehicle_rate"]
    print(f"\n  Vehicle rate delta (MTY - ZMG): {vr_diff:+.3f}")
    if vr_diff > 0.05:
        print("  [NOTE] Monterrey has higher car ownership -> lower transit propensity")
    elif vr_diff < -0.05:
        print("  [NOTE] Monterrey has lower car ownership -> higher transit propensity")
    else:
        print("  [NOTE] Car ownership levels are similar between cities")

    transfer_report = pd.DataFrame([zmg_stats, mty_stats])
    transfer_report.to_csv(OUTPUT_DIR / "transfer_comparison.csv", index=False)
    print(f"\n  [OK] Transfer comparison -> outputs/w9/transfer_comparison.csv")


# =============================================================================
# Main
# =============================================================================
def main():
    print("\n" + "=" * 70)
    print(f"W9.5 -- TIER-1 PIPELINE FOR {CITY_NAME.upper()}")
    print("=" * 70)

    # Step 1: Check for census data
    census_path = find_census_file()
    if census_path is None:
        print_census_download_instructions()
        print("[INFO] Pipeline cannot proceed without census data. Exiting.")
        sys.exit(0)

    print(f"[Step 1] Census data found: {census_path}")

    # Steps 2-5: Run pipeline
    census_df = load_census(census_path)

    denue_path = find_denue_file()
    if denue_path:
        place_df = load_denue_features(denue_path)
    else:
        place_df = None
        print("[Step 2b] DENUE not found; attractions will use population proxy")

    trip_df = compute_trip_ends(census_df, place_df)

    shp_path = find_ageb_shp()
    if shp_path:
        centroids = load_ageb_centroids(shp_path, trip_df["cve_ageb"].tolist())
        trip_df = trip_df.merge(centroids, on="cve_ageb", how="inner")
        print(f"  [OK] {len(trip_df):,} AGEBs with real centroids")
    else:
        trip_df = _random_centroids_fallback(trip_df)

    T, D      = run_gravity_model(trip_df)
    result    = compute_transit_demand(trip_df, T)

    # Step 6: Write outputs
    write_outputs(result, T, trip_df["cve_ageb"].tolist())

    # Step 7: Transfer comparison
    print_transfer_comparison(result)

    print("\n" + "=" * 70)
    print(f"W9.5 TIER-1 PIPELINE COMPLETE ({CITY_NAME.upper()})")
    print("=" * 70)
    print(result[["total_demand", "vehicle_rate", "transit_propensity", "transit_demand"]]
          .describe().to_string())


if __name__ == "__main__":
    main()
