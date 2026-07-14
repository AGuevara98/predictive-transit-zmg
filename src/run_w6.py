"""
W6: New Corridor Generation -- Orchestrator
===========================================
Generates demand-driven transit corridor candidates for ZMG.

Pipeline:
  1. Run DB migration 006_w6_tables.sql
  2. Load coverage-gap surface from DB
  3. Select anchor AGEBs via Jenks natural breaks
  4. Cluster anchors into N_CORRIDORS spatial groups
  5. Load / download OSM drive graph (cached to data/osm_zmg_drive.graphml)
  6. Snap anchor centroids to OSM nodes; build one MST path per cluster
  7. Construct RouteCandidate for each valid corridor
  8. Evaluate with W5 objective + constraint checker
  9. Pareto-rank feasible candidates
 10. Assign BRT / Local Bus mode by demand volume
 11. Write results to features.route_candidates (DB) and outputs/w6/

Usage:
    python src/run_w6.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import LineString
from sqlalchemy import create_engine, text

from config import PG_URI
from src.w5_constraints import check_constraints
from src.w5_objective import evaluate_objective, load_ageb_context
from src.w5_pareto import pareto_rank
from src.w5_types import W5Config
from src.w6_anchors import (
    N_ANCHORS,
    N_CORRIDORS,
    cluster_anchors,
    load_gap_agebs,
    select_anchors_jenks,
)
from src.w6_candidates import build_route_candidate
from src.w6_graph import build_corridor_path, load_or_download_osm, project_to_6372, snap_to_osm_nodes
from src.w6_mode import BRT_THRESHOLD, LRT_THRESHOLD, assign_mode

OUTPUT_DIR = Path("outputs/w6")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MIGRATION_PATH = Path("db_setup/migrations/006_w6_tables.sql")


def run_migration(engine) -> None:
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    print("  [OK] Migration 006_w6_tables.sql applied")


def write_to_db(engine, rows: list) -> None:
    if not rows:
        return
    insert_sql = text("""
        INSERT INTO features.route_candidates (
            candidate_id, corridor_group, route_km, n_stops, straight_line_km,
            connects_to_existing, n_served_agebs, total_demand,
            f1_demand_gain, f2_route_km, f3_equity,
            composite_score, total_score, pareto_rank, feasible,
            mode_assignment, geom
        ) VALUES (
            :candidate_id, :corridor_group, :route_km, :n_stops, :straight_line_km,
            :connects_to_existing, :n_served_agebs, :total_demand,
            :f1_demand_gain, :f2_route_km, :f3_equity,
            :composite_score, :total_score, :pareto_rank, :feasible,
            :mode_assignment, ST_GeomFromText(:geom_wkt, 6372)
        )
    """)
    with engine.begin() as conn:
        for row in rows:
            conn.execute(insert_sql, row)
    print(f"  [OK] {len(rows)} corridors written to features.route_candidates")


def write_geojson(rows: list, geoms: list) -> None:
    if not rows:
        return
    records = [{k: v for k, v in r.items() if k != "geom_wkt"} for r in rows]
    gdf = gpd.GeoDataFrame(records, geometry=geoms, crs="EPSG:6372")
    gdf = gdf.to_crs("EPSG:4326")
    out = OUTPUT_DIR / "corridor_candidates.geojson"
    gdf.to_file(out, driver="GeoJSON")
    print(f"  [OK] GeoJSON written: {out}")


def write_scores_csv(rows: list) -> None:
    cols = [
        "candidate_id", "corridor_group", "route_km", "n_stops",
        "connects_to_existing", "n_served_agebs", "total_demand",
        "f1_demand_gain", "f3_equity", "composite_score",
        "total_score", "pareto_rank", "feasible", "mode_assignment",
    ]
    df = pd.DataFrame([{c: r[c] for c in cols if c in r} for r in rows])
    out = OUTPUT_DIR / "corridor_scores.csv"
    df.to_csv(out, index=False)
    print(f"  [OK] Scores CSV written: {out}")


def write_pareto_chart(rows: list) -> None:
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(9, 6))
    cmap = plt.cm.RdYlGn
    max_rank = max(r["pareto_rank"] for r in rows) if rows else 1
    for row in rows:
        color = cmap(1.0 - (row["pareto_rank"] - 1) / max(max_rank, 1))
        ax.scatter(row["f2_route_km"], row["f1_demand_gain"], c=[color], s=200, zorder=3)
        ax.annotate(
            f"{row['candidate_id']} ({row['mode_assignment']}, rank {row['pareto_rank']})",
            (row["f2_route_km"], row["f1_demand_gain"]),
            textcoords="offset points", xytext=(8, 4), fontsize=8,
        )
    ax.set_xlabel("f2: Route length (km) -- minimize")
    ax.set_ylabel("f1: Demand-weighted accessibility gain -- maximize")
    ax.set_title("W6 Corridor Candidates: Pareto Space (f1 vs f2)")
    ax.grid(True, alpha=0.3)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=1, vmax=max_rank))
    fig.colorbar(sm, ax=ax, label="Pareto rank (1=best)")
    fig.tight_layout()
    out = OUTPUT_DIR / "pareto_front.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  [OK] Pareto chart written: {out}")


def write_report(rows: list) -> None:
    feasible = [r for r in rows if r["feasible"]]
    infeasible = [r for r in rows if not r["feasible"]]
    lines = [
        "# W6 New Corridor Generation -- Report",
        "",
        f"**Generated corridors:** {len(rows)} total ({len(feasible)} feasible, {len(infeasible)} infeasible)",
        "",
        "## Methodology",
        "",
        "1. **Anchor selection:** Jenks natural breaks (k=5) on coverage_gap_n; top class only; min 500 trips/day demand.",
        f"2. **Spatial clustering:** KMeans (k={N_CORRIDORS}) on EPSG:6372 centroids to form corridor groups.",
        "3. **Path generation:** MST-based Steiner approximation on ZMG OSM drive graph (osmnx 2.1.0).",
        "4. **Evaluation:** W5 multi-objective function (f1 demand gain, f2 route cost, f3 equity).",
        "5. **Mode assignment:** Light Rail/Metro if total served demand >= 75,000 trips/day; "
        "BRT if >= 15,000; Local Bus otherwise.",
        "",
        "## Candidate Summary",
        "",
        "| ID | Group | km | Stops | Connected | Served AGEBs | Total Demand | f1 | f3 | Score | Rank | Mode | Feasible |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda x: x["pareto_rank"]):
        lines.append(
            f"| {r['candidate_id']} | {r['corridor_group']} | {r['route_km']:.1f}"
            f" | {r['n_stops']} | {r['connects_to_existing']}"
            f" | {r['n_served_agebs']} | {r['total_demand']:.0f}"
            f" | {r['f1_demand_gain']:.3f} | {r['f3_equity']:.3f}"
            f" | {r['total_score']:.3f} | {r['pareto_rank']}"
            f" | {r['mode_assignment']} | {r['feasible']} |"
        )
    lines += [
        "",
        "## Mode Assignment Sensitivity",
        "",
        "BRT threshold fixed at 15,000 trips/day; varying the Light Rail/Metro threshold:",
        "",
        "| LRT Threshold (trips/day) | Light Rail/Metro | BRT | Local Bus |",
        "|---|---|---|---|",
    ]
    for lrt_t in [50000, 75000, 100000]:
        n_lrt = sum(1 for r in feasible if r["total_demand"] >= lrt_t)
        n_brt = sum(1 for r in feasible if BRT_THRESHOLD <= r["total_demand"] < lrt_t)
        n_bus = len(feasible) - n_lrt - n_brt
        lines.append(f"| {lrt_t:,} | {n_lrt} | {n_brt} | {n_bus} |")
    lines += [
        "",
        "Light Rail/Metro threshold fixed at 75,000 trips/day; varying the BRT threshold:",
        "",
        "| BRT Threshold (trips/day) | Light Rail/Metro | BRT | Local Bus |",
        "|---|---|---|---|",
    ]
    for brt_t in [10000, 15000, 20000]:
        n_lrt = sum(1 for r in feasible if r["total_demand"] >= LRT_THRESHOLD)
        n_brt = sum(1 for r in feasible if brt_t <= r["total_demand"] < LRT_THRESHOLD)
        n_bus = len(feasible) - n_lrt - n_brt
        lines.append(f"| {brt_t:,} | {n_lrt} | {n_brt} | {n_bus} |")
    lines += [
        "",
        "## W5 Config Used",
        "",
        "```",
        "w_demand_gain=0.50, w_efficiency=0.25, w_equity=0.25",
        "max_detour_ratio=1.8, min_stop_spacing=300m, max_stop_spacing=1000m",
        "min_daily_demand=500 trips/day, max_route_km=30km",
        "```",
    ]
    out = OUTPUT_DIR / "w6_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [OK] Report written: {out}")


def main() -> None:
    SEP = "=" * 70
    print(f"\n{SEP}\n  W6: NEW CORRIDOR GENERATION\n{SEP}")
    cfg = W5Config()
    engine = create_engine(PG_URI)
    try:
        print("\n[Step 1] Applying DB migration...")
        run_migration(engine)

        print("\n[Step 2] Loading coverage-gap surface from DB...")
        gap_gdf = load_gap_agebs(engine)
        print(f"  [OK] {len(gap_gdf)} AGEBs loaded")

        print("\n[Step 3] Selecting anchor AGEBs via Jenks natural breaks...")
        anchors = select_anchors_jenks(gap_gdf, k_classes=5, min_demand=500.0)
        print(f"  [OK] {len(anchors)} anchor AGEBs in top Jenks class")
        if len(anchors) == 0:
            print("  [ERR] No anchors found. Run W3 first.")
            sys.exit(1)

        # Anchor trim criterion. Kept as coverage_gap_n because W6 conceptually targets the
        # COVERAGE GAP (the W3 dependent variable) rather than raw demand. NOTE (honest finding,
        # 2026-07-12 Line 4 backtest): this is empirically IDENTICAL to trimming by
        # "transit_demand". Within the unserved high-gap anchor pool, accessibility ~ 0 by
        # construction, so coverage_gap_n = demand/(access+1) ~ demand -- gap-ranking IS
        # demand-ranking here. Switching this axis did NOT change the corridors (it does not
        # rescue the dropped Line 4 anchors, contrary to an earlier note). The real reason W6
        # misses sparse peripheral corridors is architectural (30 anchors / KMeans k=6 / MST),
        # not the trim column. Set to "transit_demand" to confirm the null effect.
        ANCHOR_TRIM_COL = "coverage_gap_n"
        if len(anchors) > N_ANCHORS:
            anchors = anchors.nlargest(N_ANCHORS, ANCHOR_TRIM_COL).reset_index(drop=True)
            print(f"  [OK] Trimmed to top {N_ANCHORS} by {ANCHOR_TRIM_COL}")

        print("\n[Step 4] Clustering anchors into corridor groups...")
        anchors = cluster_anchors(anchors, n_corridors=N_CORRIDORS)
        n_groups = anchors["corridor_group"].nunique()
        print(f"  [OK] {n_groups} corridor groups formed")

        print("\n[Step 5] Loading OSM drive graph...")
        G_raw = load_or_download_osm()
        G_proj = project_to_6372(G_raw)
        print(f"  [OK] Graph: {G_proj.number_of_nodes()} nodes, {G_proj.number_of_edges()} edges (EPSG:6372)")

        print("\n[Step 6] Snapping anchor centroids to OSM nodes...")
        cx_list = anchors["cx"].tolist()
        cy_list = anchors["cy"].tolist()
        osm_node_ids = snap_to_osm_nodes(G_proj, cx_list, cy_list)
        anchors = anchors.copy()
        anchors["osm_node"] = osm_node_ids
        print(f"  [OK] {len(osm_node_ids)} centroids snapped")

        print("\n[Step 7] Building corridor paths (one MST per cluster)...")
        corridor_geoms = []
        corridor_groups = []
        corridor_kms = []
        for group_id in sorted(anchors["corridor_group"].unique()):
            group_rows = anchors[anchors["corridor_group"] == group_id]
            terminal_nodes = group_rows["osm_node"].tolist()
            geom, route_km = build_corridor_path(G_proj, terminal_nodes)
            if geom is None or route_km <= 0.01:
                print(f"  [SKIP] Group {group_id}: could not build path")
                continue
            corridor_geoms.append(geom)
            corridor_groups.append(group_id)
            corridor_kms.append(route_km)
            print(f"  [OK] Group {group_id}: {route_km:.2f} km, {len(terminal_nodes)} terminals")

        if not corridor_geoms:
            print("  [ERR] No valid corridor paths built.")
            sys.exit(1)

        print("\n[Step 8] Building RouteCandidate objects...")
        candidates = []
        for geom, gid, road_km in zip(corridor_geoms, corridor_groups, corridor_kms):
            cid = f"W6_G{gid:02d}"
            rc = build_route_candidate(cid, geom, engine, config=cfg, route_km_override=road_km)
            if rc is None:
                print(f"  [SKIP] {cid}: fewer than 2 served AGEBs")
                continue
            candidates.append((rc, geom, gid))
            print(f"  [OK] {cid}: {len(rc.served_ageb_ids)} served AGEBs, "
                  f"{rc.route_km:.2f}km, connected={rc.connects_to_existing}")

        if not candidates:
            print("  [ERR] No valid RouteCandidate objects built.")
            sys.exit(1)

        print("\n[Step 9] Evaluating W5 objectives and constraints...")
        all_ids = list({aid for rc, _, _ in candidates for aid in rc.served_ageb_ids})
        ctx_list = load_ageb_context(all_ids, engine)
        ctx_map = {c.cvegeo: c for c in ctx_list}

        objectives = []
        constraint_results = []
        for rc, geom, gid in candidates:
            ctxs = [ctx_map[aid] for aid in rc.served_ageb_ids if aid in ctx_map]
            obj = evaluate_objective(rc, ctxs, cfg)
            cr = check_constraints(rc, ctxs, cfg)
            objectives.append(obj)
            constraint_results.append(cr)
            print(f"  {rc.candidate_id}: f1={obj.f1_demand_gain:.3f} f2={obj.f2_route_km:.2f}km "
                  f"f3={obj.f3_equity:.3f} score={obj.total_score:.3f} feasible={cr.feasible}")
            for v in cr.violations:
                print(f"    [VIOLATION] {v.message}")

        print("\n[Step 10] Pareto ranking...")
        ranks = pareto_rank(objectives)

        print("\n[Step 11] Assembling output rows...")
        rows = []
        geom_list = []
        for (rc, geom, gid), obj, cr, rank in zip(candidates, objectives, constraint_results, ranks):
            ctxs = [ctx_map[aid] for aid in rc.served_ageb_ids if aid in ctx_map]
            td = sum(c.transit_demand for c in ctxs)
            mode = assign_mode(td, BRT_THRESHOLD, LRT_THRESHOLD)
            rows.append({
                "candidate_id": rc.candidate_id,
                "corridor_group": int(gid),
                "route_km": float(obj.f2_route_km),
                "n_stops": int(rc.n_stops),
                "straight_line_km": float(rc.straight_line_km),
                "connects_to_existing": bool(rc.connects_to_existing),
                "n_served_agebs": len(rc.served_ageb_ids),
                "total_demand": float(td),
                "f1_demand_gain": float(obj.f1_demand_gain),
                "f2_route_km": float(obj.f2_route_km),
                "f3_equity": float(obj.f3_equity),
                "composite_score": float(obj.composite_score),
                "total_score": float(obj.total_score),
                "pareto_rank": int(rank),
                "feasible": bool(cr.feasible),
                "mode_assignment": mode,
                "geom_wkt": geom.wkt,
            })
            geom_list.append(geom)

        print("\n[Step 12] Writing outputs...")
        write_to_db(engine, rows)
        write_geojson(rows, geom_list)
        write_scores_csv(rows)
        write_pareto_chart(rows)
        write_report(rows)

        print(f"\n{SEP}\n  [OK] W6 CORRIDOR GENERATION COMPLETE\n{SEP}")
        print(f"\nOutputs: {OUTPUT_DIR}/")
        print("  corridor_candidates.geojson  -- QGIS-ready ranked corridors")
        print("  corridor_scores.csv          -- objective function scores")
        print("  pareto_front.png             -- Pareto scatter (f1 vs f2)")
        print("  w6_report.md                 -- methodology + results table")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
