import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString

from src.w8_corridor_merit import MeritBaselines, score_corridor


def _baselines():
    # Three AGEBs strung along y=0 at x=0,1000,2000; first two High-gap.
    ageb = gpd.GeoDataFrame(
        {
            "cve_ageb": ["A0", "A1", "A2"],
            "gap_category": ["High-gap", "High-gap", "Low-gap"],
            "coverage_gap_n": [0.9, 0.8, 0.1],
            "transit_demand": [1000.0, 1000.0, 100.0],
            "final_score": [0.5, 0.5, 0.2],
        },
        geometry=[Point(0, 0), Point(1000, 0), Point(2000, 0)],
        crs="EPSG:6372",
    )
    # metro High-gap share = 2/3; one existing route overlaps only A2.
    return MeritBaselines(
        ageb=ageb,
        route_served={"R1": {"A2"}},
        baseline_dpk=pd.Series({"R1": 50.0}),
        metro_hi_share=2 / 3,
    )


def test_score_corridor_flags_needy_nonredundant_efficient():
    b = _baselines()
    # Corridor along A0-A1 (both High-gap); buffer 400m picks up A0,A1 only.
    geom = LineString([(0, 0), (1000, 0)])
    r = score_corridor(geom, route_km=1.0, total_demand=2000.0, b=b)
    assert r["n_served"] == 2
    assert r["hi_share"] == 1.0            # both served AGEBs High-gap
    assert r["best_jaccard"] == 0.0        # no overlap with R1's {A2}
    assert r["redundant"] is False
    assert r["dpk_pct"] == 100.0           # 2000/1.0 beats baseline 50
    assert r["passed"] is True
