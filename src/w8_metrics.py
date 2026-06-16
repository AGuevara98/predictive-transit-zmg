"""
W8 Validation Metrics
=====================
Pure functions for computing coverage rate, Gini coefficient, and
population-served-per-km. No DB writes; all inputs are DataFrames/GeoDataFrames.
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CRS_CANONICAL


def gini_coefficient(values: np.ndarray) -> float:
    """Gini coefficient of an array of non-negative values. Returns 0 for empty/all-zero arrays."""
    vals = np.asarray(values, dtype=float).flatten()
    vals = vals[~np.isnan(vals)]
    if len(vals) == 0 or vals.sum() == 0:
        return 0.0
    vals = np.sort(vals)
    n = len(vals)
    idx = np.arange(1, n + 1)
    return float((2 * np.sum(idx * vals) / (n * vals.sum())) - (n + 1) / n)


def coverage_rate(ageb_centroids_gdf: gpd.GeoDataFrame,
                  service_buffers_gdf: gpd.GeoDataFrame) -> float:
    """Fraction of AGEBs whose centroid falls within any service buffer polygon."""
    if len(ageb_centroids_gdf) == 0:
        return 0.0
    union = service_buffers_gdf.geometry.union_all()
    covered = ageb_centroids_gdf.geometry.within(union).sum()
    return float(covered) / len(ageb_centroids_gdf)


def pop_served_per_km(ageb_gdf: gpd.GeoDataFrame,
                      corridor_gdf: gpd.GeoDataFrame,
                      buffer_m: float = 400.0) -> float:
    """Population served by new corridors per route-km.

    'Served' = AGEB centroid within buffer_m of any corridor LineString.
    ageb_gdf must have a 'pe_population' column.
    corridor_gdf must have a 'route_km' column.
    """
    if len(corridor_gdf) == 0:
        return 0.0
    if "route_km" not in corridor_gdf.columns or corridor_gdf["route_km"].sum() == 0:
        return 0.0
    total_km = float(corridor_gdf["route_km"].sum())
    union_buf = corridor_gdf.geometry.union_all().buffer(buffer_m)
    served = ageb_gdf[ageb_gdf.geometry.within(union_buf)]
    total_pop = float(served["pe_population"].sum())
    return total_pop / total_km


def compute_before_after_metrics(engine, corridor_geojson_path: Path,
                                 buffer_m: float = 400.0) -> dict:
    """Compute before/after coverage rate, Gini, and pop-served/km for W6 corridors.

    Returns a dict with keys:
      coverage_rate_before, coverage_rate_after,
      gini_before, gini_after,
      pop_served_per_km_w6,
      n_ageb_newly_served, total_population_newly_served,
      w6_total_km
    """
    # Load AGEB centroids + population + accessibility from DB
    with engine.connect() as conn:
        ageb_df = pd.read_sql(text("""
            SELECT a.cvegeo AS cve_ageb,
                   ST_X(ST_Centroid(a.geom)) AS cx,
                   ST_Y(ST_Centroid(a.geom)) AS cy,
                   COALESCE(f.pe_population, 0) AS pe_population,
                   COALESCE(ac.accessibility_score, 0) AS accessibility_score
            FROM base.ageb a
            LEFT JOIN features.nppv_features f ON f.cve_ageb = a.cvegeo
            LEFT JOIN features.ageb_accessibility ac ON ac.cve_ageb = a.cvegeo
        """), conn)

    ageb_gdf = gpd.GeoDataFrame(
        ageb_df,
        geometry=gpd.points_from_xy(ageb_df["cx"], ageb_df["cy"]),
        crs=CRS_CANONICAL,
    )

    # Load existing GTFS stop buffers as "before" service area
    with engine.connect() as conn:
        stops_df = gpd.read_postgis(
            "SELECT geom FROM base.gtfs_stops",
            conn, geom_col="geom", crs=CRS_CANONICAL,
        )
    gtfs_service = gpd.GeoDataFrame(
        geometry=stops_df.geometry.buffer(buffer_m),
        crs=CRS_CANONICAL,
    )

    # Load W6 corridors
    corridor_gdf = gpd.read_file(corridor_geojson_path).to_crs(CRS_CANONICAL)
    if "feasible" in corridor_gdf.columns:
        feasible = corridor_gdf[corridor_gdf["feasible"].astype(bool)].copy()
    else:
        feasible = corridor_gdf.copy()
    if "route_km" not in feasible.columns:
        feasible["route_km"] = feasible.geometry.length / 1000.0

    w6_union_geom = feasible.geometry.union_all().buffer(buffer_m) if len(feasible) > 0 else None

    combined_geom = (
        gtfs_service.geometry.union_all().union(w6_union_geom)
        if w6_union_geom is not None
        else gtfs_service.geometry.union_all()
    )
    combined_service_gdf = gpd.GeoDataFrame(geometry=[combined_geom], crs=CRS_CANONICAL)

    rate_before = coverage_rate(ageb_gdf, gtfs_service)
    rate_after = coverage_rate(ageb_gdf, combined_service_gdf)
    gini_before = gini_coefficient(ageb_df["accessibility_score"].values)

    # After Gini: newly-served AGEBs (zero accessibility, within 400m of W6) get mean of currently-served
    served_scores = ageb_df.loc[ageb_df["accessibility_score"] > 0, "accessibility_score"]
    mean_served = float(served_scores.mean()) if len(served_scores) > 0 else 0.0
    acc_after = ageb_df["accessibility_score"].copy()
    if w6_union_geom is not None:
        newly_served_mask = (ageb_df["accessibility_score"] == 0) & ageb_gdf.geometry.within(w6_union_geom)
        acc_after.loc[newly_served_mask] = mean_served
    gini_after = gini_coefficient(acc_after.values)

    pop_km = pop_served_per_km(ageb_gdf, feasible, buffer_m)

    # Count newly-served AGEBs (previously unserved only)
    if w6_union_geom is not None:
        newly_served_mask = (ageb_df["accessibility_score"] == 0) & ageb_gdf.geometry.within(w6_union_geom)
        n_newly = int(newly_served_mask.sum())
        pop_newly = float(ageb_df.loc[newly_served_mask, "pe_population"].sum())
    else:
        n_newly = 0
        pop_newly = 0.0

    return {
        "coverage_rate_before": rate_before,
        "coverage_rate_after": rate_after,
        "gini_before": gini_before,
        "gini_after": gini_after,
        "pop_served_per_km_w6": pop_km,
        "n_ageb_newly_served": n_newly,
        "total_population_newly_served": pop_newly,
        "w6_total_km": float(feasible["route_km"].sum()) if len(feasible) > 0 else 0.0,
    }
