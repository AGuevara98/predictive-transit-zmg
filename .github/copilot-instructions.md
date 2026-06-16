# AI Agent Instructions: predictive-transit-zmg

## Project Overview

Master's thesis: a demand-driven, transferable framework for optimal transit network design in Mexican metropolitan areas. Applied to the Zona Metropolitana de Guadalajara (ZMG). Unit of analysis: 2,068 urban AGEBs across 10 ZMG municipalities.

The pipeline implements the **NPP (Node-Place-People)** framework and answers two research questions:
- **R1:** Where should new routes go? → demand surface + coverage-gap index + corridor generation
- **R2:** Are existing routes optimal? → W5 objective scoring of all SITEUR GTFS routes

See `CLAUDE.md` for the authoritative technical reference. This file is a short orientation for AI coding assistants.

## Architecture

**Two-tier data model:**
- Tier 1: INEGI census, DENUE, OSM, GTFS — runs in any Mexican city
- Tier 2: EOD OD survey — calibration only, not a hard dependency

**Workstream pipeline (W0–W9):**
```
W1: Trip generation → gravity model → transit-demand surface
W2: EOD 2022 calibration (beta=2.0 prior retained)
W3: GTFS accessibility → coverage-gap index → ML retrain on gap target
W4: CRITIC + EWM on 14 NPP features → final_score = 0.80×npp + 0.20×equity
W5: Multi-objective function (demand gain, cost, equity + Pareto ranking)
W6: Anchor AGEBs from W3 → OSM MST → W5 evaluation → BRT corridors
W7: SITEUR routes → W5 scoring → flags + modification proposals
W8: Validation (backtest + benchmark + accessibility/equity metrics)
W9: Monterrey Tier-1 pipeline (transferability)
```

## Tech Stack

- **Python 3.9+** — `geopandas`, `networkx`, `osmnx`, `sqlalchemy`, `lightgbm`, `shap`, `scipy`
- **PostgreSQL 14+ / PostGIS 3.2+** — three schemas: `raw`, `base`, `features`
- **Database:** `gdl_metro` (localhost:5432)
- **GTFS data:** `data/gtfs/` directory

## Key Conventions

1. **CRS:** EPSG:6372 (conic equidistant for Mexico) for all calculations and DB storage. EPSG:4326 is ingestion-only — transform immediately.
2. **AGEB filter:** `CVE_ENT='14'`, exclude `CVE_AGEB` with 'A' suffix, 10 ZMG municipalities.
3. **Config:** All credentials and constants in `config.py` (Python) and `config.sh` (shell). Never duplicate elsewhere.
4. **DB pattern:** `create_engine(PG_URI)` + `gpd.read_postgis()`. All analytical outputs → `features` schema.
5. **Print conventions:** `[Step N]`, `  [OK]`, `  [ERR]` — ASCII only (Windows console encoding).
6. **SQL migrations:** Split on `;` in orchestrators — do not include `COMMENT ON TABLE` statements.

## Configuration Import

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI, CRS_CANONICAL, ZMG_BBOX
```

## Key Source Files

| File | Role |
|------|------|
| `src/run_w1.py` … `src/run_w8.py` | Workstream orchestrators |
| `src/w5_types.py` | Core data classes (RouteCandidate, ObjectiveResult) |
| `src/w5_objective.py` | Multi-objective evaluation |
| `src/w5_constraints.py` | Feasibility checks |
| `src/w5_pareto.py` | Pareto ranking |
| `src/w7_gtfs_loader.py` | GTFS → LineString per route |
| `src/w9_city_config.py` | Monterrey constants |
| `db_setup/DDL.sql` | Full schema definition |
| `db_setup/migrations/` | Incremental migrations (001–007) |
| `config.py` | Credentials + constants |

## Key DB Tables

| Table | Contents |
|-------|----------|
| `base.ageb` | 2,068 AGEB polygons (EPSG:6372) |
| `features.nppv_features` | 14 normalized NPP indicators per AGEB |
| `features.ageb_trip_ends` | W1 productions, attractions, transit demand |
| `features.ageb_coverage_gap` | W3 gap index, quintile ranks, gap category |
| `features.nppv_prioritization` | W4 npp_score, equity_score, final_score |
| `features.route_candidates` | W6 corridor candidates + W5 scores |
| `features.route_audit` | W7 SITEUR route scorecard |

## References

- Bertolini (1996/1999): Node-Place Model
- Mumford et al. (arXiv:2201.11616): Multi-objective TNDP
- Park et al. (2022): Variable-demand TNDP with equity
- Liu et al. (2024/2025): LightGBM + SHAP for transit suitability
- Takahashi (1980): Steiner Tree heuristic
