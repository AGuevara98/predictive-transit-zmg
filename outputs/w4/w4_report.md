# W4 NPP Prioritization Layer Report
*Generated: 2026-06-20 18:08:56*

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
| p_employment_proxy_n     | PLACE       |       0.131041  |    0.188889  |         0.159965  |
| p_service_density_n      | PLACE       |       0.0957538 |    0.187614  |         0.141684  |
| n_intersection_density_n | NODE        |       0.0889276 |    0.0992846 |         0.0941061 |
| pe_rezago_n              | PEOPLE      |       0.0724768 |    0.113163  |         0.0928197 |
| p_land_use_mix_n         | PLACE       |       0.0891248 |    0.0774534 |         0.0832891 |
| pe_marginacion_n         | PEOPLE      |       0.0955363 |    0.04734   |         0.0714382 |
| p_retail_density_n       | PLACE       |       0.0597552 |    0.0688071 |         0.0642811 |
| n_intersections_n        | NODE        |       0.0752273 |    0.0385473 |         0.0568873 |
| p_poi_density_n          | PLACE       |       0.0613515 |    0.0485361 |         0.0549438 |
| n_street_density_n       | NODE        |       0.0740222 |    0.0262102 |         0.0501162 |
| pe_population_n          | PEOPLE      |       0.0528237 |    0.0217609 |         0.0372923 |
| pe_pop_density_n         | PEOPLE      |       0.0528959 |    0.0135969 |         0.0332464 |
| pe_youth_share_n         | PEOPLE      |       0.0259011 |    0.037952  |         0.0319266 |
| pe_dep_ratio_n           | PEOPLE      |       0.0251623 |    0.030846  |         0.0280042 |

## Score Summary (1,881 AGEBs)

| Metric | npp_score | equity_score | final_score |
|---|---|---|---|
| Mean | 0.4942 | 0.5275 | 0.5009 |
| Std  | 0.1592 | 0.1565 | 0.1481 |
| Min  | 0.0000 | 0.0000 | 0.0000 |
| Max  | 0.7276 | 0.8707 | 0.7021 |

Priority quintile 5 (highest priority): **376 AGEBs**
Priority quintile 1 (lowest priority): **377 AGEBs**

## Top 10 Highest-Priority AGEBs

|      cve_ageb |   npp_score |   equity_score |   final_score |   priority_rank |   priority_quintile |
|--------------:|------------:|---------------:|--------------:|----------------:|--------------------:|
| 1403900011626 |    0.727626 |       0.599866 |      0.702074 |               1 |                   5 |
| 1403900011344 |    0.717628 |       0.628353 |      0.699773 |               2 |                   5 |
| 1403900011310 |    0.721841 |       0.589387 |      0.69535  |               3 |                   5 |
| 1403900011359 |    0.707476 |       0.646195 |      0.69522  |               4 |                   5 |
| 1403900011630 |    0.693503 |       0.673603 |      0.689523 |               5 |                   5 |
| 1403900014546 |    0.708924 |       0.607538 |      0.688647 |               6 |                   5 |
| 1403900011325 |    0.714893 |       0.582478 |      0.68841  |               7 |                   5 |
| 1403900011132 |    0.704062 |       0.611945 |      0.685639 |               8 |                   5 |
| 1403900014550 |    0.70668  |       0.600428 |      0.68543  |               9 |                   5 |
| 1403900010929 |    0.718723 |       0.539425 |      0.682863 |              10 |                   5 |

## Equity Sensitivity (Spearman rank correlation vs alpha=0.20 baseline)

| alpha | Spearman rho |
|---|---|
| 0.1 | 0.9979 |
| 0.2 | 1.0000 |
| 0.3 | 0.9967 |

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
