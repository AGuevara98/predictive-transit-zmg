# W9 City Onboarding Checklist

Step-by-step guide for applying the NPP-V predictive transit pipeline to a new Mexican metropolitan area.

**Reference city:** ZMG (Guadalajara, Jalisco) — fully implemented in W1-W6.  
**Transfer city:** MTY (Monterrey, Nuevo Leon) — W9 transferability study.

---

## Section 1: Data Acquisition

### 1.1 INEGI CPV2020 Census (Tier-1, REQUIRED)

- [ ] Go to: https://www.inegi.org.mx/programas/ccpv/2020/#Microdatos
- [ ] Navigate: Microdatos > AGEB y manzana urbana > [Select target state]
- [ ] Download the CSV ZIP (file name pattern: `conjunto_de_datos_ageb_urbana_{CVE_ENT}_cpv2020_csv.zip`)
- [ ] Extract to `data/conjunto_de_datos_ageb_urbana_{CVE_ENT}_cpv2020/`
- [ ] Verify: CSV exists at `data/conjunto_de_datos_ageb_urbana_{CVE_ENT}_cpv2020/conjunto_de_datos/conjunto_de_datos_ageb_urbana_{CVE_ENT}_cpv2020.csv`
- [ ] Spot-check columns: confirm `POBTOT`, `VPH_AUTOM`, `VIVPAR_HAB`, `P_15A17`, `P_18A24` exist
- [ ] Filter rows where `MZA == "000"` to get AGEB-level summaries (manzana rows have other values)

**Monterrey-specific:**
- CVE_ENT = 19
- URL: https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/ageb_manzana/conjunto_de_datos_ageb_urbana_19_cpv2020_csv.zip

### 1.2 DENUE Business Registry (Tier-1, REQUIRED for full W1 attractions)

- [ ] Go to: https://www.inegi.org.mx/app/descarga/?ti=6
- [ ] Select: DENUE > [Target state] > Download point data (CSV or shapefile)
- [ ] Place file in `data/` and update city config `DENUE_PATH` accordingly
- [ ] Verify presence of `CODIGO_ACT` (SCIAN code) and `PER_OCU` (employment class) columns
- [ ] Verify `LATITUD`, `LONGITUD` columns for spatial join

**File naming convention:** `DENUE_{STATE_KEY}_{YEAR}.csv`

### 1.3 OSM Street Network (Tier-1, auto-downloaded)

- [ ] Run: `python src/w9_osm_download.py`
- [ ] Verify output at `data/osm_{city_key}_drive.graphml`
- [ ] Record node and edge counts for the methods section
- [ ] If bounding box download fails: check osmnx version; try `graph_from_place` fallback

### 1.4 INEGI CEM 3.0 DEM (Tier-1, optional — terrain feature only)

- [ ] Go to: https://www.inegi.org.mx/app/geo2/elevacionesmex/
- [ ] Select 15m resolution tiles covering the city bounding box
- [ ] Merge tiles if necessary (GDAL `gdalwarp -t_srs EPSG:6372 ...`)
- [ ] Place merged raster in `data/dem_{city_key}_15m.tif`
- [ ] Note: pipeline uses `COALESCE(slope_mean, 0)` — missing DEM is handled gracefully

### 1.5 GTFS Transit Feed (Tier-2, required for W3)

- [ ] Check operator website for GTFS download link
- [ ] For Monterrey: check https://transmetro.monterrey.gob.mx and https://datos.gob.mx
- [ ] Download and extract to `data/gtfs_{city_key}/`
- [ ] Required files: `stops.txt`, `stop_times.txt`, `trips.txt`, `frequencies.txt`, `shapes.txt`
- [ ] Validate stop coordinate coverage: plot stops on a basemap to check spatial extent
- [ ] If `frequencies.txt` is absent: confirm that `stop_times.txt` has consistent departure times for headway computation

**File naming convention for flat layout (current W3 approach):** Copy all GTFS TXT files directly to `data/` (the W3 accessibility script reads `data/stops.txt`, etc. — update paths if using subdirectory layout).

### 1.6 EOD Origin-Destination Survey (Tier-2, optional for W2 calibration)

- [ ] Contact: IMPLAN of the target metro area, SEDATU, or university transport labs
- [ ] For Monterrey: check IMPLAN NL (https://implan.monterrey.gob.mx) or AMTU
- [ ] If available: note file format (shapefile, CSV, or geodatabase) and column names
- [ ] If unavailable: document this and proceed with `GRAVITY_BETA = 2.0` (ZMG calibrated prior)
- [ ] Record survey year and spatial coverage (number of zones, zone boundaries available?)

---

## Section 2: Configuration

### 2.1 Create City Configuration Module

- [ ] Copy `src/w9_city_config.py` as a template
- [ ] Set `CITY_NAME`, `CITY_KEY`, `CVE_ENT`
- [ ] Populate `ZM_MUNICIPALITIES` with zero-padded 3-digit CVE_MUN codes from CONAPO delimitation
- [ ] Set `BBOX_LON_MIN/MAX`, `BBOX_LAT_MIN/MAX` using the city boundary + 5km buffer
- [ ] Set `DB_SCHEMA_PREFIX` to a unique short identifier (e.g., `mty`, `gdl`, `mex`)
- [ ] Update `OSM_NETWORK_CACHE` path
- [ ] Update `CENSUS_ZIP_URL`, `CENSUS_DIR_NAME`, `CENSUS_CSV_NAME`
- [ ] Verify `GRAVITY_BETA = 2.0` (use ZMG prior unless EOD calibration is done first)

### 2.2 Verify SCIAN Sector Mapping

- [ ] Confirm that `EMPLOYMENT_PROXY_MAP` in `config.py` applies nationally (it does — SCIAN codes are Mexican national standard)
- [ ] No per-city changes needed for employment proxy weights

### 2.3 Verify CRS

- [ ] `CRS_CANONICAL = "EPSG:6372"` applies to all of Mexico — no change needed

---

## Section 3: Database Setup

### 3.1 Schema Creation

- [ ] Decide whether to use a shared PostgreSQL instance or a separate database:
  - **Shared instance (recommended):** use `features_mty` schema alongside existing `features` (ZMG) schema
  - **Separate database:** create `mty_metro` database and run full DDL
- [ ] Create city-specific schema: `CREATE SCHEMA IF NOT EXISTS features_{city_key};`
- [ ] Ensure PostGIS extension is available: `SELECT PostGIS_Full_Version();`

### 3.2 AGEB Base Layer

Option A (if using the same DB as ZMG):
- [ ] Load new city AGEB polygons to `base.ageb_{city_key}` or a separate `base` schema
- [ ] Apply AGEB filter: `CVE_ENT = '{CVE_ENT}'` and `CVE_MUN IN ('{mun_list}')`
- [ ] Project to EPSG:6372: `ST_Transform(geom, 6372)`
- [ ] Create GIST index on geometry column
- [ ] Run `ANALYZE base.ageb_{city_key}`

Option B (separate database):
- [ ] Run `psql -d {new_db} -f db_setup/DDL.sql` (applies to the new city's tables)
- [ ] Load AGEB shapefile from INEGI Marco Geoestadistico: https://www.inegi.org.mx/temas/mg/

**AGEB shapefile source:**
- URL: https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=889463807469
- File: MGN 2020 > Estado > [State SHP]
- Filter: `CVE_ENT = '{CVE_ENT}'` and exclude non-urban or non-ZM municipalities

### 3.3 NPP-V Feature Tables

- [ ] After running feature engineering, write to `features_{city_key}.nppv_features`
- [ ] Column schema must match ZMG `features.nppv_features` exactly (same 14 `_n` columns)
- [ ] Create indexes: `CREATE INDEX ON features_{city_key}.nppv_features (cve_ageb)`

---

## Section 4: Pipeline Execution Order

### Tier-1 Pipeline (minimum viable run)

```
W1.1: Trip generation        -- requires: CPV2020 census, DENUE (or population-proxy attractions)
W1.2: Gravity model          -- requires: W1.1 outputs + AGEB centroids
W1.3: Transit demand surface -- requires: W1.2 outputs + CPV2020 vehicle ownership
W4:   NPP prioritization     -- requires: AGEB geometry + DENUE (employment/POI features)
W5:   Multi-objective func   -- requires: W1 demand + W4 prioritization
W6:   Corridor generation    -- requires: W5 + OSM graph + W1 demand
```

Run order (Tier-1 only):
1. `python src/w9_osm_download.py`         -- download OSM graph
2. `python src/w9_run_tier1.py`            -- W1 equivalent for new city
3. *(Adapt `src/run_w4.py` for new city schema)* -- NPP prioritization
4. *(Adapt `src/run_w6.py` for new city)* -- corridor generation

### Tier-2 Extension (if GTFS available)

```
W3: Accessibility + coverage gap -- requires: GTFS + W1 demand surface
```

Run after W1:
5. `python src/run_w3.py`  *(with city-specific GTFS path)*

### Optional Calibration (if EOD available)

```
W2: Gravity calibration -- requires: EOD survey + W1 trip ends
```

Run between W1.1 and W1.2:
- `python src/run_w2.py` *(with city-specific EOD paths)*
- Update `GRAVITY_BETA` in city config based on calibration output

---

## Section 5: Validation Checkpoints

### After Data Acquisition
- [ ] Census: row count per municipality matches INEGI published AGEB counts
- [ ] DENUE: spot-check 10 establishments with known addresses against map
- [ ] OSM: plot graph on basemap; verify major roads are present
- [ ] GTFS (if available): `stops.txt` coordinates fall within city bounding box

### After W1 Trip Generation
- [ ] `features.ageb_trip_ends` row count equals number of AGEBs in base layer
- [ ] Total productions equals total attractions (doubly-constrained requirement)
- [ ] Mean productions per AGEB is plausible (ZMG mean: ~9,000 trips/AGEB)
- [ ] Zero-production AGEBs: should be rare (<5%); investigate if higher

### After W1 Gravity Model
- [ ] Furness IPF converged (look for convergence log message); warn if not
- [ ] Row and column sums of OD matrix match productions/attractions (within tolerance 1e-4)
- [ ] Mean OD distance is geographically plausible (ZMG mean: ~3,000-8,000 m)
- [ ] Number of stored OD pairs: expect 30-70% of N^2 for urban areas

### After W1 Demand Surface
- [ ] Mean transit propensity: 0.3-0.7 for typical Mexican cities
- [ ] AGEBs with `transit_demand = 0`: review whether these are truly high-car-ownership zones
- [ ] Mean vehicle_rate: ZMG was 0.577; Monterrey may differ due to higher car ownership

### After W3 Accessibility (if GTFS available)
- [ ] AGEBs with zero accessibility: expect 20-40% in dispersed metro areas
- [ ] Mean jobs reachable in 45 min: compare to published accessibility benchmarks
- [ ] High-gap AGEB share: expect 15-25% (ZMG: 20.7%)

### After W4 NPP Prioritization
- [ ] All 2,068 (or N city) AGEBs have non-null `final_score`
- [ ] Score distribution: mean ~0.5, std ~0.15 (typical for normalized composite)
- [ ] Cluster profiles: verify A/B/C clusters are interpretable spatially

### After W6 Corridor Generation
- [ ] At least 1 feasible corridor (if demand and geometry allow)
- [ ] All feasible corridors pass W5 constraint checks
- [ ] Corridor geometries are within city bounding box

---

## Section 6: Known Adaptation Points

### Census Column Names
The CPV2020 schema is identical across Mexican states — no column name changes required. However, verify that all expected columns exist before running; some small municipalities may have suppressed values (reported as `*`).

### AGEB Filter Logic
- ZMG filter: `CVE_ENT='14'` and `MUN IN {'039','120','098','101','097','070','044','051','124','002'}`
- For new city: update `CVE_ENT` and `ZM_MUNICIPALITIES` in city config
- Alpha-suffix AGEBs (`CVE_AGEB` containing 'A'): the ZMG pipeline retains these as valid INEGI codes; apply same logic for other cities

### Municipality Code Completeness
- CONAPO delimitations of metropolitan zones are updated periodically
- Always verify the CONAPO 2020 definition for the target city
- Source: https://www.gob.mx/conapo/acciones-y-programas/delimitacion-de-las-zonas-metropolitanas-de-mexico-2020

### DENUE Employment Proxy
- `EMPLOYMENT_PROXY_MAP` in `config.py` maps PER_OCU strings to headcounts
- The PER_OCU encoding is national standard — no adaptation needed
- However, economic profile differs by city: Monterrey is more industrial than GDL; this affects the attraction distribution but not the pipeline code

### Gravity Model Beta
- ZMG W2 calibration found beta=2.0 is the optimal value (calibrated optimum hit boundary at beta=5.0 with worse fit)
- Use beta=2.0 as prior for new cities
- If EOD data is available for the new city: run W2-equivalent calibration and report transfer error

### GTFS Feed Structure
- All W3 GTFS parsing assumes flat file layout in `data/` (not subdirectory)
- If operator provides ZIP: extract to `data/` before running W3
- Column names in `stop_times.txt` and `frequencies.txt` vary by operator; check for `headway_secs` vs. `headways_in_seconds`
- If `frequencies.txt` is absent: W3 computes headway from consecutive stop times in `stop_times.txt`

### Database Schema Isolation
- ZMG uses `features` schema; new city must use `features_{city_key}` to avoid table collision
- All W1-W6 scripts use `features.` prefix hardcoded — create per-city adapters or parameterize schema name
- Recommendation: use PostgreSQL search_path for transparent schema switching in new city scripts

### Population Density Calculation
- ZMG pipeline computes `pe_pop_density = pe_population / area_km2` from polygon areas
- AGEB polygon areas in EPSG:6372 (metres); divide by 1e6 for km2 — same formula applies nationally

### OSM Network Coverage
- Dense urban cores: high OSM coverage in all major Mexican cities
- Peripheral or informal settlements: OSM may be incomplete; Steiner corridor routing will detour around gaps
- If coverage is poor: consider using INEGI road network (`red_nacional_de_caminos`) as supplement
