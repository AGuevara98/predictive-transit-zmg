# predictive-transit-zmg
Master's thesis repo. Optimal public transit routes framework
## Project Overview

This is a **geospatial analysis pipeline** for identifying optimal public transit route placement opportunities in the Zona Metropolitana de Guadalajara (ZMG). The project ingests GTFS, OSM, and economic (DENUE) data to predict suitable areas (AGEBs) by analyzing employment, accessibility gaps, topography, and existing infrastructure.

## Quick Start

### Prerequisites

- **Python 3.9+** (with virtualenv)
- **PostgreSQL 14+** with **PostGIS 3.2+** (includes PostGIS raster)
- **Ubuntu/WSL** (for shell scripts; Windows users: WSL2 recommended)
- **QGIS** (optional, for spatial data inspection)
- **ogr2ogr** and **raster2pgsql** (GDAL/PostGIS tools)

### 1. Set Up Python Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2. Configure Database Credentials

All database and project settings are centralized in two files:

**For Python scripts:** Edit `config.py` at project root
```python
PG_USER = "user"
PG_PASS = "password"
PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "gdl_metro"
```

**For shell scripts:** Edit `config.sh` at project root
```bash
DB_USER="user"
DB_PASS="password"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="gdl_metro"
```

**Production:** Override via environment variables (recommended):
```bash
export PG_USER=your_user
export PG_PASS=your_password
export PG_HOST=your_host
export DB_PORT=5432
export PG_DB=gdl_metro
```

### 3. Set Up PostgreSQL + PostGIS Database

**Option A: Automated Setup (Ubuntu/WSL)**

```bash
sudo bash db_setup/setup_postgis_gdl.sh
```

This script will:
- Install PostgreSQL and PostGIS
- Create database user and database
- Enable PostGIS extensions
- Create schemas (raw, base, features, meta)
- Configure password authentication for localhost
- Generate `.pgpass` file for passwordless tool access

Customize with environment variables:
```bash
DB_NAME=gdl_metro DB_USER=user DB_PASS=change_me sudo bash db_setup/setup_postgis_gdl.sh
```

**Option B: Manual Setup**

```bash
# Create database and user
createdb -U postgres gdl_metro
psql -U postgres -d gdl_metro -c "CREATE ROLE user WITH LOGIN PASSWORD 'password';"
psql -U postgres -d gdl_metro -c "ALTER DATABASE gdl_metro OWNER TO user;"

# Enable extensions
psql -U user -d gdl_metro -c "CREATE EXTENSION postgis;"
psql -U user -d gdl_metro -c "CREATE EXTENSION postgis_raster;"

# Create schemas
psql -U user -d gdl_metro -f db_setup/DDL.sql
```

### 4. Load Source Data

Place all source files in the `data/` directory:
- `stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt`, `shapes.txt`, `calendar.txt`, `frequencies.txt` (GTFS)
- `INEGI_DENUE_UTF8.csv` (DENUE economic data)
- `ageb_zmg_2020_v2.gpkg` (AGEB boundaries)
- `linea_4.geojson` (Line 4 rail geometry)
- `continuonacional_15m.tif` (DEM raster for slope calculations)

Then run the data loader:

```bash
cd data
bash _load_gdl_data.sh
cd ..
```

This script will:
- Import GTFS files (stops, routes, trips, shapes)
- Load AGEB boundaries (GeoPackage)
- Import DENUE economic establishments (CSV)
- Load Line 4 rail geometry (GeoJSON)
- Import DEM raster for topography analysis

Customize database connection:
```bash
DB_USER=my_user DB_PASS=my_pass DB_HOST=db.example.com bash data/_load_gdl_data.sh
```

### 5. Run Feature Engineering Pipeline

Execute the SQL feature engineering queries from the database setup:

```bash
psql -U user -d gdl_metro -f db_setup/DDL.sql
```

This materializes:
- **features.ageb_accessibility**: Stop counts at 400m/800m buffers
- **features.ageb_employment**: Employment proxies aggregated by SCIAN sector
- **features.ageb_topography**: Mean slope from DEM
- **features.ageb_route_supply**: Transit kilometers within 800m
- **features.master_suitability**: Master table joining all features by AGEB

### 6. Verify Database Setup

```bash
psql -U user -d gdl_metro -c "SELECT PostGIS_Version();"
psql -U user -d gdl_metro -c "SELECT table_name FROM information_schema.tables WHERE table_schema IN ('raw', 'base', 'features');"
```

## Predictive Framework: Six-Phase Pipeline

This project implements a data-driven **NPP-V (Node-Place-People-Vitality)** framework applied to 2,068 AGEBs across the ZMG. All weights are computed objectively — no expert subjectivity.

### Phase 1: Data Acquisition

**Goal:** Ingest all raw geospatial, socioeconomic, and transit data into the database.

```bash
python src/run_phase1.py

# Individual components:
python src/phase1_osm_extraction.py        # OSM street network & POIs
python src/phase1_denue_acquisition.py     # DENUE economic establishments
python src/phase1_census_indicators.py     # INEGI Census (population, marginalization)
python src/phase1_viirs_acquisition.py     # NASA VIIRS night-time light raster
python src/phase1_ridership_acquisition.py # GTFS ridership data
python src/phase1_report.py                # Phase 1 summary report
```

**Outputs:**
- Raw tables in `raw` schema: OSM streets/POIs, DENUE establishments, Census AGEBs, VIIRS raster, GTFS feeds
- `outputs/phase1/phase1_report.md`

### Phase 2: Feature Engineering

**Goal:** Normalize and engineer 16 NPP-V features at the AGEB level.

```bash
python src/run_phase2.py

# Individual components:
python src/phase2_db_setup.py          # Initialize feature schema
python src/phase2_feature_engineering.py  # Compute all 16 NPP-V features
python src/phase2_train_models.py      # Train RF + LightGBM classifiers
python src/phase2_predict_surface.py   # Score all AGEBs
python src/phase2_shap_analysis.py     # SHAP global feature importance
python src/phase2_report.py            # Phase 2 report
```

**Outputs:**
- `features.nppv_features`: 16 normalized NPP-V indicators per AGEB
- `features.ageb_suitability_predictions`: RF and LightGBM scores
- `features.model_feature_importance`: SHAP feature importance
- `outputs/phase2/models/*.pkl`, `outputs/phase2/shap/*.png`
- `outputs/phase2/phase2_report.md`

### Phase 3: Objective Weighting (CRITIC + EWM)

**Goal:** Compute objective indicator weights using an ensemble of CRITIC and Entropy Weight Method (EWM).

```bash
bash scripts/run_phase3_wsl.sh

# Or directly:
python src/phase3_weighting.py   # Compute CRITIC & EWM weights
python src/phase3_report.py      # Phase 3 report
```

**Outputs:**
- `features.nppv_weights`: Objective weights for all 16 indicators
- `outputs/phase3/phase3_report.md`

### Phase 4: Transit Suitability Typologies

**Goal:** Cluster AGEBs into 3 transit suitability typologies (A/B/C) using K-Means++.

```bash
bash scripts/run_phase4_wsl.sh

python src/phase4_clustering.py   # K-Means++ clustering
python src/phase4_report.py       # Typology profiling report
```

**Outputs:**
- `features.ageb_typologies`: Cluster assignments per AGEB
- `outputs/phase4/phase4_report.md`

### Phase 5: Predictive Modeling & Interpretability

**Goal:** Train Random Forest and XGBoost multi-class classifiers to predict typology membership; explain predictions with SHAP.

```bash
bash scripts/run_phase5_wsl.sh

python src/phase5_predictive_modeling.py   # RF + XGBoost, 5-fold Stratified CV
python src/phase5_report.py                # Metrics and SHAP interpretability report
```

**Outputs:**
- Model artifacts: `outputs/phase5/models/*.pkl`
- CV metrics (primary metric: macro F1 ~1.0)
- SHAP plots per typology: `outputs/phase5/shap/*.png`
- `outputs/phase5/phase5_report.md`

**Key findings:** `v_ridership_annual` and `pe_marginacion` are the primary drivers across all typologies.

### Phase 6: Final Synthesis

**Goal:** Compile all phase reports and visualizations into a single master thesis document.

```bash
bash scripts/run_phase6_wsl.sh

python src/phase6_synthesis.py   # Consolidate all phase reports
```

**Outputs:**
- `outputs/phase6/synthesis_report.md`: Master thesis synthesis document
- `outputs/phase6/images/`: All phase visualizations consolidated

## Project Structure

```
predictive-transit-zmg/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── config.py                      # Python configuration (credentials, constants)
├── config.sh                      # Shell configuration (credentials, constants)
├── .github/
│   └── copilot-instructions.md   # AI agent instructions for development
├── data/
│   ├── _load_gdl_data.sh          # Data import script
│   ├── encuesta_origen_destino/   # Raw OD survey data (gitignored, large)
│   ├── *.txt                      # GTFS files
│   ├── *.csv                      # DENUE economic data
│   ├── *.gpkg                     # AGEB boundaries
│   └── *.geojson                  # Line 4 rail geometry
├── db_setup/
│   ├── setup_postgis_gdl.sh       # Database & PostGIS setup script
│   └── DDL.sql                    # Schema initialization & feature engineering
├── scripts/
│   ├── run_phase2_wsl.sh          # WSL runner: feature engineering
│   ├── run_phase3_wsl.sh          # WSL runner: objective weighting
│   ├── run_phase4_wsl.sh          # WSL runner: clustering
│   ├── run_phase5_wsl.sh          # WSL runner: predictive modeling
│   ├── run_phase6_wsl.sh          # WSL runner: synthesis
│   └── debug/                     # Development/debug utilities
├── src/
│   ├── run_phase1.py              # Phase 1 orchestrator
│   ├── run_phase2.py              # Phase 2 orchestrator
│   ├── phase1_*.py                # Phase 1 acquisition modules
│   ├── phase2_*.py                # Phase 2 feature engineering modules
│   ├── phase3_*.py                # Phase 3 weighting modules
│   ├── phase4_*.py                # Phase 4 clustering modules
│   ├── phase5_*.py                # Phase 5 predictive modeling modules
│   ├── phase6_synthesis.py        # Phase 6 synthesis
│   ├── geo_restrictions.py        # OSM extraction for 10 municipalities
│   └── overture_extraction.py     # POI extraction from Overture S3
├── notebooks/
│   └── to_ageb.ipynb              # AGEB-level aggregation workflow
└── outputs/
    ├── phase1/ … phase6/          # Generated reports, models, visualizations
```

## Key Concepts

### Database Schema Organization

- **raw**: Original data ingestion (no transformations)
- **base**: Normalized tables, all geometries projected to EPSG:6372 (conic equidistant), indexed for performance
- **features**: AGEB-level aggregated metrics for modeling
- **meta**: Configuration and dataset registry

### Spatial Reference System (CRS)

All spatial operations use **EPSG:6372** (Conic Equidistant Projection for Mexico). External data is ingested in EPSG:4326 (WGS84) and transformed immediately.

### Geography

The study area covers 10 municipalities in the ZMG:
1. Guadalajara
2. Zapopan
3. San Pedro Tlaquepaque
4. Tonalá
5. Tlajomulco de Zúñiga
6. El Salto
7. Ixtlahuacán de los Membrillos
8. Juanacatlán
9. Zapotlanejo
10. Acatlán de Juárez

### Feature Engineering

Each AGEB (Área Geoestadística Básica) receives computed features:

| Feature | Source | Calculation |
|---------|--------|-------------|
| **Accessibility** | GTFS stops | Count stops within 400m/800m buffers; min distance |
| **Employment** | DENUE | Establishment counts by SCIAN sector; employment proxy |
| **Topography** | DEM raster | Mean slope (degrees) |
| **Route Supply**