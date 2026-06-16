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
        JOIN features.ageb_trip_ends t ON t.cve_ageb = g.cve_ageb
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
