"""
W8 probe -- WHY did W6 miss Line 4? Trace the anchor funnel.

Reproduces W6's exact anchor selection (src.w6_anchors, wired as in run_w6):
  load_gap_agebs -> select_anchors_jenks(k=5, min_demand=500)
  -> trim to top N_ANCHORS=30 by transit_demand -> cluster_anchors(k=6)
and reports, at each stage, how many AGEBs on the real Line 4 corridor survive.

Localizes the failure:
  ~0 survive the Jenks/demand filter  -> ELIGIBILITY problem (Line 4 gap/demand too low)
  survive the filter but not the top-30 trim -> RANKING problem (out-competed on demand)
  survive to final anchors but corridor routed away -> ROUTING problem (KMeans/MST)

Run (WSL, venv active): python src/w8_line4_anchors.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geopandas as gpd
from shapely.ops import unary_union
from sqlalchemy import create_engine

from config import PG_URI
from src.w6_anchors import (
    N_ANCHORS, N_CORRIDORS, MIN_DEMAND,
    load_gap_agebs, select_anchors_jenks, cluster_anchors,
)

BUF = 800
L4_PATH = Path(__file__).resolve().parent.parent / "data" / "linea_4.geojson"


def l4_corridor():
    l4 = gpd.read_file(L4_PATH)
    if l4.crs is None:
        l4 = l4.set_crs(4326)
    l4 = l4.to_crs(6372)
    lines = l4[l4.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    src = lines if len(lines) else l4
    return unary_union(list(src.geometry)).buffer(BUF)


def main():
    eng = create_engine(PG_URI)
    corridor = l4_corridor()

    gap = load_gap_agebs(eng)
    gap["on_l4"] = gap.geometry.centroid.within(corridor)
    l4_ids = set(gap.loc[gap["on_l4"], "cve_ageb"])
    print(f"[Line 4] {len(l4_ids)} AGEBs on corridor (of {len(gap)} total)\n")

    # Stage 1 -- Jenks top class + demand filter (exact W6 call)
    pool = select_anchors_jenks(gap, k_classes=5, min_demand=MIN_DEMAND)
    pool_l4 = pool[pool["cve_ageb"].isin(l4_ids)]
    print(f"[Stage 1] Jenks top-class & demand >= {MIN_DEMAND:.0f}: "
          f"{len(pool)} in anchor pool; {len(pool_l4)} of them on Line 4")

    # Stage 2 -- trim to top N_ANCHORS by demand (exact W6 logic)
    anchors = pool
    if len(anchors) > N_ANCHORS:
        anchors = anchors.nlargest(N_ANCHORS, "transit_demand").reset_index(drop=True)
    anchors_l4 = anchors[anchors["cve_ageb"].isin(l4_ids)]
    print(f"[Stage 2] Trim to top {N_ANCHORS} by demand: "
          f"{len(anchors)} final anchors; {len(anchors_l4)} on Line 4")

    # Stage 3 -- cluster; which group(s) do the surviving Line 4 anchors land in
    anchors = cluster_anchors(anchors, n_corridors=N_CORRIDORS)
    a_l4 = anchors[anchors["cve_ageb"].isin(l4_ids)]
    if len(a_l4):
        print(f"[Stage 3] Line 4 anchors in corridor_group(s): "
              f"{sorted(a_l4['corridor_group'].unique().tolist())}")
        print(a_l4[["cve_ageb", "coverage_gap_n", "transit_demand", "corridor_group"]]
              .to_string(index=False))
    else:
        print("[Stage 3] No Line 4 AGEB survived into the final anchor set.")

    # Context -- where the Line 4 corridor sits on the two selection axes
    l4_rows = gap[gap["on_l4"]]
    print(f"\n[Context] anchor-pool coverage_gap_n floor ~ {pool['coverage_gap_n'].min():.4f}")
    print(f"  Line 4 coverage_gap_n : median {l4_rows['coverage_gap_n'].median():.4f}, "
          f"max {l4_rows['coverage_gap_n'].max():.4f}")
    print(f"  Line 4 transit_demand : median {l4_rows['transit_demand'].median():.0f}, "
          f"max {l4_rows['transit_demand'].max():.0f}")
    if len(anchors):
        print(f"  Final-anchor demand   : min {anchors['transit_demand'].min():.0f}, "
              f"median {anchors['transit_demand'].median():.0f}, "
              f"max {anchors['transit_demand'].max():.0f}")


if __name__ == "__main__":
    main()
