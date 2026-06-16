"""
W7.1 -- GTFS Shape Loader
==========================
Reads GTFS files from data/ and builds one LineString geometry per route
(EPSG:6372). Falls back from shapes.txt to stop-sequence reconstruction when
shapes are absent or when a route has no shape_id mapping.

Returns a GeoDataFrame with columns:
    route_id, route_short_name, route_long_name, geometry (LineString, 6372),
    route_km, n_stops, straight_line_km, connects_to_existing
"""
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CRS_CANONICAL

DATA_DIR = Path(__file__).parent.parent / "data" / "gtfs"


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_routes(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load routes.txt; return route_id, route_short_name, route_long_name."""
    routes = pd.read_csv(
        data_dir / "routes.txt",
        dtype={"route_id": str},
        usecols=["route_id", "route_short_name", "route_long_name"],
    )
    routes["route_short_name"] = routes["route_short_name"].fillna("")
    routes["route_long_name"] = routes["route_long_name"].fillna("")
    return routes


def load_trips(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load trips.txt; return route_id, trip_id, shape_id, direction_id."""
    cols = ["trip_id", "route_id", "shape_id", "direction_id"]
    trips = pd.read_csv(data_dir / "trips.txt", dtype=str, usecols=cols)
    trips["direction_id"] = trips["direction_id"].fillna("0")
    return trips


def load_shapes(data_dir: Path = DATA_DIR) -> Optional[pd.DataFrame]:
    """Load shapes.txt; return None if file absent."""
    path = data_dir / "shapes.txt"
    if not path.exists():
        return None
    shapes = pd.read_csv(
        path,
        dtype={"shape_id": str},
        usecols=["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
    )
    shapes["shape_pt_lat"] = pd.to_numeric(shapes["shape_pt_lat"], errors="coerce")
    shapes["shape_pt_lon"] = pd.to_numeric(shapes["shape_pt_lon"], errors="coerce")
    shapes["shape_pt_sequence"] = pd.to_numeric(shapes["shape_pt_sequence"], errors="coerce")
    shapes = shapes.dropna()
    return shapes


def load_stops(data_dir: Path = DATA_DIR) -> gpd.GeoDataFrame:
    """Load stops.txt as GeoDataFrame in CRS_CANONICAL."""
    stops = pd.read_csv(
        data_dir / "stops.txt",
        dtype={"stop_id": str},
        usecols=["stop_id", "stop_lat", "stop_lon"],
    )
    stops["stop_lat"] = pd.to_numeric(stops["stop_lat"], errors="coerce")
    stops["stop_lon"] = pd.to_numeric(stops["stop_lon"], errors="coerce")
    stops = stops.dropna(subset=["stop_lat", "stop_lon"])
    gdf = gpd.GeoDataFrame(
        stops,
        geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]),
        crs="EPSG:4326",
    ).to_crs(CRS_CANONICAL)
    return gdf


def load_stop_times(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load stop_times.txt; return trip_id, stop_id, stop_sequence."""
    st = pd.read_csv(
        data_dir / "stop_times.txt",
        dtype={"trip_id": str, "stop_id": str},
        usecols=["trip_id", "stop_id", "stop_sequence"],
    )
    st["stop_sequence"] = pd.to_numeric(st["stop_sequence"], errors="coerce")
    return st.dropna(subset=["stop_sequence"])


def load_frequencies(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load frequencies.txt; return trip_id, headway_secs. Empty df if absent."""
    path = data_dir / "frequencies.txt"
    if not path.exists():
        return pd.DataFrame(columns=["trip_id", "headway_secs"])
    freq = pd.read_csv(path, dtype={"trip_id": str})
    freq["headway_secs"] = pd.to_numeric(freq["headway_secs"], errors="coerce")
    return freq[["trip_id", "headway_secs"]].dropna()


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _straight_km(line: LineString) -> float:
    """Euclidean distance in km between first and last coordinate of a LineString."""
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.001
    x0, y0 = coords[0][0], coords[0][1]
    x1, y1 = coords[-1][0], coords[-1][1]
    return max(math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2) / 1000.0, 0.001)


def _build_shape_geometries(
    shapes: pd.DataFrame,
    crs_canonical: str = CRS_CANONICAL,
) -> Dict[str, LineString]:
    """Build one LineString per shape_id (sorted by sequence, projected to CRS_CANONICAL)."""
    result: Dict[str, LineString] = {}
    for shape_id, grp in shapes.groupby("shape_id", sort=False):
        grp_sorted = grp.sort_values("shape_pt_sequence")
        coords_wgs = list(zip(grp_sorted["shape_pt_lon"], grp_sorted["shape_pt_lat"]))
        if len(coords_wgs) < 2:
            continue
        # Project to canonical CRS using a temporary GeoDataFrame
        pts = gpd.GeoDataFrame(
            geometry=[Point(lon, lat) for lon, lat in coords_wgs],
            crs="EPSG:4326",
        ).to_crs(crs_canonical)
        coords_proj = [(pt.x, pt.y) for pt in pts.geometry]
        result[str(shape_id)] = LineString(coords_proj)
    return result


def _build_route_geom_from_stops(
    route_id: str,
    trips_df: pd.DataFrame,
    stop_times_df: pd.DataFrame,
    stops_gdf: gpd.GeoDataFrame,
) -> Optional[LineString]:
    """Fallback: build route geometry from ordered stop sequence for the first trip."""
    route_trips = trips_df[trips_df["route_id"] == route_id]["trip_id"].tolist()
    if not route_trips:
        return None
    trip_id = route_trips[0]
    seq = stop_times_df[stop_times_df["trip_id"] == trip_id].sort_values("stop_sequence")
    if len(seq) < 2:
        return None
    stop_ids = seq["stop_id"].tolist()
    stops_idx = stops_gdf.set_index("stop_id")
    coords = []
    for sid in stop_ids:
        if sid in stops_idx.index:
            pt = stops_idx.loc[sid, "geometry"]
            coords.append((pt.x, pt.y))
    if len(coords) < 2:
        return None
    return LineString(coords)


# ---------------------------------------------------------------------------
# Per-route statistics
# ---------------------------------------------------------------------------

def _route_n_stops(
    route_id: str,
    trips_df: pd.DataFrame,
    stop_times_df: pd.DataFrame,
) -> int:
    """Count unique stops served across all trips for this route."""
    route_trips = set(trips_df[trips_df["route_id"] == route_id]["trip_id"].tolist())
    served = stop_times_df[stop_times_df["trip_id"].isin(route_trips)]["stop_id"].unique()
    return int(len(served))


def _route_mean_headway(
    route_id: str,
    trips_df: pd.DataFrame,
    freq_df: pd.DataFrame,
) -> float:
    """Mean headway in seconds across all trips for this route. Default 420 s."""
    if freq_df.empty:
        return 420.0
    route_trips = set(trips_df[trips_df["route_id"] == route_id]["trip_id"].tolist())
    matched = freq_df[freq_df["trip_id"].isin(route_trips)]["headway_secs"]
    if matched.empty:
        return 420.0
    return float(matched.mean())


# ---------------------------------------------------------------------------
# Connectivity check
# ---------------------------------------------------------------------------

def _compute_connectivity(gdf: gpd.GeoDataFrame) -> pd.Series:
    """
    Mark a route as connects_to_existing=True if it shares any stop with
    at least one other route (i.e. it is part of a connected network).
    Uses route stop sets built from trips / stop_times would require a full
    join; instead we use spatial overlap: a route is 'connected' if its geometry
    is within 50m of any other route geometry in the GeoDataFrame.

    All routes in the GTFS ARE the existing network. We flag routes that share
    a spatial corridor with at least one other route as 'connected', which means
    passengers can transfer without walking far.
    """
    connected = []
    geoms = gdf["geometry"].tolist()
    ids = gdf["route_id"].tolist()
    for i, (rid, g) in enumerate(zip(ids, geoms)):
        found = False
        for j, g2 in enumerate(geoms):
            if i == j:
                continue
            if g.distance(g2) <= 50.0:
                found = True
                break
        connected.append(found)
    return pd.Series(connected, index=gdf.index)


# ---------------------------------------------------------------------------
# Main loader function
# ---------------------------------------------------------------------------

def load_gtfs_routes(data_dir: Path = DATA_DIR) -> gpd.GeoDataFrame:
    """
    Build one LineString per GTFS route (EPSG:6372).

    Returns GeoDataFrame with columns:
        route_id, route_short_name, route_long_name,
        geometry, route_km, n_stops, straight_line_km, connects_to_existing
    """
    print("[Step 1] Loading GTFS files...")
    routes_df = load_routes(data_dir)
    trips_df = load_trips(data_dir)
    shapes_df = load_shapes(data_dir)
    stops_gdf = load_stops(data_dir)
    stop_times_df = load_stop_times(data_dir)
    freq_df = load_frequencies(data_dir)
    print(f"  [OK] {len(routes_df)} routes, {len(trips_df)} trips, "
          f"{len(stops_gdf)} stops, {len(stop_times_df)} stop_times")

    # Build shape_id -> geometry map
    print("[Step 2] Building route geometries...")
    shape_geoms: Dict[str, LineString] = {}
    if shapes_df is not None and not shapes_df.empty:
        shape_geoms = _build_shape_geometries(shapes_df, CRS_CANONICAL)
        print(f"  [OK] {len(shape_geoms)} shape geometries built from shapes.txt")

    # Map route_id to preferred shape_id (direction 0 preferred, else first found)
    route_to_shape: Dict[str, str] = {}
    for route_id, grp in trips_df.groupby("route_id", sort=False):
        dir0 = grp[grp["direction_id"] == "0"]
        candidates = dir0 if not dir0.empty else grp
        for _, row in candidates.iterrows():
            sid = str(row.get("shape_id", ""))
            if sid and sid in shape_geoms:
                route_to_shape[str(route_id)] = sid
                break

    # Assemble one geometry per route
    records = []
    for _, row in routes_df.iterrows():
        route_id = str(row["route_id"])
        geom: Optional[LineString] = None

        if route_id in route_to_shape:
            geom = shape_geoms[route_to_shape[route_id]]
        else:
            geom = _build_route_geom_from_stops(
                route_id, trips_df, stop_times_df, stops_gdf
            )

        if geom is None or geom.is_empty or geom.length <= 0:
            continue

        route_km = geom.length / 1000.0
        straight_km = _straight_km(geom)
        n_stops = _route_n_stops(route_id, trips_df, stop_times_df)

        records.append({
            "route_id": route_id,
            "route_short_name": str(row["route_short_name"]),
            "route_long_name": str(row["route_long_name"]),
            "geometry": geom,
            "route_km": route_km,
            "n_stops": n_stops,
            "straight_line_km": straight_km,
        })

    print(f"  [OK] {len(records)} route geometries assembled")

    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=CRS_CANONICAL)
    gdf = gdf.reset_index(drop=True)

    # Connectivity: mark routes that spatially overlap with others
    print("[Step 3] Computing route connectivity...")
    gdf["connects_to_existing"] = _compute_connectivity(gdf)
    n_conn = gdf["connects_to_existing"].sum()
    print(f"  [OK] {n_conn}/{len(gdf)} routes flagged as connected")

    return gdf
