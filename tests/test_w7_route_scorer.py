"""
Tests for W7.2 -- Route Scorer (src/w7_route_scorer.py)
All tests use mock AgebContext objects; no DB calls.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.w5_types import AgebContext, W5Config
from src.w7_route_scorer import (
    assign_flags,
    compute_detour_ratio,
    jaccard_overlap,
    route_to_candidate,
)


# ---------------------------------------------------------------------------
# Test compute_detour_ratio
# ---------------------------------------------------------------------------

def test_compute_detour_ratio_typical():
    assert abs(compute_detour_ratio(15.0, 10.0) - 1.5) < 1e-6


def test_compute_detour_ratio_zero_straight():
    # Should return 1.0 (not divide by zero)
    assert compute_detour_ratio(5.0, 0.0) == 1.0


def test_compute_detour_ratio_direct_route():
    # Route is as straight as possible -> ratio 1.0
    assert abs(compute_detour_ratio(10.0, 10.0) - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Test jaccard_overlap
# ---------------------------------------------------------------------------

def test_jaccard_overlap_identical_sets():
    a = {"A", "B", "C"}
    assert jaccard_overlap(a, a) == 1.0


def test_jaccard_overlap_disjoint_sets():
    assert jaccard_overlap({"A", "B"}, {"C", "D"}) == 0.0


def test_jaccard_overlap_partial():
    a = {"A", "B", "C"}
    b = {"B", "C", "D"}
    # |A & B| = 2, |A | B| = 4 -> 0.5
    result = jaccard_overlap(a, b)
    assert abs(result - 0.5) < 1e-9


def test_jaccard_overlap_empty_sets():
    assert jaccard_overlap(set(), set()) == 0.0


def test_jaccard_overlap_one_empty():
    assert jaccard_overlap({"A"}, set()) == 0.0


# ---------------------------------------------------------------------------
# Test route_to_candidate
# ---------------------------------------------------------------------------

def test_route_to_candidate_basic():
    rc = route_to_candidate(
        route_id="R1",
        route_km=10.0,
        n_stops=15,
        straight_line_km=8.0,
        connects_to_existing=True,
        served_ageb_ids=["001", "002", "003"],
    )
    assert rc.candidate_id == "R1"
    assert rc.route_km == 10.0
    assert rc.n_stops == 15
    assert rc.straight_line_km == 8.0
    assert rc.connects_to_existing is True
    assert "001" in rc.served_ageb_ids


def test_route_to_candidate_minimum_stops():
    """n_stops below 2 should be raised to 2."""
    rc = route_to_candidate("R1", 5.0, 1, 4.0, False, ["001"])
    assert rc.n_stops >= 2


# ---------------------------------------------------------------------------
# Test assign_flags
# ---------------------------------------------------------------------------

def _make_record(
    route_id: str,
    total_score: float,
    f1_demand_gain: float,
    detour_ratio: float,
    served_ageb_ids: set,
    overlap_route_id=None,
) -> dict:
    return {
        "route_id": route_id,
        "total_score": total_score,
        "f1_demand_gain": f1_demand_gain,
        "detour_ratio": detour_ratio,
        "served_ageb_ids": served_ageb_ids,
        "overlap_route_id": overlap_route_id,
    }


def test_assign_flags_low_demand():
    records = [
        _make_record("R1", 0.1, 0.05, 1.0, {"A", "B"}),
    ]
    flags = assign_flags(records)
    assert flags[0][0] == "Low demand"
    assert flags[0][1] is None


def test_assign_flags_indirect():
    records = [
        _make_record("R1", 0.6, 0.4, 1.8, {"A", "B", "C", "D"}),
    ]
    flags = assign_flags(records)
    assert flags[0][0] == "Indirect"


def test_assign_flags_redundant():
    # R2 has lower score and shares 80% with R1
    records = [
        _make_record("R1", 0.8, 0.5, 1.2, {"A", "B", "C", "D", "E"}),
        _make_record("R2", 0.3, 0.3, 1.1, {"A", "B", "C", "D", "F"}),
    ]
    flags = assign_flags(records)
    # R1 is not redundant (highest scoring)
    assert flags[0][0] is None
    # R2 overlaps 4/6 = 0.667 with R1 -> Redundant
    assert flags[1][0] == "Redundant"
    assert flags[1][1] == "R1"


def test_assign_flags_no_flag_for_good_route():
    records = [
        _make_record("R1", 0.7, 0.5, 1.2, {"A", "B", "C", "D"}),
    ]
    flags = assign_flags(records)
    assert flags[0][0] is None


def test_assign_flags_priority_redundant_over_indirect():
    """A route that is both redundant and indirect should be flagged Redundant."""
    records = [
        _make_record("R1", 0.8, 0.5, 1.2, {"A", "B", "C", "D", "E"}),
        # R2: indirect (detour=2.0) AND redundant with R1 (jaccard=4/6)
        _make_record("R2", 0.3, 0.3, 2.0, {"A", "B", "C", "D", "F"}),
    ]
    flags = assign_flags(records)
    assert flags[1][0] == "Redundant"


def test_assign_flags_multiple_routes_ordering():
    """The flag result list must be in the same order as input."""
    records = [
        _make_record("R_high", 0.9, 0.6, 1.0, {"A", "B", "C"}),
        _make_record("R_low", 0.1, 0.05, 1.0, {"X", "Y", "Z"}),
        _make_record("R_ind", 0.5, 0.4, 2.0, {"D", "E", "F"}),
    ]
    flags = assign_flags(records)
    assert len(flags) == 3
    # R_high: no flag; R_low: low demand; R_ind: indirect
    assert flags[0][0] is None
    assert flags[1][0] == "Low demand"
    assert flags[2][0] == "Indirect"
