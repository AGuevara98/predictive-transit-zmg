import logging
import duckdb
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine
import sys
from pathlib import Path

# Add project root to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI, ZMG_BBOX, OVERTURE_S3_PATH

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------
def setup_duckdb() -> duckdb.DuckDBPyConnection:
    """Initializes an in-memory DuckDB connection with required spatial and S3 extensions."""
    logging.info("Initializing DuckDB & extensions...")
    con = duckdb.connect(':memory:') # Use in-memory DB for performance
    
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET s3_region='us-west-2';")
    
    # Anonymous S3 Access for Overture
    con.execute("""
        CREATE OR REPLACE SECRET (
            TYPE S3,
            KEY_ID '',
            SECRET '',
            REGION 'us-west-2'
        );
    """)
    return con

def extract_overture_pois(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    """Extracts POIs from Overture Maps on S3, filtering by bounding box."""
    logging.info("Running Overture Extraction (this may take 1-2 minutes)...")
    
    # Query extracts directly as WKB to easily parse into GeoPandas
    query = f"""
        SELECT 
            id,
            names.primary AS name,
            basic_category AS category,
            ST_AsWKB(geometry) AS geom_wkb
        FROM read_parquet('{OVERTURE_S3_PATH}', hive_partitioning=1)
        WHERE bbox.xmin BETWEEN {ZMG_BBOX['xmin']} AND {ZMG_BBOX['xmax']}
          AND bbox.ymin BETWEEN {ZMG_BBOX['ymin']} AND {ZMG_BBOX['ymax']}
    """
    
    # Read natively into a Pandas DataFrame
    df = con.query(query).to_df()
    
    logging.info(f"Extracted {len(df)} records. Converting to GeoDataFrame...")
    
    # Convert WKB directly to GeoPandas geometry (Fastest method)
    df['geom'] = gpd.GeoSeries.from_wkb(df['geom_wkb'])
    df.drop(columns=['geom_wkb'], inplace=True)
    
    gdf = gpd.GeoDataFrame(df, geometry='geom', crs="EPSG:4326")
    return gdf

def load_to_postgis(gdf: gpd.GeoDataFrame, engine):
    """Reprojects and loads the GeoDataFrame into PostGIS."""
    logging.info("Reprojecting to EPSG:6372...")
    gdf = gdf.to_crs("EPSG:6372")
    
    logging.info("Pushing to PostGIS (features.overture_pois)...")
    gdf.to_postgis("overture_pois", engine, schema="features", if_exists="replace", index=False)
    logging.info("Successfully loaded POIs into PostGIS.")

def check_database_metadata(engine):
    """Prints current database schemas to verify ingestion."""
    logging.info("Fetching PostGIS Table Metadata...")
    
    spatial_query = """
    SELECT 
        f_table_schema AS schema_name, 
        f_table_name AS table_name, 
        f_geometry_column AS geom_column, 
        type AS geom_type, 
        srid
    FROM geometry_columns
    WHERE f_table_schema = 'features' AND f_table_name = 'overture_pois';
    """
    
    df_spatial = pd.read_sql(spatial_query, engine)
    print("\n### Target Table Meta Verification ###")
    print(df_spatial.to_markdown(index=False))

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        # 1. Setup
        con = setup_duckdb()
        pg_engine = create_engine(PG_URI)
        
        # 2. Extract & Transform
        gdf_pois = extract_overture_pois(con)
        
        # 3. Load
        if not gdf_pois.empty:
            load_to_postgis(gdf_pois, pg_engine)
            check_database_metadata(pg_engine)
        else:
            logging.warning("No POIs found in the specified bounding box.")
            
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
    finally:
        if 'con' in locals():
            con.close()