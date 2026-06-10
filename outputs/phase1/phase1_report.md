# Phase 1: Data Discovery and Acquisition Report
*Generated on: 2026-05-12 10:17:17*

## Methodology
Phase 1 focused on identifying, acquiring, and ingesting the core datasets required for the NPP-V (Node-Place-People-Vitality) model. Data was pulled from multiple sources:
1. **OpenStreetMap (OSM)**: Street network and intersections.
2. **INEGI DENUE**: Economic units and POIs.
3. **INEGI Census 2020**: Socioeconomic indicators (Marginación, Rezago Social).
4. **NASA Earthdata**: VIIRS Nighttime Lights (Vitality proxy).
5. **SITEUR/IIEG**: Official transit ridership data.

## Ingestion Summary
The following table summarizes the data successfully ingested into the `raw` database schema:

| Dataset | Record Count |
|---------|--------------|
| OSM Street Intersections | 84,868 |
| OSM Street Segments | 244,876 |
| DENUE POIs (Economic Units) | 231,113 |
| Socioeconomic Indicators (AGEB) | 4,683 |
| Transit Ridership Records | 8,850 |
| AGEB Polygons | 2,068 |

## Spatial Context
All datasets have been projected to **EPSG:6372** (Mexico ITRF2008 / LCC) to ensure geometric consistency for spatial joins and density calculations in Phase 2.

## Conclusion
Data acquisition is complete. The raw schema is fully populated with the necessary spatial and alphanumeric foundations for the predictive model.
