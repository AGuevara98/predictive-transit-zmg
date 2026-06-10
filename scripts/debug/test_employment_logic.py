from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from config import PG_URI

engine = create_engine(PG_URI)
queries = [
    ("denue_intersects_any_ageb", "SELECT COUNT(*) FROM raw.denue d WHERE EXISTS (SELECT 1 FROM base.ageb a WHERE ST_Intersects(a.geom, ST_Transform(d.geom, 6372)))"),
    ("denue_rows_joining_ageb", "SELECT COUNT(*) FROM base.ageb a JOIN raw.denue d ON ST_Intersects(a.geom, ST_Transform(d.geom, 6372))"),
    ("employment_recomputed_no_where", "SELECT SUM(CASE WHEN d.estrato_personal = '11 a 30 personas' THEN 20 WHEN d.estrato_personal = '31 a 50 personas' THEN 40 WHEN d.estrato_personal = '51 a 100 personas' THEN 75 WHEN d.estrato_personal = '101 a 250 personas' THEN 175 WHEN d.estrato_personal = '251 y más personas' THEN 300 ELSE 0 END) AS employment_proxy_sum FROM base.ageb a LEFT JOIN raw.denue d ON ST_Intersects(a.geom, ST_Transform(d.geom, 6372))"),
    ("employment_recomputed_with_where", "SELECT SUM(CASE WHEN d.estrato_personal = '11 a 30 personas' THEN 20 WHEN d.estrato_personal = '31 a 50 personas' THEN 40 WHEN d.estrato_personal = '51 a 100 personas' THEN 75 WHEN d.estrato_personal = '101 a 250 personas' THEN 175 WHEN d.estrato_personal = '251 y más personas' THEN 300 ELSE 0 END) AS employment_proxy_sum FROM base.ageb a LEFT JOIN raw.denue d ON ST_Intersects(a.geom, ST_Transform(d.geom, 6372)) WHERE (d.scian_codigo IS NULL OR (LEFT(d.scian_codigo::text, 2) IN ('31','32','33','43','46','54','55','61','62','71') OR d.scian_codigo::text LIKE '561%' OR d.scian_codigo::text LIKE '722%' OR d.scian_codigo::text LIKE '931%') AND d.estrato_personal NOT IN ('0 a 5 personas', '6 a 10 personas'))"),
]

with engine.connect() as conn:
    for name, q in queries:
        print(f"\n-- {name} --")
        try:
            for row in conn.execute(text(q)).fetchall():
                print(row)
        except Exception as exc:
            print(f"ERROR: {exc}")
