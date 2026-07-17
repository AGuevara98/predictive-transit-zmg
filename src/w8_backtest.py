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
from src.w5_constraints import check_constraints
from src.w5_objective import load_ageb_context
from src.w5_types import W5Config
from src.w6_anchors import (
    cluster_anchors,
    select_anchors_jenks,
    select_frontier_anchors,
)
from src.w6_candidates import build_route_candidate
from src.w6_graph import (
    anchor_span_km,
    corridor_trunk_diameter,
    load_or_download_osm,
    project_to_6372,
    snap_to_osm_nodes,
)

DATA_DIR = Path(__file__).parent.parent / "data" / "gtfs"
N_SAMPLE_POINTS = 200   # sample count along each route shape for overlap calculation


# ---------------------------------------------------------------------------
# Step 1: Identify premium-route stop IDs
# ---------------------------------------------------------------------------

def get_premium_stop_ids(
    data_dir: Path, agency_ids: Set[str] = None, route_ids: Set[str] = None
) -> Set[str]:
    """Return stop_ids belonging to the masked routes.

    Selection: `route_ids` (exact route-level mask, e.g. Line 3 = {MT_L3, ST_L3}) when
    given, else all routes of `agency_ids` (default MM + MT). route_ids takes precedence
    so a single line can be masked without pulling its whole agency.
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

    if route_ids is not None:
        premium_routes = set(route_ids)
    else:
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
    route_ids: Set[str] = None,
) -> gpd.GeoDataFrame:
    """Reconstruct one LineString per masked route from shapes.txt.

    Selection mirrors get_premium_stop_ids: `route_ids` when given, else `agency_ids`.
    Returns GeoDataFrame with columns: route_id, shape_id, geometry (EPSG:6372).
    """
    if agency_ids is None:
        agency_ids = {"MM", "MT"}

    routes = pd.read_csv(data_dir / "routes.txt", dtype=str)
    trips = pd.read_csv(data_dir / "trips.txt", dtype=str)
    shapes = pd.read_csv(data_dir / "shapes.txt", dtype={"shape_id": str})

    if route_ids is not None:
        premium_routes = set(route_ids)
    else:
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
# Step 5b: Masked network connectivity (for frontier anchors)
# ---------------------------------------------------------------------------

def masked_network_connected(
    masked_gap_gdf: gpd.GeoDataFrame,
    excluded_stop_ids: Set[str],
    data_dir: Path,
    radius_m: float = 400.0,
) -> gpd.GeoDataFrame:
    """AGEBs whose centroid is within radius_m of a REMAINING (non-masked) GTFS stop.

    The masked-world analogue of w6_anchors.network_connected_agebs (which queries the
    full base.gtfs_stops). Frontier anchor selection must use the served/unserved seam
    of the network AFTER masking -- otherwise a corridor could be judged "connected" via
    a premium stop that the backtest just removed. Returns the subset of masked_gap_gdf
    (carrying cx, cy) that select_frontier_anchors needs.
    """
    from scipy.spatial import cKDTree

    stops_df = pd.read_csv(data_dir / "stops.txt", dtype={"stop_id": str})
    stops_df = stops_df[~stops_df["stop_id"].isin(excluded_stop_ids)].copy()
    if len(stops_df) == 0 or len(masked_gap_gdf) == 0:
        return masked_gap_gdf.iloc[0:0].copy()
    stops_gdf = gpd.GeoDataFrame(
        stops_df,
        geometry=gpd.points_from_xy(stops_df["stop_lon"], stops_df["stop_lat"]),
        crs="EPSG:4326",
    ).to_crs(CRS_CANONICAL)

    tree = cKDTree(np.c_[stops_gdf.geometry.x.values, stops_gdf.geometry.y.values])
    dist, _ = tree.query(masked_gap_gdf[["cx", "cy"]].values, k=1)
    return masked_gap_gdf[dist <= radius_m].copy().reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 6: Full backtest orchestrator
# ---------------------------------------------------------------------------

def run_backtest(
    engine,
    data_dir: Path = DATA_DIR,
    agency_ids: Set[str] = None,
    route_ids: Set[str] = None,
) -> dict:
    """Run full hold-out backtest.

    1. Mask routes from GTFS -- `route_ids` (exact lines, e.g. Line 3 = {MT_L3, ST_L3})
       when given, else all routes of `agency_ids` (default MM + MT premium).
    2. Recompute accessibility without those stops
    3. Recompute coverage gap
    4. Re-run the canonical W6 generator on the masked surface: frontier anchors
       (masked served/unserved seam) -> coverage_gap_n trim -> MST-diameter-trunk ->
       anchor-directness feasibility gate. "Re-proposed" = the FEASIBLE corridors.
    5. Evaluate overlap between re-proposed (feasible) corridors and masked route shapes
    Returns a dict with summary statistics (incl. n_corridors_built vs n_corridors_reproposed).
    """
    if agency_ids is None:
        agency_ids = {"MM", "MT"}
    mask_label = f"routes {sorted(route_ids)}" if route_ids else f"agencies {sorted(agency_ids)}"

    print("[Backtest] Identifying masked stop IDs...")
    excluded = get_premium_stop_ids(data_dir, agency_ids, route_ids=route_ids)
    print(f"  [OK] {len(excluded)} stops masked ({mask_label})")

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

    print("[Backtest] Re-running W6 anchor selection (frontier, masked connectivity)...")
    # Canonical run_w6 pipeline (2026-07-15 re-architecture): frontier anchors on the
    # MASKED served/unserved seam, coverage_gap_n trim, MST-diameter-trunk shaper, and
    # the anchor-directness feasibility gate. Replaces the retired build_corridor_path +
    # transit_demand-trim + no-frontier + no-feasibility path so backtest overlap is
    # measured on the same generator run_w6 actually ships.
    N_ANCHORS = 30
    N_CORRIDORS = 6
    cfg = W5Config()

    empty = {
        "n_excluded_stops": len(excluded),
        "n_anchors_found": 0,
        "n_corridors_built": 0,
        "n_corridors_reproposed": 0,
        "mean_overlap_fraction": None,
        "per_route_overlap": [],
    }

    anchors = select_anchors_jenks(masked_gap_gdf, k_classes=5, min_demand=500.0)
    if len(anchors) == 0:
        print("  [WARN] No Jenks anchors after masking. Skipping.")
        return empty

    connected = masked_network_connected(masked_gap_gdf, excluded, data_dir, radius_m=400.0)
    anchors = select_frontier_anchors(anchors, connected, radius_m=400.0)
    if len(anchors) == 0:
        print("  [WARN] No frontier anchors after masking. Skipping.")
        return empty
    if len(anchors) > N_ANCHORS:
        anchors = anchors.nlargest(N_ANCHORS, "coverage_gap_n").reset_index(drop=True)
    anchors = cluster_anchors(anchors, n_corridors=N_CORRIDORS)
    print(f"  [OK] {len(anchors)} frontier anchors, "
          f"{anchors['corridor_group'].nunique()} groups")

    print("[Backtest] Loading OSM graph...")
    G_proj = project_to_6372(load_or_download_osm())

    print("[Backtest] Building diameter-trunk corridors + anchor-directness gate...")
    osm_node_ids = snap_to_osm_nodes(G_proj, anchors["cx"].tolist(), anchors["cy"].tolist())
    anchors = anchors.copy()
    anchors["osm_node"] = osm_node_ids

    reproposed = []       # FEASIBLE corridor geoms (what run_w6 ships)
    n_built = 0
    for gid in sorted(anchors["corridor_group"].unique()):
        nodes = anchors.loc[anchors["corridor_group"] == gid, "osm_node"].tolist()
        geom, route_km = corridor_trunk_diameter(G_proj, nodes)
        if geom is None or route_km <= 0.01:
            continue
        n_built += 1
        span = anchor_span_km(G_proj, nodes)
        rc = build_route_candidate(f"BT_G{gid:02d}", geom, engine, config=cfg,
                                   route_km_override=route_km, anchor_span_km=span)
        if rc is None:
            continue
        ctxs = load_ageb_context(rc.served_ageb_ids, engine)
        if check_constraints(rc, ctxs, cfg).feasible:
            reproposed.append(geom)

    print(f"  [OK] {n_built} corridors built, {len(reproposed)} feasible after masking")

    print("[Backtest] Loading masked route shapes...")
    masked_shapes = load_premium_route_shapes(data_dir, agency_ids, route_ids=route_ids)
    print(f"  [OK] {len(masked_shapes)} masked route shapes loaded")

    if not reproposed or len(masked_shapes) == 0:
        return {
            "n_excluded_stops": len(excluded),
            "n_anchors_found": len(anchors),
            "n_corridors_built": n_built,
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
        "n_corridors_built": n_built,
        "n_corridors_reproposed": len(reproposed),
        "mean_overlap_fraction": mean_overlap,
        "per_route_overlap": per_route,
    }
