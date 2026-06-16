-- 003_w2_eod_tables.sql
-- W2 Survey Calibration -- EOD 2022 raw ingestion tables

CREATE TABLE IF NOT EXISTS raw.eod_zones (
    zone_id     TEXT PRIMARY KEY,
    zone_name   TEXT,
    productions NUMERIC,
    attractions NUMERIC,
    geom        GEOMETRY(MULTIPOLYGON, 6372)
);
CREATE INDEX IF NOT EXISTS idx_eod_zones_geom ON raw.eod_zones USING GIST(geom);

CREATE TABLE IF NOT EXISTS raw.eod_desire_lines (
    origin_zone   TEXT    NOT NULL,
    dest_zone     TEXT    NOT NULL,
    observed_flow NUMERIC NOT NULL,
    PRIMARY KEY (origin_zone, dest_zone)
);

-- Calibration results table -- written by w2_gravity_calibration.py
CREATE TABLE IF NOT EXISTS features.w2_calibration (
    run_ts          TIMESTAMPTZ DEFAULT NOW(),
    beta_w1         NUMERIC,          -- W1 prior value (2.0)
    beta_calibrated NUMERIC,          -- fitted value
    n_pairs         INTEGER,
    rmse_log        NUMERIC,
    r2              NUMERIC,
    notes           TEXT,
    PRIMARY KEY (run_ts)
);

ANALYZE raw.eod_zones;
