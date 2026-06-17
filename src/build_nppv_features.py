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

sys.path.insert(0, str(Path(__file__).parent.parent))

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
