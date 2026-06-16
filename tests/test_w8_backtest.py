"""
Tests for W8 GTFS masking utilities and shape overlap metric.
"""
import pytest
import pandas as pd
from pathlib import Path


def test_get_premium_stop_ids_returns_set():
    """get_premium_stop_ids returns a Python set of stop_id strings."""
    from src.w8_backtest import get_premium_stop_ids
    data_dir = Path("data")
    if not (data_dir / "routes.txt").exists():
        pytest.skip("GTFS data not available")
    stop_ids = get_premium_stop_ids(data_dir, agency_ids={"MM", "MT"})
    assert isinstance(stop_ids, set)
    assert len(stop_ids) > 0
    assert all(isinstance(s, str) for s in stop_ids)


def test_get_premium_stop_ids_excludes_bus():
    """BUS-agency stops should NOT appear in the premium set."""
    from src.w8_backtest import get_premium_stop_ids
    data_dir = Path("data")
    if not (data_dir / "routes.txt").exists():
        pytest.skip("GTFS data not available")
    all_stops = get_premium_stop_ids(data_dir, agency_ids={"MM", "MT", "BUS", "ME"})
    premium_only = get_premium_stop_ids(data_dir, agency_ids={"MM", "MT"})
    assert premium_only.issubset(all_stops)
    assert len(premium_only) < len(all_stops)


def test_compute_shape_overlap_full():
    """A corridor that exactly follows a route shape -> overlap = 1.0."""
    from shapely.geometry import LineString
    from src.w8_backtest import compute_shape_overlap
    route = LineString([(0, 0), (1000, 0)])
    corridor = LineString([(0, 0), (1000, 0)])
    overlap = compute_shape_overlap(route, corridor, buffer_m=400)
    assert overlap == pytest.approx(1.0, abs=1e-3)


def test_compute_shape_overlap_none():
    """A corridor far from a route shape -> overlap = 0.0."""
    from shapely.geometry import LineString
    from src.w8_backtest import compute_shape_overlap
    route = LineString([(0, 0), (1000, 0)])
    corridor = LineString([(0, 100000), (1000, 100000)])
    overlap = compute_shape_overlap(route, corridor, buffer_m=400)
    assert overlap == pytest.approx(0.0, abs=1e-3)


def test_compute_shape_overlap_partial():
    """Corridor covers half the route -> overlap ~0.5."""
    from shapely.geometry import LineString
    from src.w8_backtest import compute_shape_overlap
    route = LineString([(0, 0), (2000, 0)])
    corridor = LineString([(0, 0), (1000, 0)])
    overlap = compute_shape_overlap(route, corridor, buffer_m=10)
    assert 0.3 < overlap < 0.7
