# W9 Transferability Report: ZMG → Toluca + Aguascalientes

**Pipeline:** Demand-driven transit corridor prioritization (W1–W6)
**Source city:** ZMG — Zona Metropolitana de Guadalajara (Jalisco, CVE_ENT=14)
**Transfer cities:** Toluca / ZM Valle de Toluca (México, CVE_ENT=15) and Aguascalientes
(CVE_ENT=01)
**Date:** 2026-07-17
**Status:** ✅ Full pipeline (W1 demand → W3 supply/coverage-gap → W4 prioritization → W6 corridor
generation) run end-to-end for both transfer cities.

> **Note on the original plan.** The W9 second city was **Monterrey**, but its Metrorrey/Transmetro
> GTFS feed proved unavailable (confirmed 2026-06-24), which blocks the W3 supply layer — the core
> diagnostic. Rather than ship a Tier-1-only transfer, Monterrey was retained as a Tier-1 reference
> and **two GTFS-available metros were onboarded instead**: **Toluca** (large, 16 municipios) and
> **Aguascalientes** (compact, 3 municipios), chosen from a verified scout of the Mobility Database
> (`docs/w9_gtfs_scouting_findings.md`). This yields a stronger, deliberately size-contrasted
> transfer study.

---

## 1. Study design

Four Mexican metros span a wide range of size and car dependence, letting the framework be tested
across structurally different cities using the **same code path** (`src/w9_*.py --city …`):

| City | Metro pop | ZM municipios | Urban AGEBs | Role |
|------|-----------|---------------|-------------|------|
| ZMG (Guadalajara) | ~5.0M | 10 | 1,881 | Source (fully calibrated) |
| Monterrey | ~5.3M | 12 | 1,903 | Tier-1 reference (GTFS unavailable) |
| **Toluca** | ~2.3M | 16 | 538 | **Full transfer (large/dispersed)** |
| **Aguascalientes** | ~1.1M | 3 | 356 | **Full transfer (compact)** |

**Research questions.**
- **RQ1 (model transfer):** Do ZMG-calibrated parameters (gravity β=1.2005, CRITIC/EWM weighting
  recipe, equity α=0.20) produce plausible surfaces for new cities without local recalibration?
- **RQ2 (diagnostic transfer):** Does the coverage-gap diagnostic differentiate cities meaningfully?
- **RQ3 (generative transfer):** Does W6 produce substantive feasible corridors in new cities, or
  only in ZMG?

**Transfer parameters (held fixed from ZMG).** Gravity β=1.2005 (ZMG-calibrated prior; no local
EOD survey for the transfer cities — the demand-surface transfer signal is β-independent anyway);
trip-generation rates (2.5 trips/person/day, youth multiplier); attraction weights; W5 objective
weights and the 1.8 anchor-directness cap. **Re-derived per city:** the CRITIC/EWM feature weights
(computed from each city's own data), all demand/supply/gap surfaces.

---

## 2. Data availability (transfer cities)

Tier-1 (INEGI census, DENUE, OSM) is national and available for every candidate. The differentiator
was **GTFS** (Tier-2), which is what made Toluca/Aguascalientes viable where Monterrey was not.

| Layer | Toluca (15) | Aguascalientes (01) | Source |
|-------|-------------|----------------------|--------|
| CPV2020 census (AGEB urbana) | ✅ | ✅ | INEGI Microdatos (`RESAGEBURB`) |
| DENUE business registry | ✅ (split `denue_15_1/2`) | ✅ (`denue_01`) | INEGI masiva |
| AGEB shapefile | ✅ | ✅ | INEGI Marco Geoestadístico 2020 |
| OSM drive graph | ✅ 116k nodes | ✅ 42k nodes | osmnx |
| **GTFS** | ✅ 60,295 stops | ✅ 1,507 stops | Mobility Database (official) |
| CONAPO marginación (IM_2020) | ✅ | ✅ | CONAPO IMU_2020 (national) |
| CONEVAL rezago (AGEB grade) | ✅ | ✅ | CONEVAL GRS_AGEB_urbana_2020 |
| EOD OD survey | ❌ (β prior used) | ❌ (β prior used) | — |

---

## 3. Results

### 3.1 Demand surface (W1) — car dependence gradient

| City | Mean vehicle rate | Mean transit propensity |
|------|-------------------|--------------------------|
| **Toluca** | 0.529 | **0.471** (most transit-dependent) |
| ZMG | 0.577 | 0.423 |
| Monterrey | 0.635 | 0.365 |
| **Aguascalientes** | 0.667 | **0.333** (most car-oriented) |

A clean **monotonic gradient**: Toluca (lower-income, transit-dependent) → ZMG → Monterrey →
Aguascalientes (prosperous, compact, car-oriented). The demand surface transfers cleanly and
discriminates between metros. Note that urban-AGEB count **decouples from metro population**
(Toluca's 2.3M metro has only 538 urban AGEBs vs ZMG's 1,881) — ZM Toluca spreads across 16
semi-rural municipios.

### 3.2 Supply + coverage gap (W3) — the diagnostic (RQ2: ✅)

GTFS cumulative-opportunities accessibility (45-min budget, jobs reachable) + coverage-gap index.

| City | Unserved % (no stop ≤400m) | High-gap % |
|------|-----------------------------|------------|
| ZMG | 32.7% | 20.7% |
| **Toluca** | 19.1% | **14.9%** |
| **Aguascalientes** | 19.7% | **9.6%** |

High-gap share follows a clear gradient (ZMG > Toluca > Aguascalientes). Because High-gap =
(top-2 demand quintile ∩ bottom-2 access quintile), a *low* share means demand and supply are well
aligned — Aguascalientes' compact network serves its modest demand well; Guadalajara has the most
high-demand-yet-underserved AGEBs. Both transfer cities are better-covered than ZMG (denser feeder
GTFS over smaller footprints). **The diagnostic transfers and differentiates — the thesis's strong
contribution, now demonstrated on cities Monterrey could not support.**

### 3.3 Prioritization (W4) — weights re-derive per city

| City | Top-3 objective-weight drivers (CRITIC/EWM ensemble) | final_score mean |
|------|-------------------------------------------------------|------------------|
| ZMG | `pe_population_n`, `p_employment_proxy_n`, `pe_rezago_n` | 0.413 |
| **Toluca** | `pe_rezago_n` (0.18), `p_employment_proxy_n` (0.14), `p_service_density_n` (0.12) | 0.457 |
| **Aguascalientes** | `pe_rezago_n` (0.25), `p_employment_proxy_n` (0.13), `p_service_density_n` (0.13) | 0.440 |

**RQ1 finding:** the framework does not import ZMG's weights — the objective CRITIC/EWM weighting
**re-derives itself from each city's data**. `pe_rezago_n` (social-lag variation) is the top
discriminator in both new metros, whereas ZMG's top driver was population — an interpretable,
city-specific adaptation. Equity uses CONAPO's continuous IM_2020 (marginación, INVERTED per the
2026-07-12 ZMG fix) + CONEVAL rezago mapped from AGEB grade to an ordinal 0–4 (documented
approximation of ZMG's continuous IRS; direction preserved).

### 3.4 Corridor generation (W6) — the generative layer (RQ3: ✅)

Canonical re-architected generator (frontier anchors → MST-diameter trunk → anchor-directness gate,
cap 1.8). Best feasible corridor per city:

| City | Corridors / feasible | Best feasible corridor | Mode |
|------|----------------------|------------------------|------|
| **Toluca** | 5 / 4 | **W6_G01** — 12.6 km, 23 AGEBs, 133,728 demand/day, directness 1.19 | Light Rail/Metro |
| **Aguascalientes** | 5 / 3 | **W6_G05** — 5.9 km, 12 AGEBs, 107,633 demand/day, directness 1.27 | Light Rail/Metro |

**RQ3 finding:** the generator produces **substantive, feasible, high-demand corridors** in both new
cities — not just stubs. Toluca's W6_G01 is the transfer analogue of ZMG's merit-passing W6_G02.
The **same feasibility-vs-directness signature reproduces**: each city yields one genuine
high-demand corridor plus short stubs, and one high-demand corridor that blows the 1.8 directness
cap (Toluca G02 at 8.76, Aguascalientes G03 at 2.03) — the documented ZMG behaviour, transferred.

---

## 4. Transfer error / limitations

- **No local EOD calibration** — β=1.2005 is transferred from ZMG. The size-comparison metrics
  (vehicle rate, transit propensity, High-gap share) are β-independent; absolute demand magnitudes
  carry the prior's error. A local EOD survey (if obtainable) would tighten RQ4.
- **Rezago approximation** — CONEVAL publishes only a categorical *grade* at AGEB level for 2020, so
  `pe_rezago` is an ordinal 0–4 map rather than ZMG's continuous IRS. Direction is preserved;
  magnitude granularity is coarser. Marginación is the exact continuous CONAPO IM_2020.
- **Population-independent unit scaling** — the AGEB unit is much coarser relative to population in
  ZM Toluca (semi-rural spread), so cross-city AGEB counts are not directly comparable; per-AGEB and
  per-capita metrics are.
- **Not run for transfer cities:** W7 (existing-route audit), W8 (masked backtests), W3.3 supervised
  retrain. Inputs for all three are in place per city; none are required for the transfer claim.

---

## 5. Conclusion

The **complete demand-driven framework transfers end-to-end to two metros of very different size**
using a single parameterized code path, on cities Monterrey's missing GTFS made impossible. The
diagnostic layer (W1→W4) differentiates cities interpretably and re-derives its own objective
weights; the generative layer (W6) produces substantive feasible corridors in both. This is a
strong, defensible transferability result for the thesis.

**Reproduce:** see `docs/w9_onboarding_tol_ags.md` (exact data downloads + one command per stage).
All per-city outputs are in `outputs/w9/{tol,ags}_*` and the consolidated comparisons
`w9_transfer_comparison_4city.csv`, `w9_w3_comparison.csv`.
