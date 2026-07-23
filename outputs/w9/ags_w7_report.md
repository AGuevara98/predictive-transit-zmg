# W9 W7 Existing Route Audit -- Aguascalientes

Transfer analogue of ZMG's `run_w7.py`, CSV-based. All routes are route_type=3 bus (Gobierno del Estado de Aguascalientes); the audit is mode-agnostic.

## Summary

- **Routes audited:** 48
- **Feasible (W5 constraints):** 6
- **Routes flagged:** 47 (10 Low demand, 33 Indirect, 4 Redundant)
- **Modification proposals:** 47

> **Feasibility note:** median GTFS stop spacing is 239m and 77% of routes sit below the W5 300m minimum. Where the feasible count is low (6/48 here), the binding constraint is this sub-300m stop density in the source feed, not route directness or length -- the audit flags (Low demand / Indirect / Redundant) and W5 scores are the primary signal and are independent of the feasibility gate.

## Score Distribution

- Mean total_score: 0.151  |  median: 0.147
- Mean detour_ratio: 1.854
- Mean f1_demand_gain: 0.011  |  mean f3_equity: 0.253

## Top 10 Routes by Score

| route_id | route_short_name | total_score | f1_demand_gain | detour_ratio | flag |
|---|---|---|---|---|---|
| R_50B | R50B | 0.329 | 0.112 | 1.244 | nan |
| R_52 | R52 | 0.275 | 0.007 | 1.083 | Low demand |
| R_08 | R08 | 0.234 | 0.025 | 1.558 | Indirect |
| R_14 | R14 | 0.224 | 0.027 | 2.01 | Indirect |
| R_51 | R51 | 0.218 | 0.01 | 1.077 | Low demand |
| R_10N | R10N | 0.213 | 0.004 | 1.214 | Low demand |
| R_02 | R02 | 0.2 | 0.004 | 2.048 | Indirect |
| R_07 | R07 | 0.196 | 0.004 | 1.966 | Indirect |
| R_36 | R36 | 0.194 | 0.004 | 1.885 | Indirect |
| R_43N | R43N | 0.194 | 0.009 | 1.916 | Indirect |

## Flagged Routes

| route_id | route_short_name | total_score | detour_ratio | flag | overlap_route_id |
|---|---|---|---|---|---|
| R_40N | R40N | 0.055 | 3.614 | Redundant | R_40S |
| R_03 | R03 | 0.074 | 1.734 | Indirect | nan |
| R_11 | R11 | 0.08 | 1.537 | Indirect | nan |
| R_23 | R23 | 0.084 | 2.067 | Indirect | nan |
| R_06 | R06 | 0.084 | 1.699 | Indirect | nan |
| R_28 | R28 | 0.088 | 1.612 | Indirect | nan |
| R_40S | R40S | 0.089 | 2.913 | Indirect | nan |
| R_50 | R50 | 0.095 | 2.099 | Indirect | nan |
| R_05 | R05 | 0.106 | 1.743 | Indirect | nan |
| R_37 | R37 | 0.106 | 1.79 | Indirect | nan |
| R_01 | R01 | 0.111 | 1.346 | Low demand | nan |
| R_04 | R04 | 0.113 | 1.444 | Low demand | nan |
| R_33 | R33 | 0.123 | 1.371 | Low demand | nan |
| R_34 | R34 | 0.123 | 1.482 | Low demand | nan |
| R_09 | R09 | 0.124 | 2.169 | Indirect | nan |
| R_47 | R47 | 0.126 | 2.125 | Indirect | nan |
| R_46 | R46 | 0.126 | 1.734 | Indirect | nan |
| R_19 | R19 | 0.127 | 1.697 | Indirect | nan |
| R_30 | R30 | 0.131 | 2.025 | Indirect | nan |
| R_16 | R16 | 0.131 | 1.86 | Indirect | nan |
| R_35 | R35 | 0.136 | 1.733 | Indirect | nan |
| R_41PENAL | R41PENAL | 0.139 | 1.584 | Redundant | R_41ALAMEDA |
| R_45 | R45 | 0.145 | 1.946 | Indirect | nan |
| R_18 | R18 | 0.146 | 1.551 | Indirect | nan |
| R_38 | R38 | 0.147 | 1.306 | Low demand | nan |
| R_12 | R12 | 0.148 | 2.66 | Indirect | nan |
| R_41ALAMEDA | R41ALAMEDA | 0.149 | 1.578 | Redundant | R_24 |
| R_25 | R25 | 0.152 | 1.477 | Low demand | nan |
| R_20S | R20S | 0.154 | 3.334 | Redundant | R_20N |
| R_20N | R20N | 0.154 | 3.323 | Indirect | nan |
| R_24 | R24 | 0.167 | 1.368 | Low demand | nan |
| R_27 | R27 | 0.17 | 1.986 | Indirect | nan |
| R_42 | R42 | 0.175 | 1.733 | Indirect | nan |
| R_43S | R43S | 0.178 | 1.692 | Indirect | nan |
| R_29 | R29 | 0.178 | 2.272 | Indirect | nan |
| R_48 | R48 | 0.18 | 2.1 | Indirect | nan |
| R_39 | R39 | 0.185 | 1.643 | Indirect | nan |
| R_10S | R10S | 0.19 | 1.636 | Indirect | nan |
| R_43N | R43N | 0.194 | 1.916 | Indirect | nan |
| R_36 | R36 | 0.194 | 1.885 | Indirect | nan |
| R_07 | R07 | 0.196 | 1.966 | Indirect | nan |
| R_02 | R02 | 0.2 | 2.048 | Indirect | nan |
| R_10N | R10N | 0.213 | 1.214 | Low demand | nan |
| R_51 | R51 | 0.218 | 1.077 | Low demand | nan |
| R_14 | R14 | 0.224 | 2.01 | Indirect | nan |
| R_08 | R08 | 0.234 | 1.558 | Indirect | nan |
| R_52 | R52 | 0.275 | 1.083 | Low demand | nan |

## Method

1. GTFS route geometries from shapes.txt (EPSG:6372); straight_line_km = hull diameter.
2. Served AGEBs: centroid within 400m of route (geopandas sjoin).
3. W5 objective (f1 demand-gain, f2 length, f3 equity) + constraints (detour<=1.8, spacing 300-1000m, demand>=500/day, km<=30) + Pareto rank.
4. Flags: Low demand (f1<0.2 & score<0.3), Indirect (detour>1.5), Redundant (served-AGEB Jaccard>=0.60 with a higher-scoring route).