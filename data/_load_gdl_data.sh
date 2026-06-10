#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Source central configuration from project root
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Build the connection string
PG_CONN="host=$DB_HOST port=$DB_PORT dbname=$DB_NAME user=$DB_USER"
PG_CONN_URI="dbname=$DB_NAME user=$DB_USER host=$DB_HOST"

echo "========================================"
echo " Starting Data Import Process"
echo "========================================"

echo "[1/9] Securing PostgreSQL password file..."
chmod 600 ~/.pgpass

echo "[2/9] Importing GTFS Stops..."
ogr2ogr -f "PostgreSQL" \
  PG:"$PG_CONN" \
  -nln raw.gtfs_stops \
  -lco FID=gid \
  -overwrite \
  "CSV:stops.txt"

echo "[3/9] Importing Linea 4 GeoJSON..."
ogr2ogr -f "PostgreSQL" \
  PG:"$PG_CONN" \
  linea4.geojson \
  -nln raw.linea4 \
  -lco GEOMETRY_NAME=geom \
  -lco FID=gid \
  -overwrite \
  -nlt PROMOTE_TO_MULTI

echo "[4/9] Importing GTFS Routes..."
ogr2ogr -f "PostgreSQL" PG:"$PG_CONN" -nln raw.gtfs_routes -overwrite "CSV:routes.txt"

echo "[5/9] Importing GTFS Trips..."
ogr2ogr -f "PostgreSQL" PG:"$PG_CONN" -nln raw.gtfs_trips -overwrite "CSV:trips.txt"

echo "[6/9] Importing GTFS Shapes..."
ogr2ogr -f "PostgreSQL" PG:"$PG_CONN" -nln raw.gtfs_shapes -overwrite "CSV:shapes.txt"

echo "[7/9] Importing AGEB GeoPackage..."
ogr2ogr -f "PostgreSQL" \
  PG:"$PG_CONN" \
  ageb_zmg_2020_v2.gpkg \
  -nln raw.ageb \
  -lco GEOMETRY_NAME=geom \
  -lco FID=gid \
  -overwrite \
  -nlt PROMOTE_TO_MULTI \
  ageb_zmg_2020_v2

echo "[8/9] Importing DENUE staging data..."
ogr2ogr -f "PostgreSQL" \
  PG:"$PG_CONN_URI" \
  INEGI_DENUE_UTF8.csv \
  -nln raw.denue_staging \
  -oo AUTODETECT_TYPE=YES \
  -oo EMPTY_STRING_AS_NULL=YES \
  -overwrite

echo "[9/9] Importing Raster DEM..."
raster2pgsql -s 6372 -I -C -M -t 100x100 continuonacional_15m.tif raw.dem | psql -d "$DB_NAME" -U "$DB_USER" -h "$DB_HOST"

echo "========================================"
echo " Data Import Completed Successfully!"
echo "========================================"