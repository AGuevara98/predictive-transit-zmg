# W6 New Corridor Generation -- Report

**Generated corridors:** 6 total (2 feasible, 4 infeasible)

## Methodology

1. **Anchor selection:** Jenks natural breaks (k=5) on coverage_gap_n; top class only; min 500 trips/day demand.
2. **Spatial clustering:** KMeans (k=6) on EPSG:6372 centroids to form corridor groups.
3. **Path generation:** MST-based Steiner approximation on ZMG OSM drive graph (osmnx 2.1.0).
4. **Evaluation:** W5 multi-objective function (f1 demand gain, f2 route cost, f3 equity).
5. **Mode assignment:** BRT if total served demand >= 15,000 trips/day; Local Bus otherwise.

## Candidate Summary

| ID | Group | km | Stops | Connected | Served AGEBs | Total Demand | f1 | f3 | Score | Rank | Mode | Feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W6_G00 | 0 | 65.5 | 132 | True | 90 | 519763 | 0.173 | 0.576 | 0.317 | 1 | BRT | False |
| W6_G02 | 2 | 13.2 | 27 | True | 3 | 40260 | 0.424 | 0.422 | 0.669 | 1 | BRT | True |
| W6_G03 | 3 | 32.3 | 66 | True | 27 | 188842 | 0.210 | 0.476 | 0.329 | 1 | BRT | False |
| W6_G04 | 4 | 50.0 | 101 | True | 63 | 305191 | 0.178 | 0.547 | 0.315 | 1 | BRT | False |
| W6_G05 | 5 | 16.4 | 34 | True | 15 | 47816 | 0.412 | 0.450 | 0.638 | 1 | BRT | True |
| W6_G01 | 1 | 51.7 | 104 | True | 26 | 110474 | 0.376 | 0.441 | 0.487 | 2 | BRT | False |

## Mode Assignment Sensitivity

| Threshold (trips/day) | BRT corridors | Local Bus corridors |
|---|---|---|
| 10,000 | 2 | 0 |
| 15,000 | 2 | 0 |
| 20,000 | 2 | 0 |

## W5 Config Used

```
w_demand_gain=0.50, w_efficiency=0.25, w_equity=0.25
max_detour_ratio=1.8, min_stop_spacing=300m, max_stop_spacing=1000m
min_daily_demand=500 trips/day, max_route_km=30km
```