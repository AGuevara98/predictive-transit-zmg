"""
W9 W7 -- Existing Route Audit for a transfer city (CSV-based, no DB)
===================================================================
Scores every existing GTFS route of a transfer city against the W5
multi-objective function, flags weak routes (Low demand / Indirect / Redundant),
and proposes modifications -- the transfer analogue of the ZMG `run_w7.py`.

The single DB dependency of the ZMG scorer (the ST_DWithin served-AGEB spatial
join + load_ageb_context) is replaced with in-memory geopandas over the city's
AGEB shapefile centroids + the W3/W4 CSVs, exactly as w9_run_w6.py does for
corridor generation. Everything else reuses the PURE ZMG W5/W7 functions.

Note on transfer scope: Toluca (622 routes, ~30 concessioned operators) and
Aguascalientes (48 routes, single operator SIT) are ALL route_type=3 bus -- there
is no premium BRT/rail tier. The audit is mode-agnostic, so it transfers cleanly;
only the W8 hold-out backtest (which masks a premium tier) does not (see w9_run_w8).

Inputs (per city, --city {tol,ags}):
  - data/gtfs_{key}/                       (routes/trips/shapes/stops/stop_times)
  - data/2020_1_{ENT}_A/*.shp             (AGEB centroids -> served-AGEB join)
  - outputs/w9/{key}_coverage_gap.csv     (unserved_fraction, transit_demand)
  - outputs/w9/{key}_prioritization.csv   (equity_score)

Outputs: outputs/w9/{key}_route_scorecard.csv, {key}_route_modifications.csv,
         {key}_route_audit.geojson, {key}_w7_report.md

Usage:
    python src/w9_run_w7.py --city ags     # compact -- fast
    python src/w9_run_w7.py --city tol     # large  -- slower (622 routes)
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import CRS_CANONICAL
# Pure reused functions (none open a DB connection at import).
from src.w7_gtfs_loader import load_gtfs_routes
from src.w7_route_scorer import (
    assign_flags, compute_detour_ratio, route_to_candidate,
)
from src.w7_modifications import propose_modifications
from src.w5_objective import evaluate_objective
from src.w5_constraints import check_constraints
from src.w5_pareto import pareto_rank
from src.w5_types import W5Config
from src.w9_run_tier1 import load_city_config, resolve_paths, _first_existing
from src.w9_run_w6 import build_context_map

OUTPUT_DIR = ROOT / "outputs" / "w9"
CRS = CRS_CANONICAL
WALK_BUFFER_M = 400.0


def load_ageb_centroids(paths) -> gpd.GeoDataFrame:
    """AGEB centroids (cve_ageb, geometry) from the committed shapefile."""
    shp = gpd.read_file(_first_existing(paths["shp"])).to_crs(CRS)
    if "CVEGEO" in shp.columns:
        cve = shp["CVEGEO"].astype(str).str.strip()
    else:
        cve = (shp["CVE_ENT"].astype(str).str.zfill(2) + shp["CVE_MUN"].astype(str).str.zfill(3)
               + shp["CVE_LOC"].astype(str).str.zfill(4) + shp["CVE_AGEB"].astype(str).str.zfill(4))
    return gpd.GeoDataFrame({"cve_ageb": cve}, geometry=shp.geometry.centroid, crs=CRS)


def served_agebs_per_route(routes_gdf, centroids_gdf, buffer_m=WALK_BUFFER_M) -> dict:
    """cve_ageb list per route_id: AGEB centroids within buffer_m of the route.

    Vectorized spatial join (replaces the per-route ST_DWithin DB query).
    """
    bufs = gpd.GeoDataFrame(
        routes_gdf[["route_id"]].copy(),
        geometry=routes_gdf.geometry.buffer(buffer_m), crs=CRS,
    )
    joined = gpd.sjoin(centroids_gdf, bufs, predicate="within", how="inner")
    served = joined.groupby("route_id")["cve_ageb"].apply(list).to_dict()
    return {rid: served.get(rid, []) for rid in routes_gdf["route_id"]}


def score_routes(routes_gdf, served_map, ctx_map, config) -> pd.DataFrame:
    """W5 objective + constraints + Pareto + audit flags, entirely in-memory."""
    objectives, constraints, candidates = [], [], []
    for _, row in routes_gdf.iterrows():
        rid = row["route_id"]
        served = served_map.get(rid, [])
        rc = route_to_candidate(
            route_id=rid, route_km=float(row["route_km"]),
            n_stops=int(row["n_stops"]) if int(row["n_stops"]) >= 2 else 2,
            straight_line_km=float(row["straight_line_km"]),
            connects_to_existing=bool(row["connects_to_existing"]),
            served_ageb_ids=served,
        )
        ctxs = [ctx_map[a] for a in served if a in ctx_map]
        candidates.append(rc)
        objectives.append(evaluate_objective(rc, ctxs, config))
        constraints.append(check_constraints(rc, ctxs, config))
    ranks = pareto_rank(objectives)

    records = []
    for i, (_, row) in enumerate(routes_gdf.iterrows()):
        rid = row["route_id"]
        obj, cr, rc = objectives[i], constraints[i], candidates[i]
        detour = compute_detour_ratio(float(row["route_km"]), float(row["straight_line_km"]))
        records.append({
            "route_id": rid,
            "route_short_name": row.get("route_short_name", ""),
            "route_long_name": row.get("route_long_name", ""),
            "route_km": float(row["route_km"]),
            "n_stops": int(rc.n_stops),
            "straight_line_km": float(row["straight_line_km"]),
            "detour_ratio": round(detour, 3),
            "connects_to_existing": bool(row["connects_to_existing"]),
            "f1_demand_gain": float(obj.f1_demand_gain),
            "f2_route_km": float(obj.f2_route_km),
            "f3_equity": float(obj.f3_equity),
            "composite_score": float(obj.composite_score),
            "total_score": float(obj.total_score),
            "pareto_rank": int(ranks[i]),
            "feasible": bool(cr.feasible),
            "served_ageb_ids": set(served_map.get(rid, [])),
            "n_served_agebs": len(served_map.get(rid, [])),
        })

    flag_results = assign_flags(records)
    for rec, (flag, overlap_id) in zip(records, flag_results):
        rec["flag"] = flag
        rec["overlap_route_id"] = overlap_id
    for rec in records:
        rec["served_agebs"] = "|".join(sorted(rec["served_ageb_ids"]))
        del rec["served_ageb_ids"]
    return pd.DataFrame(records)


def write_report(city_key, cfg, scored_df, proposals) -> None:
    n = len(scored_df)
    fc = scored_df["flag"].value_counts().to_dict()
    n_flagged = int(scored_df["flag"].notna().sum())
    n_feasible = int(scored_df["feasible"].sum())
    # Stop-spacing diagnostic: concessioned feeds (e.g. Toluca) place a stop every
    # ~45-85m, which fails the W5 [300,1000]m spacing constraint independent of route
    # quality. Surface it so a low feasible count is read correctly.
    spacing = scored_df["route_km"] * 1000.0 / (scored_df["n_stops"].clip(lower=2) - 1)
    med_spacing = float(spacing.median())
    share_dense = float((spacing < 300).mean())
    top10 = scored_df.nlargest(10, "total_score")[
        ["route_id", "route_short_name", "total_score", "f1_demand_gain", "detour_ratio", "flag"]]
    flagged = scored_df[scored_df["flag"].notna()][
        ["route_id", "route_short_name", "total_score", "detour_ratio", "flag", "overlap_route_id"]
    ].sort_values("total_score")

    def md(df):
        out = ["| " + " | ".join(map(str, df.columns)) + " |",
               "|" + "|".join(["---"] * len(df.columns)) + "|"]
        for _, r in df.iterrows():
            out.append("| " + " | ".join(str(round(v, 3) if isinstance(v, float) else v)
                                          for v in r) + " |")
        return "\n".join(out)

    lines = [
        f"# W9 W7 Existing Route Audit -- {cfg.CITY_NAME}", "",
        f"Transfer analogue of ZMG's `run_w7.py`, CSV-based. All routes are "
        f"route_type=3 bus ({cfg.TRANSIT_OPERATOR}); the audit is mode-agnostic.", "",
        "## Summary", "",
        f"- **Routes audited:** {n}",
        f"- **Feasible (W5 constraints):** {int(scored_df['feasible'].sum())}",
        f"- **Routes flagged:** {n_flagged} "
        f"({fc.get('Low demand', 0)} Low demand, {fc.get('Indirect', 0)} Indirect, "
        f"{fc.get('Redundant', 0)} Redundant)",
        f"- **Modification proposals:** {len(proposals)}", "",
        f"> **Feasibility note:** median GTFS stop spacing is {med_spacing:.0f}m and "
        f"{share_dense:.0%} of routes sit below the W5 300m minimum. Where the feasible "
        f"count is low ({n_feasible}/{n} here), the binding constraint is this sub-300m stop "
        f"density in the source feed, not route directness or length -- the audit flags "
        f"(Low demand / Indirect / Redundant) and W5 scores are the primary signal and are "
        f"independent of the feasibility gate.", "",
        "## Score Distribution", "",
        f"- Mean total_score: {scored_df['total_score'].mean():.3f}  |  "
        f"median: {scored_df['total_score'].median():.3f}",
        f"- Mean detour_ratio: {scored_df['detour_ratio'].mean():.3f}",
        f"- Mean f1_demand_gain: {scored_df['f1_demand_gain'].mean():.3f}  |  "
        f"mean f3_equity: {scored_df['f3_equity'].mean():.3f}", "",
        "## Top 10 Routes by Score", "", md(top10), "",
        "## Flagged Routes", "",
        md(flagged) if not flagged.empty else "_No routes flagged._", "",
        "## Method", "",
        "1. GTFS route geometries from shapes.txt (EPSG:6372); straight_line_km = hull diameter.",
        "2. Served AGEBs: centroid within 400m of route (geopandas sjoin).",
        "3. W5 objective (f1 demand-gain, f2 length, f3 equity) + constraints (detour<=1.8, "
        "spacing 300-1000m, demand>=500/day, km<=30) + Pareto rank.",
        "4. Flags: Low demand (f1<0.2 & score<0.3), Indirect (detour>1.5), "
        "Redundant (served-AGEB Jaccard>=0.60 with a higher-scoring route).",
    ]
    (OUTPUT_DIR / f"{city_key}_w7_report.md").write_text("\n".join(lines), encoding="utf-8")


def run_city(city_key: str) -> None:
    cfg = load_city_config(city_key)
    paths = resolve_paths(cfg)
    config = W5Config()
    print("\n" + "=" * 70)
    print(f"W9 W7 -- ROUTE AUDIT for {cfg.CITY_NAME.upper()} ({city_key})")
    print("=" * 70)

    print("[1] Loading GTFS routes...")
    routes_gdf = load_gtfs_routes(data_dir=ROOT / cfg.GTFS_DIR).reset_index(drop=True)
    print(f"  [OK] {len(routes_gdf)} routes")

    print("[2] Loading AGEB centroids + served-AGEB join (400m)...")
    ctx_map = build_context_map(cfg)
    centroids = load_ageb_centroids(paths)
    # Restrict to the ZM study universe (the demand-surface AGEBs) so served counts
    # and redundancy Jaccard match the ZMG audit, which queries only base.ageb.
    centroids = centroids[centroids["cve_ageb"].isin(ctx_map)].reset_index(drop=True)
    served_map = served_agebs_per_route(routes_gdf, centroids)
    print(f"  [OK] {len(centroids)} study-universe AGEBs; "
          f"{sum(len(v) for v in served_map.values())} route-AGEB pairs")

    print("[3] Scoring routes (W5 objective + constraints + Pareto + flags)...")
    scored_df = score_routes(routes_gdf, served_map, ctx_map, config)
    n_flagged = int(scored_df["flag"].notna().sum())
    print(f"  [OK] {len(scored_df)} scored; {n_flagged} flagged")

    print("[4] Proposing modifications...")
    proposals = propose_modifications(scored_df, engine=None, config=config)

    print("[5] Writing outputs...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scorecard_cols = [
        "route_id", "route_short_name", "route_long_name", "route_km", "n_stops",
        "straight_line_km", "detour_ratio", "connects_to_existing", "n_served_agebs",
        "f1_demand_gain", "f2_route_km", "f3_equity", "composite_score", "total_score",
        "pareto_rank", "feasible", "flag", "overlap_route_id",
    ]
    scored_df[[c for c in scorecard_cols if c in scored_df.columns]].to_csv(
        OUTPUT_DIR / f"{city_key}_route_scorecard.csv", index=False)
    pd.DataFrame(proposals).to_csv(
        OUTPUT_DIR / f"{city_key}_route_modifications.csv", index=False)

    geo = routes_gdf.merge(
        scored_df[["route_id", "total_score", "pareto_rank", "feasible", "flag",
                   "detour_ratio", "n_served_agebs", "f1_demand_gain", "f3_equity"]],
        on="route_id", how="left").to_crs("EPSG:4326")
    geo.to_file(OUTPUT_DIR / f"{city_key}_route_audit.geojson", driver="GeoJSON")
    write_report(city_key, cfg, scored_df, proposals)

    fc = scored_df["flag"].value_counts().to_dict()
    print("\n" + "=" * 70)
    print(f"W9 W7 COMPLETE ({cfg.CITY_NAME}): {len(scored_df)} routes, {n_flagged} flagged")
    print(f"  Low demand={fc.get('Low demand', 0)}  Indirect={fc.get('Indirect', 0)}  "
          f"Redundant={fc.get('Redundant', 0)}  |  proposals={len(proposals)}")
    print("=" * 70)


def main() -> None:
    ap = argparse.ArgumentParser(description="W9 W7 route audit (city-parameterized)")
    ap.add_argument("--city", required=True, choices=["tol", "ags"])
    run_city(ap.parse_args().city)


if __name__ == "__main__":
    main()
