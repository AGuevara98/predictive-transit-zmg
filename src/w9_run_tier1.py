"""
W9.5 -- Tier-1 Pipeline Orchestrator (city-parameterized)
=========================================================
Runs the W1-equivalent demand-estimation pipeline for a transfer city using
Tier-1 data only (INEGI CPV2020 census, DENUE, AGEB shapefile). No transit
supply data required.

Cities (select with --city; default mty for backward compatibility):
  mty  -> Monterrey, Nuevo Leon        (src/w9_city_config.py)
  tol  -> Toluca, Estado de Mexico     (src/w9_city_config_tol.py)  -- LARGE metro
  ags  -> Aguascalientes               (src/w9_city_config_ags.py)  -- COMPACT metro

Steps: load census -> DENUE attractions -> shapefile centroids -> Furness gravity
-> vehicle-ownership transit-propensity weighting -> outputs/w9/{key}_*.csv +
a ZMG-vs-city transfer comparison.

Usage:
    python src/w9_run_tier1.py                # Monterrey (default)
    python src/w9_run_tier1.py --city tol     # Toluca
    python src/w9_run_tier1.py --city ags     # Aguascalientes

Data paths are derived by convention from CITY_KEY + CVE_ENT (matching the
committed MTY layout), with raw-INEGI-download layouts checked as fallback:
  census slim : data/raw/census/ageb_urbana_{ENT}_cpv2020_{KEY}.csv
  denue combo : data/raw/denue/{KEY}_denue_combined.csv
  ageb shp    : data/2020_1_{ENT}_A/2020_1_{ENT}_A.shp

If census data is absent the script prints download instructions and exits 0.
"""
import argparse
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import EMPLOYMENT_PROXY_MAP, SCIAN_SECTORS

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "outputs" / "w9"
DATA_DIR     = PROJECT_ROOT / "data"

# City key -> config module name
CITY_CONFIGS = {
    "mty": "src.w9_city_config",
    "tol": "src.w9_city_config_tol",
    "ags": "src.w9_city_config_ags",
}

# ZMG reference stats (corrected 1,881-AGEB universe; from the W1 run) for the
# transfer comparison. mean_vehicle_rate/transit_prop are beta-independent.
ZMG_REF = {
    "city": "ZMG (Guadalajara)", "n_agebs": 1881, "n_municipalities": 10,
    "mean_vehicle_rate": 0.577, "mean_transit_prop": 0.423, "cve_ent": "14",
}


def load_city_config(city_key: str):
    if city_key not in CITY_CONFIGS:
        raise SystemExit(f"Unknown --city '{city_key}'. Choose from {list(CITY_CONFIGS)}.")
    return importlib.import_module(CITY_CONFIGS[city_key])


def resolve_paths(cfg) -> dict:
    """Data-file candidate paths for a city, derived by convention + raw fallbacks."""
    ent, key = cfg.CVE_ENT, cfg.CITY_KEY
    census = [
        DATA_DIR / "raw" / "census" / f"ageb_urbana_{ent}_cpv2020_{key}.csv",
        DATA_DIR / cfg.CENSUS_DIR_NAME / "conjunto_de_datos" / cfg.CENSUS_CSV_NAME,
        DATA_DIR / cfg.CENSUS_CSV_NAME,
    ]
    denue = [
        DATA_DIR / "raw" / "denue" / f"{key}_denue_combined.csv",
        DATA_DIR / f"denue_{ent}_0420_csv" / "conjunto_de_datos" / f"denue_inegi_{ent}_.csv",
    ]
    denue += sorted(DATA_DIR.glob(f"denue_{ent}_*/conjunto_de_datos/denue_inegi_{ent}_.csv"))
    shp = [DATA_DIR / f"2020_1_{ent}_A" / f"2020_1_{ent}_A.shp"]
    shp += sorted(DATA_DIR.glob(f"2020_1_{ent}_*/*.shp"))
    return {"census": census, "denue": denue, "shp": shp}


def _first_existing(paths):
    for p in paths:
        if Path(p).exists():
            return Path(p)
    return None


def print_census_download_instructions(cfg, census_paths) -> None:
    print("\n" + "=" * 70)
    print(f"  CENSUS DATA NOT FOUND FOR {cfg.CITY_NAME.upper()} -- DOWNLOAD REQUIRED")
    print("=" * 70)
    print(f"\n  Expected (first is the committed slim-extract path):")
    for p in census_paths:
        print(f"    {p}")
    print(f"\n  Download steps:")
    print(f"  1. Portal (INEGI direct URLs 404 now; use the interactive picker):")
    print(f"     {cfg.CENSUS_ZIP_URL}")
    print(f"     Microdatos > AGEB y manzana urbana > state {cfg.CVE_ENT} > CSV")
    print(f"  2. Extract under data/{cfg.CENSUS_DIR_NAME}/ (or drop the raw CSV in data/)")
    print(f"  3. Slim to the ZM extract:")
    print(f"       python scripts/data_prep/make_city_census_extract.py --city {cfg.CITY_KEY}")
    print(f"  4. Re-run: python src/w9_run_tier1.py --city {cfg.CITY_KEY}")
    print()


# =============================================================================
# Step 2: Census + DENUE
# =============================================================================
def load_census(cfg, census_path: Path) -> pd.DataFrame:
    print(f"[Step 2] Loading census: {census_path.name}...")
    census = pd.read_csv(census_path, dtype=str, encoding="utf-8-sig")

    if "cve_ageb" in census.columns:
        # Committed slim extract: already AGEB-level + ZM-municipio filtered.
        pass
    else:
        census = census[census[cfg.COL_MZA] == "000"].copy()
        census["cve_ageb"] = (
            census[cfg.COL_ENTIDAD].str.zfill(2) + census[cfg.COL_MUN].str.zfill(3)
            + census[cfg.COL_LOC].str.zfill(4) + census[cfg.COL_AGEB].str.zfill(4)
        )
        census = census[census[cfg.COL_MUN].isin(cfg.ZM_MUNICIPALITIES)].copy()
    print(f"  [OK] {len(census):,} AGEB rows in {len(cfg.ZM_MUNICIPALITIES)} municipalities")

    for col in [cfg.POP_COL, cfg.VEHICLES_COL, cfg.OCCUPIED_HOUSING_COL]:
        if col in census.columns:
            census[col] = pd.to_numeric(census[col], errors="coerce").fillna(0)
        else:
            print(f"  [WARN] Column '{col}' not found; defaulting to 0")
            census[col] = 0.0

    if cfg.YOUTH_COL_COMBINED in census.columns:
        census["youth_pop"] = pd.to_numeric(census[cfg.YOUTH_COL_COMBINED], errors="coerce").fillna(0)
    else:
        for c in [cfg.YOUTH_COL_LOW, cfg.YOUTH_COL_HIGH]:
            if c not in census.columns:
                census[c] = 0
            census[c] = pd.to_numeric(census[c], errors="coerce").fillna(0)
        census["youth_pop"] = census[cfg.YOUTH_COL_LOW] + census[cfg.YOUTH_COL_HIGH]

    census["pe_youth_share"] = census["youth_pop"] / census[cfg.POP_COL].clip(lower=1)
    census["pe_population"]  = census[cfg.POP_COL]
    census["vehicle_rate"]   = (
        census[cfg.VEHICLES_COL] / census[cfg.OCCUPIED_HOUSING_COL].clip(lower=1)
    ).clip(0, 1)

    print(f"  [OK] Mean population  : {census['pe_population'].mean():,.0f}")
    print(f"  [OK] Mean vehicle_rate: {census['vehicle_rate'].mean():.3f}")
    return census[["cve_ageb", "pe_population", "pe_youth_share", "vehicle_rate"]]


def load_denue_features(cfg, denue_path: Path) -> pd.DataFrame:
    print(f"[Step 2b] Loading DENUE: {denue_path.name}...")
    usecols = ["cve_ent", "cve_mun", "cve_loc", "ageb", "codigo_act", "per_ocu"]
    denue = pd.read_csv(denue_path, dtype=str, encoding="latin-1", usecols=usecols)

    denue = denue[denue["cve_ent"].str.strip().str.zfill(2) == cfg.CVE_ENT].copy()
    denue["cve_mun_z"] = denue["cve_mun"].str.strip().str.zfill(3)
    denue = denue[denue["cve_mun_z"].isin(cfg.ZM_MUNICIPALITIES)].copy()
    denue["cve_ageb"] = (
        denue["cve_ent"].str.strip().str.zfill(2) + denue["cve_mun_z"]
        + denue["cve_loc"].str.strip().str.zfill(4) + denue["ageb"].str.strip().str.zfill(4)
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
    return agg


# =============================================================================
# Step 3: Trip ends
# =============================================================================
def compute_trip_ends(cfg, census_df, place_df=None) -> pd.DataFrame:
    print("[Step 3] Computing trip productions and attractions...")
    rate = cfg.TRIPS_PER_PERSON_DAY * (1 + cfg.YOUTH_MULTIPLIER * census_df["pe_youth_share"])
    census_df = census_df.copy()
    census_df["productions"] = (census_df["pe_population"] * rate).clip(lower=0)

    if place_df is not None:
        merged = census_df.merge(place_df, on="cve_ageb", how="left")
        for col in ["employment_proxy", "poi_count", "retail_count"]:
            merged[col] = merged[col].fillna(0)
        merged["attractions"] = (
            cfg.EMPLOY_WEIGHT * merged["employment_proxy"]
            + cfg.POI_WEIGHT  * merged["poi_count"]
            + cfg.RETAIL_WEIGHT * merged["retail_count"]
        ).clip(lower=0)
        census_df = merged.drop(columns=["employment_proxy", "poi_count", "retail_count"])
        print("  [OK] Attractions from DENUE employment + POI + retail")
    else:
        census_df["attractions"] = census_df["productions"].copy()
        print("  [NOTE] Attractions = population proxy (DENUE not loaded)")

    total_prod = census_df["productions"].sum()
    total_attr = census_df["attractions"].sum()
    if total_attr > 0:
        census_df["attractions"] *= total_prod / total_attr
    print(f"  [OK] Total productions : {total_prod:,.0f}")
    return census_df


# =============================================================================
# Step 4: Gravity model
# =============================================================================
def load_ageb_centroids(shp_path: Path, cve_agebs: list) -> pd.DataFrame:
    import geopandas as gpd
    print(f"[Step 4a] Loading AGEB centroids from shapefile: {shp_path.name}...")
    gdf = gpd.read_file(shp_path).to_crs("EPSG:6372")
    if "CVEGEO" in gdf.columns:
        gdf["cve_ageb"] = gdf["CVEGEO"].astype(str).str.strip()
    else:
        parts = {"CVE_ENT": 2, "CVE_MUN": 3, "CVE_LOC": 4, "CVE_AGEB": 4}
        for col in parts:
            if col not in gdf.columns:
                raise KeyError(f"Shapefile missing expected column: {col}")
        gdf["cve_ageb"] = (
            gdf["CVE_ENT"].astype(str).str.zfill(2) + gdf["CVE_MUN"].astype(str).str.zfill(3)
            + gdf["CVE_LOC"].astype(str).str.zfill(4) + gdf["CVE_AGEB"].astype(str).str.zfill(4)
        )
    centroids = gdf.copy()
    centroids["x"] = gdf.geometry.centroid.x
    centroids["y"] = gdf.geometry.centroid.y
    matched = centroids[centroids["cve_ageb"].isin(set(cve_agebs))][["cve_ageb", "x", "y"]]
    print(f"  [OK] {len(matched):,} / {len(cve_agebs):,} AGEBs matched to shapefile")
    if len(matched) < len(cve_agebs) * 0.90:
        print("  [WARN] <90% match rate -- check CVEGEO format / municipio codes")
    return matched


def _random_centroids_fallback(cfg, census_df) -> pd.DataFrame:
    print("[Step 4a] No AGEB shapefile found -- using random proxy centroids")
    print("  [WARN] Gravity model distances are meaningless with random centroids.")
    rng = np.random.default_rng(42)
    n = len(census_df)
    census_df = census_df.copy()
    census_df["x"] = rng.uniform(0, (cfg.BBOX_LON_MAX - cfg.BBOX_LON_MIN) * 100_173, n)
    census_df["y"] = rng.uniform(0, (cfg.BBOX_LAT_MAX - cfg.BBOX_LAT_MIN) * 110_574, n)
    return census_df


def run_gravity_model(cfg, trip_df):
    print("[Step 4] Running doubly-constrained gravity model...")
    from scipy.spatial.distance import cdist
    from src.w1_gravity_model import furness_ipf
    coords = trip_df[["x", "y"]].values
    D = cdist(coords, coords, metric="euclidean")
    np.fill_diagonal(D, 0.0)
    prods = trip_df["productions"].values.astype(float)
    attrs = trip_df["attractions"].values.astype(float)
    print(f"  [OK] Distance matrix: {D.shape}, mean non-zero dist = {D[D>0].mean():.0f} m")
    T = furness_ipf(prods, attrs, D, beta=cfg.GRAVITY_BETA,
                    max_iter=cfg.GRAVITY_MAX_ITER, tol=cfg.GRAVITY_TOL)
    return T, D


# =============================================================================
# Step 5: Transit demand surface
# =============================================================================
def compute_transit_demand(trip_df, T) -> pd.DataFrame:
    print("[Step 5] Computing transit demand surface...")
    total_demand = T.sum(axis=1) + T.sum(axis=0)
    result = trip_df[["cve_ageb", "vehicle_rate"]].copy()
    result["total_demand"]       = total_demand
    result["transit_propensity"] = (1.0 - result["vehicle_rate"]).clip(0, 1)
    result["transit_demand"]     = result["total_demand"] * result["transit_propensity"]
    print(f"  [OK] Mean transit_propensity : {result['transit_propensity'].mean():.3f}")
    print(f"  [OK] Mean transit_demand     : {result['transit_demand'].mean():,.1f}")
    return result


# =============================================================================
# Step 6-7: Outputs + transfer comparison
# =============================================================================
def write_outputs(cfg, result, T, cve_list) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    key = cfg.CITY_KEY
    print(f"[Step 6] Writing outputs to outputs/w9/ ({key})...")
    result.to_csv(OUTPUT_DIR / f"{key}_demand_surface.csv", index=False)
    n_pairs = int((T >= cfg.GRAVITY_FLOW_THRESHOLD).sum()) - len(cve_list)
    pd.DataFrame([{
        "city": cfg.CITY_NAME, "n_agebs": len(cve_list), "beta": cfg.GRAVITY_BETA,
        "flow_threshold": cfg.GRAVITY_FLOW_THRESHOLD, "n_od_pairs_stored": max(0, n_pairs),
        "total_flow": float(T.sum()), "mean_transit_demand": result["transit_demand"].mean(),
        "mean_vehicle_rate": result["vehicle_rate"].mean(),
        "mean_transit_prop": result["transit_propensity"].mean(),
    }]).to_csv(OUTPUT_DIR / f"{key}_tier1_summary.csv", index=False)
    print(f"  [OK] {key}_demand_surface.csv + {key}_tier1_summary.csv")


def print_transfer_comparison(cfg, result) -> None:
    print("\n" + "=" * 70)
    print(f"TRANSFER COMPARISON: ZMG vs {cfg.CITY_NAME}")
    print("=" * 70)
    city_stats = {
        "city": f"{cfg.CITY_NAME} (W9 run)", "n_agebs": len(result),
        "n_municipalities": len(cfg.ZM_MUNICIPALITIES),
        "mean_vehicle_rate": result["vehicle_rate"].mean(),
        "mean_transit_prop": result["transit_propensity"].mean(), "cve_ent": cfg.CVE_ENT,
    }
    print(f"  {'Metric':<24} {'ZMG':>15} {cfg.CITY_NAME:>18}")
    print(f"  {'-'*24} {'-'*15} {'-'*18}")
    for key in ["n_agebs", "n_municipalities", "mean_vehicle_rate", "mean_transit_prop"]:
        z, c = ZMG_REF.get(key), city_stats.get(key)
        if isinstance(z, float):
            print(f"  {key:<24} {z:>15.3f} {c:>18.3f}")
        else:
            print(f"  {key:<24} {z!s:>15} {c!s:>18}")
    vr_diff = city_stats["mean_vehicle_rate"] - ZMG_REF["mean_vehicle_rate"]
    print(f"\n  Vehicle rate delta ({cfg.CITY_KEY} - ZMG): {vr_diff:+.3f}")
    if vr_diff > 0.05:
        print("  [NOTE] Higher car ownership -> lower transit propensity than ZMG")
    elif vr_diff < -0.05:
        print("  [NOTE] Lower car ownership -> higher transit propensity than ZMG")
    else:
        print("  [NOTE] Car ownership similar to ZMG")
    pd.DataFrame([ZMG_REF, city_stats]).to_csv(
        OUTPUT_DIR / f"transfer_comparison_{cfg.CITY_KEY}.csv", index=False)
    print(f"  [OK] transfer_comparison_{cfg.CITY_KEY}.csv")


# =============================================================================
# Main
# =============================================================================
def run_city(city_key: str) -> None:
    cfg = load_city_config(city_key)
    paths = resolve_paths(cfg)
    print("\n" + "=" * 70)
    print(f"W9.5 -- TIER-1 PIPELINE FOR {cfg.CITY_NAME.upper()} ({city_key})")
    print("=" * 70)

    census_path = _first_existing(paths["census"])
    if census_path is None:
        print_census_download_instructions(cfg, paths["census"])
        print("[INFO] Pipeline cannot proceed without census data. Exiting.")
        return
    print(f"[Step 1] Census data found: {census_path}")

    census_df = load_census(cfg, census_path)

    denue_path = _first_existing(paths["denue"])
    place_df = load_denue_features(cfg, denue_path) if denue_path else None
    if denue_path is None:
        print("[Step 2b] DENUE not found; attractions will use population proxy")

    trip_df = compute_trip_ends(cfg, census_df, place_df)

    shp_path = _first_existing(paths["shp"])
    if shp_path:
        centroids = load_ageb_centroids(shp_path, trip_df["cve_ageb"].tolist())
        trip_df = trip_df.merge(centroids, on="cve_ageb", how="inner")
        print(f"  [OK] {len(trip_df):,} AGEBs with real centroids")
    else:
        trip_df = _random_centroids_fallback(cfg, trip_df)

    T, _   = run_gravity_model(cfg, trip_df)
    result = compute_transit_demand(trip_df, T)
    write_outputs(cfg, result, T, trip_df["cve_ageb"].tolist())
    print_transfer_comparison(cfg, result)

    print("\n" + "=" * 70)
    print(f"W9.5 TIER-1 PIPELINE COMPLETE ({cfg.CITY_NAME.upper()})")
    print("=" * 70)
    print(result[["total_demand", "vehicle_rate", "transit_propensity", "transit_demand"]]
          .describe().to_string())


def main() -> None:
    ap = argparse.ArgumentParser(description="W9 Tier-1 demand pipeline (city-parameterized)")
    ap.add_argument("--city", default="mty", choices=list(CITY_CONFIGS),
                    help="Transfer city (default: mty)")
    run_city(ap.parse_args().city)


if __name__ == "__main__":
    main()
