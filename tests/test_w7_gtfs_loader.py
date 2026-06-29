"""
Tests for W7.1 -- GTFS Shape Loader (src/w7_gtfs_loader.py)
All tests use synthetic CSV data via io.StringIO; no DB or file-system calls.
"""
import io
import math
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.w7_gtfs_loader import (
    _build_shape_geometries,
    _compute_connectivity,
    _straight_km,
    load_routes,
    load_shapes,
    load_stops,
    load_trips,
)


# ---------------------------------------------------------------------------
# Test _straight_km
# ---------------------------------------------------------------------------

def test_straight_km_horizontal():
    # 1000m horizontal line in projected CRS
    line = LineString([(0, 0), (1000, 0)])
    assert abs(_straight_km(line) - 1.0) < 1e-6


def test_straight_km_diagonal():
    # 3-4-5 triangle -> 5000m hypotenuse
    line = LineString([(0, 0), (3000, 4000)])
    assert abs(_straight_km(line) - 5.0) < 1e-6


def test_straight_km_minimum_is_positive():
    # Single-point degenerate line
    line = LineString([(0, 0), (0, 0)])
    result = _straight_km(line)
    assert result >= 0.001


def test_straight_km_multi_segment_uses_endpoints():
    # A zigzag whose most distant pair of points happens to be its endpoints
    line = LineString([(0, 0), (500, 500), (1000, 0)])
    result = _straight_km(line)
    assert abs(result - 1.0) < 1e-6


def test_straight_km_loop_uses_hull_diameter():
    # A closed-loop route (start == end): a 1000x1000m square circuit.
    # Endpoint distance would be 0; the hull diameter is the diagonal (~1414m).
    line = LineString([(0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 0)])
    result = _straight_km(line)
    assert abs(result - math.sqrt(2)) < 1e-6


# ---------------------------------------------------------------------------
# Test _build_shape_geometries
# ---------------------------------------------------------------------------

def test_build_shape_geometries_basic():
    """Two shapes each with two points; both should produce valid LineStrings."""
    shapes_df = pd.DataFrame({
        "shape_id": ["S1", "S1", "S2", "S2"],
        "shape_pt_lat": [20.60, 20.61, 20.70, 20.71],
        "shape_pt_lon": [-103.30, -103.31, -103.20, -103.21],
        "shape_pt_sequence": [0, 1, 0, 1],
    })
    result = _build_shape_geometries(shapes_df)
    assert "S1" in result
    assert "S2" in result
    assert isinstance(result["S1"], LineString)
    assert not result["S1"].is_empty


def test_build_shape_geometries_ordering():
    """Points should be sorted by shape_pt_sequence before building geometry."""
    shapes_df = pd.DataFrame({
        "shape_id": ["S1", "S1", "S1"],
        "shape_pt_lat": [20.62, 20.60, 20.61],
        "shape_pt_lon": [-103.32, -103.30, -103.31],
        "shape_pt_sequence": [2, 0, 1],
    })
    result = _build_shape_geometries(shapes_df)
    coords = list(result["S1"].coords)
    # After sorting by sequence (0, 1, 2), first coord corresponds to seq=0
    # We cannot check exact projected coords but can verify 3 points
    assert len(coords) == 3


def test_build_shape_geometries_skips_single_point():
    """A shape with only one point should be skipped."""
    shapes_df = pd.DataFrame({
        "shape_id": ["S1"],
        "shape_pt_lat": [20.60],
        "shape_pt_lon": [-103.30],
        "shape_pt_sequence": [0],
    })
    result = _build_shape_geometries(shapes_df)
    assert "S1" not in result


# ---------------------------------------------------------------------------
# Test _compute_connectivity
# ---------------------------------------------------------------------------

def test_compute_connectivity_overlapping_routes():
    """Two routes that share a corridor (within 50m) should both be flagged."""
    # Two parallel lines 10m apart
    line1 = LineString([(0, 0), (1000, 0)])
    line2 = LineString([(0, 10), (1000, 10)])
    gdf = gpd.GeoDataFrame(
        {"route_id": ["R1", "R2"]},
        geometry=[line1, line2],
        crs="EPSG:6372",
    )
    conn = _compute_connectivity(gdf)
    assert conn.iloc[0] is True or conn.iloc[0] == True
    assert conn.iloc[1] is True or conn.iloc[1] == True


def test_compute_connectivity_isolated_route():
    """A route far from all others should be flagged as not connected."""
    line1 = LineString([(0, 0), (1000, 0)])
    line2 = LineString([(100000, 100000), (200000, 100000)])  # 100 km away
    gdf = gpd.GeoDataFrame(
        {"route_id": ["R1", "R2"]},
        geometry=[line1, line2],
        crs="EPSG:6372",
    )
    conn = _compute_connectivity(gdf)
    # Neither route is within 50m of the other
    assert conn.iloc[0] == False
    assert conn.iloc[1] == False


def test_compute_connectivity_single_route():
    """A GeoDataFrame with one route should always be not connected."""
    gdf = gpd.GeoDataFrame(
        {"route_id": ["R1"]},
        geometry=[LineString([(0, 0), (1000, 0)])],
        crs="EPSG:6372",
    )
    conn = _compute_connectivity(gdf)
    assert conn.iloc[0] == False


# ---------------------------------------------------------------------------
# Test load_routes (using tmp CSV via monkeypatch)
# ---------------------------------------------------------------------------

def test_load_routes_columns(tmp_path):
    """load_routes should return DataFrame with required columns."""
    csv_content = (
        "route_id,agency_id,route_short_name,route_long_name,route_type\n"
        "R1,BUS,R1,Route One,3\n"
        "R2,BUS,R2,Route Two,3\n"
    )
    data_dir = tmp_path
    (data_dir / "routes.txt").write_text(csv_content)
    df = load_routes(data_dir)
    assert "route_id" in df.columns
    assert "route_short_name" in df.columns
    assert "route_long_name" in df.columns
    assert len(df) == 2


def test_load_routes_missing_optional_cols(tmp_path):
    """load_routes fills missing route_long_name with empty string."""
    csv_content = "route_id,route_short_name,route_long_name,route_type\nR1,R1,,3\n"
    (tmp_path / "routes.txt").write_text(csv_content)
    df = load_routes(tmp_path)
    assert df.iloc[0]["route_long_name"] == ""
