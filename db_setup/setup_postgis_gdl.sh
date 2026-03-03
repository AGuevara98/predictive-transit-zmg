#!/usr/bin/env bash
# setup_postgis_gdl.sh
# Fully sets up PostgreSQL + PostGIS on Ubuntu/WSL, creates DB, user, schemas, and baseline metadata tables.
#
# Usage:
#   sudo bash setup_postgis_gdl.sh
#
# Configuration is sourced from ../config.sh. Override via environment variables:
#   DB_NAME=gdl_metro DB_USER=aguevara DB_PASS=change_me sudo bash setup_postgis_gdl.sh
#
# Notes:
# - This script is idempotent (safe to run multiple times).
# - It configures password auth for localhost (recommended for QGIS/ogr2ogr).
# - It does NOT open PostgreSQL to external networks.

set -euo pipefail

# Source central configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${SCRIPT_DIR}/config.sh"

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: Run as root (sudo)."
  exit 1
fi

echo "[1/7] Updating packages..."
apt-get update -y
apt-get install -y ca-certificates gnupg lsb-release

echo "[2/7] Installing PostgreSQL + PostGIS..."
apt-get install -y postgresql postgresql-contrib postgis postgresql-postgis

echo "[3/7] Starting PostgreSQL service..."
service postgresql start

# Detect installed PostgreSQL major version and config directory
PG_VER="$(psql -V | awk '{print $3}' | cut -d. -f1)"
PG_CONF_DIR="/etc/postgresql/${PG_VER}/main"
PG_HBA="${PG_CONF_DIR}/pg_hba.conf"

if [[ ! -f "${PG_HBA}" ]]; then
  echo "ERROR: Could not find pg_hba.conf at ${PG_HBA}"
  exit 1
fi

echo "[4/7] Ensuring localhost password auth in pg_hba.conf..."
# Ensure localhost uses password auth (md5 or scram). We'll use scram-sha-256 if present, else md5 is acceptable.
# We add entries if missing; we do not remove existing ones.
grep -qE '^\s*host\s+all\s+all\s+127\.0\.0\.1/32\s+' "${PG_HBA}" || \
  echo "host    all             all             127.0.0.1/32            scram-sha-256" >> "${PG_HBA}"

grep -qE '^\s*host\s+all\s+all\s+::1/128\s+' "${PG_HBA}" || \
  echo "host    all             all             ::1/128                 scram-sha-256" >> "${PG_HBA}"

# Keep local peer auth for terminal convenience; QGIS/ogr2ogr will use host=localhost with password.
service postgresql restart

echo "[5/7] Creating role/user and database, enabling PostGIS..."
# Create role if missing, set password, create DB if missing, and install extensions + schemas.
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN;
  END IF;
END
\$\$;

ALTER ROLE ${DB_USER} WITH PASSWORD '${DB_PASS}';

-- Create DB if it doesn't exist
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}') THEN
    CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
  END IF;
END
\$\$;
SQL

sudo -u postgres psql -d "${DB_NAME}" -v ON_ERROR_STOP=1 <<SQL
-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS base;
CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS features;

-- Canonical SRID setting
CREATE TABLE IF NOT EXISTS meta.settings (
  key text PRIMARY KEY,
  value text NOT NULL
);
INSERT INTO meta.settings(key, value)
VALUES ('canonical_srid', '${CANONICAL_SRID}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Dataset registry (optional but useful for thesis reproducibility)
CREATE TABLE IF NOT EXISTS meta.dataset_registry (
  dataset_name text PRIMARY KEY,
  source text,
  loaded_at timestamptz DEFAULT now(),
  raw_table text,
  base_table text,
  source_srid int,
  target_srid int DEFAULT ${CANONICAL_SRID},
  notes text
);
SQL

echo "[6/7] Creating ~/.pgpass for the invoking user (for ogr2ogr), if possible..."
# Create pgpass for the non-root user that invoked sudo, so ogr2ogr can connect without prompting.
if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  HOME_DIR="$(getent passwd "${SUDO_USER}" | cut -d: -f6)"
  PGPASS_FILE="${HOME_DIR}/.pgpass"
  LINE="${DB_HOST}:${DB_PORT}:${DB_NAME}:${DB_USER}:${DB_PASS}"

  # Add or replace line for this DB/user combo
  touch "${PGPASS_FILE}"
  chmod 600 "${PGPASS_FILE}"
  chown "${SUDO_USER}:${SUDO_USER}" "${PGPASS_FILE}"

  # Remove any existing matching entry (host:port:db:user:*)
  grep -vE "^${DB_HOST//./\\.}:${DB_PORT}:${DB_NAME}:${DB_USER}:" "${PGPASS_FILE}" > "${PGPASS_FILE}.tmp" || true
  echo "${LINE}" >> "${PGPASS_FILE}.tmp"
  mv "${PGPASS_FILE}.tmp" "${PGPASS_FILE}"
  chmod 600 "${PGPASS_FILE}"
  chown "${SUDO_USER}:${SUDO_USER}" "${PGPASS_FILE}"

  echo "  Wrote ${PGPASS_FILE} (permissions 600)."
else
  echo "  Skipped ~/.pgpass creation (no SUDO_USER)."
fi

echo "[7/7] Connectivity test (password auth) ..."
# Test host-based password auth using PGPASSWORD to avoid interactive prompts
export PGPASSWORD="${DB_PASS}"
psql "host=${DB_HOST} port=${DB_PORT} dbname=${DB_NAME} user=${DB_USER}" -v ON_ERROR_STOP=1 -c "SELECT PostGIS_Version();" >/dev/null
psql "host=${DB_HOST} port=${DB_PORT} dbname=${DB_NAME} user=${DB_USER}" -v ON_ERROR_STOP=1 -c "SELECT value AS canonical_srid FROM meta.settings WHERE key='canonical_srid';" >/dev/null
unset PGPASSWORD

echo "OK: PostGIS database '${DB_NAME}' ready."
echo "Connection string:"
echo "  host=${DB_HOST} port=${DB_PORT} dbname=${DB_NAME} user=${DB_USER}"