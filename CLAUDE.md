# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Master's thesis: a **7-phase geospatial ML pipeline** to predict optimal transit route placement in the Zona Metropolitana de Guadalajara (ZMG), implementing the **NPP-V** (Node-Place-People-Vitality) framework. The unit of analysis is the **AGEB** (census enumeration area); 2,068 AGEBs in 10 ZMG municipalities.

**The pipeline is being re-architected** into a demand-driven, transferable framework per `docs/game_plan_demand_driven_restructure.md`. The work is organized as workstreams W0–W9.

**Workstream status:**
- W0 (Remediation): ✅ Complete — see errata below
- W1 (Demand Estimation Layer): ✅ Complete — `ageb_trip_ends` + `ageb_od_matrix` in DB; transit_demand surface written; see W1 section below
- W2 (Survey Calibration): 📋 Planned
- W3 (Supply & Coverage-Gap Layer): 📋 Planned
- W4–W9: 📋 Planned

**Legacy phase status (pre-restructure):**
- Phase 1 (Data Acquisition): ✅ Complete
- Phase 2 (Feature Engineering + Binary ML Suitability): ✅ Complete — leakage resolved, baseline `no_stop_features_v1`; **target will be replaced by W3 coverage-gap index**
- Phase 3 (CRITIC/EWM Objective Weighting): ✅ Complete — weights in `features.nppv_weights`; **repositioned as W4 prioritization layer**
- Phase 4 (K-Means Clustering / Transit Suitability Typologies): ✅ Complete — clusters in `features.nppv_clusters`; **kept as descriptive segmentation only**
- Phase 5 (Predictive Modeling & Interpretability): ✅ Complete — RF + XGBoost; **1.0000 accuracy is tautological (predicts its own K-Means labels); will be re-pointed at W3 external target**
- Phase 6 (Synthesis Report): ✅ Complete — `outputs/phase6/master_thesis_synthesis.md`; **will be rewritten after W8**
- Phase 7 (Steiner Tree Route Synthesis): 📋 Subsumed into W5+W6

## Environment Setup

**Python:** 3.9+ with virtualenv at `.venv/`

```bash
# Activate (WSL/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Database:** PostgreSQL 14+ with PostGIS 3.2+ (raster extension required), database name `gdl_metro`.

```bash
# Initialize schema
psql -h localhost -d gdl_metro -f db_setup/DDL.sql

# Verify PostGIS
psql -h localhost -d gdl_metro -c "SELECT PostGIS_Full_Version();"
```

**WSL runners** (phases 2–6 use shell wrappers):
```bash
bash scripts/run_phase2_wsl.sh
bash scripts/run_phase3_wsl.sh
# etc.
```

**Run individual phase orchestrators:**
```bash
python src/run_phase1.py
python src/run_phase2.py
```

## Configuration

All credentials and constants live in **two files** — never duplicate elsewhere:
- `config.py` — Python (imported by all `src/` scripts)
- `config.sh` — Bash (sourced by `scripts/`)

```python
# Python import pattern (used in every src/ file)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI, CRS_CANONICAL, ZMG_BBOX, EMPLOYMENT_PROXY_MAP, SCIAN_SECTORS
```

```bash
# Shell source pattern
source "$(dirname "$0")/config.sh"
# then use: $DB_HOST, $DB_PORT, $DB_NAME, $DB_USER, $CANONICAL_SRID
```

**Environment variable overrides** (for production):
```bash
export PG_USER=your_user PG_PASS=your_password PG_HOST=localhost PG_PORT=5432 PG_DB=gdl_metro
```

External API tokens (optional): `INEGI_TOKEN`, `NASA_JWT`.

## Database Architecture

Three-schema PostgreSQL design:

| Schema | Purpose |
|--------|---------|
| `raw` | Original data ingestion, no transformations |
| `base` | Normalized, projected to EPSG:6372, GIST-indexed |
| `features` | AGEB-level aggregated metrics, model outputs, weights, clusters |

**Key tables:**
- `base.ageb` — 2,068 AGEB polygons (filtered: `CVE_ENT='14'`, no 'A' suffix in `CVE_AGEB`, 10 ZMG municipalities)
- `features.nppv_features` — **15** normalized NPP-V indicators per AGEB (`_n` suffix = normalized; `v_ntl_median` dropped per W0.1)
- `features.nppv_weights` — CRITIC + Entropy Weight Method outputs (15 features)
- `features.nppv_clusters` — K-Means typology assignments (A/B/C), silhouette 0.58
- `features.ageb_suitability_predictions` — Phase 2/5 model predictions
- `features.model_runs` — Persisted validation metrics

**All analytical outputs go to the `features` schema.**

## Critical Spatial Conventions

1. **Canonical CRS:** EPSG:6372 (conic equidistant for Mexico) for all calculations and storage. EPSG:4326 (WGS84) is ingestion-only.
   ```python
   gdf = gdf.to_crs("EPSG:6372")  # always upfront
   ```
   ```sql
   ST_Transform(geom, 6372)  -- in all SQL spatial ops
   ```

2. **ZMG bounding box:** Lon −103.60 to −103.10, Lat 20.30 to 20.90.

3. **AGEB filter:** Exclude cells where `CVE_AGEB` contains 'A' and exclude non-ZMG municipality codes. See `db_setup/DDL.sql:60`.

4. **GIST indexes on all geometry columns.** Always `ANALYZE` after bulk inserts.

## Key Source Files

| File | Role |
|------|------|
| `src/run_phase1.py`, `src/run_phase2.py` | Phase orchestrators (main entry points) |
| `src/geo_restrictions.py` | OSM extraction for 10 ZMG municipalities via `osmnx` |
| `src/overture_extraction.py` | POI extraction from Overture S3 via DuckDB spatial |
| `src/phase2_train_models.py` | RF + LightGBM training with leakage checks |
| `src/phase2_predict_surface.py` | AGEB suitability scoring + GeoJSON export |
| `src/phase2_shap_analysis.py` | SHAP TreeExplainer interpretability |
| `src/phase3_weighting.py` | CRITIC + Entropy Weight Method |
| `src/phase4_clustering.py` | K-Means++ typology assignment |
| `src/phase5_predictive_modeling.py` | RF + XGBoost multi-class prediction |
| `db_setup/DDL.sql` | Full schema definition + raw→base→features materialization |
| `config.py` | Single source of truth for all constants and credentials |

## Coding Patterns

**Database connections (Python):**
```python
from sqlalchemy import create_engine, text
import geopandas as gpd

ENGINE = create_engine(PG_URI)
with ENGINE.raw_connection() as conn:
    gdf = gpd.read_postgis(query, conn, geom_col="geometry")
```

**DuckDB + Overture S3:**
```python
import duckdb
con = duckdb.connect()
con.execute("LOAD spatial; LOAD httpfs;")
con.execute("CREATE SECRET (TYPE S3, KEY_ID '', SECRET '', REGION 'us-east-1');")
# Use ST_AsWKB() when passing results to GeoPandas
```

**Output paths:**
```python
output_dir = Path("outputs") / f"phase{N}"
output_dir.mkdir(parents=True, exist_ok=True)
```

**Print conventions:**
```python
print(f"[Step N] Description...")
print(f"  [OK] Result")
print(f"  [ERR] Error message")
```

## Adding a New Feature

1. Write aggregation SQL in `features` schema, grouped by `a.cvegeo`
2. Add GIST/btree index on `ageb_id`; run `ANALYZE`
3. Update `features.nppv_features` master table
4. Document any SCIAN sector filters or distance thresholds used
5. Add `_n` normalized version alongside raw

## Phase 2 Model State

**Current baseline:** run ID `no_stop_features_v1`

**Active feature columns** (in `FEATURE_COLUMNS`, [src/phase2_train_models.py](src/phase2_train_models.py)):
- `employment_proxy` — job density demand signal (top SHAP feature alongside route coverage)
- `route_km_800m` — transit route km within 800m buffer
- `slope_mean` — mean terrain slope from DEM

**Dropped features:** `stops_400m`, `stops_800m`, `min_stop_dist_m` — all removed due to tautology (labels were assigned partly based on stop proximity, so using stop counts as features meant the model learned "transit exists where transit exists" rather than genuine demand patterns).

**Baseline metrics (test split):** RF PR-AUC 0.94, ROC-AUC 0.83 — no leakage flags. Top SHAP driver: `route_km_800m` > `employment_proxy` > `slope_mean`.

**Outputs:** `outputs/phase2/predictions/no_stop_features_v1_ageb_predictions.geojson` (QGIS-ready), SHAP plots in `outputs/phase2/shap/`.

## W0 Errata (completed 2026-06-14)

Three integrity defects fixed before W1 work begins:

1. **`v_ntl_median` dropped (W0.1):** VIIRS VNP46A3 HDF5 zonal-stats silently failed (try-except swallowed a rasterio error; tile bounds from `WestBoundingCoordinate` attrs may have mismatched). All 2,068 values were zero. Feature removed from `phase2_feature_engineering.py`, `phase3_weighting.py`, `phase2_db_setup.py`, and the live DB via `db_setup/migrations/001_drop_ntl_columns.sql`. Vitality dimension is now single-proxy: `v_ridership_annual`.

2. **Phase 5 weight join fixed (W0.2):** `phase5_report.py` was appending `_n` to feature names that already ended in `_n`, producing `n_intersections_n_n` — no matches, all Phase 3 weights showed 0.0000. Fixed by removing the erroneous suffix concatenation. Report also updated with an errata block flagging the 1.0000 cluster-recovery accuracy as a tautology.

3. **Scaling fixed (W0.3):** Replaced global min-max with `log1p + minmax` for 10 right-skewed count/economic features (`p_employment_proxy`, `p_poi_density`, population/density, ridership, street metrics). Bounded ratios (`pe_marginacion`, `pe_dep_ratio`, `pe_youth_share`, `p_land_use_mix`) keep plain min-max. Phases 2–4 re-run after this change.

**Known remaining issue:** `v_ridership_annual` is assigned at municipality level (all AGEBs in a municipality share the same value), so after normalization it functions as a binary "has SITEUR" flag. This produces a geographic cluster split (B = SITEUR municipalities) rather than AGEB-level demand signal. Will be replaced by W1 trip-generation estimates.

## Known Issues

- **DEM raster not in git:** `continuonacional_15m.tif` (~7.2 GB) must be downloaded manually from the INEGI CEM 3.0 portal and placed in `data/`. The `LEFT JOIN` in `master_suitability` and `COALESCE(topo.slope_mean, 0)` handle missing raster rows gracefully.

## Debugging Utilities

```bash
python scripts/debug/check_db.py          # Validate database schema/tables
python scripts/debug/db_checks.py         # Schema/table verification
python scripts/debug/inspect_employment.py # Employment feature diagnostics
bash scripts/debug/run_db_checks.sh        # Shell-based validation
```

## NPP-V Indicator Reference

**15 indicators** computed per AGEB, stored normalized in `features.nppv_features` (`v_ntl_median` dropped per W0.1):

- **Node (3):** `n_intersections` (all intersections/km²), `n_intersection_density` (4-way intersections/km²), `n_street_density`
- **Place (5):** `p_poi_density`, `p_employment_proxy`, `p_retail_density`, `p_service_density`, `p_land_use_mix`
- **People (6):** `pe_population`, `pe_pop_density`, `pe_marginacion`, `pe_rezago`, `pe_dep_ratio`, `pe_youth_share`
- **Vitality (1):** `v_ridership_annual` (municipality-level proxy; to be replaced by W1 AGEB-level demand estimates)

**Normalization:** log1p + min-max for count/economic features; plain min-max for bounded ratios. See `LOG_FEATURES` in `src/phase2_feature_engineering.py`.

Primary Phase 2 model drivers (SHAP, run `no_stop_features_v1`): `route_km_800m`, `employment_proxy`, `slope_mean`. **This model will be re-pointed at the W3 coverage-gap target.**

## W1 — Demand Estimation Layer (completed 2026-06-15)

W1 replaces the circular "has-a-stop" target with an explicit modeled transit-demand surface using **only Tier-1 data** (census, DENUE, OSM) — no existing transit supply as input.

**Completed sub-tasks:**

1. **W1.1 — Trip generation** (`src/w1_trip_generation.py`)
   - Productions: `2.5 trips/person/day × population × (1 + 0.10 × youth_share)`
   - Attractions: weighted sum of `p_employment_proxy`, `p_poi_density × area_km2`, `p_retail_density × area_km2`; scaled so `sum(A) = sum(P)`
   - Output: `features.ageb_trip_ends` — 2,068 rows with `productions`, `attractions`

2. **W1.2 — Doubly-constrained gravity model** (`src/w1_gravity_model.py`)
   - Power-law impedance `f(d) = d^(-2.0)`; Furness IPF with `tol=1e-5`, `max_iter=300`
   - Euclidean centroid distances in EPSG:6372 (metres); self-flows zeroed on diagonal
   - Sparse OD matrix: pairs with `modeled_flow >= 0.5` stored
   - Output: `features.ageb_od_matrix`; summary at `outputs/w1/od_matrix_summary.csv`

3. **W1.3 — Transit-demand surface** (`src/w1_demand_surface.py`)
   - `vehicle_rate = VPH_AUTOM / VIVPAR_HAB.clip(1)`, clipped to [0, 1]; VIVPAR_HAB=0 handled via `clip(lower=1)`
   - `transit_propensity = 1 - vehicle_rate`; `transit_demand = total_demand × transit_propensity`
   - Mean-fill fallback for AGEBs not matched in CPV2020 (mean computed on non-NaN values — correct)
   - Output: `features.ageb_trip_ends` updated with `vehicle_rate`, `transit_propensity`, `transit_demand`; CSV at `outputs/w1/ageb_demand_surface.csv`
   - Run stats: 2,068 rows, avg_vehicle_rate=0.577, avg_transit_prop=0.423

**Orchestrator:** `src/run_w1.py` — runs DDL migration + all three modules in sequence.

**Key files (all created):**
- `src/w1_trip_generation.py`, `src/w1_gravity_model.py`, `src/w1_demand_surface.py`, `src/run_w1.py`
- `db_setup/migrations/002_w1_demand_tables.sql`
- `tests/test_w1_gravity_model.py` (5 Furness IPF unit tests — all passing)
- `outputs/w1/ageb_trip_ends.csv`, `outputs/w1/od_matrix_summary.csv`, `outputs/w1/ageb_demand_surface.csv`

**Known W1 limitations (for W2 attention):**
- Euclidean distance proxy — W2 may refine with `osmnx` network travel times after EOD 2022 calibration
- `beta=2.0` (power-law decay) is uncalibrated; W2 will fit against EOD 2022 desire lines
- 187 AGEBs with alpha-suffix `cve_ageb` (e.g. `140020002005A`) passed through from CPV2020 census — these match the 'A' AGEB codes that `base.ageb` filters out; they appear in `ageb_trip_ends` because `w1_trip_generation.py` reads census directly without applying the same municipal filter that excludes A-codes. Effect is minor (9% of rows, correct propensity values) but should be cleaned in W2 or by adding the same exclusion to trip generation.
- 171 AGEBs have `vehicle_rate=1.0` (all occupied dwellings own a car), resulting in `transit_demand=0` even when they carry significant OD flow (~19% of total flow zeroed). These are likely small high-income residential areas; flag for W2 review.

**Invariants maintained:**
- All spatial ops in EPSG:6372; OD network distances computed in metres
- Output demand surface joins cleanly to `base.ageb` on `cve_ageb`
- Gravity model runnable with Tier-1 only (EOD 2022 is calibration, not a hard dependency)

## Methodological References

- Bertolini (1996/1999): Node-Place Model
- Liu et al. (2024/2025): NP-RV Model, LightGBM+SHAP
- Niu et al. (2023): Random Forest for station suitability
- Takahashi (1980): Steiner Tree heuristic for network design
