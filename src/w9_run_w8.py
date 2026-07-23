"""
W9 W8 -- Validation for a transfer city (CSV-based, no DB)
=========================================================
Transfer analogue of ZMG's `run_w8.py`. Three components, all reusing the PURE
ZMG W8/W3/W6 functions over the city's CSVs + GTFS + AGEB shapefile:

  W8.2 Benchmark      (both cities) -- overlap of feasible W6 corridors vs the
                       existing route network. Low overlap = new coverage.
  W8.3 Before/after   (both cities) -- coverage rate, accessibility Gini, and
                       pop-served/km that the feasible W6 corridors add.
  W8.1 Backtest       (Toluca only) -- hold-out test. NEITHER transfer city has a
                       premium BRT/rail tier to mask the ZMG way (all route_type=3
                       bus). For Toluca we proxy a "trunk" by the routes serving the
                       most MODELED transit demand (frequencies.txt is a uniform-300s
                       placeholder, so real frequency cannot define trunk), mask them,
                       recompute accessibility/gap, re-run the canonical W6 generator,
                       and measure overlap with the masked trunk shapes. Aguascalientes
                       (48 routes, single operator) is too small for a meaningful
                       hold-out and is documented N/A -- consistent with the decision to
                       run the proxy for Toluca only.

Outputs: outputs/w9/{key}_w8_report.md, {key}_w8_benchmark_detail.csv,
         {key}_w8_backtest_per_route.csv (tol only)

Usage:
    python src/w9_run_w8.py --city ags     # benchmark + before/after
    python src/w9_run_w8.py --city tol      # + trunk-proxy backtest (slower)
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import CRS_CANONICAL
# Pure reused functions
from src.w8_backtest import compute_shape_overlap
from src.w8_metrics import gini_coefficient, coverage_rate, pop_served_per_km
from src.w3_accessibility import build_transit_graph, ageb_stop_join, compute_accessibility
from src.w6_anchors import (
    N_ANCHORS, N_CORRIDORS, select_anchors_jenks, select_frontier_anchors, cluster_anchors,
)
from src.w6_graph import project_to_6372, snap_to_osm_nodes, corridor_trunk_diameter, anchor_span_km
from src.w5_constraints import check_constraints
from src.w5_types import W5Config
from src.w9_run_tier1 import load_city_config, resolve_paths, _first_existing
from src.w9_run_w3 import (
    load_stops as w3_load_stops, load_stop_times as w3_load_stop_times,
    load_frequencies as w3_load_frequencies, load_ageb_centroids as w3_load_centroids,
    load_employment as w3_load_employment, compute_gap,
)
from src.w9_run_w6 import (
    load_city_stops, network_connected, build_candidate, build_context_map,
)
from src.w9_run_w7 import load_ageb_centroids, served_agebs_per_route
from src.w7_gtfs_loader import load_gtfs_routes

OUTPUT_DIR = ROOT / "outputs" / "w9"
CRS = CRS_CANONICAL
BUFFER_M = 400.0
TRUNK_STOP_SHARE = 0.12  # mask trunk routes until ~this share of network stops is held out


# ===========================================================================
# Shared loaders
# ===========================================================================

def load_feasible_corridors(city_key: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(OUTPUT_DIR / f"{city_key}_corridor_candidates.geojson").to_crs(CRS)
    if "feasible" in gdf.columns:
        gdf = gdf[gdf["feasible"].astype(bool)].copy()
    if "route_km" not in gdf.columns:
        gdf["route_km"] = gdf.geometry.length / 1000.0
    return gdf.reset_index(drop=True)


def load_route_shapes(gtfs_dir: Path, route_ids=None) -> gpd.GeoDataFrame:
    """One LineString per route from shapes.txt (EPSG:6372). Filter to route_ids if given."""
    trips = pd.read_csv(gtfs_dir / "trips.txt", dtype=str)
    shapes = pd.read_csv(gtfs_dir / "shapes.txt", dtype={"shape_id": str})
    shapes["shape_pt_lat"] = pd.to_numeric(shapes["shape_pt_lat"], errors="coerce")
    shapes["shape_pt_lon"] = pd.to_numeric(shapes["shape_pt_lon"], errors="coerce")
    shapes["shape_pt_sequence"] = pd.to_numeric(shapes["shape_pt_sequence"], errors="coerce")
    if route_ids is not None:
        trips = trips[trips["route_id"].isin(set(route_ids))]
    route_shapes = trips.dropna(subset=["shape_id"]).drop_duplicates("route_id")[["route_id", "shape_id"]]
    recs = []
    for _, r in route_shapes.iterrows():
        pts = shapes[shapes["shape_id"] == r["shape_id"]].sort_values("shape_pt_sequence")
        if len(pts) < 2:
            continue
        recs.append({"route_id": r["route_id"], "shape_id": r["shape_id"],
                     "geometry": LineString(list(zip(pts["shape_pt_lon"], pts["shape_pt_lat"])))})
    if not recs:
        return gpd.GeoDataFrame(columns=["route_id", "shape_id", "geometry"], crs="EPSG:4326")
    return gpd.GeoDataFrame(recs, crs="EPSG:4326").to_crs(CRS)


# ===========================================================================
# W8.2 Benchmark -- feasible W6 corridors vs existing network
# ===========================================================================

def run_benchmark(city_key: str, cfg) -> dict:
    corridors = load_feasible_corridors(city_key)
    routes = load_route_shapes(ROOT / cfg.GTFS_DIR)
    print(f"  [OK] {len(corridors)} feasible corridors vs {len(routes)} existing routes")
    if len(corridors) == 0 or len(routes) == 0:
        return {"n_corridors": len(corridors), "n_routes": len(routes),
                "mean_overlap": 0.0, "total_km": float(corridors["route_km"].sum())
                if len(corridors) else 0.0, "detail": pd.DataFrame()}
    recs = []
    for _, c in corridors.iterrows():
        best_ov, best_r = 0.0, None
        for _, r in routes.iterrows():
            ov = compute_shape_overlap(c.geometry, r.geometry, BUFFER_M)
            if ov > best_ov:
                best_ov, best_r = ov, r["route_id"]
        recs.append({"candidate_id": c.get("candidate_id", "?"),
                     "best_matching_route": best_r, "max_overlap_fraction": best_ov,
                     "route_km": float(c["route_km"])})
    detail = pd.DataFrame(recs)
    return {"n_corridors": len(corridors), "n_routes": len(routes),
            "mean_overlap": float(detail["max_overlap_fraction"].mean()),
            "total_km": float(corridors["route_km"].sum()), "detail": detail}


# ===========================================================================
# W8.3 Before/after metrics
# ===========================================================================

def run_metrics(city_key: str, cfg, paths) -> dict:
    # AGEB study universe with population + accessibility
    gap = pd.read_csv(OUTPUT_DIR / f"{city_key}_coverage_gap.csv", dtype={"cve_ageb": str})
    npp = pd.read_csv(OUTPUT_DIR / f"{city_key}_nppv_features.csv", dtype={"cve_ageb": str})
    cent = load_ageb_centroids(paths)
    cent = cent[cent["cve_ageb"].isin(set(gap["cve_ageb"]))].reset_index(drop=True)
    ageb = cent.merge(gap[["cve_ageb", "accessibility_score"]], on="cve_ageb", how="left") \
               .merge(npp[["cve_ageb", "pe_population"]], on="cve_ageb", how="left")
    ageb["accessibility_score"] = pd.to_numeric(ageb["accessibility_score"], errors="coerce").fillna(0.0)
    ageb["pe_population"] = pd.to_numeric(ageb["pe_population"], errors="coerce").fillna(0.0)
    ageb_gdf = gpd.GeoDataFrame(ageb, geometry="geometry", crs=CRS)

    # "Before" service = existing GTFS stop buffers
    stops = load_city_stops(cfg)
    before_svc = gpd.GeoDataFrame(geometry=stops.geometry.buffer(BUFFER_M), crs=CRS)

    corridors = load_feasible_corridors(city_key)
    w6_union = corridors.geometry.union_all().buffer(BUFFER_M) if len(corridors) else None
    combined = (before_svc.geometry.union_all().union(w6_union) if w6_union is not None
                else before_svc.geometry.union_all())
    combined_gdf = gpd.GeoDataFrame(geometry=[combined], crs=CRS)

    rate_before = coverage_rate(ageb_gdf, before_svc)
    rate_after = coverage_rate(ageb_gdf, combined_gdf)
    gini_before = gini_coefficient(ageb_gdf["accessibility_score"].values)

    served = ageb_gdf.loc[ageb_gdf["accessibility_score"] > 0, "accessibility_score"]
    mean_served = float(served.mean()) if len(served) else 0.0
    acc_after = ageb_gdf["accessibility_score"].copy()
    n_newly, pop_newly = 0, 0.0
    if w6_union is not None:
        newly = (ageb_gdf["accessibility_score"] == 0) & ageb_gdf.geometry.within(w6_union)
        acc_after.loc[newly] = mean_served
        n_newly = int(newly.sum())
        pop_newly = float(ageb_gdf.loc[newly, "pe_population"].sum())
    gini_after = gini_coefficient(acc_after.values)
    pop_km = pop_served_per_km(ageb_gdf, corridors, BUFFER_M) if len(corridors) else 0.0

    return {
        "coverage_rate_before": rate_before, "coverage_rate_after": rate_after,
        "gini_before": gini_before, "gini_after": gini_after,
        "pop_served_per_km_w6": pop_km, "n_ageb_newly_served": n_newly,
        "total_population_newly_served": pop_newly,
        "w6_total_km": float(corridors["route_km"].sum()) if len(corridors) else 0.0,
    }


# ===========================================================================
# W8.1 Backtest (Toluca only) -- demand-trunk proxy hold-out
# ===========================================================================

def select_trunk_routes(city_key, cfg, paths, gtfs_dir) -> tuple:
    """Trunk = existing routes serving the most modeled transit demand, accumulated
    until ~TRUNK_STOP_SHARE of network stops are held out. Returns (route_ids, excluded_stop_ids,
    n_total_stops, served_demand_series)."""
    routes_gdf = load_gtfs_routes(data_dir=gtfs_dir).reset_index(drop=True)
    ctx_map = build_context_map(cfg)
    cent = load_ageb_centroids(paths)
    cent = cent[cent["cve_ageb"].isin(ctx_map)].reset_index(drop=True)
    served_map = served_agebs_per_route(routes_gdf, cent)
    demand = {a: ctx_map[a].transit_demand for a in ctx_map}
    served_demand = pd.Series({rid: sum(demand.get(a, 0.0) for a in ags)
                               for rid, ags in served_map.items()}).sort_values(ascending=False)

    trips = pd.read_csv(gtfs_dir / "trips.txt", dtype=str)
    st = pd.read_csv(gtfs_dir / "stop_times.txt", dtype={"trip_id": str, "stop_id": str},
                     usecols=["trip_id", "stop_id"])
    route_to_trips = trips.groupby("route_id")["trip_id"].apply(set).to_dict()
    n_total_stops = st["stop_id"].nunique()

    chosen, excluded = [], set()
    for rid in served_demand.index:
        chosen.append(rid)
        tids = route_to_trips.get(rid, set())
        excluded |= set(st.loc[st["trip_id"].isin(tids), "stop_id"])
        if len(excluded) >= TRUNK_STOP_SHARE * n_total_stops:
            break
    return chosen, excluded, n_total_stops, served_demand


def run_backtest_tol(city_key, cfg, paths) -> dict:
    import osmnx as ox
    gtfs_dir = ROOT / cfg.GTFS_DIR

    print("[BT] Selecting demand-trunk routes to mask...")
    trunk_ids, excluded, n_total, served_demand = select_trunk_routes(city_key, cfg, paths, gtfs_dir)
    print(f"  [OK] {len(trunk_ids)} trunk routes masked -> {len(excluded)} stops "
          f"({len(excluded)/n_total:.1%} of {n_total})")

    print("[BT] Recomputing masked accessibility (Dijkstra)...")
    stops = w3_load_stops(gtfs_dir)
    stops = stops[~stops["stop_id"].isin(excluded)].reset_index(drop=True)
    stimes = w3_load_stop_times(gtfs_dir)
    stimes = stimes[~stimes["stop_id"].isin(excluded)].copy()
    keep_trips = stimes.groupby("trip_id")["stop_id"].count()
    stimes = stimes[stimes["trip_id"].isin(set(keep_trips[keep_trips >= 2].index))].copy()
    headway = w3_load_frequencies(gtfs_dir)
    G = build_transit_graph(stimes, headway)

    demand_df = pd.read_csv(OUTPUT_DIR / f"{city_key}_demand_surface.csv", dtype={"cve_ageb": str})
    demand_df["transit_demand"] = pd.to_numeric(demand_df["transit_demand"], errors="coerce").fillna(0.0)
    agebs = w3_load_centroids(_first_existing(paths["shp"]))
    agebs = agebs[agebs["cve_ageb"].isin(set(demand_df["cve_ageb"]))].reset_index(drop=True)
    emp = w3_load_employment(cfg, paths, agebs)
    ageb_stop = ageb_stop_join(agebs, stops)
    acc = compute_accessibility(agebs, stops, G, ageb_stop, emp)

    print("[BT] Recomputing masked coverage gap...")
    gap = compute_gap(demand_df[["cve_ageb", "transit_demand"]],
                      acc[["cve_ageb", "accessibility_score"]])
    # gap_gdf for the W6 generator (centroid geometry + cx/cy)
    gap_gdf = agebs.merge(
        gap[["cve_ageb", "coverage_gap_n", "transit_demand", "gap_category"]],
        on="cve_ageb", how="inner")
    gap_gdf = gpd.GeoDataFrame(gap_gdf, geometry="geom", crs=CRS)
    for c in ["coverage_gap_n", "transit_demand"]:
        gap_gdf[c] = pd.to_numeric(gap_gdf[c], errors="coerce").fillna(0.0)
    gap_gdf["cx"], gap_gdf["cy"] = gap_gdf.geometry.x, gap_gdf.geometry.y
    gap_gdf = gap_gdf.sort_values("coverage_gap_n", ascending=False).reset_index(drop=True)

    print("[BT] Re-running W6 generator on masked surface...")
    w5 = W5Config()
    masked_stops = load_city_stops(cfg)
    masked_stops = masked_stops[~masked_stops["stop_id"].isin(excluded)].reset_index(drop=True)
    connected = network_connected(gap_gdf, masked_stops, 400.0)
    jenks = select_anchors_jenks(gap_gdf, k_classes=5, min_demand=500.0)
    anchors = select_frontier_anchors(jenks, connected, radius_m=400.0)
    print(f"  [OK] masked seam: {len(connected)} network-connected, {len(jenks)} Jenks high-gap, "
          f"{len(anchors)} frontier anchors (non-masked baseline: 14)")
    empty = {"n_trunk_routes": len(trunk_ids), "n_excluded_stops": len(excluded),
             "stop_share": len(excluded) / n_total, "n_anchors": len(anchors),
             "n_built": 0, "n_reproposed": 0, "mean_overlap": None, "per_route": [],
             "seam_collapse": True}
    if len(anchors) == 0:
        print("  [WARN] No frontier anchors after masking (seam collapse).")
        return empty
    if len(anchors) > N_ANCHORS:
        anchors = anchors.nlargest(N_ANCHORS, "coverage_gap_n").reset_index(drop=True)
    anchors = cluster_anchors(anchors, n_corridors=N_CORRIDORS)
    grp_sizes = anchors.groupby("corridor_group").size().to_dict()
    print(f"  [OK] {len(anchors)} anchors in {len(grp_sizes)} groups; sizes {grp_sizes}")

    G_road = project_to_6372(ox.load_graphml(filepath=str(ROOT / cfg.OSM_NETWORK_CACHE)))
    anchors = anchors.copy()
    anchors["osm_node"] = snap_to_osm_nodes(G_road, anchors["cx"].tolist(), anchors["cy"].tolist())
    ctx_map = build_context_map(cfg)

    reproposed, n_built = [], 0
    for gid in sorted(anchors["corridor_group"].unique()):
        nodes = anchors.loc[anchors["corridor_group"] == gid, "osm_node"].tolist()
        geom, road_km = corridor_trunk_diameter(G_road, nodes)
        if geom is None or road_km <= 0.01:
            continue
        n_built += 1
        span = anchor_span_km(G_road, nodes)
        rc = build_candidate(f"BT_G{gid:02d}", geom, gap_gdf, masked_stops, w5, road_km, span)
        if rc is None:
            continue
        ctxs = [ctx_map[a] for a in rc.served_ageb_ids if a in ctx_map]
        if check_constraints(rc, ctxs, w5).feasible:
            reproposed.append(geom)
    print(f"  [OK] {n_built} corridors built, {len(reproposed)} feasible")

    trunk_shapes = load_route_shapes(gtfs_dir, route_ids=trunk_ids)
    if not reproposed or len(trunk_shapes) == 0:
        empty.update({"n_anchors": len(anchors), "n_built": n_built,
                      "n_reproposed": len(reproposed)})
        return empty
    per_route = [{"route_id": r["route_id"],
                  "max_overlap_fraction": max(compute_shape_overlap(r.geometry, c, BUFFER_M)
                                              for c in reproposed)}
                 for _, r in trunk_shapes.iterrows()]
    mean_ov = float(np.mean([p["max_overlap_fraction"] for p in per_route]))
    print(f"  [OK] Mean trunk-recovery overlap: {mean_ov:.3f}")
    return {"n_trunk_routes": len(trunk_ids), "n_excluded_stops": len(excluded),
            "stop_share": len(excluded) / n_total, "n_anchors": len(anchors),
            "n_built": n_built, "n_reproposed": len(reproposed),
            "mean_overlap": mean_ov, "per_route": per_route}


# ===========================================================================
# Report
# ===========================================================================

def write_report(city_key, cfg, bench, metrics, backtest) -> None:
    L = [f"# W9 W8 Validation -- {cfg.CITY_NAME}", "",
         "Transfer analogue of ZMG's `run_w8.py`, CSV-based.", ""]

    L += ["## W8.1 -- Backtest (hold-out)", ""]
    if backtest is None:
        L += [f"**N/A for {cfg.CITY_NAME}.** No premium BRT/rail tier exists to hold out "
              "(all routes are route_type=3 bus), and the network is too small "
              f"({cfg.CITY_NAME} = 48 routes, single operator) for a meaningful demand-trunk "
              "proxy. Backtest is run for Toluca only (see that report).", ""]
    elif backtest.get("mean_overlap") is None:
        L += [f"**Demand-trunk proxy** (frequencies.txt is a uniform-300s placeholder, so "
              "'trunk' = routes serving the most modeled demand).",
              f"- Trunk routes masked: {backtest['n_trunk_routes']}  "
              f"({backtest['n_excluded_stops']:,} stops, {backtest['stop_share']:.1%} of network)",
              f"- Frontier anchors after masking: {backtest['n_anchors']} "
              f"(non-masked baseline: 14)  |  corridors built {backtest['n_built']}, "
              f"feasible {backtest['n_reproposed']}",
              "",
              "**Degenerate outcome -- seam collapse.** The hold-out re-proposes 0 corridors. "
              "The mechanism is intrinsic to a bus-only network: unlike ZMG's premium rail "
              "(a separable overlay redundant with parallel buses, so masking it leaves the "
              "served/unserved frontier intact), the demand-trunk here *is* the local bus "
              "service. Masking its stops erases the very served/unserved seam the frontier "
              "generator anchors on, so few or no frontier anchors survive and no multi-anchor "
              "corridor can be built. This confirms the ZMG-documented precondition: the "
              "mask-and-reconstruct backtest needs a premium tier redundant with underlying "
              "coverage -- a condition neither transfer city meets. The benchmark (W8.2) and "
              "before/after metrics (W8.3) are the operative validation for these cities.", ""]
    else:
        L += [f"**Demand-trunk proxy** (frequencies.txt is a uniform-300s placeholder, so "
              "'trunk' = routes serving the most modeled demand).",
              f"- Trunk routes masked: {backtest['n_trunk_routes']}  "
              f"({backtest['n_excluded_stops']:,} stops, {backtest['stop_share']:.1%} of network)",
              f"- Anchors after masking: {backtest['n_anchors']}  |  "
              f"corridors built {backtest['n_built']}, feasible {backtest['n_reproposed']}",
              f"- **Mean trunk-recovery overlap: {backtest['mean_overlap']:.1%}**",
              "", "| Trunk route | Max overlap |", "|---|---|"]
        for p in sorted(backtest["per_route"], key=lambda x: -x["max_overlap_fraction"]):
            L.append(f"| {p['route_id']} | {p['max_overlap_fraction']:.1%} |")
        L += ["", "*(Low overlap = the generator does not reconstruct the busiest existing "
              "corridors, consistent with the ZMG rail finding.)*", ""]

    if bench["mean_overlap"] >= 0.40:
        bench_note = ("*(Substantial overlap: in this already well-served network (~80% baseline "
                      "coverage) W6 largely re-identifies existing high-demand corridors rather "
                      "than adding new coverage -- revealed-preference corroboration.)*")
    else:
        bench_note = ("*(Low overlap: W6 finds new un-served corridors rather than replicating "
                      "existing lines.)*")
    L += ["## W8.2 -- Benchmark: feasible W6 corridors vs existing network", "",
          f"- Feasible W6 corridors: {bench['n_corridors']}  vs  {bench['n_routes']} existing routes",
          f"- **Mean W6 overlap with existing routes: {bench['mean_overlap']:.1%}**",
          f"- Total W6 km: {bench['total_km']:.1f}",
          "", bench_note, ""]
    if not bench["detail"].empty:
        L += ["| W6 corridor | Best-matching route | Overlap |", "|---|---|---|"]
        for _, r in bench["detail"].iterrows():
            L.append(f"| {r['candidate_id']} | {r['best_matching_route']} | "
                     f"{r['max_overlap_fraction']:.1%} |")

    m = metrics
    L += ["", "## W8.3 -- Before/after metrics", "",
          "| Metric | Before W6 | After W6 | Delta |", "|---|---|---|---|",
          f"| Coverage rate | {m['coverage_rate_before']:.1%} | {m['coverage_rate_after']:.1%} | "
          f"+{m['coverage_rate_after'] - m['coverage_rate_before']:.1%} |",
          f"| Accessibility Gini | {m['gini_before']:.4f} | {m['gini_after']:.4f} | "
          f"{m['gini_after'] - m['gini_before']:+.4f} |",
          f"| Pop-served / route-km | -- | {m['pop_served_per_km_w6']:,.0f} | -- |",
          f"| AGEBs newly served | -- | {m['n_ageb_newly_served']:,} | -- |",
          f"| Population newly served | -- | {m['total_population_newly_served']:,.0f} | -- |",
          f"| Total W6 route km | -- | {m['w6_total_km']:.1f} | -- |", ""]

    (OUTPUT_DIR / f"{city_key}_w8_report.md").write_text("\n".join(L), encoding="utf-8")


def run_city(city_key: str) -> None:
    cfg = load_city_config(city_key)
    paths = resolve_paths(cfg)
    print("\n" + "=" * 70)
    print(f"W9 W8 -- VALIDATION for {cfg.CITY_NAME.upper()} ({city_key})")
    print("=" * 70)

    print("[W8.2] Benchmark: W6 corridors vs existing network...")
    bench = run_benchmark(city_key, cfg)

    print("[W8.3] Before/after metrics...")
    metrics = run_metrics(city_key, cfg, paths)

    backtest = None
    if city_key == "tol":
        print("[W8.1] Backtest: demand-trunk proxy hold-out (Toluca)...")
        backtest = run_backtest_tol(city_key, cfg, paths)

    print("[W8] Writing outputs...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not bench["detail"].empty:
        bench["detail"].to_csv(OUTPUT_DIR / f"{city_key}_w8_benchmark_detail.csv", index=False)
    if backtest and backtest.get("per_route"):
        pd.DataFrame(backtest["per_route"]).to_csv(
            OUTPUT_DIR / f"{city_key}_w8_backtest_per_route.csv", index=False)
    write_report(city_key, cfg, bench, metrics, backtest)

    print("\n" + "=" * 70)
    print(f"W9 W8 COMPLETE ({cfg.CITY_NAME})")
    print(f"  Benchmark mean overlap: {bench['mean_overlap']:.1%}  ({bench['n_corridors']} corridors)")
    print(f"  Coverage: {metrics['coverage_rate_before']:.1%} -> {metrics['coverage_rate_after']:.1%}  |  "
          f"Gini: {metrics['gini_before']:.4f} -> {metrics['gini_after']:.4f}")
    print(f"  Pop newly served: {metrics['total_population_newly_served']:,.0f} "
          f"({metrics['n_ageb_newly_served']} AGEBs)")
    if backtest and backtest.get("mean_overlap") is not None:
        print(f"  Backtest trunk-recovery overlap: {backtest['mean_overlap']:.1%}")
    print("=" * 70)


def main() -> None:
    ap = argparse.ArgumentParser(description="W9 W8 validation (city-parameterized)")
    ap.add_argument("--city", required=True, choices=["tol", "ags"])
    run_city(ap.parse_args().city)


if __name__ == "__main__":
    main()
