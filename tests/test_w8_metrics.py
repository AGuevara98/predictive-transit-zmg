"""Tests for W8 validation metrics (pure functions only)."""
import numpy as np
import pytest

from src.w8_metrics import gini_coefficient, coverage_rate, pop_served_per_km


# ---------------------------------------------------------------------------
# gini_coefficient
# ---------------------------------------------------------------------------

def test_gini_perfect_equality():
    vals = np.array([5.0, 5.0, 5.0, 5.0])
    assert gini_coefficient(vals) == pytest.approx(0.0, abs=1e-6)


def test_gini_perfect_inequality():
    vals = np.array([0.0, 0.0, 0.0, 100.0])
    assert gini_coefficient(vals) == pytest.approx(0.75, abs=1e-6)


def test_gini_known_value():
    vals = np.array([1.0, 2.0, 3.0, 4.0])
    n = 4
    sorted_v = np.sort(vals)
    gini_expected = (2 * np.sum((np.arange(1, n + 1)) * sorted_v) / (n * np.sum(sorted_v))) - (n + 1) / n
    assert gini_coefficient(vals) == pytest.approx(gini_expected, abs=1e-6)


def test_gini_single_value():
    assert gini_coefficient(np.array([42.0])) == pytest.approx(0.0, abs=1e-6)


def test_gini_all_zeros():
    assert gini_coefficient(np.zeros(5)) == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# coverage_rate
# ---------------------------------------------------------------------------

def test_coverage_rate_all_covered():
    import geopandas as gpd
    from shapely.geometry import Point
    ageb_gdf = gpd.GeoDataFrame(
        {"cve_ageb": ["A", "B", "C"]},
        geometry=[Point(0, 0), Point(1, 0), Point(2, 0)],
        crs="EPSG:6372",
    )
    service_buf = gpd.GeoDataFrame(
        geometry=[Point(1, 0).buffer(1000)],
        crs="EPSG:6372",
    )
    rate = coverage_rate(ageb_gdf, service_buf)
    assert rate == pytest.approx(1.0, abs=1e-6)


def test_coverage_rate_none_covered():
    import geopandas as gpd
    from shapely.geometry import Point
    ageb_gdf = gpd.GeoDataFrame(
        {"cve_ageb": ["A", "B"]},
        geometry=[Point(0, 0), Point(1, 0)],
        crs="EPSG:6372",
    )
    service_buf = gpd.GeoDataFrame(
        geometry=[Point(100000, 100000).buffer(1)],
        crs="EPSG:6372",
    )
    rate = coverage_rate(ageb_gdf, service_buf)
    assert rate == pytest.approx(0.0, abs=1e-6)


def test_coverage_rate_partial():
    import geopandas as gpd
    from shapely.geometry import Point
    ageb_gdf = gpd.GeoDataFrame(
        {"cve_ageb": ["A", "B", "C", "D"]},
        geometry=[Point(0, 0), Point(200, 0), Point(100000, 0), Point(100200, 0)],
        crs="EPSG:6372",
    )
    service_buf = gpd.GeoDataFrame(
        geometry=[Point(100, 0).buffer(300)],
        crs="EPSG:6372",
    )
    rate = coverage_rate(ageb_gdf, service_buf)
    assert rate == pytest.approx(0.5, abs=1e-6)


# ---------------------------------------------------------------------------
# pop_served_per_km
# ---------------------------------------------------------------------------

def test_pop_served_per_km():
    import geopandas as gpd
    from shapely.geometry import Point, LineString
    ageb_gdf = gpd.GeoDataFrame(
        {"cve_ageb": ["A", "B"], "pe_population": [1000, 500]},
        geometry=[Point(0, 0), Point(10000, 0)],
        crs="EPSG:6372",
    )
    corridor_gdf = gpd.GeoDataFrame(
        {"candidate_id": ["C1"], "route_km": [1.0]},
        geometry=[LineString([(0, -100), (0, 100)])],
        crs="EPSG:6372",
    )
    result = pop_served_per_km(ageb_gdf, corridor_gdf, buffer_m=400)
    assert result == pytest.approx(1000.0, abs=1.0)


def test_pop_served_per_km_no_corridors():
    import geopandas as gpd
    from shapely.geometry import Point
    ageb_gdf = gpd.GeoDataFrame(
        {"cve_ageb": ["A"], "pe_population": [1000]},
        geometry=[Point(0, 0)],
        crs="EPSG:6372",
    )
    corridor_gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:6372")
    result = pop_served_per_km(ageb_gdf, corridor_gdf, buffer_m=400)
    assert result == 0.0
