# W8 -- Per-Line Masked Backtests (route-level)

**Question.** *Which line types does the re-architected W6 generator trace?* Each mask holds
out a line (or agency), recomputes W3 accessibility + coverage-gap on the surviving GTFS
network, re-runs the canonical W6 generator (frontier anchors on the masked served/unserved
seam -> `coverage_gap_n` trim -> MST-diameter-trunk shaper -> anchor-directness feasibility
gate), and measures the fraction of each masked route's shape that falls within 400 m of any
re-proposed **feasible** corridor.

All overlaps below are on the **aligned** generator (canonical `run_w6`), directly citable --
not the retired `build_corridor_path` path.

## Per-line / per-agency overlap table

| Mask | route_ids / agencies | Stops masked | Built / feasible | Mean overlap |
|------|----------------------|--------------|------------------|--------------|
| Premium (all rail+BRT) | agencies MM + MT | 1,344 | 5 / 5 | **0.150** |
| Mi Macro (BRT only) | agency MM | 1,268 | 5 / 5 | **0.166** |
| Line 1 (rail) | MT_L1 + ST_L1 | 138 | 5 / 4 | **0.000** |
| Line 2 (rail) | MT_L2 + ST_L2 | 108 | 5 / 4 | **0.000** |
| Line 3 (rail) | MT_L3 + ST_L3 | 126 | 5 / 4 | **0.000** |
| Line 4 (out-of-sample) | not in 2024 GTFS; probe vs feasible set | -- | -- | **0.05** recall |

Line 1/2 per-route overlap is 0.000 for **both** the rail alignment (`MT_Lx`) and its SiTren
feeder (`ST_Lx`).

## Interpretation

The generator **weakly traces the dense Mi Macro BRT feeder network** (premium 0.150, Mi Macro
0.166) but **does not reconstruct any rail line** (Lines 1/2/3 all 0.000; Line 4 out-of-sample
0.05 recall). n = 5 masks now support this split (3 rail lines + 1 rail out-of-sample + 2
agency-level), overturning nothing and firming up the "diagnostic strong / generative
characterized-limitation" narrative.

**Mechanism.** Masking a single rail line barely moves accessibility -- the parallel bus network
survives (non-zero-accessibility AGEBs stay at 1,266 for every rail mask), so no strong new
coverage gap forms along the held-out corridor and the frontier-anchor pool does not
concentrate there. This is the same anchor-funnel limitation documented for the Line 4
reconstruction failure: the generator surfaces demand gaps on the served/unserved *seam* of the
bus network, not thinly-served peripheral rail corridors. The BRT masks move the needle more
because Mi Macro carries a larger share of local bus-network accessibility, so masking it opens
a real gap that the anchors partly re-trace.

**Caveat on the A-vs-B distinction (unchanged).** Reconstruction of a *built* line is a weak,
asymmetric proxy for corridor merit (Question B): rail lines are chosen for
political/financial/land reasons a demand model cannot see, so non-reconstruction is faint
evidence against the generator. The strong contribution remains the demand-gap **diagnostic**
(W3/W4); the generative layer is a characterized, partially-positive contribution (W6_G02
passes all three merit axes -- see the W6 re-architecture section).

## Data note -- MT_* vs ST_* are distinct services, not duplicates

CLAUDE.md previously described `ST_L1/ST_L2` as "duplicates" of the `MT_*` rail lines. Verified
here they are **not** spatial duplicates (MT_Lx-vs-ST_Lx shape overlap < 0.10 for all three
lines). `MT_*` is the Mi Tren tram/light-rail (route_type 0, ~1 km stop spacing); `ST_*` is the
SiTren feeder-bus network (route_type 3, ~85 m spacing) on a different alignment. Masking both
per line removes the whole "line system" (rail + dedicated feeder), mirroring the Line 3
precedent; per-route overlap keeps the rail alignment distinct (both still 0.000).

## Reproduce

```
python src/w8_line_backtests.py L1 L2       # or L1 L2 L3
```

Outputs: `outputs/w8/w8_line_backtests_summary.csv`,
`outputs/w8/w8_line_backtests_per_route.csv`, this report.
