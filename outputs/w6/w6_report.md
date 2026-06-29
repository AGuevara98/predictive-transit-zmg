# W6 New Corridor Generation -- Report

**Generated corridors:** 6 total (3 feasible, 3 infeasible)

## Methodology

1. **Anchor selection:** Jenks natural breaks (k=5) on coverage_gap_n; top class only; min 500 trips/day demand.
2. **Spatial clustering:** KMeans (k=6) on EPSG:6372 centroids to form corridor groups.
3. **Path generation:** MST-based Steiner approximation on ZMG OSM drive graph (osmnx 2.1.0).
4. **Evaluation:** W5 multi-objective function (f1 demand gain, f2 route cost, f3 equity).
5. **Mode assignment:** Light Rail/Metro if total served demand >= 75,000 trips/day; BRT if >= 15,000; Local Bus otherwise.

## Candidate Summary

| ID | Group | km | Stops | Connected | Served AGEBs | Total Demand | f1 | f3 | Score | Rank | Mode | Feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W6_G00 | 0 | 16.6 | 34 | True | 12 | 47343 | 0.412 | 0.506 | 0.650 | 1 | BRT | True |
| W6_G03 | 3 | 1.4 | 4 | True | 3 | 32386 | 0.355 | 0.579 | 0.739 | 1 | BRT | True |
| W6_G05 | 5 | 14.6 | 30 | True | 3 | 40154 | 0.423 | 0.422 | 0.657 | 1 | BRT | True |
| W6_G02 | 2 | 36.3 | 74 | True | 84 | 486581 | 0.184 | 0.575 | 0.328 | 2 | Light Rail/Metro | False |
| W6_G04 | 4 | 39.0 | 79 | True | 25 | 123515 | 0.385 | 0.486 | 0.506 | 2 | Light Rail/Metro | False |
| W6_G01 | 1 | 43.5 | 88 | True | 77 | 415674 | 0.171 | 0.531 | 0.304 | 3 | Light Rail/Metro | False |

## Mode Assignment Sensitivity

BRT threshold fixed at 15,000 trips/day; varying the Light Rail/Metro threshold:

| LRT Threshold (trips/day) | Light Rail/Metro | BRT | Local Bus |
|---|---|---|---|
| 50,000 | 0 | 3 | 0 |
| 75,000 | 0 | 3 | 0 |
| 100,000 | 0 | 3 | 0 |

Light Rail/Metro threshold fixed at 75,000 trips/day; varying the BRT threshold:

| BRT Threshold (trips/day) | Light Rail/Metro | BRT | Local Bus |
|---|---|---|---|
| 10,000 | 0 | 3 | 0 |
| 15,000 | 0 | 3 | 0 |
| 20,000 | 0 | 3 | 0 |

## W5 Config Used

```
w_demand_gain=0.50, w_efficiency=0.25, w_equity=0.25
max_detour_ratio=1.8, min_stop_spacing=300m, max_stop_spacing=1000m
min_daily_demand=500 trips/day, max_route_km=30km
```