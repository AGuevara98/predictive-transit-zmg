# src/w6_candidates.py
"""
W6 Candidate Builder: converts a corridor LineString (EPSG:6372) into a
RouteCandidate by spatial-joining with base.ageb to find served AGEBs,
checking SITEUR connectivity, and computing route geometry statistics.
"""
import math
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from shapely.geometry import LineString
from sqlalchemy import text

from src.w5_types import RouteCandidate, W5Config

WALK_BUFFER_M = 400.0
DEFAULT_STOP_SPACING_M = 500.0


def compute_n_stops(
    route_km: float,
    min_spacing_m: float = 300.0,
    max_spacing_m: float = 1000.0,
    default_spacing_m: float = DEFAULT_STOP_SPACING_M,
) -> int:
    """
    Estimate number of stops so per-stop spacing satisfies [min_spacing_m, max_spacing_m].
    n_default = round(route_m / default_spacing_m) + 1
    n_min     = ceil(route_m / max_spacing_m) + 1   (fewest stops, max spacing)
    n_max     = floor(route_m / min_spacing_m) + 1  (most stops, min spacing)
    n         = clamp(n_default, n_min, n_max), minimum 2
    """
    route_m = route_km * 1000.0
    if route_m <= 0.0:
        return 2
    n_default = round(route_m / default_spacing_m) + 1
    n_min = math.ceil(route_m / max_spacing_m) + 1
    n_max = math.floor(route_m / min_spacing_m) + 1
    return max(2, max(n_min, min(n_max, n_default)))


def get_served_agebs(
    geom_wkt: str,
    engine,
    buffer_m: float = WALK_BUFFER_M,
) -> List[str]:
    """Return cve_ageb of all AGEBs with centroid within buffer_m of the corridor."""
    query = text("""
        SELECT a.cvegeo
        FROM base.ageb a
        WHERE ST_DWithin(
            ST_Centroid(a.geom),
            ST_GeomFromText(:wkt, 6372),
            :buf
        )
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"wkt": geom_wkt, "buf": buffer_m}).fetchall()
    return [str(r.cvegeo) for r in rows]


def check_connects_siteur(
    geom_wkt: str,
    engine,
    buffer_m: float = WALK_BUFFER_M,
) -> bool:
    """True if the corridor passes within buffer_m of any SITEUR GTFS stop."""
    query = text("""
        SELECT EXISTS (
            SELECT 1 FROM base.gtfs_stops s
            WHERE ST_DWithin(s.geom, ST_GeomFromText(:wkt, 6372), :buf)
        )
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"wkt": geom_wkt, "buf": buffer_m}).scalar()
    return bool(result)


def build_route_candidate(
    corridor_id: str,
    geom: LineString,
    engine,
    config: W5Config = None,
) -> Optional[RouteCandidate]:
    """
    Construct RouteCandidate from a corridor LineString.
    Returns None if fewer than 2 AGEBs are served (degenerate corridor).
    """
    if config is None:
        config = W5Config()

    geom_wkt = geom.wkt
    route_km = geom.length / 1000.0

    start = geom.coords[0]
    end = geom.coords[-1]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    straight_km = max(math.sqrt(dx * dx + dy * dy) / 1000.0, 0.001)

    n_stops = compute_n_stops(
        route_km,
        min_spacing_m=config.min_stop_spacing_m,
        max_spacing_m=config.max_stop_spacing_m,
    )

    served_ids = get_served_agebs(geom_wkt, engine)
    if len(served_ids) < 2:
        return None

    connects = check_connects_siteur(geom_wkt, engine)

    return RouteCandidate(
        candidate_id=corridor_id,
        served_ageb_ids=served_ids,
        route_km=route_km,
        n_stops=n_stops,
        straight_line_km=straight_km,
        connects_to_existing=connects,
    )
