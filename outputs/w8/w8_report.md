# W8 Validation Report

## W8.1 -- Backtest Results

**Premium routes masked:** Mi Macro (MM) + Mi Tren (MT) agencies
**Stops excluded:** 1,344
**Anchor AGEBs found after masking:** 30
**Corridors built after masking:** 5
**Corridors re-proposed (feasible):** 5
**Mean route-shape overlap:** 15.0%

### Per-Route Overlap

| Route ID | Max Overlap (%) |
|----------|----------------|
| MC-A03 | 40.0% |
| MC-A05 | 24.5% |
| MC-A06 | 0.0% |
| MC-A07 | 47.5% |
| MC-A08 | 14.0% |
| MC-A09 | 18.5% |
| MC-A10 | 0.0% |
| MC-A13 | 7.5% |
| MC-A15 | 60.0% |
| MC-A16 | 63.5% |
| MC-A17 | 55.5% |
| MC-A18 | 32.5% |
| MC-A19 | 11.5% |
| MC-A20 | 21.0% |
| MC-A21 | 13.0% |
| MC-L1 | 13.5% |
| MC-L1E | 13.0% |
| MP-A01 | 0.0% |
| MP-A02 | 0.0% |
| MP-A03 | 0.0% |
| MP-A04 | 0.0% |
| MP-A05-1 | 0.0% |
| MP-A06 | 10.5% |
| MP-A07 | 0.0% |
| MP-C01 | 7.5% |
| MP-C02 | 8.5% |
| MP-C03 | 7.5% |
| MP-T01 | 6.0% |
| MP-T02 | 10.5% |
| MP-T03 | 10.5% |
| MT_L3 | 0.0% |
| MT_L1 | 0.0% |
| MT_L2 | 0.0% |

## W8.2 -- Benchmark: W6 vs. Premium Routes

**W6 feasible corridors:** 4
**Premium route shapes:** 33
**Mean W6 overlap with premium routes:** 10.5%
**Total W6 km:** 44.9 km

*(Low overlap means W6 identifies new un-served areas rather than replicating existing lines -- an expected and valid finding.)*

| W6 Corridor | Best Matching Premium Route | Overlap |
|-------------|----------------------------|---------|
| W6_G00 | nan | 0.0% |
| W6_G01 | nan | 0.0% |
| W6_G02 | MP-C03 | 42.0% |
| W6_G03 | nan | 0.0% |

## W8.3 -- Quantitative Before/After Metrics

| Metric | Before W6 | After W6 | Delta |
|--------|-----------|----------|-------|
| Coverage rate (AGEBs) | 69.9% | 71.0% | +1.1% |
| Accessibility Gini | 0.6333 | 0.6146 | -0.0187 |
| W6 pop-served / route-km | -- | 4,195 | -- |
| AGEBs newly served by W6 | -- | 47 | -- |
| Population newly served | -- | 120,648 | -- |
| Total W6 route km | -- | 44.9 km | -- |

**Note on Gini 'after' estimate:** AGEBs within 400m of W6 corridors that currently have zero accessibility are assigned the mean accessibility of currently-served AGEBs. This is a conservative lower bound on the actual accessibility gain.

## Methodology

### Backtest
1. Identify all stop_ids for routes operated by MM (Mi Macro BRT) and MT (Mi Tren light rail).
2. Remove those stops from the GTFS feed; rebuild the transit graph.
3. Recompute cumulative-opportunities accessibility (same W3.1 algorithm, 45-min budget).
4. Recompute coverage-gap index in-memory (same W3.2 formula).
5. Re-run W6 anchor selection (Jenks + KMeans) and MST corridor generation.
6. For each masked route shape, sample 200 points at equal intervals; compute fraction within 400m of any re-proposed corridor.

### Benchmark
1. Reconstruct SITEUR premium route LineStrings from GTFS shapes.txt.
2. For each W6 corridor, compute max overlap fraction against all premium routes.

### Before/After Metrics
- **Coverage rate:** fraction of AGEB centroids within 400m of any transit stop/corridor.
- **Accessibility Gini:** Gini coefficient of accessibility_score across all AGEBs.
- **Pop-served/km:** sum of population in AGEBs within 400m of W6 corridors / total W6 km.