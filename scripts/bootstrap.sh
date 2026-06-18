#!/bin/bash
# Build the full gdl_metro DB from a fresh clone.
# Prereqs: PostgreSQL+PostGIS running; committed data/ inputs present.
# DEM (continuonacional_15m.tif, 7GB) is optional -- see data/download_dem.sh.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "${SCRIPT_DIR}/config.sh"
cd "${SCRIPT_DIR}"

echo "[1/4] Creating DB + PostGIS extensions (idempotent)..."
createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null || echo "  db exists, continuing"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  -c "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS postgis_raster;"

echo "[2/4] Applying schema (DDL.sql)..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f db_setup/DDL.sql

echo "[3/4] Loading GTFS / AGEB / DENUE / DEM (if present)..."
( cd data && bash _load_gdl_data.sh )

echo "[4/4] Building features.nppv_features (osmnx may download on first run)..."
python src/build_nppv_features.py

echo "[DONE] gdl_metro ready. Run: python src/run_w1.py"
