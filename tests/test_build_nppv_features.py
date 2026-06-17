import numpy as np
import pandas as pd
import pytest
from src import build_nppv_features as b

def test_minmax_basic():
    s = pd.Series([0.0, 5.0, 10.0])
    out = b.minmax(s)
    assert out.tolist() == [0.0, 0.5, 1.0]

def test_minmax_constant_is_zero():
    out = b.minmax(pd.Series([3.0, 3.0, 3.0]))
    assert (out == 0.0).all()

def test_bounded_feature_uses_plain_minmax():
    s = pd.Series([0.0, 1.0, 4.0])
    out = b.normalize_feature(s, "pe_dep_ratio")
    assert out.tolist() == [0.0, 0.25, 1.0]

def test_count_feature_uses_log1p():
    s = pd.Series([0.0, 9.0, 99.0])  # log1p -> [0, ln10, ln100]
    out = b.normalize_feature(s, "p_poi_density")
    expected = b.minmax(np.log1p(s))
    assert np.allclose(out.values, expected.values)
    # log compresses the top: midpoint must be > 0.5 (vs 0.0909 for plain minmax)
    assert out.iloc[1] >= 0.5

def test_feature_partition_is_total_and_disjoint():
    assert set(b.LOG_FEATURES).isdisjoint(b.BOUNDED_FEATURES)
    assert set(b.LOG_FEATURES) | set(b.BOUNDED_FEATURES) == set(b.RAW_FEATURES)

def test_raw_features_excludes_ntl():
    assert "v_ntl_median" not in b.RAW_FEATURES
    assert len(b.RAW_FEATURES) == 15

def test_scian_sector_first_two_digits():
    assert b.scian_sector("236221") == "23"
    assert b.scian_sector("") == ""
    assert b.scian_sector(None) == ""

def test_land_use_entropy_zero_for_single_class():
    assert b.land_use_entropy(pd.Series(["retail", "retail"])) == 0.0

def test_land_use_entropy_positive_for_mix():
    assert b.land_use_entropy(pd.Series(["retail", "health", "other"])) > 0.0

def test_dep_ratio_capped_at_five():
    assert b.dep_ratio(100, 100, 1) == 5.0
    assert b.dep_ratio(10, 10, 40) == pytest.approx(0.5)

def test_youth_share_safe_when_pop_zero():
    assert b.youth_share(0, 0) == 0.0
    assert b.youth_share(25, 100) == pytest.approx(0.25)
