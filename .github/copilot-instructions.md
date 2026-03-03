# AI Agent Instructions: predictive-transit-zmg

## Project Overview

Master's thesis analyzing optimal transit routes in the Zona Metropolitana de Guadalajara (ZMG). This is a **geospatial analysis pipeline** that ingests GTFS, OSM, and economic data to identify transit route placement opportunities using AGEB-level spatial analysis.

**Core objective:** Predict suitable areas (AGEBs) for new transit routes by analyzing employment, accessibility gaps, topography, and existing infrastructure.

## Architecture & Data Flows

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
