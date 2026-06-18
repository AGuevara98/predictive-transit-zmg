"""
W4: NPP Prioritization Layer -- Master Execution Script
=======================================================
Runs W4 in sequence:
  1. Apply DDL migration 005_w4_tables.sql (idempotent -- DROP/CREATE)
  2. w4_prioritization.py  -- CRITIC/EWM weights, scores, all outputs

Usage:
    python src/run_w4.py
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


def run_python_script(_engine, script: Path, description: str, timeout: int = 3600) -> bool:
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
    print(" W4: NPP PRIORITIZATION LAYER")
    print("="*70)

    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    mig_dir = project_root / "db_setup" / "migrations"

    print("\nConnecting to PostgreSQL...")
    engine = create_engine(PG_URI)
    ensure_nppv_features(engine)

    steps = [
        (run_sql_file,      engine, mig_dir / "005_w4_tables.sql",      "Step 1: DDL -- W4 output tables"),
        (run_python_script, None,   src_dir / "w4_prioritization.py",   "Step 2: W4 -- NPP prioritization scores + outputs"),
    ]

    for fn, *args in steps:
        if not fn(*args):
            print(f"\n[ERR] W4 pipeline aborted.")
            engine.dispose()
            sys.exit(1)

    print("\n" + "="*70)
    print(" [OK] W4 NPP PRIORITIZATION LAYER COMPLETE")
    print("="*70)
    print("DB outputs:")
    print("  features.nppv_w4_weights     -- 14 feature weights")
    print("  features.nppv_prioritization -- 2,068 AGEB scores + ranks")
    print("File outputs: outputs/w4/")
    engine.dispose()


if __name__ == "__main__":
    main()
