# W9 Onboarding — Toluca (large) & Aguascalientes (compact)

Two Monterrey-replacement transfer cities are wired up to run the W9 Tier-1 demand
pipeline. **Toluca** (ZM Toluca, 16 municipios, ~2.3M — large, ZMG-scale) and
**Aguascalientes** (ZM Aguascalientes, 3 municipios, ~1.1M — compact) give a
large-vs-small transfer comparison. See `docs/w9_gtfs_scouting_findings.md` for why
these two.

## What's already done (in-repo)

- **City configs:** `src/w9_city_config_tol.py`, `src/w9_city_config_ags.py` (identity,
  CONAPO municipio codes, bbox, GTFS source, ZMG-calibrated β=1.2005 prior).
- **City-parameterized runner:** `src/w9_run_tier1.py --city {mty,tol,ags}`.
- **Parameterized data-prep:** `scripts/data_prep/make_city_census_extract.py` and
  `make_city_denue_extract.py` (both `--city …`, with a municipio-coverage sanity check).
- **GTFS staged & validated** (for the later W3 step): `data/gtfs_tol/` (60,295 stops;
  gitignored, 28 MB) and `data/gtfs_ags/` (1,506 stops; committed). Re-fetch Toluca with
  `curl -k "https://datos.movimex.gob.mx/gtfs/toluca.gtfs.zip" -o data/gtfs_tol.zip`
  (host has an expired TLS cert → `-k`).

## What you need to download (INEGI blocks scripted download — use a browser)

Per city, **2 files** (DENUE is optional — improves attractions; falls back to a
population proxy if absent):

| File | Toluca (state 15) | Aguascalientes (state 01) |
|------|-------------------|----------------------------|
| **CPV2020 census** (AGEB y manzana urbana, CSV) | [INEGI Microdatos](https://www.inegi.org.mx/programas/ccpv/2020/#Microdatos) → *AGEB y manzana urbana* → **México (15)** → CSV | same portal → **Aguascalientes (01)** → CSV |
| **AGEB shapefile** (Marco Geoestadístico 2020) | [INEGI MG 2020](https://www.inegi.org.mx/temas/mg/) → state **15** → extract `2020_1_15_A/2020_1_15_A.shp` into `data/` | state **01** → `data/2020_1_01_A/2020_1_01_A.shp` |
| DENUE (optional) | [INEGI descarga](https://www.inegi.org.mx/app/descarga/?ti=6) → state 15 CSV | state 01 CSV (masiva path `denue_01_csv.zip` also works) |

Place the raw census CSV under `data/ageb_mza_urbana_{15,01}_cpv2020_csv/…` (or pass its
path with `--src`). The AGEB shapefile just needs to land at `data/2020_1_{15,01}_A/`.

## Run (per city)

```bash
# 1. slim the raw census to the ZM extract (asserts exact municipio coverage)
python scripts/data_prep/make_city_census_extract.py --city tol   # 16 munis expected
python scripts/data_prep/make_city_census_extract.py --city ags   #  3 munis expected

# 2. (optional) slim DENUE for richer attractions
python scripts/data_prep/make_city_denue_extract.py  --city tol
python scripts/data_prep/make_city_denue_extract.py  --city ags

# 3. run the Tier-1 demand pipeline
python src/w9_run_tier1.py --city tol
python src/w9_run_tier1.py --city ags
```

Outputs land in `outputs/w9/{tol,ags}_demand_surface.csv`, `{tol,ags}_tier1_summary.csv`,
and `transfer_comparison_{tol,ags}.csv` (ZMG vs city: n_agebs, municipios, mean vehicle
rate, mean transit propensity). This is the "both city sizes" comparison.

## Then (W3 — the GTFS payoff, not yet wired)

The GTFS feeds are staged so the coverage-gap diagnostic (the strong thesis contribution)
can follow: adapt `w3_accessibility.py` / `w3_coverage_gap.py` to read `data/gtfs_{tol,ags}/`
and the city demand surface. This is the next build after Tier-1 results look right.

## Results — Tier-1 demand surface (run 2026-07-17)

Both cities ran end-to-end. Consolidated transfer comparison
(`outputs/w9/w9_transfer_comparison_4city.csv`), sorted by car ownership:

| City | Metro pop | ZM munis | Urban AGEBs (matched) | Mean vehicle rate | Mean transit propensity | DENUE |
|------|-----------|----------|-----------------------|-------------------|-------------------------|-------|
| **Toluca** | 2.3M | 16 | 538 | **0.529** | **0.471** | population proxy |
| ZMG (Guadalajara) | 5.0M | 10 | 1,881 | 0.577 | 0.423 | full |
| Monterrey | 2.3M | 12 | 1,903 | 0.635 | 0.365 | full |
| **Aguascalientes** | 1.1M | 3 | 356 | **0.667** | **0.333** | full |

**Two transfer findings:**
1. **A monotonic transit-dependence gradient:** Toluca (most transit-dependent) → ZMG → Monterrey
   → Aguascalientes (most car-oriented). Toluca has *lower* car ownership than Guadalajara (a
   lower-income metro → higher transit propensity); Aguascalientes is the most car-oriented
   (prosperous, compact). The demand surface transfers cleanly and discriminates between metros.
2. **Urban-AGEB count decouples from metro population:** Toluca's 2.3M metro has only 538 urban
   AGEBs vs ZMG's 1,881 — because ZM Toluca spreads across 16 municipios with many semi-rural
   AGEBs, only a minority of which are dense/urban. The pipeline's unit-of-analysis scales very
   differently across metros; a "large metro" by population can be small in urban AGEBs.

Shapefile match rates (real AGEBs → polygons): Toluca 538/577 (93%), Aguascalientes 356/357
(99.7%). Match is computed after the census extract drops hierarchical summary rows (municipio /
locality totals at MZA=="000", AGEB=="0000") and alpha-suffix AGEBs, per the ZMG base.ageb
convention.

## Results — W3 supply + coverage-gap diagnostic (the GTFS payoff, run 2026-07-17)

`src/w9_run_w3.py --city {tol,ags}` builds the W3 supply layer (GTFS
cumulative-opportunities accessibility, 45-min budget, jobs reachable) and the coverage-gap
diagnostic from files, reusing the pure ZMG W3 functions. **This is the layer Monterrey could
never reach** (no GTFS). Consolidated (`outputs/w9/w9_w3_comparison.csv`):

| City | Urban AGEBs | Mean vehicle rate | Unserved % (no stop ≤400m) | High-gap % |
|------|-------------|-------------------|-----------------------------|------------|
| ZMG (Guadalajara) | 1,881 | 0.577 | 32.7% | 20.7% |
| **Toluca** | 538 | 0.529 | 19.1% | **14.9%** |
| **Aguascalientes** | 356 | 0.667 | 19.7% | **9.6%** |

**Findings:**
1. **The diagnostic transfers cleanly and differentiates cities.** High-gap share follows a clear
   gradient — ZMG 20.7% > Toluca 14.9% > Aguascalientes 9.6%. Because High-gap = (top-2 demand
   quintile ∩ bottom-2 access quintile), a *low* share means demand and supply are well aligned:
   Aguascalientes' compact network serves its (modest, car-suppressed) demand well; Guadalajara has
   the most high-demand-yet-underserved AGEBs.
2. **Both transfer cities are better-covered than ZMG** (~19% unserved vs 32.7%) — their compact
   urban footprints plus dense feeder GTFS (Toluca's feed alone has 60,295 stops) reach more of
   their area; ZMG's 615 zero-access AGEBs are largely peripheral.

Both cities use **DENUE employment** as the accessibility opportunity (matching ZMG). Toluca's
Edomex DENUE is split into two INEGI parts (`denue_15_1_csv.zip` + `denue_15_2_csv.zip`, ~820k
establishments combined); Aguascalientes' downloads as one (`denue_01_csv.zip`).

Not yet built for the transfer cities: W3.3 supervised retrain (needs the full 14-feature NPP
build — OSM node + DENUE place indicators), W4 prioritization, W5/W6 corridor generation. The
**diagnostic (W1→W3, the thesis's strong contribution) is now demonstrated end-to-end on two new
metros of very different size.**

## Results — NPP features + W4 prioritization (run 2026-07-17)

The full 14-feature NODE+PLACE+PEOPLE build (`src/w9_build_nppv.py --city {tol,ags}`) and the
CRITIC/EWM + equity prioritization (`src/w9_run_w4.py --city {tol,ags}`) now run for both cities,
reusing the pure ZMG feature + weighting functions.

**Inputs assembled per city:**
- **Node:** OSM drive graphs downloaded via osmnx (Toluca 116k nodes / 271k edges; Aguascalientes
  42k / 96k) — intersections, 4-way density, street density per AGEB.
- **Place:** slim INEGI DENUE aggregated by AGEB code (SCIAN sector from `codigo_act`, employment
  from `per_ocu`) — POI/employment/retail/service density, land-use mix.
- **People:** census + **CONAPO marginación (IM_2020, continuous)** + **CONEVAL rezago** (published
  at AGEB level only as a *grade* Muy bajo…Muy alto → mapped to an ordinal 0–4 as `IRS_2020`, a
  documented approximation of ZMG's continuous index; direction preserved, higher = more rezago).
  Equity data via `scripts/data_prep/make_city_indicators_extract.py --city {tol,ags}`.

**W4 top prioritization drivers (ensemble CRITIC/EWM weight):**

| City | 1st | 2nd | 3rd | final_score mean |
|------|-----|-----|-----|------------------|
| Toluca | `pe_rezago_n` (0.18) | `p_employment_proxy_n` (0.14) | `p_service_density_n` (0.12) | 0.457 |
| Aguascalientes | `pe_rezago_n` (0.25) | `p_employment_proxy_n` (0.13) | `p_service_density_n` (0.13) | 0.440 |

**Transfer finding:** the objective weighting *adapts per city* — `pe_rezago_n` (social-lag
variation) is the top discriminator in both new metros, whereas ZMG's top drivers were
`pe_population_n` / `p_employment_proxy_n`. The framework re-derives its own weights from each
city's data rather than importing ZMG's. Outputs: `outputs/w9/{key}_nppv_features.csv`,
`{key}_w4_weights.csv`, `{key}_prioritization.csv`.

Equity approximation caveat: for a fully ZMG-identical equity term, substitute CONEVAL's continuous
IRS (not published at AGEB level in 2020) — the ordinal-grade mapping is the faithful available
proxy. Marginación is the exact CONAPO continuous IM_2020, INVERTED in normalization (higher
`pe_marginacion_n` = more marginalized), matching the 2026-07-12 ZMG equity fix.

## Notes / caveats

- **β = 1.2005** (the current ZMG-calibrated prior) is used for both cities; no local EOD
  survey. The size-comparison signal (vehicle rate / transit propensity) is β-independent.
- The Edomex census filter **must** be exact (125 municipios in the state); the extract
  script asserts exactly 16 distinct munis and prints per-municipio AGEB counts, so a wrong
  CVE_MUN surfaces immediately. Aguascalientes asserts 3.
- MTY (`--city mty`) still runs unchanged from the committed data (verified: 0.635 vehicle
  rate, 1,903 AGEBs).
