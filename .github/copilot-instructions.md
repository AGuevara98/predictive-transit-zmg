# AI Agent Instructions: predictive-transit-zmg

## Project Overview

Master's thesis analyzing optimal transit routes in the Zona Metropolitana de Guadalajara (ZMG). This is a **geospatial analysis pipeline** that ingests GTFS, OSM, and economic data to identify transit route placement opportunities using AGEB-level spatial analysis.

**Core objective:** Predict suitable areas (AGEBs) for new transit routes by analyzing employment, accessibility gaps, topography, and existing infrastructure.

## Implementation Status (May 2026)

**Phase 1 (Audit):** ✅ **COMPLETE**
- CRITIC weighting for 7 NP-RV features ✓
- Station NP-RV audit with scoring ✓
- Balanced training dataset creation ✓
- HTML audit report ✓

**Phase 2 (Prediction):** ✅ **IMPLEMENTED / UNDER REVIEW**
- ML model training (RandomForest + LightGBM) implemented in [src/phase2_train_models.py](src/phase2_train_models.py)
- Leakage and sanity diagnostics implemented and persisted to `outputs/phase2/metrics/*_leakage_checks.json`
- Suitability surface generation implemented in [src/phase2_predict_surface.py](src/phase2_predict_surface.py)
- QGIS-ready GeoJSON export implemented for AGEB predictions
- SHAP interpretability implemented in [src/phase2_shap_analysis.py](src/phase2_shap_analysis.py)
- Phase 2 report generation implemented in [src/phase2_report.py](src/phase2_report.py)
- Current caveat: metrics are extremely high and a leakage risk flag is still present (`stops_400m` near-separates the classes); treat Phase 2 as complete but not yet fully trusted for Phase 3 coupling

**Phase 3 (Synthesis):** 📋 **PLANNED**
- Steiner Tree route optimization
- OSM network with cost injection
- Route export and validation

## Architecture & Data Flows

## Recent Handoff Notes

Phase 2 now has an executable end-to-end pipeline via [src/run_phase2.py](src/run_phase2.py). The main artifacts are the run registry and metrics tables in PostgreSQL, the prediction surface in `features.ageb_suitability_predictions`, SHAP rankings in `features.model_feature_importance`, and exports under `outputs/phase2/`.

The latest successful run produced a leakage warning because `stops_400m` is highly separable. Before Phase 3 depends on suitability scores, review whether the label construction or feature set is too tautological. If necessary, add a fail gate or rebuild the training labels with a stricter separation between features and target.

What to do next:
1. Decide whether the leakage flag should block promotion to Phase 3.
2. Review SHAP vs CRITIC disagreement, especially around `stops_400m`, before using the model in cost injection.
3. Use the Phase 2 GeoJSON output for a quick visual QA pass in QGIS.
4. Start Phase 3 scaffolding once the Phase 2 trust threshold is accepted.

### 1. **Data Layers (3 main sources)**
- **GTFS Data** (`data/*.txt`): Standard transit feeds with stops, routes, trips
- **DENUE** (`data/INEGI_DENUE_UTF8.csv`): Economic establishments by location (SCIAN codes)
- **Spatial**: AGEB boundaries (`ageb_zmg_2020_v2.gpkg`), line 4 rail (`linea_4.geojson`), OSM street networks

### 2. **Database Schema (PostgreSQL+PostGIS)**
See [db_setup/DDL.sql](db_setup/DDL.sql) for the 3-schema organization:
- **raw**: Original data ingestion (no transformations)
- **base**: Normalized, projected to EPSG:6372 (conic equidistant for Mexico), indexed
- **features**: Aggregated metrics by AGEB for modeling

**Critical design pattern:** All spatial queries use `ST_Transform(..., 6372)` for consistent projections. Never mix EPSG:4326 (WGS84) with operations.

### 3. **Feature Engineering Pipeline**
Each AGEB gets computed features:
- **Accessibility**: Stop counts at 400m/800m buffers, minimum distance
- **Employment**: DENUE unit counts aggregated by SCIAN sector (manufacturing, retail, education, health, government)
- **Topography**: Mean slope from DEM raster
- **Route Supply**: Transit kilometers within 800m buffer
- Master table joins all features for downstream modeling

## Key Files & Patterns

| File | Purpose | Key Pattern |
|------|---------|------------|
| [src/geo_restrictions.py](src/geo_restrictions.py) | OSM extraction for 10 municipalities | Uses `ox.graph_from_polygon()` for large areas; outputs to GPKG with layer naming |
| [src/overture_extraction.py](src/overture_extraction.py) | POI extraction from Overture S3 | DuckDB + spatial extensions for S3 querying; WKB conversion to GeoPandas |
| [src/phase2_train_models.py](src/phase2_train_models.py) | Phase 2 model training | Trains RF + LightGBM, runs leakage checks, persists metrics and artifacts |
| [src/phase2_predict_surface.py](src/phase2_predict_surface.py) | Phase 2 prediction surface | Scores AGEBs, writes DB/CSV outputs, exports GeoJSON for QGIS |
| [src/phase2_report.py](src/phase2_report.py) | Phase 2 report generator | Summarizes metrics, leakage, and SHAP vs CRITIC comparison |
| [notebooks/to_ageb.ipynb](notebooks/to_ageb.ipynb) | AGEB-level aggregation workflow | Spatial joins with `ST_Intersects`, employment stratification logic |
| [db_setup/DDL.sql](db_setup/DDL.sql) | Schema initialization | Raw → Base → Features materialization; all geom transformations upfront |

## Developer Workflows

### Configuration Management
**All credentials and project constants are centralized:**

**Python:** `config.py` at project root
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI, ZMG_BBOX, CRS_CANONICAL
```

**Shell Scripts:** `config.sh` at project root
```bash
source "$(dirname "$0")/config.sh"
# Now use: $DB_HOST, $DB_PORT, $DB_NAME, $DB_USER, $CANONICAL_SRID, etc.
```

Both files are the single source of truth for:
- Database connection details (`PG_URI`, `DB_HOST`, `DB_PORT`, etc.)
- Spatial bounds (ZMG bounding box, municipalities list)
- CRS definitions (EPSG:6372 canonical, EPSG:4326 for ingestion)
- Feature engineering parameters (accessibility buffers, employment proxies, SCIAN sectors)

**Environment variables override defaults** (recommended for production):
```bash
export PG_USER=your_user
export PG_PASS=your_password
export PG_HOST=your_host
export PG_PORT=5432
export PG_DB=gdl_metro
```

### Database Setup
```bash
# 1. Load raw data (auto-run by Python scripts or manual SQL)
psql -h localhost -d gdl_metro -f db_setup/DDL.sql

# 2. Verify PostGIS extension
SELECT PostGIS_Full_Version();
```

### Environment
- **Python 3.9+** with virtualenv (`.venv/` directory)
- Requires: `geopandas`, `osmnx`, `duckdb`, `sqlalchemy`, `geoalchemy2`, `psycopg2-binary`, scikit-learn
- PostgreSQL 14+ with PostGIS 3.2+ (PostGIS raster required for slope calculations)

### Credential Management
See **Configuration Management** section above. Never commit `.pgpass` files or hardcoded credentials.

## Project-Specific Conventions

1. **CRS Management**: Always use EPSG:6372 (conic equidistant) for spatial calculations. WGS84 (4326) is read-only for ingestion.
2. **ZMG Boundary**: 10 fixed municipalities (hardcoded in [src/geo_restrictions.py](src/geo_restrictions.py#L4)). Bounding box: Longitude -103.60 to -103.10, Latitude 20.30 to 20.90.
3. **AGEB Filtering**: Exclude cells with 'A' in CVE_AGEB and non-ZMG municipalities (see [db_setup/DDL.sql](db_setup/DDL.sql#L60)).
4. **Spatial Index**: All base/features tables use GIST indexes on geom columns. Run `ANALYZE` after bulk inserts.
5. **Employment Stratification**: DENUE establishment size is categorized (0-5, 6-10, 11-30, etc.). Map to employment proxy for aggregation (no 0-10 person units in features).

## Integration Points

- **GTFS → PostgreSQL**: Manual or script-based load; SCIAN filtering for sector analysis
- **OSM ↔ DuckDB**: S3-backed queries (Overture 2026-02-18.0 release); results materialized to GPKG
- **Raster (DEM) → PostGIS**: Slope calculations require `postgis_raster` extension
- **Python → PostgreSQL**: SQLAlchemy + geoalchemy2 for ORM; bulk inserts use COPY

## Common Pitfalls

- **Projection mismatch**: If spatial joins fail silently, verify both tables use EPSG:6372
- **Missing indexes**: Spatial queries on unindexed geom columns timeout on large tables
- **DENUE duplication**: Verify `denue_id` uniqueness before aggregation joins
- **Raster null values**: DEM slope calculations return NaN for water/no-data; coalesce or filter as needed

## When Adding Features

1. Create aggregation query in **features** schema (see [db_setup/DDL.sql](db_setup/DDL.sql#L180+))
2. Ensure AGEB-level granularity (`GROUP BY a.cvegeo`)
3. Add index on `ageb_id`; run `ANALYZE`
4. Update master_suitability table to include new feature
5. Document SCIAN filters or distance thresholds used


# Copilot Instructions: Project Predictive Transit ZMG

## 1. Project Context
This repository develops a predictive planning framework for mass transit in the Guadalajara Metropolitan Area (ZMG). The scientific core is the **NP-RV** (Node-Place-Real Estate-Vitality) model and network synthesis via **Steiner Trees**.

## 2. Tech Stack & Environment
* **Environment:** WSL (Ubuntu) running PostgreSQL 16 with PostGIS.
* **Database:** `gdl_metro` (Host: `localhost`, Port: `5432`).
* **Credentials:** User: `aguevara`, Password: `550800`.
* **Data Engines:** 
    * **PostGIS:** For persistent storage and complex spatial topology.
    * **DuckDB:** For fast S3/Parquet ingestion (Overture Maps) and in-memory aggregations.

## 3. Data Structure (Postgres Schemas)
* `base`: Existing infrastructure (GTFS stops, INEGI AGEBs, OSM road network).
* `raw`: Unprocessed external data (DENUE, raw Overture).
* `features`: Processed layers, NP-RV indicators, and model results. **Always save analytical outputs here.**

## 4. Coding Rules & Libraries
* **Spatial:** Prioritize `geopandas` and `shapely`. Always use CRS **EPSG:6372** (Official projected CRS for Mexico).
* **Connection:** Use `sqlalchemy.create_engine` for Postgres connections.
* **DuckDB Pattern:** 
    * Load `spatial` and `httpfs` extensions.
    * Use an anonymous S3 `SECRET` with empty keys for Overture Maps access.
    * Convert to WKB (`ST_AsWKB`) when passing data from DuckDB to GeoPandas.
* **Machine Learning:** 
    * Implement benchmarks between `RandomForestClassifier` and `lightgbm`.
    * Use `shap` for model interpretability and feature importance analysis.

## 5. Methodological Workflow (Steps for Copilot)
1. **Phase 1 (Audit):** Join stations with NP-RV variables -> Calculate weights using the **CRITIC Method**.
2. **Phase 2 (Prediction):** Train models using "Balanced" stations -> Predict the **Suitability Surface ($S$)** at the AGEB grain.
3. **Phase 3 (Synthesis):** Generate an `osmnx` graph -> Apply **Steiner Tree** logic with $Cost = Distance \times (1/S)$.

## 6. Key Bibliographic References
When generating code comments or documentation, refer to:
* **Bertolini (1996/1999):** Node-Place Model foundation.
* **Niu et al. (2023):** Random Forest for station suitability.
* **Liu et al. (2024/2025):** NP-RV Model and LightGBM+SHAP interpretability.
* **Takahashi (1980):** Steiner Tree heuristic for network design.