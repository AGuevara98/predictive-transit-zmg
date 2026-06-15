# src/w5_constraints.py
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.w5_types import AgebContext, ConstraintResult, ConstraintViolation, RouteCandidate, W5Config


def check_constraints(
    candidate: RouteCandidate,
    ageb_contexts: List[AgebContext],
    config: W5Config,
) -> ConstraintResult:
    """Return feasibility status and list of all constraint violations."""
    violations: List[ConstraintViolation] = []

    # 1. Detour ratio
    if candidate.straight_line_km > 0:
        detour = candidate.route_km / candidate.straight_line_km
        if detour > config.max_detour_ratio:
            violations.append(ConstraintViolation(
                name="detour_ratio",
                value=round(detour, 3),
                limit=config.max_detour_ratio,
                message=(
                    f"Detour ratio {detour:.2f} exceeds max {config.max_detour_ratio}"
                ),
            ))

    # 2. Stop spacing (requires at least 2 stops to define spacing)
    if candidate.n_stops >= 2:
        spacing_m = (candidate.route_km * 1000.0) / (candidate.n_stops - 1)
        if spacing_m < config.min_stop_spacing_m:
            violations.append(ConstraintViolation(
                name="stop_spacing_min",
                value=round(spacing_m, 1),
                limit=config.min_stop_spacing_m,
                message=(
                    f"Stop spacing {spacing_m:.0f}m below minimum {config.min_stop_spacing_m:.0f}m"
                ),
            ))
        if spacing_m > config.max_stop_spacing_m:
            violations.append(ConstraintViolation(
                name="stop_spacing_max",
                value=round(spacing_m, 1),
                limit=config.max_stop_spacing_m,
                message=(
                    f"Stop spacing {spacing_m:.0f}m above maximum {config.max_stop_spacing_m:.0f}m"
                ),
            ))

    # 3. Minimum daily demand served
    total_demand = sum(c.transit_demand for c in ageb_contexts)
    if total_demand < config.min_daily_demand:
        violations.append(ConstraintViolation(
            name="min_demand",
            value=round(total_demand, 1),
            limit=config.min_daily_demand,
            message=(
                f"Served demand {total_demand:.0f} trips/day < minimum {config.min_daily_demand:.0f}"
            ),
        ))

    # 4. Maximum route length
    if candidate.route_km > config.max_route_km:
        violations.append(ConstraintViolation(
            name="max_route_km",
            value=round(candidate.route_km, 2),
            limit=config.max_route_km,
            message=(
                f"Route length {candidate.route_km:.1f}km exceeds max {config.max_route_km:.1f}km"
            ),
        ))

    return ConstraintResult(feasible=len(violations) == 0, violations=violations)
