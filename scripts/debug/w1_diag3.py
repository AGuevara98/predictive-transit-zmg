"""Check cvegeo formats."""
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)

with ENGINE.begin() as conn:
    rows = conn.execute(text("SELECT cvegeo FROM base.ageb LIMIT 5")).fetchall()
print("base.ageb cvegeo examples:")
for r in rows:
    print(f"  {r[0]}  (len: {len(r[0])})")

with ENGINE.begin() as conn:
    rows = conn.execute(text("SELECT cve_ageb FROM features.nppv_features LIMIT 5")).fetchall()
print("nppv_features cve_ageb examples:")
for r in rows:
    print(f"  {r[0]}  (len: {len(r[0])})")

with ENGINE.begin() as conn:
    count = conn.execute(text("SELECT COUNT(*) FROM base.ageb WHERE cvegeo LIKE '%A%'")).scalar()
print(f"base.ageb cvegeo values containing A: {count}")

# Also see the DDL filter for base.ageb
with ENGINE.begin() as conn:
    rows = conn.execute(text("SELECT cvegeo FROM base.ageb WHERE cvegeo LIKE '%0000%' LIMIT 5")).fetchall()
print("base.ageb where cvegeo has 0000 (mun-level aggregates?):")
for r in rows:
    print(f"  {r[0]}")
