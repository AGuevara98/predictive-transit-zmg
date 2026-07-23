# W9 W8 Validation -- Toluca

Transfer analogue of ZMG's `run_w8.py`, CSV-based.

## W8.1 -- Backtest (hold-out)

**Demand-trunk proxy** (frequencies.txt is a uniform-300s placeholder, so 'trunk' = routes serving the most modeled demand).
- Trunk routes masked: 23  (7,503 stops, 12.4% of network)
- Frontier anchors after masking: 6 (non-masked baseline: 14)  |  corridors built 0, feasible 0

**Degenerate outcome -- seam collapse.** The hold-out re-proposes 0 corridors. The mechanism is intrinsic to a bus-only network: unlike ZMG's premium rail (a separable overlay redundant with parallel buses, so masking it leaves the served/unserved frontier intact), the demand-trunk here *is* the local bus service. Masking its stops erases the very served/unserved seam the frontier generator anchors on, so few or no frontier anchors survive and no multi-anchor corridor can be built. This confirms the ZMG-documented precondition: the mask-and-reconstruct backtest needs a premium tier redundant with underlying coverage -- a condition neither transfer city meets. The benchmark (W8.2) and before/after metrics (W8.3) are the operative validation for these cities.

## W8.2 -- Benchmark: feasible W6 corridors vs existing network

- Feasible W6 corridors: 4  vs  622 existing routes
- **Mean W6 overlap with existing routes: 75.0%**
- Total W6 km: 32.9

*(Substantial overlap: in this already well-served network (~80% baseline coverage) W6 largely re-identifies existing high-demand corridors rather than adding new coverage -- revealed-preference corroboration.)*

| W6 corridor | Best-matching route | Overlap |
|---|---|---|
| W6_G00 | 18869220 | 41.5% |
| W6_G01 | 18878146 | 58.5% |
| W6_G03 | 18782088 | 100.0% |
| W6_G05 | 19369234 | 100.0% |

## W8.3 -- Before/after metrics

| Metric | Before W6 | After W6 | Delta |
|---|---|---|---|
| Coverage rate | 80.9% | 81.2% | +0.4% |
| Accessibility Gini | 0.4164 | 0.4133 | -0.0031 |
| Pop-served / route-km | -- | 3,516 | -- |
| AGEBs newly served | -- | 2 | -- |
| Population newly served | -- | 9,444 | -- |
| Total W6 route km | -- | 32.9 | -- |
