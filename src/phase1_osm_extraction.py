import osmnx as ox
import geopandas as gpd
import pandas as pd
from pathlib import Path
import sys
import os

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ZMG_MUNICIPALITIES, CRS_CANONICAL, CRS_WGS84

def extract_osm_data(output_dir="data/raw/osm"):
    """
    Extract street network and intersections from OSM for ZMG municipalities.
    """
    print("\n" + "="*70)
    print("PHASE 1: OSM DATA EXTRACTION")
    print("="*70)
    
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Extract Network for each municipality
    all_nodes = []
    all_edges = []
    
    for muni in ZMG_MUNICIPALITIES:
        print(f"Extracting OSM network for: {muni}...")
        try:
            # Get graph
            G = ox.graph_from_place(muni, network_type='drive')
            
            # Convert to GeoDataFrames
            nodes, edges = ox.graph_to_gdfs(G)
            
            # Add municipality metadata
            nodes['municipality'] = muni
            edges['municipality'] = muni
            
            all_nodes.append(nodes)
            all_edges.append(edges)
            print(f"  [OK] Nodes: {len(nodes)}, Edges: {len(edges)}")
            
        except Exception as e:
            print(f"  [ERR] Failed to extract {muni}: {e}")
            
    if not all_nodes:
        print("ERROR: No OSM data extracted.")
        return False
    
    # Merge and project
    print("\nMerging and projecting data to canonical CRS...")
    merged_nodes = pd.concat(all_nodes)
    merged_edges = pd.concat(all_edges)
    
    # Convert to GeoDataFrame if needed (concat might lose it if not careful)
    merged_nodes = gpd.GeoDataFrame(merged_nodes, crs=CRS_WGS84)
    merged_edges = gpd.GeoDataFrame(merged_edges, crs=CRS_WGS84)
    
    # Project to Canonical CRS (EPSG:6372)
    merged_nodes_proj = merged_nodes.to_crs(CRS_CANONICAL)
    merged_edges_proj = merged_edges.to_crs(CRS_CANONICAL)
    
    # Save to GeoPackage
    nodes_out = out_path / "zmg_nodes.gpkg"
    edges_out = out_path / "zmg_edges.gpkg"
    
    print(f"Saving nodes to: {nodes_out}")
    merged_nodes_proj.to_file(nodes_out, driver="GPKG")
    
    print(f"Saving edges to: {edges_out}")
    merged_edges_proj.to_file(edges_out, driver="GPKG")
    
    print("\n[OK] OSM extraction complete!")
    return True

if __name__ == "__main__":
    extract_osm_data()
