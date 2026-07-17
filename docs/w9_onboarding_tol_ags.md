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

## Notes / caveats

- **β = 1.2005** (the current ZMG-calibrated prior) is used for both cities; no local EOD
  survey. The size-comparison signal (vehicle rate / transit propensity) is β-independent.
- The Edomex census filter **must** be exact (125 municipios in the state); the extract
  script asserts exactly 16 distinct munis and prints per-municipio AGEB counts, so a wrong
  CVE_MUN surfaces immediately. Aguascalientes asserts 3.
- MTY (`--city mty`) still runs unchanged from the committed data (verified: 0.635 vehicle
  rate, 1,903 AGEBs).
