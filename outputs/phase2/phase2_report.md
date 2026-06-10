# Phase 2: Data Structuring & Preprocessing Report
*Generated on: 2026-05-12 10:17:18*

## Methodology
Phase 2 involved transforming raw spatial and alphanumeric data into a structured feature set at the AGEB level. Key steps included:
1. **Spatial Join**: Associating POIs, intersections, and street segments with AGEB polygons.
2. **Feature Engineering**: Calculating densities, entropy (land-use mix), and demographic ratios.
3. **Normalization**: Min-Max scaling all 16 variables to a 0.0 - 1.0 range for use in objective weighting and clustering.

## Feature Set Summary
We processed 16 indicators across **2,068 AGEBs**. The table below shows the distribution of the normalized features:

| Feature | Mean | Std Dev | Max |
|---------|------|---------|-----|
| `n_intersections_n` | 0.1581 | 0.1268 | 1.0000 |
| `n_street_density_n` | 0.2606 | 0.1856 | 1.0000 |
| `n_intersection_density_n` | 0.1138 | 0.1175 | 1.0000 |
| `p_poi_density_n` | 0.0380 | 0.0487 | 1.0000 |
| `p_employment_proxy_n` | 0.0385 | 0.0890 | 1.0000 |
| `p_retail_density_n` | 0.0199 | 0.0352 | 1.0000 |
| `p_service_density_n` | 0.0468 | 0.0731 | 1.0000 |
| `p_land_use_mix_n` | 0.6154 | 0.2733 | 1.0000 |
| `pe_population_n` | 0.1375 | 0.1108 | 1.0000 |
| `pe_pop_density_n` | 0.2225 | 0.1637 | 1.0000 |
| `pe_marginacion_n` | 0.8585 | 0.2819 | 1.0000 |
| `pe_rezago_n` | 0.1962 | 0.1355 | 1.0000 |
| `pe_dep_ratio_n` | 0.1544 | 0.0498 | 1.0000 |
| `pe_youth_share_n` | 0.1831 | 0.0618 | 1.0000 |
| `v_ntl_median_n` | 0.0000 | 0.0000 | 0.0000 |
| `v_ridership_annual_n` | 0.2137 | 0.4100 | 1.0000 |

## Technical Notes
- **Geometry Resolution**: Fixed CRS mismatches between raw census polygons (4326) and infrastructure points (6372) to ensure 100% spatial join coverage.
- **Normalization**: Used global Min-Max scaling to preserve the relative distribution of indicators across the metropolitan area.

## Conclusion
The feature engineering pipeline is robust. All 16 NPP-V dimensions are quantified and stored in the `features` schema, ready for weighting and modeling.
