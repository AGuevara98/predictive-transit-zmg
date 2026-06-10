#!/bin/bash
# Phase 2 WSL Runner
# Runs Phase 2 scripts inside WSL using the Unix socket for PostgreSQL.
set -e

VENV="/home/aguevara/venv_thesis"
PROJ="/mnt/c/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg"

cd "$PROJ"
export PGHOST="/var/run/postgresql"
export PYTHONPATH="$PROJ"

echo "============================================================"
echo "PHASE 2 – Step 1: DB Schema Setup & Raw Data Ingestion"
echo "============================================================"
$VENV/bin/python src/phase2_db_setup.py

echo ""
echo "============================================================"
echo "PHASE 2 – Step 2: Feature Engineering"
echo "============================================================"
$VENV/bin/python src/phase2_feature_engineering.py

echo ""
echo "============================================================"
echo "PHASE 2 COMPLETE"
echo "============================================================"
