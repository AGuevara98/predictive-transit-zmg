# W6 New Corridor Generation -- Report

**Generated corridors:** 6 total (3 feasible, 3 infeasible)

## Methodology

1. **Anchor selection:** Jenks natural breaks (k=5) on coverage_gap_n; top class only; min 500 trips/day demand.
2. **Spatial clustering:** KMeans (k=6) on EPSG:6372 centroids to form corridor groups.
3. **Path generation:** MST-based Steiner approximation on ZMG OSM drive graph (osmnx 2.1.0).
4. **Evaluation:** W5 multi-objective function (f1 demand gain, f2 route cost, f3 equity).
5. **Mode assignment:** BRT if total served demand >= 15,000 trips/day; Local Bus otherwise.

## Candidate Summary

| ID | Group | km | Stops | Connected | Served AGEBs | Total Demand | f1 | f3 | Score | Rank | Mode | Feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W6_G00 | 0 | 16.6 | 34 | True | 12 | 47809 | 0.412 | 0.506 | 0.650 | 1 | BRT | True |
| W6_G02 | 2 | 36.3 | 74 | True | 84 | 486693 | 0.184 | 0.575 | 0.328 | 1 | BRT | False |
| W6_G03 | 3 | 14.6 | 30 | True | 3 | 40028 | 0.424 | 0.422 | 0.658 | 1 | BRT | True |
| W6_G05 | 5 | 30.6 | 62 | True | 19 | 101797 | 0.431 | 0.559 | 0.571 | 1 | BRT | False |
| W6_G01 | 1 | 19.5 | 40 | True | 11 | 130622 | 0.232 | 0.329 | 0.402 | 2 | BRT | True |
| W6_G04 | 4 | 39.3 | 80 | True | 74 | 387913 | 0.165 | 0.569 | 0.308 | 2 | BRT | False |

## Mode Assignment Sensitivity

| Threshold (trips/day) | BRT corridors | Local Bus corridors |
|---|---|---|
| 10,000 | 3 | 0 |
| 15,000 | 3 | 0 |
| 20,000 | 3 | 0 |

## W5 Config Used

```
w_demand_gain=0.50, w_efficiency=0.25, w_equity=0.25
max_detour_ratio=1.8, min_stop_spacing=300m, max_stop_spacing=1000m
min_daily_demand=500 trips/day, max_route_km=30km
```