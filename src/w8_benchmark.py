# src/w8_benchmark.py
"""
W8.2 -- Benchmark: W6 Corridors vs Existing SITEUR Premium Routes
=================================================================
Computes spatial overlap between W6-proposed corridors and existing
Mi Macro (BRT) + Mi Tren (light rail) route shapes.

Interpretation:
  - High overlap: W6 reproduces known high-quality corridors (validation)
  - Low overlap:  W6 identifies genuinely unserved areas (new coverage)

Both outcomes are expected and reported in the W8 report.
"""
import sys
from pathlib import Path
from typing import Set

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CRS_CANONICAL
from src.w8_backtest import compute_shape_overlap, load_premium_route_shapes

DATA_DIR = Path(__file__).parent.parent / "data" / "gtfs"
BUFFER_M = 400.0
N_SAMPLES = 200


def load_w6_corridors(geojson_path: Path) -> gpd.GeoDataFrame:
    """Load W6 corridor GeoJSON and return only feasible corridors in EPSG:6372."""
    gdf = gpd.read_file(geojson_path).to_crs(CRS_CANONICAL)
    if "feasible" in gdf.columns:
        gdf = gdf[gdf["feasible"].astype(bool)].copy()
    if "route_km" not in gdf.columns:
        gdf = gdf.copy()
        gdf["route_km"] = gdf.geometry.length / 1000.0
    return gdf.reset_index(drop=True)


def benchmark_w6_against_premium(
    corridor_gdf: gpd.GeoDataFrame,
    premium_shapes_gdf: gpd.GeoDataFrame,
    buffer_m: float = BUFFER_M,
) -> pd.DataFrame:
    """For each W6 corridor, compute its max overlap fraction with any premium route.

    Returns DataFrame: candidate_id, best_matching_premium_route, max_overlap_fraction, route_km.
    """
    records = []
    for idx, corr_row in corridor_gdf.iterrows():
        cid = corr_row.get("candidate_id", f"corridor_{idx}")
        corr_geom = corr_row.geometry
        best_route = None
        best_overlap = 0.0
        for _, route_row in premium_shapes_gdf.iterrows():
            ov = compute_shape_overlap(corr_geom, route_row.geometry, buffer_m, N_SAMPLES)
            if ov > best_overlap:
                best_overlap = ov
                best_route = route_row["route_id"]
        records.append({
            "candidate_id": cid,
            "best_matching_premium_route": best_route,
            "max_overlap_fraction": best_overlap,
            "route_km": float(corr_row.get("route_km", corr_geom.length / 1000.0)),
        })
    return pd.DataFrame(records)


def run_benchmark(
    corridor_geojson_path: Path,
    data_dir: Path = DATA_DIR,
    agency_ids: Set[str] = None,
) -> dict:
    """Run benchmark comparison and return summary dict + detail DataFrame."""
    if agency_ids is None:
        agency_ids = {"MM", "MT"}

    corridor_gdf = load_w6_corridors(corridor_geojson_path)
    print(f"  [OK] {len(corridor_gdf)} feasible W6 corridors loaded")

    premium_gdf = load_premium_route_shapes(data_dir, agency_ids)
    print(f"  [OK] {len(premium_gdf)} premium route shapes loaded")

    if len(corridor_gdf) == 0 or len(premium_gdf) == 0:
        return {
            "n_w6_corridors": len(corridor_gdf),
            "n_premium_routes": len(premium_gdf),
            "mean_w6_overlap_with_premium": 0.0,
            "w6_total_km": float(corridor_gdf["route_km"].sum()) if len(corridor_gdf) > 0 else 0.0,
            "detail": pd.DataFrame(),
        }

    detail_df = benchmark_w6_against_premium(corridor_gdf, premium_gdf)
    mean_overlap = float(detail_df["max_overlap_fraction"].mean())

    return {
        "n_w6_corridors": len(corridor_gdf),
        "n_premium_routes": len(premium_gdf),
        "mean_w6_overlap_with_premium": mean_overlap,
        "w6_total_km": float(corridor_gdf["route_km"].sum()),
        "detail": detail_df,
    }
