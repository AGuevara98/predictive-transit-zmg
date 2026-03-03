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
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-gdl_metro}"
export DB_USER="${DB_USER:-aguevara}"
export DB_PASS="${DB_PASS:-550800}"

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
