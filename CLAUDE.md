# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Master's thesis: a **7-phase geospatial ML pipeline** to predict optimal transit route placement in the Zona Metropolitana de Guadalajara (ZMG), implementing the **NPP-V** (Node-Place-People-Vitality) framework. The unit of analysis is the **AGEB** (census enumeration area); 2,068 AGEBs in 10 ZMG municipalities.

**The pipeline is being re-architected** into a demand-driven, transferable framework per `docs/game_plan_demand_driven_restructure.md`. The work is organized as workstreams W0–W9.

**Workstream status:**
- W0 (Remediation): ✅ Complete — see errata below
- W1 (Demand Estimation Layer): ✅ Complete — `ageb_trip_ends` + `ageb_od_matrix` in DB; transit_demand surface written; see W1 section below
- W2 (Survey Calibration): ✅ Complete — EOD 2022 ingested; beta=2.0 retained (calibrated optimum worse); see W2 section below
- W3 (Supply & Coverage-Gap Layer): ✅ Complete — accessibility surface + coverage-gap index in DB; model retrained on external target; see W3 section below
- W4 (Reposition NPP-V): ✅ Complete — features.nppv_prioritization in DB; 14 NODE+PLACE+PEOPLE features; final_score=(0.80*npp_score)+(0.20*equity_score); see W4 section below
- W5 (Multi-objective function): 📋 Planned
- W6 (New corridor generation): 📋 Planned
- W7 (Existing route audit): 📋 Planned
- W8 (Validation): 📋 Planned
- W9 (Transferability): 📋 Planned

**Legacy phase status (pre-restructure):**
- Phase 1 (Data Acquisition): ✅ Complete
- Phase 2 (Feature Engineering + Binary ML Suitability): ✅ Complete — leakage resolved, baseline `no_stop_features_v1`; **target will be replaced by W3 coverage-gap index**
- Phase 3 (CRITIC/EWM Objective Weighting): ✅ Complete — weights in `features.nppv_weights`; **repositioned as W4 prioritization layer**
- Phase 4 (K-Means Clustering / Transit Suitability Typologies): ✅ Complete — clusters in `features.nppv_clusters`; **kept as descriptive segmentation only**
- Phase 5 (Predictive Modeling & Interpretability): ✅ Complete — RF + XGBoost; **1.0000 accuracy is tautological (predicts its own K-Means labels); re-pointed at W3 coverage-gap target — see W3 section**
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

**W2/W3 tables added:**
- `raw.eod_zones` — 71 EOD 2022 survey zones (EPSG:6372), with productions and attractions
- `raw.eod_desire_lines` — 3,509 observed zone OD pairs (all modes, total person trips)
- `features.w2_calibration` — timestamped calibration results (beta, RMSE, R²)
- `features.ageb_accessibility` — GTFS-based cumulative-opportunities accessibility per AGEB (jobs reachable in 45 min)
- `features.ageb_coverage_gap` — coverage-gap index, quintile ranks, and gap category per AGEB

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
| `src/run_phase1.py`, `src/run_phase2.py` | Legacy phase orchestrators |
| `src/run_w1.py` | W1 orchestrator: trip generation → gravity model → demand surface |
| `src/run_w2.py` | W2 orchestrator: EOD ingest → gravity calibration |
| `src/run_w3.py` | W3 orchestrator: GTFS accessibility → coverage gap → model retrain |
| `src/w1_trip_generation.py` | Four-step trip generation (Tier-1 only) |
| `src/w1_gravity_model.py` | Doubly-constrained gravity model (Furness IPF) |
| `src/w1_demand_surface.py` | Vehicle-ownership transit-propensity weighting |
| `src/w2_eod_ingest.py` | EOD 2022 shapefile ingestion (auto-detects format via /vsizip/) |
| `src/w2_gravity_calibration.py` | Beta calibration against EOD desire lines via scipy |
| `src/w3_accessibility.py` | GTFS transit accessibility (networkx Dijkstra, 45 min budget) |
| `src/w3_coverage_gap.py` | Coverage-gap index (demand / accessibility) |
| `src/w3_retrain.py` | RF + LightGBM on high-gap binary target, SHAP interpretability |
| `src/geo_restrictions.py` | OSM extraction for 10 ZMG municipalities via `osmnx` |
| `src/phase3_weighting.py` | CRITIC + Entropy Weight Method (to be repositioned as W4) |
| `src/phase4_clustering.py` | K-Means++ typology assignment (descriptive only) |
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
- **DDL migration semicolon bug:** The `run_sql_file` helper in all run_w*.py scripts splits SQL on `;`. Any `COMMENT ON TABLE ... IS '...'` string that itself contains a semicolon will be split mid-statement and fail. All current migrations have had COMMENT statements removed to avoid this. Do not add `COMMENT ON TABLE` statements to future migrations unless you use a smarter SQL splitter.
- **Windows CP1252 console encoding:** Non-ASCII characters (e.g. `↔`, `—`) in print statements inside subprocess-launched scripts cause `UnicodeEncodeError` on Windows. Use plain ASCII in all `print()` calls in `src/` files.
- **671 AGEBs with zero transit accessibility:** These are AGEBs with no GTFS stops within 400m. They receive `accessibility_score=0` and are assigned to the highest-gap quintile by default. Verify before W4 that these are genuinely unserved, not a GTFS coverage gap.

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

**Known W1 limitations (addressed in W2/W3):**
- Euclidean distance proxy retained — W2 calibration found beta=2.0 is already the best-fitting value at zone level; network distances not pursued further
- `beta=2.0` confirmed as W1 prior via W2 calibration (see W2 section)
- 187 AGEBs with alpha-suffix `cve_ageb` passed through from CPV2020 — minor effect, not cleaned; acceptable for thesis
- 171 AGEBs with `vehicle_rate=1.0` have `transit_demand=0`; these show as Low-gap in W3 (low demand → low gap), which is the correct treatment for high car-ownership areas

**Invariants maintained:**
- All spatial ops in EPSG:6372; OD network distances computed in metres
- Output demand surface joins cleanly to `base.ageb` on `cve_ageb`
- Gravity model runnable with Tier-1 only (EOD 2022 is calibration, not a hard dependency)

## W2 — Survey Calibration (completed 2026-06-15)

W2 calibrates the W1 gravity model's distance-decay parameter against EOD 2022 observed OD flows and documents the transfer error.

**Completed sub-tasks:**

1. **W2.1 — EOD data ingestion** (`src/w2_eod_ingest.py`)
   - Format: all EOD files are shapefiles inside zip archives; read via `/vsizip/` URI (not `zip://`, which breaks with pyogrio)
   - Zone polygons (`Zonificación...zip`): 71 survey zones, EPSG:32613 → reprojected to 6372
   - Productions (`viajes_ori`) and attractions (`viajes_atr`) joined from polygon attribute shapefiles (not tabular CSVs)
   - Desire lines (`Líneas de deseo...zip`): both the 5k–10k and 10k–47k files contain **identical** complete OD matrices (4,970 directed zone pairs, 3,511 non-zero); column names are `zona_de_or`, `zona_de_de`, `total_de_v`
   - Output: `raw.eod_zones` (71 rows), `raw.eod_desire_lines` (3,509 pairs after dedup + zero-drop)

2. **W2.2/W2.3 — Gravity calibration** (`src/w2_gravity_calibration.py`)
   - Spatial join: 2,005 of 2,068 AGEBs matched to 63 of 71 zones (63 AGEBs outside zone boundaries)
   - Calibration: `scipy.optimize.minimize_scalar` on log-space SSE, beta search range 0.5–5.0
   - **Result: beta=2.0 (W1 prior) retained.** The calibrated optimum hit the upper boundary (5.0) with worse RMSE (10,861 vs 5,215 for beta=2.0) and R²=−3.31. Likely cause: zone-AGEB aggregation mismatch at very different spatial scales. Documented in `outputs/w2/calibration_report.md`.
   - Output: `features.w2_calibration`, `outputs/w2/zone_od_comparison.csv`, `outputs/w2/calibration_report.md`

**Orchestrator:** `src/run_w2.py`

**Key files:**
- `src/w2_eod_ingest.py`, `src/w2_gravity_calibration.py`, `src/run_w2.py`
- `db_setup/migrations/003_w2_eod_tables.sql`

---

## W3 — Supply & Coverage-Gap Layer (completed 2026-06-15)

W3 builds an independent transit supply measure, defines the coverage gap (the new dependent variable), and re-trains the supervised model on it.

**Completed sub-tasks:**

1. **W3.1 — GTFS-based transit accessibility** (`src/w3_accessibility.py`)
   - GTFS files in `data/`: 12,231 stops, 49,066 stop-time records, 970 trips with headway data
   - Transit graph: 10,650 nodes, 12,744 directed edges (consecutive stop pairs, minimum IVT per pair)
   - Spatial join: 17,210 AGEB-stop pairs within 400m (avg 7 boarding stops per AGEB, max 48)
   - Travel budget: 45 min total = walk time (dist/80 m·min⁻¹) + wait time (headway/2) + in-vehicle time
   - Dijkstra per boarding stop using networkx; employment at catchment AGEBs of reachable stops summed
   - Result: 1,397 AGEBs with non-zero accessibility, 671 with zero (no stops within 400m)
   - Output: `features.ageb_accessibility`; CSV at `outputs/w3/ageb_accessibility.csv`

2. **W3.2 — Coverage-gap index** (`src/w3_coverage_gap.py`)
   - `coverage_gap_raw = transit_demand / (accessibility_score + 1.0)`
   - Normalized with log1p + min-max; quintile ranks for demand and accessibility; categorical labels
   - Gap categories: **428 High-gap** (20.7%), 1,560 Medium-gap, 80 Low-gap
   - High-gap definition: demand quintile ≥ 4 AND access quintile ≤ 2
   - Output: `features.ageb_coverage_gap`; CSV at `outputs/w3/ageb_coverage_gap.csv`

3. **W3.3 — Model retrain on coverage-gap target** (`src/w3_retrain.py`)
   - Binary target: `is_high_gap = 1` if `gap_category == 'High-gap'` else 0
   - Features: 14 normalized NPP-V indicators — all transit-supply variables excluded (`route_km_800m`, `stops_*`) to prevent circularity
   - **Test metrics:** LightGBM PR-AUC 0.871, ROC-AUC 0.962; RF PR-AUC 0.862, ROC-AUC 0.956 — no leakage flags
   - **Top SHAP drivers (LightGBM):** `pe_population_n` > `p_employment_proxy_n` > `pe_rezago_n` > `pe_marginacion_n` > `n_intersection_density_n` — high-gap areas are dense, high-need, employment-rich zones not served by current SITEUR network
   - Output: `outputs/w3/models/`, `outputs/w3/metrics/`, `outputs/w3/shap/`; run ID `w3_coverage_gap_v1`

**Orchestrator:** `src/run_w3.py` (timeout 7,200s for accessibility step)

**Key files:**
- `src/w3_accessibility.py`, `src/w3_coverage_gap.py`, `src/w3_retrain.py`, `src/run_w3.py`
- `db_setup/migrations/004_w3_tables.sql`

---

## Next Steps (W4 onward)

Per `docs/game_plan_demand_driven_restructure.md`:

**W4 — Reposition NPP-V as prioritization/equity layer (next)**
- Reframe NPP-V scores + CRITIC/EWM weights as a multi-criteria prioritization diagnostic, not a demand estimator
- Fold equity indicators (`pe_marginacion`, `pe_rezago`) as explicit equity weights on prioritization
- Apply SHAP from W3.3 to explain which NPP-V factors drive the W3 coverage-gap — this connects the two layers
- No new DB tables needed; primarily a methods reframing + updated outputs from existing `features.nppv_weights`

**W4 design decisions (locked 2026-06-15):**
- **W4 output scope: report + charts + GeoJSON + cluster profile update.** Outputs: (1) `features.nppv_prioritization` DB table; (2) markdown report with weight table and ranked AGEB list; (3) bar chart of NPP weights and npp_score vs final_score scatter; (4) QGIS-ready GeoJSON of all 2,068 AGEBs with `npp_score`, `equity_score`, `final_score`; (5) updated Phase 4 cluster profiles showing mean scores per cluster (A/B/C) to connect descriptive segmentation to prioritization.
- **W4 scores all 2,068 AGEBs** (not only High-gap ones). W4 is a full-coverage NPP + equity prioritization map; W6 applies the W3 gap as a pre-filter when selecting corridor anchors. This keeps W4 independent of W3's threshold choices and makes the prioritization map reusable if gap thresholds change.
- **Equity integration: additive bonus term (option B).** Three approaches considered: (A) boost `pe_marginacion_n`/`pe_rezago_n` weights inside CRITIC/EWM by a manual multiplier — rejected because an arbitrary multiplier undermines R3's "no expert weighting" claim; (B) additive equity term after CRITIC/EWM: `final_score = (1 - α) × npp_score + α × equity_score` where `equity_score = mean(pe_marginacion_n, pe_rezago_n)` and α=0.20 — chosen because it is transparent, separable, and the thesis can report scores with and without the equity term, making trade-offs explicit; (C) equity as a tie-breaker/rank modifier within quintiles — rejected because it makes the equity contribution invisible in the continuous score. **α=0.20 is the documented default; sensitivity analysis with α∈{0.10, 0.20, 0.30} should be reported.**
- **Vitality dimension dropped entirely from W4 CRITIC/EWM.** `v_ridership_annual_n` is a municipality-level proxy (all AGEBs in a SITEUR municipality share the same value), so after normalization it behaves as a binary "has SITEUR" flag — providing zero AGEB-level discrimination and dominating ensemble weight (0.2519) for the wrong reason. Two alternatives were considered: (a) replace with W1 `transit_demand_n`, rejected because feeding modeled demand back into the prioritization score blurs the clean conceptual separation between the demand layer (W1/W3) and the place-characteristics layer (NPP-V); (b) keep `v_ridership_annual_n`, rejected because the known defect would be inherited. Decision: run CRITIC/EWM on the **14 NODE + PLACE + PEOPLE indicators only**. The framework is renamed from NPP-V to NPP (Node-Place-People) for W4 onward, or framed as "NPP-V with V replaced by the W3 coverage-gap index" depending on thesis framing preference. Demand signal lives exclusively in W1/W3; NPP captures place characteristics.

---

## W4 — NPP Prioritization Layer (completed 2026-06-15)

W4 repositions Phase 3's CRITIC/EWM weighting as a place-based prioritization map decoupled from demand/supply measures, introduces an explicit equity term, and scores all 2,068 AGEBs.

**Completed sub-tasks:**

1. **W4.1 — CRITIC + EWM weighting on 14 NPP features** (`src/w4_prioritization.py` lines 1–120)
   - Input: 14 normalized features from `features.nppv_features` (Node: 3, Place: 5, People: 6; Vitality dropped per design decision)
   - CRITIC step: standard deviation × correlation entropy, ranks features by importance
   - EWM step: proportional entropy weights, α=0.5 (equal weighting to CRITIC + EWM)
   - Output: `features.nppv_w4_weights` — one row per feature with `critic_weight`, `ewm_weight`, `ensemble_weight`
   - Example: `pe_population_n` scores high (dense, high-need areas); `p_land_use_mix_n` scores lower (less discriminating in ZMG)

2. **W4.2 — NPP + equity composite scoring** (`src/w4_prioritization.py` lines 121–160)
   - `npp_score = sum(feature_n × ensemble_weight)` over 14 features per AGEB; normalized [0, 1]
   - `equity_score = mean(pe_marginacion_n, pe_rezago_n)` — average of two poverty/deprivation indicators
   - `final_score = 0.80 × npp_score + 0.20 × equity_score` (α=0.20, documented default per W4 design decision)
   - Ranks, quintiles, and ratio `final_score / npp_score` computed for diagnostics
   - Output: `features.nppv_prioritization` — 2,068 rows, all AGEBs scored

3. **W4.3 — Export + visualization** (`src/w4_prioritization.py` lines 161–200)
   - **CSV outputs:** `nppv_w4_weights.csv` (14 rows), `nppv_prioritization.csv` (2,068 rows)
   - **GeoJSON:** `nppv_prioritization.geojson` — all AGEBs with geometries, scores, and rank quintiles
   - **Charts:** (a) `nppv_w4_weights_bar.png` — ensemble weights sorted descending; (b) `nppv_score_vs_equity.png` — scatter plot npp_score vs final_score, colored by equity_score
   - **Cluster profiles:** `cluster_priority_profiles.csv` — mean/median scores per K-Means cluster (A/B/C), connecting Phase 4 segmentation to W4 prioritization
   - **Report:** `w4_report.md` — weight table, top/bottom 20 AGEBs by final_score, methodology + design decisions

**Orchestrator:** `src/run_w4.py` — runs DDL migration 005 + w4_prioritization.py in sequence.

**Key files (all created):**
- `src/w4_prioritization.py`
- `src/run_w4.py`
- `db_setup/migrations/005_w4_tables.sql`
- `outputs/w4/{nppv_w4_weights.csv, nppv_prioritization.csv, nppv_prioritization.geojson, nppv_w4_weights_bar.png, nppv_score_vs_equity.png, cluster_priority_profiles.csv, w4_report.md}`

**Key results:**
- **14 CRITIC/EWM weights computed** — top drivers: `pe_population_n` (0.1186), `p_employment_proxy_n` (0.1063), `pe_rezago_n` (0.1052)
- **All 2,068 AGEBs ranked** — mean npp_score=0.500, mean equity_score=0.527, mean final_score=0.506
- **Cluster priority profiles:** Cluster 0 (474 AGEBs, npp_score=0.24) = low-priority peripheral areas; Cluster 1 (442 AGEBs, npp_score=0.66) = high-priority dense urban cores; Cluster 2 (1,152 AGEBs, npp_score=0.55) = medium-priority transitional/suburban
- **No circularity risk:** W4 uses only NPP-V place characteristics + equity; decoupled from W1 demand and W3 accessibility; safe to apply as prioritization lens

**Invariants maintained:**
- All spatial ops in EPSG:6372; outputs join cleanly to `base.ageb` on `cve_ageb`
- 14 features (Node+Place+People) exclude supply-side variables (`route_km_800m`, `stops_*`) and vitality proxy (`v_ridership_annual`)
- Equity term (α=0.20) is transparent and documented; thesis can report sensitivity analysis with α∈{0.10, 0.20, 0.30}
- W4 scores all AGEBs; W6 applies W3 gap as pre-filter when selecting anchors — clean separation of concerns

**Next: W5 multi-objective function (depends on no upstream changes)**

---

**W5 — Multi-objective function (blocks W6 and W7)**
- Define the formal optimality criterion: maximize demand-weighted accessibility gain, minimize route-km cost, add equity term (W4), add transfer penalty
- Specify constraints: max detour ratio, stop-spacing standards, minimum demand threshold, route-length cap
- Recommend Pareto/NSGA-II framing so trade-offs are explicit
- Output: a written spec + code skeleton reused by both W6 and W7

**W6 — New corridor generation (depends on W3 + W5)**
- Anchor selection from `features.ageb_coverage_gap` (high-gap AGEBs) using Jenks natural breaks, not arbitrary thresholds
- Population-weighted centroids snapped to OSM drive graph
- Steiner/MST as connectivity scaffold; evaluate candidates against W5 objective; optionally run NSGA-II
- Mode assignment by corridor demand volume vs. BRT/local-bus capacity bands
- Output: ranked corridor candidates as GeoJSON with objective-function scores

**W7 — Existing route audit (depends on W5, uses GTFS from W3)**
- Load SITEUR GTFS shapes; score each route/segment against W5 terms
- Flag low-demand, redundant, or highly indirect segments
- Propose modifications via demand-weighted shortest paths; report before/after objective scores
- Output: route scorecard + modification proposals GeoJSON

**W8 — Validation**
- Backtest: mask high-ridership network segments; test whether W6 re-proposes them
- Benchmark against announced ZMG expansions (Mi Macro Periférico, Línea 4/5)
- Quantitative: coverage rate, pop-served/route-km, accessibility Gini before/after

## Methodological References

- Bertolini (1996/1999): Node-Place Model
- Liu et al. (2024/2025): NP-RV Model, LightGBM+SHAP
- Niu et al. (2023): Random Forest for station suitability
- Takahashi (1980): Steiner Tree heuristic for network design
