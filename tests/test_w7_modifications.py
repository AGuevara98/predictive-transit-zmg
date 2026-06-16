"""
Tests for W7.3 -- Modification Proposer (src/w7_modifications.py)
Uses synthetic route pair DataFrames; no DB calls.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.w7_modifications import (
    _compute_jaccard,
    _estimate_shortcut_route_km,
    propose_modifications,
)


# ---------------------------------------------------------------------------
# Test _compute_jaccard
# ---------------------------------------------------------------------------

def test_compute_jaccard_identical():
    assert _compute_jaccard({"A", "B"}, {"A", "B"}) == 1.0


def test_compute_jaccard_disjoint():
    assert _compute_jaccard({"A"}, {"B"}) == 0.0


def test_compute_jaccard_partial():
    result = _compute_jaccard({"A", "B", "C"}, {"B", "C", "D"})
    assert abs(result - 2 / 4) < 1e-9


def test_compute_jaccard_empty_sets():
    assert _compute_jaccard(set(), set()) == 0.0


# ---------------------------------------------------------------------------
# Test _estimate_shortcut_route_km
# ---------------------------------------------------------------------------

def test_estimate_shortcut_km_basic():
    result = _estimate_shortcut_route_km(20.0, 10.0)
    assert abs(result - 11.0) < 1e-6


def test_estimate_shortcut_km_is_shorter_than_detoured():
    current_km = 25.0
    straight_km = 12.0
    shortcut = _estimate_shortcut_route_km(current_km, straight_km)
    assert shortcut < current_km


def test_estimate_shortcut_km_ratio():
    """Shortcut should be 1.1 * straight_line_km."""
    result = _estimate_shortcut_route_km(15.0, 8.0)
    assert abs(result - 8.8) < 1e-6


# ---------------------------------------------------------------------------
# Helpers to build synthetic scored DataFrames
# ---------------------------------------------------------------------------

def _make_scored_row(
    route_id: str,
    flag=None,
    overlap_route_id=None,
    total_score: float = 0.5,
    f1_demand_gain: float = 0.4,
    detour_ratio: float = 1.2,
    route_km: float = 10.0,
    straight_line_km: float = 8.5,
    n_stops: int = 15,
    connects_to_existing: bool = True,
    served_agebs: str = "001|002|003",
    n_served_agebs: int = 3,
    route_short_name: str = "",
) -> dict:
    return {
        "route_id": route_id,
        "flag": flag,
        "overlap_route_id": overlap_route_id,
        "total_score": total_score,
        "f1_demand_gain": f1_demand_gain,
        "detour_ratio": detour_ratio,
        "route_km": route_km,
        "straight_line_km": straight_line_km,
        "n_stops": n_stops,
        "connects_to_existing": connects_to_existing,
        "served_agebs": served_agebs,
        "n_served_agebs": n_served_agebs,
        "route_short_name": route_short_name,
    }


# ---------------------------------------------------------------------------
# Test propose_modifications
# ---------------------------------------------------------------------------

def test_propose_modifications_indirect():
    df = pd.DataFrame([
        _make_scored_row("R1", flag="Indirect", detour_ratio=1.8,
                         route_km=20.0, straight_line_km=10.0),
    ])
    proposals = propose_modifications(df, engine=None)
    assert len(proposals) == 1
    assert proposals[0]["modification_type"] == "shortcut"
    assert proposals[0]["route_id"] == "R1"
    assert "detour_ratio" in proposals[0]["reason"]


def test_propose_modifications_redundant():
    df = pd.DataFrame([
        _make_scored_row("R1", total_score=0.8, served_agebs="001|002|003"),
        _make_scored_row("R2", flag="Redundant", overlap_route_id="R1",
                         total_score=0.3, served_agebs="001|002|003|004"),
    ])
    proposals = propose_modifications(df, engine=None)
    assert any(p["modification_type"] == "merge" for p in proposals)
    merge_p = next(p for p in proposals if p["modification_type"] == "merge")
    assert merge_p["route_id"] == "R2"
    assert merge_p["overlap_route_id"] == "R1"


def test_propose_modifications_retire_low_demand_redundant():
    df = pd.DataFrame([
        _make_scored_row("R1", total_score=0.8, served_agebs="001|002|003"),
        _make_scored_row(
            "R2", flag="Low demand", overlap_route_id="R1",
            total_score=0.1, f1_demand_gain=0.05,
            served_agebs="001|002|003|004",
        ),
    ])
    proposals = propose_modifications(df, engine=None)
    retire_p = next((p for p in proposals if p["route_id"] == "R2"), None)
    assert retire_p is not None
    assert retire_p["modification_type"] == "retire"


def test_propose_modifications_empty_if_no_flags():
    df = pd.DataFrame([
        _make_scored_row("R1", flag=None),
        _make_scored_row("R2", flag=None),
    ])
    proposals = propose_modifications(df, engine=None)
    assert proposals == []


def test_propose_modifications_shortcut_proposed_score_none_without_engine():
    """Without engine, proposed_score should be None for shortcut."""
    df = pd.DataFrame([
        _make_scored_row("R1", flag="Indirect", detour_ratio=2.0,
                         route_km=22.0, straight_line_km=9.0),
    ])
    proposals = propose_modifications(df, engine=None)
    assert len(proposals) == 1
    assert proposals[0]["proposed_score"] is None


def test_propose_modifications_retire_standalone_low_demand():
    """A Low demand route with no redundant match should also get retire."""
    df = pd.DataFrame([
        _make_scored_row("R1", flag="Low demand", overlap_route_id=None,
                         total_score=0.1, f1_demand_gain=0.05),
    ])
    proposals = propose_modifications(df, engine=None)
    assert len(proposals) == 1
    assert proposals[0]["modification_type"] == "retire"
    assert proposals[0]["overlap_route_id"] is None


def test_propose_modifications_returns_list_of_dicts():
    df = pd.DataFrame([
        _make_scored_row("R1", flag="Indirect", detour_ratio=1.9,
                         route_km=18.0, straight_line_km=9.0),
    ])
    proposals = propose_modifications(df, engine=None)
    assert isinstance(proposals, list)
    assert isinstance(proposals[0], dict)
    required_keys = {
        "route_id", "modification_type", "reason",
        "current_score", "proposed_score", "overlap_route_id", "detail",
    }
    assert required_keys.issubset(proposals[0].keys())
