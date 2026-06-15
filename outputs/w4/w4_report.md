# W4 NPP Prioritization Layer Report
*Generated: 2026-06-15 14:04:00*

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
| p_employment_proxy_n     | PLACE       |       0.109934  |    0.152008  |         0.130971  |
| p_service_density_n      | PLACE       |       0.0810962 |    0.150822  |         0.115959  |
| n_intersection_density_n | NODE        |       0.0945333 |    0.136616  |         0.115575  |
| n_street_density_n       | NODE        |       0.13113   |    0.0905759 |         0.110853  |
| n_intersections_n        | NODE        |       0.105381  |    0.0984559 |         0.101918  |
| pe_rezago_n              | PEOPLE      |       0.0660174 |    0.0929592 |         0.0794883 |
| p_land_use_mix_n         | PLACE       |       0.0776023 |    0.0616881 |         0.0696452 |
| pe_marginacion_n         | PEOPLE      |       0.0862481 |    0.0381587 |         0.0622034 |
| p_retail_density_n       | PLACE       |       0.0536831 |    0.0558086 |         0.0547458 |
| p_poi_density_n          | PLACE       |       0.0542032 |    0.038877  |         0.0465401 |
| pe_population_n          | PEOPLE      |       0.047959  |    0.017295  |         0.032627  |
| pe_pop_density_n         | PEOPLE      |       0.0474933 |    0.0107507 |         0.029122  |
| pe_youth_share_n         | PEOPLE      |       0.0230422 |    0.0310875 |         0.0270648 |
| pe_dep_ratio_n           | PEOPLE      |       0.0216773 |    0.0248974 |         0.0232874 |

## Score Summary (2,068 AGEBs)

| Metric | npp_score | equity_score | final_score |
|---|---|---|---|
| Mean | 0.5001 | 0.5274 | 0.5056 |
| Std  | 0.1823 | 0.1564 | 0.1631 |
| Min  | 0.0000 | 0.0000 | 0.0000 |
| Max  | 0.7461 | 0.8705 | 0.7168 |

Priority quintile 5 (highest priority): **414 AGEBs**
Priority quintile 1 (lowest priority): **414 AGEBs**

## Top 10 Highest-Priority AGEBs

|      cve_ageb |   npp_score |   equity_score |   final_score |   priority_rank |   priority_quintile |
|--------------:|------------:|---------------:|--------------:|----------------:|--------------------:|
| 1403900011626 |    0.746121 |       0.599645 |      0.716825 |               1 |                   5 |
| 1403900011630 |    0.725749 |       0.673386 |      0.715276 |               2 |                   5 |
| 1403900011344 |    0.735684 |       0.628133 |      0.714174 |               3 |                   5 |
| 1403900011359 |    0.722396 |       0.645977 |      0.707112 |               4 |                   5 |
| 1403900011310 |    0.734143 |       0.589163 |      0.705147 |               5 |                   5 |
| 1403900011132 |    0.725841 |       0.611722 |      0.703017 |               6 |                   5 |
| 1403900014546 |    0.726884 |       0.607318 |      0.702971 |               7 |                   5 |
| 1403900011325 |    0.732755 |       0.582257 |      0.702656 |               8 |                   5 |
| 1403900014550 |    0.726431 |       0.600207 |      0.701186 |               9 |                   5 |
| 1403900010929 |    0.738428 |       0.539201 |      0.698583 |              10 |                   5 |

## Equity Sensitivity (Spearman rank correlation vs alpha=0.20 baseline)

| alpha | Spearman rho |
|---|---|
| 0.1 | 0.9979 |
| 0.2 | 1.0000 |
| 0.3 | 0.9972 |

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
