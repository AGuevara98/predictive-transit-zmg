# W2 Gravity Model Calibration Report

## Summary

| Metric | Value |
|--------|-------|
| W1 prior beta | 2.0 |
| Calibrated beta | 1.1851 |
| Delta (|cal - prior|) | 0.8149 |
| Zone-pair calibration pairs | 1987 |
| Log-space SSE at calibrated beta | 4011.4389 |
| RMSE (scaled, calibrated) | 4,590.0 trips |
| RMSE (scaled, W1 beta=2.0) | 5,215.2 trips |
| R² (calibrated) | 0.2299 |

## Verdict

The calibrated beta (1.1851) differs from the W1 prior (2.0) by 0.81. This indicates ZMG commuters travel longer distances (weaker distance decay) than the W1 prior assumed. Consider rerunning W1.2 with `BETA = 1.19` in `src/w1_gravity_model.py` for a calibrated demand surface, then rerunning W3 and downstream workstreams. The relative prioritization ordering (W4/W6/W7) is robust to this change since it depends on demand ratios, not absolute values.

## Data Sources

- **EOD 2022 zones:** 71 survey zones from `Zonificacion de la Encuesta Origen-Destino.zip`
- **Observed desire lines:** 3509 zone OD pairs from the two desire-line zips
  (range 5,000-47,555 trips per pair; only pairs >= 100 trips used for fitting)
- **Modeled OD:** `features.ageb_od_matrix` (W1 doubly-constrained gravity, Euclidean distances)

## Methodology

1. **Zone-AGEB spatial join** (W2.2): Each AGEB centroid was assigned to the EOD survey zone
   containing it. AGEB-level modeled flows were summed to zone level (`T_zone(i,j) = sum T_ageb`).

2. **Beta fitting** (W2.3): `scipy.optimize.minimize_scalar` (bounded Brent method) minimised
   the sum of squared log-errors across zone OD pairs:

   `min_beta sum[ log(T_ij_model_scaled(beta)) - log(T_ij_observed) ]^2`

   The log-space objective treats proportional errors equally across low- and high-flow pairs.
   The unconstrained gravity formula `T_ij = P_i x d_ij^(-beta) x A_j` was used at zone level
   (Furness IPF balancing is omitted at zone level due to partial zone-pair coverage). Before
   computing log-errors, **T_ij_model is rescaled so that sum(T_model) == sum(T_observed)**.
   This normalization is essential: the raw unconstrained model produces flows 10^5 larger than
   observed zone OD pairs (because AGEB-level productions are absolute trip volumes, not
   normalized to match zone-pair counts). Without this step the optimizer sees a constant
   ~12 log-unit level offset and drives beta to the search boundary regardless of shape fit.
   The scaling isolates the SHAPE of the distance decay (which is what beta controls) from
   the LEVEL (which is handled by the doubly-constrained Furness balancing in W1).
   Both scaled modeled and observed flows are also used for RMSE and R² computation.

3. **Distance metric:** Mean Euclidean centroid-to-centroid distance (metres, EPSG:6372) across
   all AGEB pairs in each zone pair. This is the same metric used in W1.

## Caveats and Limitations

- **Resolution mismatch:** EOD zones are survey aggregations containing 10-50 AGEBs each.
  Zone-level modeled flows are sums of AGEB-level flows, not a zone-native gravity model.
  This aggregation bias means the calibrated beta may absorb zone-size effects. A proper
  calibration would rerun Furness IPF at zone resolution (feasible once zone trip ends
  are confirmed from the tabular EOD files).

- **Euclidean proxy:** W1 and W2 both use Euclidean (straight-line) distances. EOD surveys
  record actual travel times. If network travel time data becomes available (e.g. OSRM or
  osmnx routing), the calibration should be repeated with time-based impedance.

- **Total trips (all modes):** Observed desire-line flows include all motorised modes (transit,
  car, taxi, etc.). This is correct because the gravity model distributes total person trips;
  W1.3 then applies zone-level transit propensity weights derived from vehicle ownership.

- **Desire-line threshold:** Only zone pairs with >= 100 observed trips are used
  for fitting. Low-flow pairs are excluded because their log-errors are dominated by noise
  relative to the structural distance-decay signal.

## Comparison CSV

`outputs/w2/zone_od_comparison.csv` contains one row per calibration pair with columns:
`origin_zone`, `dest_zone`, `dist_km`, `observed_flow`,
`modeled_flow_beta20`, `modeled_flow_calibrated`.
