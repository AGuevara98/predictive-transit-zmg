# W6 Anchor Mode Comparison (baseline / two_tier / frontier)

Metro High-gap baseline share: 20.7%. demand/km pass = >= 50th pct of existing routes; non-redundant = best Jaccard < 0.60.

| Mode | Corridors | Feasible | Endpoints connected | Mean High-gap share | All non-redundant | Mean demand/km pct | Merit-pass |
|---|---|---|---|---|---|---|---|
| baseline | 6 | 0 | 0/0 | nan% | True | nan | 0/0 |
| two_tier | 6 | 3 | 1/3 | 80.6% | True | 32 | 1/3 |
| frontier | 5 | 1 | 1/1 | 60.0% | True | 66 | 1/1 |

## Per-corridor detail

| Mode | ID | km | Served | Demand | Feasible | Endpts conn | High-gap | Jaccard | demand/km pct | Merit pass |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | baseline_G00 | 24.9 | 18 | 59220 | False | False | 33.3% | 0.04 | 1 | False |
| baseline | baseline_G01 | 46.9 | 89 | 410816 | False | True | 33.7% | 0.23 | 28 | False |
| baseline | baseline_G02 | 36.6 | 84 | 487683 | False | True | 48.8% | 0.11 | 57 | True |
| baseline | baseline_G03 | 3.5 | 3 | 32386 | False | True | 100.0% | 0.03 | 31 | False |
| baseline | baseline_G04 | 44.5 | 28 | 148616 | False | False | 46.4% | 0.09 | 2 | False |
| baseline | baseline_G05 | 21.3 | 4 | 40614 | False | False | 75.0% | 0.04 | 1 | False |
| two_tier | two_tier_G00 | 16.6 | 12 | 47343 | True | False | 41.7% | 0.00 | 1 | False |
| two_tier | two_tier_G01 | 43.7 | 83 | 421077 | False | True | 34.9% | 0.22 | 34 | False |
| two_tier | two_tier_G02 | 36.3 | 84 | 486581 | False | False | 48.8% | 0.11 | 57 | True |
| two_tier | two_tier_G03 | 1.4 | 3 | 32386 | True | True | 100.0% | 0.03 | 94 | True |
| two_tier | two_tier_G04 | 39.2 | 27 | 134468 | False | False | 44.4% | 0.05 | 2 | False |
| two_tier | two_tier_G05 | 15.0 | 3 | 40154 | True | False | 100.0% | 0.02 | 1 | False |
| frontier | frontier_G00 | 8.5 | 22 | 82085 | False | True | 45.5% | 0.08 | 34 | False |
| frontier | frontier_G01 | 28.6 | 47 | 247390 | False | True | 36.2% | 0.13 | 28 | False |
| frontier | frontier_G02 | 12.6 | 36 | 234414 | False | False | 47.2% | 0.16 | 85 | True |
| frontier | frontier_G03 | 2.4 | 5 | 35784 | True | True | 60.0% | 0.03 | 66 | True |
| frontier | frontier_G05 | 5.4 | 14 | 80234 | False | False | 57.1% | 0.15 | 69 | True |

## Notes

- baseline injects bare GTFS stops as MST terminals (routing-level connection).
- two_tier / frontier inject a supply-side signal into anchor SELECTION; the
  'Mean High-gap share' and 'demand/km pct' columns show how much corridor merit
  each buys relative to the pure-demand baseline. Weigh realism vs the clean
  'generate purely from the demand gap' story when choosing a mode.