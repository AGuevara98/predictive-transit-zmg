"""
Unit tests for W9 city configuration (Monterrey).

Tests verify:
  - All required constants exist in w9_city_config.py
  - Municipality codes are 3-digit zero-padded strings
  - Bounding box is valid (min < max, within Mexico)
  - DB_SCHEMA_PREFIX is a valid PostgreSQL identifier
  - GRAVITY_BETA is a positive float
  - CPV2020 column names are non-empty strings
  - Trip generation parameters are positive
  - NPP feature lists total exactly 14 features
  - EQUITY_ALPHA is in the valid range [0, 1]
"""
import re
import sys
from pathlib import Path

import pytest

# Make sure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))
import src.w9_city_config as cfg


# ---------------------------------------------------------------------------
# Test 1: Required constants exist
# ---------------------------------------------------------------------------
REQUIRED_CONSTANTS = [
    "CITY_NAME",
    "CITY_KEY",
    "CVE_ENT",
    "ZM_MUNICIPALITIES",
    "BBOX_LON_MIN",
    "BBOX_LON_MAX",
    "BBOX_LAT_MIN",
    "BBOX_LAT_MAX",
    "MTY_BBOX",
    "CRS_CANONICAL",
    "AGEB_FILTER_CVE_ENT",
    "DB_SCHEMA_PREFIX",
    "OSM_NETWORK_CACHE",
    "TRIPS_PER_PERSON_DAY",
    "YOUTH_MULTIPLIER",
    "EMPLOY_WEIGHT",
    "POI_WEIGHT",
    "RETAIL_WEIGHT",
    "GRAVITY_BETA",
    "GRAVITY_MAX_ITER",
    "GRAVITY_TOL",
    "GRAVITY_FLOW_THRESHOLD",
    "POP_COL",
    "VEHICLES_COL",
    "OCCUPIED_HOUSING_COL",
    "YOUTH_COL_COMBINED",
    "YOUTH_COL_LOW",
    "YOUTH_COL_HIGH",
    "CENSUS_ZIP_URL",
    "CENSUS_DIR_NAME",
    "CENSUS_CSV_NAME",
    "NODE_FEATURES",
    "PLACE_FEATURES",
    "PEOPLE_FEATURES",
    "ALL_NPP_FEATURES",
    "EQUITY_ALPHA",
]


@pytest.mark.parametrize("const_name", REQUIRED_CONSTANTS)
def test_required_constant_exists(const_name):
    """Every required constant must be defined in w9_city_config."""
    assert hasattr(cfg, const_name), (
        f"Missing required constant '{const_name}' in w9_city_config.py"
    )


# ---------------------------------------------------------------------------
# Test 2: Municipality codes are 3-digit zero-padded strings
# ---------------------------------------------------------------------------
def test_municipality_codes_are_three_digit_strings():
    """All ZM_MUNICIPALITIES entries must be zero-padded 3-digit numeric strings."""
    assert len(cfg.ZM_MUNICIPALITIES) > 0, "ZM_MUNICIPALITIES must not be empty"
    for code in cfg.ZM_MUNICIPALITIES:
        assert isinstance(code, str), f"Municipality code {code!r} is not a string"
        assert re.fullmatch(r"\d{3}", code), (
            f"Municipality code {code!r} is not a zero-padded 3-digit string"
        )


def test_monterrey_municipality_present():
    """Monterrey proper (code 039) must be in ZM_MUNICIPALITIES."""
    assert "039" in cfg.ZM_MUNICIPALITIES, (
        "Monterrey city code '039' must be in ZM_MUNICIPALITIES"
    )


def test_municipality_count():
    """ZM Monterrey per CONAPO 2020 has 12 municipalities."""
    assert len(cfg.ZM_MUNICIPALITIES) == 12, (
        f"Expected 12 ZM Monterrey municipalities, got {len(cfg.ZM_MUNICIPALITIES)}"
    )


def test_municipality_codes_unique():
    """No duplicate municipality codes."""
    assert len(cfg.ZM_MUNICIPALITIES) == len(set(cfg.ZM_MUNICIPALITIES)), (
        "ZM_MUNICIPALITIES contains duplicate codes"
    )


# ---------------------------------------------------------------------------
# Test 3: Bounding box is valid and within Mexico
# ---------------------------------------------------------------------------
def test_bbox_min_less_than_max():
    """Bounding box min values must be strictly less than max values."""
    assert cfg.BBOX_LON_MIN < cfg.BBOX_LON_MAX, (
        f"BBOX_LON_MIN ({cfg.BBOX_LON_MIN}) >= BBOX_LON_MAX ({cfg.BBOX_LON_MAX})"
    )
    assert cfg.BBOX_LAT_MIN < cfg.BBOX_LAT_MAX, (
        f"BBOX_LAT_MIN ({cfg.BBOX_LAT_MIN}) >= BBOX_LAT_MAX ({cfg.BBOX_LAT_MAX})"
    )


def test_bbox_within_mexico_longitude():
    """Bounding box longitude must fall within Mexico's range (-118.5 to -86.7)."""
    assert -118.5 <= cfg.BBOX_LON_MIN, (
        f"BBOX_LON_MIN ({cfg.BBOX_LON_MIN}) is west of Mexico"
    )
    assert cfg.BBOX_LON_MAX <= -86.7, (
        f"BBOX_LON_MAX ({cfg.BBOX_LON_MAX}) is east of Mexico"
    )


def test_bbox_within_mexico_latitude():
    """Bounding box latitude must fall within Mexico's range (14.5 to 32.7)."""
    assert 14.5 <= cfg.BBOX_LAT_MIN, (
        f"BBOX_LAT_MIN ({cfg.BBOX_LAT_MIN}) is south of Mexico"
    )
    assert cfg.BBOX_LAT_MAX <= 32.7, (
        f"BBOX_LAT_MAX ({cfg.BBOX_LAT_MAX}) is north of Mexico"
    )


def test_bbox_dict_consistent():
    """MTY_BBOX dict keys must be consistent with scalar bbox constants."""
    assert cfg.MTY_BBOX["xmin"] == cfg.BBOX_LON_MIN
    assert cfg.MTY_BBOX["xmax"] == cfg.BBOX_LON_MAX
    assert cfg.MTY_BBOX["ymin"] == cfg.BBOX_LAT_MIN
    assert cfg.MTY_BBOX["ymax"] == cfg.BBOX_LAT_MAX


def test_bbox_covers_monterrey_city():
    """Bounding box must contain the approximate centroid of Monterrey city."""
    # Monterrey city approx centroid: lon=-100.32, lat=25.67
    monterrey_lon = -100.32
    monterrey_lat = 25.67
    assert cfg.BBOX_LON_MIN <= monterrey_lon <= cfg.BBOX_LON_MAX, (
        f"Monterrey lon {monterrey_lon} is outside bounding box"
    )
    assert cfg.BBOX_LAT_MIN <= monterrey_lat <= cfg.BBOX_LAT_MAX, (
        f"Monterrey lat {monterrey_lat} is outside bounding box"
    )


# ---------------------------------------------------------------------------
# Test 4: DB_SCHEMA_PREFIX is a valid PostgreSQL identifier
# ---------------------------------------------------------------------------
def test_db_schema_prefix_is_valid_pg_identifier():
    """DB_SCHEMA_PREFIX must be a valid PostgreSQL unquoted identifier.

    Rules: starts with letter or underscore, contains only letters, digits,
    underscores; max 63 characters.
    """
    prefix = cfg.DB_SCHEMA_PREFIX
    assert isinstance(prefix, str), "DB_SCHEMA_PREFIX must be a string"
    assert len(prefix) <= 63, f"DB_SCHEMA_PREFIX '{prefix}' exceeds 63 characters"
    assert re.fullmatch(r"[a-z_][a-z0-9_]*", prefix), (
        f"DB_SCHEMA_PREFIX '{prefix}' is not a valid PostgreSQL identifier "
        "(lowercase letters, digits, underscores; must start with letter or underscore)"
    )


def test_db_schema_prefix_not_reserved():
    """DB_SCHEMA_PREFIX must not clash with existing ZMG schemas."""
    reserved = {"raw", "base", "features", "public", "pg_catalog"}
    assert cfg.DB_SCHEMA_PREFIX not in reserved, (
        f"DB_SCHEMA_PREFIX '{cfg.DB_SCHEMA_PREFIX}' clashes with existing ZMG schema"
    )


# ---------------------------------------------------------------------------
# Test 5: GRAVITY_BETA is a positive float
# ---------------------------------------------------------------------------
def test_gravity_beta_is_positive_float():
    """GRAVITY_BETA must be a positive finite float."""
    beta = cfg.GRAVITY_BETA
    assert isinstance(beta, float), (
        f"GRAVITY_BETA must be a float, got {type(beta).__name__}"
    )
    assert beta > 0, f"GRAVITY_BETA must be positive, got {beta}"
    assert beta < 100, f"GRAVITY_BETA {beta} is unreasonably large (> 100)"


def test_gravity_beta_matches_zmg_prior():
    """GRAVITY_BETA should equal the ZMG calibrated value of 2.0 (W2 finding)."""
    assert cfg.GRAVITY_BETA == 2.0, (
        f"GRAVITY_BETA is {cfg.GRAVITY_BETA}, expected 2.0 (ZMG calibrated prior from W2)"
    )


# ---------------------------------------------------------------------------
# Test 6: CPV2020 column names are non-empty strings
# ---------------------------------------------------------------------------
CPV2020_COLUMN_CONSTANTS = [
    "POP_COL",
    "VEHICLES_COL",
    "OCCUPIED_HOUSING_COL",
    "YOUTH_COL_COMBINED",
    "YOUTH_COL_LOW",
    "YOUTH_COL_HIGH",
]


@pytest.mark.parametrize("attr", CPV2020_COLUMN_CONSTANTS)
def test_cpv2020_column_name_is_nonempty_string(attr):
    """CPV2020 column name constants must be non-empty strings."""
    val = getattr(cfg, attr)
    assert isinstance(val, str), f"{attr} must be a string, got {type(val).__name__}"
    assert len(val.strip()) > 0, f"{attr} must not be empty"


def test_cpv2020_known_column_names():
    """Spot-check known CPV2020 column names from the ZMG pipeline."""
    assert cfg.POP_COL == "POBTOT", f"POP_COL expected 'POBTOT', got '{cfg.POP_COL}'"
    assert cfg.VEHICLES_COL == "VPH_AUTOM"
    assert cfg.OCCUPIED_HOUSING_COL == "VIVPAR_HAB"


# ---------------------------------------------------------------------------
# Test 7: Trip generation parameters are positive
# ---------------------------------------------------------------------------
def test_trip_generation_params_positive():
    """TRIPS_PER_PERSON_DAY and YOUTH_MULTIPLIER must be positive."""
    assert cfg.TRIPS_PER_PERSON_DAY > 0
    assert cfg.YOUTH_MULTIPLIER > 0
    assert cfg.EMPLOY_WEIGHT > 0
    assert cfg.POI_WEIGHT > 0
    assert cfg.RETAIL_WEIGHT > 0


def test_trips_per_person_day_matches_zmg():
    """TRIPS_PER_PERSON_DAY must equal ZMG value of 2.5."""
    assert cfg.TRIPS_PER_PERSON_DAY == 2.5


# ---------------------------------------------------------------------------
# Test 8: NPP feature lists total exactly 14 features
# ---------------------------------------------------------------------------
def test_npp_feature_lists_total_14():
    """ALL_NPP_FEATURES must contain exactly 14 indicators (Node + Place + People)."""
    assert len(cfg.ALL_NPP_FEATURES) == 14, (
        f"Expected 14 NPP features, got {len(cfg.ALL_NPP_FEATURES)}"
    )


def test_npp_feature_lists_correct_counts():
    """Node (3), Place (5), People (6) indicator counts must match W4 design."""
    assert len(cfg.NODE_FEATURES)   == 3, f"Expected 3 Node features, got {len(cfg.NODE_FEATURES)}"
    assert len(cfg.PLACE_FEATURES)  == 5, f"Expected 5 Place features, got {len(cfg.PLACE_FEATURES)}"
    assert len(cfg.PEOPLE_FEATURES) == 6, f"Expected 6 People features, got {len(cfg.PEOPLE_FEATURES)}"


def test_npp_all_features_union():
    """ALL_NPP_FEATURES must equal Node + Place + People concatenated."""
    expected = cfg.NODE_FEATURES + cfg.PLACE_FEATURES + cfg.PEOPLE_FEATURES
    assert cfg.ALL_NPP_FEATURES == expected, (
        "ALL_NPP_FEATURES does not match concatenation of NODE + PLACE + PEOPLE"
    )


def test_npp_features_end_in_n_suffix():
    """All NPP feature names must end in '_n' (normalized indicator convention)."""
    for feat in cfg.ALL_NPP_FEATURES:
        assert feat.endswith("_n"), (
            f"Feature '{feat}' does not end in '_n' (expected normalized name)"
        )


# ---------------------------------------------------------------------------
# Test 9: EQUITY_ALPHA is in valid range [0, 1]
# ---------------------------------------------------------------------------
def test_equity_alpha_in_range():
    """EQUITY_ALPHA must be a float in the range [0, 1]."""
    alpha = cfg.EQUITY_ALPHA
    assert isinstance(alpha, float), (
        f"EQUITY_ALPHA must be a float, got {type(alpha).__name__}"
    )
    assert 0.0 <= alpha <= 1.0, f"EQUITY_ALPHA must be in [0, 1], got {alpha}"


def test_equity_alpha_matches_w4_default():
    """EQUITY_ALPHA must equal W4 documented default of 0.20."""
    assert cfg.EQUITY_ALPHA == 0.20, (
        f"EQUITY_ALPHA is {cfg.EQUITY_ALPHA}, expected 0.20 (W4 documented default)"
    )


# ---------------------------------------------------------------------------
# Test 10: CRS and state code correctness
# ---------------------------------------------------------------------------
def test_crs_canonical():
    """CRS must be EPSG:6372 (canonical for all Mexico)."""
    assert cfg.CRS_CANONICAL == "EPSG:6372"


def test_cve_ent_is_nuevo_leon():
    """CVE_ENT must be '19' for Nuevo Leon."""
    assert cfg.CVE_ENT == "19", f"CVE_ENT expected '19', got '{cfg.CVE_ENT}'"
    assert cfg.AGEB_FILTER_CVE_ENT == "19"
