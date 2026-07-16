# External Data Acquisition Manifest

Purpose: single source of truth for the external datasets identified to strengthen the
thesis (validation + feature credibility), with verified source pages, AGEB-vintage
compatibility handling, and target repo paths. Compiled 2026-07-09.

## Vintage compatibility rule (read first)

The project baseline is **2020 Marco Geoestadistico** (CPV2020 + `data/ageb_zmg_2020_v2.gpkg`,
2,068 ZMG AGEBs).

- Any dataset **derived from the 2020 census** (same vintage) -> safe direct join on `CVEGEO`.
- Any dataset from **another vintage** (2010 census, Censos Economicos 2019, DENUE's own
  coding) -> do **NOT** join on `CVEGEO`. Reconcile by **areal interpolation**: intersect the
  source polygons with the 2020 AGEB polygons in EPSG:6372 and apportion values by area (or,
  better, population) weight.
- Correction to an earlier note: INEGI's AGEEML "tablas de equivalencia" only go down to
  **locality** level, not AGEB. **There is no official AGEB-to-AGEB crosswalk.** Areal
  interpolation is the practical reconciliation method.
- Ridership / corridor totals are **not AGEB-keyed** -> no vintage problem; aggregate the
  model's AGEB outputs up to the corridor/system to compare.

---

## 1. Line 4 observed ridership  --  STATUS: ACQUIRED

- File: `data/raw/ridership/linea4_ridership_observed.csv` (compiled from verified figures).
- Vintage/compatibility: N/A (corridor total, not AGEB-keyed).
- Supports: **quantitative arm of the Line 4 backtest (Gap B)** -- compare the modeled
  transit-demand sum over the Line 4 catchment against observed boardings.
- CRITICAL caveat baked into the file: Dec 15-31 was **free fare**; the 106k/day figure is a
  **mature-state projection**, not a first-month expectation. Use a **steady-state paid month
  (Feb 2026+)** for any magnitude comparison, and frame the free ramp-up separately. Do not
  compute a naive observed/projected ratio.
- Sources: SITEUR one-month bulletin; El Informador; El Congresista (see CSV `source` column).

## 2. CONAPO Indice de Marginacion Urbana 2020 (AGEB level)  --  STATUS: ACQUIRED + JOIN VERIFIED

- Landing page (verified): https://www.gob.mx/conapo/documentos/indices-de-marginacion-2020-284372
- On that page, under the heading **"Indice de marginacion urbana 2020"**, download:
  - link labelled **"Base de datos a nivel AGEB 2020"** (the AGEB socioeconomic + index table)
  - optional: **"Programa de calculo a nivel AGEB urbana 2020"** (the R script, for method transparency)
  - optional cross-check: **"Base de datos a nivel colonia 2020"** and **"Cartografia digital (shp)
    del indice de marginacion urbana por colonia 2020"**
- Portal note (from the page): use Firefox/Edge; in Chrome right-click the link -> "Guardar enlace como".
- Vintage/compatibility: **2020 (CPV2020) -> SAFE direct `CVEGEO` join.**
- Target path: `data/external/conapo_imu_2020_ageb.xlsx` (keep original filename alongside).
- Supports: PROVENANCE/VERSION check only. `pe_marginacion` is ALREADY sourced from CONAPO
  `IM_2020` (see `data/raw/census/zmg_indicators_combined.csv`, cols IM_2020/GM_2020/IRS_2020),
  so this download is NOT an independent validator of the equity term -- it is the same source.
  Genuine added value: the component sub-indicators and the colonia layer, if ever needed.

### VERIFIED RESULT (2026-07-09)
- Source file: `data/IMU_2020.xls` (CONAPO, 50,790 national AGEBs; sheet `IMU_2020`).
- Ready-to-join outputs written: `data/external/conapo_imu_2020_zmg.csv` (2,068 base AGEBs
  left-joined, with `has_conapo` flag) and `data/external/conapo_imu_2020_unmatched.csv` (200).
- **Key compatibility: CONFIRMED.** 13-char `CVE_AGEB` == base `CVEGEO`; direct join valid,
  NO areal interpolation needed. The 200 unmatched keys appear NOWHERE in the national CONAPO
  file, so this is a **scope** gap, not a vintage/format mismatch.
- **Coverage: 1,868 / 2,068 = 90.3%.** Missing 200 = CONAPO's index is *urban-only*, so it drops
  AGEBs in secondary localities and peripheral zones. The gap is CONCENTRATED in peripheral
  growth municipios (Tlajomulco 097: 64 missing; Zapotlanejo 124: 16; Acatic 002: 15) -- i.e.
  exactly the high-priority / Line-4-corridor areas. **Do NOT wholesale-replace `pe_marginacion`
  with CONAPO** or you blind the equity term where it matters most.
- **Do NOT use `IMN_2020`.** It is min-max normalized NATIONALLY, so within ZMG it is compressed
  (mean 0.948, std 0.024, range 0.80-0.997) and barely discriminates. Use raw `IM_2020`
  (within-ZMG range 102.6-127.7) re-normalized inside the ZMG sample (std 0.125, ~5x the spread),
  or the `GM_2020` grade. `corr(IM_2020, IMN_2020)=1.0` so no information is lost by re-normalizing.
- **Recommended use: provenance/version + coverage check, NOT a correlation.** Since
  `pe_marginacion` already IS CONAPO `IM_2020`, verify the committed copy matches the official file
  and check how the 200 out-of-scope AGEBs are handled (null vs imputed) -- see the WSL check.

## 3. INEGI Marco Geoestadistico 2020 - AGEB polygons  --  STATUS: LIKELY ALREADY HAVE

- You already hold `data/ageb_zmg_2020_v2.gpkg` (2020 ZMG AGEBs). Only re-download if you need
  national/other-state 2020 polygons.
- Landing: https://www.inegi.org.mx/temas/mg/  (Descarga -> "Areas geoestadisticas basicas urbanas").
- Needed only as the **target geometry for areal interpolation** if you ingest any non-2020 dataset.

## 4. Censos Economicos 2019 (personal ocupado)  --  STATUS: OPTIONAL / HANDLE WITH CAUTION

- Landing: https://www.inegi.org.mx/programas/ce/2019/
- Aggregate tabulator (SAIC): https://www.inegi.org.mx/app/saic/
- Vintage/compatibility: **2018/2019 marco != 2020** -> NOT a safe `CVEGEO` join; also INEGI
  **suppresses fine-geography cells for confidentiality**, leaving holes in low-density AGEBs.
- Recommendation: use **only as a municipality-level cross-check** of the DENUE `employment_proxy`,
  not as an AGEB feature. If AGEB-level is ever required, areal-interpolate from the 2019 marco.
- Supports: sanity-check that the DENUE employment proxy tracks real `personal ocupado` in aggregate.

## 5. IIEG ETUP system ridership  --  STATUS: ALREADY IN REPO

- File in repo: `data/raw/ridership/jalisco_ridership_etup.csv` (system-level, semi-annual, by
  service type: tren electrico, Macrobus, SITREN, trolebus, Mi Transporte Electrico).
- Landing (for updates): https://iieg.gob.mx/ns/?page_id=25290
- Compatibility: system/municipality level; **station-level open data is not published.**
- Supports: magnitude/trend sanity check of the W1 demand surface at system level (not micro-placement).

---

## Priority order for manual download

1. **CONAPO IMU 2020 AGEB** (#2) -- highest credibility payoff, zero compatibility risk.
2. Nothing else is required. Line 4 (#1) is done; ETUP (#5) is in repo; CE2019 (#4) is optional
   and vintage-risky; MG polygons (#3) you already have.

## What was NOT downloadable automatically (and why)

- CONAPO/INEGI portals are click-through / JavaScript-rendered; approved fetch tools return the
  page text but strip the file `href`s, and the browser extension was offline at compile time.
- Direct file URLs were deliberately **not guessed** -- a wrong link in a thesis data pipeline is
  worse than a manual click. The verified landing pages + exact link labels above make each
  download unambiguous.
