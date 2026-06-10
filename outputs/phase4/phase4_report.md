# Phase 4: Unsupervised Transit Suitability Clustering
*Generated on: 2026-05-11 21:10:25*

## Methodology
In Phase 4, we applied the Phase 3 ensemble weights to the 16 normalized NPP-V features. Using Scikit-Learn's **K-Means++** algorithm, we grouped the 2,068 AGEBs in the Guadalajara Metropolitan Area (ZMG) into distinct transit suitability typologies. The optimal number of clusters ($K$) was selected by maximizing the Silhouette Score.

## Cluster Visualization

The following PCA (Principal Component Analysis) scatter plot shows how the different typologies group together in a 2D projection based on their weighted feature distances.

![PCA Clusters](cluster_pca.png)

## Typology Profiles
The table below shows the average normalized feature values for each cluster. Features closer to 1.0 indicate very high densities/values for that typology.

| Feature | Typology A | Typology B | Typology C |
|---------|---|---|---|
| `n_intersections_n` | 0.1583 | 0.2021 | 0.0570 |
| `n_street_density_n` | 0.2635 | 0.3069 | 0.1336 |
| `n_intersection_density_n` | 0.0929 | 0.2216 | 0.0221 |
| `p_poi_density_n` | 0.0291 | 0.0814 | 0.0055 |
| `p_employment_proxy_n` | 0.0279 | 0.0835 | 0.0138 |
| `p_retail_density_n` | 0.0160 | 0.0401 | 0.0024 |
| `p_service_density_n` | 0.0328 | 0.1103 | 0.0054 |
| `p_land_use_mix_n` | 0.6268 | 0.7651 | 0.1905 |
| `pe_population_n` | 0.1445 | 0.1746 | 0.0020 |
| `pe_pop_density_n` | 0.2317 | 0.2785 | 0.0268 |
| `pe_marginacion_n` | 0.9480 | 0.9454 | 0.0000 |
| `pe_rezago_n` | 0.2092 | 0.1611 | 0.1809 |
| `pe_dep_ratio_n` | 0.1603 | 0.1510 | 0.1186 |
| `pe_youth_share_n` | 0.1984 | 0.1770 | 0.0835 |
| `v_ntl_median_n` | 0.0000 | 0.0000 | 0.0000 |
| `v_ridership_annual_n` | 0.0000 | 1.0000 | 0.0000 |

## Conclusion
These typologies directly translate into targeted urban transit policies. For example, a typology with high *Place/Vitality* but low *Node* connectivity represents a "Transit Desert" ripe for immediate BRT or Light Rail expansion.
