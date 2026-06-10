#!/bin/bash
# Phase 3 WSL Runner
# Runs Phase 3 scripts inside WSL using the Unix socket for PostgreSQL.
set -e

VENV="/home/aguevara/venv_thesis"
PROJ="/mnt/c/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg"

cd "$PROJ"
export PGHOST="/var/run/postgresql"
export PYTHONPATH="$PROJ"

echo "============================================================"
echo "Executing Phase 3 (Weighting) in WSL Python Environment"
echo "============================================================"
$VENV/bin/python src/phase3_weighting.py
