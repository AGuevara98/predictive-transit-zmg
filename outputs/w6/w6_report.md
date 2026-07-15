# W6 New Corridor Generation -- Report

**Generated corridors:** 6 total (0 feasible, 6 infeasible)

## Methodology

1. **Anchor selection:** Jenks natural breaks (k=5) on coverage_gap_n; top class only; min 500 trips/day demand.
2. **Spatial clustering:** KMeans (k=6) on EPSG:6372 centroids to form corridor groups.
3. **Path generation:** MST-based Steiner approximation on ZMG OSM drive graph (osmnx 2.1.0).
4. **Evaluation:** W5 multi-objective function (f1 demand gain, f2 route cost, f3 equity).
5. **Mode assignment:** Light Rail/Metro if total served demand >= 75,000 trips/day; BRT if >= 15,000; Local Bus otherwise.

## Candidate Summary

| ID | Group | km | Stops | Connected | Served AGEBs | Total Demand | f1 | f3 | Score | Rank | Mode | Feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W6_G00 | 0 | 24.9 | 51 | True | 18 | 59220 | 0.391 | 0.274 | 0.503 | 1 | BRT | False |
| W6_G03 | 3 | 3.5 | 8 | True | 3 | 32386 | 0.355 | 0.321 | 0.656 | 1 | BRT | False |
| W6_G05 | 5 | 21.3 | 44 | True | 4 | 40614 | 0.422 | 0.247 | 0.556 | 1 | BRT | False |
| W6_G02 | 2 | 36.6 | 74 | True | 84 | 487683 | 0.183 | 0.284 | 0.254 | 2 | Light Rail/Metro | False |
| W6_G04 | 4 | 44.5 | 90 | True | 28 | 148616 | 0.345 | 0.300 | 0.420 | 2 | Light Rail/Metro | False |
| W6_G01 | 1 | 46.9 | 95 | True | 89 | 410816 | 0.177 | 0.229 | 0.234 | 3 | Light Rail/Metro | False |

## Mode Assignment Sensitivity

BRT threshold fixed at 15,000 trips/day; varying the Light Rail/Metro threshold:

| LRT Threshold (trips/day) | Light Rail/Metro | BRT | Local Bus |
|---|---|---|---|
| 50,000 | 0 | 0 | 0 |
| 75,000 | 0 | 0 | 0 |
| 100,000 | 0 | 0 | 0 |

Light Rail/Metro threshold fixed at 75,000 trips/day; varying the BRT threshold:

| BRT Threshold (trips/day) | Light Rail/Metro | BRT | Local Bus |
|---|---|---|---|
| 10,000 | 0 | 0 | 0 |
| 15,000 | 0 | 0 | 0 |
| 20,000 | 0 | 0 | 0 |

## W5 Config Used

```
w_demand_gain=0.50, w_efficiency=0.25, w_equity=0.25
max_detour_ratio=1.8, min_stop_spacing=300m, max_stop_spacing=1000m
min_daily_demand=500 trips/day, max_route_km=30km
```