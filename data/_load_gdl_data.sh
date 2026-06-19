#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Source central configuration from project root
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Build the connection string
PG_CONN="host=$DB_HOST port=$DB_PORT dbname=$DB_NAME user=$DB_USER"
PG_CONN_URI="dbname=$DB_NAME user=$DB_USER host=$DB_HOST"

# ogr2ogr/raster2pgsql can't prompt interactively like psql does, so they need
# PGPASSWORD or ~/.pgpass. Export PGPASSWORD when DB_PASS is set; otherwise
# fall back to ~/.pgpass (if present) or a passwordless/trust connection.
if [ -n "$DB_PASS" ]; then
  export PGPASSWORD="$DB_PASS"
fi

echo "========================================"
echo " Starting Data Import Process"
echo "========================================"

echo "[1/9] Securing PostgreSQL password file..."
if [ -f ~/.pgpass ]; then
  chmod 600 ~/.pgpass
else
  echo "  ~/.pgpass not found -- skipping (relying on PGPASSWORD or trust auth)."
fi

echo "[2/9] Importing GTFS Stops..."
ogr2ogr -f "PostgreSQL" \
  PG:"$PG_CONN" \
  -nln raw.gtfs_stops \
  -lco FID=gid \
  -lco GEOMETRY_NAME=geom \
  -oo X_POSSIBLE_NAMES=stop_lon \
  -oo Y_POSSIBLE_NAMES=stop_lat \
  -oo KEEP_GEOM_COLUMNS=NO \
  -a_srs EPSG:4326 \
  -overwrite \
  "CSV:gtfs/stops.txt"

echo "[3/9] Importing Linea 4 GeoJSON..."
ogr2ogr -f "PostgreSQL" \
  PG:"$PG_CONN" \
  linea_4.geojson \
  -nln raw.linea4 \
  -lco GEOMETRY_NAME=geom \
  -lco FID=gid \
  -overwrite \
  -nlt PROMOTE_TO_MULTI

echo "[4/9] Importing GTFS Routes..."
ogr2ogr -f "PostgreSQL" PG:"$PG_CONN" -nln raw.gtfs_routes -overwrite "CSV:gtfs/routes.txt"

echo "[5/9] Importing GTFS Trips..."
ogr2ogr -f "PostgreSQL" PG:"$PG_CONN" -nln raw.gtfs_trips -overwrite "CSV:gtfs/trips.txt"

echo "[6/9] Importing GTFS Shapes..."
ogr2ogr -f "PostgreSQL" PG:"$PG_CONN" -nln raw.gtfs_shapes -overwrite "CSV:gtfs/shapes.txt"

echo "[7/9] Importing AGEB GeoPackage..."
ogr2ogr -f "PostgreSQL" \
  PG:"$PG_CONN" \
  ageb_zmg_2020_v2.gpkg \
  -nln raw.ageb \
  -lco GEOMETRY_NAME=geom \
  -lco FID=gid \
  -overwrite \
  -nlt PROMOTE_TO_MULTI \
  zmg

echo "[8/9] Importing DENUE staging data..."
ogr2ogr -f "PostgreSQL" \
  PG:"$PG_CONN_URI" \
  INEGI_DENUE_UTF8.csv \
  -nln raw.denue_staging \
  -oo AUTODETECT_TYPE=YES \
  -oo EMPTY_STRING_AS_NULL=YES \
  -overwrite

echo "[9/9] Importing Raster DEM..."
if [ -f continuonacional_15m.tif ]; then
  # Source raster is geographic EPSG:6365 (Mexico ITRF2008), confirmed via
  # gdalinfo -- NOT EPSG:6372. raster2pgsql only tags SRID metadata, it does
  # not reproject, so this must match the file's true CRS or every spatial
  # join against base.ageb (EPSG:6372) silently returns zero matches.
  raster2pgsql -d -s 6365 -I -C -M -t 100x100 continuonacional_15m.tif raw.dem | psql -d "$DB_NAME" -U "$DB_USER" -h "$DB_HOST"
else
  echo "[9/9] DEM raster continuonacional_15m.tif not found - skipping (slope_mean will COALESCE to 0)."
fi

echo "========================================"
echo " Data Import Completed Successfully!"
echo "========================================"