-- Phase 2 output schema objects
-- Creates run registry, model metrics, prediction outputs, and SHAP importance tables.

CREATE SCHEMA IF NOT EXISTS features;

CREATE TABLE IF NOT EXISTS features.model_runs (
    run_id TEXT PRIMARY KEY,
    phase TEXT NOT NULL DEFAULT 'phase2',
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP,
    status TEXT NOT NULL,
    primary_metric TEXT NOT NULL DEFAULT 'pr_auc',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS features.model_metrics (
    run_id TEXT NOT NULL REFERENCES features.model_runs(run_id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    split_name TEXT NOT NULL,
    fold INTEGER,
    pr_auc DOUBLE PRECISION,
    roc_auc DOUBLE PRECISION,
    f1 DOUBLE PRECISION,
    precision DOUBLE PRECISION,
    recall DOUBLE PRECISION,
    threshold DOUBLE PRECISION,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (run_id, model_name, split_name, fold)
);

CREATE INDEX IF NOT EXISTS idx_model_metrics_run ON features.model_metrics (run_id);
CREATE INDEX IF NOT EXISTS idx_model_metrics_model ON features.model_metrics (model_name);

CREATE TABLE IF NOT EXISTS features.ageb_suitability_predictions (
    run_id TEXT NOT NULL REFERENCES features.model_runs(run_id) ON DELETE CASCADE,
    ageb_id VARCHAR(20) NOT NULL,
    score_rf DOUBLE PRECISION,
    score_lgbm DOUBLE PRECISION,
    class_rf SMALLINT,
    class_lgbm SMALLINT,
    threshold_rf DOUBLE PRECISION,
    threshold_lgbm DOUBLE PRECISION,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (run_id, ageb_id)
);

CREATE INDEX IF NOT EXISTS idx_phase2_predictions_run ON features.ageb_suitability_predictions (run_id);
CREATE INDEX IF NOT EXISTS idx_phase2_predictions_rf ON features.ageb_suitability_predictions (score_rf DESC);
CREATE INDEX IF NOT EXISTS idx_phase2_predictions_lgbm ON features.ageb_suitability_predictions (score_lgbm DESC);

CREATE TABLE IF NOT EXISTS features.model_feature_importance (
    run_id TEXT NOT NULL REFERENCES features.model_runs(run_id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    mean_abs_shap DOUBLE PRECISION NOT NULL,
    rank_position INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (run_id, model_name, feature_name)
);

CREATE INDEX IF NOT EXISTS idx_model_feature_importance_run ON features.model_feature_importance (run_id);

ANALYZE features.model_runs;
ANALYZE features.model_metrics;
ANALYZE features.ageb_suitability_predictions;
ANALYZE features.model_feature_importance;
