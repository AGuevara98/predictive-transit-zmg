"""
W4 -- NPP Prioritization Layer
===============================
Repositions the NPP-V framework as a multi-criteria place-characteristics
prioritization index, decoupled from demand estimation.

Vitality dimension (v_ridership_annual_n) is excluded -- it is a
municipality-level proxy with no AGEB-level discrimination power.
Demand signal lives exclusively in W1/W3.

Score formula:
    npp_score    = sum(feature_i * ensemble_weight_i)    [CRITIC+EWM, 14 features]
    equity_score = mean(pe_marginacion_n, pe_rezago_n)
    final_score  = (1 - ALPHA) * npp_score + ALPHA * equity_score
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2.extras
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)
PROJECT_ROOT = Path(__file__).parent.parent

ALPHA = 0.20  # equity bonus weight; sensitivity tested at 0.10, 0.20, 0.30

NPP_FEATURES = [
    "n_intersections_n", "n_street_density_n", "n_intersection_density_n",
    "p_poi_density_n", "p_employment_proxy_n", "p_retail_density_n",
    "p_service_density_n", "p_land_use_mix_n",
    "pe_population_n", "pe_pop_density_n", "pe_marginacion_n", "pe_rezago_n",
    "pe_dep_ratio_n", "pe_youth_share_n",
]
EQUITY_FEATURES = ["pe_marginacion_n", "pe_rezago_n"]
DIMENSIONS = {
    "n_intersections_n": "NODE",
    "n_street_density_n": "NODE",
    "n_intersection_density_n": "NODE",
    "p_poi_density_n": "PLACE",
    "p_employment_proxy_n": "PLACE",
    "p_retail_density_n": "PLACE",
    "p_service_density_n": "PLACE",
    "p_land_use_mix_n": "PLACE",
    "pe_population_n": "PEOPLE",
    "pe_pop_density_n": "PEOPLE",
    "pe_marginacion_n": "PEOPLE",
    "pe_rezago_n": "PEOPLE",
    "pe_dep_ratio_n": "PEOPLE",
    "pe_youth_share_n": "PEOPLE",
}


def compute_critic_weights(df: pd.DataFrame) -> dict:
    """CRITIC weights: contrast intensity x conflict across features."""
    std_dev = df.std()
    corr_matrix = df.corr()
    conflict = (1 - corr_matrix).sum()
    c_j = std_dev * conflict
    w = c_j / c_j.sum()
    return w.to_dict()


def compute_ewm_weights(df: pd.DataFrame) -> dict:
    """Entropy Weight Method weights: information dispersion across features."""
    n = len(df)
    shifted = df + 1e-6
    p_ij = shifted / shifted.sum()
    k = 1.0 / np.log(n)
    e_j = -k * (p_ij * np.log(p_ij)).sum()
    d_j = 1 - e_j
    w = d_j / d_j.sum()
    return w.to_dict()


def compute_ensemble_weights(critic_w: dict, ewm_w: dict) -> dict:
    """Average of CRITIC and EWM, re-normalized to sum to 1."""
    features = list(critic_w.keys())
    raw = {f: (critic_w[f] + ewm_w[f]) / 2.0 for f in features}
    total = sum(raw.values())
    return {f: v / total for f, v in raw.items()}


def compute_scores(df: pd.DataFrame, ensemble_w: dict, alpha: float = ALPHA) -> pd.DataFrame:
    """
    Compute npp_score, equity_score, final_score, priority_rank, priority_quintile.

    df must contain 'cve_ageb' plus all NPP_FEATURES columns.
    ensemble_w keys must cover all NPP_FEATURES.
    """
    npp_score = sum(df[f] * w for f, w in ensemble_w.items())
    equity_score = df[EQUITY_FEATURES].mean(axis=1)
    final_score = (1 - alpha) * npp_score + alpha * equity_score

    priority_rank = final_score.rank(ascending=False, method="min").astype(int)
    try:
        priority_quintile = pd.qcut(final_score, q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    except ValueError:
        priority_quintile = pd.cut(final_score, bins=5, labels=[1, 2, 3, 4, 5]).astype(int)

    return pd.DataFrame({
        "cve_ageb": df["cve_ageb"].values,
        "npp_score": npp_score.values,
        "equity_score": equity_score.values,
        "final_score": final_score.values,
        "priority_rank": priority_rank.values,
        "priority_quintile": priority_quintile.values,
    })
