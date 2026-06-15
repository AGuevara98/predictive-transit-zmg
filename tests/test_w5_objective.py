# tests/test_w5_objective.py
import pytest
from src.w5_types import W5Config, RouteCandidate, AgebContext
from src.w5_objective import evaluate_objective


@pytest.fixture
def cfg():
    return W5Config()


def make_candidate(cid, ageb_ids, route_km=8.0, n_stops=14, straight_km=6.0, connected=True):
    return RouteCandidate(
        candidate_id=cid,
        served_ageb_ids=ageb_ids,
        route_km=route_km,
        n_stops=n_stops,
        straight_line_km=straight_km,
        connects_to_existing=connected,
    )


def make_ctx(cvegeo, demand, unserved, equity):
    return AgebContext(cvegeo=cvegeo, transit_demand=demand,
                       unserved_fraction=unserved, equity_score=equity)


def test_connected_route_has_no_transfer_penalty(cfg):
    candidate = make_candidate("R1", ["A001", "A002"], connected=True)
    contexts = [make_ctx("A001", 1000.0, 0.8, 0.7), make_ctx("A002", 800.0, 0.6, 0.6)]
    result = evaluate_objective(candidate, contexts, cfg)
    assert result.transfer_penalty == 0.0


def test_isolated_route_has_transfer_penalty(cfg):
    candidate = make_candidate("R2", ["A001"], connected=False)
    contexts = [make_ctx("A001", 1000.0, 0.8, 0.7)]
    result = evaluate_objective(candidate, contexts, cfg)
    assert result.transfer_penalty == pytest.approx(cfg.transfer_penalty)


def test_total_score_equals_composite_minus_penalty(cfg):
    candidate = make_candidate("R3", ["A001"], connected=False)
    contexts = [make_ctx("A001", 800.0, 0.5, 0.5)]
    result = evaluate_objective(candidate, contexts, cfg)
    assert result.total_score == pytest.approx(result.composite_score - result.transfer_penalty)


def test_f1_higher_for_more_unserved_ageb(cfg):
    candidate_base = make_candidate("R", ["A"], connected=True)
    high_unserved = [make_ctx("A", 1000.0, 0.9, 0.5)]
    low_unserved  = [make_ctx("A", 1000.0, 0.1, 0.5)]
    r_high = evaluate_objective(candidate_base, high_unserved, cfg)
    r_low  = evaluate_objective(candidate_base, low_unserved,  cfg)
    assert r_high.f1_demand_gain > r_low.f1_demand_gain


def test_f1_higher_with_connected_gain_factor(cfg):
    connected   = make_candidate("R_conn", ["A"], connected=True)
    isolated    = make_candidate("R_iso",  ["A"], connected=False)
    contexts    = [make_ctx("A", 1000.0, 0.8, 0.5)]
    r_conn = evaluate_objective(connected, contexts, cfg)
    r_iso  = evaluate_objective(isolated,  contexts, cfg)
    assert r_conn.f1_demand_gain > r_iso.f1_demand_gain


def test_f3_equals_mean_equity(cfg):
    candidate = make_candidate("R", ["A001", "A002"], connected=True)
    contexts = [make_ctx("A001", 500.0, 0.5, 0.8), make_ctx("A002", 500.0, 0.5, 0.4)]
    result = evaluate_objective(candidate, contexts, cfg)
    assert result.f3_equity == pytest.approx(0.6)


def test_empty_contexts_returns_zero_scores(cfg):
    candidate = make_candidate("R_empty", [], connected=True)
    result = evaluate_objective(candidate, [], cfg)
    assert result.f1_demand_gain == 0.0
    assert result.f3_equity == 0.0
    assert result.composite_score == 0.0
    assert result.total_score == 0.0


def test_composite_bounded_above_one(cfg):
    candidate = make_candidate("R_max", ["A"], route_km=1.0, n_stops=5, straight_km=0.9, connected=True)
    contexts = [make_ctx("A", 1e6, 1.0, 1.0)]
    result = evaluate_objective(candidate, contexts, cfg)
    assert result.composite_score <= 1.0 + 1e-9


def test_zero_demand_corridor_returns_zero_f1(cfg):
    candidate = make_candidate("R_zero", ["A"], connected=True)
    contexts = [make_ctx("A", 0.0, 0.8, 0.5)]
    result = evaluate_objective(candidate, contexts, cfg)
    assert result.f1_demand_gain == 0.0


def test_fully_served_ageb_returns_zero_f1(cfg):
    candidate = make_candidate("R_served", ["A"], connected=True)
    contexts = [make_ctx("A", 1000.0, 0.0, 0.5)]
    result = evaluate_objective(candidate, contexts, cfg)
    assert result.f1_demand_gain == 0.0


def test_route_km_exceeds_max_gives_zero_efficiency(cfg):
    # route_km=35 > max_route_km=30 -> efficiency=0, composite only from f1+f3
    candidate = make_candidate("R_long", ["A"], route_km=35.0, n_stops=50, straight_km=20.0, connected=True)
    contexts = [make_ctx("A", 1000.0, 0.5, 0.5)]
    result = evaluate_objective(candidate, contexts, cfg)
    f1_scaled = result.f1_demand_gain / cfg.connected_gain_factor
    expected_composite = cfg.w_demand_gain * f1_scaled + cfg.w_equity * result.f3_equity
    assert result.composite_score == pytest.approx(expected_composite, rel=1e-6)


def test_zero_route_km_gives_max_efficiency(cfg):
    # route_km=0 -> efficiency = max(0, 1 - 0/30) = 1.0
    candidate = make_candidate("R_zero_km", ["A"], route_km=0.0, n_stops=2, straight_km=0.0, connected=True)
    contexts = [make_ctx("A", 500.0, 0.5, 0.5)]
    result = evaluate_objective(candidate, contexts, cfg)
    f1_scaled = result.f1_demand_gain / cfg.connected_gain_factor
    expected_composite = (
        cfg.w_demand_gain * f1_scaled
        + cfg.w_efficiency * 1.0
        + cfg.w_equity * result.f3_equity
    )
    assert result.composite_score == pytest.approx(expected_composite, rel=1e-6)
