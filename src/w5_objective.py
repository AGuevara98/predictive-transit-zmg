# src/w5_objective.py
from typing import List

from sqlalchemy import text

from .w5_types import AgebContext, ObjectiveResult, RouteCandidate, W5Config


def load_ageb_context(cvegeos: List[str], engine) -> List[AgebContext]:
    """Fetch transit_demand, unserved_fraction, equity_score for a set of AGEBs."""
    if not cvegeos:
        return []
    query = text("""
        SELECT
            g.cve_ageb                             AS cvegeo,
            t.transit_demand,
            COALESCE(g.coverage_gap_n, 0)          AS unserved_fraction,
            COALESCE(p.equity_score, 0)            AS equity_score
        FROM features.ageb_coverage_gap g
        JOIN features.ageb_trip_ends t
            ON t.cve_ageb = g.cve_ageb
        LEFT JOIN features.nppv_prioritization p
            ON p.cve_ageb = g.cve_ageb
        WHERE g.cve_ageb = ANY(:ids)
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"ids": list(cvegeos)}).fetchall()
    return [
        AgebContext(
            cvegeo=str(r.cvegeo),
            transit_demand=float(r.transit_demand or 0.0),
            unserved_fraction=float(r.unserved_fraction or 0.0),
            equity_score=float(r.equity_score or 0.0),
        )
        for r in rows
    ]


def evaluate_objective(
    candidate: RouteCandidate,
    ageb_contexts: List[AgebContext],
    config: W5Config,
) -> ObjectiveResult:
    """Compute multi-objective scores for a route candidate (no DB calls)."""
    if not ageb_contexts:
        return ObjectiveResult(
            candidate_id=candidate.candidate_id,
            f1_demand_gain=0.0,
            f2_route_km=candidate.route_km,
            f3_equity=0.0,
            transfer_penalty=0.0,
            composite_score=0.0,
            total_score=0.0,
        )

    gain_factor = (
        config.connected_gain_factor
        if candidate.connects_to_existing
        else config.isolated_gain_factor
    )

    total_demand = sum(c.transit_demand for c in ageb_contexts)
    if total_demand <= 0.0:
        total_demand = 1.0  # zero-demand corridor: gain will be 0 regardless

    # f1: demand-weighted accessibility gain, rescaled to [0, 1] via gain_factor
    weighted_gain = sum(
        c.transit_demand * gain_factor * c.unserved_fraction
        for c in ageb_contexts
    )
    f1_raw = weighted_gain / total_demand          # in [0, gain_factor]
    f1_scaled = f1_raw / gain_factor if gain_factor > 0.0 else 0.0

    # f2: route km (stored raw; composite uses efficiency instead)
    f2 = candidate.route_km

    # f3: mean equity score of served AGEBs
    f3 = sum(c.equity_score for c in ageb_contexts) / len(ageb_contexts)

    # transfer penalty (flat deduction from composite)
    penalty = 0.0 if candidate.connects_to_existing else config.transfer_penalty

    # efficiency: higher score for shorter routes
    if config.max_route_km > 0.0:
        efficiency = max(0.0, 1.0 - f2 / config.max_route_km)
    else:
        efficiency = 0.0

    composite = (
        config.w_demand_gain * f1_scaled
        + config.w_efficiency * efficiency
        + config.w_equity * f3
    )

    return ObjectiveResult(
        candidate_id=candidate.candidate_id,
        f1_demand_gain=f1_raw,          # raw (unscaled) gain stored for Pareto comparisons
        f2_route_km=f2,
        f3_equity=f3,
        transfer_penalty=penalty,
        composite_score=composite,
        total_score=composite - penalty,
    )
