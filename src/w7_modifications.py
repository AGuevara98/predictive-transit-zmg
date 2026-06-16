"""
W7.3 -- Modification Proposer
===============================
For each flagged route, proposes one of three modifications:

    'shortcut' -- if Indirect (detour_ratio > 1.5): propose straight-line
                  shortcut between the two highest-demand AGEBs on the route;
                  estimate new route_km and new score.
    'merge'    -- if Redundant: flag the pair for merger; report overlap %.
    'retire'   -- if Low demand AND Redundant: recommend retirement.

Each proposal is a dict with:
    route_id, modification_type, reason, current_score,
    proposed_score (float or None), overlap_route_id (str or None),
    detail (human-readable explanation)
"""
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.w5_constraints import check_constraints
from src.w5_objective import evaluate_objective, load_ageb_context
from src.w5_types import AgebContext, RouteCandidate, W5Config

INDIRECT_DETOUR_THRESH = 1.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _straight_km_between_agebs(ctx_a: AgebContext, ctx_b: AgebContext) -> float:
    """
    We do not have coordinates here -- use a heuristic:
    assume average AGEB diameter ~0.7 km so the straight-line between
    the two highest-demand AGEBs on a route spans roughly
    (n_served_agebs / 2) * 0.7 km.
    This is purely an estimate used for proposed_score computation.
    """
    return 0.7  # km


def _estimate_shortcut_route_km(
    current_route_km: float,
    straight_line_km: float,
) -> float:
    """
    Estimate shortcut length as 1.1 * straight_line_km (10% road detour
    tolerance above Euclidean distance).
    """
    return round(straight_line_km * 1.1, 2)


def _build_shortcut_candidate(
    route_id: str,
    proposed_km: float,
    n_stops: int,
    straight_line_km: float,
    connects_to_existing: bool,
    served_ageb_ids: List[str],
) -> RouteCandidate:
    return RouteCandidate(
        candidate_id=f"{route_id}_shortcut",
        served_ageb_ids=served_ageb_ids,
        route_km=proposed_km,
        n_stops=max(n_stops, 2),
        straight_line_km=straight_line_km,
        connects_to_existing=connects_to_existing,
    )


def _compute_jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 0.0
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return len(set_a & set_b) / union


# ---------------------------------------------------------------------------
# Main proposer
# ---------------------------------------------------------------------------

def propose_modifications(
    scored_df: pd.DataFrame,
    engine=None,
    config: Optional[W5Config] = None,
) -> List[Dict[str, Any]]:
    """
    Generate modification proposals for all flagged routes.

    Parameters
    ----------
    scored_df : DataFrame from w7_route_scorer.score_all_routes()
        Must have columns: route_id, flag, overlap_route_id, total_score,
        detour_ratio, route_km, straight_line_km, n_stops, connects_to_existing,
        n_served_agebs, served_agebs (pipe-separated cve_ageb list).
    engine : SQLAlchemy engine (optional; needed to compute proposed_score for shortcuts)
    config : W5Config (defaults to standard config)
    """
    if config is None:
        config = W5Config()

    flagged = scored_df[scored_df["flag"].notna()].copy()
    proposals: List[Dict[str, Any]] = []

    for _, row in flagged.iterrows():
        rid = str(row["route_id"])
        flag = str(row["flag"])
        current_score = float(row["total_score"])
        overlap_id = row.get("overlap_route_id", None)
        if pd.isna(overlap_id):
            overlap_id = None

        # --- Determine modification type ---
        if flag == "Low demand" and overlap_id is not None:
            # Low demand AND redundant -> retire
            mod_type = "retire"
            reason = (
                f"Route has low demand-gain (f1={row['f1_demand_gain']:.3f}) "
                f"and is redundant with {overlap_id}. "
                "Retirement frees capacity without net coverage loss."
            )
            proposals.append({
                "route_id": rid,
                "modification_type": mod_type,
                "reason": reason,
                "current_score": current_score,
                "proposed_score": None,
                "overlap_route_id": overlap_id,
                "detail": f"Retire {rid}; redirect resources to {overlap_id}.",
            })

        elif flag == "Redundant":
            # Redundant but not low-demand -> merge proposal
            mod_type = "merge"
            # Compute overlap percentage
            served_a = set(str(row["served_agebs"]).split("|")) if row["served_agebs"] else set()
            overlap_row = scored_df[scored_df["route_id"] == overlap_id]
            if not overlap_row.empty:
                served_b = set(
                    str(overlap_row.iloc[0]["served_agebs"]).split("|")
                    if overlap_row.iloc[0]["served_agebs"] else ""
                )
                jaccard = _compute_jaccard(served_a, served_b)
                overlap_pct = round(jaccard * 100, 1)
            else:
                overlap_pct = 0.0
            reason = (
                f"Route overlaps {overlap_pct}% of served AGEBs with {overlap_id} "
                f"(Jaccard={overlap_pct/100:.2f}). Consolidation improves frequency "
                "without expanding coverage."
            )
            proposals.append({
                "route_id": rid,
                "modification_type": mod_type,
                "reason": reason,
                "current_score": current_score,
                "proposed_score": None,
                "overlap_route_id": overlap_id,
                "detail": (
                    f"Merge {rid} into {overlap_id}; "
                    f"combine headways to improve service frequency."
                ),
            })

        elif flag == "Indirect":
            # Indirect -> shortcut proposal
            mod_type = "shortcut"
            proposed_km = _estimate_shortcut_route_km(
                float(row["route_km"]),
                float(row["straight_line_km"]),
            )
            proposed_score: Optional[float] = None

            # Try to compute proposed score if engine is available
            if engine is not None:
                try:
                    served_ids = [s for s in str(row["served_agebs"]).split("|") if s]
                    ctxs = load_ageb_context(served_ids, engine)
                    n_stops = int(row["n_stops"])
                    shortcut_rc = _build_shortcut_candidate(
                        rid,
                        proposed_km,
                        n_stops,
                        float(row["straight_line_km"]),
                        bool(row["connects_to_existing"]),
                        served_ids,
                    )
                    obj = evaluate_objective(shortcut_rc, ctxs, config)
                    proposed_score = round(float(obj.total_score), 4)
                except Exception:
                    proposed_score = None

            reason = (
                f"Route detour_ratio={row['detour_ratio']:.2f} > {INDIRECT_DETOUR_THRESH}. "
                f"Current route_km={row['route_km']:.1f}km; "
                f"estimated shortcut={proposed_km:.1f}km "
                f"(straight_line_km={row['straight_line_km']:.1f}km x 1.1)."
            )
            proposals.append({
                "route_id": rid,
                "modification_type": mod_type,
                "reason": reason,
                "current_score": current_score,
                "proposed_score": proposed_score,
                "overlap_route_id": None,
                "detail": (
                    f"Replace detoured alignment with direct route "
                    f"between highest-demand endpoints (~{proposed_km:.1f}km)."
                ),
            })

        elif flag == "Low demand":
            # Low demand, not redundant -> no concrete merge target; suggest review
            mod_type = "retire"
            reason = (
                f"Route has low demand-gain (f1={row['f1_demand_gain']:.3f}, "
                f"score={current_score:.3f}) with no high-scoring overlapping route. "
                "Consider service reduction or rerouting to higher-demand corridor."
            )
            proposals.append({
                "route_id": rid,
                "modification_type": mod_type,
                "reason": reason,
                "current_score": current_score,
                "proposed_score": None,
                "overlap_route_id": None,
                "detail": (
                    f"Reduce frequency or retire {rid}; "
                    "reallocate vehicles to higher-demand routes."
                ),
            })

    print(f"  [OK] {len(proposals)} modification proposals generated")
    return proposals
