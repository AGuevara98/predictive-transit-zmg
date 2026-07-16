"""
Compare three corridor SHAPERS on the frontier anchor groups:

  mst_flatten  -- current build_corridor_path (branching MST flattened to one line;
                  inserts phantom straight jumps + self-loops)
  tsp_path     -- corridor_path_tsp: open path visiting all anchors
  diameter     -- corridor_trunk_diameter: MST longest leaf-to-leaf trunk

Reports per corridor: terminals, route_km, biggest inter-vertex jump (phantom-jump
detector), is_simple, served AGEBs, endpoint detour ratio, and standard W5 feasibility.
Path shapers should show max_jump ~ real edge length (no km-scale jumps) and make the
standard endpoint detour_ratio meaningful again.

Run (venv active): python src/w6_shaper_compare.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from sqlalchemy import create_engine

from config import PG_URI
from src.w5_constraints import check_constraints
from src.w5_objective import evaluate_objective, load_ageb_context
from src.w5_types import W5Config
from src.w6_anchors import load_gap_agebs, load_gtfs_stops, network_connected_agebs
from src.w6_candidates import build_route_candidate
from src.w6_graph import (
    build_corridor_path, corridor_path_tsp, corridor_trunk_diameter,
    load_or_download_osm, project_to_6372,
)
from src.w6_anchor_experiment import build_anchor_terminals, CONNECT_M
from src.w8_corridor_merit import build_merit_baselines, score_corridor

SHAPERS = {
    "mst_flatten": build_corridor_path,
    "tsp_path": corridor_path_tsp,
    "diameter": corridor_trunk_diameter,
}


def max_jump_m(geom):
    xy = np.array(geom.coords)
    if len(xy) < 2:
        return 0.0
    return float(np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1])).max())


def main():
    eng = create_engine(PG_URI)
    cfg = W5Config()
    baselines = build_merit_baselines(eng)
    gap = load_gap_agebs(eng)
    conn = network_connected_agebs(eng, radius_m=CONNECT_M)
    stops = load_gtfs_stops(eng)
    G = project_to_6372(load_or_download_osm())
    terminals, _ = build_anchor_terminals("frontier", gap, conn, stops, G)

    hdr = (f"{'corridor':16s} {'nT':>3s} {'km':>6s} {'maxJump_m':>9s} {'simple':>6s} "
           f"{'served':>6s} {'detour':>6s} {'feas':>5s} {'merit':>5s}")
    for shaper_name, shaper in SHAPERS.items():
        print(f"\n=== {shaper_name} ===")
        print(hdr)
        print("-" * len(hdr))
        n_feas = 0
        for gid in sorted(terminals):
            nodes = terminals[gid]
            geom, km = shaper(G, nodes)
            if geom is None or km <= 0.01:
                continue
            cid = f"G{gid:02d}"
            rc = build_route_candidate(cid, geom, eng, config=cfg, route_km_override=km)
            if rc is None:
                continue
            ctxs = load_ageb_context(rc.served_ageb_ids, eng)
            cr = check_constraints(rc, ctxs, cfg)
            td = sum(c.transit_demand for c in ctxs)
            merit = score_corridor(geom, km, td, baselines)
            detour = rc.route_km / rc.straight_line_km if rc.straight_line_km else float("inf")
            n_feas += cr.feasible
            print(f"{cid:16s} {len(dict.fromkeys(nodes)):3d} {km:6.1f} {max_jump_m(geom):9.0f} "
                  f"{str(geom.is_simple):>6s} {len(rc.served_ageb_ids):6d} {detour:6.2f} "
                  f"{str(cr.feasible):>5s} {str(merit['passed']):>5s}")
        print(f"  feasible under standard W5 endpoint detour: {n_feas}")
    eng.dispose()


if __name__ == "__main__":
    main()
