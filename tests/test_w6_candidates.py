# tests/test_w6_candidates.py
import math
import pytest

from src.w6_candidates import compute_n_stops


def test_compute_n_stops_typical_route():
    n = compute_n_stops(8.0)
    assert n >= 2
    spacing = (8.0 * 1000) / (n - 1)
    assert 300.0 <= spacing <= 1000.0


def test_compute_n_stops_very_short_route():
    n = compute_n_stops(0.6)
    assert n >= 2
    spacing = (0.6 * 1000) / (n - 1)
    assert spacing <= 1000.0


def test_compute_n_stops_long_route():
    n = compute_n_stops(25.0)
    spacing = (25.0 * 1000) / (n - 1)
    assert 300.0 <= spacing <= 1000.0


def test_compute_n_stops_minimum_is_two():
    n = compute_n_stops(0.001)
    assert n >= 2


def test_compute_n_stops_respects_min_stop_spacing():
    n = compute_n_stops(3.0, min_spacing_m=300.0)
    if n > 2:
        spacing = (3.0 * 1000) / (n - 1)
        assert spacing >= 300.0


def test_compute_n_stops_respects_max_stop_spacing():
    n = compute_n_stops(10.0, max_spacing_m=1000.0)
    if n > 2:
        spacing = (10.0 * 1000) / (n - 1)
        assert spacing <= 1000.0
