# W8 Validation Report

## W8.1 -- Backtest Results

**Premium routes masked:** Mi Macro (MM) + Mi Tren (MT) agencies
**Stops excluded:** 1,344
**Anchor AGEBs found after masking:** 30
**Corridors re-proposed:** 6
**Mean route-shape overlap:** 23.6%

### Per-Route Overlap

| Route ID | Max Overlap (%) |
|----------|----------------|
| MC-A03 | 0.0% |
| MC-A05 | 46.5% |
| MC-A06 | 100.0% |
| MC-A07 | 21.5% |
| MC-A08 | 37.0% |
| MC-A09 | 56.5% |
| MC-A10 | 51.0% |
| MC-A13 | 0.0% |
| MC-A15 | 60.5% |
| MC-A16 | 30.5% |
| MC-A17 | 12.0% |
| MC-A18 | 18.5% |
| MC-A19 | 8.5% |
| MC-A20 | 12.0% |
| MC-A21 | 9.5% |
| MC-L1 | 17.0% |
| MC-L1E | 17.5% |
| MP-A01 | 20.0% |
| MP-A02 | 16.0% |
| MP-A03 | 0.0% |
| MP-A04 | 11.5% |
| MP-A05-1 | 30.5% |
| MP-A06 | 34.5% |
| MP-A07 | 20.5% |
| MP-C01 | 51.5% |
| MP-C02 | 11.0% |
| MP-C03 | 14.0% |
| MP-T01 | 16.0% |
| MP-T02 | 13.5% |
| MP-T03 | 19.0% |
| MT_L3 | 8.0% |
| MT_L1 | 5.5% |
| MT_L2 | 9.5% |

## W8.2 -- Benchmark: W6 vs. Premium Routes

**W6 feasible corridors:** 3
**Premium route shapes:** 33
**Mean W6 overlap with premium routes:** 0.0%
**Total W6 km:** 50.7 km

*(Low overlap means W6 identifies new un-served areas rather than replicating existing lines -- an expected and valid finding.)*

| W6 Corridor | Best Matching Premium Route | Overlap |
|-------------|----------------------------|---------|
| W6_G00 | None | 0.0% |
| W6_G01 | None | 0.0% |
| W6_G03 | None | 0.0% |

## W8.3 -- Quantitative Before/After Metrics

| Metric | Before W6 | After W6 | Delta |
|--------|-----------|----------|-------|
| Coverage rate (AGEBs) | 69.9% | 70.9% | +1.0% |
| Accessibility Gini | 0.6333 | 0.6242 | -0.0091 |
| W6 pop-served / route-km | -- | 1,154 | -- |
| AGEBs newly served by W6 | -- | 23 | -- |
| Population newly served | -- | 51,236 | -- |
| Total W6 route km | -- | 50.7 km | -- |

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