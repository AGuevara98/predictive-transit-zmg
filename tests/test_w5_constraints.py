# tests/test_w5_constraints.py
import pytest
from src.w5_types import W5Config, RouteCandidate, AgebContext
from src.w5_constraints import check_constraints


@pytest.fixture
def cfg():
    return W5Config()


def make_ctx(demand):
    return AgebContext(cvegeo="X", transit_demand=demand,
                       unserved_fraction=0.5, equity_score=0.5)


def make_candidate(route_km, n_stops, straight_km, served_ids=None):
    return RouteCandidate(
        candidate_id="R",
        served_ageb_ids=served_ids or ["A001", "A002"],
        route_km=route_km,
        n_stops=n_stops,
        straight_line_km=straight_km,
    )


def test_feasible_candidate_passes(cfg):
    # detour=8/6=1.33, spacing=7000/13=538m, demand=700, km=8
    candidate = make_candidate(route_km=8.0, n_stops=14, straight_km=6.0)
    contexts = [make_ctx(350.0), make_ctx(350.0)]
    result = check_constraints(candidate, contexts, cfg)
    assert result.feasible is True
    assert result.violations == []


def test_detour_ratio_violation(cfg):
    # detour = 20 / 5 = 4.0 > 1.8
    candidate = make_candidate(route_km=20.0, n_stops=30, straight_km=5.0)
    contexts = [make_ctx(300.0), make_ctx(300.0)]
    result = check_constraints(candidate, contexts, cfg)
    assert not result.feasible
    assert any(v.name == "detour_ratio" for v in result.violations)


def test_anchor_span_overrides_endpoint_detour(cfg):
    # Endpoint detour 12/5 = 2.40 would FAIL, but the corridor efficiently connects a
    # bent anchor set whose straight-line span is 8km -> anchor-directness 12/8 = 1.50,
    # which passes. This is the G02 case: a curved coverage corridor, not wasteful.
    candidate = make_candidate(route_km=12.0, n_stops=25, straight_km=5.0)
    candidate.anchor_span_km = 8.0
    contexts = [make_ctx(700.0), make_ctx(700.0)]
    result = check_constraints(candidate, contexts, cfg)
    assert result.feasible is True
    assert not any(v.name == "detour_ratio" for v in result.violations)


def test_anchor_directness_can_still_violate(cfg):
    # A genuinely wasteful route: 12km to connect anchors that span only 4km straight
    # -> anchor-directness 3.0 > 1.8, flagged even though it is anchor-based.
    candidate = make_candidate(route_km=12.0, n_stops=25, straight_km=10.0)
    candidate.anchor_span_km = 4.0
    contexts = [make_ctx(700.0), make_ctx(700.0)]
    result = check_constraints(candidate, contexts, cfg)
    assert not result.feasible
    assert any(v.name == "detour_ratio" for v in result.violations)


def test_detour_ratio_at_limit_passes(cfg):
    # detour = 9.0 / 5.0 = 1.8 exactly
    candidate = make_candidate(route_km=9.0, n_stops=15, straight_km=5.0)
    contexts = [make_ctx(300.0), make_ctx(300.0)]
    result = check_constraints(candidate, contexts, cfg)
    assert not any(v.name == "detour_ratio" for v in result.violations)


def test_stop_spacing_too_small(cfg):
    # spacing = 1000m / (50-1) = ~20m < 300m
    candidate = make_candidate(route_km=1.0, n_stops=50, straight_km=0.9)
    contexts = [make_ctx(300.0), make_ctx(300.0)]
    result = check_constraints(candidate, contexts, cfg)
    assert any(v.name == "stop_spacing_min" for v in result.violations)


def test_stop_spacing_too_large(cfg):
    # spacing = 10000m / (3-1) = 5000m > 1000m
    candidate = make_candidate(route_km=10.0, n_stops=3, straight_km=9.0)
    contexts = [make_ctx(300.0), make_ctx(300.0)]
    result = check_constraints(candidate, contexts, cfg)
    assert any(v.name == "stop_spacing_max" for v in result.violations)


def test_min_demand_violation(cfg):
    # total demand = 100 < 500
    candidate = make_candidate(route_km=5.0, n_stops=9, straight_km=4.0)
    contexts = [make_ctx(50.0), make_ctx(50.0)]
    result = check_constraints(candidate, contexts, cfg)
    assert not result.feasible
    assert any(v.name == "min_demand" for v in result.violations)


def test_min_demand_exactly_at_limit_passes(cfg):
    candidate = make_candidate(route_km=5.0, n_stops=9, straight_km=4.0)
    contexts = [make_ctx(250.0), make_ctx(250.0)]  # sum = 500.0
    result = check_constraints(candidate, contexts, cfg)
    assert not any(v.name == "min_demand" for v in result.violations)


def test_max_route_km_violation(cfg):
    # 35 km > 30 km limit
    candidate = make_candidate(route_km=35.0, n_stops=50, straight_km=20.0)
    contexts = [make_ctx(300.0), make_ctx(300.0)]
    result = check_constraints(candidate, contexts, cfg)
    assert any(v.name == "max_route_km" for v in result.violations)


def test_multiple_violations_all_reported(cfg):
    # detour violation + max_route_km violation
    candidate = make_candidate(route_km=35.0, n_stops=50, straight_km=5.0)
    contexts = [make_ctx(300.0), make_ctx(300.0)]
    result = check_constraints(candidate, contexts, cfg)
    names = [v.name for v in result.violations]
    assert "detour_ratio" in names
    assert "max_route_km" in names
    assert not result.feasible
