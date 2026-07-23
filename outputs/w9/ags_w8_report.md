# W9 W8 Validation -- Aguascalientes

Transfer analogue of ZMG's `run_w8.py`, CSV-based.

## W8.1 -- Backtest (hold-out)

**N/A for Aguascalientes.** No premium BRT/rail tier exists to hold out (all routes are route_type=3 bus), and the network is too small (Aguascalientes = 48 routes, single operator) for a meaningful demand-trunk proxy. Backtest is run for Toluca only (see that report).

## W8.2 -- Benchmark: feasible W6 corridors vs existing network

- Feasible W6 corridors: 3  vs  48 existing routes
- **Mean W6 overlap with existing routes: 54.3%**
- Total W6 km: 12.0

*(Substantial overlap: in this already well-served network (~80% baseline coverage) W6 largely re-identifies existing high-demand corridors rather than adding new coverage -- revealed-preference corroboration.)*

| W6 corridor | Best-matching route | Overlap |
|---|---|---|
| W6_G00 | R_04 | 34.0% |
| W6_G01 | R_48 | 69.5% |
| W6_G05 | R_29 | 59.5% |

## W8.3 -- Before/after metrics

| Metric | Before W6 | After W6 | Delta |
|---|---|---|---|
| Coverage rate | 80.3% | 80.6% | +0.3% |
| Accessibility Gini | 0.2681 | 0.2655 | -0.0027 |
| Pop-served / route-km | -- | 5,395 | -- |
| AGEBs newly served | -- | 1 | -- |
| Population newly served | -- | 1,940 | -- |
| Total W6 route km | -- | 12.0 | -- |
