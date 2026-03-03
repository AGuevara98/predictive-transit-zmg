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

## Project Structure

```
predictive-transit-zmg/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── config.py                      # Python configuration (credentials, constants)
├── config.sh                      # Shell configuration (credentials, constants)
├── .github/
│   └── copilot-instructions.md   # AI agent instructions for development
├── db_setup/
│   ├── setup_postgis_gdl.sh       # Database & PostGIS setup script
│   └── DDL.sql                    # Schema initialization & feature engineering
├── data/
│   ├── _load_gdl_data.sh          # Data import script
│   ├── *.txt                      # GTFS files
│   ├── *.csv                      # DENUE economic data
│   ├── *.gpkg                     # AGEB boundaries
│   └── *.geojson                  # Line 4 rail geometry
├── src/
│   ├── geo_restrictions.py        # OSM extraction for 10 municipalities
│   └── overture_extraction.py     # POI extraction from Overture S3
└── notebooks/
    └── to_ageb.ipynb              # AGEB-level aggregation workflow
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
| **Route Supply** | Transit routes | Transit kilometers within 800m buffer |

## Troubleshooting

### Projection Mismatch Errors
If spatial joins fail silently, verify both tables use EPSG:6372:
```sql
SELECT ST_SRID(geom) FROM base.ageb LIMIT 1;
SELECT ST_SRID(geom) FROM base.gtfs_stops LIMIT 1;
```

### Slow Spatial Queries
Ensure GIST indexes exist on all geometry columns:
```sql
CREATE INDEX IF NOT EXISTS idx_ageb_geom ON base.ageb USING GIST (geom);
ANALYZE base.ageb;
```

### DENUE Duplication Issues
Verify `denue_id` uniqueness before aggregation:
```sql
SELECT denue_id, COUNT(*) FROM raw.denue GROUP BY denue_id HAVING COUNT(*) > 1;
```

### Raster Null Values
DEM slope calculations may return NaN for water/no-data areas. Coalesce in queries:
```sql
COALESCE(slope_mean, 0) AS slope_safe
```

## Contributing

When adding new features:
1. Create aggregation query in **features** schema (see [db_setup/DDL.sql](db_setup/DDL.sql))
2. Ensure AGEB-level granularity (`GROUP BY a.cvegeo`)
3. Add GIST index on `ageb_id`; run `ANALYZE`
4. Update `features.master_suitability` to include new feature
5. Document SCIAN filters or distance thresholds used

## Citation

Master's thesis, Universidad de Guadalajara. [Add thesis details here]