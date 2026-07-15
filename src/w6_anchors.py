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
