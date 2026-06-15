# W4 — NPP Prioritization Layer Design

*Date: 2026-06-15*
*Status: Approved — ready for implementation*

---

## Purpose

W4 repositions the NPP-V indicator set as a **multi-criteria place-characteristics prioritization index**, decoupled from demand estimation. Demand lives in W1/W3; W4 ranks AGEBs by their intrinsic place-characteristics suitability and equity need, producing scores that W6 will use to select corridor anchors.

The Vitality dimension (`v_ridership_annual_n`) is dropped entirely — it is a municipality-level binary proxy with zero AGEB-level discrimination. The framework operates on 14 NODE + PLACE + PEOPLE indicators. This resolves the circularity in the original Phase 3 weighting (where `v_ridership_annual_n` dominated ensemble weight at 0.2519 for the wrong reason).

---

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Vitality dimension | Dropped | Municipality-level proxy; blurs demand/place separation if replaced with W1 demand |
| Features | 14 NODE + PLACE + PEOPLE `_n` columns | All from `features.nppv_features`; excludes `v_ridership_annual_n` |
| Equity integration | Additive bonus term post-CRITIC/EWM | Transparent, separable; allows reporting with/without equity term |
| Equity formula | `final_score = 0.80 × npp_score + 0.20 × equity_score` | α=0.20 default; sensitivity analysis at α∈{0.10,0.20,0.30} |
| Equity operationalization | `equity_score = mean(pe_marginacion_n, pe_rezago_n)` | Two W3-validated equity drivers |
| AGEB scope | All 2,068 AGEBs | W4 independent of W3 gap thresholds; W6 applies gap as pre-filter |
| Output scope | DB + report + charts + GeoJSON + cluster profiles | Full deliverable set for thesis and W6 consumption |
| Architecture | New module + orchestrator + migration | Consistent with W1/W2/W3 pattern; Phase 3 `nppv_weights` untouched |

---

## Computation Pipeline

```
features.nppv_features  (14 cols, 2,068 rows)
         │
         ▼
   CRITIC weights (14)    EWM weights (14)
         └────────┬────────┘
                  ▼
     ensemble_weight = (CRITIC + EWM) / 2   [normalized, sums to 1]
                  │
                  ▼
     npp_score = sum(feature_i × ensemble_weight_i)  per AGEB  [0–1]
                  │
     equity_score = mean(pe_marginacion_n, pe_rezago_n)         [0–1]
                  │
                  ▼
     final_score = 0.80 × npp_score + 0.20 × equity_score      [0–1]
                  │
                  ▼
     features.nppv_prioritization
       (cve_ageb, npp_score, equity_score, final_score,
        priority_rank, priority_quintile)
```

CRITIC and EWM formulas are unchanged from `src/phase3_weighting.py`. The only change is the 14-feature input list.

---

## Database Schema

Created by `db_setup/migrations/005_w4_tables.sql`:

```sql
-- W4 weights (separate from Phase 3 nppv_weights historical record)
CREATE TABLE features.nppv_w4_weights (
    feature          VARCHAR(50) PRIMARY KEY,
    dimension        VARCHAR(20),
    critic_weight    NUMERIC,
    ewm_weight       NUMERIC,
    ensemble_weight  NUMERIC
);

-- One row per AGEB prioritization scores
CREATE TABLE features.nppv_prioritization (
    cve_ageb          VARCHAR(20) PRIMARY KEY,
    npp_score         NUMERIC,    -- pure CRITIC/EWM weighted sum (0–1)
    equity_score      NUMERIC,    -- mean(pe_marginacion_n, pe_rezago_n) (0–1)
    final_score       NUMERIC,    -- 0.80*npp_score + 0.20*equity_score (0–1)
    priority_rank     INTEGER,    -- rank by final_score DESC (1 = highest priority)
    priority_quintile INTEGER     -- 1–5, where 5 = highest priority
);
CREATE INDEX ON features.nppv_prioritization (cve_ageb);
```

`features.nppv_weights` (Phase 3) is **not modified** — it remains the historical 15-feature record.

No geometry stored in `features` schema tables; GeoJSON output joins `base.ageb` at write time.

---

## Files

### New files
| File | Role |
|---|---|
| `src/w4_prioritization.py` | Main module: CRITIC/EWM → scores → DB + all outputs |
| `src/run_w4.py` | Orchestrator: migration → w4_prioritization |
| `db_setup/migrations/005_w4_tables.sql` | Schema migration for W4 tables |

### Outputs (`outputs/w4/`)
| File | Description |
|---|---|
| `nppv_w4_weights.csv` | 14-row weight table (feature, dimension, critic, ewm, ensemble) |
| `nppv_prioritization.csv` | 2,068-row ranked AGEB table |
| `nppv_prioritization.geojson` | QGIS-ready, joins `base.ageb` geometry |
| `w4_report.md` | Markdown report: weight table, top-ranked AGEBs, interpretation |
| `nppv_w4_weights_bar.png` | Horizontal bar chart of 14 ensemble weights |
| `nppv_score_vs_equity.png` | Scatter: npp_score (x) vs equity_score (y), colored by final_score, sized by transit_demand |
| `cluster_priority_profiles.csv` | Mean npp_score / equity_score / final_score per cluster A/B/C |

---

## Module Steps (`w4_prioritization.py`)

Following the standard `[Step N]` print convention used across all `src/` files:

1. Load 14 NPP features from `features.nppv_features`
2. Compute CRITIC weights
3. Compute EWM weights
4. Compute `npp_score`, `equity_score`, `final_score` per AGEB; assign rank and quintile
5. Write `features.nppv_w4_weights` to DB
6. Write `features.nppv_prioritization` to DB
7. Export `nppv_w4_weights.csv` and `nppv_prioritization.csv`
8. Export `nppv_prioritization.geojson` (join `base.ageb` for geometry)
9. Generate `nppv_w4_weights_bar.png` and `nppv_score_vs_equity.png`
10. Generate `cluster_priority_profiles.csv` (join `features.nppv_clusters`)
11. Write `w4_report.md`

---

## 14 NPP Features

| Dimension | Features |
|---|---|
| NODE (3) | `n_intersections_n`, `n_intersection_density_n`, `n_street_density_n` |
| PLACE (5) | `p_poi_density_n`, `p_employment_proxy_n`, `p_retail_density_n`, `p_service_density_n`, `p_land_use_mix_n` |
| PEOPLE (6) | `pe_population_n`, `pe_pop_density_n`, `pe_marginacion_n`, `pe_rezago_n`, `pe_dep_ratio_n`, `pe_youth_share_n` |

Note: `pe_marginacion_n` and `pe_rezago_n` appear in both the CRITIC/EWM pool (they contribute to `npp_score`) **and** as the equity bonus term (`equity_score`). This double-counts their influence slightly — a limitation to acknowledge in the thesis methods section.

---

## Sensitivity Analysis

The report must include a table showing `final_score` rank correlation (Spearman) across α values:

| α | Interpretation |
|---|---|
| 0.10 | Equity as a light adjustment |
| 0.20 | Default (balanced) |
| 0.30 | Equity-forward prioritization |

---

## Connections to Other Workstreams

- **W3 → W4:** `features.ageb_coverage_gap` provides context for the report (how many High-gap AGEBs are in each priority quintile) but does not feed into the score computation.
- **W4 → W6:** `features.nppv_prioritization.final_score` is one input to anchor selection; W6 applies the W3 gap filter on top.
- **Phase 4 → W4:** `features.nppv_clusters` cluster labels (A/B/C) are used only for the cluster profile output — descriptive, not causal.
