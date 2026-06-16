"""
W3.2 — Coverage-Gap Index
=========================
Combines W1 transit demand with W3.1 accessibility to produce a normalized
coverage-gap index per AGEB.

  coverage_gap_raw = transit_demand / (accessibility_score + 1.0)
  coverage_gap_n   = log1p + min-max normalization of coverage_gap_raw

Quintile ranks and gap_category labels are also computed:
  gap_category = 'High-gap'   if demand_quantile >= 4 AND access_quantile <= 2
  gap_category = 'Low-gap'    if demand_quantile <= 2 AND access_quantile >= 4
  gap_category = 'Medium-gap' otherwise

Output: features.ageb_coverage_gap
        outputs/w3/ageb_coverage_gap.csv
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

GAP_EPSILON = 1.0   # prevents div-by-zero; unserved AGEBs get gap = transit_demand


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_demand() -> pd.DataFrame:
    print("[Step 1] Loading transit demand from features.ageb_trip_ends...")
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(
            "SELECT cve_ageb, transit_demand FROM features.ageb_trip_ends",
            conn,
        )
    df["transit_demand"] = pd.to_numeric(df["transit_demand"], errors="coerce").fillna(0.0)
    print(f"  [OK] Demand loaded for {len(df):,} AGEBs")
    return df


def load_accessibility() -> pd.DataFrame:
    print("[Step 2] Loading accessibility from features.ageb_accessibility...")
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(
            "SELECT cve_ageb, accessibility_score FROM features.ageb_accessibility",
            conn,
        )
    df["accessibility_score"] = pd.to_numeric(df["accessibility_score"], errors="coerce").fillna(0.0)
    print(f"  [OK] Accessibility loaded for {len(df):,} AGEBs")
    return df


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def normalize_log1p_minmax(series: pd.Series) -> pd.Series:
    log_vals = np.log1p(series.clip(lower=0))
    mn, mx = log_vals.min(), log_vals.max()
    if mx - mn < 1e-9:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (log_vals - mn) / (mx - mn)


def quintile_rank(series: pd.Series) -> pd.Series:
    """Rank into quintiles 1–5 using qcut with duplicate-safe labels."""
    try:
        return pd.qcut(series, q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    except ValueError:
        # Fallback when too many ties prevent clean quintile cuts
        return pd.cut(series, bins=5, labels=[1, 2, 3, 4, 5]).astype(int)


def assign_gap_category(demand_q: pd.Series, access_q: pd.Series) -> pd.Series:
    conditions = [
        (demand_q >= 4) & (access_q <= 2),
        (demand_q <= 2) & (access_q >= 4),
    ]
    choices = ["High-gap", "Low-gap"]
    return pd.Series(
        np.select(conditions, choices, default="Medium-gap"),
        index=demand_q.index,
    )


def compute_gap(demand: pd.DataFrame, access: pd.DataFrame) -> pd.DataFrame:
    print("[Step 3] Computing coverage-gap index...")
    merged = demand.merge(access, on="cve_ageb", how="outer")

    # AGEBs missing from either table get zero values
    merged["transit_demand"]    = merged["transit_demand"].fillna(0.0)
    merged["accessibility_score"] = merged["accessibility_score"].fillna(0.0)

    merged["coverage_gap_raw"] = merged["transit_demand"] / (
        merged["accessibility_score"] + GAP_EPSILON
    )
    merged["coverage_gap_n"] = normalize_log1p_minmax(merged["coverage_gap_raw"])

    merged["demand_quantile"] = quintile_rank(merged["transit_demand"])
    merged["access_quantile"] = quintile_rank(merged["accessibility_score"])
    merged["gap_category"]    = assign_gap_category(
        merged["demand_quantile"], merged["access_quantile"]
    )

    print(f"  [OK] Gap computed for {len(merged):,} AGEBs")
    cat_counts = merged["gap_category"].value_counts().to_dict()
    for cat, n in cat_counts.items():
        print(f"    {cat}: {n:,}")
    return merged


# ---------------------------------------------------------------------------
# DB write
# ---------------------------------------------------------------------------

def write_coverage_gap(df: pd.DataFrame):
    print("[Step 4] Writing to features.ageb_coverage_gap...")
    cols = [
        "cve_ageb", "transit_demand", "accessibility_score",
        "coverage_gap_raw", "coverage_gap_n",
        "demand_quantile", "access_quantile", "gap_category",
    ]
    rows = list(df[cols].itertuples(index=False, name=None))

    with ENGINE.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM features.ageb_coverage_gap")
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO features.ageb_coverage_gap
                   (cve_ageb, transit_demand, accessibility_score,
                    coverage_gap_raw, coverage_gap_n,
                    demand_quantile, access_quantile, gap_category)
                   VALUES %s""",
                rows, page_size=500,
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("ANALYZE features.ageb_coverage_gap")
        conn.commit()
    print(f"  [OK] {len(rows):,} rows written")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\n" + "="*70)
    print("W3.2 -- COVERAGE-GAP INDEX")
    print("="*70)

    out_dir = PROJECT_ROOT / "outputs" / "w3"
    out_dir.mkdir(parents=True, exist_ok=True)

    demand_df = load_demand()
    access_df = load_accessibility()

    gap_df = compute_gap(demand_df, access_df)
    write_coverage_gap(gap_df)

    gap_df.to_csv(out_dir / "ageb_coverage_gap.csv", index=False)
    print(f"  [OK] CSV -> outputs/w3/ageb_coverage_gap.csv")

    print("\n" + "="*70)
    print("W3.2 COVERAGE-GAP COMPLETE")
    print("="*70)
    print(gap_df[["transit_demand", "accessibility_score", "coverage_gap_raw", "coverage_gap_n"]].describe().to_string())
    print("\nGap category counts:")
    print(gap_df["gap_category"].value_counts().to_string())


if __name__ == "__main__":
    main()
