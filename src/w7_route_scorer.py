"""
W7.2 -- Route Scorer
=====================
Scores every GTFS route using the W5 multi-objective function, checks
constraints, computes Pareto rank, and assigns audit flags.

Flags (not mutually exclusive; priority order applied for single flag):
    'Low demand'  -- f1_demand_gain < 0.2 AND total_score < 0.3
    'Indirect'    -- detour_ratio > 1.5
    'Redundant'   -- served-AGEB Jaccard overlap >= 0.60 with a higher-scoring route

Redundancy uses the first higher-scoring route it finds (by total_score).
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.w5_constraints import check_constraints
from src.w5_objective import evaluate_objective, load_ageb_context
from src.w5_pareto import pareto_rank
from src.w5_types import AgebContext, ConstraintResult, ObjectiveResult, RouteCandidate, W5Config

WALK_BUFFER_M = 400.0
LOW_DEMAND_F1_THRESH = 0.2
LOW_DEMAND_SCORE_THRESH = 0.3
INDIRECT_DETOUR_THRESH = 1.5
REDUNDANCY_JACCARD_THRESH = 0.60


# ---------------------------------------------------------------------------
# Spatial: find served AGEBs per route
# ---------------------------------------------------------------------------

def get_served_agebs_for_route(
    route_id: str,
    geom: LineString,
    engine,
    buffer_m: float = WALK_BUFFER_M,
) -> List[str]:
    """Return cve_ageb list of AGEBs whose centroid is within buffer_m of route."""
    query = text("""
        SELECT a.cvegeo
        FROM base.ageb a
        WHERE ST_DWithin(
            ST_Centroid(a.geom),
            ST_GeomFromText(:wkt, 6372),
            :buf
        )
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"wkt": geom.wkt, "buf": buffer_m}).fetchall()
    return [str(r.cvegeo) for r in rows]


# ---------------------------------------------------------------------------
# Build RouteCandidate from GDF row
# ---------------------------------------------------------------------------

def route_to_candidate(
    route_id: str,
    route_km: float,
    n_stops: int,
    straight_line_km: float,
    connects_to_existing: bool,
    served_ageb_ids: List[str],
) -> RouteCandidate:
    return RouteCandidate(
        candidate_id=route_id,
        served_ageb_ids=served_ageb_ids,
        route_km=route_km,
        n_stops=max(n_stops, 2),
        straight_line_km=straight_line_km,
        connects_to_existing=connects_to_existing,
    )


# ---------------------------------------------------------------------------
# Flagging
# ---------------------------------------------------------------------------

def compute_detour_ratio(route_km: float, straight_line_km: float) -> float:
    if straight_line_km <= 0:
        return 1.0
    return route_km / straight_line_km


def jaccard_overlap(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return intersection / union


def assign_flags(
    route_records: List[Dict],
) -> List[Tuple[Optional[str], Optional[str]]]:
    """
    For each record in route_records (sorted by evaluation order), return
    (flag, overlap_route_id). Records must have:
        route_id, total_score, f1_demand_gain, detour_ratio, served_ageb_ids (set)

    Priority: Redundant > Indirect > Low demand > None
    (A route that is both redundant and indirect gets 'Redundant'.)
    """
    # Sort by total_score descending to establish dominance for redundancy check
    scored = sorted(route_records, key=lambda r: r["total_score"], reverse=True)

    # Build index: route_id -> position in scored list
    pos_map = {r["route_id"]: i for i, r in enumerate(scored)}

    result_map: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

    for i, rec in enumerate(scored):
        rid = rec["route_id"]
        ageb_set = rec["served_ageb_ids"]
        detour = rec["detour_ratio"]
        f1 = rec["f1_demand_gain"]
        score = rec["total_score"]

        flag: Optional[str] = None
        overlap_id: Optional[str] = None

        # Check redundancy against all higher-scoring routes
        for j, other in enumerate(scored):
            if j >= i:
                break  # only higher-scoring routes
            jaccard = jaccard_overlap(ageb_set, other["served_ageb_ids"])
            if jaccard >= REDUNDANCY_JACCARD_THRESH:
                flag = "Redundant"
                overlap_id = other["route_id"]
                break

        if flag is None:
            if detour > INDIRECT_DETOUR_THRESH:
                flag = "Indirect"
            elif f1 < LOW_DEMAND_F1_THRESH and score < LOW_DEMAND_SCORE_THRESH:
                flag = "Low demand"

        result_map[rid] = (flag, overlap_id)

    # Return in original input order
    return [(result_map[r["route_id"]]) for r in route_records]


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------

def score_all_routes(
    routes_gdf: gpd.GeoDataFrame,
    engine,
    config: Optional[W5Config] = None,
) -> pd.DataFrame:
    """
    Score all routes in routes_gdf against W5 objective function.

    Returns a DataFrame with one row per route including scores, flags,
    detour_ratio, and served_ageb_ids (as pipe-separated string in 'served_agebs').
    """
    if config is None:
        config = W5Config()

    print(f"[Score] Scoring {len(routes_gdf)} routes...")

    # Step 1: collect served AGEBs for all routes
    print("[Score] Step 1 -- collecting served AGEBs per route...")
    served_map: Dict[str, List[str]] = {}
    for idx, row in routes_gdf.iterrows():
        rid = row["route_id"]
        served = get_served_agebs_for_route(rid, row["geometry"], engine)
        served_map[rid] = served

    # Step 2: load all AGEB contexts in one batch
    all_ageb_ids = list({aid for ids in served_map.values() for aid in ids})
    print(f"[Score] Step 2 -- loading context for {len(all_ageb_ids)} unique AGEBs...")
    ctx_list = load_ageb_context(all_ageb_ids, engine)
    ctx_map: Dict[str, AgebContext] = {c.cvegeo: c for c in ctx_list}

    # Step 3: evaluate objectives and constraints
    print("[Score] Step 3 -- evaluating objectives and constraints...")
    objectives: List[ObjectiveResult] = []
    constraint_results: List[ConstraintResult] = []
    candidates: List[RouteCandidate] = []

    for _, row in routes_gdf.iterrows():
        rid = row["route_id"]
        served = served_map[rid]
        rc = route_to_candidate(
            route_id=rid,
            route_km=float(row["route_km"]),
            n_stops=int(row["n_stops"]) if int(row["n_stops"]) >= 2 else 2,
            straight_line_km=float(row["straight_line_km"]),
            connects_to_existing=bool(row["connects_to_existing"]),
            served_ageb_ids=served,
        )
        candidates.append(rc)
        ctxs = [ctx_map[aid] for aid in served if aid in ctx_map]
        obj = evaluate_objective(rc, ctxs, config)
        cr = check_constraints(rc, ctxs, config)
        objectives.append(obj)
        constraint_results.append(cr)

    # Step 4: Pareto rank
    print("[Score] Step 4 -- Pareto ranking...")
    ranks = pareto_rank(objectives)

    # Step 5: Assemble pre-flag records
    records = []
    for i, (_, row) in enumerate(routes_gdf.iterrows()):
        rid = row["route_id"]
        obj = objectives[i]
        cr = constraint_results[i]
        rc = candidates[i]
        detour = compute_detour_ratio(float(row["route_km"]), float(row["straight_line_km"]))
        records.append({
            "route_id": rid,
            "route_short_name": row["route_short_name"],
            "route_long_name": row["route_long_name"],
            "route_km": float(row["route_km"]),
            "n_stops": int(rc.n_stops),
            "straight_line_km": float(row["straight_line_km"]),
            "detour_ratio": round(detour, 3),
            "connects_to_existing": bool(row["connects_to_existing"]),
            "f1_demand_gain": float(obj.f1_demand_gain),
            "f2_route_km": float(obj.f2_route_km),
            "f3_equity": float(obj.f3_equity),
            "composite_score": float(obj.composite_score),
            "total_score": float(obj.total_score),
            "pareto_rank": int(ranks[i]),
            "feasible": bool(cr.feasible),
            "violations": [v.message for v in cr.violations],
            "served_ageb_ids": set(served_map[rid]),
            "n_served_agebs": len(served_map[rid]),
        })

    # Step 5: assign flags
    print("[Score] Step 5 -- assigning audit flags...")
    flag_results = assign_flags(records)
    for rec, (flag, overlap_id) in zip(records, flag_results):
        rec["flag"] = flag
        rec["overlap_route_id"] = overlap_id

    # Clean up: convert set to pipe-separated string for CSV output
    for rec in records:
        rec["served_agebs"] = "|".join(sorted(rec["served_ageb_ids"]))
        del rec["served_ageb_ids"]

    df = pd.DataFrame(records)
    n_flagged = df["flag"].notna().sum()
    print(f"  [OK] {len(df)} routes scored; {n_flagged} flagged")
    return df
