import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from config import PG_URI


SQL = """
DROP TABLE IF EXISTS features.master_suitability CASCADE;
CREATE TABLE features.master_suitability AS
SELECT 
    a.cvegeo AS ageb_id,
    acc.stops_400m,
    acc.stops_800m,
    acc.min_stop_dist_m,
    emp.employment_proxy,
    COALESCE(rs.route_km_within_800m, 0) AS route_km_800m,
    COALESCE(topo.slope_mean, 0) AS slope_mean
FROM base.ageb a
JOIN features.ageb_accessibility acc ON a.cvegeo = acc.ageb_id
JOIN features.ageb_employment emp ON a.cvegeo = emp.ageb_id
LEFT JOIN features.ageb_topography topo ON a.cvegeo = topo.ageb_id
LEFT JOIN features.ageb_route_supply rs ON a.cvegeo = rs.ageb_id;

ANALYZE features.master_suitability;
"""


def main() -> int:
    engine = create_engine(PG_URI)
    try:
        with engine.begin() as conn:
            for stmt in [s.strip() for s in SQL.split(';') if s.strip()]:
                conn.execute(text(stmt))

        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM features.master_suitability")).scalar()
            print(f"master_suitability_rows={count}")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())