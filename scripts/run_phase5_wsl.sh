#!/bin/bash
# Phase 5 WSL Runner
set -e

VENV="/home/aguevara/venv_thesis"
PROJ="/mnt/c/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg"

cd "$PROJ"
export PGHOST="/var/run/postgresql"
export PYTHONPATH="$PROJ"

echo "============================================================"
echo "Executing Phase 5 Predictive Modeling & SHAP Interpretability"
echo "============================================================"
$VENV/bin/python src/phase5_predictive_modeling.py

echo ""
echo "============================================================"
echo "Executing Phase 5 Report Generator"
echo "============================================================"
$VENV/bin/python src/phase5_report.py

echo "Phase 5 Complete!"
