"""Self-heal a missing/empty features.nppv_features before W-series runs."""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))
from src import build_nppv_features


def ensure_nppv_features(engine) -> bool:
    """Build features.nppv_features if missing/empty. Returns True if built."""
    try:
        with engine.connect() as conn:
            n = conn.execute(text("SELECT count(*) FROM features.nppv_features")).scalar()
        if n and n > 0:
            print(f"[OK] features.nppv_features present ({n} rows).")
            return False
    except Exception:
        print("[Step] features.nppv_features missing; building...")
    build_nppv_features.build(engine)
    return True
