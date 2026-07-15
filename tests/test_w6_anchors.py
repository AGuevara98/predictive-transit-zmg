# tests/test_w6_anchors.py
import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
from shapely.geometry import Point

from src.w6_anchors import select_anchors_jenks, cluster_anchors, select_group_hubs


def make_anchor_gdf(gap_values, demands):
    """Synthetic GDF with coverage_gap_n and transit_demand columns."""
    n = len(gap_values)
    geoms = [Point(i * 1000.0, 0.0) for i in range(n)]
    return gpd.GeoDataFrame(
        {
            "cve_ageb": [f"A{i:03d}" for i in range(n)],
            "coverage_gap_n": gap_values,
            "transit_demand": demands,
            "cx": [i * 1000.0 for i in range(n)],
            "cy": [0.0] * n,
        },
        geometry=geoms,
        crs="EPSG:6372",
    )


def test_select_anchors_jenks_returns_only_top_class():
    low = [0.1, 0.15, 0.2, 0.25, 0.3, 0.32, 0.35, 0.37, 0.38, 0.40,
           0.42, 0.43, 0.44, 0.45, 0.46]
    high = [0.81, 0.85, 0.90, 0.95, 1.00]
    demands = [600.0] * 20
    gdf = make_anchor_gdf(low + high, demands)
    result = select_anchors_jenks(gdf, k_classes=5, min_demand=500.0)
    assert len(result) > 0
    assert all(result["coverage_gap_n"] >= 0.8 - 1e-6)


def test_select_anchors_jenks_filters_low_demand():
    gap = [0.9, 0.95, 1.0] + [0.1] * 17
    demands = [300.0, 600.0, 600.0] + [600.0] * 17
    gdf = make_anchor_gdf(gap, demands)
    result = select_anchors_jenks(gdf, k_classes=5, min_demand=500.0)
    assert "A000" not in result["cve_ageb"].values


def test_cluster_anchors_creates_n_groups():
    cx = [0.0, 1000.0, 2000.0, 10000.0, 11000.0, 12000.0]
    cy = [0.0] * 6
    gdf = gpd.GeoDataFrame(
        {
            "cve_ageb": [f"A{i}" for i in range(6)],
            "coverage_gap_n": [0.9] * 6,
            "transit_demand": [800.0] * 6,
            "cx": cx,
            "cy": cy,
        },
        geometry=[Point(x, y) for x, y in zip(cx, cy)],
        crs="EPSG:6372",
    )
    result = cluster_anchors(gdf, n_corridors=2)
    assert "corridor_group" in result.columns
    assert result["corridor_group"].nunique() == 2
    assert len(result) == 6


def test_cluster_anchors_clamps_groups_to_n_anchors():
    cx = [0.0, 1000.0, 2000.0]
    cy = [0.0, 0.0, 0.0]
    gdf = gpd.GeoDataFrame(
        {
            "cve_ageb": ["A0", "A1", "A2"],
            "coverage_gap_n": [0.9, 0.95, 1.0],
            "transit_demand": [800.0, 900.0, 1000.0],
            "cx": cx,
            "cy": cy,
        },
        geometry=[Point(x, y) for x, y in zip(cx, cy)],
        crs="EPSG:6372",
    )
    result = cluster_anchors(gdf, n_corridors=10)
    assert result["corridor_group"].nunique() <= 3


def make_grouped_anchors(rows):
    """rows: list of (cve_ageb, corridor_group, cx, cy)."""
    return gpd.GeoDataFrame(
        {
            "cve_ageb": [r[0] for r in rows],
            "corridor_group": [r[1] for r in rows],
            "coverage_gap_n": [0.9] * len(rows),
            "transit_demand": [800.0] * len(rows),
            "cx": [r[2] for r in rows],
            "cy": [r[3] for r in rows],
        },
        geometry=[Point(r[2], r[3]) for r in rows],
        crs="EPSG:6372",
    )


def make_stops(rows):
    """rows: list of (stop_id, cx, cy)."""
    return pd.DataFrame(
        {
            "stop_id": [r[0] for r in rows],
            "cx": [r[1] for r in rows],
            "cy": [r[2] for r in rows],
        }
    )


def test_select_group_hubs_picks_min_distance_pair():
    # Group 0 anchors near x=0; group 1 anchors near x=10000.
    anchors = make_grouped_anchors([
        ("A0", 0, 0.0, 0.0),
        ("A1", 0, 1000.0, 0.0),
        ("A2", 1, 10000.0, 0.0),
        ("A3", 1, 11000.0, 0.0),
    ])
    stops = make_stops([
        ("S_near0", 50.0, 0.0),      # 50m from A0  -> best for group 0
        ("S_mid0", 1200.0, 0.0),     # 200m from A1
        ("S_far", 5000.0, 0.0),
        ("S_near1", 10990.0, 0.0),   # 10m from A3  -> best for group 1
    ])
    hubs = select_group_hubs(anchors, stops)

    assert set(hubs["corridor_group"]) == {0, 1}
    g0 = hubs[hubs["corridor_group"] == 0].iloc[0]
    g1 = hubs[hubs["corridor_group"] == 1].iloc[0]
    assert g0["hub_stop_id"] == "S_near0"
    assert g0["hub_dist_m"] == pytest.approx(50.0)
    assert g0["anchor_cve_ageb"] == "A0"
    assert g1["hub_stop_id"] == "S_near1"
    assert g1["hub_dist_m"] == pytest.approx(10.0)
    assert g1["anchor_cve_ageb"] == "A3"


def test_select_group_hubs_far_hub_targets_most_remote_anchor():
    # One group; A0 sits next to a stop, A1 is remote from every stop.
    anchors = make_grouped_anchors([
        ("A0", 0, 0.0, 0.0),
        ("A1", 0, 5000.0, 0.0),
    ])
    stops = make_stops([
        ("S0", 10.0, 0.0),       # 10m from A0   -> near hub
        ("S1", 5100.0, 0.0),     # 100m from A1  -> far hub (nearest stop to remote anchor)
    ])
    hubs = select_group_hubs(anchors, stops)
    row = hubs[hubs["corridor_group"] == 0].iloc[0]
    # near hub = cheapest entry (A0)
    assert row["hub_stop_id"] == "S0"
    assert row["anchor_cve_ageb"] == "A0"
    assert row["hub_dist_m"] == pytest.approx(10.0)
    # far hub = nearest stop to the most-remote anchor (A1)
    assert row["far_hub_stop_id"] == "S1"
    assert row["far_anchor_cve_ageb"] == "A1"
    assert row["far_hub_dist_m"] == pytest.approx(100.0)


def test_select_group_hubs_far_equals_near_for_single_anchor():
    anchors = make_grouped_anchors([("A0", 0, 0.0, 0.0)])
    stops = make_stops([("S0", 30.0, 0.0), ("S1", 9000.0, 0.0)])
    hubs = select_group_hubs(anchors, stops)
    row = hubs.iloc[0]
    assert row["hub_stop_id"] == row["far_hub_stop_id"] == "S0"
    assert row["anchor_cve_ageb"] == row["far_anchor_cve_ageb"] == "A0"


def test_select_group_hubs_one_row_per_group():
    anchors = make_grouped_anchors([
        ("A0", 0, 0.0, 0.0),
        ("A1", 0, 1000.0, 0.0),
        ("A2", 1, 10000.0, 0.0),
        ("A3", 2, 20000.0, 0.0),
    ])
    stops = make_stops([("S", 100.0, 0.0), ("S2", 9900.0, 0.0), ("S3", 20100.0, 0.0)])
    hubs = select_group_hubs(anchors, stops)
    assert len(hubs) == hubs["corridor_group"].nunique() == 3
    assert set(hubs["corridor_group"]) == {0, 1, 2}


def test_select_group_hubs_empty_inputs():
    empty_anchors = make_grouped_anchors([])
    empty_stops = make_stops([])
    some_stops = make_stops([("S", 0.0, 0.0)])
    assert len(select_group_hubs(empty_anchors, some_stops)) == 0
    assert len(select_group_hubs(
        make_grouped_anchors([("A0", 0, 0.0, 0.0)]), empty_stops)) == 0


from src.w6_anchors import add_network_anchors


def make_connected_gdf(rows):
    """rows: list of (cve_ageb, cx, cy)."""
    return gpd.GeoDataFrame(
        {
            "cve_ageb": [r[0] for r in rows],
            "coverage_gap_n": [0.2] * len(rows),
            "transit_demand": [700.0] * len(rows),
            "cx": [r[1] for r in rows],
            "cy": [r[2] for r in rows],
        },
        geometry=[Point(r[1], r[2]) for r in rows],
        crs="EPSG:6372",
    )


def test_add_network_anchors_injects_nearest_connected_per_group():
    anchors = make_grouped_anchors([
        ("A0", 0, 0.0, 0.0),
        ("A1", 0, 1000.0, 0.0),
        ("A2", 1, 10000.0, 0.0),
    ])
    connected = make_connected_gdf([
        ("C_g0", 300.0, 0.0),        # 300m from A0 -> tie-in for group 0
        ("C_g1", 10200.0, 0.0),      # 200m from A2 -> tie-in for group 1
        ("C_far", 50000.0, 0.0),
    ])
    out, fallback = add_network_anchors(anchors, connected, max_tie_in_m=5000.0)
    assert fallback == set()
    net = out[out["role"] == "network"]
    assert set(net["cve_ageb"]) == {"C_g0", "C_g1"}
    assert set(net["corridor_group"]) == {0, 1}
    # original anchors tagged demand, nothing dropped
    assert (out[out["role"] == "demand"]["cve_ageb"].tolist()
            == ["A0", "A1", "A2"])


def test_add_network_anchors_falls_back_when_no_connected_in_range():
    anchors = make_grouped_anchors([("A0", 0, 0.0, 0.0)])
    connected = make_connected_gdf([("C_far", 20000.0, 0.0)])  # 20km > 5km cap
    out, fallback = add_network_anchors(anchors, connected, max_tie_in_m=5000.0)
    assert fallback == {0}
    assert (out["role"] == "network").sum() == 0
