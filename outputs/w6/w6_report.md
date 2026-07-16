# W6 New Corridor Generation -- Report

**Generated corridors:** 5 total (4 feasible, 1 infeasible)

## Methodology

1. **Anchor selection (frontier):** Jenks top-class coverage_gap_n anchors (min 500 trips/day) restricted to within 400m of a network-connected AGEB (the served/unserved seam).
2. **Spatial clustering:** KMeans (k=6) on EPSG:6372 centroids to form corridor groups.
3. **Path generation:** MST-diameter trunk (longest leaf-to-leaf path) per cluster on the ZMG OSM drive graph -- one road-following alignment, no phantom jumps.
4. **Evaluation:** W5 multi-objective function (f1 demand gain, f2 route cost, f3 equity); feasibility gated on ANCHOR-DIRECTNESS (route_km / straight-line anchor span, cap 1.8).
5. **Mode assignment:** Light Rail/Metro if total served demand >= 75,000 trips/day; BRT if >= 15,000; Local Bus otherwise.

## Candidate Summary

| ID | Group | km | Stops | Connected | Served AGEBs | Total Demand | f1 | f3 | Score | Rank | Mode | Feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W6_G03 | 3 | 2.4 | 6 | True | 5 | 35784 | 0.357 | 0.349 | 0.674 | 1 | BRT | True |
| W6_G00 | 0 | 7.3 | 16 | True | 18 | 66041 | 0.301 | 0.338 | 0.574 | 2 | BRT | True |
| W6_G01 | 1 | 23.0 | 47 | True | 27 | 96839 | 0.270 | 0.347 | 0.415 | 2 | Light Rail/Metro | True |
| W6_G05 | 5 | 5.4 | 12 | True | 14 | 80234 | 0.125 | 0.271 | 0.397 | 2 | Light Rail/Metro | False |
| W6_G02 | 2 | 12.1 | 25 | True | 25 | 192357 | 0.164 | 0.265 | 0.380 | 3 | Light Rail/Metro | True |

## Mode Assignment Sensitivity

BRT threshold fixed at 15,000 trips/day; varying the Light Rail/Metro threshold:

| LRT Threshold (trips/day) | Light Rail/Metro | BRT | Local Bus |
|---|---|---|---|
| 50,000 | 3 | 1 | 0 |
| 75,000 | 2 | 2 | 0 |
| 100,000 | 1 | 3 | 0 |

Light Rail/Metro threshold fixed at 75,000 trips/day; varying the BRT threshold:

| BRT Threshold (trips/day) | Light Rail/Metro | BRT | Local Bus |
|---|---|---|---|
| 10,000 | 2 | 2 | 0 |
| 15,000 | 2 | 2 | 0 |
| 20,000 | 2 | 2 | 0 |

## W5 Config Used

```
w_demand_gain=0.50, w_efficiency=0.25, w_equity=0.25
max_detour_ratio=1.8 (anchor-directness), min_stop_spacing=300m, max_stop_spacing=1000m
min_daily_demand=500 trips/day, max_route_km=30km
```