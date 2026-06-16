-- 006_w6_tables.sql
-- W6 New Corridor Generation -- output table

DROP TABLE IF EXISTS features.route_candidates CASCADE;

CREATE TABLE features.route_candidates (
    candidate_id        TEXT PRIMARY KEY,
    corridor_group      INTEGER,
    route_km            FLOAT8,
    n_stops             INTEGER,
    straight_line_km    FLOAT8,
    connects_to_existing BOOLEAN,
    n_served_agebs      INTEGER,
    total_demand        FLOAT8,
    f1_demand_gain      FLOAT8,
    f2_route_km         FLOAT8,
    f3_equity           FLOAT8,
    composite_score     FLOAT8,
    total_score         FLOAT8,
    pareto_rank         INTEGER,
    feasible            BOOLEAN,
    mode_assignment     TEXT,
    geom                GEOMETRY(LineString, 6372) NOT NULL
);

CREATE INDEX IF NOT EXISTS route_candidates_geom_gix
    ON features.route_candidates USING GIST (geom);

CREATE INDEX IF NOT EXISTS route_candidates_total_score_idx
    ON features.route_candidates (total_score DESC);

ANALYZE features.route_candidates;
