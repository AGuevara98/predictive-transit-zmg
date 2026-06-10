#!/bin/bash
# Phase 6 WSL Runner
set -e

VENV="/home/aguevara/venv_thesis"
PROJ="/mnt/c/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg"

cd "$PROJ"
export PYTHONPATH="$PROJ"

echo "============================================================"
echo "Executing Phase 6: Final Synthesis Report"
echo "============================================================"
$VENV/bin/python src/phase6_synthesis.py

echo "Phase 6 Complete!"
