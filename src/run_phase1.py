"""
Phase 1: Master Execution Script
=================================

This script orchestrates all Phase 1 components in the correct order:
1. Execute SQL views for CRITIC weights
2. Execute SQL views for station audit
3. Run critic_analysis.py
4. Run balanced_station_selection.py
5. Run phase1_report.py

Usage:
    python src/run_phase1.py
"""

import subprocess
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI


def run_sql_file(engine, sql_file, description):
    """
    Execute a SQL file against the database.
    
    Parameters:
        engine: SQLAlchemy engine
        sql_file: Path to SQL file
        description: Human-readable description of what's being executed
    """
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}")
    
    try:
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Split by statements (simple approach - may need refinement for complex SQL)
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        
        with engine.begin() as connection:
            for stmt in statements:
                if stmt:
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


def run_python_script(script_file, description):
    """
    Execute a Python script.
    
    Parameters:
        script_file: Path to Python script
        description: Human-readable description
    """
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_file)],
            capture_output=True,
            text=True,
            timeout=300  # 5-minute timeout
        )
        
        # Print output
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
    """Execute all Phase 1 components."""
    
    print("\n" + "="*70)
    print(" PHASE 1: AUDIT - COMPLETE EXECUTION")
    print("="*70)
    
    # Get paths
    project_root = Path(__file__).parent.parent
    db_setup_dir = project_root / "db_setup"
    src_dir = project_root / "src"
    
    # Connect to database
    print("\nConnecting to PostgreSQL...")
    engine = create_engine(PG_URI)
    
    try:
        # Step 1: CRITIC Weights SQL
        if not run_sql_file(
            engine,
            db_setup_dir / "10_critic_weights_view.sql",
            "Step 1: CRITIC Weights - SQL View Creation"
        ):
            return False
        
        # Step 2: Station Audit SQL
        if not run_sql_file(
            engine,
            db_setup_dir / "20_station_audit.sql",
            "Step 2: Station Audit - SQL View Creation"
        ):
            return False
        
        # Step 3: CRITIC Analysis Python
        if not run_python_script(
            src_dir / "critic_analysis.py",
            "Step 3: CRITIC Analysis - Feature Importance Visualization"
        ):
            return False
        
        # Step 4: Balanced Station Selection Python
        if not run_python_script(
            src_dir / "balanced_station_selection.py",
            "Step 4: Balanced Station Selection - Training Data Creation"
        ):
            return False
        
        # Step 5: Phase 1 Report Python
        if not run_python_script(
            src_dir / "phase1_report.py",
            "Step 5: Phase 1 Report - HTML Report Generation"
        ):
            return False
        
        print("\n" + "="*70)
        print(" [OK] PHASE 1 EXECUTION COMPLETE")
        print("="*70)
        print("\nPhase 1 Outputs:")
        print("  - Database: features.v_critic_weights (view)")
        print("  - Database: features.station_npv_audit (table)")
        print("  - Database: features.training_labels (table)")
        print("  - Files: outputs/phase1/critic_weights_barplot.png")
        print("  - Files: outputs/phase1/critic_variance_correlation.png")
        print("  - Files: outputs/phase1/critic_weights_pie.png")
        print("  - Files: outputs/phase1/critic_weights.csv")
        print("  - Files: outputs/phase1/training_labels.csv")
        print("  - Files: outputs/phase1/report.html")
        print("\nReady for Phase 2: ML Model Training")
        print("="*70 + "\n")
        
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
