# src/w6_anchors.py
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sqlalchemy import text

try:
    import mapclassify
    HAVE_MAPCLASSIFY = True
except ImportError:
    HAVE_MAPCLASSIFY = False


N_ANCHORS = 30
N_CORRIDORS = 6
MIN_DEMAND = 500.0


def load_gap_agebs(engine) -> gpd.GeoDataFrame:
    query = text("""
        SELECT
            g.cve_ageb,
            g.coverage_gap_n,
            g.transit_demand,
            g.gap_category,
            ST_X(ST_Centroid(a.geom)) AS cx,
            ST_Y(ST_Centroid(a.geom)) AS cy,
            a.geom
        FROM features.ageb_coverage_gap g
        JOIN base.ageb a ON a.cvegeo = g.cve_ageb
        ORDER BY g.coverage_gap_n DESC
    """)
    with engine.connect() as conn:
        gdf = gpd.read_postgis(query, conn, geom_col="geom", crs="EPSG:6372")
    gdf["coverage_gap_n"] = gdf["coverage_gap_n"].astype(float)
    gdf["transit_demand"] = gdf["transit_demand"].astype(float)
    gdf["cx"] = gdf["cx"].astype(float)
    gdf["cy"] = gdf["cy"].astype(float)
    return gdf


def select_anchors_jenks(
    gdf: gpd.GeoDataFrame,
    k_classes: int = 5,
    min_demand: float = MIN_DEMAND,
) -> gpd.GeoDataFrame:
    # Return AGEBs in the highest Jenks natural-break class of coverage_gap_n
    # that also meet the minimum daily demand threshold.
    # Falls back to top-20th-percentile if mapclassify is unavailable.
    values = gdf["coverage_gap_n"].values.astype(float)

    if HAVE_MAPCLASSIFY:
        breaks = mapclassify.NaturalBreaks(values, k=k_classes)
        threshold = float(breaks.bins[-2])
    else:
        threshold = float(np.percentile(values, 80))

    mask = (gdf["coverage_gap_n"] >= threshold) & (gdf["transit_demand"] >= min_demand)
    return gdf[mask].copy().reset_index(drop=True)


def load_gtfs_stops(engine) -> pd.DataFrame:
    """Load all existing SITEUR GTFS stops with projected centroid coords.

    Returns a plain DataFrame (stop_id, cx, cy) in EPSG:6372 metres -- used as
    candidate network entry points ("hubs") for corridor generation.
    """
    query = text("""
        SELECT stop_id, ST_X(geom) AS cx, ST_Y(geom) AS cy
        FROM base.gtfs_stops
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    df["cx"] = df["cx"].astype(float)
    df["cy"] = df["cy"].astype(float)
    return df


def select_group_hubs(
    anchors_gdf: gpd.GeoDataFrame,
    stops_df: pd.DataFrame,
) -> pd.DataFrame:
    """Pick two existing SITEUR stops per corridor group to root both ends.

    Each anchor is matched to its nearest stop. The group then gets two hubs,
    both injected as mandatory MST terminals so the corridor is rooted in the
    existing network at both ends by construction:

      - near hub: the stop nearest the CLOSEST anchor -- the cheapest natural
        entry point onto the network (not the group centroid).
      - far hub: the stop nearest the most REMOTE anchor (the anchor with the
        largest distance-to-nearest-stop) -- so the would-be dead-end end of
        the corridor is connected too, rather than trailing off kilometres from
        any stop. When a group has a single anchor (or its closest and most
        remote anchors share a nearest stop) the two hubs coincide.

    Returns one row per group: corridor_group, hub_stop_id/hub_cx/hub_cy/
    hub_dist_m/anchor_cve_ageb (near), and far_hub_stop_id/far_hub_cx/
    far_hub_cy/far_hub_dist_m/far_anchor_cve_ageb (far).
    """
    from scipy.spatial import cKDTree

    empty = pd.DataFrame(
        columns=["corridor_group", "hub_stop_id", "hub_cx", "hub_cy",
                 "hub_dist_m", "anchor_cve_ageb",
                 "far_hub_stop_id", "far_hub_cx", "far_hub_cy",
                 "far_hub_dist_m", "far_anchor_cve_ageb"]
    )
    if len(anchors_gdf) == 0 or len(stops_df) == 0:
        return empty

    tree = cKDTree(stops_df[["cx", "cy"]].values)
    dist, idx = tree.query(anchors_gdf[["cx", "cy"]].values, k=1)

    tmp = pd.DataFrame({
        "corridor_group": anchors_gdf["corridor_group"].astype(int).values,
        "cve_ageb": anchors_gdf["cve_ageb"].values,
        "stop_row": idx,
        "dist_m": dist,
    })

    rows = []
    for gid, sub in tmp.groupby("corridor_group"):
        near = sub.loc[sub["dist_m"].idxmin()]
        far = sub.loc[sub["dist_m"].idxmax()]
        near_stop = stops_df.iloc[int(near["stop_row"])]
        far_stop = stops_df.iloc[int(far["stop_row"])]
        rows.append({
            "corridor_group": int(gid),
            "hub_stop_id": near_stop["stop_id"],
            "hub_cx": float(near_stop["cx"]),
            "hub_cy": float(near_stop["cy"]),
            "hub_dist_m": float(near["dist_m"]),
            "anchor_cve_ageb": near["cve_ageb"],
            "far_hub_stop_id": far_stop["stop_id"],
            "far_hub_cx": float(far_stop["cx"]),
            "far_hub_cy": float(far_stop["cy"]),
            "far_hub_dist_m": float(far["dist_m"]),
            "far_anchor_cve_ageb": far["cve_ageb"],
        })
    return pd.DataFrame(rows)


def network_connected_agebs(engine, radius_m: float = 400.0) -> gpd.GeoDataFrame:
    """AGEBs with >=1 GTFS stop within radius_m of their centroid (EPSG:6372).

    Returns cve_ageb, coverage_gap_n, transit_demand, cx, cy, geom -- the pool of
    "network-connected" AGEBs used by the two_tier and frontier anchor modes.
    """
    query = text("""
        SELECT g.cve_ageb, g.coverage_gap_n, g.transit_demand,
               ST_X(ST_Centroid(a.geom)) AS cx,
               ST_Y(ST_Centroid(a.geom)) AS cy,
               a.geom
        FROM features.ageb_coverage_gap g
        JOIN base.ageb a ON a.cvegeo = g.cve_ageb
        WHERE EXISTS (
            SELECT 1 FROM base.gtfs_stops s
            WHERE ST_DWithin(s.geom, ST_Centroid(a.geom), :r)
        )
    """)
    with engine.connect() as conn:
        gdf = gpd.read_postgis(query, conn, geom_col="geom", params={"r": radius_m},
                               crs="EPSG:6372")
    for col in ("coverage_gap_n", "transit_demand", "cx", "cy"):
        gdf[col] = gdf[col].astype(float)
    return gdf


def add_network_anchors(anchors_gdf, connected_gdf, max_tie_in_m: float = 5000.0):
    """two_tier (Approach A): inject one network-connected AGEB per corridor group.

    For each group, pick the connected AGEB nearest to ANY anchor in that group
    (cheapest network entry). Inject it as a role="network" anchor iff that nearest
    distance <= max_tie_in_m and it is not already an anchor in the group. Groups with
    no connected AGEB in range are returned in fallback_group_ids (caller applies hub
    injection). Existing anchors are tagged role="demand".

    Returns (augmented_gdf, fallback_group_ids: set[int]).
    """
    from scipy.spatial import cKDTree

    out = anchors_gdf.copy()
    out["role"] = "demand"
    if len(anchors_gdf) == 0 or len(connected_gdf) == 0:
        return out, set(int(g) for g in out.get("corridor_group", pd.Series([], dtype=int)).unique())

    # Use the anchors' active geometry column name (prod: "geom", tests: "geometry")
    # so the concat below stays single-geometry-column.
    gname = anchors_gdf.geometry.name
    tree = cKDTree(connected_gdf[["cx", "cy"]].values)
    new_rows = []
    fallback = set()
    for gid, sub in anchors_gdf.groupby("corridor_group"):
        dist, idx = tree.query(sub[["cx", "cy"]].values, k=1)
        best = int(dist.argmin())
        best_dist = float(dist[best])
        conn_row = connected_gdf.iloc[int(idx[best])]
        if best_dist > max_tie_in_m or conn_row["cve_ageb"] in set(sub["cve_ageb"]):
            if best_dist > max_tie_in_m:
                fallback.add(int(gid))
            continue
        new_rows.append({
            "cve_ageb": conn_row["cve_ageb"],
            "corridor_group": int(gid),
            "coverage_gap_n": float(conn_row["coverage_gap_n"]),
            "transit_demand": float(conn_row["transit_demand"]),
            "cx": float(conn_row["cx"]),
            "cy": float(conn_row["cy"]),
            gname: conn_row.geometry,
            "role": "network",
        })

    if new_rows:
        add_gdf = gpd.GeoDataFrame(new_rows, geometry=gname, crs=anchors_gdf.crs)
        out = pd.concat([out, add_gdf], ignore_index=True)
        out = gpd.GeoDataFrame(out, geometry=gname, crs=anchors_gdf.crs)
    return out, fallback


def select_frontier_anchors(anchors_gdf, connected_gdf, radius_m: float = 400.0):
    """frontier (Approach B): keep only anchors on the served/unserved seam.

    An anchor survives iff its centroid is within radius_m of a network-connected
    AGEB centroid. Deep-interior high-gap anchors (far from any connected AGEB) are
    dropped -- the mode's defining trade-off. Returns a reset-index GeoDataFrame.
    """
    from scipy.spatial import cKDTree

    if len(anchors_gdf) == 0 or len(connected_gdf) == 0:
        return anchors_gdf.iloc[0:0].copy()
    tree = cKDTree(connected_gdf[["cx", "cy"]].values)
    dist, _ = tree.query(anchors_gdf[["cx", "cy"]].values, k=1)
    keep = dist <= radius_m
    return anchors_gdf[keep].copy().reset_index(drop=True)


def cluster_anchors(
    anchors_gdf: gpd.GeoDataFrame,
    n_corridors: int = N_CORRIDORS,
) -> gpd.GeoDataFrame:
    """Assign each anchor to one of n_corridors spatial groups via KMeans."""
    n = len(anchors_gdf)
    if n == 0:
        result = anchors_gdf.copy()
        result["corridor_group"] = pd.Series([], dtype=int)
        return result

    k = min(n_corridors, n)
    coords = anchors_gdf[["cx", "cy"]].values
    labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(coords)
    result = anchors_gdf.copy()
    result["corridor_group"] = labels.astype(int)
    return result
