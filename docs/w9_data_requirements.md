# W9 Data Requirements — Tiered Data Matrix

**Pipeline:** Predictive Transit Placement (NPP-V Framework)  
**Cities:** ZMG (Guadalajara, Jalisco) and MTY (Monterrey, Nuevo Leon)  
**Date:** 2026-06-15

---

## Tier Definitions

| Tier | Description |
|------|-------------|
| **Tier-1** | Universally available across Mexican metropolitan areas via federal open-data portals (INEGI, OSM). Sufficient to run W1, W4, W5, W6 core logic. |
| **Tier-2** | Available in major Mexican cities but requires per-city sourcing. GTFS feeds (W3) and origin-destination surveys (W2). |
| **Tier-3** | City-specific or proprietary. Ridership counts, local open-data portals, operator APIs. Not transferable without per-city collection. |

---

## Data Layer Requirements

### 1. INEGI CPV2020 — Census Microdata (AGEB Level)

| Field | Details |
|-------|---------|
| **Tier** | 1 |
| **Source URL** | https://www.inegi.org.mx/programas/ccpv/2020/#Microdatos |
| **Download path** | Microdatos > AGEB y manzana urbana > [State] > CSV |
| **ZMG status** | Available and used — `ageb_mza_urbana_14_cpv2020_csv/` (Jalisco, CVE_ENT=14) |
| **MTY status** | Not yet downloaded — NL ZIP at: https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/ageb_manzana/conjunto_de_datos_ageb_urbana_19_cpv2020_csv.zip |
| **Pipeline steps** | W1 (trip generation, demand surface), W4 (people indicators) |
| **Key columns** | `POBTOT`, `P_15A17`, `P_18A24`, `P_15A29`, `VPH_AUTOM`, `VIVPAR_HAB`, `MZA`, `ENTIDAD`, `MUN`, `LOC`, `AGEB` |
| **AGEB filter** | `MZA == "000"` selects AGEB summary rows; filter `MUN` to target municipalities |
| **Format notes** | CSV, latin-1 encoding; all values as strings; numeric coercion required. Schema is identical across all Mexican states — no adaptation needed. |
| **Approx size** | 50-100 MB compressed per state |

---

### 2. DENUE — Business Registry (Point Data)

| Field | Details |
|-------|---------|
| **Tier** | 1 |
| **Source URL** | https://www.inegi.org.mx/app/descarga/?ti=6 |
| **ZMG status** | Available and used — `data/INEGI_DENUE_UTF8.csv` (ZMG area extract) |
| **MTY status** | Not yet downloaded — request NL state extract from INEGI DENUE portal |
| **Pipeline steps** | W1 (employment proxy / attractions), W4 (place indicators: POI density, employment proxy, retail density) |
| **Key fields** | `CODIGO_ACT` (SCIAN code), `PER_OCU` (employment size class), `LATITUD`, `LONGITUD` |
| **Employment proxy** | Size class mapped to headcount using `EMPLOYMENT_PROXY_MAP` in `config.py`; establishments with <11 employees excluded |
| **Format notes** | CSV UTF-8; spatial join to AGEBs via point-in-polygon. SCIAN codes are national standard — no adaptation needed. |
| **Adaptation** | Filter by municipality codes: ZMG uses Jalisco DENUE; MTY needs Nuevo Leon DENUE extract |

---

### 3. OSM Street Network (via osmnx)

| Field | Details |
|-------|---------|
| **Tier** | 1 |
| **Source** | OpenStreetMap via `osmnx` library (`graph_from_bbox` or `graph_from_place`) |
| **ZMG status** | Downloaded and cached — `data/osm_zmg_drive.graphml` (125,410 nodes, 304,579 edges) |
| **MTY status** | Not yet downloaded — script `src/w9_osm_download.py` will download on first run |
| **Pipeline steps** | W6 (corridor routing via Steiner approximation), W3 (transit graph construction uses stop coordinates) |
| **Key parameters** | `network_type="drive"`, `simplify=True`; output in WGS84, reprojected to EPSG:6372 for spatial ops |
| **Format** | GraphML (osmnx native); ~200-500 MB uncompressed for a metro area |
| **Adaptation** | Bounding box changes per city; all other parameters identical. Use `MTY_BBOX` from `w9_city_config.py`. |

---

### 4. INEGI CEM 3.0 — Digital Elevation Model (DEM)

| Field | Details |
|-------|---------|
| **Tier** | 1 |
| **Source URL** | https://www.inegi.org.mx/app/geo2/elevacionesmex/ |
| **ZMG status** | Available — `data/continuonacional_15m.tif` (~7.2 GB, 15m resolution); not tracked in git |
| **MTY status** | Not yet downloaded — same portal, select tiles covering NL bounding box |
| **Pipeline steps** | Phase 2 / W4 (slope_mean feature); `COALESCE(slope_mean, 0)` handles missing raster gracefully |
| **Key processing** | Zonal statistics (mean slope per AGEB polygon) via rasterio or GDAL |
| **Format** | GeoTIFF, EPSG:4326 or ITRF2008; reproject to EPSG:6372 for zonal stats |
| **Adaptation** | Download tiles covering city bounding box; processing pipeline is identical. Note: DEM is NOT used in W1-W6 core demand pipeline — only for terrain feature in NPP model. |
| **Known issue (ZMG)** | VIIRS NTL (v_ntl_median) was dropped (W0.1) due to HDF5 parsing failure; DEM zonal stats worked correctly |

---

### 5. GTFS Transit Feed

| Field | Details |
|-------|---------|
| **Tier** | 2 |
| **ZMG source** | Local file: `data/*.txt` (GTFS flat files for SITEUR/TUR network) |
| **ZMG status** | Available and used — 12,231 stops, 49,066 stop-time records, 970 trips |
| **MTY source** | Check: transmetro.monterrey.gob.mx / datos.gob.mx / transitfeeds.com/l/491-monterrey-mexico |
| **MTY status** | Unknown — availability requires verification with Metrorrey/Transmetro operator |
| **Pipeline steps** | W3 (transit accessibility graph, AGEB-stop spatial join, cumulative-opportunity measure) |
| **Key files** | `stops.txt`, `stop_times.txt`, `trips.txt`, `frequencies.txt`, `shapes.txt` |
| **Key columns** | `stops.txt`: `stop_id`, `stop_lat`, `stop_lon`; `stop_times.txt`: `trip_id`, `stop_id`, `arrival_time`, `departure_time`; `frequencies.txt`: `trip_id`, `headway_secs` |
| **Format notes** | Standard GTFS CSV; place all files in `data/` directory. Parser at `src/w3_accessibility.py` reads from `data/` — no path changes needed if same layout. |
| **Fallback if unavailable** | W3 cannot run without GTFS. W1 and W4 run without GTFS. Coverage-gap index requires GTFS; pipeline can report "all AGEBs unserved" as placeholder but W3 model retrain would be meaningless. |
| **Adaptation** | Headway columns: `frequencies.txt` uses `headway_secs`; if absent, `stop_times.txt` intervals computed per `src/w3_accessibility.py`. No structural changes needed. |

---

### 6. EOD Origin-Destination Survey

| Field | Details |
|-------|---------|
| **Tier** | 2 |
| **ZMG source** | EOD 2022 (Encuesta Origen-Destino); shapefiles inside ZIP archives |
| **ZMG status** | Available and used — 71 survey zones, 3,509 OD desire lines; stored in `raw.eod_zones`, `raw.eod_desire_lines` |
| **MTY source** | AMTU or Monterrey metropolitan planning office; CONAPO / IMPLAN NL may hold 2017 or 2022 EOD |
| **MTY status** | Unknown — EOD surveys are infrequent (5-10 year cycles); check with IMPLAN Nuevo Leon or SEDATU |
| **Pipeline steps** | W2 (gravity model calibration: beta parameter estimation via spatial join to AGEB gravity model) |
| **Key fields** | Zone polygons with `viajes_ori`, `viajes_atr` fields; desire lines with `zona_de_or`, `zona_de_de`, `total_de_v` |
| **Format notes** | ZMG used shapefiles inside ZIP archives, read via GDAL `/vsizip/` URI. Column names may differ for other city surveys. |
| **Fallback if unavailable** | W2 cannot calibrate without EOD data. Use ZMG prior `beta=2.0` (documented finding: ZMG calibration confirmed 2.0 was optimal). Apply sensitivity analysis with beta in {1.5, 2.0, 2.5} and document as a limitation. |
| **Adaptation** | Column name mapping likely required; `w2_eod_ingest.py` uses hardcoded ZMG column names — new city needs an adapter or updated column map. |

---

### 7. Local Ridership Data

| Field | Details |
|-------|---------|
| **Tier** | 3 |
| **ZMG source** | SITEUR annual ridership report (municipality-level totals); used as `v_ridership_annual` |
| **ZMG status** | Used as Vitality proxy but flagged as defective (municipality-level, not AGEB-level); **dropped from W4** (see W4 design decisions in CLAUDE.md) |
| **MTY source** | Metrorrey + Transmetro operator annual reports / INEGI ENVI survey |
| **MTY status** | Unknown — no collection attempted for W9 |
| **Pipeline steps** | Was Phase 3 / W4 Vitality indicator; now excluded from W4 CRITIC/EWM (W4 uses 14 Node+Place+People indicators only) |
| **Current role** | Informational only; may be used in W8 validation backtest if AGEB-level boarding data is available |
| **Adaptation** | If AGEB-level or stop-level ridership becomes available, it can be added back as a Vitality feature. Current pipeline does not require it. |

---

## Summary Matrix

| Data Layer | Tier | ZMG Status | MTY Status | Required for Core Pipeline |
|-----------|------|-----------|-----------|--------------------------|
| INEGI CPV2020 census | 1 | Used | Not downloaded | YES (W1, W4) |
| DENUE business registry | 1 | Used | Not downloaded | YES (W1, W4) |
| OSM street network | 1 | Cached | Not downloaded | YES (W6, W3) |
| INEGI CEM 3.0 DEM | 1 | Available | Not downloaded | Optional (terrain feature only) |
| GTFS transit feed | 2 | Used | Unknown | YES for W3; W1/W4 run without it |
| EOD OD survey | 2 | Used | Unknown | Optional (W2 calibration; use beta=2.0 prior if absent) |
| Local ridership data | 3 | Excluded from W4 | N/A | No (dropped per W4 design decision) |

---

## Minimum Dataset to Run Tier-1 Pipeline (W1, W4, W5, W6)

1. INEGI CPV2020 census CSV for the target state
2. DENUE point extract for the target municipalities
3. OSM drive network (auto-downloaded by `w9_osm_download.py`)

The Tier-1 pipeline produces: trip ends, OD demand surface, NPP prioritization scores, and corridor candidates — without any transit supply data.
