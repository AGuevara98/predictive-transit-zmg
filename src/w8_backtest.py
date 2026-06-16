"""
W8.1 -- Backtest Validation
==========================
Masks premium transit routes (Mi Macro + Mi Tren) from the GTFS network,
re-runs the W3 accessibility + W3 coverage-gap pipeline in-memory,
re-runs the W6 corridor generation, and reports what fraction of the
masked route shapes are recovered by the re-proposed corridors.

Usage (standalone):
    python src/run_w8.py   # invoked by orchestrator; not meant for direct use
"""
import sys
from pathlib import Path
from typing import Optional, Set

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CRS_CANONICAL, PG_URI

# Reuse W3 accessibility building blocks
from src.w3_accessibility import (
    DEFAULT_HEADWAY_MIN,
    TRAVEL_BUDGET_MIN,
    WALK_BUFFER_M,
    WALK_SPEED_M_MIN,
    ageb_stop_join,
    build_transit_graph,
    compute_accessibility,
    load_frequencies,
    load_stop_times,
)

# Reuse W6 pipeline building blocks
from src.w6_anchors import cluster_anchors, select_anchors_jenks
from src.w6_candidates import build_route_candidate
from src.w6_graph import (
    build_corridor_path,
    load_or_download_osm,
    project_to_6372,
    snap_to_osm_nodes,
)

DATA_DIR = Path("data")
N_SAMPLE_POINTS = 200   # sample count along each route shape for overlap calculation


# ---------------------------------------------------------------------------
# Step 1: Identify premium-route stop IDs
# ---------------------------------------------------------------------------

def get_premium_stop_ids(data_dir: Path, agency_ids: Set[str] = None) -> Set[str]:
    """Return stop_ids belonging to routes operated by the given agencies.

    Default agencies: MM (Mi Macro BRT) and MT (Mi Tren light rail).
    """
    if agency_ids is None:
        agency_ids = {"MM", "MT"}

    routes = pd.read_csv(data_dir / "routes.txt", dtype=str)
    trips = pd.read_csv(data_dir / "trips.txt", dtype=str)
    stop_times = pd.read_csv(
        data_dir / "stop_times.txt",
        dtype={"trip_id": str, "stop_id": str},
        usecols=["trip_id", "stop_id"],
    )

    premium_routes = set(routes.loc[routes["agency_id"].isin(agency_ids), "route_id"])
    premium_trips = set(trips.loc[trips["route_id"].isin(premium_routes), "trip_id"])
    premium_stops = set(
        stop_times.loc[stop_times["trip_id"].isin(premium_trips), "stop_id"]
    )
    return premium_stops


# ---------------------------------------------------------------------------
# Step 2: Overlap metric
# ---------------------------------------------------------------------------

def compute_shape_overlap(
    route_geom: LineString,
    corridor_geom: LineString,
    buffer_m: float = 400.0,
    n_samples: int = N_SAMPLE_POINTS,
) -> float:
    """Fraction of sampled points along route_geom that fall within buffer_m of corridor_geom.

    Returns float in [0, 1].
    """
    if route_geom is None or corridor_geom is None:
        return 0.0
    total_len = route_geom.length
    if total_len == 0:
        return 0.0
    distances = np.linspace(0, total_len, n_samples)
    points = [route_geom.interpolate(d) for d in distances]
    corridor_buf = corridor_geom.buffer(buffer_m)
    covered = sum(1 for p in points if corridor_buf.contains(p))
    return covered / n_samples
