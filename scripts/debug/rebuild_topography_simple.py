"""
Rebuild features.ageb_topography using raster sampling at AGEB centroids.
Avoids raster alignment issues by sampling elevation at point locations.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from config import PG_URI


SQL = """
DROP TABLE IF EXISTS features.ageb_topography CASCADE;
CREATE TABLE features.ageb_topography AS
SELECT
    a.cvegeo AS ageb_id,
    AVG((stats).mean)::float AS slope_mean
FROM base.ageb a
JOIN raw.dem r ON ST_Intersects(r.rast, ST_Transform(a.geom, 4326)),
LATERAL ST_SummaryStats(ST_Clip(r.rast, ST_Transform(a.geom, 4326)), 1, false) AS stats
GROUP BY a.cvegeo;

CREATE INDEX idx_ageb_topo_id ON features.ageb_topography (ageb_id);
ANALYZE features.ageb_topography;
"""


def main() -> int:
    engine = create_engine(PG_URI)
    try:
        with engine.begin() as conn:
            for stmt in [s.strip() for s in SQL.split(';') if s.strip()]:
                conn.execute(text(stmt))

        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM features.ageb_topography")).scalar()
            nonnull = conn.execute(text("SELECT COUNT(*) FROM features.ageb_topography WHERE slope_mean IS NOT NULL")).scalar()
            print(f"ageb_topography_rows={count}")
            print(f"ageb_topography_nonnull={nonnull}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
