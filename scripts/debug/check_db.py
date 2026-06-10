import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

def check_columns():
    engine = create_engine(PG_URI)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'base' AND table_name = 'ageb';"))
            columns = [row[0] for row in result]
            print("Columns in base.ageb:")
            for col in columns:
                print(f"  - {col}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    check_columns()
