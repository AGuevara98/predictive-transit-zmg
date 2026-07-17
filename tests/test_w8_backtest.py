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


# ---------------------------------------------------------------------------
# Route-level masking (Line 3 = {MT_L3, ST_L3}) -- takes precedence over agency
# ---------------------------------------------------------------------------

def test_get_premium_stop_ids_route_level_precedence():
    """route_ids selects exactly those routes' stops, ignoring agency_ids."""
    from src.w8_backtest import get_premium_stop_ids
    data_dir = Path("data/gtfs")
    if not (data_dir / "routes.txt").exists():
        pytest.skip("GTFS data not available")
    line3 = get_premium_stop_ids(data_dir, route_ids={"MT_L3", "ST_L3"})
    mt_agency = get_premium_stop_ids(data_dir, agency_ids={"MT"})
    assert isinstance(line3, set) and len(line3) > 0
    # Line 3 is one line within (and beyond, via ST) the MT agency -> strictly fewer
    # stops than the whole MT agency, and route_ids must override the agency default.
    assert len(line3) < len(get_premium_stop_ids(data_dir, agency_ids={"MM", "MT"}))
    assert line3 != mt_agency


def test_load_route_shapes_route_level():
    """load_premium_route_shapes(route_ids=...) returns only those routes."""
    from src.w8_backtest import load_premium_route_shapes
    data_dir = Path("data/gtfs")
    if not (data_dir / "routes.txt").exists():
        pytest.skip("GTFS data not available")
    shapes = load_premium_route_shapes(data_dir, route_ids={"MT_L3", "ST_L3"})
    assert set(shapes["route_id"]).issubset({"MT_L3", "ST_L3"})
    assert len(shapes) > 0


# ---------------------------------------------------------------------------
# masked_network_connected: AGEB kept iff within radius of a REMAINING stop
# ---------------------------------------------------------------------------

def test_masked_network_connected_seam(tmp_path):
    """An AGEB near a remaining stop is kept; one near only a masked stop is dropped."""
    import geopandas as gpd
    from pyproj import Transformer
    from src.w8_backtest import masked_network_connected

    # Two stops in WGS84; project their coords into EPSG:6372 for the AGEB centroids.
    stops = pd.DataFrame({
        "stop_id": ["keep_stop", "masked_stop"],
        "stop_lon": [-103.35, -103.30],
        "stop_lat": [20.65, 20.70],
    })
    stops.to_csv(tmp_path / "stops.txt", index=False)

    tf = Transformer.from_crs("EPSG:4326", "EPSG:6372", always_xy=True)
    kx, ky = tf.transform(-103.35, 20.65)      # on top of keep_stop
    mx, my = tf.transform(-103.30, 20.70)      # on top of masked_stop
    gap = gpd.GeoDataFrame(
        {"cve_ageb": ["A_near_keep", "A_near_masked"], "cx": [kx, mx], "cy": [ky, my]},
        geometry=gpd.points_from_xy([kx, mx], [ky, my]), crs="EPSG:6372",
    )

    # Mask only masked_stop -> A_near_masked loses its connectivity, A_near_keep retains it.
    out = masked_network_connected(gap, excluded_stop_ids={"masked_stop"},
                                   data_dir=tmp_path, radius_m=400.0)
    kept = set(out["cve_ageb"])
    assert "A_near_keep" in kept
    assert "A_near_masked" not in kept
