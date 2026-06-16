"""
W6 Mode Assignment: classify corridor candidates as BRT or Local Bus
based on total transit demand in their 400m service buffer.

Threshold rationale (cite in thesis):
  LatAm BRT corridors typically serve 4,000+ pax/direction/peak-hour.
  At 10% peak-hour share and 50% directional split:
    4,000 / 0.10 / 0.50 = 80,000 daily boardings (system-wide).
  For a corridor covering ~15-30 AGEBs in ZMG, a conservative proxy
  threshold is 15,000 transit trip-ends/day in the 400m buffer.
  Sensitivity: report results at 10,000 and 20,000 as well.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

BRT_THRESHOLD = 15_000.0


def assign_mode(total_demand: float, brt_threshold: float = BRT_THRESHOLD) -> str:
    return "BRT" if total_demand >= brt_threshold else "Local Bus"


def label_mode_column(
    candidates_df: pd.DataFrame,
    brt_threshold: float = BRT_THRESHOLD,
) -> pd.DataFrame:
    df = candidates_df.copy()
    df["mode_assignment"] = df["total_demand"].apply(
        lambda d: assign_mode(d, brt_threshold)
    )
    return df
