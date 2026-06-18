"""
Drift-guard integration test: live features.nppv_features vs the committed
post-W0 oracle (data/raw/nppv_features.csv).

Purpose: this guards against BUILD REGRESSIONS in src/build_nppv_features.py
while tolerating ACCEPTED SOURCE DRIFT. Two kinds of change can move a
live-vs-oracle column away from rho=1.0:

  1. A real regression in the builder logic (bad join, wrong formula,
     broken normalization) -- this must fail the test.
  2. Accepted drift from a regenerated external source feeding into the
     builder (D1/D6): osmnx pulls the OSM 'drive' graph live on each run,
     so the 3 NODE columns (n_intersections_n, n_street_density_n,
     n_intersection_density_n) will never match the oracle's frozen OSM
     snapshot exactly -- this is expected and must NOT fail the test.

PLACE and PEOPLE columns are deterministic functions of committed inputs
(DENUE CSV, CPV2020 census, frozen marginacion/rezago indices), so they are
held to a TIGHT threshold (Spearman rho >= 0.98; all measured at 1.000).
NODE columns are regenerated from live OSM data on every build, so they are
held to a LOOSE threshold (Spearman rho >= 0.60; measured 0.667-0.860) --
loose enough to tolerate live-OSM drift, tight enough that a real node-logic
regression (which would collapse rho toward 0) still trips the test.

v_ridership_annual_n is intentionally excluded: it is a known-defective
municipality-level proxy that behaves as a near-binary "has SITEUR" flag
(see W0 errata / W4 vitality decision in CLAUDE.md), so rank agreement with
the oracle is not a meaningful regression signal.
"""

from pathlib import Path

import pandas as pd
import pytest
from scipy.stats import spearmanr
from sqlalchemy import create_engine, text

ORACLE_PATH = Path(__file__).parent.parent / "data" / "raw" / "nppv_features.csv"

TIGHT_COLUMNS = [
    "p_poi_density_n",
    "p_employment_proxy_n",
    "p_retail_density_n",
    "p_service_density_n",
    "p_land_use_mix_n",
    "pe_population_n",
    "pe_pop_density_n",
    "pe_marginacion_n",
    "pe_rezago_n",
    "pe_dep_ratio_n",
    "pe_youth_share_n",
]

LOOSE_COLUMNS = [
    "n_intersections_n",
    "n_street_density_n",
    "n_intersection_density_n",
]

TIGHT_RHO_MIN = 0.98
LOOSE_RHO_MIN = 0.60


def _live():
    """Load features.nppv_features from the live DB. Skips the test (not
    error) on ANY failure -- missing DB, missing table, bad credentials,
    etc. -- since this is a drift guard, not a DB-availability check."""
    try:
        from config import PG_URI

        engine = create_engine(PG_URI)
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM features.nppv_features"), conn)
    except Exception as exc:
        pytest.skip(f"DB unavailable, skipping oracle drift check: {exc}")
    return df


def _oracle():
    return pd.read_csv(ORACLE_PATH, dtype={"cve_ageb": str})


def _joined_column(live_df, oracle_df, column):
    live = live_df[["cve_ageb", column]].copy()
    live["cve_ageb"] = live["cve_ageb"].astype(str)
    oracle = oracle_df[["cve_ageb", column]].copy()
    merged = live.merge(oracle, on="cve_ageb", suffixes=("_live", "_oracle"))
    merged = merged.dropna(subset=[f"{column}_live", f"{column}_oracle"])
    return merged[f"{column}_live"], merged[f"{column}_oracle"]


def test_structure_matches_post_w0():
    live = _live()
    assert len(live) > 2000
    assert "v_ntl_median" not in live.columns

    n_columns = [c for c in live.columns if c.endswith("_n")]
    assert len(n_columns) > 0
    assert live[n_columns].isna().sum().sum() == 0


@pytest.mark.parametrize("column", TIGHT_COLUMNS)
def test_tight_columns_match_oracle(column):
    live = _live()
    oracle = _oracle()
    live_vals, oracle_vals = _joined_column(live, oracle, column)
    rho, _ = spearmanr(live_vals, oracle_vals)
    assert rho >= TIGHT_RHO_MIN, (
        f"{column}: rho={rho:.4f} below tight threshold {TIGHT_RHO_MIN} "
        f"-- possible build regression (deterministic column should match oracle)"
    )


@pytest.mark.parametrize("column", LOOSE_COLUMNS)
def test_loose_columns_match_oracle(column):
    live = _live()
    oracle = _oracle()
    live_vals, oracle_vals = _joined_column(live, oracle, column)
    rho, _ = spearmanr(live_vals, oracle_vals)
    assert rho >= LOOSE_RHO_MIN, (
        f"{column}: rho={rho:.4f} below loose threshold {LOOSE_RHO_MIN} "
        f"-- exceeds accepted live-OSM drift, check for a node-logic regression"
    )
