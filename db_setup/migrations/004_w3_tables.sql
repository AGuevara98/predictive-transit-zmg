-- 004_w3_tables.sql
-- W3 Supply & Coverage-Gap Layer — output tables

DROP TABLE IF EXISTS features.ageb_coverage_gap CASCADE;
DROP TABLE IF EXISTS features.ageb_accessibility CASCADE;

CREATE TABLE features.ageb_accessibility (
    cve_ageb            TEXT PRIMARY KEY REFERENCES base.ageb(cvegeo),
    n_boarding_stops    INTEGER,
    accessibility_score NUMERIC,
    accessibility_n     NUMERIC
);

CREATE TABLE features.ageb_coverage_gap (
    cve_ageb            TEXT PRIMARY KEY REFERENCES base.ageb(cvegeo),
    transit_demand      NUMERIC,
    accessibility_score NUMERIC,
    coverage_gap_raw    NUMERIC,
    coverage_gap_n      NUMERIC,
    demand_quantile     INTEGER,
    access_quantile     INTEGER,
    gap_category        TEXT
);

CREATE INDEX ageb_accessibility_score_idx
    ON features.ageb_accessibility (accessibility_score);

CREATE INDEX ageb_coverage_gap_category_idx
    ON features.ageb_coverage_gap (gap_category);

ANALYZE features.ageb_accessibility;
ANALYZE features.ageb_coverage_gap;
