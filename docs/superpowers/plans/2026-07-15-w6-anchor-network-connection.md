# W6 Anchor-Level Network Connection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two anchor-level mechanisms for forcing W6 corridors to connect to the existing SITEUR network (`two_tier`, `frontier`) and a harness that runs them against the incumbent `baseline` (hub injection) 3-way, scoring all three on the W8 Question-B merit axes.

**Architecture:** Two new pure selection functions in `src/w6_anchors.py` plus one DB helper; the merit scoring in `src/w8_corridor_merit.py` refactored into an importable `build_merit_baselines()` + `score_corridor()`; a new standalone orchestrator `src/w6_anchor_experiment.py` that runs each anchor mode end-to-end through the existing W6 graph/W5 pipeline, writes per-mode outputs, and emits `outputs/w6_experiment/comparison.md`. The harness is read-only against the DB and never writes `features.route_candidates`.

**Tech Stack:** Python 3.9+, geopandas, shapely, scipy (cKDTree), scikit-learn (KMeans, already used), networkx/osmnx (via existing `w6_graph`), SQLAlchemy + PostGIS, pytest.

## Global Constraints

- Canonical CRS **EPSG:6372** for all geometry ops and stored coords; never compute distance in 4326.
- "Network-connected" AGEB is defined once: **≥1 GTFS stop within 400 m of the AGEB centroid** (`base.gtfs_stops`, `ST_DWithin`). Threshold fixed at 400 m this round (not swept).
- The experiment **must not** write to `features.route_candidates` or any `features`/`base` table — DB access is read-only. Outputs go only to `outputs/w6_experiment/`.
- Reuse existing pipeline functions (import, do not copy): `w6_graph.build_corridor_path/load_or_download_osm/project_to_6372/snap_to_osm_nodes`, `w6_candidates.build_route_candidate`, `w5_objective.evaluate_objective/load_ageb_context`, `w5_constraints.check_constraints`, `w6_mode.assign_mode`.
- ASCII-only in `print()` calls (Windows CP1252 console constraint).
- Anchor trim column stays `coverage_gap_n` (matches committed `run_w6.py`); N_ANCHORS=30, N_CORRIDORS=6 from `w6_anchors`.
- Activate venv before any python/pytest: `source .venv/bin/activate`.

---

### Task 1: Refactor merit scoring into importable functions

**Files:**
- Modify: `src/w8_corridor_merit.py` (extract reusable API from the monolithic `main()`; preserve its printed behavior)
- Test: `tests/test_w8_corridor_merit.py` (new)

**Interfaces:**
- Consumes: existing module-level `load_ageb_metrics(engine)`, `served_ageb_ids(ageb_gdf, geom, buffer_m=400.0)`, `jaccard(a, b)`, constants `REDUNDANCY_JACCARD_THRESH=0.60`.
- Produces:
  - `MeritBaselines` dataclass with fields `ageb: gpd.GeoDataFrame`, `route_served: dict[str, set]`, `baseline_dpk: pd.Series`, `metro_hi_share: float`.
  - `build_merit_baselines(engine) -> MeritBaselines`
  - `score_corridor(geom, route_km: float, total_demand: float, b: MeritBaselines) -> dict` returning keys `n_served, hi_share, best_jaccard, redundant, demand_per_km, dpk_pct, passed`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_w8_corridor_merit.py
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString

from src.w8_corridor_merit import MeritBaselines, score_corridor


def _baselines():
    # Three AGEBs strung along y=0 at x=0,1000,2000; first two High-gap.
    ageb = gpd.GeoDataFrame(
        {
            "cve_ageb": ["A0", "A1", "A2"],
            "gap_category": ["High-gap", "High-gap", "Low-gap"],
            "coverage_gap_n": [0.9, 0.8, 0.1],
            "transit_demand": [1000.0, 1000.0, 100.0],
            "final_score": [0.5, 0.5, 0.2],
        },
        geometry=[Point(0, 0), Point(1000, 0), Point(2000, 0)],
        crs="EPSG:6372",
    )
    # metro High-gap share = 2/3; one existing route overlaps only A2.
    return MeritBaselines(
        ageb=ageb,
        route_served={"R1": {"A2"}},
        baseline_dpk=pd.Series({"R1": 50.0}),
        metro_hi_share=2 / 3,
    )


def test_score_corridor_flags_needy_nonredundant_efficient():
    b = _baselines()
    # Corridor along A0-A1 (both High-gap); buffer 400m picks up A0,A1 only.
    geom = LineString([(0, 0), (1000, 0)])
    r = score_corridor(geom, route_km=1.0, total_demand=2000.0, b=b)
    assert r["n_served"] == 2
    assert r["hi_share"] == 1.0            # both served AGEBs High-gap
    assert r["best_jaccard"] == 0.0        # no overlap with R1's {A2}
    assert r["redundant"] is False
    assert r["dpk_pct"] == 100.0           # 2000/1.0 beats baseline 50
    assert r["passed"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/test_w8_corridor_merit.py -v`
Expected: FAIL with `ImportError: cannot import name 'MeritBaselines'`.

- [ ] **Step 3: Extract the reusable API**

At the top of `src/w8_corridor_merit.py`, add `from dataclasses import dataclass` to the imports. Immediately after the `jaccard()` function (currently ~line 53), insert:

```python
@dataclass
class MeritBaselines:
    """Precomputed reference stats for scoring corridor merit (Question B axes)."""
    ageb: gpd.GeoDataFrame
    route_served: dict          # route_id -> set(cve_ageb)
    baseline_dpk: pd.Series     # route_id -> served-demand / route_km
    metro_hi_share: float       # system-wide High-gap AGEB share


def build_merit_baselines(engine) -> MeritBaselines:
    """Load AGEB metrics + existing-route served sets and demand/km baseline."""
    ageb = load_ageb_metrics(engine)
    routes = gpd.read_postgis(
        "SELECT route_id, route_km, geom FROM features.route_audit",
        engine, geom_col="geom",
    )
    route_served, dpk = {}, {}
    for _, r in routes.iterrows():
        served = served_ageb_ids(ageb, r.geom)
        route_served[r.route_id] = served
        demand_sum = ageb.loc[ageb["cve_ageb"].isin(served), "transit_demand"].sum()
        if r.route_km and r.route_km > 0:
            dpk[r.route_id] = demand_sum / r.route_km
    return MeritBaselines(
        ageb=ageb,
        route_served=route_served,
        baseline_dpk=pd.Series(dpk),
        metro_hi_share=float((ageb["gap_category"] == "High-gap").mean()),
    )


def score_corridor(geom, route_km: float, total_demand: float,
                   b: MeritBaselines) -> dict:
    """Score one corridor on the three Question-B merit axes.

    passed = serves genuine need (High-gap share > metro baseline) AND
             non-redundant (best Jaccard < 0.60) AND
             efficient (demand/km >= 50th pct of existing routes).
    """
    served = served_ageb_ids(b.ageb, geom)
    sub = b.ageb[b.ageb["cve_ageb"].isin(served)]
    hi_share = float((sub["gap_category"] == "High-gap").mean()) if len(sub) else float("nan")
    best_j = max((jaccard(served, rs) for rs in b.route_served.values()), default=0.0)
    redundant = best_j >= REDUNDANCY_JACCARD_THRESH
    dpk = total_demand / route_km if route_km else float("nan")
    dpk_pct = float((b.baseline_dpk < dpk).mean() * 100) if len(b.baseline_dpk) else float("nan")
    passed = bool((hi_share > b.metro_hi_share) and (not redundant) and (dpk_pct >= 50))
    return dict(n_served=len(served), hi_share=hi_share, best_jaccard=float(best_j),
                redundant=redundant, demand_per_km=dpk, dpk_pct=dpk_pct, passed=passed)
```

Leave the existing `main()` in place for now (it still runs standalone). Do **not** delete its inline logic in this step — the refactor to call the new helpers is Step 5 so the test gate is isolated.

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest tests/test_w8_corridor_merit.py -v`
Expected: PASS.

- [ ] **Step 5: Rewrite `main()` to consume the new API (no behavior change)**

Replace the body of `main()` (currently lines ~56-149) so it builds baselines once and calls `score_corridor` per feasible corridor, keeping the same printed sections. Concretely, replace the manual `route_served`/`baseline` construction and the per-corridor `(a)/(b)/(c)` block with:

```python
def main():
    eng = create_engine(PG_URI)
    b = build_merit_baselines(eng)
    print(f"[Load] {len(b.ageb)} AGEBs; {len(b.route_served)} existing routes; "
          f"metro High-gap baseline={b.metro_hi_share:.1%}\n")

    w6 = gpd.read_postgis(
        "SELECT candidate_id, route_km, total_demand, geom FROM features.route_candidates "
        "WHERE feasible = true ORDER BY candidate_id",
        eng, geom_col="geom",
    )
    print(f"[W6] {len(w6)} feasible corridors: {list(w6['candidate_id'])}\n")
    print("=" * 78)
    for _, c in w6.iterrows():
        r = score_corridor(c.geom, c.route_km, c.total_demand, b)
        need = "need+" if r["hi_share"] > b.metro_hi_share else "need-"
        red = "unique" if not r["redundant"] else "REDUNDANT"
        eff = "eff+" if r["dpk_pct"] >= 50 else "eff-"
        verdict = "PASS" if r["passed"] else "MIXED/FAIL"
        print(f"  {c.candidate_id}: High-gap {r['hi_share']:.1%} ({need})  "
              f"best-Jaccard {r['best_jaccard']:.2f} ({red})  "
              f"demand/km {r['demand_per_km']:.0f} = {r['dpk_pct']:.0f}pct ({eff})  -> {verdict}")
    print("=" * 78)
```

- [ ] **Step 6: Verify the refactored script still runs (live DB)**

Run: `source .venv/bin/activate && python src/w8_corridor_merit.py`
Expected: prints the load line, 3 feasible corridors, and a PASS/MIXED line per corridor (G03 PASS, G00/G05 MIXED/FAIL) — same conclusion as before the refactor.

- [ ] **Step 7: Commit**

```bash
git add src/w8_corridor_merit.py tests/test_w8_corridor_merit.py
git commit -m "refactor(w8): extract build_merit_baselines + score_corridor for reuse"
```

---

### Task 2: `two_tier` selection primitives (network-connected AGEBs + anchor injection)

**Files:**
- Modify: `src/w6_anchors.py` (add two functions after `select_group_hubs`)
- Test: `tests/test_w6_anchors.py` (add cases)

**Interfaces:**
- Consumes: existing `select_anchors_jenks`, `cluster_anchors`; `scipy.spatial.cKDTree`.
- Produces:
  - `network_connected_agebs(engine, radius_m: float = 400.0) -> gpd.GeoDataFrame` with columns `cve_ageb, coverage_gap_n, transit_demand, cx, cy, geom` (only AGEBs with ≥1 stop within `radius_m`).
  - `add_network_anchors(anchors_gdf, connected_gdf, max_tie_in_m: float = 5000.0) -> tuple[gpd.GeoDataFrame, set]` — returns `(augmented_anchors, fallback_group_ids)`. Adds a `role` column (`"demand"`/`"network"`). For each `corridor_group`, injects the connected AGEB nearest to any anchor in that group as a `role="network"` row **iff** that nearest distance ≤ `max_tie_in_m` and the AGEB is not already an anchor in the group; otherwise the group id is returned in `fallback_group_ids` (caller applies hub injection).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_w6_anchors.py
from src.w6_anchors import add_network_anchors


def make_connected_gdf(rows):
    """rows: list of (cve_ageb, cx, cy)."""
    from shapely.geometry import Point
    return gpd.GeoDataFrame(
        {
            "cve_ageb": [r[0] for r in rows],
            "coverage_gap_n": [0.2] * len(rows),
            "transit_demand": [700.0] * len(rows),
            "cx": [r[1] for r in rows],
            "cy": [r[2] for r in rows],
        },
        geometry=[Point(r[1], r[2]) for r in rows],
        crs="EPSG:6372",
    )


def test_add_network_anchors_injects_nearest_connected_per_group():
    anchors = make_grouped_anchors([
        ("A0", 0, 0.0, 0.0),
        ("A1", 0, 1000.0, 0.0),
        ("A2", 1, 10000.0, 0.0),
    ])
    connected = make_connected_gdf([
        ("C_g0", 300.0, 0.0),        # 300m from A0 -> tie-in for group 0
        ("C_g1", 10200.0, 0.0),      # 200m from A2 -> tie-in for group 1
        ("C_far", 50000.0, 0.0),
    ])
    out, fallback = add_network_anchors(anchors, connected, max_tie_in_m=5000.0)
    assert fallback == set()
    net = out[out["role"] == "network"]
    assert set(net["cve_ageb"]) == {"C_g0", "C_g1"}
    assert set(net["corridor_group"]) == {0, 1}
    # original anchors tagged demand, nothing dropped
    assert (out[out["role"] == "demand"]["cve_ageb"].tolist()
            == ["A0", "A1", "A2"])


def test_add_network_anchors_falls_back_when_no_connected_in_range():
    anchors = make_grouped_anchors([("A0", 0, 0.0, 0.0)])
    connected = make_connected_gdf([("C_far", 20000.0, 0.0)])  # 20km > 5km cap
    out, fallback = add_network_anchors(anchors, connected, max_tie_in_m=5000.0)
    assert fallback == {0}
    assert (out["role"] == "network").sum() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/test_w6_anchors.py -k add_network_anchors -v`
Expected: FAIL with `ImportError: cannot import name 'add_network_anchors'`.

- [ ] **Step 3: Implement both functions**

Add to `src/w6_anchors.py` after `select_group_hubs` (keep the top-level `from sqlalchemy import text` and `import geopandas as gpd` already present):

```python
def network_connected_agebs(engine, radius_m: float = 400.0) -> gpd.GeoDataFrame:
    """AGEBs with >=1 GTFS stop within radius_m of their centroid (EPSG:6372).

    Returns cve_ageb, coverage_gap_n, transit_demand, cx, cy, geom -- the pool of
    "network-connected" AGEBs used by the two_tier and frontier anchor modes.
    """
    query = text("""
        SELECT g.cve_ageb, g.coverage_gap_n, g.transit_demand,
               ST_X(ST_Centroid(a.geom)) AS cx,
               ST_Y(ST_Centroid(a.geom)) AS cy,
               a.geom
        FROM features.ageb_coverage_gap g
        JOIN base.ageb a ON a.cvegeo = g.cve_ageb
        WHERE EXISTS (
            SELECT 1 FROM base.gtfs_stops s
            WHERE ST_DWithin(s.geom, ST_Centroid(a.geom), :r)
        )
    """)
    with engine.connect() as conn:
        gdf = gpd.read_postgis(query, conn, geom_col="geom", params={"r": radius_m},
                               crs="EPSG:6372")
    for col in ("coverage_gap_n", "transit_demand", "cx", "cy"):
        gdf[col] = gdf[col].astype(float)
    return gdf


def add_network_anchors(anchors_gdf, connected_gdf, max_tie_in_m: float = 5000.0):
    """two_tier (Approach A): inject one network-connected AGEB per corridor group.

    For each group, pick the connected AGEB nearest to ANY anchor in that group
    (cheapest network entry). Inject it as a role="network" anchor iff that nearest
    distance <= max_tie_in_m and it is not already an anchor in the group. Groups with
    no connected AGEB in range are returned in fallback_group_ids (caller applies hub
    injection). Existing anchors are tagged role="demand".

    Returns (augmented_gdf, fallback_group_ids: set[int]).
    """
    from scipy.spatial import cKDTree

    out = anchors_gdf.copy()
    out["role"] = "demand"
    if len(anchors_gdf) == 0 or len(connected_gdf) == 0:
        return out, set(int(g) for g in out.get("corridor_group", pd.Series([], dtype=int)).unique())

    # Use the anchors' active geometry column name (prod: "geom", tests: "geometry")
    # so the concat below stays single-geometry-column.
    gname = anchors_gdf.geometry.name
    tree = cKDTree(connected_gdf[["cx", "cy"]].values)
    new_rows = []
    fallback = set()
    for gid, sub in anchors_gdf.groupby("corridor_group"):
        dist, idx = tree.query(sub[["cx", "cy"]].values, k=1)
        best = int(dist.argmin())
        best_dist = float(dist[best])
        conn_row = connected_gdf.iloc[int(idx[best])]
        if best_dist > max_tie_in_m or conn_row["cve_ageb"] in set(sub["cve_ageb"]):
            if best_dist > max_tie_in_m:
                fallback.add(int(gid))
            continue
        new_rows.append({
            "cve_ageb": conn_row["cve_ageb"],
            "corridor_group": int(gid),
            "coverage_gap_n": float(conn_row["coverage_gap_n"]),
            "transit_demand": float(conn_row["transit_demand"]),
            "cx": float(conn_row["cx"]),
            "cy": float(conn_row["cy"]),
            gname: conn_row.geometry,
            "role": "network",
        })

    if new_rows:
        add_gdf = gpd.GeoDataFrame(new_rows, geometry=gname, crs=anchors_gdf.crs)
        out = pd.concat([out, add_gdf], ignore_index=True)
        out = gpd.GeoDataFrame(out, geometry=gname, crs=anchors_gdf.crs)
    return out, fallback
```

Note: `make_grouped_anchors` in the test builds geometry via `geometry=[Point(...)]` (active geometry column named `geometry`), matching the `out["geometry"]` usage above.

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest tests/test_w6_anchors.py -k add_network_anchors -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/w6_anchors.py tests/test_w6_anchors.py
git commit -m "feat(w6): two_tier anchor mode primitives (network-connected AGEBs + injection)"
```

---

### Task 3: `frontier` selection (seam anchor pool)

**Files:**
- Modify: `src/w6_anchors.py` (add one function)
- Test: `tests/test_w6_anchors.py` (add cases)

**Interfaces:**
- Consumes: `scipy.spatial.cKDTree`; `make_connected_gdf`/`make_anchor_gdf` test helpers from Task 2.
- Produces: `select_frontier_anchors(anchors_gdf, connected_gdf, radius_m: float = 400.0) -> gpd.GeoDataFrame` — keeps only anchors whose centroid is within `radius_m` of any network-connected AGEB centroid; index reset.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_w6_anchors.py
from src.w6_anchors import select_frontier_anchors


def test_select_frontier_keeps_seam_drops_interior():
    anchors = make_anchor_gdf([0.9, 0.95, 1.0], [800.0, 800.0, 800.0])
    # anchors at x=0,1000,2000. Connected AGEB sits at x=1100 (100m from A1).
    connected = make_connected_gdf([("C", 1100.0, 0.0)])
    out = select_frontier_anchors(anchors, connected, radius_m=400.0)
    assert out["cve_ageb"].tolist() == ["A001"]   # only the seam anchor near C


def test_select_frontier_empty_when_no_connected():
    anchors = make_anchor_gdf([0.9, 0.95], [800.0, 800.0])
    empty = make_connected_gdf([])
    out = select_frontier_anchors(anchors, empty, radius_m=400.0)
    assert len(out) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/test_w6_anchors.py -k frontier -v`
Expected: FAIL with `ImportError: cannot import name 'select_frontier_anchors'`.

- [ ] **Step 3: Implement**

Add to `src/w6_anchors.py`:

```python
def select_frontier_anchors(anchors_gdf, connected_gdf, radius_m: float = 400.0):
    """frontier (Approach B): keep only anchors on the served/unserved seam.

    An anchor survives iff its centroid is within radius_m of a network-connected
    AGEB centroid. Deep-interior high-gap anchors (far from any connected AGEB) are
    dropped -- the mode's defining trade-off. Returns a reset-index GeoDataFrame.
    """
    from scipy.spatial import cKDTree

    if len(anchors_gdf) == 0 or len(connected_gdf) == 0:
        return anchors_gdf.iloc[0:0].copy()
    tree = cKDTree(connected_gdf[["cx", "cy"]].values)
    dist, _ = tree.query(anchors_gdf[["cx", "cy"]].values, k=1)
    keep = dist <= radius_m
    return anchors_gdf[keep].copy().reset_index(drop=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest tests/test_w6_anchors.py -k frontier -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full anchor + merit test suite**

Run: `source .venv/bin/activate && pytest tests/test_w6_anchors.py tests/test_w8_corridor_merit.py -q`
Expected: all pass (13 existing anchor + 4 new anchor + 1 merit).

- [ ] **Step 6: Commit**

```bash
git add src/w6_anchors.py tests/test_w6_anchors.py
git commit -m "feat(w6): frontier anchor mode (seam selection)"
```

---

### Task 4: Comparison harness `src/w6_anchor_experiment.py`

**Files:**
- Create: `src/w6_anchor_experiment.py`
- (No test file — this is an integration orchestrator exercised by the live run in Task 5; its pure inputs are already unit-tested in Tasks 1-3.)

**Interfaces:**
- Consumes: `w6_anchors` (`load_gap_agebs, select_anchors_jenks, cluster_anchors, load_gtfs_stops, select_group_hubs, network_connected_agebs, add_network_anchors, select_frontier_anchors, N_ANCHORS, N_CORRIDORS`), `w6_graph` (`load_or_download_osm, project_to_6372, snap_to_osm_nodes, build_corridor_path`), `w6_candidates.build_route_candidate`, `w5_*` evaluation, `w6_mode.assign_mode/BRT_THRESHOLD/LRT_THRESHOLD`, `w8_corridor_merit.build_merit_baselines/score_corridor`.
- Produces: `outputs/w6_experiment/<mode>/{corridor_candidates.geojson, corridor_scores.csv}` and `outputs/w6_experiment/comparison.md`. Entry point `python src/w6_anchor_experiment.py`.

- [ ] **Step 1: Create the harness file**

```python
"""
W6 Anchor-Level Network Connection -- 3-way comparison harness.

Runs corridor generation under three anchor modes and scores each on the W8
Question-B merit axes (need / non-redundancy / demand-per-km + feasibility):

  baseline  -- Jenks high-gap anchors + KMeans + near/far bare-stop hub injection
               (the incumbent committed logic).
  two_tier  -- baseline anchors + one nearest network-connected AGEB per group as a
               role="network" tie-in (no bare-stop hubs; hub fallback for out-of-range
               groups).
  frontier  -- high-gap anchor pool restricted to the served/unserved seam
               (within 400m of a connected AGEB) before clustering; no hubs.

READ-ONLY against the DB: never writes features.route_candidates. Outputs go only to
outputs/w6_experiment/.

Run (WSL, venv active): python src/w6_anchor_experiment.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geopandas as gpd
import pandas as pd
from scipy.spatial import cKDTree
from sqlalchemy import create_engine

from config import PG_URI
from src.w5_constraints import check_constraints
from src.w5_objective import evaluate_objective, load_ageb_context
from src.w5_types import W5Config
from src.w6_anchors import (
    N_ANCHORS, N_CORRIDORS, add_network_anchors, cluster_anchors, load_gap_agebs,
    load_gtfs_stops, network_connected_agebs, select_anchors_jenks,
    select_frontier_anchors, select_group_hubs,
)
from src.w6_candidates import build_route_candidate
from src.w6_graph import (
    build_corridor_path, load_or_download_osm, project_to_6372, snap_to_osm_nodes,
)
from src.w6_mode import BRT_THRESHOLD, LRT_THRESHOLD, assign_mode
from src.w8_corridor_merit import build_merit_baselines, score_corridor

MODES = ["baseline", "two_tier", "frontier"]
OUT = Path("outputs/w6_experiment")
CONNECT_M = 400.0


def _hub_terminals(anchors_sub, stops_df, G_proj):
    """Return {group_id: [near_node, far_node]} for the given anchor subset."""
    hubs = select_group_hubs(anchors_sub, stops_df)
    if len(hubs) == 0:
        return {}
    gids = [int(r.corridor_group) for r in hubs.itertuples(index=False)]
    near = snap_to_osm_nodes(G_proj, [r.hub_cx for r in hubs.itertuples(index=False)],
                             [r.hub_cy for r in hubs.itertuples(index=False)])
    far = snap_to_osm_nodes(G_proj, [r.far_hub_cx for r in hubs.itertuples(index=False)],
                            [r.far_hub_cy for r in hubs.itertuples(index=False)])
    return {g: [n, f] for g, n, f in zip(gids, near, far)}


def build_anchor_terminals(mode, gap_gdf, connected_gdf, stops_df, G_proj):
    """Return (terminals_by_group: {gid: [osm_nodes]}, anchors_gdf) for a mode."""
    anchors = select_anchors_jenks(gap_gdf, k_classes=5, min_demand=500.0)
    if mode == "frontier":
        anchors = select_frontier_anchors(anchors, connected_gdf, radius_m=CONNECT_M)
    if len(anchors) > N_ANCHORS:
        anchors = anchors.nlargest(N_ANCHORS, "coverage_gap_n").reset_index(drop=True)
    if len(anchors) == 0:
        return {}, anchors
    anchors = cluster_anchors(anchors, n_corridors=N_CORRIDORS)
    anchors["role"] = "demand"

    hub_groups = set()
    if mode == "baseline":
        hub_groups = set(int(g) for g in anchors["corridor_group"].unique())
    elif mode == "two_tier":
        anchors, fallback = add_network_anchors(anchors, connected_gdf)
        hub_groups = fallback

    anchors = anchors.copy()
    anchors["osm_node"] = snap_to_osm_nodes(G_proj, anchors["cx"].tolist(),
                                            anchors["cy"].tolist())

    hub_osm = {}
    if hub_groups:
        sub = anchors[anchors["corridor_group"].isin(hub_groups)]
        hub_osm = _hub_terminals(sub, stops_df, G_proj)

    terminals = {}
    for gid, grp in anchors.groupby("corridor_group"):
        nodes = grp["osm_node"].tolist()
        if int(gid) in hub_osm:
            nodes = nodes + hub_osm[int(gid)]
        terminals[int(gid)] = nodes
    return terminals, anchors


def generate_mode(mode, engine, G_proj, gap_gdf, connected_gdf, stops_df, stop_tree,
                  cfg, baselines):
    print(f"\n[{mode}] generating corridors...")
    terminals, _ = build_anchor_terminals(mode, gap_gdf, connected_gdf, stops_df, G_proj)
    rows, geoms = [], []
    for gid in sorted(terminals):
        geom, route_km = build_corridor_path(G_proj, terminals[gid])
        if geom is None or route_km <= 0.01:
            continue
        cid = f"{mode}_G{gid:02d}"
        rc = build_route_candidate(cid, geom, engine, config=cfg, route_km_override=route_km)
        if rc is None:
            continue
        ctxs = load_ageb_context(rc.served_ageb_ids, engine)
        obj = evaluate_objective(rc, ctxs, cfg)
        cr = check_constraints(rc, ctxs, cfg)
        td = sum(c.transit_demand for c in ctxs)
        merit = score_corridor(geom, route_km, td, baselines)
        ep = stop_tree.query([geom.coords[0], geom.coords[-1]], k=1)[0]
        rows.append({
            "candidate_id": cid, "corridor_group": gid,
            "route_km": float(route_km), "n_served_agebs": len(rc.served_ageb_ids),
            "total_demand": float(td), "f1_demand_gain": float(obj.f1_demand_gain),
            "f3_equity": float(obj.f3_equity), "total_score": float(obj.total_score),
            "feasible": bool(cr.feasible),
            "mode_assignment": assign_mode(td, BRT_THRESHOLD, LRT_THRESHOLD),
            "endpoints_connected": bool((ep <= CONNECT_M).all()),
            "hi_share": merit["hi_share"], "best_jaccard": merit["best_jaccard"],
            "redundant": merit["redundant"], "dpk_pct": merit["dpk_pct"],
            "merit_passed": merit["passed"],
        })
        geoms.append(geom)
        print(f"  {cid}: {route_km:.1f}km served={len(rc.served_ageb_ids)} "
              f"demand={td:.0f} feasible={cr.feasible} "
              f"endpoints_connected={rows[-1]['endpoints_connected']} "
              f"merit_pass={merit['passed']}")

    mode_dir = OUT / mode
    mode_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(mode_dir / "corridor_scores.csv", index=False)
    if geoms:
        gdf = gpd.GeoDataFrame(rows, geometry=geoms, crs="EPSG:6372").to_crs("EPSG:4326")
        gdf.to_file(mode_dir / "corridor_candidates.geojson", driver="GeoJSON")
    return rows


def write_comparison(all_rows, baselines):
    lines = [
        "# W6 Anchor Mode Comparison (baseline / two_tier / frontier)",
        "",
        f"Metro High-gap baseline share: {baselines.metro_hi_share:.1%}. "
        "demand/km pass = >= 50th pct of existing routes; non-redundant = best Jaccard < 0.60.",
        "",
        "| Mode | Corridors | Feasible | Endpoints connected | Mean High-gap share | "
        "All non-redundant | Mean demand/km pct | Merit-pass |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for mode in MODES:
        rows = all_rows[mode]
        feas = [r for r in rows if r["feasible"]]
        n_conn = sum(1 for r in feas if r["endpoints_connected"])
        mean_hi = (sum(r["hi_share"] for r in feas) / len(feas)) if feas else float("nan")
        all_uniq = all(not r["redundant"] for r in feas) if feas else True
        mean_pct = (sum(r["dpk_pct"] for r in feas) / len(feas)) if feas else float("nan")
        n_pass = sum(1 for r in feas if r["merit_passed"])
        conn_txt = f"{n_conn}/{len(feas)}" if feas else "0/0"
        lines.append(
            f"| {mode} | {len(rows)} | {len(feas)} | {conn_txt} | {mean_hi:.1%} | "
            f"{all_uniq} | {mean_pct:.0f} | {n_pass}/{len(feas)} |"
        )
    lines += [
        "",
        "## Per-corridor detail",
        "",
        "| Mode | ID | km | Served | Demand | Feasible | Endpts conn | High-gap | "
        "Jaccard | demand/km pct | Merit pass |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for mode in MODES:
        for r in all_rows[mode]:
            lines.append(
                f"| {mode} | {r['candidate_id']} | {r['route_km']:.1f} | "
                f"{r['n_served_agebs']} | {r['total_demand']:.0f} | {r['feasible']} | "
                f"{r['endpoints_connected']} | {r['hi_share']:.1%} | "
                f"{r['best_jaccard']:.2f} | {r['dpk_pct']:.0f} | {r['merit_passed']} |"
            )
    lines += [
        "",
        "## Notes",
        "",
        "- baseline injects bare GTFS stops as MST terminals (routing-level connection).",
        "- two_tier / frontier inject a supply-side signal into anchor SELECTION; the",
        "  'Mean High-gap share' and 'demand/km pct' columns show how much corridor merit",
        "  each buys relative to the pure-demand baseline. Weigh realism vs the clean",
        "  'generate purely from the demand gap' story when choosing a mode.",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[OK] comparison written: {OUT / 'comparison.md'}")


def main():
    engine = create_engine(PG_URI)
    try:
        cfg = W5Config()
        print("[Load] merit baselines + coverage gap + connected AGEBs + stops...")
        baselines = build_merit_baselines(engine)
        gap_gdf = load_gap_agebs(engine)
        connected_gdf = network_connected_agebs(engine, radius_m=CONNECT_M)
        stops_df = load_gtfs_stops(engine)
        stop_tree = cKDTree(stops_df[["cx", "cy"]].values)
        print(f"  gap AGEBs={len(gap_gdf)}, connected AGEBs={len(connected_gdf)}, "
              f"stops={len(stops_df)}")

        G_proj = project_to_6372(load_or_download_osm())
        print(f"  OSM graph: {G_proj.number_of_nodes()} nodes")

        all_rows = {}
        for mode in MODES:
            all_rows[mode] = generate_mode(
                mode, engine, G_proj, gap_gdf, connected_gdf, stops_df, stop_tree,
                cfg, baselines,
            )
        write_comparison(all_rows, baselines)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Import-smoke the harness (no full run yet)**

Run: `source .venv/bin/activate && python -c "import src.w6_anchor_experiment as m; print('import ok', m.MODES)"`
Expected: `import ok ['baseline', 'two_tier', 'frontier']` (verifies every imported name resolves against the real modules).

- [ ] **Step 3: Commit**

```bash
git add src/w6_anchor_experiment.py
git commit -m "feat(w6): 3-way anchor-mode comparison harness (read-only, no route_candidates write)"
```

---

### Task 5: Live run, populate comparison, verify success criteria

**Files:**
- Generated: `outputs/w6_experiment/comparison.md`, `outputs/w6_experiment/<mode>/*`
- Modify: `CLAUDE.md` (append a dated W6/W8 entry per the existing errata/re-run pattern)

**Interfaces:**
- Consumes: everything from Tasks 1-4; the live `gdl_metro` DB and cached `data/osm_zmg_drive.graphml`.
- Produces: a populated comparison report and a documented finding.

- [ ] **Step 1: Confirm route_candidates is untouched before the run**

Run: `source .venv/bin/activate && psql -h localhost -d gdl_metro -c "SELECT count(*) FROM features.route_candidates;"`
Record the count (expected 6 from the last canonical W6 run).

- [ ] **Step 2: Run the harness end-to-end**

Run: `source .venv/bin/activate && python src/w6_anchor_experiment.py`
Expected: per-mode generation logs for `baseline`, `two_tier`, `frontier`, then `[OK] comparison written`. No errors, no INSERTs.

- [ ] **Step 3: Verify route_candidates is still untouched (isolation invariant)**

Run: `source .venv/bin/activate && psql -h localhost -d gdl_metro -c "SELECT count(*) FROM features.route_candidates;"`
Expected: identical count to Step 1. If it changed, the harness violated read-only — stop and fix before proceeding.

- [ ] **Step 4: Verify the realism success criterion (A/B fully connected)**

Open `outputs/w6_experiment/comparison.md`. Confirm that for `two_tier` and `frontier`, the "Endpoints connected" column reads `N/N` (100% of feasible corridors connected). If not, inspect per-corridor rows: a two_tier group in hub-fallback should still connect; a frontier corridor that isn't connected indicates the seam radius is too loose — note it as a finding (do not silently relax).

- [ ] **Step 5: Sanity-read the comparison and write the finding into CLAUDE.md**

Append a dated entry (`## W6/W8 -- anchor-mode comparison (2026-07-15)`) to `CLAUDE.md` following the existing re-run note style: which mode produced the most feasible + connected + high-merit corridors, the mean High-gap share vs the 20.7% baseline per mode, and the explicit trade-off (supply-side signal injected into generation). State plainly which mode (if any) beats baseline on merit — this is the deciding output for choosing a mode.

- [ ] **Step 6: Commit outputs + doc**

```bash
git add outputs/w6_experiment CLAUDE.md
git commit -m "run(w6): 3-way anchor-mode comparison results + finding"
```

---

## Notes for the implementer

- `build_corridor_path`, `snap_to_osm_nodes`, `build_route_candidate`, and the W5/W6 helpers are already exercised by `run_w6.py` — read `src/run_w6.py` Steps 4b-11 (lines 254-383) for the canonical call sequence the harness mirrors.
- The OSM graph is cached at `data/osm_zmg_drive.graphml`; the first `load_or_download_osm()` in a clean environment can be slow but subsequent runs are fast.
- If `two_tier`/`frontier` yield zero feasible corridors on the live DB, that is a **valid finding**, not a failure — report per-mode `route_km`/feasibility exactly as the hub-connectivity spec's contingency note prescribes, rather than relaxing W5 caps to force output.
