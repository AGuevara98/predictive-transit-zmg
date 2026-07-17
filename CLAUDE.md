# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Master's thesis: a **7-phase geospatial ML pipeline** to predict optimal transit route placement in the Zona Metropolitana de Guadalajara (ZMG), implementing the **NPP-V** (Node-Place-People-Vitality) framework. The unit of analysis is the **AGEB** (census enumeration area); 1,881 AGEBs in 10 ZMG municipalities (corrected 2026-06-19; see errata near the end of this file -- most W1-W8 numbers throughout this doc predate the correction and are being updated as sections are revisited).

**The pipeline is being re-architected** into a demand-driven, transferable framework per `docs/game_plan_demand_driven_restructure.md`. The work is organized as workstreams W0–W9.

**Workstream status:**
- W0 (Remediation): ✅ Complete — see errata below
- W1 (Demand Estimation Layer): ✅ Complete — `ageb_trip_ends` + `ageb_od_matrix` in DB; transit_demand surface written; gravity model re-run 2026-06-25 on the W2-calibrated beta=1.2005 (was 2.0); see W1 section below
- W2 (Survey Calibration): ✅ Complete — EOD 2022 ingested; **beta=1.2005 outperforms the beta=2.0 prior** as of the 2026-06-19 base.ageb correction, and was adopted into `w1_gravity_model.py` on 2026-06-25 (W1/W3/W6/W7/W8 re-run); see W2 section below
- W3 (Supply & Coverage-Gap Layer): ✅ Complete — accessibility surface + coverage-gap index in DB; model retrained on external target; re-run 2026-06-25 on beta=1.2005 demand surface; see W3 section below
- W4 (Reposition NPP-V): ✅ Complete — features.nppv_prioritization in DB; 14 NODE+PLACE+PEOPLE features; final_score=(0.80*npp_score)+(0.20*equity_score); see W4 section below
- W5 (Multi-objective function): ✅ Complete — code skeleton (types, objective, constraints, Pareto) + spec contract for W6/W7; 39 tests; see W5 section below
- W6 (New corridor generation): ✅ Complete — **re-architected 2026-07-15** into frontier anchors + MST-diameter-trunk shaper + anchor-directness feasibility gate (see the "W6 re-architecture" entry below). 4 feasible corridors (W6_G00/G01/G02/G03; G05 rejected on directness 1.93); **W6_G02 is the first substantive corridor to pass W8 Question B** (56% High-gap, unique, 73rd-pct demand/km — a real 12.1km/25-AGEB line, not a stub). Prior state (superseded): 3 BRT corridors via baseline anchors + MST-flatten + hub injection. See W6 section below.
- **W6**: superseded — the `ANCHOR_TRIM_COL` / hub-injection notes below predate the 2026-07-15 re-architecture; hub injection and the MST-flatten shaper are retired.
- W7 (Existing route audit): ✅ Code complete — 247 SITEUR routes scored via W5 (route count reflects the current GTFS snapshot in `data/gtfs/`, not the base.ageb correction); Low-demand/Indirect/Redundant flags; modification proposals; `straight_line_km` fixed 2026-06-24 for closed-loop routes (was collapsing to ~0); re-run 2026-06-25 on beta=1.2005 (flag totals unchanged: 229 flagged); 43 tests; see W7 section below
- W8 (Validation): ✅ Code complete — backtest + benchmark + before/after metrics run end-to-end via `python src/run_w8.py`; see W8 section below
- **W8**: append — "First out-of-sample validation run 2026-07-12 (Line 4 backtest). Diagnostic
  layer corroborated; generative layer does NOT reconstruct Line 4. See W8 Line 4 section."
- W9 (Transferability): 🔄 In progress — Tier-1 pipeline for Monterrey operational; DENUE + AGEB shapefile + OSM graph acquired; GTFS still needed for W3 equivalent; see W9 section below

**Legacy phase status (pre-restructure):**
- Phase 1 (Data Acquisition): ✅ Complete
- Phase 2 (Feature Engineering + Binary ML Suitability): 🗑️ Retired 2026-06-24 — code (`phase2_*.py`) already deleted in the W1-W9 restructure (448f14a); baseline `no_stop_features_v1` was a tautological "has-a-stop" target on corrupted DEM-derived `slope_mean`; fully superseded by W3.3's coverage-gap retrain. Outputs removed from `outputs/phase2/`.
- Phase 3 (CRITIC/EWM Objective Weighting): ✅ Complete — weights in `features.nppv_weights`; **repositioned as W4 prioritization layer**
- Phase 4 (K-Means Clustering / Transit Suitability Typologies): ✅ Complete — clusters in `features.nppv_clusters`; **kept as descriptive segmentation only**
- Phase 5 (Predictive Modeling & Interpretability): 🗑️ Retired 2026-06-24 — RF + XGBoost on K-Means labels (1.0000 accuracy, tautological); fully superseded by W3.3's coverage-gap retrain. Outputs removed from `outputs/phase5/`.
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

**Run workstream orchestrators** (legacy `run_phase*.py`/`run_phase*_wsl.sh` scripts were removed in the W1-W9 restructure, commit 448f14a):
```bash
bash scripts/bootstrap.sh   # from-scratch DB build: createdb -> DDL -> load data -> build_nppv_features.py
python src/run_w1.py        # then run_w2.py ... run_w9.py in sequence
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

**Environment variable overrides** (for production) — set the `PG_*` names; `config.sh`
reads the same `PG_*` vars and re-exports them as `DB_*` aliases for the shell scripts,
so one `export` configures both sides of the pipeline:
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
- `base.ageb` — 1,881 AGEB polygons (filtered: `CVE_ENT='14'`, no 'A' suffix in `CVE_AGEB`, 10 ZMG municipalities)
- `features.nppv_features` — **15** normalized NPP-V indicators per AGEB (`_n` suffix = normalized; `v_ntl_median` dropped per W0.1); table DDL in `db_setup/DDL.sql`, populated by `src/build_nppv_features.py`
- `features.nppv_weights` — CRITIC + Entropy Weight Method outputs (15 features)
- `features.nppv_clusters` — K-Means typology assignments (A/B/C), silhouette 0.58
- `features.ageb_suitability_predictions` — legacy Phase 2/5 model predictions; retired 2026-06-24, no longer written to by current code
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

3. **AGEB filter:** Exclude cells where `CVE_AGEB` contains 'A' and exclude non-ZMG municipality codes. See `db_setup/DDL.sql:56-58`.

4. **GIST indexes on all geometry columns.** Always `ANALYZE` after bulk inserts.

## Key Source Files

| File | Role |
|------|------|
| `scripts/bootstrap.sh` | Single entry point for a from-scratch DB build: createdb -> DDL -> load data -> `build_nppv_features.py` |
| `src/build_nppv_features.py` | Builds `features.nppv_features` (15 raw + 15 normalized indicators) from committed census/DENUE/indicators/ridership inputs; replaces the deleted `phase2_db_setup.py`/`phase2_feature_engineering.py` |
| `src/db_preflight.py` | `ensure_nppv_features(engine)` - self-heals a missing/empty `nppv_features` table; wired into run_w1/w3/w4/w8.py |
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

## Phase 2 Model State (retired 2026-06-24)

The legacy Phase 2 model (`no_stop_features_v1` baseline, `src/phase2_train_models.py`) predicted a target derived from Phase 4's K-Means cluster labels — tautological by construction, and its `slope_mean` feature was later found to be computed from a mis-tagged DEM raster (see 2026-06-19 errata). Rather than re-run it on the corrected DEM, the model was retired: it predicted a target with no independent validity, so a clean re-run would still not have been citable. `src/phase2_train_models.py` was already deleted in the W1-W9 restructure (448f14a); its outputs (`outputs/phase2/`) have now been removed too.

It is fully superseded by **W3.3** (`src/w3_retrain.py`), which trains on the same 14 NPP-V feature set but against the independently-derived coverage-gap target (`is_high_gap`) instead of the circular cluster-label target — see the W3 section below for current metrics (LightGBM PR-AUC 0.842, ROC-AUC 0.960).

## W0 Errata (completed 2026-06-14)

Three integrity defects fixed before W1 work begins:

1. **`v_ntl_median` dropped (W0.1):** VIIRS VNP46A3 HDF5 zonal-stats silently failed (try-except swallowed a rasterio error; tile bounds from `WestBoundingCoordinate` attrs may have mismatched). All 2,068 values were zero. Feature removed at the time from `phase2_feature_engineering.py`, `phase3_weighting.py`, `phase2_db_setup.py` (since deleted in the W1-W9 restructure, commit 448f14a), and the live DB via `db_setup/migrations/001_drop_ntl_columns.sql`. The feature is built today by `src/build_nppv_features.py`, which does not include `v_ntl_median`. Vitality dimension is now single-proxy: `v_ridership_annual`.

2. **Phase 5 weight join fixed (W0.2):** `phase5_report.py` was appending `_n` to feature names that already ended in `_n`, producing `n_intersections_n_n` — no matches, all Phase 3 weights showed 0.0000. Fixed by removing the erroneous suffix concatenation. Report also updated with an errata block flagging the 1.0000 cluster-recovery accuracy as a tautology.

3. **Scaling fixed (W0.3):** Replaced global min-max with `log1p + minmax` for 10 right-skewed count/economic features (`p_employment_proxy`, `p_poi_density`, population/density, ridership, street metrics). Bounded ratios (`pe_marginacion`, `pe_dep_ratio`, `pe_youth_share`, `p_land_use_mix`) keep plain min-max. Phases 2–4 re-run after this change.

**Known remaining issue:** `v_ridership_annual` is assigned at municipality level (all AGEBs in a municipality share the same value), so after normalization it functions as a binary "has SITEUR" flag. This produces a geographic cluster split (B = SITEUR municipalities) rather than AGEB-level demand signal. Will be replaced by W1 trip-generation estimates.

## Known Issues

- **DEM raster not in git:** `continuonacional_15m.tif` (~7.2 GB) must be downloaded manually from the INEGI CEM 3.0 portal and placed in `data/`. The `LEFT JOIN` in `master_suitability` and `COALESCE(topo.slope_mean, 0)` handle missing raster rows gracefully. Must be loaded with `raster2pgsql -s 6365 -t 100x100` (the DEM's true CRS); loading with the wrong SRID produces a raster that doesn't spatially match `base.ageb` at all, so the topography `JOIN` either matches zero rows or, worse, silently computes geometrically meaningless slope values without erroring -- see 2026-06-19 errata, this happened to the live `gdl_metro` DB.
- **DDL migration semicolon bug:** The `run_sql_file` helper in all run_w*.py scripts splits SQL on `;`. Any `COMMENT ON TABLE ... IS '...'` string that itself contains a semicolon will be split mid-statement and fail. All current migrations have had COMMENT statements removed to avoid this. Do not add `COMMENT ON TABLE` statements to future migrations unless you use a smarter SQL splitter.
- **Windows CP1252 console encoding:** Non-ASCII characters (e.g. `↔`, `—`) in print statements inside subprocess-launched scripts cause `UnicodeEncodeError` on Windows. Use plain ASCII in all `print()` calls in `src/` files.
- **615 AGEBs with zero transit accessibility** (out of 1,881; see 2026-06-19 errata for the AGEB-count correction): These are AGEBs with no GTFS stops within 400m. They receive `accessibility_score=0` and are assigned to the highest-gap quintile by default. Verify before W4 that these are genuinely unserved, not a GTFS coverage gap.
- **features.nppv_features is built by `src/build_nppv_features.py`** (post-W0; log1p+minmax, no v_ntl_median). It is re-derivable from committed inputs and auto-built by `ensure_nppv_features()` preflight in run_w1/w3/w4/w8. The old phase2 builders were removed in the restructure (448f14a). A from-scratch rebuild reproduces place/people/equity columns at Spearman rho~1.0, but the 3 node/street features drift (rho ~0.67-0.86) because the OSM drive graph is pulled live via `osmnx` on first build; see `tests/test_nppv_oracle.py`.

## 2026-06-19 Errata — base.ageb, DEM raster, and W1–W8 fresh-clone fixes

A full `bootstrap.sh` → `DDL.sql` → `build_nppv_features.py` → `run_w1.py`...`run_w8.py` run against a throwaway test database (and then against the live `gdl_metro` DB) surfaced three defects that had been silently present since before the W1–W9 restructure. **The corrected, current AGEB universe is 1,881 rows** (10 ZMG municipalities, alpha-suffix `cve_ageb` excluded) — not the 2,068 cited throughout most of this document below this point; sections are being corrected as revisited, but treat any uncorrected "2,068" you find as stale.

## 2026-07-12 Errata — pe_marginacion sign inversion + zero-fill
 
Two stacked defects in the equity input `pe_marginacion` (src/build_nppv_features.py), found
while validating the equity term against the source CONAPO data.
 
1. **Sign inversion.** `pe_marginacion` is CONAPO's `IM_2020` (verified byte-identical to the
   official AGEB file on the overlap; provenance confirmed). CONAPO's 2020 index runs
   **higher = LESS marginalized** (mean IM by grade: Muy alto 112.5, Alto 117.4, Medio 119.9,
   Bajo 122.3, Muy bajo 124.8 -- monotonic). The code used it directly in
   `equity_score = mean(pe_marginacion_n, pe_rezago_n)`, which treats higher = more need, so the
   marginacion half rewarded the LEAST-marginalized areas, opposing the rezago half (`IRS_2020`,
   correctly higher = more rezago).
2. **Zero-fill.** The ~200 ZMG AGEBs absent from CONAPO's *urban* index (1,868 of the 2,068 in
   `ageb_zmg_2020_v2.gpkg` matched; ~200 non-urban unmatched) were `.fillna(0)`. Since IM_2020
   floors near ~102, 0 is out-of-range and dragged the min-max floor down, compressing real
   values into [0.80, 1.0]. The two bugs partially masked each other (compression muted the
   inverted signal), so the pre-fix equity term was effectively rezago-dominated; fixing the
   zero-fill alone would have amplified the inversion -- both had to be fixed together.
 
**Fix (src/build_nppv_features.py):** raw `pe_marginacion` stays the literal CONAPO IM_2020;
direction corrected in `normalize_feature` via `INVERTED_FEATURES` (`pe_marginacion_n =
1 - minmax(IM_2020)`); the missing AGEBs are median-imputed (skipna) instead of zero-filled.
`pe_rezago` (IRS_2020) keeps its correct direction; its gaps are also median-imputed, not zeroed.
 
**Verified:** post-fix `pe_marginacion_n` monotonic by grade (Muy alto 0.606 highest -> Muy bajo
0.108 lowest); `equity_score` monotonic by grade after W4 re-run (Muy alto 0.500 -> Muy bajo
0.095); no nulls in any `_n` column. Aggregate shifts consistent with de-inversion:
`equity_score` mean 0.527 -> 0.227, `npp_score` mean 0.500 -> 0.4595, `final_score` 0.506 ->
0.4131 (ZMG is mostly low-marginalization, so a correctly-signed need score should average low).
 
**Impact:** re-ran build -> W4. W3.3 SHAP *direction* of `pe_marginacion_n` flips (tree metrics
unchanged -- invariant to monotonic transforms; re-run run_w3 to refresh plots). W6/W7/W8
unaffected (they use `coverage_gap_n`, not the equity term). Oracle `data/raw/nppv_features.csv`
regenerated; `tests/test_nppv_oracle.py` row-count assertion corrected 2000 -> 1881 (stale since
the 2026-06-19 base.ageb correction). W9's W4-equivalent must reuse `INVERTED_FEATURES` when built.

1. **`db_setup/DDL.sql` municipality-code typo (since the initial commit):** the `base.ageb` filter's `cve_mun IN (...)` list had `'009'` instead of `'002'` (Acatlán de Juárez). Silently dropped that whole municipality on every from-scratch bootstrap. Fixed to `'002'`.
2. **`build_nppv_features.py` read AGEBs from unfiltered `raw.ageb` instead of `base.ageb`:** `features.nppv_features` ended up carrying alpha-suffix AGEBs that don't exist in `base.ageb`, which broke `run_w4.py`'s FK-constrained write the moment `base.ageb` was correctly filtered (it was previously masked because the live DB's `base.ageb` had also never actually been rebuilt by `DDL.sql` — see point 4). Fixed `load_agebs()` to read `base.ageb`.
3. **DEM raster loaded with the wrong SRID in the live `gdl_metro` DB:** `raw.dem` was tagged SRID 4326 with 512×512 tiles (instead of the DEM's true CRS, 6365, at 100×100 tiles — see the DEM bullet in Known Issues above). This produced geometrically meaningless `slope_mean` values (observed range ~3,931–27,541 in `features.master_suitability`, not the plausible 0–~20 range produced after the fix). `slope_mean` was a documented top-3 SHAP driver for the legacy Phase 2 model (`no_stop_features_v1`), which was retired 2026-06-24 rather than re-run on the corrected DEM — see "Phase 2 Model State" above. Fixed by reloading `raw.dem` via `raster2pgsql -d -s 6365 -I -C -M -t 100x100`.
4. **Root cause tying 1-3 together:** the live `gdl_metro` database's `base.ageb` (2,068 rows, all 10 munis, all 187 alpha-suffix AGEBs included) was never actually rebuilt by the checked-in `DDL.sql` — it predates it. Every Phase 1–8 / W1–W9 number in this document was computed against that never-actually-reproducible 2,068-row table. `gdl_metro`'s `base.ageb`, `raw.dem`, `features.nppv_features`, and `features.ageb_trip_ends` through `features.route_audit`/`features.nppv_prioritization` have now been rebuilt with the fixes above; W1–W8 outputs under `outputs/` reflect the corrected 1,881-AGEB run as of 2026-06-19. **Phase 1-2 (legacy) have not been re-run** — `no_stop_features_v1`'s reported SHAP ranking still reflects the corrupted DEM.
5. **Substantive finding, not a bug:** W2's gravity-model calibration changes conclusion under the corrected universe — see the W2 section. `w1_gravity_model.py` was updated to `BETA=1.2005` on 2026-06-25, and W1/W3/W6/W7/W8 were re-run on it — see those sections for updated results.
6. Two smaller fresh-clone breaks fixed in the same pass: `w4_prioritization.py` hard-crashed when the legacy Phase 4 `features.nppv_clusters` table doesn't exist (now skips that step with a log line instead of aborting -- the live DB still has this table from a prior Phase 4 run, so it isn't exercised there); `run_w8.py`/`w8_backtest.py`/`w8_benchmark.py` pointed `DATA_DIR` at `data/` instead of `data/gtfs/`.
7. A `pg_dump` backup of `gdl_metro` was taken immediately before these fixes were applied (`/home/aguevara/db_backups/gdl_metro_pre_ageb_fix_*.dump`) in case any number here needs to be cross-checked against the pre-fix state.

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

**Normalization:** log1p + min-max for count/economic features; plain min-max for bounded ratios. See `LOG_FEATURES` in `src/build_nppv_features.py`.

The legacy Phase 2 model (`no_stop_features_v1`) is retired — see "Phase 2 Model State" above. Its successor, W3.3, drives off these same 14 indicators; top SHAP drivers there are `pe_population_n` > `pe_rezago_n` > `p_employment_proxy_n`.

## W1 — Demand Estimation Layer (completed 2026-06-15)

W1 replaces the circular "has-a-stop" target with an explicit modeled transit-demand surface using **only Tier-1 data** (census, DENUE, OSM) — no existing transit supply as input.

**Completed sub-tasks:**

1. **W1.1 — Trip generation** (`src/w1_trip_generation.py`)
   - Productions: `2.5 trips/person/day × population × (1 + 0.10 × youth_share)`
   - Attractions: weighted sum of `p_employment_proxy`, `p_poi_density × area_km2`, `p_retail_density × area_km2`; scaled so `sum(A) = sum(P)`
   - Output: `features.ageb_trip_ends` — 1,881 rows with `productions`, `attractions`

2. **W1.2 — Doubly-constrained gravity model** (`src/w1_gravity_model.py`)
   - Power-law impedance `f(d) = d^(-1.2005)` — calibrated value adopted 2026-06-25 (was the `d^(-2.0)` prior; see W2 below); Furness IPF with `tol=1e-5`, `max_iter=300`
   - Euclidean centroid distances in EPSG:6372 (metres); self-flows zeroed on diagonal
   - Sparse OD matrix: pairs with `modeled_flow >= 0.5` stored
   - Output: `features.ageb_od_matrix`; summary at `outputs/w1/od_matrix_summary.csv`
   - **Effect of the beta=2.0 → 1.2005 re-run (2026-06-25):** `total_flow` unchanged (11,816,597 — Furness IPF conserves marginals); `n_pairs_stored` 987,491 → 1,446,695 (+46%, slower decay pushes more pairs above the 0.5 flow threshold); `mean_dist_m_filtered` 12,417m → 14,107m (flows now reach farther); `mean_flow_filtered` 11.79 → 8.03 (diluted by the larger pair count)

3. **W1.3 — Transit-demand surface** (`src/w1_demand_surface.py`)
   - `vehicle_rate = VPH_AUTOM / VIVPAR_HAB.clip(1)`, clipped to [0, 1]; VIVPAR_HAB=0 handled via `clip(lower=1)`
   - `transit_propensity = 1 - vehicle_rate`; `transit_demand = total_demand × transit_propensity`
   - Mean-fill fallback for AGEBs not matched in CPV2020 (mean computed on non-NaN values — correct)
   - Output: `features.ageb_trip_ends` updated with `vehicle_rate`, `transit_propensity`, `transit_demand`; CSV at `outputs/w1/ageb_demand_surface.csv`
   - Run stats: 1,881 rows, avg_vehicle_rate=0.577, avg_transit_prop=0.423

**Orchestrator:** `src/run_w1.py` — runs DDL migration + all three modules in sequence.

**Key files (all created):**
- `src/w1_trip_generation.py`, `src/w1_gravity_model.py`, `src/w1_demand_surface.py`, `src/run_w1.py`
- `db_setup/migrations/002_w1_demand_tables.sql`
- `tests/test_w1_gravity_model.py` (5 Furness IPF unit tests — all passing)
- `outputs/w1/ageb_trip_ends.csv`, `outputs/w1/od_matrix_summary.csv`, `outputs/w1/ageb_demand_surface.csv`

**Known W1 limitations (addressed in W2/W3):**
- Euclidean distance proxy retained — `w1_gravity_model.py` now uses the W2-calibrated `BETA=1.2005` (adopted 2026-06-25; see the W2 section and 2026-06-19 errata below for the calibration history)
- 187 AGEBs with alpha-suffix `cve_ageb` are correctly excluded from `base.ageb` (per `db_setup/DDL.sql`'s `cve_ageb NOT LIKE '%A%'` filter) — `base.ageb` is 1,881 rows, not 2,068; see errata
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
   - Spatial join: 1,822 of 1,881 AGEBs matched to 63 of 71 zones (59 AGEBs outside zone boundaries)
   - Calibration: `scipy.optimize.minimize_scalar` on log-space SSE, beta search range 0.5–5.0
   - **Result (2026-06-19, re-run on corrected `base.ageb`): calibrated beta=1.2005, which now has a *better* fit than the W1 prior** — RMSE=4,524.9 vs 5,088.2 for beta=2.0, R²=0.2498 (n=1,993 zone pairs). This reverses the original finding below, which was computed on the never-actually-applied 2,068-AGEB `base.ageb` (see 2026-06-19 errata). **Adopted into `w1_gravity_model.py` on 2026-06-25; W1, W3, W6, W7, and W8 were re-run on the new beta — see those sections for updated results.**
   - Original (now superseded) finding, kept for reference: on the old, incorrectly-filtered base.ageb (2,068 rows), the calibrated optimum hit the search boundary (5.0) with worse RMSE (10,861 vs 5,215 for beta=2.0) and R²=−3.31, so beta=2.0 was retained.
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
   - GTFS files in `data/gtfs/`: 12,231 stops, 49,066 stop-time records, 970 trips with headway data
   - Transit graph: 10,650 nodes, 12,744 directed edges (consecutive stop pairs, minimum IVT per pair)
   - Spatial join: 15,491 AGEB-stop pairs within 400m (avg ~8 boarding stops per AGEB)
   - Travel budget: 45 min total = walk time (dist/80 m·min⁻¹) + wait time (headway/2) + in-vehicle time
   - Dijkstra per boarding stop using networkx; employment at catchment AGEBs of reachable stops summed
   - Result: 1,266 AGEBs with non-zero accessibility, 615 with zero (no stops within 400m) -- out of 1,881 (see 2026-06-19 errata); **confirmed unchanged by the 2026-06-25 beta=1.2005 re-run — accessibility is demand-independent by construction**
   - Output: `features.ageb_accessibility`; CSV at `outputs/w3/ageb_accessibility.csv`

2. **W3.2 — Coverage-gap index** (`src/w3_coverage_gap.py`)
   - `coverage_gap_raw = transit_demand / (accessibility_score + 1.0)`
   - Normalized with log1p + min-max; quintile ranks for demand and accessibility; categorical labels
   - Gap categories (re-run 2026-06-25 on beta=1.2005): **390 High-gap** (20.7%), 1,413 Medium-gap, 78 Low-gap -- out of 1,881 (was 389/1,413/79 under beta=2.0; one AGEB shifted Low→High-gap)
   - High-gap definition: demand quintile ≥ 4 AND access quintile ≤ 2
   - Output: `features.ageb_coverage_gap`; CSV at `outputs/w3/ageb_coverage_gap.csv`

3. **W3.3 — Model retrain on coverage-gap target** (`src/w3_retrain.py`)
   - Binary target: `is_high_gap = 1` if `gap_category == 'High-gap'` else 0
   - Features: 14 normalized NPP-V indicators — all transit-supply variables excluded (`route_km_800m`, `stops_*`) to prevent circularity
   - **Test metrics (re-run 2026-07-17, post equity-fix):** LightGBM PR-AUC 0.883, ROC-AUC 0.962; RF PR-AUC 0.877, ROC-AUC 0.962 — no leakage flags (supersedes the 2026-06-25 pre-equity-fix run: RF 0.872/0.965, LightGBM 0.835/0.961; shifts are from the `pe_marginacion` median-impute vs zero-fill, a non-monotonic change, not the de-inversion which is monotonic and tree-invariant)
   - **Top SHAP drivers (LightGBM, 2026-07-17):** `pe_population_n` > `pe_rezago_n` > `p_employment_proxy_n` > `pe_marginacion_n` > `n_intersection_density_n` — high-gap areas are dense, high-need, employment-rich zones not served by current SITEUR network; `pe_marginacion_n` SHAP *direction* is now correctly signed (de-inverted) in the refreshed `outputs/w3/shap/` beeswarm plots
   - Output: `outputs/w3/models/`, `outputs/w3/metrics/`, `outputs/w3/shap/`; run ID `w3_coverage_gap_v1`

**Orchestrator:** `src/run_w3.py` (timeout 7,200s for accessibility step)

**Key files:**
- `src/w3_accessibility.py`, `src/w3_coverage_gap.py`, `src/w3_retrain.py`, `src/run_w3.py`
- `db_setup/migrations/004_w3_tables.sql`

---

**W4 design decisions (locked 2026-06-15):**
- **W4 output scope: report + charts + GeoJSON + cluster profile update.** Outputs: (1) `features.nppv_prioritization` DB table; (2) markdown report with weight table and ranked AGEB list; (3) bar chart of NPP weights and npp_score vs final_score scatter; (4) QGIS-ready GeoJSON of all 1,881 AGEBs with `npp_score`, `equity_score`, `final_score`; (5) updated Phase 4 cluster profiles showing mean scores per cluster (A/B/C) to connect descriptive segmentation to prioritization.
- **W4 scores all 1,881 AGEBs** (not only High-gap ones). W4 is a full-coverage NPP + equity prioritization map; W6 applies the W3 gap as a pre-filter when selecting corridor anchors. This keeps W4 independent of W3's threshold choices and makes the prioritization map reusable if gap thresholds change.
- **Equity integration: additive bonus term (option B).** Three approaches considered: (A) boost `pe_marginacion_n`/`pe_rezago_n` weights inside CRITIC/EWM by a manual multiplier — rejected because an arbitrary multiplier undermines R3's "no expert weighting" claim; (B) additive equity term after CRITIC/EWM: `final_score = (1 - α) × npp_score + α × equity_score` where `equity_score = mean(pe_marginacion_n, pe_rezago_n)` and α=0.20 — chosen because it is transparent, separable, and the thesis can report scores with and without the equity term, making trade-offs explicit; (C) equity as a tie-breaker/rank modifier within quintiles — rejected because it makes the equity contribution invisible in the continuous score. **α=0.20 is the documented default; sensitivity analysis with α∈{0.10, 0.20, 0.30} should be reported.**
- **Vitality dimension dropped entirely from W4 CRITIC/EWM.** `v_ridership_annual_n` is a municipality-level proxy (all AGEBs in a SITEUR municipality share the same value), so after normalization it behaves as a binary "has SITEUR" flag — providing zero AGEB-level discrimination and dominating ensemble weight (0.2519) for the wrong reason. Two alternatives were considered: (a) replace with W1 `transit_demand_n`, rejected because feeding modeled demand back into the prioritization score blurs the clean conceptual separation between the demand layer (W1/W3) and the place-characteristics layer (NPP-V); (b) keep `v_ridership_annual_n`, rejected because the known defect would be inherited. Decision: run CRITIC/EWM on the **14 NODE + PLACE + PEOPLE indicators only**. The framework is renamed from NPP-V to NPP (Node-Place-People) for W4 onward, or framed as "NPP-V with V replaced by the W3 coverage-gap index" depending on thesis framing preference. Demand signal lives exclusively in W1/W3; NPP captures place characteristics.

---

## W4 — NPP Prioritization Layer (completed 2026-06-15)

W4 repositions Phase 3's CRITIC/EWM weighting as a place-based prioritization map decoupled from demand/supply measures, introduces an explicit equity term, and scores all 1,881 AGEBs.

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
   - Output: `features.nppv_prioritization` — 1,881 rows, all AGEBs scored

3. **W4.3 — Export + visualization** (`src/w4_prioritization.py` lines 161–200)
   - **CSV outputs:** `nppv_w4_weights.csv` (14 rows), `nppv_prioritization.csv` (1,881 rows)
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
- **All 1,881 AGEBs ranked** — mean npp_score=0.500, mean equity_score=0.527, mean final_score=0.506
- **Cluster priority profiles:** Cluster 0 (474 AGEBs, npp_score=0.24) = low-priority peripheral areas; Cluster 1 (442 AGEBs, npp_score=0.66) = high-priority dense urban cores; Cluster 2 (1,152 AGEBs, npp_score=0.55) = medium-priority transitional/suburban
- **No circularity risk:** W4 uses only NPP-V place characteristics + equity; decoupled from W1 demand and W3 accessibility; safe to apply as prioritization lens

**Invariants maintained:**
- All spatial ops in EPSG:6372; outputs join cleanly to `base.ageb` on `cve_ageb`
- 14 features (Node+Place+People) exclude supply-side variables (`route_km_800m`, `stops_*`) and vitality proxy (`v_ridership_annual`)
- Equity term (α=0.20) is transparent and documented; thesis can report sensitivity analysis with α∈{0.10, 0.20, 0.30}
- W4 scores all AGEBs; W6 applies W3 gap as pre-filter when selecting anchors — clean separation of concerns

**Next: W8 validation (W7 code complete; run `python src/run_w7.py` to produce audit outputs)**

---

## W5 — Multi-Objective Function (completed 2026-06-15)

W5 defines the formal evaluation framework that W6 (corridor generation) and W7 (route audit) use to score and rank route candidates against three competing objectives.

**Completed sub-tasks:**

1. **W5.1 — Data types and config** (`src/w5_types.py`)
   - `W5Config` — all tunable parameters with defaults (weights, constraints, gain factors)
   - `RouteCandidate` — input interface: `served_ageb_ids`, `route_km`, `n_stops`, `straight_line_km`, `connects_to_existing`
   - `AgebContext` — per-AGEB context fetched from DB: `transit_demand`, `unserved_fraction`, `equity_score`
   - `ObjectiveResult` — scored output: `f1_demand_gain`, `f2_route_km`, `f3_equity`, `composite_score`, `total_score`
   - `ConstraintResult` / `ConstraintViolation` — feasibility status with named violation details

2. **W5.2 — Objective function** (`src/w5_objective.py`)
   - `load_ageb_context(cvegeos, engine)` — parameterized DB fetch joining `ageb_coverage_gap` + `ageb_trip_ends` + `nppv_prioritization`; uses `ANY(:ids)` (no SQL injection)
   - `evaluate_objective(candidate, contexts, config)` — pure math, no DB:
     - `f1 = sum(demand_i × gain_factor × unserved_fraction_i) / sum(demand_i)` [maximize]
     - `f2 = route_km` [minimize]
     - `f3 = mean(equity_score_i)` [maximize]
     - `gain_factor = 0.50` if connected to SITEUR, else `0.20`
     - `transfer_penalty = 0.10` for isolated routes (flat deduction from composite)
     - `composite = 0.50 × f1_scaled + 0.25 × efficiency + 0.25 × f3`
     - `total_score = composite - transfer_penalty`

3. **W5.3 — Constraint checker** (`src/w5_constraints.py`)
   - `check_constraints(candidate, contexts, config)` — accumulates all violations (not short-circuit):
     - `detour_ratio = route_km / straight_line_km ≤ 1.8`
     - `stop_spacing = route_km × 1000 / (n_stops − 1) ∈ [300, 1000] m`
     - `sum(transit_demand) ≥ 500 trips/day`
     - `route_km ≤ 30.0 km`

4. **W5.4 — Pareto ranking** (`src/w5_pareto.py`)
   - `pareto_objectives(results)` — returns `(n, 3)` matrix minimizing `(-f1, f2, -f3)`
   - `dominates(a, b)` — standard weak-domination: `all(a ≤ b) and any(a < b)`
   - `pareto_rank(results)` — fast non-dominated sort (O(n²)); rank 1 = Pareto front

5. **W5.5 — Demo orchestrator + spec** (`src/run_w5.py`)
   - Fetches top-10 High-gap AGEBs; builds 3 synthetic candidates; evaluates + constrains + Pareto-ranks
   - Writes `outputs/w5/w5_spec.md` (interface contract for W6/W7), `w5_report.md`, `w5_pareto_demo.png`

**Orchestrator:** `python src/run_w5.py` — no DB migration (W6 owns `features.route_candidates`)

**Key files (all created):**
- `src/w5_types.py`, `src/w5_objective.py`, `src/w5_constraints.py`, `src/w5_pareto.py`, `src/run_w5.py`
- `tests/test_w5_types.py`, `tests/test_w5_objective.py`, `tests/test_w5_constraints.py`, `tests/test_w5_pareto.py` (39 tests)
- `outputs/w5/{w5_spec.md, w5_report.md, w5_pareto_demo.png}`

**DB schema notes (actual column names, differ from plan):**
- `features.ageb_coverage_gap`: PK column is `cve_ageb` (not `ageb_id`); normalized gap column is `coverage_gap_n` (not `coverage_gap_normalized`)
- `features.nppv_prioritization`: join key is `cve_ageb` (not `cvegeo`)
- `base.ageb`: geometry column is `geom` (not `geometry`)

**Invariants maintained:**
- All W5 functions are pure or DB-read-only; no writes to DB
- `f1_demand_gain` stored raw (unscaled) in `ObjectiveResult` for correct Pareto comparisons; scaling only applied inside composite calculation
- `unserved_fraction` sourced from `coverage_gap_n` — 1.0 = completely unserved, 0.0 = well-served
- W6/W7 interface fully documented in `outputs/w5/w5_spec.md`

---

## W6 — New Corridor Generation (completed 2026-06-15)

> ⚠️ **SUPERSEDED (2026-07-15).** Everything in THIS section — the "3 feasible corridors",
> the BRT/LRT split, `build_corridor_path`, hub injection, Jenks baseline anchors, endpoint
> detour, and the "21 tests" count — describes the PRE-re-architecture pipeline and is kept
> only for history. The canonical W6 is now **frontier anchors + MST-diameter-trunk shaper +
> anchor-directness gate** with **4 feasible corridors (G00/G01/G02/G03)** and **39 W6 tests**;
> see the "W6 re-architecture -- 2026-07-15" section below for current numbers. Do not cite the
> figures in this section as current.

W6 generates demand-driven new transit corridor candidates using anchor AGEBs from the W3 coverage-gap surface, MST-based OSM routing, and W5 multi-objective evaluation.

**Completed sub-tasks:**

1. **W6.1 — Anchor selection** (`src/w6_anchors.py`)
   - Jenks natural breaks (k=5) on `coverage_gap_n`; top class only; min 500 trips/day demand
   - KMeans spatial clustering into N_CORRIDORS=6 corridor groups
   - Trims to top N_ANCHORS=30 by transit_demand before clustering

2. **W6.2 — OSM graph + path building** (`src/w6_graph.py`)
   - Drive graph downloaded once, cached to `data/osm_zmg_drive.graphml` (125,410 nodes, 304,579 edges)
   - MST Steiner approximation (Kou-Markowsky-Berman) per cluster
   - Centroids snapped to nearest OSM nodes via `ox.distance.nearest_nodes`

3. **W6.3 — Candidate construction** (`src/w6_candidates.py`)
   - Served AGEBs via `ST_DWithin(ST_Centroid(a.geom), corridor, 400m)`
   - SITEUR connectivity via `ST_DWithin(gtfs_stop, corridor, 400m)`
   - n_stops computed to satisfy W5 [300, 1000]m stop-spacing constraints

4. **W6.4 — W5 evaluation + Pareto ranking**
   - All W5 objective terms and constraints applied via existing W5 functions
   - 6 corridors generated; 3 feasible as of the 2026-06-25 beta=1.2005 re-run (W6_G00, W6_G03, W6_G05, all Pareto rank 1) — group composition changed from the prior beta=2.0 run (which had W6_G00, W6_G01, W6_G03 feasible); see "Key results" below
   - 3 infeasible corridors exceeded route_km > 30km or detour_ratio > 1.8 (geographically dispersed clusters)

5. **W6.5 — Mode assignment** (`src/w6_mode.py`, three-tier classification added 2026-06-24)
   - `total_demand >= LRT_THRESHOLD (75,000 trips/day)` → Light Rail/Metro; `>= BRT_THRESHOLD (15,000)` → BRT; else Local Bus
   - LRT threshold derived the same way as the original BRT threshold (peak-hour pax/direction capacity scaled by 10% peak-hour share / 50% directional split / corridor-coverage ratio), using mid-range grade-separated light rail capacity (~15,000 pax/direction/peak-hour) rather than BRT's ~4,000 — see derivation comment in `w6_mode.py`
   - As of the 2026-06-25 beta=1.2005 re-run, all 3 feasible corridors classify as BRT (47,343 / 32,386 / 40,154 trips/day) — no feasible corridor reaches the LRT threshold; the higher-demand groups (W6_G01 130k-equivalent under beta=2.0, W6_G02, W6_G04) are now all infeasible on route length/detour, so the Light Rail/Metro tier currently has no feasible representative. See "Key results" below for the prior (beta=2.0) BRT/LRT split.
   - Sensitivity tables reported in w6_report.md: BRT fixed at 15k varying LRT threshold (50k/75k/100k), and LRT fixed at 75k varying BRT threshold (10k/15k/20k)

**Key files (all created):**
- `src/w6_anchors.py`, `src/w6_graph.py`, `src/w6_candidates.py`, `src/w6_mode.py`, `src/run_w6.py`
- `db_setup/migrations/006_w6_tables.sql`
- `tests/test_w6_anchors.py`, `tests/test_w6_graph.py`, `tests/test_w6_candidates.py`, `tests/test_w6_mode.py` (21 tests)
- `outputs/w6/{corridor_candidates.geojson, corridor_scores.csv, pareto_front.png, w6_report.md}`

**Key results (2026-06-25 re-run, beta=1.2005 adopted into `w1_gravity_model.py`):**
- **3 feasible corridors, all BRT** — W6_G00 (16.6km, 12 served AGEBs, 47,343 trips/day, score=0.650), W6_G03 (1.4km, 3 served AGEBs, 32,386 trips/day, score=0.739), W6_G05 (14.6km, 3 served AGEBs, 40,154 trips/day, score=0.657), all Pareto rank 1
- **3 infeasible corridors** — W6_G01 (43.5km, detour ratio 3.25), W6_G02 (36.3km, detour ratio 8.17), W6_G04 (39.0km, detour ratio 2.69), all exceed the 30km cap; these are also the highest-demand groups (123k-486k trips/day) and would have classified Light Rail/Metro had they been feasible
- **Demand is more geographically dispersed under the slower-decaying beta=1.2005** — anchor selection and MST corridor-building now produce longer, less feasible corridors than under beta=2.0; only the count of feasible corridors (3) coincidentally matches the prior run, not their identity or composition
- **OSM graph cached** — subsequent runs load from `data/osm_zmg_drive.graphml` (fast)
- Superseded (beta=2.0) result, 2026-06-19 run on corrected 1,881-AGEB base.ageb: 3 feasible corridors W6_G00 (16.6km, score=0.650, BRT), W6_G01 (19.5km, score=0.402, Light Rail/Metro, 130,622 trips/day), W6_G03 (14.6km, score=0.658, BRT) — group IDs are not comparable across the beta=2.0 and beta=1.2005 runs since anchor clustering depends on the recomputed demand surface
- Original (now further superseded) result on the uncorrected 2,068-AGEB base.ageb: 2 feasible corridors named W6_G02 (13.2km, score=0.669) and W6_G05 (16.4km, score=0.638)

**DB schema notes (actual column types):**
- `features.route_candidates`: float scores as FLOAT8, geom as GEOMETRY(LineString, 6372) NOT NULL
- Indexes: `route_candidates_geom_gix` (GIST), `route_candidates_total_score_idx` (btree DESC)

**Next: W8 validation (see W8 section below)**

---

## W7 — Existing Route Audit (code complete 2026-06-15)

W7 scores every SITEUR GTFS route against the W5 multi-objective function, flags weak routes, and proposes modifications.

**Key files (all created):**
- `src/w7_gtfs_loader.py` — loads GTFS shapes → one LineString per route (EPSG:6372); computes route_km, n_stops, straight_line_km, connectivity
- `src/w7_route_scorer.py` — PostGIS spatial join (served AGEBs within 400m), W5 objective + constraint evaluation, Pareto ranking; flags: **Low demand** (f1<0.2 AND score<0.3), **Indirect** (detour_ratio>1.5), **Redundant** (Jaccard AGEB overlap ≥60% with higher-scoring route)
- `src/w7_modifications.py` — proposes shortcut / merge / retire per flagged route; estimates shortcut score as 1.1×straight_line_km
- `src/run_w7.py` — orchestrator: migration → GTFS load → scoring → proposals → DB write → 6 output files
- `db_setup/migrations/007_w7_tables.sql` — `features.route_audit` table with GIST index
- `tests/test_w7_gtfs_loader.py` (13 tests), `tests/test_w7_route_scorer.py` (16 tests), `tests/test_w7_modifications.py` (14 tests) — 43 total

**Errata (fixed 2026-06-24) — `straight_line_km` collapsed to ~0 for closed-loop routes:** `_straight_km()` in `w7_gtfs_loader.py` originally measured Euclidean distance between a shape's *first and last* coordinate. For the 11 GTFS routes that are genuine closed loops (start == end terminal, e.g. C104, C108, C133-V1, the T09/T18 pairs, MP-A05-1), that distance floored at the 0.001km div-by-zero guard, sending `detour_ratio` (`route_km/straight_line_km`) into the tens of thousands and making every loop route's "Indirect" flag and shortcut proposal (`straight_line_km×1.1`) meaningless (e.g. "shrink this 82.8km loop to 0.0km"). Fixed by redefining `straight_line_km` as the route's **convex-hull diameter** (max distance between any two points on the shape) — equal to the old endpoint distance for simple point-to-point routes (so non-loop routes are unaffected in net counts), but a real value for loops. Verified against the live `gdl_metro` DB: `route_km`, `f1_demand_gain`, and `total_score` are untouched (they don't depend on this metric); `detour_ratio` never increased for any of the 247 routes; only 6/247 routes lost their "Indirect" flag (3 became "Low demand", 3 became unflagged) because their detour ratio dropped below the 1.5 threshold once measured correctly. Flag totals: 229 flagged (was 232) — 109 Indirect (was 115), 80 Low demand (was 77), 40 Redundant (unchanged — Redundant doesn't depend on this metric). `outputs/w7/` regenerated 2026-06-24.

**Outputs (written by `run_w7.py`):**
- `outputs/w7/route_scorecard.csv` — all 247 SITEUR routes (current GTFS snapshot) with W5 scores and flags
- `outputs/w7/route_modifications.csv` — proposed modifications per flagged route
- `outputs/w7/route_audit.geojson` — QGIS-ready GeoJSON (EPSG:4326) with scores + flags
- `outputs/w7/pareto_space.png`, `outputs/w7/score_distributions.png` — diagnostic charts
- `outputs/w7/w7_report.md` — methodology, score distribution, flagged routes table, proposals

**DB schema:**
- `features.route_audit` — PK: route_id; columns: route_km, n_stops, straight_line_km, detour_ratio, f1_demand_gain, f2_route_km, f3_equity, total_score, pareto_rank, flag, modification_type, overlap_route_id, geom (LineString 6372)

**Run:** `python src/run_w7.py`

---

## W8 — Validation (code complete; first full run 2026-06-19)

W8 validates W6's corridor-generation logic two ways: a backtest (mask existing premium routes, check whether W6 re-proposes them) and a benchmark (spatial overlap between W6 corridors and existing SITEUR premium routes), plus before/after coverage metrics.

**Key files (all created):**
- `src/w8_backtest.py` — masks GTFS stops belonging to premium agencies (Mi Macro `MT`, Mi Tren `MM`), recomputes accessibility/coverage-gap without them, re-runs W6 anchor selection + corridor building on the masked surface, then computes shape-overlap fraction between re-proposed corridors and the masked-out premium routes
- `src/w8_benchmark.py` — spatial overlap between W6's actual (non-masked) feasible corridors and premium route shapes
- `src/w8_metrics.py` — `gini_coefficient`, `coverage_rate`, `pop_served_per_km` before/after W6
- `src/run_w8.py` — orchestrator: backtest → benchmark → before/after metrics → charts → report
- `tests/test_w8_backtest.py`, `tests/test_w8_metrics.py`

**Outputs (written by `run_w8.py`):**
- `outputs/w8/w8_report.md` — consolidated validation report
- `outputs/w8/w8_before_after_metrics.png`, `outputs/w8/w8_backtest_overlap.png` — charts
- `outputs/w8/w8_backtest_per_route.csv`, `outputs/w8/w8_benchmark_detail.csv`

**Key results (2026-07-16 re-run, against the W6-re-architecture feasible set — frontier anchors + MST-diameter-trunk + anchor-directness gate):**
- Backtest: 1,344 GTFS stops masked (agencies MT + MM); 30 anchor AGEBs after masking; 5 built / 5 feasible corridors re-proposed; mean overlap fraction with masked-out premium routes = **0.150** as of the 2026-07-17 backtest alignment (was 0.249 under the legacy build_corridor_path generator; the aligned frontier + diameter-trunk pipeline traces premium routes less — see "W8 backtest alignment" in the follow-through section below)
- Benchmark: **4 feasible W6 corridors** (G00/G01/G02/G03) compared against 33 premium route shapes; mean overlap = **10.5%** (was 0.0% under the stale 3-stub set); total W6 = 44.9 km. **W6_G02 overlaps premium route MP-C03 at 42%** — shape-proximity overlap (fraction of sampled points within 400m), a different metric from the merit analysis's Jaccard AGEB-set overlap (0.18), so not contradictory; read as revealed-preference corroboration (real planners drew a similar alignment), with a mild caveat on the "unique corridor" framing
- Before/after metrics strengthened vs the stale 3-stub set: coverage rate +1.1% (was +0.7%), accessibility Gini -0.0187 (was -0.0063, ~3x), pop-served/km 4,195 (was 1,748), AGEBs newly served 47 (was 16), population newly served 120,648 (was 49,686), total W6 route km 44.9 (was 32.6) — the gains are larger because the new feasible set is real corridors (incl. the 23km G01 and 12.1km G02), not three short stubs
- Superseded (beta=1.2005, 2026-06-25, pre-re-architecture 3-stub set): benchmark 3 feasible corridors, mean premium overlap 0.0%, coverage +0.7%, Gini -0.0063; backtest 5 corridors / 0.249 overlap
- Superseded (beta=2.0, 2026-06-19): 6 corridors re-proposed after masking, mean overlap 0.236

**Run:** `python src/run_w8.py` (depends on `outputs/w6/corridor_candidates.geojson` from W6)
## W8 — Line 4 out-of-sample backtest (2026-07-12)
 
The `data/gtfs/` snapshot is 2024, predating SITEUR Line 4's opening (2025-12-15, 21 km,
Tlajomulco-Tlaquepaque-Guadalajara). So the W3 accessibility/coverage-gap layer treats the
Line 4 corridor as UNSERVED -- a genuine out-of-sample natural experiment. Real alignment in
`data/linea_4.geojson`; observed ridership in `data/raw/ridership/linea4_ridership_observed.csv`
(free-fare ramp: 820k in first 30 days vs ~106k/day mature projection -- not directly comparable).
 
Probe scripts (all read the live DB + linea_4.geojson):
- `src/w8_line4_probe.py`   -- corridor AGEB gap/demand vs metro baseline
- `src/w8_line4_overlap.py` -- spatial overlap of W6 corridors with the real alignment
- `src/w8_line4_anchors.py` -- traces the W6 anchor funnel for the Line 4 AGEBs
 
**Findings.**
- **Diagnostic layer corroborated.** 68 AGEBs within 800 m of Line 4: 33.8% High-gap vs 20.7%
  metro (1.6x), 0% Low-gap vs 4.1%. Flagged via the SUPPLY gap, not demand (corridor demand
  median 3,801 vs metro 3,240 -- barely elevated). Framing: revealed-preference agreement, NOT
  proof of optimality (Line 4 was long-planned).
- **Generative layer does NOT reconstruct Line 4.** The 3 feasible W6 corridors sit 7.6 / 17 /
  26 km away, recall 0.00. Only the infeasible W6_G01 (60 km sprawl) touches it, clipping 6%.
- **Mechanism (anchor funnel).** 15 of 68 Line 4 AGEBs cleared the anchor pool (Jenks top-class
  of `coverage_gap_n` AND demand >= 500). The top-30-by-`transit_demand` trim kept only 1 (the
  rest out-competed; final-anchor demand floor ~8,211 vs Line 4 median 3,801). That 1 survivor
  was absorbed into group 1 (= infeasible W6_G01). Also fundamental: only 15/68 corridor AGEBs
  are high-gap at all (median `coverage_gap_n` 0.014 vs 0.50 pool floor) -- Line 4 is only
  sparsely high-gap.
- **Attempted fix had no effect.** Switching the trim to `coverage_gap_n` (run_w6
  `ANCHOR_TRIM_COL`) left the corridors identical, because within the unserved high-gap pool
  `coverage_gap_n` is ~monotonic in `transit_demand` (accessibility ~ 0 by construction, so
  gap = demand/(access+1) ~ demand). Gap-ranking == demand-ranking for anchors. The bottleneck is
  architectural (30 anchors / KMeans k=6 / MST cannot target a sparse peripheral corridor), not
  the ranking axis.
 
**Interpretation (important for the thesis claim).** Two separate questions:
(A) does the generator reproduce lines that were BUILT? and (B) does it produce GOOD corridors
(serving real unmet demand)? Every test so far measures A (Line 4, and the pre-existing masked
backtest at ~0.25 overlap). A is a weak, asymmetric proxy for B: agreement corroborates, but
disagreement is faint evidence because built lines are not guaranteed optimal (politics, cost,
land). **B is untested.** Defensible claim: validated demand-gap DIAGNOSTIC; corridor GENERATION
has a characterized limitation; generative effectiveness on its own corridors is not yet measured.

## W8 — Question B: do W6's own feasible corridors have merit? (2026-07-13)

The first direct test of Question B (not reconstruction of a built line). Script:
`src/w8_corridor_merit.py` (DB-backed; re-run before trusting numbers -- values drift with any
beta/equity re-run). Companion interactive map: `src/w8_corridor_map_data.py` ->
`src/w8_corridor_map_render.py` -> `outputs/w8/w6_corridor_map.html` (AGEB coverage-gap
choropleth + the 3 corridors, hover-synced merit stats; also published as a private Claude
Artifact). Each feasible corridor scored on three axes:

- **(a) genuine need** -- High-gap share of served AGEBs vs the 20.7% metro baseline.
- **(b) non-redundancy** -- best Jaccard AGEB-overlap vs all 247 existing SITEUR GTFS routes
  (W7's >=0.60 threshold).
- **(c) demand/km** -- corridor `total_demand / route_km` vs the same ratio for every existing
  GTFS route (pass = >= median = 50th pct).

**Results (2026-07-13, beta=1.2005 / post-equity-fix DB).** All 3 are non-redundant (best
Jaccard <= 0.03). Only **W6_G03 passes all three** (100% High-gap, 94th-pct demand/km) -- but
only because it is a 1.4km stub of 2 anchors ~1km apart, i.e. short by luck, not a real corridor.
**W6_G00** serves weak need (41.7% High-gap, barely above baseline; final_score BELOW metro
median) and is low-efficiency (~1st pct demand/km). **W6_G05** serves real need (100% High-gap)
but is also ~1st pct demand/km -- a 14.6km anchor-to-anchor connector.

**Mechanism -- feasibility is confounded with anchor-cluster SPARSITY (traced 2026-07-13).**
Reproduced `w6_anchors.py` -> `build_corridor_path()`: the 3 feasible groups have only 2-3 raw
anchor AGEBs each (G00 3 anchors ~11km apart; G03 2 anchors ~1km; G05 2 anchors ~10.6km); the 3
INfeasible groups had 6-9 anchors each. `build_corridor_path()` MSTs only the anchor terminal
nodes and walks OSM shortest-path between them (never considers intermediate demand or existing
corridors), so more anchors -> longer/more convoluted MST -> more likely to blow the 30km /
1.8-detour caps. So the feasibility filter selects for FEW anchors, not for GOOD corridors -- a
different symptom of the same architecture (30 anchors / KMeans k=6 / MST) already flagged as the
Line 4 reconstruction-failure mechanism above.

**Verdict on B: essentially negative.** W6's generator, as built, does not reliably produce good
corridors on its own terms -- the one "passing" corridor is a degenerate short stub, and merit is
uncorrelated with (indeed slightly opposed to) what its feasibility filter selects. This is a
generator-architecture limitation, and is now measured (not merely asserted). The demand-gap
DIAGNOSTIC (W3/W4) remains the defensible contribution; the thesis claim should be narrowed
accordingly (see Next steps item 4).

---

## W6/W8 — anchor-mode network-connection comparison (2026-07-15)

First attempt to force W6 corridors to tie into the existing SITEUR network at the ANCHOR level
(rather than the routing level, which the 2026-07-14 both-ends hub injection already does). Three
modes compared 3-way by `src/w6_anchor_experiment.py` (read-only harness; does NOT write
`features.route_candidates`); outputs in `outputs/w6_experiment/{baseline,two_tier,frontier}/` +
`comparison.md`. Spec/plan: `docs/superpowers/specs/2026-07-15-w6-anchor-network-connection-design.md`,
`docs/superpowers/plans/2026-07-15-w6-anchor-network-connection.md`. "Connected" = >=1 GTFS stop
within 400m of an AGEB centroid (`network_connected_agebs()`; 1,316 of 1,881 AGEBs qualify).

- **baseline** (incumbent both-ends bare-stop hub injection): **0 of 6 feasible.** The 2026-07-14
  hub work, re-run into the live DB, lengthened every corridor past the 30km / 1.8-detour caps
  (G00 16.6->24.9km, G05 14.6->21.3km, G01/G02/G04 all >36km). So the current
  `features.route_candidates` has 0 feasible corridors, superseding the "3 feasible" state
  documented in the W6 section above — that section predates the hub re-run.
- **two_tier** (inject the nearest network-connected AGEB per group as a `role="network"` MST
  terminal; hub fallback only for groups whose nearest connected AGEB is >5km): **3 of 6 feasible**
  (G00 16.6km, G03 1.4km, G05 15.0km) — RECOVERS the pre-hub feasible set because a single tie-in
  is a lighter touch than two bare-stop hubs. BUT only **1/3 have connected endpoints**: injecting
  one terminal tethers the MST tree without controlling which nodes become the corridor's visible
  leaf ends, so two_tier corridors still dead-end away from the network. Only 1/3 pass merit (G03,
  the 1.4km stub); mean feasible demand/km = 32nd pct.
- **frontier** (restrict the Jenks high-gap pool to anchors within 400m of a connected AGEB before
  clustering; no hubs): **1 of 5 feasible** (G03 2.4km), but that corridor has connected endpoints
  and passes merit; frontier has the best per-corridor quality (feasible demand/km 66th pct vs
  two_tier 32nd; 3/5 endpoint-connected overall) at the cost of COVERAGE — seam restriction drops
  deep-interior high-gap pockets, shrinking served AGEBs/demand.

**Verdict.** Neither anchor-level mode breaks the core Question-B confound: the merit-passing
FEASIBLE corridor in both modes is still G03, the ~1.4-2.4km short stub, while the genuinely
high-merit corridors (G02-family: ~36km, ~486k demand, 57-85th-pct demand/km) remain INfeasible on
the length cap in every mode. Feasibility still selects for short/sparse; merit still lives in the
long/dense corridors that blow the caps. **frontier is the better REALISM lever** (endpoint
connectivity + higher demand/km, all feasible corridors connected) and is the recommended direction
if one must be chosen, but its coverage cost and the unbroken feasibility-vs-merit confound mean the
narrowed thesis claim (Next steps item 4) still stands.

**Mechanism -- the binding constraint is detour_ratio, not length (traced 2026-07-15).** All 13
infeasible corridors across the three modes fail `detour_ratio = route_km /
dist(endpoint0,endpoint1) <= 1.8`; the 30km length cap is NEVER a sole binding constraint (every
length violation co-occurs with an already-fatal detour violation, so raising the length cap alone
rescues zero corridors). Stop-spacing and min-demand never bind. The endpoint detour metric is
structurally mismatched to `build_corridor_path`'s MST/Steiner output: an MST walked into a
LineString sums every anchor edge into `route_km`, but its two endpoints are just two leaves, which
sit close together in a compact cluster -- so any corridor with >=3 non-collinear anchors has
`route_km` >> endpoint distance and blows the 1.8 cap REGARDLESS of absolute length (frontier_G02:
12.6km road, 1.9km endpoint span, detour 6.75). Only near-collinear 2-anchor point-to-point
corridors pass (G03 in every mode; two_tier G00/G05 where the network tie-in happens to line up).
So the feasibility filter is really a "near-linear, few-anchor" filter -- which is WHY it selects
sparse anchor clusters independent of corridor merit. The confound is the `detour_ratio` x MST-
topology interaction, not the anchor logic and not the length cap.

Decision on which mode (if any) to promote into `run_w6.py` is left open pending review of
`comparison.md`; the detour-metric finding above suggests the higher-leverage change may be to the
W5 `detour_ratio` definition rather than to the anchor mode (prototyped separately 2026-07-15 --
an MST-aware directness metric roughly triples frontier's feasible set; see session notes).
**RESOLVED 2026-07-15: frontier mode was promoted into the canonical `run_w6.py` -- see the
"W6 re-architecture" entry below.**

---

## W6 re-architecture -- frontier + diameter trunk + anchor-directness (2026-07-15)

The canonical `run_w6.py` was rebuilt around three changes traced this session; the earlier W6
result (3 BRT corridors via baseline Jenks anchors + branching-MST-flatten + near/far hub
injection) is fully superseded.

1. **Frontier anchors** (`select_frontier_anchors` + `network_connected_agebs`): the top-Jenks
   `coverage_gap_n` pool is restricted to anchors within 400m of a network-connected AGEB (>=1
   GTFS stop within 400m) -- the served/unserved seam. Hub injection is removed (connection is
   intrinsic).
2. **MST-diameter-trunk shaper** (`corridor_trunk_diameter` in `w6_graph.py`): each corridor is
   the longest leaf-to-leaf path of the anchors' spanning tree, stitched from real road segments.
   This retires `build_corridor_path`'s branching-MST flatten, which drew a single LineString by
   concatenating tree edges in arbitrary order and so inserted straight PHANTOM JUMPS between
   non-adjacent branches (observed: an 11.5km line across a river with no road) plus self-loops.
   `corridor_path_tsp` (visits all anchors) is also available; diameter was chosen (straighter).
3. **Anchor-directness feasibility gate** (`w5_constraints.py` + `RouteCandidate.anchor_span_km`
   + `w6_graph.anchor_span_km`): W5 now gates on `route_km / straight-line-span-of-the-anchors`
   ("does the route waste distance connecting its demand?") instead of endpoint detour
   (`route_km / endpoint-distance`). Endpoint detour assumes a straight trunk and over-penalizes a
   demand-COVERAGE corridor that legitimately curves (the G02 case: endpoint detour 2.09 FAIL vs
   anchor-directness 1.54 PASS). W7 routes and the W5 demo carry no anchors and fall back to
   endpoint detour unchanged (`anchor_span_km=None`).

**Why endpoint-detour was wrong here (traced via G02):** G02's 6 anchors sit in a bent
arrangement (straight-line spanning tree ~7.9km) whose two extreme ends are only ~5.8km apart, so
any corridor serving them must exceed the endpoint distance -- baked into the anchor geometry, not
routing waste. The road route (12.1km) is only 1.54x the ideal anchor span (efficient) but 2.09x
the endpoint distance (looks "circuitous"). Anchor-directness measures the right thing.

**Results (2026-07-15, live DB, `features.route_candidates` rewritten):** 5 corridors, **4
feasible** -- W6_G00 (7.3km, 18 AGEBs, dir 1.44, BRT), W6_G01 (23.0km, 27 AGEBs, dir 1.16,
Light Rail/Metro), W6_G02 (12.1km, 25 AGEBs, 192k demand, dir 1.54, Light Rail/Metro), W6_G03
(2.4km, 5 AGEBs, dir 1.25, BRT); W6_G05 rejected (directness 1.93 > 1.8). Group 4 failed to build.

**Question B (merit on own terms) -- partially POSITIVE now, overturning the 2026-07-13 verdict.**
`src/w8_corridor_merit.py` on the new feasible set: **W6_G02 PASSES all three axes** (High-gap
56% vs 20.7% baseline; unique, best Jaccard 0.18; demand/km 73rd pct) and is a substantive
12.1km/25-AGEB corridor -- NOT the degenerate stub. W6_G03 also PASSES but is the 2.4km stub.
W6_G00/G01 are need+ and unique but low-efficiency (demand/km 30th/5th pct) -> MIXED. So the
generator now produces at least one real, meritorious, feasible corridor on its own terms -- the
earlier "only the degenerate stub passes" verdict no longer holds.

**Scope / still open:** `outputs/w6/` regenerated. The published corridor map
(`outputs/w6_experiment/frontier_corridor_map.html`, Claude Artifact) reflects this pipeline. NOT
yet re-run: `run_w8.py` backtest/benchmark (depends on `outputs/w6/corridor_candidates.geojson`
-- the overlap numbers in the W8 section are stale) and `run_w7.py` (unaffected -- W7 uses its own
endpoint detour). W6 test count references elsewhere in this doc predate the new
`test_w6_graph.py` shaper/anchor-span tests.

---

## Post-re-architecture follow-through (2026-07-16/17)

Cleared Next-steps items 1, 3, 5, 6 and the bulk of 2 in one session on branch
`chore/w8-rerun-post-rearch` (off `feat/db-setup-from-scratch`, unpushed). Committed:
W8 re-run (`0faa5a5`) + detour-cap sweep (`fc94826`); the items below are read-only harnesses
in scratchpad unless noted.

**#1 W8 re-run (committed).** See the updated W8 "Key results (2026-07-16 re-run)" above.

**#3 detour-cap sweep (committed).** See the updated Next-steps item 3. 1.8 confirmed on a stable
plateau; anchor-directness is the sole binding constraint.

**#5 TSP vs diameter-trunk shaper.** Read-only harness built BOTH shapers per group. Diameter
confirmed as the default: for the 2-3-anchor groups (G03/G05) TSP == diameter; for G02 (the
meritorious corridor) TSP ~ diameter (+1 AGEB/+7k demand, both feasible); G00 TSP is a small
FEASIBLE win (+2 AGEBs/+9.5k demand, directness 1.76<1.8); G01 is the only group where diameter
drops meaningful demand -- TSP would capture +12 AGEBs/+89k demand (~2x) but blows the 30km cap
(31.8km -> INfeasible). So diameter's dropped demand is the price of feasibility, not a defect;
TSP rescues no corridor and would lose G01. A "TSP-where-feasible" hybrid would only marginally
help G00. Verdict: keep diameter.

**#6 equity refresh (DONE).** (a) Re-ran `src/w3_retrain.py` standalone (accessibility/coverage-gap
are equity-independent, so the full slow run_w3 was unnecessary) -> SHAP plots regenerated with the
de-inverted `pe_marginacion_n` (`outputs/w3/shap/`, 2026-07-17). Refreshed metrics: LightGBM
PR-AUC 0.883 / ROC-AUC 0.962, RF PR-AUC 0.877 / ROC-AUC 0.962, no leakage flags (the W3 section's
0.835/0.872 numbers are from the 2026-06-25 pre-equity-fix run; supersede with these). SHAP top-5
now LightGBM: pe_population_n > pe_rezago_n > p_employment_proxy_n > pe_marginacion_n >
n_intersection_density_n. (b) alpha sensitivity on `final_score = (1-a)*npp + a*equity` over
a in {0.10,0.20,0.30}: prioritization is ROBUST to alpha -- Spearman vs the a=0.20 baseline 0.990
(a=0.10) / 0.984 (a=0.30); top-50 overlap 36-37/50; top-100 overlap 78-82/100; quintile membership
changes for 14-16% of AGEBs. Equity weight matters at the margin (which specific AGEBs top the
list) but not for broad structure. (`fs_0.20` reproduced the stored `final_score` exactly.)

**#2 validation power -- n>1 masked backtests + Line 4 re-check.** Extends the single premium
backtest to three more natural experiments. As of 2026-07-17 these run through the ALIGNED
(re-architected) generator -- see "W8 backtest alignment" below -- so the fractions are citable for
canonical `run_w6`. Aligned numbers first, legacy (retired build_corridor_path) in parentheses:
- **Premium (MM+MT):** 1,344 stops masked, 5 built / 5 feasible, mean overlap **0.150** (legacy
  0.249) -- the diameter-trunk generator traces premium routes LESS than the old branching flatten.
- **Mi Macro only (agency MM):** 1,268 stops masked, 5/5 feasible, mean overlap **0.166** (legacy
  0.267) across 30 MM routes.
- **Line 3 (routes MT_L3+ST_L3):** 126 stops masked, 5 built / 4 feasible, overlap **0.000** (legacy
  0.000) -- the generator does NOT re-discover Line 3. Masking only the rail stops barely moves
  accessibility (non-zero AGEBs ~1266; parallel buses remain), so no strong new gap forms.
- **Line 4 out-of-sample (overlap probe vs the NEW feasible set):** best match is FEASIBLE W6_G02 at
  only **5% recall** (closest approach 0m -- touches Line 4 at one point); other feasible corridors
  0% (6.4-26km away). Still non-reconstruction. The Line 4 anchor probe was ALSO aligned to the
  frontier pipeline (2026-07-17), which sharpens the mechanism: 15/68 Line 4 AGEBs clear Jenks, but
  the **frontier seam drops them 15 -> 4** (Line 4 is mostly deep-interior unserved, not on the
  served/unserved seam), and the coverage_gap_n top-30 trim drops the last 4 -> **0 survive** (the
  old demand-trim probe kept 1). Consistent story across all four: the aligned generator traces the
  dense Mi Macro feeders only weakly (~0.15-0.17) and does not reconstruct rail lines (Line 3 0.00,
  Line 4 0.05) -- the documented anchor-funnel limitation, now measured on n=4 and on the correct
  generator.

**W8 backtest alignment (RESOLVED 2026-07-17 -- was the "legacy generator" known issue).**
`run_backtest` and `w8_line4_anchors.py` previously used the retired `build_corridor_path` +
`transit_demand` trim + no frontier + no feasibility filter. Both were ported to canonical `run_w6`:
frontier anchors on the MASKED served/unserved seam (new `masked_network_connected()` computes
connectivity from the REMAINING GTFS stops, not the full `base.gtfs_stops` -- the subtle correctness
point), coverage_gap_n trim, MST-diameter-trunk shaper, and the anchor-directness feasibility gate;
overlap is now measured against the FEASIBLE re-proposed set (the report distinguishes
`n_corridors_built` vs `n_corridors_reproposed`). `run_backtest` also gained a `route_ids=` argument
for route-level masks (e.g. Line 3 = {MT_L3, ST_L3}) alongside the agency-level default. Net effect:
aligned overlaps are LOWER than legacy (premium 0.249->0.150, MM 0.267->0.166), which strengthens --
does not weaken -- the "generator does not replicate premium lines" finding. `outputs/w8/`
regenerated via `run_w8.py`; 6 new tests in `tests/test_w8_backtest.py` (route-level masking +
masked-connectivity seam). Caveat retained: `build_route_candidate`'s `connects_to_existing` still
reads live (unmasked) GTFS, but that only feeds the objective's gain factor, never the feasibility
gate, so it does not affect which corridors are re-proposed.

---

## W9 — Transferability (in progress 2026-06-15)

W9 applies the pipeline to **Monterrey, Nuevo León** (ZM Monterrey, CVE_ENT=19, 12 municipalities, ~1,958 AGEBs) as the second city for transferability validation.

**Second city: Monterrey, Nuevo León**
- 12 ZM municipalities (CONAPO 2020): Apodaca, Cadereyta Jiménez, García, San Pedro Garza García, General Escobedo, Guadalupe, Juárez, Monterrey, Salinas Victoria, San Nicolás de los Garza, Santa Catarina, Santiago
- Config: `src/w9_city_config.py` — all constants, CPV2020 column names, bbox, DB schema prefix `mty`

**Data acquired (all in `data/`):**
- CPV2020 census NL: `ageb_mza_urbana_19_cpv2020_csv/ageb_mza_urbana_19_cpv2020/conjunto_de_datos/conjunto_de_datos_ageb_urbana_19_cpv2020.csv` — encoding: utf-8-sig
- DENUE NL: `denue_19_0420_csv/conjunto_de_datos/denue_inegi_19_.csv` — encoding: latin-1; joined to AGEBs via `cve_ent+cve_mun+cve_loc+ageb` (no spatial join needed)
- AGEB shapefile: `2020_1_19_A/2020_1_19_A.shp` — INEGI Marco Geoestadístico 2020; reprojected to EPSG:6372; joined on CVEGEO (13-char)
- OSM drive graph: `data/osm_mty_drive.graphml` — 132,701 nodes, 336,923 edges; downloaded via place-name queries per municipality

**Tier-1 pipeline status:**
- `src/w9_run_tier1.py` — W1-equivalent orchestrator for MTY: census → DENUE attractions → shapefile centroids → Furness gravity model → transit demand surface
- `src/w9_osm_download.py` — OSM download (place-name fallback; bbox API changed in newer osmnx)
- `src/w9_city_config.py` — all MTY constants; `CENSUS_DIR_NAME` and `CENSUS_CSV_NAME` reflect actual extracted path
- `docs/w9_data_requirements.md` — tiered data matrix (7 layers), ZMG/MTY status, download URLs
- `docs/w9_city_onboarding.md` — 6-section checklist for applying pipeline to any new Mexican city
- `outputs/w9/w9_transferability_report.md` — study design, data availability matrix, transfer error sources (placeholders for results)
- `tests/test_w9_city_config.py` (26 tests)

**Key transfer finding so far:**
- Mean vehicle rate: MTY 0.634 vs ZMG 0.577 (+0.057) → Monterrey has structurally lower transit propensity due to higher car ownership
- 1,958 AGEBs across 12 municipalities

**Remaining for W9:**
1. GTFS feed for Metrorrey/Transmetro — needed for W3 accessibility equivalent; check `datos.gob.mx` or `transmetro.monterrey.gob.mx`
2. OSM street features per AGEB (node indicators) — needed for W4 NPP equivalent
3. EOD survey (optional, Tier-2) — for W2 beta calibration; use β=2.0 prior if unavailable
4. Run W3→W4→W5→W6 equivalent for MTY after GTFS acquired
5. Transfer error report comparing MTY vs ZMG pipeline outputs

**Next steps (W8 onward):**
- W8 requires W7 run output; backtest sub-task (mask high-ridership segments, test W6 re-proposes them) can start now
- W9 full pipeline blocked on GTFS; Tier-1 demand surface is complete
- W8 and W9 full run can proceed in parallel once GTFS is acquired

## E. Next steps

Last refreshed 2026-07-17. The W6 re-architecture (frontier anchors + MST-diameter-trunk shaper +
anchor-directness gate; see the "W6 re-architecture -- 2026-07-15" section above) merged to `main`
(PR #8); items 1/3/5/6 and most of 2 were then cleared on branch `chore/w8-rerun-post-rearch` (see
"Post-re-architecture follow-through (2026-07-16/17)" above for full numbers). Remaining work first,
then the closed items for the record.

**Open:**

A. ✅ **DONE 2026-07-17 — aligned the W8 backtest + Line 4 anchor probe to the re-architected
   generator.** `run_backtest` and `w8_line4_anchors.py` now use frontier anchors (masked
   connectivity via new `masked_network_connected()`) + coverage_gap_n trim + diameter-trunk +
   anchor-directness gate; `run_backtest` gained `route_ids=` for route-level masks. Aligned
   overlaps: premium 0.150 (was 0.249), MM 0.166 (was 0.267), Line 3 0.000. Qualitative findings
   held and in fact strengthened (lower overlap = less premium-line replication). `outputs/w8/`
   regenerated; 6 new tests. See "W8 backtest alignment (RESOLVED 2026-07-17)" above.

B. **W9 transferability** unchanged: blocked on a Metrorrey/Transmetro GTFS feed (see W9 section);
   Tier-1 demand surface for Monterrey is complete.

C. **Optional: TSP-where-feasible hybrid shaper.** #5 showed a pure TSP swap loses G01; a hybrid
   that uses TSP only where it stays feasible would marginally improve G00 (+2 AGEBs/+9.5k demand).
   Low priority -- diameter is the confirmed default.

**Closed this session (2026-07-16/17):**

1. ✅ **Re-ran `run_w8.py` against the new corridors** (committed `0faa5a5`). W8 "Key results
   (2026-07-16 re-run)": benchmark 4 feasible corridors / 10.5% mean premium overlap (W6_G02 x
   MP-C03 42%), before/after gains ~2-3x the stale 3-stub set. Regenerated `outputs/w8/`.
2. ✅ **Validation power extended to n=4, on the aligned generator** (caveat in old item A now
   resolved -- see item A above). Aligned masked backtests: premium 0.150, Mi Macro 0.166, Line 3
   0.000 (generator does not re-discover Line 3); Line 4 probes re-run vs the new feasible set (best
   feasible recall 5%, still non-reconstruction). Consistent: weak overlap of the dense MM feeders,
   no rail reconstruction.
3. ✅ **1.8 detour cap confirmed** (committed `fc94826`). Sole binding constraint; feasible set
   invariant across [1.6,1.9]; 1.8 sits mid-plateau.
4. ✅ **Thesis claim (Gap A) settled -- adopt this wording:** *"A data-driven, transferable
   framework that (i) diagnoses transit demand-gap priority at AGEB resolution (W3/W4, validated:
   Line 4 corridor 1.6x the metro High-gap rate) and (ii) identifies and generates candidate
   corridors evaluated on genuine need, non-redundancy, and demand efficiency (W5/W6). On its own
   terms the generator produces at least one substantive, feasible, merit-passing corridor (W6_G02:
   56% High-gap, unique, 73rd-pct demand/km) once corridors are shaped as real paths and judged by
   anchor-directness. Residual, characterized limitations remain: it surfaces low-efficiency
   connectors (G00/G01) alongside good corridors, and does not reconstruct built rail lines (Line 3
   0.00, Line 4 0.05 recall) -- expected, since reconstruction of politically/financially chosen
   lines is a weak, asymmetric proxy for corridor merit."* The diagnostic layer is the strong
   contribution; the generative layer is a characterized, partially-positive contribution -- no
   longer the "essentially negative" framing from 2026-07-13.
5. ✅ **TSP vs diameter-trunk evaluated** -- diameter kept as default (see follow-through section;
   optional hybrid noted in open item C).
6. ✅ **Equity fix downstream refreshed** -- `w3_retrain` SHAP plots regenerated with the
   de-inverted `pe_marginacion_n`; alpha in {0.10,0.20,0.30} sensitivity reported (prioritization
   robust, Spearman >=0.98).
7. ✅ **Stale numbers reconciled** -- old W6 section banner-flagged SUPERSEDED; W6 test count
   21->39, W7 34->43; refreshed W3.3 metrics noted; legacy-backtest-shaper known issue documented.

## Methodological References

- Bertolini (1996/1999): Node-Place Model
- Liu et al. (2024/2025): NP-RV Model, LightGBM+SHAP
- Niu et al. (2023): Random Forest for station suitability
- Takahashi (1980): Steiner Tree heuristic for network design
