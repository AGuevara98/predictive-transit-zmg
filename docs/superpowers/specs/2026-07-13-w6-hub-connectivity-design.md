# W6 Corridor Hub Connectivity — Design

**Date:** 2026-07-13 (amended 2026-07-14)
**Status:** Accepted — implemented, strengthened to both-ends per the amendment below
**Context:** Follow-up to W8 Question B (corridor merit investigation, see
`w8_question_b_corridor_merit` memory and CLAUDE.md's W8 "Next steps" item 1).

## Amendment (2026-07-14) — root BOTH ends, not just the cheapest

The single min-distance hub below was implemented first and verified faithful, but on
the live DB it produced a NULL effect: the feasible set (G00/G03/G05) and all route_km
were unchanged, and the motivating dead-ends persisted (G00 still starts 6,124m from any
stop; G05 still ends 6,473m away). Cause: the min-distance rule roots each corridor at its
CHEAPEST entry, and every corridor group already contains an anchor within ~700m of a stop
(high-gap anchors sit in ZMG's stop-dense core), so the hub is absorbed at the end that was
already connected. It guaranteed connectivity structurally but did not fix "leads nowhere."

**Strengthened rule (this is what is implemented):** per group, inject TWO hub terminals —
the nearest stop to the CLOSEST anchor (cheapest entry) AND the nearest stop to the most
REMOTE anchor (the anchor with the maximum distance-to-nearest-stop, i.e. the would-be
dead-end). This roots the corridor at both ends. It deliberately lengthens route_km for
groups with a remote anchor (adds a spur of that anchor's dead-end distance) and is expected
to change the feasible set — see original "Expected impact" below, which now actually fires.
`select_group_hubs` returns near-hub columns (unchanged contract) plus `far_hub_*` columns;
`run_w6.py` snaps and appends both hub OSM nodes to each group's `terminal_nodes`.

## Problem

W6's corridor generator (`src/w6_graph.py::build_corridor_path`) builds an MST-based
Steiner approximation over anchor AGEB centroids only. It has no notion of the existing
SITEUR network — a corridor can (and does) dead-end tens of kilometers from anywhere a
rider could transfer onto the rest of the system.

Confirmed on the live DB (2026-07-13): of the 3 corridors currently marked `feasible=true`,
`W6_G00`'s start point is 6,124m from the nearest GTFS stop; `W6_G05`'s end point is 6,473m
away. `W6_G03` — independently flagged by `src/w8_corridor_merit.py` as the one corridor with
genuine merit (100% High-gap AGEBs served, 94th-percentile demand/km) — has both endpoints
close (361m / 88m).

The existing `connects_to_existing` flag (`src/w6_candidates.py::check_connects_siteur`) does
not catch this: it's `True` for all 6 corridors, including the two dead-enders, because it
only checks whether *any point along the route* passes within 400m of *any* stop — trivially
satisfied by a route's middle crossing ZMG's dense stop network, regardless of where the route
actually starts or ends.

## Fix

Make network connectivity structural, not incidental: inject the nearest existing SITEUR stop
as a mandatory MST terminal for each corridor group, so every generated corridor is rooted in
the existing network by construction.

**Selection rule:** for each corridor group (post-KMeans clustering, pre-path-building), find
the single (anchor, stop) pair with minimum distance across all anchors in that group and all
`base.gtfs_stops`. That stop becomes an extra terminal for the group — one hub per group,
chosen as the cheapest natural entry point (not the group centroid, which could pick an
inconvenient stop when anchors are spread out).

**Mechanism:** `build_corridor_path()` in `src/w6_graph.py` is unchanged — it already treats
its `terminal_nodes` list generically via MST/Steiner over pairwise OSM shortest paths. The
hub stop is snapped to an OSM node the same way anchor centroids already are
(`snap_to_osm_nodes`) and appended to that group's `terminal_nodes` before calling
`build_corridor_path()`. No bolted-on connector segment after the fact — the hub participates
in the same tree as the anchors.

**Where:**
- `src/w6_anchors.py` — add `load_gtfs_stops(engine)` (loads `base.gtfs_stops` with cx/cy
  once, ~12,231 rows) and a nearest-hub selector using a KDTree (scipy) for in-memory
  nearest-neighbor lookup across all anchors in a group — avoids one SQL round-trip per anchor.
- `src/run_w6.py` — Step 6/7 (currently lines 254–276): after snapping anchor centroids to
  OSM nodes, for each corridor group also snap its selected hub stop to an OSM node and append
  it to that group's `terminal_nodes` list before calling `build_corridor_path()`.
- `src/w6_candidates.py::check_connects_siteur` — unchanged. With the hub as a real tree node,
  this will trivially pass by construction; it doesn't need to become an endpoint-based check
  since the thing it was approximating is now guaranteed structurally.

## Expected impact

Adding a hub terminal lengthens `route_km` for any group whose anchors sit far from the
network (worst case observed: 6+ km). This will likely:
- Push some currently-feasible corridors (`W6_G00`, `W6_G05`) over the 30km cap or the 1.8
  detour-ratio cap
- Possibly make previously-infeasible corridors feasible if their hub happens to sit
  conveniently
- Change the feasible set's *composition*, not just its size — re-run required, not just a
  reinterpretation of existing output

**Contingency — if the feasible set becomes empty:** do not treat that as a silent failure or
immediately relax constraints to force output. Instead, inspect per-group `route_km` and
`detour_ratio` against the W5 caps (30km, 1.8) to see how far over each infeasible group is,
and which single constraint (route length vs. detour ratio vs. stop spacing vs. min demand) is
binding. That determines whether the caps are actually wrong (worth revisiting as a W5 config
question) or whether the honest conclusion is that W6's anchor/clustering architecture
(30 anchors / KMeans k=6 / MST) — already flagged in CLAUDE.md's W8 Line 4 section as the
mechanism behind the Line 4 reconstruction failure — cannot produce network-connected corridors
under its current parameters, which is itself a valid and citable finding for the thesis.

## Downstream re-run scope

- `python src/run_w6.py` — full re-run, new `features.route_candidates`
- `src/w8_corridor_merit.py` — re-run against the new feasible set (currently uncommitted;
  will be committed as part of this work per the existing memory action item)
- `src/w8_corridor_map_data.py` / `src/w8_corridor_map_render.py` — re-run to regenerate the
  visualization (currently uncommitted, still have hardcoded scratchpad I/O paths that need
  fixing to `outputs/w8/` regardless of this change)
- CLAUDE.md's W6 and W8 sections — new dated entry with updated corridor IDs/km/scores,
  following the existing pattern used for the beta=1.2005 and mode-assignment re-runs
- `tests/test_w6_anchors.py` — extend with a case verifying nearest-stop selection picks the
  minimum-distance anchor-stop pair per group

## Out of scope (deferred per user direction)

- Requiring corridors to terminate at a genuine trip *destination* (job center, CBD) rather
  than just the network — noted as a possible follow-up if hub-connectivity alone doesn't fully
  resolve the "leads nowhere" concern
- Requiring corridors to pick up demand *along* their length, not just at anchors/hub —
  same, deferred
- Resolving `ANCHOR_TRIM_COL` (`coverage_gap_n` vs `transit_demand`) — flagged in CLAUDE.md as
  a related open question but not required to implement this fix; empirically the two are
  near-identical in the unserved anchor pool per the Line 4 backtest, so it doesn't block this
  work
