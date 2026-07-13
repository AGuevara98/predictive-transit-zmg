# W4 NPP Prioritization Layer Report
*Generated: 2026-07-12 16:33:04*

## Methodology

W4 repositions the NPP-V indicator set as a multi-criteria place-characteristics
prioritization index, decoupled from demand estimation. The Vitality dimension
(`v_ridership_annual_n`) is excluded because it is a municipality-level proxy with
no AGEB-level discrimination. Demand lives in W1/W3.

**Score formula:**
- `npp_score = sum(feature_i * ensemble_weight_i)` over 14 NODE+PLACE+PEOPLE features
- `equity_score = mean(pe_marginacion_n, pe_rezago_n)`
- `final_score = 0.80 * npp_score + 0.20 * equity_score`

CRITIC and EWM weights are computed independently and averaged (ensemble).

## Feature Weights (14 features)

| feature                  | dimension   |   critic_weight |   ewm_weight |   ensemble_weight |
|:-------------------------|:------------|----------------:|-------------:|------------------:|
| p_employment_proxy_n     | PLACE       |       0.133654  |    0.192258  |         0.162956  |
| p_service_density_n      | PLACE       |       0.100004  |    0.190961  |         0.145482  |
| n_intersection_density_n | NODE        |       0.09271   |    0.101056  |         0.0968828 |
| p_land_use_mix_n         | PLACE       |       0.0929197 |    0.078835  |         0.0858773 |
| pe_rezago_n              | PEOPLE      |       0.0703917 |    0.0940689 |         0.0822303 |
| p_retail_density_n       | PLACE       |       0.0620848 |    0.0700344 |         0.0660596 |
| n_intersections_n        | NODE        |       0.0777894 |    0.0392349 |         0.0585122 |
| pe_marginacion_n         | PEOPLE      |       0.0634947 |    0.0514591 |         0.0574769 |
| p_poi_density_n          | PLACE       |       0.0638204 |    0.0494018 |         0.0566111 |
| n_street_density_n       | NODE        |       0.0749018 |    0.0266777 |         0.0507898 |
| pe_population_n          | PEOPLE      |       0.0598439 |    0.0221491 |         0.0409965 |
| pe_pop_density_n         | PEOPLE      |       0.0575198 |    0.0138394 |         0.0356796 |
| pe_youth_share_n         | PEOPLE      |       0.0263539 |    0.038629  |         0.0324914 |
| pe_dep_ratio_n           | PEOPLE      |       0.0245126 |    0.0313962 |         0.0279544 |

## Score Summary (1,881 AGEBs)

| Metric | npp_score | equity_score | final_score |
|---|---|---|---|
| Mean | 0.4595 | 0.2274 | 0.4131 |
| Std  | 0.1502 | 0.1121 | 0.1217 |
| Min  | 0.0295 | 0.0000 | 0.0520 |
| Max  | 0.6861 | 0.8611 | 0.5926 |

Priority quintile 5 (highest priority): **376 AGEBs**
Priority quintile 1 (lowest priority): **377 AGEBs**

## Top 10 Highest-Priority AGEBs

|      cve_ageb |   npp_score |   equity_score |   final_score |   priority_rank |   priority_quintile |
|--------------:|------------:|---------------:|--------------:|----------------:|--------------------:|
| 1403900011359 |    0.667861 |       0.291614 |      0.592611 |               1 |                   5 |
| 1403900011626 |    0.686131 |       0.214247 |      0.591754 |               2 |                   5 |
| 1403900011344 |    0.675904 |       0.245029 |      0.589729 |               3 |                   5 |
| 1403900011630 |    0.654092 |       0.331605 |      0.589594 |               4 |                   5 |
| 1409800011063 |    0.645558 |       0.340377 |      0.584522 |               5 |                   5 |
| 1403900014546 |    0.667328 |       0.225836 |      0.579029 |               6 |                   5 |
| 1409708221954 |    0.62296  |       0.402449 |      0.578858 |               7 |                   5 |
| 1403900011325 |    0.673307 |       0.189852 |      0.576616 |               8 |                   5 |
| 1412000010617 |    0.615379 |       0.404825 |      0.573269 |               9 |                   5 |
| 1403900010863 |    0.650678 |       0.257771 |      0.572097 |              10 |                   5 |

## Equity Sensitivity (Spearman rank correlation vs alpha=0.20 baseline)

| alpha | Spearman rho |
|---|---|
| 0.1 | 0.9901 |
| 0.2 | 1.0000 |
| 0.3 | 0.9840 |

A rho close to 1.0 indicates that changing alpha has little effect on the
priority ranking.

## Methodological Note

`pe_marginacion_n` and `pe_rezago_n` contribute to both `npp_score` (via CRITIC/EWM)
and `equity_score`. This mild double-count slightly amplifies their influence on
`final_score`. If this becomes overinfluential, the equity_score operationalization
can be changed to use other equity indicators.

## Outputs

- `features.nppv_w4_weights` -- 14 feature weights (DB)
- `features.nppv_prioritization` -- 2,068 AGEB scores + ranks (DB)
- `outputs/w4/nppv_w4_weights.csv`
- `outputs/w4/nppv_prioritization.csv`
- `outputs/w4/nppv_prioritization.geojson` (QGIS-ready, EPSG:4326)
- `outputs/w4/nppv_w4_weights_bar.png`
- `outputs/w4/nppv_score_vs_equity.png`
- `outputs/w4/cluster_priority_profiles.csv`
- `outputs/w4/w4_report.md`
