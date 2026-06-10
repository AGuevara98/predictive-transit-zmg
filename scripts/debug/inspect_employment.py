from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from config import PG_URI

engine = create_engine(PG_URI)
queries = [
    ("raw_denue_count", "SELECT COUNT(*) FROM raw.denue"),
    ("raw_denue_nonnull_geom", "SELECT COUNT(*) FROM raw.denue WHERE geom IS NOT NULL"),
    ("raw_denue_strata", "SELECT COALESCE(estrato_personal, '<NULL>') AS estrato_personal, COUNT(*) FROM raw.denue GROUP BY 1 ORDER BY 2 DESC"),
    ("raw_denue_scian_prefixes", "SELECT LEFT(COALESCE(scian_codigo::text, '<NULL>'), 3) AS scian_prefix, COUNT(*) FROM raw.denue GROUP BY 1 ORDER BY 2 DESC LIMIT 20"),
    ("raw_denue_sample", "SELECT denue_id, scian_codigo, estrato_personal, ageb_id FROM raw.denue WHERE estrato_personal IS NOT NULL LIMIT 10"),
    ("ageb_employment_summary", "SELECT COUNT(*) AS rows, MIN(employment_proxy) AS min_proxy, MAX(employment_proxy) AS max_proxy, AVG(employment_proxy) AS avg_proxy FROM features.ageb_employment"),
    ("ageb_employment_nonzero", "SELECT COUNT(*) FROM features.ageb_employment WHERE COALESCE(employment_proxy,0) > 0"),
    ("ageb_employment_sample", "SELECT * FROM features.ageb_employment ORDER BY employment_proxy DESC NULLS LAST LIMIT 10"),
]

with engine.connect() as conn:
    for name, q in queries:
        print(f"\n-- {name} --")
        try:
            for row in conn.execute(text(q)).fetchall():
                print(row)
        except Exception as exc:
            print(f"ERROR: {exc}")
