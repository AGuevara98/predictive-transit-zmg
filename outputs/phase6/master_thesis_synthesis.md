# Master Thesis Synthesis: A Demand-Driven, Transferable Framework for Transit Corridor Prioritization in the ZMG

*Rewritten 2026-07-17 to reflect the demand-driven W1–W8 re-architecture. Supersedes the
pre-restructure Phase 1–5 synthesis (which was built on a tautological "has-a-stop"/cluster-label
target, a corrupted DEM feature, and an uncorrected 2,068-AGEB universe). Every quantitative claim
below was cross-checked against the live `gdl_metro` database and the current `outputs/` on the
rewrite date.*

---

## Executive Summary

This thesis develops and validates a **data-driven, transferable framework** for transit planning
in the Zona Metropolitana de Guadalajara (ZMG), operating at the resolution of the **AGEB** (census
enumeration area; **1,881** AGEBs across 10 ZMG municipalities). The framework does two things:

1. **Diagnoses transit demand-gap priority** — it estimates latent transit demand from Tier-1 open
   data (census, economic units, street network), measures the existing supply from GTFS, and
   locates the AGEBs where high demand meets poor accessibility (workstreams **W1–W4**).
2. **Identifies and generates candidate corridors** — it proposes new corridors and audits the
   existing network against a formal multi-objective function scoring genuine need,
   non-redundancy, and demand efficiency (workstreams **W5–W7**), then validates the generator out
   of sample (**W8**).

**Settled thesis claim (Gap A).** *A data-driven, transferable framework that (i) diagnoses transit
demand-gap priority at AGEB resolution (W3/W4, validated: the Line 4 corridor shows 1.6× the metro
High-gap rate) and (ii) identifies and generates candidate corridors evaluated on genuine need,
non-redundancy, and demand efficiency (W5/W6). On its own terms the generator produces at least one
substantive, feasible, merit-passing corridor (W6_G02: 56% High-gap, unique, 73rd-percentile
demand/km) once corridors are shaped as real paths and judged by anchor-directness. Residual,
characterized limitations remain: it surfaces low-efficiency connectors (G00/G01) alongside good
corridors, and does not reconstruct built rail lines (Line 3 overlap 0.00, Line 4 recall 0.05) —
expected, since reconstruction of politically/financially chosen lines is a weak, asymmetric proxy
for corridor merit.*

The **diagnostic layer is the strong contribution**; the **generative layer is a characterized,
partially-positive contribution**. The framework is designed for transfer to other Mexican metros
(W9, Monterrey pipeline operational on Tier-1 data).

## Table of Contents

- [Framework Overview](#framework-overview)
- [Data Foundation](#data-foundation)
- [W1 — Demand Estimation Layer](#w1--demand-estimation-layer)
- [W2 — Survey Calibration](#w2--survey-calibration)
- [W3 — Supply & Coverage-Gap Layer](#w3--supply--coverage-gap-layer)
- [W4 — NPP Prioritization Layer](#w4--npp-prioritization-layer)
- [W5 — Multi-Objective Function](#w5--multi-objective-function)
- [W6 — New Corridor Generation](#w6--new-corridor-generation)
- [W7 — Existing Route Audit](#w7--existing-route-audit)
- [W8 — Validation](#w8--validation)
- [W9 — Transferability](#w9--transferability)
- [Limitations & Future Work](#limitations--future-work)
- [Methodological References](#methodological-references)

---

<a name="framework-overview"></a>

## Framework Overview

The framework began as an implementation of the **NPP-V (Node–Place–People–Vitality)** model
(Bertolini's Node–Place logic, extended by Liu et al.'s people/vitality dimensions), but was
**re-architected into a demand-driven pipeline** because the original supervised target was
circular: it predicted a "has-a-stop" label — the network explaining itself. The re-architecture
replaces that target with an **explicitly modeled transit-demand surface** and an **independent,
GTFS-derived supply measure**, so the dependent variable (the coverage gap) no longer contains the
network being planned.

| Workstream | Role | Status |
|---|---|---|
| **W1** | Demand estimation (trip generation → gravity model → transit-demand surface) | ✅ |
| **W2** | Survey calibration of the gravity model against EOD 2022 | ✅ |
| **W3** | Supply (GTFS accessibility) + coverage-gap index + supervised retrain | ✅ |
| **W4** | NPP place-characteristics prioritization + equity term | ✅ |
| **W5** | Formal multi-objective evaluation (objectives, constraints, Pareto) | ✅ |
| **W6** | New corridor generation (frontier anchors → diameter trunk → feasibility gate) | ✅ |
| **W7** | Existing route audit (247 SITEUR routes) | ✅ |
| **W8** | Validation (masked backtests, benchmark, before/after, corridor merit) | ✅ |
| **W9** | Transferability (Monterrey Tier-1 pipeline) | 🔄 |

The **NPP-V** framing is retained for the place-characteristics prioritization (W4), but the
Vitality dimension is dropped there (its only proxy, municipality-level ridership, carried no
AGEB-level signal); demand signal lives exclusively in W1/W3. Legacy Phase 2 (binary suitability)
and Phase 5 (RF/XGBoost on cluster labels) were **retired** as tautological and are not part of the
current framework.

---

<a name="data-foundation"></a>

## Data Foundation

All analysis operates at AGEB resolution in **EPSG:6372** (conic equidistant for Mexico); WGS84 is
ingestion-only. The **corrected universe is 1,881 AGEBs** — filtered to `CVE_ENT='14'`, the 10 ZMG
municipalities, and excluding alpha-suffix `CVE_AGEB` codes. (Earlier drafts of this project cited
2,068 AGEBs; that figure came from a `base.ageb` table that was never actually rebuilt from the
checked-in DDL and silently included a dropped municipality and 187 alpha-suffix cells. The
correction, and its downstream effects, are documented in the project errata.)

**Tier-1 inputs** (open, transferable): INEGI census 2020 (CPV/AGEB socioeconomics), INEGI DENUE
economic units (employment/POI proxies), and the OpenStreetMap drive network (intersections,
street density). **Tier-2 inputs** (used for calibration and supply, not required for the Tier-1
demand surface): the EOD 2022 origin–destination survey and the SITEUR GTFS feed (2024 snapshot).

The 15-indicator NPP-V feature set is built by `src/build_nppv_features.py` (log1p+min-max for
skewed counts, plain min-max for bounded ratios) and stored normalized in
`features.nppv_features`.

---

<a name="w1--demand-estimation-layer"></a>

## W1 — Demand Estimation Layer

W1 replaces the circular target with an explicit transit-demand surface using **Tier-1 data only**
— no existing transit supply enters as input.

- **Trip generation.** Productions = `2.5 trips/person/day × population × (1 + 0.10 × youth_share)`;
  attractions = weighted sum of employment proxy, POI density × area, and retail density × area,
  scaled so `Σ(A) = Σ(P)`. Output: `features.ageb_trip_ends` (1,881 rows).
- **Doubly-constrained gravity model.** Power-law impedance `f(d) = d^(−β)` with the
  W2-calibrated **β = 1.2005**, solved by Furness IPF (`tol=1e-5`). Total modeled flow
  **11,816,597 trips**; **1,446,695** OD pairs stored above the 0.5-flow threshold; mean filtered
  trip distance 14.1 km.
- **Transit-demand surface.** `transit_propensity = 1 − vehicle_rate` (from CPV2020 vehicle
  ownership); `transit_demand = total_demand × transit_propensity`. ZMG averages **vehicle rate
  0.577 / transit propensity 0.423**; total transit demand **≈ 8.47M trips/day**. About **177**
  high-car-ownership AGEBs have zero transit demand (correctly treated as low-gap downstream).

---

<a name="w2--survey-calibration"></a>

## W2 — Survey Calibration

W2 calibrates the gravity model's distance-decay parameter against **EOD 2022** observed flows
(71 survey zones, 3,509 non-zero zone OD pairs) and documents the transfer error.

Fitting minimizes log-space SSE over 1,993 zone pairs. On the corrected 1,881-AGEB universe the
calibrated **β = 1.2005 outperforms the β = 2.0 prior**:

| | Calibrated β = 1.2005 | Prior β = 2.0 |
|---|---|---|
| RMSE (scaled) | **4,524.9 trips** | 5,088.2 trips |
| R² | **0.2498** | — |

The weaker decay (β 1.20 vs 2.0) says ZMG commuters travel farther than the prior assumed. β=1.2005
was adopted into `w1_gravity_model.py`, and W1/W3/W4/W6/W7/W8 were re-run on it. (Note: on the old,
never-correctly-filtered 2,068-AGEB table the calibration had hit its search boundary with a worse
fit and β=2.0 was retained — a conclusion the universe correction reverses.)

---

<a name="w3--supply--coverage-gap-layer"></a>

## W3 — Supply & Coverage-Gap Layer

W3 builds an **independent supply measure**, defines the **coverage gap** (the new, non-circular
dependent variable), and re-trains a supervised model on it.

- **Accessibility (supply).** Cumulative-opportunities accessibility from GTFS: jobs reachable
  within a 45-minute budget (walk + wait + in-vehicle), Dijkstra per boarding stop on a
  10.6k-node/12.7k-edge transit graph. **1,266 AGEBs** have non-zero accessibility; **615** have
  none (no GTFS stop within 400 m). Accessibility is demand-independent by construction.
- **Coverage-gap index.** `coverage_gap_raw = transit_demand / (accessibility_score + 1)`,
  log1p+min-max normalized, with demand/accessibility quintiles. Categories: **390 High-gap
  (20.7%)**, 1,413 Medium-gap, 78 Low-gap. High-gap ≙ demand quintile ≥ 4 **and** access quintile
  ≤ 2.
- **Supervised retrain.** Binary target `is_high_gap` on the 14 NPP features (all supply variables
  excluded to prevent leakage). Test metrics: **RandomForest PR-AUC 0.877 / ROC-AUC 0.962;
  LightGBM PR-AUC 0.883 / ROC-AUC 0.962**; no leakage flags (label-shuffle PR-AUC ≈ positive rate
  0.207). Top SHAP drivers (LightGBM): `pe_population_n` > `pe_rezago_n` > `p_employment_proxy_n` >
  `pe_marginacion_n` > `n_intersection_density_n` — high-gap AGEBs are dense, high-need,
  employment-rich zones the current SITEUR network does not reach.

This retrain is the principled replacement for the retired Phase 2/5 models: same 14 features, but
against an **independently-derived** target rather than a circular one. SHAP plots
(`outputs/w3/shap/`) were regenerated after the 2026-07-12 equity fix (see W4).

---

<a name="w4--npp-prioritization-layer"></a>

## W4 — NPP Prioritization Layer

W4 repositions the CRITIC/EWM objective weighting as a **place-characteristics prioritization map**,
scored for **all 1,881 AGEBs** and deliberately decoupled from the W1/W3 demand and supply layers
(so the prioritization is reusable if gap thresholds change, with no circularity).

- **Objective weights** (ensemble of CRITIC + EWM over 14 NODE+PLACE+PEOPLE features). Top drivers:
  `p_employment_proxy_n` (0.163), `p_service_density_n` (0.145), `n_intersection_density_n`
  (0.097). Vitality (municipality-level ridership) is excluded — it carried no AGEB-level
  discrimination.
- **Composite score.** `npp_score = Σ(feature_i × weight_i)`;
  `equity_score = mean(pe_marginacion_n, pe_rezago_n)`;
  **`final_score = 0.80 × npp_score + 0.20 × equity_score`** (α = 0.20 default).
  ZMG means: npp 0.4595, equity 0.2274, final 0.4131.
- **Equity correction (2026-07-12).** The marginación input (CONAPO IM_2020, where *higher = less*
  marginalized) had been used with the wrong sign and zero-filled for ~200 non-urban AGEBs — two
  bugs that partly masked each other. Both were fixed (direction inverted via `INVERTED_FEATURES`;
  missing values median-imputed). Post-fix `equity_score` is monotonic by marginación grade
  (Muy alto 0.500 → Muy bajo 0.095).
- **α sensitivity.** Prioritization is **robust to α**: Spearman vs the α=0.20 baseline is 0.990
  (α=0.10) and 0.984 (α=0.30); equity weight shifts which specific AGEBs top the list, not the
  broad structure.

---

<a name="w5--multi-objective-function"></a>

## W5 — Multi-Objective Function

W5 is the formal, testable evaluation contract that W6 (generation) and W7 (audit) share.

- **Objectives** — `f1` demand-gain served [max], `f2` route length [min], `f3` mean equity [max];
  composite `= 0.50·f1_scaled + 0.25·efficiency + 0.25·f3`, minus a transfer penalty for
  isolated routes. Gain factor 0.50 if connected to SITEUR, else 0.20.
- **Constraints** — stop spacing ∈ [300, 1000] m; served demand ≥ 500 trips/day; route ≤ 30 km;
  and a **directness gate** (see W6 re-architecture). Violations accumulate (non-short-circuit).
- **Pareto** — fast non-dominated sort minimizing `(−f1, f2, −f3)`; rank 1 = Pareto front.

The functions are pure/read-only and unit-tested (39 tests); the interface is documented in
`outputs/w5/w5_spec.md`.

---

<a name="w6--new-corridor-generation"></a>

## W6 — New Corridor Generation

W6 generates demand-driven candidate corridors and was **re-architected (2026-07-15)** around three
changes that fixed structural defects in the earlier generator:

1. **Frontier anchors** — restrict the top-Jenks `coverage_gap_n` pool to anchors within 400 m of a
   network-connected AGEB (the served/unserved *seam*), so corridors tie into the existing network
   intrinsically (hub injection retired).
2. **MST-diameter-trunk shaper** — each corridor is the longest leaf-to-leaf path of the anchors'
   spanning tree, stitched from real road segments. This retires the old branching-MST flatten,
   which drew phantom straight jumps between non-adjacent branches (once producing an 11.5 km line
   across a river with no road).
3. **Anchor-directness feasibility gate** — the W5 directness constraint gates on
   `route_km / straight-line-anchor-span` ("does the route waste distance connecting its demand?")
   rather than endpoint detour, which over-penalized corridors that legitimately curve to cover
   demand. (Traced binding constraint: directness, not the 30 km length cap — confirmed on a
   [1.6, 1.9] cap sweep, 1.8 mid-plateau.)

**Result — 5 corridors, 4 feasible** (`features.route_candidates`):

| Corridor | km | AGEBs | Demand/day | Directness | Mode | Feasible |
|---|---|---|---|---|---|---|
| W6_G00 | 7.3 | 18 | 66,041 | 1.44 | BRT | ✅ |
| W6_G01 | 23.0 | 27 | 96,839 | 1.16 | Light Rail/Metro | ✅ |
| **W6_G02** | 12.1 | 25 | 192,357 | 1.54 | Light Rail/Metro | ✅ |
| W6_G03 | 2.4 | 5 | 35,784 | 1.25 | BRT | ✅ |
| W6_G05 | 5.4 | 14 | 80,234 | 1.93 | — | ❌ (directness > 1.8) |

**W6_G02 is the substantive result** — a real 12.1 km / 25-AGEB corridor carrying ~192k demand/day.
See W8 for its merit evaluation. Mode assignment uses demand thresholds (≥75k Light Rail/Metro,
≥15k BRT).

---

<a name="w7--existing-route-audit"></a>

## W7 — Existing Route Audit

W7 scores every existing **SITEUR route (247)** against the W5 function and flags weak routes.

- **Only 19 routes are feasible** under the W5 constraints; **229 are flagged**: **109 Indirect**
  (detour ratio > 1.5), **80 Low-demand** (f1 < 0.2 and score < 0.3), **40 Redundant** (≥ 60%
  AGEB-set Jaccard with a higher-scoring route). Mean route score 0.230; mean detour ratio 1.98.
- Each flagged route gets a proposed modification (shortcut / merge / retire).
- **Closed-loop fix (2026-06-24).** `straight_line_km` was redefined as the route's convex-hull
  diameter, fixing 11 genuine loop routes whose endpoint-distance had floored to ~0 and inflated
  their detour ratios into the tens of thousands. Net effect: 6 of 247 routes lost a spurious
  "Indirect" flag; demand/score metrics unaffected.

The audit's headline — a large majority of the existing network is indirect and/or low-demand under
a formal objective — is itself a diagnostic finding, independent of the generative layer.

---

<a name="w8--validation"></a>

## W8 — Validation

W8 tests the framework four ways.

**(1) Masked backtests — does the generator re-propose held-out lines?** Mask a line/agency's GTFS
stops, recompute accessibility + gap, re-run the generator, and measure shape overlap with the
masked-out routes. Six masks (all on the aligned generator):

| Mask | Stops | Feasible re-proposed | Mean overlap |
|---|---|---|---|
| Premium (Mi Macro + Mi Tren) | 1,344 | 5 | **0.150** |
| Mi Macro (BRT only) | 1,268 | 5 | **0.166** |
| Line 1 (rail + feeder) | 138 | 4 | **0.000** |
| Line 2 (rail + feeder) | 108 | 4 | **0.000** |
| Line 3 (rail + feeder) | 126 | 4 | **0.000** |
| Line 4 (out-of-sample probe) | — | — | **0.05** recall |

**Finding:** the generator **weakly traces the dense Mi Macro BRT feeder network (~0.15–0.17) but
reconstructs no rail line** (Lines 1–4 ≈ 0.00–0.05). Masking a single rail line barely moves
accessibility (parallel buses survive; non-zero AGEBs stay at 1,266), so no strong new gap forms on
the held-out corridor. This is the documented anchor-funnel limitation, now measured on n=6.

**(2) Line 4 natural experiment.** The GTFS snapshot predates SITEUR Line 4 (opened 2025-12-15), so
the corridor is treated as unserved — an out-of-sample test. The **diagnostic layer is
corroborated**: the 68 AGEBs within 800 m of Line 4 are **33.8% High-gap vs 20.7% metro-wide
(1.6×)** and 0% Low-gap, flagged via the *supply* gap. The **generative layer does not reconstruct
Line 4** (best feasible recall 0.05) — Line 4 is mostly deep-interior unserved, off the
served/unserved seam the frontier anchors target.

**(3) Benchmark vs premium routes.** The 4 feasible W6 corridors overlap 33 premium route shapes at
**10.5% mean** (total 44.9 km) — W6 mostly identifies new areas, not existing lines. W6_G02 overlaps
premium route MP-C03 at 42% (shape-proximity), read as mild revealed-preference corroboration
(planners drew a similar alignment) rather than redundancy (its AGEB-set Jaccard is only 0.18).

**(4) Before/after coverage.** Adding the W6 corridors:

| Metric | Before | After | Δ |
|---|---|---|---|
| AGEB coverage rate | 69.9% | 71.0% | **+1.1%** |
| Accessibility Gini (lower = fairer) | 0.6333 | 0.6146 | **−0.0187** |
| Pop-served / route-km | — | 4,195 | — |
| AGEBs newly served | — | 47 | — |
| Population newly served | — | 120,648 | — |

**(5) Question B — do W6's own corridors have merit?** Each feasible corridor scored on genuine need
(High-gap share vs 20.7% baseline), non-redundancy (best Jaccard vs 247 existing routes), and
efficiency (demand/km percentile vs existing routes):

| Corridor | High-gap | Best Jaccard | Demand/km pct | Verdict |
|---|---|---|---|---|
| **W6_G02** | 56% | 0.18 (unique) | 73rd | **PASS** |
| **W6_G03** | 60% | 0.03 (unique) | 66th | **PASS** |
| W6_G00 | 50% | 0.06 (unique) | 30th | MIXED (low efficiency) |
| W6_G01 | 33% | 0.08 (unique) | 5th | MIXED (low efficiency) |

**W6_G02 passes all three axes and is a substantive corridor** (not the degenerate short stub that
was the only pass under the pre-re-architecture generator). This is the direct, positive evidence
for the generative layer, and it **overturns the earlier "essentially negative" Question-B verdict**.
An interactive corridor map is at `outputs/w8/w6_corridor_map.html`.

**Reading the validation as a whole.** Two distinct questions: (A) does the generator reproduce
*built* lines? (B) does it produce *good* corridors? Every backtest measures A, which is a weak,
asymmetric proxy for B — built lines are chosen for political/financial/land reasons a demand model
cannot see, so non-reconstruction is faint evidence against the generator. B is measured directly by
(5): partially positive. The **diagnostic layer (W3/W4) is validated and is the strong
contribution**; the **generative layer is characterized and partially positive**.

---

<a name="w9--transferability"></a>

## W9 — Transferability

The framework is designed to transfer to any Mexican metro on Tier-1 open data. The second-city
pipeline for **Monterrey, Nuevo León** (12 municipalities, ~1,958 AGEBs) is operational through the
W1-equivalent demand surface: census + DENUE + AGEB shapefile + OSM graph acquired, gravity model
and demand surface built. Early transfer finding: Monterrey's mean vehicle rate (0.634) exceeds
ZMG's (0.577), i.e. structurally lower transit propensity. W9 is **blocked on a Metrorrey/Transmetro
GTFS feed** for the W3 accessibility equivalent; downstream (W3→W6) runs once GTFS is acquired.

---

<a name="limitations--future-work"></a>

## Limitations & Future Work

- **Generator does not reconstruct rail lines** (characterized, not a defect): the frontier-anchor /
  diameter-trunk architecture targets the served/unserved seam of the *bus* network and cannot home
  in on sparse deep-interior rail corridors. Reconstruction is a weak proxy for merit regardless.
- **Low-efficiency connectors persist** (W6_G00/G01) alongside the good corridor (G02); feasibility
  no longer *selects against* merit (the old confound), but the two are not yet strongly correlated.
- **Euclidean distances** in the gravity model (W1) are a proxy for network travel time; the W2
  calibration absorbs some of this but a full network-skim would sharpen demand.
- **Accessibility uses a static 45-minute budget** and headway/2 wait; time-of-day variation is not
  modeled.
- **Transferability** is demonstrated only to the Tier-1 stage for Monterrey; a full second-city
  validation awaits GTFS.
- **Optional shaper improvement**: a TSP-where-feasible hybrid would marginally improve W6_G00
  (+2 AGEBs) but loses G01; diameter-trunk is the confirmed default.

---

<a name="methodological-references"></a>

## Methodological References

- **Bertolini (1996/1999)** — Node–Place model (foundation of the NPP framing).
- **Liu et al. (2024/2025)** — NP-RV model; LightGBM + SHAP for station/suitability analysis.
- **Niu et al. (2023)** — Random Forest for station suitability.
- **Takahashi (1980)** — Steiner-tree heuristic for network design (basis of the MST corridor
  shaper).

---

*Figures: W3 SHAP beeswarms `outputs/w3/shap/`; W4 weights and score maps `outputs/w4/`; W6 Pareto
front `outputs/w6/pareto_front.png` and corridor GeoJSON `outputs/w6/corridor_candidates.geojson`;
W8 before/after and backtest charts `outputs/w8/`; interactive corridor map
`outputs/w8/w6_corridor_map.html`.*
