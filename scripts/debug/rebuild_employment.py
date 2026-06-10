import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import create_engine, text
from config import PG_URI

SQL = '''
DROP TABLE IF EXISTS features.ageb_employment CASCADE;
CREATE TABLE features.ageb_employment AS
SELECT 
    a.cvegeo AS ageb_id,
    COUNT(d.denue_id) AS total_establishments,
    SUM(CASE 
        WHEN d.estrato_personal = '11 a 30 personas' THEN 20
        WHEN d.estrato_personal = '31 a 50 personas' THEN 40
        WHEN d.estrato_personal = '51 a 100 personas' THEN 75
        WHEN d.estrato_personal = '101 a 250 personas' THEN 175
        WHEN d.estrato_personal = '251 y más personas' THEN 300
        ELSE 0 END) AS employment_proxy
FROM base.ageb a
LEFT JOIN raw.denue d ON ST_Intersects(a.geom, ST_Transform(d.geom, 6372))
WHERE d.estrato_personal NOT IN ('0 a 5 personas', '6 a 10 personas')
GROUP BY a.cvegeo;

CREATE INDEX idx_ageb_emp_id ON features.ageb_employment (ageb_id);
ANALYZE features.ageb_employment;
'''


def main():
    engine = create_engine(PG_URI)
    try:
        with engine.begin() as conn:
            for stmt in [s.strip() for s in SQL.split(';') if s.strip()]:
                conn.execute(text(stmt))
        with engine.connect() as conn:
            cnt = conn.execute(text("SELECT COUNT(*) FROM features.ageb_employment")).scalar()
            nonzero = conn.execute(text("SELECT COUNT(*) FROM features.ageb_employment WHERE COALESCE(employment_proxy,0) > 0")).scalar()
            print(f"ageb_employment_rows={cnt}")
            print(f"ageb_employment_nonzero={nonzero}")
        return 0
    finally:
        engine.dispose()

if __name__ == '__main__':
    raise SystemExit(main())
