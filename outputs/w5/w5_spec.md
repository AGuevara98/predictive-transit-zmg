# W5 Multi-Objective Function Specification

This document is the authoritative interface contract for W6 (corridor generation) and W7 (route audit).

## Objective Terms

| Term | Direction | Formula |
|------|-----------|---------|
| f1 demand gain | maximize | `sum(demand_i * gain_factor * unserved_fraction_i) / sum(demand_i)` |
| f2 route cost  | minimize | `route_km` |
| f3 equity      | maximize | `mean(equity_score_i)` for served AGEBs |

Where:
- `gain_factor = 0.5` if route connects to existing SITEUR network, else `0.2`
- `unserved_fraction` = `coverage_gap_normalized` from `features.ageb_coverage_gap` (1=unserved, 0=well-served)
- `equity_score` = from `features.nppv_prioritization` (mean of `pe_marginacion_n`, `pe_rezago_n`)

## Transfer Penalty

Routes not connected to the existing SITEUR network incur a flat `0.1` deduction
from the composite score, representing required transfers for riders.

## Scalar Composite Score

```
efficiency  = max(0, 1 - route_km / max_route_km)
f1_scaled   = f1_demand_gain / gain_factor   # rescale to [0, 1]
composite   = w_demand_gain * f1_scaled + w_efficiency * efficiency + w_equity * f3
total_score = composite - transfer_penalty
```

Default weights:
- `w_demand_gain = 0.5`
- `w_efficiency  = 0.25`
- `w_equity      = 0.25`
- `max_route_km  = 30.0`

## Pareto Multi-Objective Mode

For ranking a population of candidates, minimize the objective vector `(-f1, f2, -f3)`
using fast non-dominated sort (NSGA-II style). Rank 1 = Pareto-optimal front.

## Constraints

All four constraints must pass for a candidate to be feasible:

| Constraint | Limit |
|---|---|
| detour_ratio = route_km / straight_line_km | <= 1.8 |
| stop_spacing = route_km*1000 / (n_stops-1) | [300, 1000] m |
| sum(transit_demand) | >= 500 trips/day |
| route_km | <= 30 km |

## RouteCandidate Interface

W6 and W7 must populate a `RouteCandidate` with:

```python
RouteCandidate(
    candidate_id      = str,         # unique identifier
    served_ageb_ids   = List[str],   # cvegeo of AGEBs within 400m of route
    route_km          = float,       # total route length in km
    n_stops           = int,         # number of stops
    straight_line_km  = float,       # endpoint-to-endpoint Euclidean distance km
    connects_to_existing = bool,     # True if route joins SITEUR network
)
```

Then call:

```python
from w5_objective import load_ageb_context, evaluate_objective
from w5_constraints import check_constraints
from w5_pareto import pareto_rank

contexts   = load_ageb_context(candidate.served_ageb_ids, engine)
objective  = evaluate_objective(candidate, contexts, config)
constraint = check_constraints(candidate, contexts, config)
```