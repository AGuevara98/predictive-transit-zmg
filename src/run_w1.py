"""
W1: Demand Estimation Layer -- Master Execution Script
=====================================================
Runs W1 in sequence:
  1. Apply DDL migration 002_w1_demand_tables.sql (idempotent)
  2. w1_trip_generation.py  -- productions & attractions
  3. w1_gravity_model.py    -- doubly-constrained gravity OD matrix
  4. w1_demand_surface.py   -- vehicle-ownership transit-demand surface

Usage:
    python src/run_w1.py
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
        with engine.begin() as conn:
            sql_text = sql_file.read_text(encoding="utf-8")
            print(f"  Executing: {sql_file.name}...")
            conn.execute(text(sql_text))
        print(f"  [OK] {description} -- COMPLETE")
        return True
    except Exception as e:
        print(f"  [ERR] {description}: {e}")
        return False


def run_python_script(script: Path, description: str, timeout: int = 3600) -> bool:
    print(f"\n{'='*70}\n  {description}\n{'='*70}")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            timeout=timeout
        )
        if result.returncode != 0:
            print(f"  [ERR] {description} returned exit code {result.returncode}")
            return False
        print(f"  [OK] {description} -- COMPLETE")
        return True
    except subprocess.TimeoutExpired:
        print(f"  [ERR] TIMEOUT in {description}")
        return False
    except Exception as e:
        print(f"  [ERR] {description}: {e}")
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*70)
    print(" W1: DEMAND ESTIMATION LAYER")
    print("="*70)

    project_root = Path(__file__).parent.parent
    src_dir      = project_root / "src"
    mig_dir      = project_root / "db_setup" / "migrations"
    engine       = create_engine(PG_URI)

    # Step 1: DDL
    if not run_sql_file(engine, mig_dir / "002_w1_demand_tables.sql", "Step 1: DDL -- W1 output tables"):
        print(f"\n[ERR] W1 pipeline aborted.")
        engine.dispose()
        sys.exit(1)

    # Step 2-4: Python scripts
    scripts = [
        (src_dir / "w1_trip_generation.py",    "Step 2: W1.1 -- Trip generation"),
        (src_dir / "w1_gravity_model.py",      "Step 3: W1.2 -- Gravity model"),
        (src_dir / "w1_demand_surface.py",     "Step 4: W1.3 -- Transit-demand surface"),
    ]

    for script, description in scripts:
        if not run_python_script(script, description):
            print(f"\n[ERR] W1 pipeline aborted.")
            engine.dispose()
            sys.exit(1)

    print("\n" + "="*70)
    print(" [OK] W1 DEMAND ESTIMATION LAYER COMPLETE")
    print("="*70)
    print("DB outputs:")
    print("  features.ageb_trip_ends   -- productions, attractions, transit_demand per AGEB")
    print("  features.ageb_od_matrix   -- sparse AGEB x AGEB modeled flows")
    print("File outputs:")
    print("  outputs/w1/ageb_trip_ends.csv")
    print("  outputs/w1/ageb_demand_surface.csv")
    print("  outputs/w1/od_matrix_summary.csv")
    engine.dispose()


if __name__ == "__main__":
    main()
