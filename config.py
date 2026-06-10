"""
Central configuration file for database credentials and project settings.

All modules should import from this file to maintain a single source of truth
for database connection strings and project-wide constants.

Credentials can be set via environment variables or defaults (DEV ONLY).
For production, use environment variables:
  - PG_USER, PG_PASS, PG_HOST, PG_PORT, PG_DB
"""

import os

# =============================================================================
# Database Configuration (PostgreSQL + PostGIS)
# =============================================================================
PG_USER = os.getenv("PG_USER", "aguevara")
PG_PASS = os.getenv("PG_PASS", "")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "gdl_metro")

# Construct connection URI for SQLAlchemy
# When running inside WSL, PGHOST env var points to the Unix socket dir.
import socket as _socket
_pg_host_override = os.getenv("PGHOST", PG_HOST)
# Detect if running in WSL (socket path override)
if _pg_host_override.startswith("/"):
    # Unix socket: postgresql+psycopg2:///dbname?host=/var/run/postgresql
    PG_URI = f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@/{PG_DB}?host={_pg_host_override}"
else:
    PG_URI = f"postgresql://{PG_USER}:{PG_PASS}@{_pg_host_override}:{PG_PORT}/{PG_DB}"

# =============================================================================
# Project Spatial Configuration
# =============================================================================

# Zona Metropolitana de Guadalajara (ZMG) Bounding Box
ZMG_BBOX = {
    "xmin": -103.60,
    "ymin": 20.30,
    "xmax": -103.10,
    "ymax": 20.90,
}

# 10 municipalities of ZMG
ZMG_MUNICIPALITIES = [
    "Guadalajara, Jalisco, Mexico",
    "Zapopan, Jalisco, Mexico",
    "San Pedro Tlaquepaque, Jalisco, Mexico",
    "Tonalá, Jalisco, Mexico",
    "Tlajomulco de Zúñiga, Jalisco, Mexico",
    "El Salto, Jalisco, Mexico",
    "Ixtlahuacán de los Membrillos, Jalisco, Mexico",
    "Juanacatlán, Jalisco, Mexico",
    "Zapotlanejo, Jalisco, Mexico",
    "Acatlán de Juárez, Jalisco, Mexico",
]

# Canonical CRS for all spatial operations in this project
CRS_CANONICAL = "EPSG:6372"  # Conic Equidistant Projection for Mexico

# CRS for external data ingestion (read-only)
CRS_WGS84 = "EPSG:4326"

# =============================================================================
# External Data Sources
# =============================================================================

# Overture Maps S3 Release (POI data)
OVERTURE_S3_PATH = (
    "s3://overturemaps-us-west-2/release/2026-02-18.0/theme=places/type=place/*"
)

# =============================================================================
# Feature Engineering Parameters
# =============================================================================

# Distance thresholds for accessibility features (meters)
ACCESSIBILITY_BUFFER_SHORT = 400
ACCESSIBILITY_BUFFER_LONG = 800

# DENUE Employment proxy by establishment size category
EMPLOYMENT_PROXY_MAP = {
    "0 a 5 personas": 0,  # Excluded from features
    "6 a 10 personas": 0,  # Excluded from features
    "11 a 30 personas": 20,
    "31 a 50 personas": 40,
    "51 a 100 personas": 75,
    "101 a 250 personas": 175,
    "251 y más personas": 500,
}

# SCIAN sector prefixes for employment stratification
SCIAN_SECTORS = {
    "manufacturing": ["31", "32", "33"],
    "retail": ["46"],
    "education": ["61"],
    "health": ["62"],
    "government": ["931"],
}

# =============================================================================
# Database Schema Configuration
# =============================================================================

DB_SCHEMAS = {
    "raw": "Raw data ingestion (no transformations)",
    "base": "Normalized, transformed, indexed tables (EPSG:6372)",
    "features": "AGEB-aggregated features for modeling",
}
# =============================================================================
# API Credentials
# =============================================================================
INEGI_TOKEN = os.getenv("INEGI_TOKEN", "")
NASA_JWT = os.getenv("NASA_JWT", "")
