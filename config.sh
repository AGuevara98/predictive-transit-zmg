#!/usr/bin/env bash
# config.sh
# Central configuration file for shell scripts.
# This file exports all environment variables needed by database and data loading scripts.
#
# Source this file in your scripts:
#   source "$(dirname "$0")/config.sh"
#
# Or explicitly:
#   source ./config.sh
#
# Environment variables override defaults (recommended for production).

# =============================================================================
# Database Configuration (PostgreSQL + PostGIS)
# =============================================================================
# Set via PG_HOST/PG_PORT/PG_DB/PG_USER/PG_PASS -- the SAME names config.py
# reads, so one `export` line configures both the Python and shell sides of
# the pipeline. No personal credentials are hardcoded. PG_USER defaults to
# your OS login; PG_PASS defaults to empty so psql/ogr2ogr use ~/.pgpass,
# PGPASSWORD, or a prompt. The role must own PG_DB.
export PG_HOST="${PG_HOST:-localhost}"
export PG_PORT="${PG_PORT:-5432}"
export PG_DB="${PG_DB:-gdl_metro}"
export PG_USER="${PG_USER:-$(id -un)}"
export PG_PASS="${PG_PASS:-}"

# DB_* aliases: every shell script in this repo (bootstrap.sh,
# data/_load_gdl_data.sh, etc.) was written against DB_HOST/DB_PORT/DB_NAME/
# DB_USER/DB_PASS. Keep those working without touching each script.
export DB_HOST="$PG_HOST"
export DB_PORT="$PG_PORT"
export DB_NAME="$PG_DB"
export DB_USER="$PG_USER"
export DB_PASS="$PG_PASS"

# Canonical SRID for spatial operations
export CANONICAL_SRID="${CANONICAL_SRID:-6372}"

# =============================================================================
# Project Spatial Configuration
# =============================================================================

# Zona Metropolitana de Guadalajara (ZMG) Bounding Box
export ZMG_XMIN="-103.60"
export ZMG_YMIN="20.30"
export ZMG_XMAX="-103.10"
export ZMG_YMAX="20.90"

# =============================================================================
# External Data Sources
# =============================================================================

# Overture Maps S3 Release (POI data)
export OVERTURE_S3_PATH="s3://overturemaps-us-west-2/release/2026-02-18.0/theme=places/type=place/*"

# =============================================================================
# Feature Engineering Parameters
# =============================================================================

# Distance thresholds for accessibility features (meters)
export ACCESSIBILITY_BUFFER_SHORT="400"
export ACCESSIBILITY_BUFFER_LONG="800"
