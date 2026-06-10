"""
Phase 2: Master Execution Script
================================

This script orchestrates all Phase 2 components in the correct order:
1. Execute SQL bootstrap for Phase 2 outputs
2. Train RandomForest + LightGBM models (with leakage checks)
3. Generate AGEB-level suitability predictions and GeoJSON export
4. Run SHAP interpretability analysis
5. Generate Phase 2 report (metrics, leakage, SHAP vs CRITIC)

Usage:
    python src/run_phase2.py
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI


def run_sql_file(engine, sql_file, description):
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}")

    try:
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        statements = [s.strip() for s in sql_content.split(";") if s.strip()]

        with engine.begin() as connection:
            for stmt in statements:
                print(f"  Executing: {stmt[:80]}...")
                connection.execute(text(stmt))

        print(f"  [OK] {description} - COMPLETE")
        return True

    except Exception as e:
        print(f"  [ERR] ERROR in {description}:")
        print(f"    {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def run_python_script(script_file, description, args=None, timeout=1800):
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}")

    args = args or []

    try:
        result = subprocess.run(
            [sys.executable, str(script_file), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.stdout:
            print(result.stdout)

        if result.returncode != 0:
            print(f"  [ERR] ERROR in {description}:")
            if result.stderr:
                print(result.stderr)
            return False

        print(f"  [OK] {description} - COMPLETE")
        return True

    except subprocess.TimeoutExpired:
        print(f"  [ERR] TIMEOUT in {description}")
        return False
    except Exception as e:
        print(f"  [ERR] ERROR in {description}:")
        print(f"    {str(e)}")
        return False


def main():
    print("\n" + "=" * 70)
    print(" PHASE 2: PREDICTION - COMPLETE EXECUTION")
    print("=" * 70)

    run_id = datetime.now().strftime("phase2_%Y%m%d_%H%M%S")
    print(f"\nRun ID: {run_id}")

    project_root = Path(__file__).parent.parent
    db_setup_dir = project_root / "db_setup"
    src_dir = project_root / "src"

    print("\nConnecting to PostgreSQL...")
    engine = create_engine(PG_URI)

    try:
        if not run_sql_file(
            engine,
            db_setup_dir / "30_phase2_outputs.sql",
            "Step 1: Phase 2 Output Tables - SQL Bootstrap",
        ):
            return False

        if not run_python_script(
            src_dir / "phase2_train_models.py",
            "Step 2: Model Training - RandomForest + LightGBM + Leakage Checks",
            args=["--run-id", run_id],
            timeout=1800,
        ):
            return False

        if not run_python_script(
            src_dir / "phase2_predict_surface.py",
            "Step 3: Suitability Surface Prediction - All AGEBs + GeoJSON",
            args=["--run-id", run_id],
            timeout=1200,
        ):
            return False

        if not run_python_script(
            src_dir / "phase2_shap_analysis.py",
            "Step 4: SHAP Interpretability - Feature Importance",
            args=["--run-id", run_id],
            timeout=1800,
        ):
            return False

        if not run_python_script(
            src_dir / "phase2_report.py",
            "Step 5: Phase 2 Report - Metrics, Leakage, SHAP vs CRITIC",
            args=["--run-id", run_id],
            timeout=600,
        ):
            return False

        print("\n" + "=" * 70)
        print(" [OK] PHASE 2 EXECUTION COMPLETE")
        print("=" * 70)
        print(f"Run ID: {run_id}")
        print("\nPhase 2 Outputs:")
        print("  - Database: features.model_runs")
        print("  - Database: features.model_metrics")
        print("  - Database: features.ageb_suitability_predictions")
        print("  - Database: features.model_feature_importance")
        print("  - Files: outputs/phase2/models/*.pkl")
        print("  - Files: outputs/phase2/metrics/*.csv")
        print("  - Files: outputs/phase2/metrics/*_leakage_checks.json")
        print("  - Files: outputs/phase2/predictions/*.csv")
        print("  - Files: outputs/phase2/predictions/*.geojson")
        print("  - Files: outputs/phase2/shap/*.csv")
        print("  - Files: outputs/phase2/shap/*.png")
        print("  - Files: outputs/phase2/report_phase2_*.md")
        print("\nReady for Phase 3: Synthesis and route optimization")
        print("=" * 70 + "\n")

        return True

    except Exception as e:
        print(f"\n[ERR] FATAL ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        engine.dispose()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
