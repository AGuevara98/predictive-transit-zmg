-- 007_w7_tables.sql
-- W7 Existing Route Audit -- output table

DROP TABLE IF EXISTS features.route_audit CASCADE;

CREATE TABLE IF NOT EXISTS features.route_audit (
    route_id            TEXT PRIMARY KEY,
    route_short_name    TEXT,
    route_km            FLOAT8,
    n_stops             INT,
    straight_line_km    FLOAT8,
    detour_ratio        FLOAT8,
    f1_demand_gain      FLOAT8,
    f2_route_km         FLOAT8,
    f3_equity           FLOAT8,
    total_score         FLOAT8,
    pareto_rank         INT,
    flag                TEXT,
    modification_type   TEXT,
    overlap_route_id    TEXT,
    geom                GEOMETRY(LineString, 6372)
);

CREATE INDEX IF NOT EXISTS route_audit_geom_gix ON features.route_audit USING GIST(geom);

ANALYZE features.route_audit;
