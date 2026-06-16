# predictive-transit-zmg

Master's thesis: a demand-driven, transferable framework for optimal public transit network design in Mexican metropolitan areas. Applied to the Zona Metropolitana de Guadalajara (ZMG) with a second-city demonstration on Monterrey.

## What This Does

The pipeline answers two research questions:

- **R1 — Where should new routes go?** Identifies unserved, high-demand corridors using a modeled transit-demand surface and a coverage-gap index.
- **R2 — Are existing routes optimal?** Scores all SITEUR GTFS routes against a formal multi-objective function and flags low-demand, indirect, and redundant routes.

The framework is **transferable**: it runs on Tier-1 data (INEGI census, DENUE, OSM, GTFS) available in any Mexican city. OD survey data, when available, calibrates the demand model but is not required.

The unit of analysis is the **AGEB** (Área Geoestadística Básica — census enumeration area). ZMG has 2,068 urban AGEBs across 10 municipalities.

---

## Workstream Status

| Workstream | Description | Status |
|---|---|---|
| W0 | Remediation (integrity fixes) | ✅ Complete |
| W1 | Demand estimation layer (4-step model) | ✅ Complete |
| W2 | Survey calibration (EOD 2022) | ✅ Complete |
| W3 | Supply & coverage-gap layer | ✅ Complete |
| W4 | NPP prioritization (CRITIC + EWM + equity) | ✅ Complete |
| W5 | Multi-objective function | ✅ Complete |
| W6 | New corridor generation | ✅ Complete |
| W7 | Existing route audit | ✅ Complete |
| W8 | Validation (backtest + benchmark + metrics) | ✅ Complete |
| W9 | Transferability — Monterrey Tier-1 pipeline | 🔄 In progress |

---

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 14+ with PostGIS 3.2+ (raster extension required)
- GDAL tools: `ogr2ogr`, `raster2pgsql`
- Ubuntu/WSL recommended for shell scripts

### 1. Python Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Credentials

Edit `config.py` (Python scripts) and `config.sh` (shell scripts), or override via environment variables:

```bash
export PG_USER=your_user
export PG_PASS=your_password
export PG_HOST=localhost
export PG_PORT=5432
export PG_DB=gdl_metro
```

### 3. Set Up PostgreSQL + PostGIS

**Automated (Ubuntu/WSL):**
```bash
sudo bash db_setup/setup_postgis_gdl.sh
```

**Manual:**
```bash
createdb -U postgres gdl_metro
psql -U postgres -d gdl_metro -c "CREATE ROLE <user> WITH LOGIN PASSWORD '<pass>';"
psql -U postgres -d gdl_metro -c "ALTER DATABASE gdl_metro OWNER TO <user>;"
psql -U <user> -d gdl_metro -c "CREATE EXTENSION postgis;"
psql -U <user> -d gdl_metro -c "CREATE EXTENSION postgis_raster;"
psql -U <user> -d gdl_metro -f db_setup/DDL.sql
```

### 4. Place Source Data

```
data/
├── gtfs/                          # ZMG GTFS feed (SITEUR)
│   ├── agency.txt
│   ├── calendar.txt
│   ├── calendar_dates.txt
│   ├── fare_attributes.txt
│   ├── frequencies.txt
│   ├── routes.txt
│   ├── shapes.txt
│   ├── stop_times.txt
│   ├── stops.txt
│   └── trips.txt
├── ageb_zmg_2020_v2.gpkg          # ZMG AGEB boundaries (INEGI 2020)
├── INEGI_DENUE_UTF8.csv           # DENUE economic establishments (ZMG)
├── linea_4.geojson                # W8 benchmark: Línea 4 rail geometry
├── osm_zmg_drive.graphml          # ZMG OSM drive graph (auto-downloaded if missing)
├── transporte_publico.gpkg        # Public transport layer
├── continuonacional_15m.tif       # DEM raster — NOT in git (~7.2 GB)
│                                  # Download: INEGI CEM 3.0 portal → see data/download_dem.sh
├── encuesta_origen_destino/       # EOD 2022 (W2 calibration) — gitignored
├── 2020_1_19_A/                   # Monterrey AGEB shapefile (W9)
├── ageb_mza_urbana_19_cpv2020_csv/ # Monterrey CPV2020 census (W9)
├── denue_19_0420_csv/             # Monterrey DENUE (W9)
├── osm_mty_drive.graphml          # Monterrey OSM drive graph (W9)
└── lineas_transporte_masivo_mty.gpkg  # Monterrey mass transit lines (W9)
```

Load ZMG source data into PostgreSQL:
```bash
cd data
bash _load_gdl_data.sh
cd ..
```

---

## Running the Pipeline

Each workstream has an orchestrator in `src/`. Run them in dependency order (W0→W1→W3→W5→W6/W7→W8; W2 alongside W1; W4 alongside W3; W9 after W1):

```bash
# W1 — Demand estimation (trip generation → gravity model → demand surface)
python src/run_w1.py

# W2 — EOD calibration (runs after W1; beta=2.0 prior retained)
python src/run_w2.py

# W3 — Accessibility + coverage-gap index + model retrain
python src/run_w3.py          # note: accessibility step ~20 min

# W4 — NPP prioritization (CRITIC/EWM weights + equity composite)
python src/run_w4.py

# W5 — Multi-objective function demo + spec
python src/run_w5.py

# W6 — New corridor generation
python src/run_w6.py

# W7 — Existing route audit
python src/run_w7.py

# W8 — Validation (backtest + benchmark + before/after metrics)
python src/run_w8.py

# W9 — Monterrey Tier-1 pipeline
python src/w9_run_tier1.py
```

---

## Architecture

### Two-Tier Data Model

| Tier | Data | Role |
|---|---|---|
| **Tier 1** | INEGI census, DENUE, OSM, GTFS | Core pipeline — runs in any Mexican city |
| **Tier 2** | EOD OD survey | Calibration/validation only — not a hard dependency |

### Demand-Driven Pipeline

```
W1: Trip generation (census + DENUE) → OD gravity model → transit-demand surface
W2: EOD 2022 calibration of gravity model beta (β=2.0 retained as prior)
W3: GTFS accessibility surface → coverage-gap index (demand/supply gap)
W4: CRITIC + EWM objective weights on 14 NPP indicators → final_score = 0.80×npp + 0.20×equity
W5: Multi-objective function (maximize demand gain + equity; minimize route-km)
W6: Anchor selection from W3 gap → MST on OSM graph → W5 evaluation → BRT corridors
W7: SITEUR routes → W5 scoring → low-demand / indirect / redundant flags + modification proposals
W8: Backtest (mask high-ridership routes; test W6 re-proposes them) + benchmark vs Línea 4
```

### Database Schema

| Schema | Contents |
|---|---|
| `raw` | Original ingested data, no transformations |
| `base` | Normalized tables, EPSG:6372, GIST-indexed |
| `features` | AGEB-level metrics, model outputs, weights, scores |

**Key feature tables:**

| Table | Description |
|---|---|
| `features.ageb_trip_ends` | W1 productions, attractions, vehicle rate, transit demand |
| `features.ageb_od_matrix` | W1 doubly-constrained gravity model OD flows |
| `features.ageb_accessibility` | W3 cumulative-opportunities accessibility (jobs reachable in 45 min) |
| `features.ageb_coverage_gap` | W3 coverage-gap index, quintile ranks, gap category |
| `features.nppv_features` | 14 normalized NPP indicators per AGEB |
| `features.nppv_prioritization` | W4 npp_score, equity_score, final_score for all 2,068 AGEBs |
| `features.route_candidates` | W6 corridor candidates with W5 scores and geometries |
| `features.route_audit` | W7 SITEUR route scorecard with flags and modification proposals |

### Spatial Conventions

- **Canonical CRS:** EPSG:6372 (conic equidistant for Mexico) for all calculations and storage
- **Ingestion CRS:** EPSG:4326 (WGS84) — transformed immediately on load
- **AGEB filter:** `CVE_ENT='14'`, excludes cells with 'A' suffix in `CVE_AGEB`, 10 ZMG municipalities only

---

## Project Structure

```
predictive-transit-zmg/
├── config.py                      # Credentials + constants (single source of truth for Python)
├── config.sh                      # Credentials + constants (single source of truth for shell)
├── requirements.txt
├── data/
│   ├── gtfs/                      # ZMG GTFS feed
│   ├── ageb_zmg_2020_v2.gpkg
│   ├── INEGI_DENUE_UTF8.csv
│   ├── linea_4.geojson
│   ├── osm_zmg_drive.graphml
│   ├── transporte_publico.gpkg
│   ├── continuonacional_15m.tif   # gitignored — download separately
│   ├── encuesta_origen_destino/   # gitignored — EOD 2022 survey
│   ├── 2020_1_19_A/               # Monterrey AGEB shapefile (W9)
│   ├── ageb_mza_urbana_19_cpv2020_csv/  # Monterrey census (W9)
│   ├── denue_19_0420_csv/         # Monterrey DENUE (W9)
│   ├── osm_mty_drive.graphml      # Monterrey OSM graph (W9)
│   ├── lineas_transporte_masivo_mty.gpkg  # Monterrey transit (W9)
│   ├── _load_gdl_data.sh          # Data loader for ZMG
│   └── download_dem.sh            # Instructions for obtaining DEM
├── db_setup/
│   ├── DDL.sql                    # Full schema definition + raw→base→features materialization
│   ├── setup_postgis_gdl.sh       # PostgreSQL + PostGIS setup (Ubuntu/WSL)
│   └── migrations/                # Incremental schema migrations (001–007)
├── src/
│   ├── run_w1.py … run_w8.py      # Workstream orchestrators
│   ├── w1_trip_generation.py      # 4-step trip generation (productions + attractions)
│   ├── w1_gravity_model.py        # Doubly-constrained gravity model (Furness IPF)
│   ├── w1_demand_surface.py       # Vehicle-ownership transit-propensity weighting
│   ├── w2_eod_ingest.py           # EOD 2022 shapefile ingestion (/vsizip/ via pyogrio)
│   ├── w2_gravity_calibration.py  # Beta calibration vs EOD desire lines (scipy)
│   ├── w3_accessibility.py        # GTFS cumulative-opportunities accessibility (networkx)
│   ├── w3_coverage_gap.py         # Coverage-gap index (demand / accessibility)
│   ├── w3_retrain.py              # RF + LightGBM on high-gap binary target + SHAP
│   ├── w4_prioritization.py       # CRITIC + EWM weights; npp_score + equity composite
│   ├── w5_types.py                # Data classes: W5Config, RouteCandidate, ObjectiveResult
│   ├── w5_objective.py            # Multi-objective evaluation (demand gain, cost, equity)
│   ├── w5_constraints.py          # Feasibility checks (detour ratio, stop spacing, demand)
│   ├── w5_pareto.py               # Non-dominated Pareto ranking
│   ├── w6_anchors.py              # Anchor AGEB selection (Jenks + KMeans spatial clustering)
│   ├── w6_graph.py                # OSM MST Steiner approximation
│   ├── w6_candidates.py           # Corridor construction + served AGEB spatial join
│   ├── w6_mode.py                 # BRT vs. local bus mode assignment by demand volume
│   ├── w7_gtfs_loader.py          # GTFS shapes → one LineString per route
│   ├── w7_route_scorer.py         # W5 scoring + Low-demand / Indirect / Redundant flags
│   ├── w7_modifications.py        # Shortcut / merge / retire proposals
│   ├── w8_backtest.py             # Mask high-ridership routes + W6 re-run + overlap metric
│   ├── w8_benchmark.py            # Compare W6 corridors to announced ZMG expansions
│   ├── w8_metrics.py              # Accessibility/equity Gini deltas, before/after
│   ├── w9_city_config.py          # Monterrey constants (municipalities, census columns, bbox)
│   ├── w9_osm_download.py         # OSM graph download for new cities
│   └── w9_run_tier1.py            # Monterrey Tier-1 orchestrator (W1-equivalent)
├── tests/
│   ├── test_w1_gravity_model.py   # 5 Furness IPF unit tests
│   ├── test_w4_prioritization.py
│   ├── test_w5_*.py               # 39 tests for objective, constraints, Pareto, types
│   ├── test_w6_*.py               # 21 tests for anchors, graph, candidates, mode
│   ├── test_w7_*.py               # 33 tests for GTFS loader, scorer, modifications
│   ├── test_w8_*.py               # Backtest + metrics tests
│   └── test_w9_city_config.py     # 26 tests
├── outputs/
│   ├── w1/ … w9/                  # Generated reports, CSVs, GeoJSONs, charts
│   └── phase1/ … phase6/          # Legacy outputs (historical reference)
├── docs/
│   ├── critical_review_decisions.md
│   ├── game_plan_demand_driven_restructure.md
│   ├── w9_city_onboarding.md      # City-onboarding checklist for new cities
│   └── w9_data_requirements.md    # Tiered data-requirements matrix
├── notebooks/
│   └── to_ageb.ipynb
└── scripts/
    └── debug/                     # Database validation utilities
```

---

## Key Outputs

| Output | Location | Description |
|---|---|---|
| Transit demand surface | `outputs/w1/ageb_demand_surface.csv` | 2,068 AGEBs with modeled transit demand |
| Coverage-gap index | `outputs/w3/ageb_coverage_gap.csv` | 428 High-gap AGEBs (20.7%) |
| NPP prioritization | `outputs/w4/nppv_prioritization.geojson` | All AGEBs scored + ranked (QGIS-ready) |
| New corridors | `outputs/w6/corridor_candidates.geojson` | 2 feasible BRT corridors (W6_G02, W6_G05) |
| Route audit | `outputs/w7/route_audit.geojson` | 275 SITEUR routes scored with flags |
| Validation report | `outputs/w8/w8_report.md` | Backtest + benchmark + equity metrics |

---

## Tests

```bash
pytest tests/ -v
```

All 139+ tests use synthetic fixtures; no database or file-system calls required.

---

## Known Issues

- **DEM raster not in git:** `continuonacional_15m.tif` (~7.2 GB) must be downloaded manually from the INEGI CEM 3.0 portal. `COALESCE(slope_mean, 0)` handles missing raster rows.
- **671 AGEBs with zero accessibility:** AGEBs with no GTFS stops within 400m receive `accessibility_score=0` and land in the highest-gap quintile. Verify these are genuinely unserved, not a GTFS coverage gap.
- **W9 blocked on Monterrey GTFS:** The Tier-1 demand surface for Monterrey is complete. W3–W7 equivalents require a Metrorrey/Transmetro GTFS feed (check `datos.gob.mx`).

---

## Methodology References

- Bertolini (1996/1999): Node-Place Model
- Liu et al. (2024/2025): NP-RV Model, LightGBM + SHAP
- Mumford et al. (arXiv:2201.11616): Multi-objective TNDP
- Park et al. (2022, J. Advanced Transportation): Variable-demand TNDP with equity
- Takahashi (1980): Steiner Tree heuristic

---

Master's thesis — Universidad de Guadalajara, Maestría en Ciencias Computacionales
