import pandas as pd
import pytest

from src.w6_mode import assign_mode, label_mode_column


def test_assign_mode_local_bus_below_threshold():
    assert assign_mode(8000.0, brt_threshold=15000.0, lrt_threshold=75000.0) == "Local Bus"


def test_assign_mode_brt_at_threshold():
    assert assign_mode(15000.0, brt_threshold=15000.0, lrt_threshold=75000.0) == "BRT"


def test_assign_mode_brt_between_thresholds():
    assert assign_mode(40000.0, brt_threshold=15000.0, lrt_threshold=75000.0) == "BRT"


def test_assign_mode_light_rail_at_threshold():
    assert assign_mode(75000.0, brt_threshold=15000.0, lrt_threshold=75000.0) == "Light Rail/Metro"


def test_assign_mode_light_rail_above_threshold():
    assert assign_mode(130000.0, brt_threshold=15000.0, lrt_threshold=75000.0) == "Light Rail/Metro"


def test_assign_mode_zero_demand():
    assert assign_mode(0.0, brt_threshold=15000.0, lrt_threshold=75000.0) == "Local Bus"


def test_label_mode_column_adds_column():
    df = pd.DataFrame({
        "candidate_id": ["C1", "C2", "C3", "C4"],
        "total_demand": [5000.0, 18000.0, 15000.0, 90000.0],
    })
    result = label_mode_column(df, brt_threshold=15000.0, lrt_threshold=75000.0)
    assert "mode_assignment" in result.columns
    assert result.loc[result["candidate_id"] == "C1", "mode_assignment"].iloc[0] == "Local Bus"
    assert result.loc[result["candidate_id"] == "C2", "mode_assignment"].iloc[0] == "BRT"
    assert result.loc[result["candidate_id"] == "C3", "mode_assignment"].iloc[0] == "BRT"
    assert result.loc[result["candidate_id"] == "C4", "mode_assignment"].iloc[0] == "Light Rail/Metro"
