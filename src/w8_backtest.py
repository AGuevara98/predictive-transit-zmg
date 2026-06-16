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


# ---------------------------------------------------------------------------
# Step 5: Load masked route shapes as LineStrings
# ---------------------------------------------------------------------------

def load_premium_route_shapes(
    data_dir: Path,
    agency_ids: Set[str] = None,
) -> gpd.GeoDataFrame:
    """Reconstruct one LineString per premium route from shapes.txt.

    Returns GeoDataFrame with columns: route_id, shape_id, geometry (EPSG:6372).
    """
    if agency_ids is None:
        agency_ids = {"MM", "MT"}

    routes = pd.read_csv(data_dir / "routes.txt", dtype=str)
    trips = pd.read_csv(data_dir / "trips.txt", dtype=str)
    shapes = pd.read_csv(data_dir / "shapes.txt", dtype={"shape_id": str})

    premium_routes = set(routes.loc[routes["agency_id"].isin(agency_ids), "route_id"])

    # One shape_id per route -- take the first shape_id per route
    route_shapes = (
        trips[trips["route_id"].isin(premium_routes)]
        .drop_duplicates(subset=["route_id"])
        [["route_id", "shape_id"]]
        .reset_index(drop=True)
    )

    records = []
    for _, row in route_shapes.iterrows():
        pts = shapes[shapes["shape_id"] == row["shape_id"]].sort_values("shape_pt_sequence")
        if len(pts) < 2:
            continue
        coords = list(zip(pts["shape_pt_lon"], pts["shape_pt_lat"]))
        geom = LineString(coords)
        records.append({"route_id": row["route_id"], "shape_id": row["shape_id"], "geometry": geom})

    if not records:
        return gpd.GeoDataFrame(columns=["route_id", "shape_id", "geometry"], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(records, crs="EPSG:4326").to_crs(CRS_CANONICAL)
    return gdf


# ---------------------------------------------------------------------------
# Step 2 (masked): Compute masked accessibility (in-memory, no DB write)
# ---------------------------------------------------------------------------

def compute_masked_accessibility(
    excluded_stop_ids: Set[str],
    ageb_gdf: gpd.GeoDataFrame,
    emp_df: pd.DataFrame,
    data_dir: Path,
) -> pd.DataFrame:
    """Re-run W3.1 accessibility without the excluded stops.

    Returns DataFrame with columns: cve_ageb, n_boarding_stops, accessibility_score.
    """
    # Load and filter stops
    stops_df = pd.read_csv(data_dir / "stops.txt", dtype={"stop_id": str})
    stops_df = stops_df[~stops_df["stop_id"].isin(excluded_stop_ids)].copy()
    stops_gdf = gpd.GeoDataFrame(
        stops_df,
        geometry=gpd.points_from_xy(stops_df["stop_lon"], stops_df["stop_lat"]),
        crs="EPSG:4326",
    ).to_crs(CRS_CANONICAL)

    # Load and filter stop_times to masked stops only
    st = load_stop_times()
    st = st[~st["stop_id"].isin(excluded_stop_ids)].copy()

    trip_headway = load_frequencies()

    # Keep only trips that still have at least 2 stops remaining
    trip_counts = st.groupby("trip_id")["stop_id"].count()
    valid_trips = set(trip_counts[trip_counts >= 2].index)
    st = st[st["trip_id"].isin(valid_trips)].copy()

    G = build_transit_graph(st, trip_headway)
    ageb_stop = ageb_stop_join(ageb_gdf, stops_gdf)
    return compute_accessibility(ageb_gdf, stops_gdf, G, ageb_stop, emp_df)


# ---------------------------------------------------------------------------
# Step 3 (masked): Compute masked coverage gap (in-memory)
# ---------------------------------------------------------------------------

def compute_masked_gap(
    demand_df: pd.DataFrame,
    masked_acc_df: pd.DataFrame,
    ageb_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Recompute coverage_gap_n without writing to DB.

    Returns GeoDataFrame with cve_ageb, coverage_gap_n, transit_demand, gap_category, cx, cy.
    """
    GAP_EPSILON = 1.0
    merged = demand_df.merge(masked_acc_df[["cve_ageb", "accessibility_score"]], on="cve_ageb", how="left")
    merged["accessibility_score"] = merged["accessibility_score"].fillna(0.0)
    merged["coverage_gap_raw"] = merged["transit_demand"] / (merged["accessibility_score"] + GAP_EPSILON)

    raw = merged["coverage_gap_raw"].values.astype(float)
    log_raw = np.log1p(raw)
    vmin, vmax = log_raw.min(), log_raw.max()
    if vmax > vmin:
        merged["coverage_gap_n"] = (log_raw - vmin) / (vmax - vmin)
    else:
        merged["coverage_gap_n"] = 0.0

    merged["demand_q"] = pd.qcut(merged["transit_demand"].rank(method="first"), 5, labels=False)
    merged["access_q"] = pd.qcut(merged["accessibility_score"].rank(method="first"), 5, labels=False)

    def _category(row):
        if row["demand_q"] >= 3 and row["access_q"] <= 1:
            return "High-gap"
        if row["demand_q"] <= 1 and row["access_q"] >= 3:
            return "Low-gap"
        return "Medium-gap"

    merged["gap_category"] = merged.apply(_category, axis=1)

    gdf = ageb_gdf[["cve_ageb", "geom"]].merge(
        merged[["cve_ageb", "coverage_gap_n", "transit_demand", "gap_category"]],
        on="cve_ageb", how="left",
    )
    gdf = gpd.GeoDataFrame(gdf, geometry="geom", crs=CRS_CANONICAL)
    gdf["cx"] = gdf.geometry.x
    gdf["cy"] = gdf.geometry.y
    return gdf


# ---------------------------------------------------------------------------
# Step 6: Full backtest orchestrator
# ---------------------------------------------------------------------------

def run_backtest(engine, data_dir: Path = DATA_DIR, agency_ids: Set[str] = None) -> dict:
    """Run full hold-out backtest.

    1. Mask premium routes (MM + MT) from GTFS
    2. Recompute accessibility without those stops
    3. Recompute coverage gap
    4. Re-run W6 anchor selection + clustering + path generation
    5. Evaluate overlap between re-proposed corridors and masked route shapes
    Returns a dict with summary statistics.
    """
    if agency_ids is None:
        agency_ids = {"MM", "MT"}

    print("[Backtest] Identifying premium stop IDs...")
    excluded = get_premium_stop_ids(data_dir, agency_ids)
    print(f"  [OK] {len(excluded)} premium stops masked (agencies: {agency_ids})")

    with engine.connect() as conn:
        ageb_gdf = gpd.read_postgis(
            "SELECT cvegeo AS cve_ageb, ST_Centroid(geom) AS geom FROM base.ageb",
            conn, geom_col="geom", crs=CRS_CANONICAL,
        )
        emp_df = pd.read_sql(
            text("SELECT cve_ageb, p_employment_proxy FROM features.nppv_features"),
            conn,
        )
        demand_df = pd.read_sql(
            text("SELECT cve_ageb, transit_demand FROM features.ageb_trip_ends"),
            conn,
        )

    print("[Backtest] Computing masked accessibility...")
    masked_acc = compute_masked_accessibility(excluded, ageb_gdf, emp_df, data_dir)

    print("[Backtest] Computing masked coverage gap...")
    masked_gap_gdf = compute_masked_gap(demand_df, masked_acc, ageb_gdf)

    print("[Backtest] Re-running W6 anchor selection...")
    anchors = select_anchors_jenks(masked_gap_gdf, k_classes=5, min_demand=500.0)
    if len(anchors) == 0:
        print("  [WARN] No anchors found after masking. Skipping path generation.")
        return {
            "n_excluded_stops": len(excluded),
            "n_anchors_found": 0,
            "n_corridors_reproposed": 0,
            "mean_overlap_fraction": None,
            "per_route_overlap": [],
        }

    N_ANCHORS = 30
    N_CORRIDORS = 6
    if len(anchors) > N_ANCHORS:
        anchors = anchors.nlargest(N_ANCHORS, "transit_demand").reset_index(drop=True)
    anchors = cluster_anchors(anchors, n_corridors=N_CORRIDORS)

    print("[Backtest] Loading OSM graph...")
    G_raw = load_or_download_osm()
    G_proj = project_to_6372(G_raw)

    print("[Backtest] Snapping anchors and building corridor paths...")
    osm_node_ids = snap_to_osm_nodes(G_proj, anchors["cx"].tolist(), anchors["cy"].tolist())
    anchors = anchors.copy()
    anchors["osm_node"] = osm_node_ids

    reproposed = []
    for gid in sorted(anchors["corridor_group"].unique()):
        group_rows = anchors[anchors["corridor_group"] == gid]
        geom, route_km = build_corridor_path(G_proj, group_rows["osm_node"].tolist())
        if geom is not None and route_km > 0.01:
            reproposed.append(geom)

    print(f"  [OK] {len(reproposed)} corridors re-proposed after masking")

    print("[Backtest] Loading masked route shapes...")
    masked_shapes = load_premium_route_shapes(data_dir, agency_ids)
    print(f"  [OK] {len(masked_shapes)} premium route shapes loaded")

    if not reproposed or len(masked_shapes) == 0:
        return {
            "n_excluded_stops": len(excluded),
            "n_anchors_found": len(anchors),
            "n_corridors_reproposed": len(reproposed),
            "mean_overlap_fraction": None,
            "per_route_overlap": [],
        }

    print("[Backtest] Computing route overlap fractions...")
    per_route = []
    for _, row in masked_shapes.iterrows():
        max_overlap = max(
            compute_shape_overlap(row.geometry, c, buffer_m=400.0)
            for c in reproposed
        )
        per_route.append({
            "route_id": row["route_id"],
            "shape_id": row["shape_id"],
            "max_overlap_fraction": max_overlap,
        })

    mean_overlap = float(np.mean([r["max_overlap_fraction"] for r in per_route]))
    print(f"  [OK] Mean overlap fraction: {mean_overlap:.3f}")

    return {
        "n_excluded_stops": len(excluded),
        "n_anchors_found": len(anchors),
        "n_corridors_reproposed": len(reproposed),
        "mean_overlap_fraction": mean_overlap,
        "per_route_overlap": per_route,
    }
