"""
W3.1 — GTFS-based Transit Accessibility per AGEB
==================================================
Computes cumulative-opportunities accessibility: weighted employment reachable
from each AGEB by transit within a 45-minute travel-time budget.

Algorithm:
  1. Load GTFS stops (WGS84 → EPSG:6372)
  2. Load AGEB centroids; spatial-join to find boarding stops ≤400m
  3. Build stop-to-stop travel-time graph from stop_times.txt
     - Edge weight = in-vehicle minutes along a trip (A→B same trip, min over all trips)
  4. Attach headway-based wait times from frequencies.txt (default 15 min)
  5. For each AGEB, Dijkstra from each boarding stop with residual time budget
     (45 min − walk_time − wait_time); collect reachable stops
  6. Resolve reachable stops → catchment AGEBs (stops within 400m)
  7. Accessibility = sum of employment_proxy at catchment AGEBs (jobs reachable)
  8. Write results to features.ageb_accessibility

Output: features.ageb_accessibility
        outputs/w3/ageb_accessibility.csv
"""

import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import psycopg2.extras
from shapely.geometry import Point
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CRS_CANONICAL, EMPLOYMENT_PROXY_MAP, PG_URI

ENGINE = create_engine(PG_URI)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "gtfs"

WALK_BUFFER_M = 400          # boarding-stop search radius
WALK_SPEED_M_MIN = 80.0      # pedestrian speed: 80 m/min (~1.33 m/s)
TRAVEL_BUDGET_MIN = 45.0     # total OD budget in minutes
DEFAULT_HEADWAY_MIN = 15.0   # used when stop has no frequencies.txt entry
EPSILON = 1.0                # division guard for normalization
MIN_FLOW_STOP = 0            # no flow filter at stop level (filter at AGEB level)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def time_to_minutes(t: str) -> float:
    """Convert GTFS time string (handles hours >= 24) to float minutes."""
    h, m, s = t.strip().split(":")
    return int(h) * 60 + int(m) + int(s) / 60.0


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_stops() -> gpd.GeoDataFrame:
    print("[Step 1] Loading GTFS stops...")
    stops = pd.read_csv(DATA_DIR / "stops.txt", dtype={"stop_id": str})
    stops_gdf = gpd.GeoDataFrame(
        stops,
        geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]),
        crs="EPSG:4326",
    ).to_crs(CRS_CANONICAL)
    print(f"  [OK] {len(stops_gdf):,} stops loaded")
    return stops_gdf


def load_ageb_centroids() -> gpd.GeoDataFrame:
    print("[Step 2] Loading AGEB centroids...")
    with ENGINE.raw_connection() as conn:
        gdf = gpd.read_postgis(
            "SELECT cvegeo AS cve_ageb, ST_Centroid(geom) AS geom FROM base.ageb",
            conn, geom_col="geom", crs=CRS_CANONICAL,
        )
    print(f"  [OK] {len(gdf):,} AGEBs loaded")
    return gdf


def load_nppv_employment() -> pd.DataFrame:
    """Load raw employment proxy values (not normalized) from nppv_features."""
    print("[Step 3] Loading employment proxy from nppv_features...")
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(
            "SELECT cve_ageb, p_employment_proxy FROM features.nppv_features",
            conn,
        )
    df["p_employment_proxy"] = pd.to_numeric(df["p_employment_proxy"], errors="coerce").fillna(0.0)
    print(f"  [OK] Employment proxy loaded for {len(df):,} AGEBs")
    return df


def load_stop_times() -> pd.DataFrame:
    print("[Step 4] Loading stop_times...")
    st = pd.read_csv(
        DATA_DIR / "stop_times.txt",
        dtype={"trip_id": str, "stop_id": str},
        usecols=["trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"],
    )
    # Convert to minutes; handle hours >= 24 (next-day service)
    st["dep_min"] = st["departure_time"].apply(time_to_minutes)
    st["arr_min"] = st["arrival_time"].apply(time_to_minutes)
    print(f"  [OK] {len(st):,} stop_time records loaded")
    return st


def load_frequencies() -> dict:
    """Return dict stop_id → mean_headway_minutes (averaged over all active periods).
    Falls back to DEFAULT_HEADWAY_MIN for any stop with no entry.
    Frequencies are keyed by trip_id; we map that to each stop served by that trip."""
    print("[Step 5] Loading frequencies...")
    freq_path = DATA_DIR / "frequencies.txt"
    if not freq_path.exists():
        print("  [WARN] frequencies.txt not found — using default headway for all stops")
        return {}

    freq = pd.read_csv(freq_path, dtype={"trip_id": str})
    freq["headway_min"] = pd.to_numeric(freq["headway_secs"], errors="coerce") / 60.0
    # Average headway per trip (across time windows during the day)
    trip_headway = freq.groupby("trip_id")["headway_min"].mean().to_dict()
    print(f"  [OK] Headway data for {len(trip_headway):,} trips")
    return trip_headway


# ---------------------------------------------------------------------------
# Build transit network graph
# ---------------------------------------------------------------------------

def build_transit_graph(stop_times: pd.DataFrame, trip_headway: dict) -> nx.DiGraph:
    """Build a directed weighted graph of stop-to-stop in-vehicle travel times.

    Each edge (A → B) carries weight = minimum in-vehicle travel time in minutes
    across all trips that consecutively serve A then B.

    We also attach wait_min as node attribute = headway / 2 for the departure stop,
    computed as the mean across all trips departing that stop.
    """
    print("[Step 6] Building stop-to-stop transit graph...")

    # Sort within each trip by sequence to identify consecutive pairs
    st_sorted = stop_times.sort_values(["trip_id", "stop_sequence"])

    # Consecutive pairs within a trip: (stop_A, dep_A) → (stop_B, arr_B)
    prev = st_sorted.shift(1)
    # Keep only rows where trip_id matches the previous row (same trip)
    same_trip = st_sorted["trip_id"] == prev["trip_id"]
    pairs = st_sorted[same_trip].copy()
    pairs["from_stop"] = prev.loc[same_trip, "stop_id"].values
    pairs["from_dep"]  = prev.loc[same_trip, "dep_min"].values
    pairs["to_arr"]    = pairs["arr_min"]
    pairs["ivt_min"]   = (pairs["to_arr"] - pairs["from_dep"]).clip(lower=0)

    # Minimum IVT per directed stop pair across all trips
    edge_min = (
        pairs.groupby(["from_stop", "stop_id"])["ivt_min"]
        .min()
        .reset_index()
        .rename(columns={"stop_id": "to_stop"})
    )

    G = nx.DiGraph()
    for _, row in edge_min.iterrows():
        G.add_edge(row["from_stop"], row["to_stop"], weight=float(row["ivt_min"]))

    # Compute node-level wait_time = mean(headway / 2) across trips departing that stop.
    # For each stop, collect all trip_ids that depart it, average their headways.
    stop_trips = stop_times.groupby("stop_id")["trip_id"].apply(set)
    for stop_id, trip_ids in stop_trips.items():
        headways = [
            trip_headway.get(tid, DEFAULT_HEADWAY_MIN) for tid in trip_ids
        ]
        wait = float(np.mean(headways)) / 2.0
        if stop_id in G.nodes:
            G.nodes[stop_id]["wait_min"] = wait
        else:
            # Stop appears in stop_times but has no outgoing edges (terminus)
            G.add_node(stop_id, wait_min=wait)

    print(f"  [OK] Graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    return G


# ---------------------------------------------------------------------------
# Spatial join: AGEBs ↔ stops (bidirectional: boarding and alighting)
# ---------------------------------------------------------------------------

def ageb_stop_join(agebs: gpd.GeoDataFrame, stops: gpd.GeoDataFrame) -> pd.DataFrame:
    """For each AGEB centroid, find all stops within WALK_BUFFER_M.

    Returns DataFrame with columns: cve_ageb, stop_id, walk_dist_m, walk_min.
    """
    print("[Step 7] Spatial join: AGEBs <-> stops within 400m...")
    # Build a proper GeoDataFrame with the buffered polygon as active geometry
    agebs_buf = gpd.GeoDataFrame(
        agebs[["cve_ageb"]].copy(),
        geometry=agebs["geom"].buffer(WALK_BUFFER_M),
        crs=CRS_CANONICAL,
    )

    joined = gpd.sjoin(
        stops[["stop_id", "geometry"]],
        agebs_buf[["cve_ageb", "geometry"]],
        how="inner",
        predicate="within",
    )

    joined = joined.reset_index().rename(columns={"index": "stop_idx"})

    # Merge centroid geometries to compute actual walking distances
    joined = joined.merge(
        agebs[["cve_ageb", "geom"]].rename(columns={"geom": "ageb_geom"}),
        on="cve_ageb", how="left",
    )
    joined["walk_dist_m"] = joined.apply(
        lambda r: r["geometry"].distance(r["ageb_geom"]), axis=1
    )
    joined["walk_min"] = joined["walk_dist_m"] / WALK_SPEED_M_MIN

    result = joined[["cve_ageb", "stop_id", "walk_dist_m", "walk_min"]].copy()
    print(f"  [OK] {len(result):,} AGEB-stop pairs (within 400m)")
    return result


# ---------------------------------------------------------------------------
# Accessibility computation
# ---------------------------------------------------------------------------

def compute_accessibility(
    agebs: gpd.GeoDataFrame,
    stops: gpd.GeoDataFrame,
    G: nx.DiGraph,
    ageb_stop: pd.DataFrame,
    ageb_employment: pd.DataFrame,
) -> pd.DataFrame:
    """For each AGEB, run Dijkstra from each boarding stop and aggregate reachable employment.

    Returns DataFrame: cve_ageb, n_boarding_stops, accessibility_score.
    """
    print("[Step 8] Computing accessibility scores...")

    # Pre-compute: for each stop, which AGEBs are within 400m (alighting catchment)
    # Reuse the same spatial join (symmetric within the same buffer distance)
    stop_to_agebs = ageb_stop.groupby("stop_id")["cve_ageb"].apply(set).to_dict()

    # AGEB employment lookup
    emp_lookup = ageb_employment.set_index("cve_ageb")["p_employment_proxy"].to_dict()

    # Valid graph stops (stops that appear in the transit network)
    graph_stops = set(G.nodes())

    # Group boarding stops per AGEB
    boarding = ageb_stop.groupby("cve_ageb").apply(
        lambda df: list(zip(df["stop_id"], df["walk_min"]))
    ).to_dict()

    results = []
    all_agebs = agebs["cve_ageb"].tolist()

    for i, cve in enumerate(all_agebs):
        if i % 200 == 0:
            print(f"    Processing AGEB {i+1}/{len(all_agebs)}...")

        board_stops = boarding.get(cve, [])
        # Filter to stops present in transit graph
        board_stops = [(s, w) for s, w in board_stops if s in graph_stops]
        n_boarding = len(board_stops)

        if n_boarding == 0:
            results.append({
                "cve_ageb": cve,
                "n_boarding_stops": 0,
                "accessibility_score": 0.0,
            })
            continue

        # Collect all reachable destination AGEBs across all boarding stops,
        # weighted by destination employment. Avoid double-counting: track
        # reachable AGEBs by minimum total time (each AGEB counted once).
        reachable_ageb_min_time: dict = {}

        for stop_id, walk_min in board_stops:
            wait_min = G.nodes[stop_id].get("wait_min", DEFAULT_HEADWAY_MIN / 2.0)
            overhead = walk_min + wait_min
            if overhead >= TRAVEL_BUDGET_MIN:
                continue

            ivt_budget = TRAVEL_BUDGET_MIN - overhead

            # Dijkstra from boarding stop with weight cutoff
            try:
                lengths = nx.single_source_dijkstra_path_length(
                    G, stop_id, cutoff=ivt_budget, weight="weight"
                )
            except nx.NetworkXError:
                continue

            # Map each reachable stop to its catchment AGEBs
            for dest_stop, ivt in lengths.items():
                total_time = overhead + ivt
                if total_time > TRAVEL_BUDGET_MIN:
                    continue
                for dest_ageb in stop_to_agebs.get(dest_stop, set()):
                    # Record minimum total time to reach this destination AGEB
                    if dest_ageb not in reachable_ageb_min_time or reachable_ageb_min_time[dest_ageb] > total_time:
                        reachable_ageb_min_time[dest_ageb] = total_time

        # Sum employment at all reachable AGEBs (each counted once)
        score = sum(emp_lookup.get(a, 0.0) for a in reachable_ageb_min_time)
        results.append({
            "cve_ageb": cve,
            "n_boarding_stops": n_boarding,
            "accessibility_score": score,
        })

    df = pd.DataFrame(results)
    print(f"  [OK] Accessibility computed for {len(df):,} AGEBs")
    print(f"  Non-zero: {(df['accessibility_score'] > 0).sum():,}")
    return df


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_log1p_minmax(series: pd.Series) -> pd.Series:
    log_vals = np.log1p(series.clip(lower=0))
    mn, mx = log_vals.min(), log_vals.max()
    if mx - mn < EPSILON:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (log_vals - mn) / (mx - mn)


# ---------------------------------------------------------------------------
# DB write
# ---------------------------------------------------------------------------

def write_accessibility(df: pd.DataFrame):
    print("[Step 9] Writing to features.ageb_accessibility...")
    df["accessibility_n"] = normalize_log1p_minmax(df["accessibility_score"])

    rows = list(df[["cve_ageb", "n_boarding_stops", "accessibility_score", "accessibility_n"]].itertuples(index=False, name=None))
    with ENGINE.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM features.ageb_accessibility")
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO features.ageb_accessibility
                   (cve_ageb, n_boarding_stops, accessibility_score, accessibility_n)
                   VALUES %s""",
                rows, page_size=500,
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("ANALYZE features.ageb_accessibility")
        conn.commit()
    print(f"  [OK] {len(rows):,} rows written")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\n" + "="*70)
    print("W3.1 -- GTFS-BASED TRANSIT ACCESSIBILITY")
    print("="*70)

    out_dir = PROJECT_ROOT / "outputs" / "w3"
    out_dir.mkdir(parents=True, exist_ok=True)

    stops_gdf   = load_stops()
    agebs_gdf   = load_ageb_centroids()
    emp_df      = load_nppv_employment()
    stop_times  = load_stop_times()
    trip_headway = load_frequencies()

    G = build_transit_graph(stop_times, trip_headway)

    ageb_stop = ageb_stop_join(agebs_gdf, stops_gdf)

    acc_df = compute_accessibility(
        agebs_gdf, stops_gdf, G, ageb_stop, emp_df
    )

    write_accessibility(acc_df)

    # Attach normalized column for CSV export
    acc_df["accessibility_n"] = normalize_log1p_minmax(acc_df["accessibility_score"])
    acc_df.to_csv(out_dir / "ageb_accessibility.csv", index=False)
    print(f"  [OK] CSV -> outputs/w3/ageb_accessibility.csv")

    print("\n" + "="*70)
    print("W3.1 ACCESSIBILITY COMPLETE")
    print("="*70)
    print(acc_df[["n_boarding_stops", "accessibility_score", "accessibility_n"]].describe().to_string())


if __name__ == "__main__":
    main()
