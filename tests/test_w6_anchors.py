# tests/test_w6_anchors.py
import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
from shapely.geometry import Point

from src.w6_anchors import select_anchors_jenks, cluster_anchors


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
