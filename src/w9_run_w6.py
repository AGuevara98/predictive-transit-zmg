"""
W9 W6 -- Corridor generation for a transfer city (CSV-based, no DB)
==================================================================
Runs the canonical re-architected W6 generator (frontier anchors -> MST-diameter
trunk -> anchor-directness feasibility gate) for a transfer city, entirely from
files, reusing the pure ZMG W6/W5 functions. The 4 DB-backed lookups
(load_gap_agebs, network_connected_agebs, get_served_agebs, load_ageb_context)
are replaced with in-memory geopandas equivalents over the city's coverage-gap
CSV + AGEB shapefile centroids + city GTFS stops.

Inputs (per city, --city {tol,ags}):
  - outputs/w9/{key}_coverage_gap.csv     (coverage_gap_n, transit_demand)
  - outputs/w9/{key}_prioritization.csv   (equity_score)
  - data/2020_1_{ENT}_A/*.shp             (AGEB centroids)
  - data/gtfs_{key}/stops.txt             (network-connection seam)
  - cfg.OSM_NETWORK_CACHE                  (osmnx drive graph)

Outputs: outputs/w9/{key}_corridor_scores.csv, {key}_corridor_candidates.geojson,
         {key}_w6_report.md

Usage:
    python src/w9_run_w6.py --city ags     # or tol
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Pure reused functions (none open a DB connection at import).
from src.w6_anchors import (
    N_ANCHORS, N_CORRIDORS, select_anchors_jenks, select_frontier_anchors, cluster_anchors,
)
from src.w6_graph import project_to_6372, snap_to_osm_nodes, corridor_trunk_diameter, anchor_span_km
from src.w6_candidates import compute_n_stops, WALK_BUFFER_M
from src.w5_objective import evaluate_objective
from src.w5_constraints import check_constraints
from src.w5_pareto import pareto_rank
from src.w5_types import RouteCandidate, AgebContext, W5Config
from src.w6_mode import assign_mode, BRT_THRESHOLD, LRT_THRESHOLD
from src.w9_run_tier1 import load_city_config, resolve_paths, _first_existing

OUTPUT_DIR = ROOT / "outputs" / "w9"
CRS = "EPSG:6372"


def load_gap_gdf(cfg, paths) -> gpd.GeoDataFrame:
    """coverage-gap AGEBs with centroid geometry (replaces DB load_gap_agebs)."""
    gap = pd.read_csv(OUTPUT_DIR / f"{cfg.CITY_KEY}_coverage_gap.csv", dtype={"cve_ageb": str})
    for c in ["coverage_gap_n", "transit_demand"]:
        gap[c] = pd.to_numeric(gap[c], errors="coerce").fillna(0.0)
    shp = gpd.read_file(_first_existing(paths["shp"])).to_crs(CRS)
    shp["cve_ageb"] = (shp["CVEGEO"].astype(str).str.strip() if "CVEGEO" in shp.columns
                       else (shp["CVE_ENT"].astype(str).str.zfill(2) + shp["CVE_MUN"].astype(str).str.zfill(3)
                             + shp["CVE_LOC"].astype(str).str.zfill(4) + shp["CVE_AGEB"].astype(str).str.zfill(4)))
    cent = gpd.GeoDataFrame(shp[["cve_ageb"]].copy(), geometry=shp.geometry.centroid, crs=CRS)
    g = cent.merge(gap[["cve_ageb", "coverage_gap_n", "transit_demand", "gap_category"]],
                   on="cve_ageb", how="inner")
    g = g.rename_geometry("geom")
    g["cx"] = g.geometry.x
    g["cy"] = g.geometry.y
    return g.sort_values("coverage_gap_n", ascending=False).reset_index(drop=True)


def load_city_stops(cfg) -> gpd.GeoDataFrame:
    stops = pd.read_csv(ROOT / cfg.GTFS_DIR / "stops.txt", dtype={"stop_id": str}).dropna(
        subset=["stop_lat", "stop_lon"])
    gdf = gpd.GeoDataFrame(stops, geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]),
                           crs="EPSG:4326").to_crs(CRS)
    gdf["cx"], gdf["cy"] = gdf.geometry.x, gdf.geometry.y
    return gdf


def network_connected(gap_gdf, stops_gdf, radius_m=400.0) -> gpd.GeoDataFrame:
    """AGEBs within radius_m of a city GTFS stop (replaces DB network_connected_agebs)."""
    if len(stops_gdf) == 0:
        return gap_gdf.iloc[0:0].copy()
    tree = cKDTree(np.c_[stops_gdf["cx"].values, stops_gdf["cy"].values])
    dist, _ = tree.query(gap_gdf[["cx", "cy"]].values, k=1)
    return gap_gdf[dist <= radius_m].copy().reset_index(drop=True)


def build_candidate(cid, geom, gap_gdf, stops_gdf, cfg_w5, road_km, span_km):
    """RouteCandidate from a corridor line (replaces DB build_route_candidate)."""
    import math
    buf = geom.buffer(WALK_BUFFER_M)
    served = gap_gdf.loc[gap_gdf.geometry.within(buf), "cve_ageb"].tolist()
    if len(served) < 2:
        return None
    connects = bool(stops_gdf.geometry.intersects(buf).any())
    s, e = geom.coords[0], geom.coords[-1]
    straight_km = max(math.hypot(e[0] - s[0], e[1] - s[1]) / 1000.0, 0.001)
    return RouteCandidate(
        candidate_id=cid, served_ageb_ids=served, route_km=road_km,
        n_stops=compute_n_stops(road_km, cfg_w5.min_stop_spacing_m, cfg_w5.max_stop_spacing_m),
        straight_line_km=straight_km, connects_to_existing=connects, anchor_span_km=span_km,
    )


def build_context_map(cfg) -> dict:
    """AgebContext per AGEB (replaces DB load_ageb_context)."""
    gap = pd.read_csv(OUTPUT_DIR / f"{cfg.CITY_KEY}_coverage_gap.csv", dtype={"cve_ageb": str})
    pri = pd.read_csv(OUTPUT_DIR / f"{cfg.CITY_KEY}_prioritization.csv", dtype={"cve_ageb": str})
    m = gap.merge(pri[["cve_ageb", "equity_score"]], on="cve_ageb", how="left")
    out = {}
    for _, r in m.iterrows():
        out[str(r["cve_ageb"])] = AgebContext(
            cvegeo=str(r["cve_ageb"]),
            transit_demand=float(pd.to_numeric(r["transit_demand"], errors="coerce") or 0.0),
            unserved_fraction=float(pd.to_numeric(r["coverage_gap_n"], errors="coerce") or 0.0),
            equity_score=float(pd.to_numeric(r.get("equity_score"), errors="coerce") or 0.0),
        )
    return out


def run_city(city_key: str) -> None:
    import osmnx as ox
    cfg = load_city_config(city_key)
    paths = resolve_paths(cfg)
    w5 = W5Config()
    print("\n" + "=" * 70)
    print(f"W9 W6 -- CORRIDOR GENERATION for {cfg.CITY_NAME.upper()} ({city_key})")
    print("=" * 70)

    gap_gdf = load_gap_gdf(cfg, paths)
    stops_gdf = load_city_stops(cfg)
    print(f"[1] {len(gap_gdf)} AGEBs, {len(stops_gdf)} GTFS stops")

    connected = network_connected(gap_gdf, stops_gdf, 400.0)
    anchors = select_anchors_jenks(gap_gdf, k_classes=5, min_demand=500.0)
    anchors = select_frontier_anchors(anchors, connected, radius_m=400.0)
    print(f"[2] {len(anchors)} frontier anchors (of {len(connected)} network-connected)")
    if len(anchors) == 0:
        raise SystemExit("No frontier anchors -- check GTFS / coverage gap.")
    if len(anchors) > N_ANCHORS:
        anchors = anchors.nlargest(N_ANCHORS, "coverage_gap_n").reset_index(drop=True)
    anchors = cluster_anchors(anchors, n_corridors=N_CORRIDORS)
    print(f"[3] {anchors['corridor_group'].nunique()} corridor groups")

    print("[4] Loading OSM graph + snapping...")
    G = project_to_6372(ox.load_graphml(filepath=str(ROOT / cfg.OSM_NETWORK_CACHE)))
    anchors = anchors.copy()
    anchors["osm_node"] = snap_to_osm_nodes(G, anchors["cx"].tolist(), anchors["cy"].tolist())

    print("[5] Building corridors + evaluating...")
    ctx_map = build_context_map(cfg)
    rows, geoms = [], []
    cands = []
    for gid in sorted(anchors["corridor_group"].unique()):
        nodes = anchors.loc[anchors["corridor_group"] == gid, "osm_node"].tolist()
        geom, road_km = corridor_trunk_diameter(G, nodes)
        if geom is None or road_km <= 0.01:
            continue
        span = anchor_span_km(G, nodes)
        rc = build_candidate(f"W6_G{gid:02d}", geom, gap_gdf, stops_gdf, w5, road_km, span)
        if rc is None:
            continue
        cands.append((rc, geom, gid, span))

    if not cands:
        raise SystemExit("No valid corridors built.")

    objectives = []
    for rc, geom, gid, span in cands:
        ctxs = [ctx_map[a] for a in rc.served_ageb_ids if a in ctx_map]
        obj = evaluate_objective(rc, ctxs, w5)
        cr = check_constraints(rc, ctxs, w5)
        td = sum(c.transit_demand for c in ctxs)
        mode = assign_mode(td, BRT_THRESHOLD, LRT_THRESHOLD)
        objectives.append(obj)
        directness = rc.route_km / span if span else float("nan")
        rows.append({
            "candidate_id": rc.candidate_id, "corridor_group": int(gid),
            "route_km": round(rc.route_km, 3), "n_stops": rc.n_stops,
            "n_served_agebs": len(rc.served_ageb_ids), "total_demand": round(td, 0),
            "directness": round(directness, 3), "connects_to_existing": rc.connects_to_existing,
            "f1_demand_gain": round(obj.f1_demand_gain, 4), "f3_equity": round(obj.f3_equity, 4),
            "total_score": round(obj.total_score, 4), "feasible": bool(cr.feasible),
            "mode_assignment": mode,
        })
        geoms.append(geom)
    ranks = pareto_rank(objectives)
    for r, rk in zip(rows, ranks):
        r["pareto_rank"] = int(rk)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUTPUT_DIR / f"{city_key}_corridor_scores.csv", index=False)
    gdf = gpd.GeoDataFrame(rows, geometry=geoms, crs=CRS).to_crs("EPSG:4326")
    gdf.to_file(OUTPUT_DIR / f"{city_key}_corridor_candidates.geojson", driver="GeoJSON")

    feasible = [r for r in rows if r["feasible"]]
    lines = [f"# W9 W6 Corridor Generation -- {cfg.CITY_NAME}", "",
             f"**{len(rows)} corridors ({len(feasible)} feasible)** via frontier anchors -> "
             f"MST-diameter trunk -> anchor-directness gate (cap 1.8).", "",
             "| ID | Group | km | Stops | Served | Demand | Directness | Conn | Score | Rank | Mode | Feasible |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: x["pareto_rank"]):
        lines.append(f"| {r['candidate_id']} | {r['corridor_group']} | {r['route_km']:.1f} | {r['n_stops']} "
                     f"| {r['n_served_agebs']} | {r['total_demand']:.0f} | {r['directness']:.2f} "
                     f"| {r['connects_to_existing']} | {r['total_score']:.3f} | {r['pareto_rank']} "
                     f"| {r['mode_assignment']} | {r['feasible']} |")
    (OUTPUT_DIR / f"{city_key}_w6_report.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"W9 W6 COMPLETE ({cfg.CITY_NAME}): {len(rows)} corridors, {len(feasible)} feasible")
    print("=" * 70)
    print(pd.DataFrame(rows)[["candidate_id", "route_km", "n_served_agebs", "total_demand",
                              "directness", "feasible", "mode_assignment"]].to_string(index=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True, choices=["tol", "ags"])
    run_city(ap.parse_args().city)


if __name__ == "__main__":
    main()
