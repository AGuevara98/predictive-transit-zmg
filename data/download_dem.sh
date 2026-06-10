#!/bin/bash
# Download the INEGI Continuo de Elevaciones Mexicano (CEM) 15m DEM raster
#
# File: continuonacional_15m.tif
# Size: ~7.2 GB
# CRS:  EPSG:4326 (WGS84), imported and reprojected to EPSG:6372 by the pipeline
#
# SOURCE
# ------
# INEGI – Continuo de Elevaciones Mexicano 3.0 (CEM 3.0), 15m resolution
# Download portal: https://www.inegi.org.mx/app/geo2/elevacionesmexicanas/
#
# HOW TO DOWNLOAD MANUALLY
# -------------------------
# 1. Go to https://www.inegi.org.mx/app/geo2/elevacionesmexicanas/
# 2. Select the area covering the ZMG (Jalisco state or the metro boundary)
# 3. Choose "Continuo nacional 15 m" and download the GeoTIFF
# 4. Place the file at:  data/continuonacional_15m.tif
#
# AUTOMATED DOWNLOAD (if you have a direct URL from INEGI)
# ---------------------------------------------------------
# Uncomment and set the URL below once you have it:
#
# DEM_URL="https://..."   # paste the INEGI direct download URL here
# OUTPUT="$(dirname "$0")/continuonacional_15m.tif"
#
# echo "Downloading CEM 15m DEM (~7.2 GB)..."
# wget -c -O "$OUTPUT" "$DEM_URL"
# echo "Done. File saved to $OUTPUT"

echo "See the comments in this script for manual download instructions."
echo "Portal: https://www.inegi.org.mx/app/geo2/elevacionesmexicanas/"
