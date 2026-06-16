# W9 Transferability Report: ZMG → Monterrey

**Pipeline:** NPP-V Predictive Transit Placement  
**Source city:** ZMG — Zona Metropolitana de Guadalajara (Jalisco, CVE_ENT=14)  
**Target city:** MTY — Zona Metropolitana de Monterrey (Nuevo Leon, CVE_ENT=19)  
**Date:** 2026-06-15  
**Status:** Tier-1 infrastructure complete; waiting on Monterrey census data download for full pipeline run

---

## 1. Study Design

### Why Monterrey?

Monterrey (ZM Monterrey) was selected as the second city for three methodological reasons:

1. **Comparable metropolitan scale:** With approximately 5.3 million inhabitants across 12 municipalities (CONAPO 2020), ZM Monterrey is the second-largest metropolitan area in Mexico. ZMG has approximately 5.2 million inhabitants across 10 municipalities. The similar scale controls for network-size effects while introducing genuine structural differences.

2. **Different network maturity:** ZMG's SITEUR system is an elevated light rail with 2 lines (46 km) and a peripheral BRT corridor. Monterrey's Metrorrey system has 3 Metro lines (~35 km) plus the Transmetro BRT network. Monterrey has a more developed rail base, but also higher car-ownership rates and a more dispersed urban form driven by industrial suburbanization. This tests whether the pipeline correctly identifies coverage gaps even in a more transit-mature context.

3. **Data availability parity:** Both cities have INEGI CPV2020 census microdata (Tier-1), DENUE (Tier-1), OSM coverage (Tier-1), and are likely to have GTFS feeds (Tier-2). The EOD survey (Tier-2) status is uncertain for Monterrey but the ZMG finding (beta=2.0 is the calibrated optimum) supports using the same prior without re-calibration.

### Research Questions

- **RQ1 (Model transfer):** Do the ZMG-calibrated parameters (gravity beta=2.0, NPP weights from CRITIC/EWM, equity alpha=0.20) produce plausible demand and prioritization surfaces for Monterrey without city-specific recalibration?
- **RQ2 (Gap identification):** Are the identified coverage-gap AGEBs in Monterrey spatially consistent with known underserved areas (informal settlements in Santa Catarina, Garcia, Santiago)?
- **RQ3 (Corridor generation):** Do the W6 corridor candidates for Monterrey align with announced or planned expansions (e.g., proposed Metrorrey Line 4 corridor)?
- **RQ4 (Transfer error):** How much does transfer of ZMG-calibrated parameters degrade pipeline outputs relative to local calibration?

---

## 2. Data Availability Matrix

| Data Layer | Tier | ZMG Status | MTY Status | Notes |
|-----------|------|-----------|-----------|-------|
| INEGI CPV2020 census | 1 | Used (CVE_ENT=14) | Not yet downloaded (CVE_ENT=19) | Schema identical; download URL documented |
| DENUE business registry | 1 | Used (ZMG extract) | Not yet downloaded | National standard; NL state extract needed |
| OSM street network | 1 | Cached (125k nodes) | Script ready (`w9_osm_download.py`) | Auto-download on first run |
| INEGI CEM 3.0 DEM | 1 | Available (7.2 GB) | Not downloaded | Optional; pipeline degrades gracefully without it |
| GTFS transit feed | 2 | Used (SITEUR) | Availability unconfirmed | Check transmetro.monterrey.gob.mx |
| EOD OD survey | 2 | Used (EOD 2022) | Unknown | IMPLAN NL may hold 2017 or 2022 EOD |
| Ridership data | 3 | Excluded from W4 | Not applicable | Dropped per W4 design decision |

**Minimum Tier-1 run:** CPV2020 + DENUE + OSM (auto-downloaded). W1, W4, W5, W6 core logic.  
**Full Tier-2 run:** Adds GTFS (W3 coverage gap) and optionally EOD (W2 gravity calibration).

---

## 3. Expected Transfer Error Sources

### 3.1 Parameter Transfer (Beta = 2.0)

The gravity model uses power-law decay `f(d) = d^(-beta)` with `beta=2.0`. ZMG calibration (W2) confirmed this is the optimal value at zone level (calibrated optimum hit the search boundary at beta=5.0 with worse RMSE). However, ZMG and Monterrey have different urban forms:

- ZMG: Guadalajara's historic grid spreads radially; trip distances are moderate
- MTY: Monterrey has a more dispersed polycentric form driven by industrial corridors (Apodaca, Santa Catarina)

**Expected effect:** Monterrey's larger spatial extent may benefit from a slightly lower beta (shallower decay, more long-distance trips). The transfer error from using beta=2.0 is expected to be moderate. Sensitivity analysis with beta in {1.5, 2.0, 2.5} is recommended.

### 3.2 CRITIC/EWM Weights (NPP Prioritization)

The 14 NPP indicator weights were estimated from ZMG AGEB variance and correlation structure using CRITIC/EWM. These weights will be applied directly to Monterrey as a first-order transfer.

**Expected effect:** Monterrey's weight distribution may differ if:
- Industrial areas have higher employment proxy variance (Apodaca, Cadereyta auto plants)
- Street network density varies differently from ZMG due to US-style grid vs. Spanish grid
- Marginalization / rezago distribution differs from Jalisco

**Mitigation:** Re-run CRITIC/EWM on Monterrey feature matrix after feature engineering; compare weight vectors. Report cosine similarity between ZMG and MTY weight vectors as a transfer quality metric.

### 3.3 Coverage-Gap Threshold (High-gap Definition)

ZMG defined high-gap as: `demand_quintile >= 4 AND access_quintile <= 2`. This produced 428 High-gap AGEBs (20.7% of 2,068).

**Expected effect:** If Monterrey has better transit coverage (3 Metro lines vs 2 in ZMG), the proportion of High-gap AGEBs may be lower. If the Metrorrey network is concentrated in the urban core and misses periphery (Garcia, Juarez, Santiago), high-gap rate may be similar or higher.

### 3.4 Trip Generation Formula

The formula `2.5 trips/person/day × population × (1 + 0.10 × youth_share)` is based on INEGI MOTIV 2017 for ZMG. Monterrey's INEGI ENVI or MOTIV data may indicate a slightly different trip rate.

**Expected effect:** Small bias in absolute trip volumes; negligible effect on relative prioritization (the gravity model normalizes via doubly-constrained balancing).

### 3.5 DENUE Coverage Differences

DENUE point data coverage quality varies by state and year. Monterrey's economic geography is dominated by large industrial establishments (lower POI density in factory zones) and large commercial centers (Monterrey Norte / San Pedro concentrations). This may shift the attraction surface relative to ZMG.

---

## 4. Results (Placeholders — to be filled after pipeline run)

### 4.1 ZMG vs MTY Baseline Statistics

| Metric | ZMG (reference) | MTY (target) | Delta |
|--------|----------------|--------------|-------|
| Number of AGEBs | 2,068 | _TBD_ | _TBD_ |
| Number of municipalities | 10 | 12 | +2 |
| Mean transit propensity | 0.423 | _TBD_ | _TBD_ |
| Mean vehicle rate | 0.577 | _TBD_ | _TBD_ |
| Total modeled trip ends | _ZMG value_ | _TBD_ | _TBD_ |
| AGEBs with GTFS coverage | 1,397 (67.6%) | _TBD_ | _TBD_ |
| High-gap AGEBs | 428 (20.7%) | _TBD_ | _TBD_ |
| Feasible BRT corridors (W6) | 2 (W6_G02, W6_G05) | _TBD_ | _TBD_ |

### 4.2 NPP Weight Transfer Quality

| Feature | ZMG weight | MTY weight | Difference |
|---------|-----------|-----------|-----------|
| pe_population_n | 0.1186 | _TBD_ | _TBD_ |
| p_employment_proxy_n | 0.1063 | _TBD_ | _TBD_ |
| pe_rezago_n | 0.1052 | _TBD_ | _TBD_ |
| ... (14 features) | ... | _TBD_ | _TBD_ |
| **Cosine similarity** | 1.000 | _TBD_ | _TBD_ |

### 4.3 Gravity Model Transfer

| Parameter | ZMG | MTY |
|-----------|-----|-----|
| Beta (decay exponent) | 2.0 (calibrated) | 2.0 (transferred) |
| W2 calibration available | Yes (EOD 2022) | Unknown |
| Mean OD distance (m) | _ZMG value_ | _TBD_ |
| Furness IPF iterations | ~50-100 | _TBD_ |

### 4.4 Corridor Generation Results

| Corridor ID | Length (km) | Mode | Total score | Pareto rank |
|------------|------------|------|------------|-------------|
| _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

### 4.5 Validation Against Known Network Expansions

_To be completed after pipeline run. Compare W6 corridor candidates against:_
- _Proposed Metrorrey Line 4 alignment (if published)_
- _Mi Macro Monterrey BRT announcements_
- _IMPLAN NL mobility plan corridors_

---

## 5. Limitations

### 5.1 No Local Calibration Data Yet

The W9 run uses all parameters transferred from ZMG without city-specific calibration. Transfer error is documented but not quantified until:
- Monterrey EOD survey data is obtained (W2 equivalent)
- Local ridership data allows backtest validation (W8 equivalent)

### 5.2 Proxy Centroids in Tier-1 Run

The `w9_run_tier1.py` script uses random proxy centroids when no spatial database connection is available. This produces a gravity model OD matrix with unrealistic distance structure. For a valid W1 run, AGEB polygon centroids from the INEGI Marco Geoestadistico shapefile must be loaded.

**Mitigation:** Load Monterrey AGEB shapefile to PostGIS (`base.ageb_mty`) and connect `w9_run_tier1.py` to the database for centroid extraction — mirroring the ZMG W1 approach.

### 5.3 Vehicle Ownership Differences

Monterrey has historically higher car ownership rates than Guadalajara (attributed to proximity to US border, NAFTA-era industrial suburbanization, and historically lower public transit quality). This will lower mean transit propensity and reduce the modeled transit demand surface. The pipeline handles this correctly through the `transit_propensity = 1 - vehicle_rate` formula, but the absolute transit demand numbers should be interpreted relative to city context.

### 5.4 OSM Coverage Gaps in Periphery

ZM Monterrey's peripheral municipalities (Santiago, Salinas Victoria) have lower OSM coverage than the urban core. The W6 corridor generator relies on the OSM drive graph for path finding; missing roads will cause corridors to detour through available nodes. This may produce longer or less direct routes in peripheral zones.

### 5.5 GTFS Availability Uncertain

As of the writing of this report, Monterrey GTFS feed availability has not been confirmed. Without GTFS, W3 (coverage-gap index) cannot run. The pipeline will produce Tier-1 outputs (W1 demand + W4 prioritization + W6 corridors) but cannot generate the coverage-gap-based dependent variable used for model training in W3. Thesis should explicitly document this as a transfer limitation if GTFS remains unavailable.

---

## 6. Next Steps

1. **Download data:** INEGI CPV2020 NL (ZIP URL in `w9_city_config.py`), DENUE NL extract, GTFS if available
2. **Run OSM download:** `python src/w9_osm_download.py`
3. **Run Tier-1 pipeline:** `python src/w9_run_tier1.py` (after census download)
4. **Load AGEB shapefile:** PostGIS ingest of NL Marco Geoestadistico for real centroids
5. **Run feature engineering:** Adapt W4 for MTY schema
6. **Run W3 (if GTFS available):** Coverage-gap index for Monterrey
7. **Run W6:** Corridor generation for Monterrey
8. **Fill results tables** in Section 4 above
9. **Write comparison analysis:** ZMG vs MTY weight vectors, corridor alignment, transfer error quantification
