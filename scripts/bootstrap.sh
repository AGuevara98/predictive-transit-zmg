#!/bin/bash
# Build the full gdl_metro DB from a fresh clone.
# Prereqs: PostgreSQL+PostGIS running; the role you connect as ($DB_USER) must be
# able to create the database OR already own it -- a superuser role is simplest.
# Override the role/password with env vars: export PG_USER=<you> PG_PASS=<pw>
# DEM (continuonacional_15m.tif, 7GB) is optional -- see data/download_dem.sh.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "${SCRIPT_DIR}/config.sh"
cd "${SCRIPT_DIR}"

# ON_ERROR_STOP makes psql exit non-zero on the FIRST SQL error (without it,
# psql returns 0 even after dozens of errors and the build marches on blindly).
PSQL=(psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER")

priv_hint() {
  echo "[ERR] $1 failed for role '$DB_USER' on database '$DB_NAME'."
  echo "      This is almost always a privileges/ownership problem: '$DB_USER' must"
  echo "      OWN '$DB_NAME' (and its schemas) to create objects in it."
  echo "      Fix one of:"
  echo "        - Build under your own superuser role:"
  echo "            export PG_USER=<you> PG_PASS=<pw>; bash scripts/bootstrap.sh"
  echo "        - Fresh DB (only if it has no data to keep):"
  echo "            dropdb -h $DB_HOST -U <you> $DB_NAME && bash scripts/bootstrap.sh"
  echo "        - Transfer ownership as a superuser (psql):"
  echo "            ALTER DATABASE $DB_NAME OWNER TO $DB_USER;"
  exit 1
}

echo "[1/4] Creating DB + schemas + PostGIS extensions..."
if createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null; then
  echo "  created database '$DB_NAME' (owned by '$DB_USER')."
else
  echo "  database '$DB_NAME' already exists -- continuing (it must be owned by '$DB_USER')."
fi
# Schemas are created here (not just in DDL.sql) because the data-load step
# below needs raw.* to exist before ogr2ogr -nln raw.<table> can target it.
"${PSQL[@]}" -d "$DB_NAME" \
  -c "CREATE SCHEMA IF NOT EXISTS raw; CREATE SCHEMA IF NOT EXISTS base; CREATE SCHEMA IF NOT EXISTS features; CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS postgis_raster;" \
  || priv_hint "Schema/extension creation"

echo "[2/4] Loading GTFS / AGEB / DENUE / DEM (if present)..."
( cd data && bash _load_gdl_data.sh )

echo "[3/4] Applying schema (DDL.sql)..."
"${PSQL[@]}" -d "$DB_NAME" -f db_setup/DDL.sql || priv_hint "Schema creation"

echo "[4/4] Building features.nppv_features (osmnx may download on first run)..."
python src/build_nppv_features.py

echo "[DONE] gdl_metro ready. Run: python src/run_w1.py"
