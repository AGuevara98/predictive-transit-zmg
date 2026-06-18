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
    # _engine kept for uniform (fn, engine, ...) dispatch signature; not used here
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
    print(" W1: DEMAND ESTIMATION LAYER")
    print("="*70)

    project_root = Path(__file__).parent.parent
    src_dir      = project_root / "src"
    mig_dir      = project_root / "db_setup" / "migrations"
    print("\nConnecting to PostgreSQL...")
    engine       = create_engine(PG_URI)
    ensure_nppv_features(engine)

    steps = [
        (run_sql_file,      engine, mig_dir / "002_w1_demand_tables.sql", "Step 1: DDL -- W1 output tables"),
        (run_python_script, None,   src_dir / "w1_trip_generation.py",    "Step 2: W1.1 -- Trip generation"),
        (run_python_script, None,   src_dir / "w1_gravity_model.py",      "Step 3: W1.2 -- Gravity model"),
        (run_python_script, None,   src_dir / "w1_demand_surface.py",     "Step 4: W1.3 -- Transit-demand surface"),
    ]

    for fn, *args in steps:
        if not fn(*args):
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
