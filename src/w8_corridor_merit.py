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
from dataclasses import dataclass
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


@dataclass
class MeritBaselines:
    """Precomputed reference stats for scoring corridor merit (Question B axes)."""
    ageb: gpd.GeoDataFrame
    route_served: dict          # route_id -> set(cve_ageb)
    baseline_dpk: pd.Series     # route_id -> served-demand / route_km
    metro_hi_share: float       # system-wide High-gap AGEB share


def build_merit_baselines(engine) -> MeritBaselines:
    """Load AGEB metrics + existing-route served sets and demand/km baseline."""
    ageb = load_ageb_metrics(engine)
    routes = gpd.read_postgis(
        "SELECT route_id, route_km, geom FROM features.route_audit",
        engine, geom_col="geom",
    )
    route_served, dpk = {}, {}
    for _, r in routes.iterrows():
        served = served_ageb_ids(ageb, r.geom)
        route_served[r.route_id] = served
        demand_sum = ageb.loc[ageb["cve_ageb"].isin(served), "transit_demand"].sum()
        if r.route_km and r.route_km > 0:
            dpk[r.route_id] = demand_sum / r.route_km
    return MeritBaselines(
        ageb=ageb,
        route_served=route_served,
        baseline_dpk=pd.Series(dpk),
        metro_hi_share=float((ageb["gap_category"] == "High-gap").mean()),
    )


def score_corridor(geom, route_km: float, total_demand: float,
                   b: MeritBaselines) -> dict:
    """Score one corridor on the three Question-B merit axes.

    passed = serves genuine need (High-gap share > metro baseline) AND
             non-redundant (best Jaccard < 0.60) AND
             efficient (demand/km >= 50th pct of existing routes).
    """
    served = served_ageb_ids(b.ageb, geom)
    sub = b.ageb[b.ageb["cve_ageb"].isin(served)]
    hi_share = float((sub["gap_category"] == "High-gap").mean()) if len(sub) else float("nan")
    best_j = max((jaccard(served, rs) for rs in b.route_served.values()), default=0.0)
    redundant = best_j >= REDUNDANCY_JACCARD_THRESH
    dpk = total_demand / route_km if route_km else float("nan")
    dpk_pct = float((b.baseline_dpk < dpk).mean() * 100) if len(b.baseline_dpk) else float("nan")
    passed = bool((hi_share > b.metro_hi_share) and (not redundant) and (dpk_pct >= 50))
    return dict(n_served=len(served), hi_share=hi_share, best_jaccard=float(best_j),
                redundant=redundant, demand_per_km=dpk, dpk_pct=dpk_pct, passed=passed)


def main():
    eng = create_engine(PG_URI)
    b = build_merit_baselines(eng)
    print(f"[Load] {len(b.ageb)} AGEBs; {len(b.route_served)} existing routes; "
          f"metro High-gap baseline={b.metro_hi_share:.1%}\n")

    w6 = gpd.read_postgis(
        "SELECT candidate_id, route_km, total_demand, geom FROM features.route_candidates "
        "WHERE feasible = true ORDER BY candidate_id",
        eng, geom_col="geom",
    )
    print(f"[W6] {len(w6)} feasible corridors: {list(w6['candidate_id'])}\n")
    print("=" * 78)
    for _, c in w6.iterrows():
        r = score_corridor(c.geom, c.route_km, c.total_demand, b)
        need = "need+" if r["hi_share"] > b.metro_hi_share else "need-"
        red = "unique" if not r["redundant"] else "REDUNDANT"
        eff = "eff+" if r["dpk_pct"] >= 50 else "eff-"
        verdict = "PASS" if r["passed"] else "MIXED/FAIL"
        print(f"  {c.candidate_id}: High-gap {r['hi_share']:.1%} ({need})  "
              f"best-Jaccard {r['best_jaccard']:.2f} ({red})  "
              f"demand/km {r['demand_per_km']:.0f} = {r['dpk_pct']:.0f}pct ({eff})  -> {verdict}")
    print("=" * 78)


if __name__ == "__main__":
    main()
