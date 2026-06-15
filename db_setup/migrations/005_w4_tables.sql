-- 005_w4_tables.sql
-- W4 NPP Prioritization Layer — output tables

DROP TABLE IF EXISTS features.nppv_w4_weights CASCADE;
DROP TABLE IF EXISTS features.nppv_prioritization CASCADE;

CREATE TABLE features.nppv_w4_weights (
    feature          VARCHAR(50) PRIMARY KEY,
    dimension        VARCHAR(20),
    critic_weight    NUMERIC,
    ewm_weight       NUMERIC,
    ensemble_weight  NUMERIC
);

CREATE TABLE features.nppv_prioritization (
    cve_ageb          TEXT PRIMARY KEY REFERENCES base.ageb(cvegeo),
    npp_score         NUMERIC,
    equity_score      NUMERIC,
    final_score       NUMERIC,
    priority_rank     INTEGER,
    priority_quintile INTEGER
);

CREATE INDEX nppv_prioritization_final_score_idx
    ON features.nppv_prioritization (final_score DESC);

ANALYZE features.nppv_prioritization;
