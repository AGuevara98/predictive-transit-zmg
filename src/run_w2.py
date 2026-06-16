"""
W2: Survey Calibration -- Master Execution Script
==================================================
Runs W2 in sequence:
  1. Apply DDL migration 003_w2_eod_tables.sql (idempotent)
  2. w2_eod_ingest.py   -- load EOD 2022 zones and desire lines into DB
  3. w2_gravity_calibration.py -- fit beta, write report and CSV

Usage:
    python src/run_w2.py

Prerequisites:
  - W1 complete (features.ageb_trip_ends and features.ageb_od_matrix populated)
  - EOD 2022 zip files in data/encuesta_origen_destino/
"""
import subprocess
import sys
import traceback
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI


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


def run_python_script(_engine, script: Path, description: str, timeout: int = 3600) -> bool:
    print(f"\n{'='*70}\n  {description}\n{'='*70}")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=timeout
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
        print(f"  [ERR] TIMEOUT in {description}")
        return False
    except Exception as e:
        print(f"  [ERR] {description}: {e}")
        return False


def main():
    print("\n" + "="*70)
    print(" W2: SURVEY CALIBRATION")
    print("="*70)

    project_root = Path(__file__).parent.parent
    src_dir      = project_root / "src"
    mig_dir      = project_root / "db_setup" / "migrations"

    print("\nConnecting to PostgreSQL...")
    engine = create_engine(PG_URI)

    steps = [
        (run_sql_file,      engine, mig_dir / "003_w2_eod_tables.sql",      "Step 1: DDL -- W2 EOD tables"),
        (run_python_script, None,   src_dir / "w2_eod_ingest.py",           "Step 2: W2.1 -- EOD data ingestion"),
        (run_python_script, None,   src_dir / "w2_gravity_calibration.py",  "Step 3: W2.2/W2.3/W2.4 -- Gravity calibration"),
    ]

    for fn, *args in steps:
        if not fn(*args):
            print(f"\n[ERR] W2 pipeline aborted.")
            engine.dispose()
            sys.exit(1)

    print("\n" + "="*70)
    print(" [OK] W2 SURVEY CALIBRATION COMPLETE")
    print("="*70)
    print("DB outputs:")
    print("  raw.eod_zones            -- EOD 2022 survey zone polygons + productions/attractions")
    print("  raw.eod_desire_lines     -- EOD 2022 observed OD flows (all modes)")
    print("  features.w2_calibration  -- calibrated beta and goodness-of-fit metrics")
    print("File outputs:")
    print("  outputs/w2/calibration_report.md")
    print("  outputs/w2/zone_od_comparison.csv")
    engine.dispose()


if __name__ == "__main__":
    main()
