# W6 Anchor-Level Network Connection — Design (A/B/baseline comparison)

**Date:** 2026-07-15
**Status:** Draft — awaiting user review
**Context:** Follow-up to the W6 hub-connectivity work
(`2026-07-13-w6-hub-connectivity-design.md`, Accepted/implemented, currently uncommitted in
the working tree) and the W8 Question-B negative verdict (`w8_corridor_merit.py`, CLAUDE.md
W8 section). The hub work forces network connection at the **routing** level (injects bare
GTFS stops as MST terminals). This work explores forcing it one level earlier, in **anchor
selection**, and compares the two anchor-level mechanisms head-to-head against the hub
baseline.

## Goal

Primary driver: **network realism** — generated corridors should read as extensions/feeders
that tie into the existing SITEUR network, not greenfield lines floating in the periphery.

Deliverable: a 3-way, apples-to-apples comparison of three anchor mechanisms, scored on the
same merit axes as the W8 Question-B verdict, so the user can choose the one that produces
the best corridors on their own terms.

## The core tension

Anchors are drawn from the top Jenks class of `coverage_gap_n`, which by construction selects
**unserved** AGEBs (accessibility ≈ 0) — precisely the AGEBs *farthest* from any GTFS stop.
"Force at least one anchor connected to a stop" therefore means deliberately admitting a
served (or served-fringe) AGEB into a set the selection rule is actively filtering out. Each
mode below resolves that tension differently.

**"Connected" is defined once, shared by all modes:** an AGEB is *network-connected* if it has
≥1 GTFS stop within **400 m** of its centroid (W3's catchment standard), computed in PostGIS
against `base.gtfs_stops`. Threshold fixed at 400 m for this round (not swept).

## The three anchor modes

A single `ANCHOR_MODE ∈ {baseline, two_tier, frontier}` selector drives generation. All three
share the existing downstream pipeline unchanged: KMeans clustering → OSM snap →
`build_corridor_path` (MST/Steiner) → W5 objective + constraints → Pareto rank.

### `baseline` — incumbent (hub injection)
Current committed-plus-uncommitted logic: Jenks high-gap anchors + KMeans (k=6) + near/far
**bare-stop hub** injection (`select_group_hubs`). Included so the comparison shows whether
either anchor-level mode actually beats what already exists.

### `two_tier` (Approach A) — demand anchor + network tie-in
- Select Jenks demand anchors exactly as today; tag `role="demand"`.
- Cluster into groups (KMeans, unchanged).
- Per group, find the **network-connected AGEB** (≥1 stop within 400 m) that is nearest to any
  anchor in that group (the cheapest network entry point, mirroring the hub rule's
  nearest-to-closest-anchor logic) and inject it as a mandatory anchor tagged `role="network"`,
  added to that group's MST terminal set.
- **No bare-stop hubs** — the tie-in is a real demand-bearing AGEB (counts toward served
  demand, equity, and High-gap share), replacing the hub's bare stop node.
- If no network-connected AGEB exists within a sane radius of a group, that group falls back to
  baseline hub injection (documented, logged) rather than producing an isolated corridor.

### `frontier` (Approach B) — seam anchor pool
- Restrict the Jenks high-gap pool, *before* clustering, to anchors that are themselves within
  400 m of a network-connected AGEB or stop (the served/unserved seam).
- Cluster and build as usual; **no hub injection** (connection is intrinsic to every anchor).
- Known trade-off: deep-interior high-gap pockets (needing a genuine long feeder) are excluded
  because they are not near the frontier. This is surfaced explicitly in the report as the
  mode's defining limitation.

## Comparison harness — `src/w6_anchor_experiment.py`

Runs all three modes end-to-end, reusing existing pipeline functions
(`w6_graph.build_corridor_path`, W5 `evaluate_objective`/`check_constraints`/`pareto_rank`,
and the merit logic factored out of `w8_corridor_merit.py`).

**Isolation invariant:** the harness **does not write to `features.route_candidates`** — the
canonical W6 run stays intact while experimenting. It reads the DB (coverage gap, stops,
contexts) but writes only to `outputs/w6_experiment/`.

**Per-mode outputs:** `outputs/w6_experiment/<mode>/{corridor_candidates.geojson,
corridor_scores.csv}`.

**Scoring — the same axes as the W8 Question-B verdict**, so the comparison answers "which
makes better corridors," not merely "which runs":

| Metric | Deciding axis |
|---|---|
| # feasible corridors | does forcing connection rescue or kill feasibility? |
| connectivity: % corridors whose endpoints touch the network | the whole point — expect ~100% for A/B |
| High-gap share of served AGEBs (vs 20.7% metro baseline) | genuine need (Question-B axis a) |
| best Jaccard AGEB-overlap vs 247 SITEUR routes | non-redundancy (axis b) |
| corridor demand/km percentile vs existing routes | efficiency (axis c) |
| mean route_km, mean W5 total_score | feasibility + overall quality |

**Comparison report:** `outputs/w6_experiment/comparison.md` — one side-by-side table across the
three modes plus a short per-mode narrative and an explicit recommendation stub for the user to
confirm.

## Thesis-cleanliness note (baked into the report)

Both A and B inject a **supply-side signal** into what was a pure demand-gap generator. The
report states this explicitly and quantifies how far each shifts the "generate purely from the
demand gap" story (e.g., what fraction of served demand/High-gap share now comes from the
injected network anchor). This lets the user weigh realism against methodological cleanliness
when choosing.

## Where the code changes land

- `src/w6_anchors.py` — add:
  - `network_connected_agebs(engine, radius_m=400)` — returns AGEBs with ≥1 stop within radius
    (PostGIS `ST_DWithin` against `base.gtfs_stops`), with centroid cx/cy.
  - `add_network_anchors(anchors_gdf, connected_gdf)` — mode A: per group, nearest connected
    AGEB → mandatory `role="network"` anchor (KDTree lookup, matching the existing hub pattern),
    with baseline-hub fallback flag when none in range.
  - `select_frontier_anchors(gap_gdf, connected_gdf, radius_m=400, ...)` — mode B: high-gap
    Jenks pool filtered to the seam.
  - `role` column convention (`demand` / `network`) carried on the anchor GeoDataFrame.
- `src/w6_anchor_experiment.py` — new orchestrator/harness (per above). Factors the merit
  scoring out of `w8_corridor_merit.py` into a reusable function (import, don't copy).
- `tests/test_w6_anchors.py` — extend with synthetic-geometry cases:
  - `add_network_anchors` picks the nearest connected AGEB per group and tags role correctly.
  - `select_frontier_anchors` keeps seam anchors, drops deep-interior ones.
  - the shared "connected within 400 m" predicate behaves at the boundary.

## Out of scope (this round)

- Sweeping the 400 m threshold (fixed at 400 m per user direction).
- Modifying the canonical `run_w6.py` default mode or writing experiment corridors to
  `features.route_candidates` — deferred until a winning mode is chosen.
- Requiring corridors to terminate at a genuine destination (job center/CBD) or to pick up
  demand *along* their length — inherited deferrals from the hub-connectivity spec.
- Committing/promoting the winning mode into the canonical pipeline — a separate follow-up once
  the user reviews `comparison.md` and chooses.

## Success criteria

1. `python src/w6_anchor_experiment.py` runs all three modes and writes
   `outputs/w6_experiment/comparison.md` + per-mode geojson/csv, without touching
   `features.route_candidates`.
2. For modes A and B, 100% of generated corridors have both endpoints network-connected
   (the realism goal is met by construction).
3. The comparison table is populated on the live DB and the report states a clear, evidenced
   recommendation among baseline / A / B.
4. New tests pass; existing W6 tests still pass.
