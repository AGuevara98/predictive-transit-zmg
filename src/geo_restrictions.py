import osmnx as ox
import geopandas as gpd
import pandas as pd
import sys
from pathlib import Path

# Add project root to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ZMG_MUNICIPALITIES, CRS_CANONICAL

target_crs = CRS_CANONICAL

print("Geocoding municipal boundaries...")
# 2. Get boundaries for all and dissolve into one study area polygon
# We use .dissolve() to create a single boundary for spatial queries [3]
metro_boundary_gdf = ox.geocode_to_gdf(ZMG_MUNICIPALITIES)
unified_boundary = metro_boundary_gdf.unary_union 

print("Extracting Santiago River and water bodies...")
# 3. Extract Santiago River (Water Bodies)
river_tags = {"waterway": "river", "natural": "water"}
river = ox.features_from_polygon(unified_boundary, tags=river_tags).to_crs(target_crs)

print("Extracting Protected Areas...")
# 4. Extract Protected Areas (Forests like Bosque de la Primavera)
protected_tags = {"boundary": "protected_area", "leisure": "nature_reserve"}
protected_areas = ox.features_from_polygon(unified_boundary, tags=protected_tags).to_crs(target_crs)

print("Extracting Drivable Street Hierarchy...")
# 5. Extract Routable Street Hierarchy
# Using graph_from_polygon is more reliable for large/complex areas [2]
G = ox.graph_from_polygon(unified_boundary, network_type='drive', simplify=True)
nodes, edges = ox.graph_to_gdfs(G)
edges = edges.to_crs(target_crs)

# --- DATA EXPORT ---
output_file = "zmg_physical_constraints_v2.gpkg"
river.to_file(output_file, layer="base_river", driver="GPKG")
protected_areas.to_file(output_file, layer="base_protected_areas", driver="GPKG")
edges.to_file(output_file, layer="base_streets", driver="GPKG")

print(f"Success. Extraction complete for 10 municipalities. Saved to {output_file}.")