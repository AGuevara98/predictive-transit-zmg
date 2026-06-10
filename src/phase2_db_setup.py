"""
Phase 2 – Step 1: Database Schema Setup & Raw Data Ingestion
=============================================================
"""

import sys
import pandas as pd
import geopandas as gpd
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI, CRS_CANONICAL

ENGINE = create_engine(PG_URI)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS raw.indicators (
    cve_ageb    VARCHAR(15) PRIMARY KEY,
    im_2020     NUMERIC,
    gm_2020     VARCHAR(30),
    irs_2020    NUMERIC,
    grs_2020    VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS raw.denue_nppv (
    id              SERIAL PRIMARY KEY,
    clee            VARCHAR(50),
    nombre          VARCHAR(255),
    clase_actividad VARCHAR(255),
    estrato         VARCHAR(50),
    sector_id       VARCHAR(10),
    subsector_id    VARCHAR(10),
    rama_id         VARCHAR(10),
    longitud        NUMERIC,
    latitud         NUMERIC,
    ageb_cve        VARCHAR(15),
    manzana         VARCHAR(10),
    area_geo        VARCHAR(20),
    geom            geometry(Point, 6372)
);

CREATE TABLE IF NOT EXISTS raw.ridership (
    id          SERIAL PRIMARY KEY,
    anio        INTEGER,
    id_mes      INTEGER,
    transporte  VARCHAR(100),
    variable    VARCHAR(100),
    cvegeo      VARCHAR(20),
    cve_ent     INTEGER,
    cve_mun     INTEGER,
    valor       NUMERIC,
    estatus     VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS raw.osm_intersections (
    osmid       BIGINT PRIMARY KEY,
    street_count INTEGER,
    geom        geometry(Point, 6372)
);

CREATE TABLE IF NOT EXISTS raw.osm_edges (
    id          SERIAL PRIMARY KEY,
    u           BIGINT,
    v           BIGINT,
    length      NUMERIC,
    highway     VARCHAR(100),
    geom        geometry(LineString, 6372)
);

CREATE TABLE IF NOT EXISTS raw.viirs_ageb (
    cve_ageb    VARCHAR(15) PRIMARY KEY,
    ntl_median  NUMERIC,
    ntl_mean    NUMERIC,
    ntl_max     NUMERIC
);

CREATE TABLE IF NOT EXISTS features.nppv_features (
    cve_ageb                VARCHAR(15) PRIMARY KEY,
    n_intersections         NUMERIC,
    n_street_density        NUMERIC,
    n_intersection_density  NUMERIC,
    p_poi_density           NUMERIC,
    p_employment_proxy      NUMERIC,
    p_retail_density        NUMERIC,
    p_service_density       NUMERIC,
    p_land_use_mix          NUMERIC,
    pe_population           NUMERIC,
    pe_pop_density          NUMERIC,
    pe_marginacion          NUMERIC,
    pe_rezago               NUMERIC,
    pe_dep_ratio            NUMERIC,
    pe_youth_share          NUMERIC,
    v_ntl_median            NUMERIC,
    v_ridership_annual      NUMERIC,
    n_intersections_n       NUMERIC,
    n_street_density_n      NUMERIC,
    n_intersection_density_n NUMERIC,
    p_poi_density_n         NUMERIC,
    p_employment_proxy_n    NUMERIC,
    p_retail_density_n      NUMERIC,
    p_service_density_n     NUMERIC,
    p_land_use_mix_n        NUMERIC,
    pe_population_n         NUMERIC,
    pe_pop_density_n        NUMERIC,
    pe_marginacion_n        NUMERIC,
    pe_rezago_n             NUMERIC,
    pe_dep_ratio_n          NUMERIC,
    pe_youth_share_n        NUMERIC,
    v_ntl_median_n          NUMERIC,
    v_ridership_annual_n    NUMERIC,
    geom                    geometry(MultiPolygon, 6372)
);

CREATE INDEX IF NOT EXISTS idx_nppv_geom ON features.nppv_features USING gist(geom);
"""


def setup_schema():
    print("\n" + "="*70)
    print("PHASE 2 - STEP 1: DATABASE SCHEMA SETUP")
    print("="*70)
    with ENGINE.begin() as conn:
        conn.execute(text(DDL))
    print("[OK] Schema ready.")


def ingest_indicators():
    print("\n[Step] Ingesting socioeconomic indicators...")
    df = pd.read_csv("data/raw/census/zmg_indicators_combined.csv")
    df.columns = [c.lower() for c in df.columns]
    df["cve_ageb"] = df["cve_ageb"].astype(str).str.zfill(13)

    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM raw.indicators"))
        df.to_sql("indicators", conn, schema="raw", if_exists="append",
                  index=False, method="multi")

    print(f"  [OK] {len(df):,} indicator rows loaded.")


def ingest_ridership():
    print("\n[Step] Ingesting ridership data...")
    df = pd.read_csv("data/raw/ridership/jalisco_ridership_etup.csv")
    df.columns = [c.lower() for c in df.columns]

    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM raw.ridership"))
        df.to_sql("ridership", conn, schema="raw", if_exists="append",
                  index=False, method="multi")

    print(f"  [OK] {len(df):,} ridership rows loaded.")


def ingest_denue():
    print("\n[Step] Ingesting DENUE establishments...")
    df = pd.read_csv(
        "data/raw/denue/zmg_denue_combined.csv",
        usecols=["CLEE", "Nombre", "Clase_actividad", "Estrato",
                 "SECTOR_ACTIVIDAD_ID", "SUBSECTOR_ACTIVIDAD_ID",
                 "RAMA_ACTIVIDAD_ID", "Longitud", "Latitud",
                 "AGEB", "Manzana", "AreaGeo"],
        dtype=str
    )
    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={
        "sector_actividad_id": "sector_id",
        "subsector_actividad_id": "subsector_id",
        "rama_actividad_id": "rama_id",
        "ageb": "ageb_cve",
        "areageo": "area_geo"
    })
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df["latitud"]  = pd.to_numeric(df["latitud"],  errors="coerce")
    df = df.dropna(subset=["longitud", "latitud"])

    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.longitud, df.latitud), crs="EPSG:4326"
    ).to_crs(CRS_CANONICAL)

    # Drop raw coord columns to avoid confusion; keep geom from GeoDataFrame
    gdf = gdf.drop(columns=["longitud", "latitud"])

    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM raw.denue_nppv"))

    gdf.rename_geometry("geom").to_postgis(
        "denue_nppv", ENGINE, schema="raw", if_exists="append",
        index=False, chunksize=2000
    )
    print(f"  [OK] {len(gdf):,} DENUE rows loaded.")


def ingest_osm():
    print("\n[Step] Ingesting OSM network...")

    nodes = gpd.read_file("data/raw/osm/zmg_nodes.gpkg").to_crs(CRS_CANONICAL)
    intersections = nodes[nodes["street_count"] >= 3][["osmid", "street_count", "geometry"]].copy()

    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM raw.osm_intersections"))

    intersections.rename_geometry("geom").to_postgis(
        "osm_intersections", ENGINE, schema="raw", if_exists="append",
        index=False, chunksize=2000
    )
    print(f"  [OK] {len(intersections):,} intersection nodes loaded.")

    edges = gpd.read_file("data/raw/osm/zmg_edges.gpkg").to_crs(CRS_CANONICAL)

    # Force all geometries to LineString (drop non-linestring entries)
    edges = edges[edges.geometry.geom_type == "LineString"]
    edge_out = edges[["u", "v", "length", "highway", "geometry"]].copy()

    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM raw.osm_edges"))

    edge_out.rename_geometry("geom").to_postgis(
        "osm_edges", ENGINE, schema="raw", if_exists="append",
        index=False, chunksize=2000
    )
    print(f"  [OK] {len(edge_out):,} edge rows loaded.")


if __name__ == "__main__":
    setup_schema()
    ingest_indicators()
    ingest_ridership()
    ingest_denue()
    ingest_osm()
    print("\n[DONE] Phase 2 Step 1 complete - all raw data loaded.")
