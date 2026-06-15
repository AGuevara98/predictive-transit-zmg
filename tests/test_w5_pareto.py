# tests/test_w5_pareto.py
import numpy as np
import pytest
from src.w5_types import ObjectiveResult
from src.w5_pareto import dominates, pareto_objectives, pareto_rank


def make_result(cid, f1, f2, f3):
    return ObjectiveResult(
        candidate_id=cid,
        f1_demand_gain=f1,
        f2_route_km=f2,
        f3_equity=f3,
        transfer_penalty=0.0,
        composite_score=0.0,
        total_score=0.0,
    )


def test_dominates_strict():
    # a better on f1 and f3, same f2 -> a dominates b (minimizing [-f1, f2, -f3])
    a = np.array([-0.8, 5.0, -0.7])
    b = np.array([-0.4, 5.0, -0.3])
    assert dominates(a, b) is True
    assert dominates(b, a) is False


def test_dominates_equal_not_dominant():
    a = np.array([1.0, 1.0, 1.0])
    assert dominates(a, a) is False


def test_dominates_one_worse_not_dominant():
    a = np.array([0.5, 5.0, 0.5])
    b = np.array([0.5, 3.0, 0.5])   # b has better f2 (lower km)
    assert dominates(a, b) is False


def test_pareto_objectives_shape():
    results = [make_result("R1", 0.5, 5.0, 0.6), make_result("R2", 0.3, 8.0, 0.8)]
    obj = pareto_objectives(results)
    assert obj.shape == (2, 3)


def test_pareto_objectives_minimization_sign():
    results = [make_result("R1", 0.5, 5.0, 0.6)]
    obj = pareto_objectives(results)
    # f1 and f3 are negated (we want to maximize them -> minimize negative)
    assert obj[0, 0] == pytest.approx(-0.5)
    assert obj[0, 1] == pytest.approx(5.0)
    assert obj[0, 2] == pytest.approx(-0.6)


def test_single_candidate_is_rank_one():
    results = [make_result("R1", 0.5, 5.0, 0.5)]
    ranks = pareto_rank(results)
    assert ranks[0] == 1


def test_dominated_candidate_gets_higher_rank():
    # R1 dominates R2 on all objectives
    results = [
        make_result("R1", f1=0.8, f2=5.0, f3=0.7),
        make_result("R2", f1=0.4, f2=8.0, f3=0.3),
    ]
    ranks = pareto_rank(results)
    assert ranks[0] == 1
    assert ranks[1] == 2


def test_pareto_front_no_domination():
    # Each candidate is best on one objective — none dominates another
    results = [
        make_result("R1", f1=0.9, f2=15.0, f3=0.3),  # best f1
        make_result("R2", f1=0.3, f2=15.0, f3=0.9),  # best f3
        make_result("R3", f1=0.5, f2=3.0,  f3=0.5),  # best f2
    ]
    ranks = pareto_rank(results)
    assert all(r == 1 for r in ranks)


def test_three_tier_ranking():
    # R1 dominates R2 dominates R3
    results = [
        make_result("R1", f1=0.9, f2=5.0, f3=0.9),
        make_result("R2", f1=0.6, f2=8.0, f3=0.6),
        make_result("R3", f1=0.3, f2=12.0, f3=0.3),
    ]
    ranks = pareto_rank(results)
    assert ranks[0] == 1
    assert ranks[1] == 2
    assert ranks[2] == 3


def test_empty_returns_empty_array():
    result = pareto_rank([])
    assert isinstance(result, np.ndarray)
    assert result.size == 0
