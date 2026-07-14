"""
W8 -- Question B: do W6's own feasible corridors have merit on their own terms?

CLAUDE.md next-steps item 1 ("Test Question B"). Every backtest run so far (masked-premium
overlap, Line 4 reconstruction) measures whether W6 reproduces lines that were BUILT -- a
weak, asymmetric proxy for whether W6 produces GOOD corridors. This script measures the
latter directly for the 3 feasible corridors (W6_G00, W6_G03, W6_G05):

  (a) genuine need    -- do served AGEBs skew High-gap / high-demand vs the metro baseline?
  (b) non-redundancy  -- Jaccard AGEB-overlap vs all 247 existing SITEUR GTFS routes,
                         reusing W7's >=0.60 redundancy threshold
  (c) demand per km    -- total_demand / route_km, benchmarked against the same ratio
                         computed for every existing GTFS route (served-AGEB demand sum / route_km)

Run (WSL, venv active): python src/w8_corridor_merit.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from config import PG_URI

BUFFER_M = 400.0
REDUNDANCY_JACCARD_THRESH = 0.60


def load_ageb_metrics(engine) -> gpd.GeoDataFrame:
    q = """
        SELECT a.cvegeo AS cve_ageb, a.geom,
               cg.gap_category, cg.coverage_gap_n,
               te.transit_demand,
               pr.final_score
        FROM base.ageb a
        LEFT JOIN features.ageb_coverage_gap   cg ON cg.cve_ageb = a.cvegeo
        LEFT JOIN features.ageb_trip_ends      te ON te.cve_ageb = a.cvegeo
        LEFT JOIN features.nppv_prioritization pr ON pr.cve_ageb = a.cvegeo
    """
    return gpd.read_postgis(q, engine, geom_col="geom")


def served_ageb_ids(ageb_gdf: gpd.GeoDataFrame, corridor_geom, buffer_m: float = BUFFER_M) -> set:
    corridor_buf = corridor_geom.buffer(buffer_m)
    hit = ageb_gdf.geometry.centroid.within(corridor_buf)
    return set(ageb_gdf.loc[hit, "cve_ageb"])


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    eng = create_engine(PG_URI)

    ageb = load_ageb_metrics(eng)
    print(f"[Load] {len(ageb)} AGEBs with gap/demand/priority metrics\n")

    w6 = gpd.read_postgis(
        "SELECT candidate_id, route_km, total_demand, geom FROM features.route_candidates "
        "WHERE feasible = true ORDER BY candidate_id",
        eng, geom_col="geom",
    )
    print(f"[W6] {len(w6)} feasible corridors: {list(w6['candidate_id'])}\n")

    routes = gpd.read_postgis(
        "SELECT route_id, route_km, geom FROM features.route_audit", eng, geom_col="geom"
    )
    print(f"[GTFS] {len(routes)} existing SITEUR routes\n")

    print("[Step] Computing served-AGEB sets for all GTFS routes (baseline for demand/km + redundancy)...")
    route_served = {}
    route_demand_per_km = {}
    for _, r in routes.iterrows():
        served = served_ageb_ids(ageb, r.geom)
        route_served[r.route_id] = served
        demand_sum = ageb.loc[ageb["cve_ageb"].isin(served), "transit_demand"].sum()
        if r.route_km and r.route_km > 0:
            route_demand_per_km[r.route_id] = demand_sum / r.route_km
    baseline = pd.Series(route_demand_per_km)
    print(f"  [OK] existing-route demand/km: median={baseline.median():.0f}, "
          f"p75={baseline.quantile(.75):.0f}, p90={baseline.quantile(.90):.0f}\n")

    print("=" * 78)
    metro_hi_share = (ageb["gap_category"] == "High-gap").mean()
    verdicts = []
    for _, c in w6.iterrows():
        cid = c.candidate_id
        served = served_ageb_ids(ageb, c.geom)
        sub = ageb[ageb["cve_ageb"].isin(served)]
        print(f"\n[{cid}] route_km={c.route_km:.1f}  n_served_agebs={len(sub)}")

        # (a) genuine need
        print("  (a) need vs metro baseline")
        hi_share = (sub["gap_category"] == "High-gap").mean() if len(sub) else float("nan")
        for cat in ["High-gap", "Medium-gap", "Low-gap"]:
            c_share = (sub["gap_category"] == cat).mean() if len(sub) else float("nan")
            m_share = (ageb["gap_category"] == cat).mean()
            print(f"      {cat:<12} corridor {c_share:>6.1%}   metro {m_share:>6.1%}")
        print(f"      transit_demand median: corridor {sub['transit_demand'].median():>10.0f}"
              f"   metro {ageb['transit_demand'].median():>10.0f}")
        print(f"      final_score    median: corridor {sub['final_score'].median():>10.3f}"
              f"   metro {ageb['final_score'].median():>10.3f}")

        # (b) redundancy vs existing SITEUR routes
        best_route, best_j = None, 0.0
        for rid, rserved in route_served.items():
            j = jaccard(served, rserved)
            if j > best_j:
                best_route, best_j = rid, j
        flag = "REDUNDANT" if best_j >= REDUNDANCY_JACCARD_THRESH else "not redundant"
        print(f"  (b) best Jaccard overlap vs existing routes: {best_j:.2f} "
              f"(route {best_route}) -> {flag}")

        # (c) demand captured per km vs existing-route baseline
        dpk = c.total_demand / c.route_km if c.route_km else float("nan")
        pct = (baseline < dpk).mean() * 100
        print(f"  (c) demand/km: corridor {dpk:.0f}  vs existing-route median {baseline.median():.0f} "
              f"-> {pct:.0f}th percentile of existing routes")
        verdicts.append(dict(cid=cid, hi_share=hi_share, redundant=(best_j >= REDUNDANCY_JACCARD_THRESH),
                             dpk_pct=pct))

    # --- Question B verdict ---------------------------------------------------
    # Merit is measured on three axes; a corridor "passes" B when it serves genuine
    # unmet need (High-gap share above the 20.7% metro baseline), is non-redundant
    # with existing SITEUR service, and captures competitive demand per km (>= median
    # of the existing 247-route system, i.e. >= 50th percentile).
    print("\n" + "=" * 78)
    print("QUESTION B VERDICT (merit on own terms, not reconstruction of a built line)")
    print(f"  metro High-gap baseline = {metro_hi_share:.1%}; demand/km pass = >=50th pct of existing routes\n")
    for v in verdicts:
        need = "need+" if v["hi_share"] > metro_hi_share else "need-"
        red = "unique" if not v["redundant"] else "REDUNDANT"
        eff = "eff+" if v["dpk_pct"] >= 50 else "eff-"
        passed = (v["hi_share"] > metro_hi_share) and (not v["redundant"]) and (v["dpk_pct"] >= 50)
        print(f"  {v['cid']}: {need:<6} {red:<9} {eff:<5} -> {'PASS' if passed else 'MIXED/FAIL'}")
    print(
        "\n  Read: only W6_G03 clears all three axes, and only because it is a 1.4km stub\n"
        "  (2 anchors ~1km apart) -- not a real corridor. G00/G05 serve real need but are\n"
        "  low-efficiency anchor-to-anchor connectors (~1st pct demand/km). The generator's\n"
        "  feasibility filter is confounded with anchor-cluster SPARSITY: sparse 2-3 anchor\n"
        "  clusters yield short/straight (feasible) paths, dense 6-9 anchor clusters yield\n"
        "  long/convoluted (infeasible) paths -- independent of corridor merit. See CLAUDE.md\n"
        "  W8 Question B section for the traced anchor-funnel mechanism.\n"
    )
    print("=" * 78)


if __name__ == "__main__":
    main()
