"""Check where 'A' appears in base.ageb cvegeo and structure."""
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)

# Columns already known to be lowercase: cvegeo, cve_ent, cve_mun, cve_loc, cve_ageb, geom

with ENGINE.begin() as conn:
    rows = conn.execute(text(
        "SELECT cvegeo, cve_ent, cve_mun, cve_loc, cve_ageb FROM base.ageb WHERE cvegeo LIKE '%A%' LIMIT 10"
    )).fetchall()
print("base.ageb rows where cvegeo contains A:")
for r in rows:
    print(f"  cvegeo={r[0]}  cve_ent={r[1]}  cve_mun={r[2]}  cve_loc={r[3]}  cve_ageb={r[4]}")

with ENGINE.begin() as conn:
    rows = conn.execute(text(
        "SELECT DISTINCT cve_loc FROM base.ageb WHERE cvegeo LIKE '%A%' ORDER BY 1"
    )).fetchall()
print("\nDistinct cve_loc values in rows where cvegeo contains A:")
print([r[0] for r in rows])

with ENGINE.begin() as conn:
    rows = conn.execute(text(
        "SELECT DISTINCT cve_ageb FROM base.ageb WHERE cvegeo LIKE '%A%' ORDER BY 1 LIMIT 20"
    )).fetchall()
print("\nDistinct cve_ageb values in rows where cvegeo contains A:")
print([r[0] for r in rows])

# Now understand the cvegeo construction
# cvegeo = cve_ent(2) + cve_mun(3) + cve_loc(4) + cve_ageb(4) = 13 chars
# Position 12 (0-indexed) = last char of cve_ageb
with ENGINE.begin() as conn:
    sample = conn.execute(text("SELECT cvegeo, cve_loc, cve_ageb FROM base.ageb LIMIT 3")).fetchall()
print("\ncvegeo decomposition sample:")
for r in sample:
    print(f"  cvegeo={r[0]}  cve_loc={r[1]}  cve_ageb={r[2]}")

# Determine where in cvegeo the 'A' is
with ENGINE.begin() as conn:
    rows = conn.execute(text(
        "SELECT cvegeo FROM base.ageb WHERE cvegeo LIKE '%A%' LIMIT 5"
    )).fetchall()
print("\nPosition of A in cvegeo (0-indexed):")
for r in rows:
    v = r[0]
    positions = [i for i, c in enumerate(v) if c == 'A']
    print(f"  {v}  -> A at {positions}")
