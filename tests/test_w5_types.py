# tests/test_w5_types.py
import pytest
from src.w5_types import (
    W5Config, RouteCandidate, AgebContext,
    ObjectiveResult, ConstraintViolation, ConstraintResult,
)


def test_w5_config_defaults():
    cfg = W5Config()
    assert cfg.max_detour_ratio == 1.8
    assert cfg.min_stop_spacing_m == 300.0
    assert cfg.max_stop_spacing_m == 1000.0
    assert cfg.min_daily_demand == 500.0
    assert cfg.max_route_km == 30.0
    assert cfg.transfer_penalty == 0.10
    assert cfg.connected_gain_factor == 0.50
    assert cfg.isolated_gain_factor == 0.20


def test_w5_config_weights_sum_to_one():
    cfg = W5Config()
    total = cfg.w_demand_gain + cfg.w_efficiency + cfg.w_equity
    assert abs(total - 1.0) < 1e-9


def test_route_candidate_instantiation():
    rc = RouteCandidate(
        candidate_id="test_A",
        served_ageb_ids=["140010010010", "140010010020"],
        route_km=5.0,
        n_stops=10,
        straight_line_km=4.0,
        connects_to_existing=True,
    )
    assert rc.candidate_id == "test_A"
    assert len(rc.served_ageb_ids) == 2
    assert rc.connects_to_existing is True


def test_ageb_context_instantiation():
    ctx = AgebContext(
        cvegeo="140010010010",
        transit_demand=850.0,
        unserved_fraction=0.75,
        equity_score=0.62,
    )
    assert ctx.cvegeo == "140010010010"
    assert ctx.unserved_fraction == 0.75


def test_constraint_result_feasible_when_no_violations():
    cr = ConstraintResult(feasible=True, violations=[])
    assert cr.feasible is True
    assert cr.violations == []


def test_constraint_result_infeasible_with_violation():
    v = ConstraintViolation(
        name="detour_ratio",
        value=2.1,
        limit=1.8,
        message="Detour ratio 2.10 exceeds max 1.8",
    )
    cr = ConstraintResult(feasible=False, violations=[v])
    assert cr.feasible is False
    assert cr.violations[0].name == "detour_ratio"
