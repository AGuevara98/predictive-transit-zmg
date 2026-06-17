"""Build features.nppv_features (post-W0) from committed source inputs.

Replaces the deleted phase2_db_setup.py + phase2_feature_engineering.py.
Corrections vs the deleted version:
  - drops v_ntl_median entirely (W0.1)
  - log1p+minmax for count/economic features, plain minmax for ratios (W0.3)
  - reads committed slim ZMG census extract (no ../gdl dependency)
  - reuses committed INEGI_DENUE_UTF8.csv (derives sector_id from scian_codigo)
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import entropy as sp_entropy

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import EMPLOYMENT_PROXY_MAP, SCIAN_SECTORS  # noqa: E402

RAW_FEATURES = [
    "n_intersections", "n_intersection_density", "n_street_density",
    "p_poi_density", "p_employment_proxy", "p_retail_density",
    "p_service_density", "p_land_use_mix",
    "pe_population", "pe_pop_density", "pe_dep_ratio", "pe_youth_share",
    "pe_marginacion", "pe_rezago", "v_ridership_annual",
]
# Bounded ratios keep plain min-max (W0.3); everything else is count/economic -> log1p+minmax
BOUNDED_FEATURES = ["pe_marginacion", "pe_rezago", "pe_dep_ratio",
                    "pe_youth_share", "p_land_use_mix"]
LOG_FEATURES = [f for f in RAW_FEATURES if f not in BOUNDED_FEATURES]


def minmax(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series(0.0, index=s.index)
    return (s - lo) / (hi - lo)


def normalize_feature(s: pd.Series, name: str) -> pd.Series:
    if name in LOG_FEATURES:
        return minmax(np.log1p(s.clip(lower=0)))
    return minmax(s)


def scian_sector(scian_codigo) -> str:
    if scian_codigo is None:
        return ""
    return str(scian_codigo)[:2] if str(scian_codigo).strip() else ""


def sector_label(sector_id) -> str:
    if not sector_id:
        return "other"
    for name, codes in SCIAN_SECTORS.items():
        if any(str(sector_id).startswith(c) for c in codes):
            return name
    return "other"


def land_use_entropy(labels: pd.Series) -> float:
    counts = labels.value_counts()
    if len(counts) <= 1:
        return 0.0
    return float(sp_entropy(counts.values))


def dep_ratio(p0_14, p65, p15_64) -> float:
    return float(min((p0_14 + p65) / max(p15_64, 1), 5.0))


def youth_share(p15_29, pop_total) -> float:
    return float(p15_29 / pop_total) if pop_total else 0.0
