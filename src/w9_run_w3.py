"""
W9 W3 -- Transit Accessibility + Coverage-Gap for a transfer city (CSV-based)
============================================================================
The GTFS payoff Monterrey could never reach: builds the W3 supply layer
(cumulative-opportunities accessibility) and the coverage-gap diagnostic for a
transfer city, entirely from files (no DB), reusing the pure ZMG W3 functions.

Inputs (per city, --city {tol,ags,mty}):
  - GTFS at cfg.GTFS_DIR (stops/stop_times/frequencies)
  - AGEB centroids from the committed shapefile (data/2020_1_{ENT}_A/)
  - per-AGEB employment "opportunity" from the slim DENUE extract
  - transit_demand from the Tier-1 demand surface (outputs/w9/{key}_demand_surface.csv)

Outputs: outputs/w9/{key}_accessibility.csv, {key}_coverage_gap.csv

Usage:
    python src/w9_run_w3.py --city ags      # compact -- fast
    python src/w9_run_w3.py --city tol      # large -- slower (60k stops)
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import CRS_CANONICAL
# Reuse the pure ZMG W3 building blocks (module-level engines are lazy -> no DB hit on import)
from src.w3_accessibility import (
    build_transit_graph, ageb_stop_join, compute_accessibility,
    time_to_minutes, normalize_log1p_minmax,
)
from src.w3_coverage_gap import quintile_rank, assign_gap_category
from src.w9_run_tier1 import load_city_config, resolve_paths, load_denue_features, _first_existing

OUTPUT_DIR = ROOT / "outputs" / "w9"
GAP_EPSILON = 1.0
ZMG_HIGH_GAP_PCT = 20.7  # ZMG baseline High-gap share for context


# ---------------------------------------------------------------------------
# City-parameterized GTFS loaders (mirror w3_accessibility but read cfg.GTFS_DIR)
# ---------------------------------------------------------------------------
def load_stops(gtfs_dir: Path) -> gpd.GeoDataFrame:
    stops = pd.read_csv(gtfs_dir / "stops.txt", dtype={"stop_id": str})
    stops = stops.dropna(subset=["stop_lat", "stop_lon"])
    gdf = gpd.GeoDataFrame(
        stops, geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]),
        crs="EPSG:4326",
    ).to_crs(CRS_CANONICAL)
    print(f"  [OK] {len(gdf):,} GTFS stops")
    return gdf


def load_stop_times(gtfs_dir: Path) -> pd.DataFrame:
    st = pd.read_csv(
        gtfs_dir / "stop_times.txt", dtype={"trip_id": str, "stop_id": str},
        usecols=["trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"],
    )
    st["dep_min"] = st["departure_time"].apply(time_to_minutes)
    st["arr_min"] = st["arrival_time"].apply(time_to_minutes)
    print(f"  [OK] {len(st):,} stop_time records")
    return st


def load_frequencies(gtfs_dir: Path) -> dict:
    fp = gtfs_dir / "frequencies.txt"
    if not fp.exists():
        print("  [WARN] no frequencies.txt -- default headway used")
        return {}
    freq = pd.read_csv(fp, dtype={"trip_id": str})
    freq["headway_min"] = pd.to_numeric(freq["headway_secs"], errors="coerce") / 60.0
    return freq.groupby("trip_id")["headway_min"].mean().to_dict()


def load_ageb_centroids(shp_path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shp_path).to_crs(CRS_CANONICAL)
    if "CVEGEO" in gdf.columns:
        gdf["cve_ageb"] = gdf["CVEGEO"].astype(str).str.strip()
    else:
        gdf["cve_ageb"] = (
            gdf["CVE_ENT"].astype(str).str.zfill(2) + gdf["CVE_MUN"].astype(str).str.zfill(3)
            + gdf["CVE_LOC"].astype(str).str.zfill(4) + gdf["CVE_AGEB"].astype(str).str.zfill(4))
    cent = gpd.GeoDataFrame(
        gdf[["cve_ageb"]].copy(), geometry=gdf.geometry.centroid, crs=CRS_CANONICAL)
    cent = cent.rename_geometry("geom")
    return cent


def load_employment(cfg, paths, agebs) -> pd.DataFrame:
    """Per-AGEB opportunity for accessibility. Prefer DENUE employment (matches ZMG);
    fall back to census population if DENUE is absent."""
    denue_path = _first_existing(paths["denue"])
    if denue_path is not None:
        agg = load_denue_features(cfg, denue_path)  # cve_ageb, employment_proxy, ...
        emp = agg.rename(columns={"employment_proxy": "p_employment_proxy"})[
            ["cve_ageb", "p_employment_proxy"]]
        print(f"  [OK] opportunity = DENUE employment ({len(emp):,} AGEBs)")
        return emp
    census_path = _first_existing(paths["census"])
    c = pd.read_csv(census_path, dtype=str)
    c["p_employment_proxy"] = pd.to_numeric(c["POBTOT"], errors="coerce").fillna(0.0)
    print("  [WARN] DENUE absent -> opportunity = census population (not jobs)")
    return c[["cve_ageb", "p_employment_proxy"]]


def compute_gap(demand, access):
    m = demand.merge(access, on="cve_ageb", how="outer")
    m["transit_demand"] = m["transit_demand"].fillna(0.0)
    m["accessibility_score"] = m["accessibility_score"].fillna(0.0)
    m["coverage_gap_raw"] = m["transit_demand"] / (m["accessibility_score"] + GAP_EPSILON)
    m["coverage_gap_n"] = normalize_log1p_minmax(m["coverage_gap_raw"])
    m["demand_quantile"] = quintile_rank(m["transit_demand"])
    m["access_quantile"] = quintile_rank(m["accessibility_score"])
    m["gap_category"] = assign_gap_category(m["demand_quantile"], m["access_quantile"])
    return m


def run_city(city_key: str) -> None:
    cfg = load_city_config(city_key)
    paths = resolve_paths(cfg)
    gtfs_dir = ROOT / cfg.GTFS_DIR
    print("\n" + "=" * 70)
    print(f"W9 W3 -- ACCESSIBILITY + COVERAGE-GAP for {cfg.CITY_NAME.upper()} ({city_key})")
    print("=" * 70)
    if not (gtfs_dir / "stops.txt").exists():
        raise SystemExit(f"GTFS not found at {gtfs_dir} (see w9_gtfs_scouting_findings.md).")

    print("[1] Loading GTFS...")
    stops = load_stops(gtfs_dir)
    stop_times = load_stop_times(gtfs_dir)
    headway = load_frequencies(gtfs_dir)

    print("[2] Building transit graph...")
    G = build_transit_graph(stop_times, headway)

    print("[3] Loading AGEB centroids + employment...")
    shp = _first_existing(paths["shp"])
    agebs = load_ageb_centroids(shp)
    # Restrict to the ZM AGEB universe actually in the demand surface
    demand = pd.read_csv(OUTPUT_DIR / f"{city_key}_demand_surface.csv", dtype={"cve_ageb": str})
    demand["transit_demand"] = pd.to_numeric(demand["transit_demand"], errors="coerce").fillna(0.0)
    agebs = agebs[agebs["cve_ageb"].isin(set(demand["cve_ageb"]))].reset_index(drop=True)
    print(f"  [OK] {len(agebs):,} AGEBs (matched to demand surface)")
    emp = load_employment(cfg, paths, agebs)

    print("[4] AGEB<->stop join (400m)...")
    ageb_stop = ageb_stop_join(agebs, stops)

    print("[5] Computing accessibility (Dijkstra, 45-min budget)...")
    acc = compute_accessibility(agebs, stops, G, ageb_stop, emp)
    acc["accessibility_n"] = normalize_log1p_minmax(acc["accessibility_score"])

    print("[6] Coverage-gap index...")
    gap = compute_gap(demand[["cve_ageb", "transit_demand"]], acc[["cve_ageb", "accessibility_score"]])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    acc.to_csv(OUTPUT_DIR / f"{city_key}_accessibility.csv", index=False)
    gap.to_csv(OUTPUT_DIR / f"{city_key}_coverage_gap.csv", index=False)

    n = len(gap)
    n_zero = int((acc["accessibility_score"] == 0).sum())
    cats = gap["gap_category"].value_counts().to_dict()
    high = cats.get("High-gap", 0)
    print("\n" + "=" * 70)
    print(f"W9 W3 COMPLETE ({cfg.CITY_NAME})")
    print("=" * 70)
    print(f"  AGEBs: {n}   |   zero-accessibility (unserved): {n_zero} ({n_zero/n:.1%})")
    print(f"  Non-zero accessibility: {n - n_zero}")
    for cat in ["High-gap", "Medium-gap", "Low-gap"]:
        c = cats.get(cat, 0)
        print(f"    {cat:<11}: {c:>4} ({c/n:.1%})")
    print(f"  High-gap share: {high/n:.1%}  (ZMG baseline {ZMG_HIGH_GAP_PCT}%)")
    print(f"  [OK] outputs/w9/{city_key}_accessibility.csv, {city_key}_coverage_gap.csv")


def main() -> None:
    ap = argparse.ArgumentParser(description="W9 W3 accessibility + coverage-gap (city-parameterized)")
    ap.add_argument("--city", required=True, choices=["tol", "ags", "mty"])
    run_city(ap.parse_args().city)


if __name__ == "__main__":
    main()
