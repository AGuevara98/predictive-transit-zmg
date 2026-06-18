"""
W3: Supply & Coverage-Gap Layer -- Master Execution Script
==========================================================
Runs W3 in sequence:
  1. Apply DDL migration 004_w3_tables.sql (idempotent -- CREATE TABLE IF NOT EXISTS)
  2. w3_accessibility.py   -- GTFS-based cumulative-opportunities accessibility per AGEB
  3. w3_coverage_gap.py    -- coverage-gap index (demand / accessibility)
  4. w3_retrain.py         -- RF + LightGBM re-trained on high-gap binary target

Usage:
    python src/run_w3.py
"""

import subprocess
import sys
import traceback
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI
from src.db_preflight import ensure_nppv_features


def run_sql_file(engine, sql_file: Path, description: str) -> bool:
    print(f"\n{'='*70}\n  {description}\n{'='*70}")
    try:
        sql_text = sql_file.read_text(encoding="utf-8")
        statements = [s.strip() for s in sql_text.split(";") if s.strip()]
        with engine.begin() as conn:
            for stmt in statements:
                print(f"  Executing: {stmt[:80]}...")
                conn.execute(text(stmt))
        print(f"  [OK] {description} -- COMPLETE")
        return True
    except Exception as e:
        print(f"  [ERR] {description}: {e}")
        traceback.print_exc()
        return False


def run_python_script(_engine, script: Path, description: str, timeout: int = 7200) -> bool:
    # _engine kept for uniform dispatch signature; not used here
    print(f"\n{'='*70}\n  {description}\n{'='*70}")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.stdout:
            print(result.stdout)
        if result.returncode != 0:
            print(f"  [ERR] {description}:")
            if result.stderr:
                print(result.stderr)
            return False
        print(f"  [OK] {description} -- COMPLETE")
        return True
    except subprocess.TimeoutExpired:
        print(f"  [ERR] TIMEOUT ({timeout}s) in {description}")
        return False
    except Exception as e:
        print(f"  [ERR] {description}: {e}")
        return False


def main():
    print("\n" + "="*70)
    print(" W3: SUPPLY & COVERAGE-GAP LAYER")
    print("="*70)

    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    mig_dir = project_root / "db_setup" / "migrations"

    print("\nConnecting to PostgreSQL...")
    engine = create_engine(PG_URI)
    ensure_nppv_features(engine)

    steps = [
        (run_sql_file,      engine, mig_dir / "004_w3_tables.sql",   "Step 1: DDL -- W3 output tables"),
        (run_python_script, None,   src_dir / "w3_accessibility.py", "Step 2: W3.1 -- GTFS transit accessibility"),
        (run_python_script, None,   src_dir / "w3_coverage_gap.py",  "Step 3: W3.2 -- Coverage-gap index"),
        (run_python_script, None,   src_dir / "w3_retrain.py",       "Step 4: W3.3 -- Retrain on high-gap target"),
    ]

    for fn, *args in steps:
        if not fn(*args):
            print(f"\n[ERR] W3 pipeline aborted.")
            engine.dispose()
            sys.exit(1)

    print("\n" + "="*70)
    print(" [OK] W3 SUPPLY & COVERAGE-GAP LAYER COMPLETE")
    print("="*70)
    print("DB outputs:")
    print("  features.ageb_accessibility  -- n_boarding_stops, accessibility_score, accessibility_n")
    print("  features.ageb_coverage_gap   -- coverage_gap_raw, coverage_gap_n, gap_category, quantiles")
    print("File outputs:")
    print("  outputs/w3/ageb_accessibility.csv")
    print("  outputs/w3/ageb_coverage_gap.csv")
    print("  outputs/w3/models/w3_coverage_gap_v1_{random_forest,lightgbm}.pkl")
    print("  outputs/w3/metrics/w3_coverage_gap_v1_{cv,test}_metrics.csv")
    print("  outputs/w3/shap/w3_coverage_gap_v1_{model}_importance.csv + _summary.png")
    engine.dispose()


if __name__ == "__main__":
    main()
