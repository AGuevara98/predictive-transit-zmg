# W5 Multi-Objective Function -- Demo Report

Three synthetic route candidates were constructed from real high-gap AGEBs
to validate the W5 evaluation framework end-to-end.

## Candidate Summary

| Candidate | AGEBs | km | Stops | Connected |
|---|---|---|---|---|
| A_demand | 3 | 60.62 | 123 | True |
| B_equity | 5 | 40.05 | 82 | False |
| C_broad | 5 | 84.61 | 171 | True |

## Objective Scores

| Candidate | f1 gain | f2 km | f3 equity | Composite | Total | Pareto Rank | Feasible |
|---|---|---|---|---|---|---|---|
| A_demand | 0.0347 | 60.62 | 0.2252 | 0.0910 | 0.0910 | 2 | False |
| B_equity | 0.0401 | 40.05 | 0.5920 | 0.2483 | 0.1483 | 1 | False |
| C_broad | 0.0299 | 84.61 | 0.3333 | 0.1133 | 0.1133 | 2 | False |

**A_demand violations:**
- Detour ratio 51.04 exceeds max 1.8
- Route length 60.6km exceeds max 30.0km

**B_equity violations:**
- Route length 40.0km exceeds max 30.0km

**C_broad violations:**
- Detour ratio 6.16 exceeds max 1.8
- Route length 84.6km exceeds max 30.0km

## W5 Config Used

```
w_demand_gain         = 0.5
w_efficiency          = 0.25
w_equity              = 0.25
connected_gain_factor = 0.5
isolated_gain_factor  = 0.2
transfer_penalty      = 0.1
max_detour_ratio      = 1.8
min_stop_spacing_m    = 300.0
max_stop_spacing_m    = 1000.0
min_daily_demand      = 500.0
max_route_km          = 30.0
```