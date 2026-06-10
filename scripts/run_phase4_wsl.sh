#!/bin/bash
# Phase 3 Report & Phase 4 WSL Runner
set -e

VENV="/home/aguevara/venv_thesis"
PROJ="/mnt/c/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg"

cd "$PROJ"
export PGHOST="/var/run/postgresql"
export PYTHONPATH="$PROJ"

echo "============================================================"
echo "Executing Phase 3 Report Generator"
echo "============================================================"
$VENV/bin/python src/phase3_report.py

echo ""
echo "============================================================"
echo "Executing Phase 4 Clustering"
echo "============================================================"
$VENV/bin/python src/phase4_clustering.py

echo ""
echo "============================================================"
echo "Executing Phase 4 Report Generator"
echo "============================================================"
$VENV/bin/python src/phase4_report.py
