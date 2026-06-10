# Phase 5: Predictive Modeling & Interpretability Report

This report summarizes the performance of the predictive models trained to classify the Phase 4 transit suitability typologies.

## 1. Model Evaluation Metrics

The models were evaluated using 5-Fold Cross-Validation. The target variable is the transit suitability typology. Metrics represent the mean across all 5 folds.

| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 |
|-------|----------|-----------------|--------------|----------|
| RandomForest | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| XGBoost | 0.9990 | 0.9995 | 0.9966 | 0.9980 |

## 2. SHAP Feature Importance (XGBoost)

The following table presents the top 10 driving features identified by XGBoost's SHAP values, compared against the objective weights assigned in Phase 3.

| Feature | Total SHAP | Typology A | Typology B | Typology C | Phase 3 Weight |
|---|---|---|---|---|---|
| `v_ridership_annual_n` | **6.3018** | 2.3785 | 3.8819 | 0.0414 | 0.0000 |
| `pe_marginacion_n` | **4.0082** | 1.4264 | 0.0000 | 2.5818 | 0.0000 |
| `pe_population_n` | **1.2996** | 0.3650 | 0.0000 | 0.9346 | 0.0000 |
| `pe_youth_share_n` | **0.6105** | 0.3780 | 0.0000 | 0.2325 | 0.0000 |
| `n_intersection_density_n` | **0.3154** | 0.0239 | 0.1302 | 0.1613 | 0.0000 |
| `p_poi_density_n` | **0.1591** | 0.0396 | 0.0636 | 0.0559 | 0.0000 |
| `pe_dep_ratio_n` | **0.1250** | 0.1250 | 0.0000 | 0.0000 | 0.0000 |
| `pe_rezago_n` | **0.0485** | 0.0063 | 0.0000 | 0.0422 | 0.0000 |
| `p_employment_proxy_n` | **0.0427** | 0.0000 | 0.0200 | 0.0228 | 0.0000 |
| `pe_pop_density_n` | **0.0204** | 0.0000 | 0.0000 | 0.0204 | 0.0000 |

## 3. Typology Drivers

### Typology A
The primary predictive drivers for **Typology A** are:
- `v_ridership_annual_n` (SHAP magnitude: 2.3785)
- `pe_marginacion_n` (SHAP magnitude: 1.4264)
- `pe_youth_share_n` (SHAP magnitude: 0.3780)

### Typology B
The primary predictive drivers for **Typology B** are:
- `v_ridership_annual_n` (SHAP magnitude: 3.8819)
- `n_intersection_density_n` (SHAP magnitude: 0.1302)
- `p_poi_density_n` (SHAP magnitude: 0.0636)

### Typology C
The primary predictive drivers for **Typology C** are:
- `pe_marginacion_n` (SHAP magnitude: 2.5818)
- `pe_population_n` (SHAP magnitude: 0.9346)
- `pe_youth_share_n` (SHAP magnitude: 0.2325)

## 4. Visualizations

- [XGBoost SHAP Summary](shap_summary_XGBoost.png)
- [Random Forest SHAP Summary](shap_summary_RandomForest.png)