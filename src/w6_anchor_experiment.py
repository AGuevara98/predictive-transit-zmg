"""
W6 Anchor-Level Network Connection -- 3-way comparison harness.

Runs corridor generation under three anchor modes and scores each on the W8
Question-B merit axes (need / non-redundancy / demand-per-km + feasibility):

  baseline  -- Jenks high-gap anchors + KMeans + near/far bare-stop hub injection
               (the incumbent committed logic).
  two_tier  -- baseline anchors + one nearest network-connected AGEB per group as a
               role="network" tie-in (no bare-stop hubs; hub fallback for out-of-range
               groups).
  frontier  -- high-gap anchor pool restricted to the served/unserved seam
               (within 400m of a connected AGEB) before clustering; no hubs.

READ-ONLY against the DB: never writes features.route_candidates. Outputs go only to
outputs/w6_experiment/.

Run (WSL, venv active): python src/w6_anchor_experiment.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geopandas as gpd
import pandas as pd
from scipy.spatial import cKDTree
from sqlalchemy import create_engine

from config import PG_URI
from src.w5_constraints import check_constraints
from src.w5_objective import evaluate_objective, load_ageb_context
from src.w5_types import W5Config
from src.w6_anchors import (
    N_ANCHORS, N_CORRIDORS, add_network_anchors, cluster_anchors, load_gap_agebs,
    load_gtfs_stops, network_connected_agebs, select_anchors_jenks,
    select_frontier_anchors, select_group_hubs,
)
from src.w6_candidates import build_route_candidate
from src.w6_graph import (
    build_corridor_path, load_or_download_osm, project_to_6372, snap_to_osm_nodes,
)
from src.w6_mode import BRT_THRESHOLD, LRT_THRESHOLD, assign_mode
from src.w8_corridor_merit import build_merit_baselines, score_corridor

MODES = ["baseline", "two_tier", "frontier"]
OUT = Path("outputs/w6_experiment")
CONNECT_M = 400.0


def _hub_terminals(anchors_sub, stops_df, G_proj):
    """Return {group_id: [near_node, far_node]} for the given anchor subset."""
    hubs = select_group_hubs(anchors_sub, stops_df)
    if len(hubs) == 0:
        return {}
    gids = [int(r.corridor_group) for r in hubs.itertuples(index=False)]
    near = snap_to_osm_nodes(G_proj, [r.hub_cx for r in hubs.itertuples(index=False)],
                             [r.hub_cy for r in hubs.itertuples(index=False)])
    far = snap_to_osm_nodes(G_proj, [r.far_hub_cx for r in hubs.itertuples(index=False)],
                            [r.far_hub_cy for r in hubs.itertuples(index=False)])
    return {g: [n, f] for g, n, f in zip(gids, near, far)}


def build_anchor_terminals(mode, gap_gdf, connected_gdf, stops_df, G_proj):
    """Return (terminals_by_group: {gid: [osm_nodes]}, anchors_gdf) for a mode."""
    anchors = select_anchors_jenks(gap_gdf, k_classes=5, min_demand=500.0)
    if mode == "frontier":
        anchors = select_frontier_anchors(anchors, connected_gdf, radius_m=CONNECT_M)
    if len(anchors) > N_ANCHORS:
        anchors = anchors.nlargest(N_ANCHORS, "coverage_gap_n").reset_index(drop=True)
    if len(anchors) == 0:
        return {}, anchors
    anchors = cluster_anchors(anchors, n_corridors=N_CORRIDORS)
    anchors["role"] = "demand"

    hub_groups = set()
    if mode == "baseline":
        hub_groups = set(int(g) for g in anchors["corridor_group"].unique())
    elif mode == "two_tier":
        anchors, fallback = add_network_anchors(anchors, connected_gdf)
        hub_groups = fallback

    anchors = anchors.copy()
    anchors["osm_node"] = snap_to_osm_nodes(G_proj, anchors["cx"].tolist(),
                                            anchors["cy"].tolist())

    hub_osm = {}
    if hub_groups:
        sub = anchors[anchors["corridor_group"].isin(hub_groups)]
        hub_osm = _hub_terminals(sub, stops_df, G_proj)

    terminals = {}
    for gid, grp in anchors.groupby("corridor_group"):
        nodes = grp["osm_node"].tolist()
        if int(gid) in hub_osm:
            nodes = nodes + hub_osm[int(gid)]
        terminals[int(gid)] = nodes
    return terminals, anchors


def generate_mode(mode, engine, G_proj, gap_gdf, connected_gdf, stops_df, stop_tree,
                  cfg, baselines):
    print(f"\n[{mode}] generating corridors...")
    terminals, _ = build_anchor_terminals(mode, gap_gdf, connected_gdf, stops_df, G_proj)
    rows, geoms = [], []
    for gid in sorted(terminals):
        geom, route_km = build_corridor_path(G_proj, terminals[gid])
        if geom is None or route_km <= 0.01:
            continue
        cid = f"{mode}_G{gid:02d}"
        rc = build_route_candidate(cid, geom, engine, config=cfg, route_km_override=route_km)
        if rc is None:
            continue
        ctxs = load_ageb_context(rc.served_ageb_ids, engine)
        obj = evaluate_objective(rc, ctxs, cfg)
        cr = check_constraints(rc, ctxs, cfg)
        td = sum(c.transit_demand for c in ctxs)
        merit = score_corridor(geom, route_km, td, baselines)
        ep = stop_tree.query([geom.coords[0], geom.coords[-1]], k=1)[0]
        rows.append({
            "candidate_id": cid, "corridor_group": gid,
            "route_km": float(route_km), "n_served_agebs": len(rc.served_ageb_ids),
            "total_demand": float(td), "f1_demand_gain": float(obj.f1_demand_gain),
            "f3_equity": float(obj.f3_equity), "total_score": float(obj.total_score),
            "feasible": bool(cr.feasible),
            "mode_assignment": assign_mode(td, BRT_THRESHOLD, LRT_THRESHOLD),
            "endpoints_connected": bool((ep <= CONNECT_M).all()),
            "hi_share": merit["hi_share"], "best_jaccard": merit["best_jaccard"],
            "redundant": merit["redundant"], "dpk_pct": merit["dpk_pct"],
            "merit_passed": merit["passed"],
        })
        geoms.append(geom)
        print(f"  {cid}: {route_km:.1f}km served={len(rc.served_ageb_ids)} "
              f"demand={td:.0f} feasible={cr.feasible} "
              f"endpoints_connected={rows[-1]['endpoints_connected']} "
              f"merit_pass={merit['passed']}")

    mode_dir = OUT / mode
    mode_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(mode_dir / "corridor_scores.csv", index=False)
    if geoms:
        gdf = gpd.GeoDataFrame(rows, geometry=geoms, crs="EPSG:6372").to_crs("EPSG:4326")
        gdf.to_file(mode_dir / "corridor_candidates.geojson", driver="GeoJSON")
    return rows


def write_comparison(all_rows, baselines):
    lines = [
        "# W6 Anchor Mode Comparison (baseline / two_tier / frontier)",
        "",
        f"Metro High-gap baseline share: {baselines.metro_hi_share:.1%}. "
        "demand/km pass = >= 50th pct of existing routes; non-redundant = best Jaccard < 0.60.",
        "",
        "| Mode | Corridors | Feasible | Endpoints connected | Mean High-gap share | "
        "All non-redundant | Mean demand/km pct | Merit-pass |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for mode in MODES:
        rows = all_rows[mode]
        feas = [r for r in rows if r["feasible"]]
        n_conn = sum(1 for r in feas if r["endpoints_connected"])
        mean_hi = (sum(r["hi_share"] for r in feas) / len(feas)) if feas else float("nan")
        all_uniq = all(not r["redundant"] for r in feas) if feas else True
        mean_pct = (sum(r["dpk_pct"] for r in feas) / len(feas)) if feas else float("nan")
        n_pass = sum(1 for r in feas if r["merit_passed"])
        conn_txt = f"{n_conn}/{len(feas)}" if feas else "0/0"
        lines.append(
            f"| {mode} | {len(rows)} | {len(feas)} | {conn_txt} | {mean_hi:.1%} | "
            f"{all_uniq} | {mean_pct:.0f} | {n_pass}/{len(feas)} |"
        )
    lines += [
        "",
        "## Per-corridor detail",
        "",
        "| Mode | ID | km | Served | Demand | Feasible | Endpts conn | High-gap | "
        "Jaccard | demand/km pct | Merit pass |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for mode in MODES:
        for r in all_rows[mode]:
            lines.append(
                f"| {mode} | {r['candidate_id']} | {r['route_km']:.1f} | "
                f"{r['n_served_agebs']} | {r['total_demand']:.0f} | {r['feasible']} | "
                f"{r['endpoints_connected']} | {r['hi_share']:.1%} | "
                f"{r['best_jaccard']:.2f} | {r['dpk_pct']:.0f} | {r['merit_passed']} |"
            )
    lines += [
        "",
        "## Notes",
        "",
        "- baseline injects bare GTFS stops as MST terminals (routing-level connection).",
        "- two_tier / frontier inject a supply-side signal into anchor SELECTION; the",
        "  'Mean High-gap share' and 'demand/km pct' columns show how much corridor merit",
        "  each buys relative to the pure-demand baseline. Weigh realism vs the clean",
        "  'generate purely from the demand gap' story when choosing a mode.",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[OK] comparison written: {OUT / 'comparison.md'}")


def main():
    engine = create_engine(PG_URI)
    try:
        cfg = W5Config()
        print("[Load] merit baselines + coverage gap + connected AGEBs + stops...")
        baselines = build_merit_baselines(engine)
        gap_gdf = load_gap_agebs(engine)
        connected_gdf = network_connected_agebs(engine, radius_m=CONNECT_M)
        stops_df = load_gtfs_stops(engine)
        stop_tree = cKDTree(stops_df[["cx", "cy"]].values)
        print(f"  gap AGEBs={len(gap_gdf)}, connected AGEBs={len(connected_gdf)}, "
              f"stops={len(stops_df)}")

        G_proj = project_to_6372(load_or_download_osm())
        print(f"  OSM graph: {G_proj.number_of_nodes()} nodes")

        all_rows = {}
        for mode in MODES:
            all_rows[mode] = generate_mode(
                mode, engine, G_proj, gap_gdf, connected_gdf, stops_df, stop_tree,
                cfg, baselines,
            )
        write_comparison(all_rows, baselines)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
