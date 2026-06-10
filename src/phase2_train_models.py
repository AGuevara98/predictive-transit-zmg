"""
Phase 2: Model Training (RandomForest + LightGBM)

This script trains two alternative models for AGEB suitability prediction and
stores metrics/artifacts for downstream prediction and interpretability.

Usage:
    python src/phase2_train_models.py --run-id <run_id>
"""

import argparse
import json
import pickle
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sqlalchemy import create_engine, text

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

FEATURE_COLUMNS = [
    "stops_400m",
    "stops_800m",
    "min_stop_dist_m",
    "employment_proxy",
    "route_km_800m",
    "slope_mean",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Train Phase 2 suitability models")
    parser.add_argument("--run-id", required=True, help="Unique run identifier")
    return parser.parse_args()


def upsert_run_status(engine, run_id, status, notes=None, finish=False):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO features.model_runs (run_id, status, notes)
                VALUES (:run_id, :status, :notes)
                ON CONFLICT (run_id) DO UPDATE
                SET status = EXCLUDED.status,
                    notes = EXCLUDED.notes
                """
            ),
            {"run_id": run_id, "status": status, "notes": notes},
        )
        if finish:
            conn.execute(
                text(
                    "UPDATE features.model_runs SET finished_at = NOW() WHERE run_id = :run_id"
                ),
                {"run_id": run_id},
            )


def load_training_data(engine):
    query = """
    SELECT
        t.ageb_id,
        t.label,
        m.stops_400m,
        m.stops_800m,
        m.min_stop_dist_m,
        m.employment_proxy,
        m.route_km_800m,
        m.slope_mean
    FROM features.training_labels t
    JOIN features.master_suitability m ON m.ageb_id = t.ageb_id
    ORDER BY t.ageb_id;
    """
    df = pd.read_sql(text(query), engine)
    if df.empty:
        raise ValueError("features.training_labels join features.master_suitability returned 0 rows")

    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    X = df[FEATURE_COLUMNS]
    y = df["label"].astype(int)
    return df, X, y


def compute_metrics(y_true, y_prob, threshold):
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "threshold": float(threshold),
    }


def find_best_f1_threshold(y_true, y_prob):
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    if thresholds.size == 0:
        return 0.5

    precision = precision[:-1]
    recall = recall[:-1]
    denom = precision + recall
    f1_values = np.where(denom > 0, 2 * precision * recall / denom, 0.0)
    best_idx = int(np.argmax(f1_values))
    return float(thresholds[best_idx])


def model_factories():
    return {
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=300,
            max_depth=16,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
        "lightgbm": lambda: LGBMClassifier(
            n_estimators=350,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="binary",
            random_state=42,
            n_jobs=-1,
            verbosity=-1,
        ),
    }


def run_cross_validation(X, y):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    rows = []

    for model_name, factory in model_factories().items():
        for fold_id, (train_idx, val_idx) in enumerate(cv.split(X, y), start=1):
            model = factory()
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            y_prob = model.predict_proba(X.iloc[val_idx])[:, 1]
            train_prob = model.predict_proba(X.iloc[train_idx])[:, 1]
            threshold = find_best_f1_threshold(y.iloc[train_idx], train_prob)
            metrics = compute_metrics(y.iloc[val_idx], y_prob, threshold)
            rows.append(
                {
                    "model_name": model_name,
                    "split_name": "cv",
                    "fold": fold_id,
                    **metrics,
                }
            )

    return pd.DataFrame(rows)


def train_final_models(X_train, y_train):
    trained = {}
    for model_name, factory in model_factories().items():
        model = factory()
        model.fit(X_train, y_train)
        train_prob = model.predict_proba(X_train)[:, 1]
        threshold = find_best_f1_threshold(y_train, train_prob)
        trained[model_name] = {"model": model, "threshold": threshold}
    return trained


def run_label_shuffle_sanity(X_train, y_train):
    shuffled = y_train.sample(frac=1.0, random_state=42).reset_index(drop=True)
    X_train = X_train.reset_index(drop=True)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

    results = {}
    for model_name, factory in model_factories().items():
        scores = []
        for tr_idx, va_idx in cv.split(X_train, shuffled):
            model = factory()
            model.fit(X_train.iloc[tr_idx], shuffled.iloc[tr_idx])
            y_prob = model.predict_proba(X_train.iloc[va_idx])[:, 1]
            score = average_precision_score(shuffled.iloc[va_idx], y_prob)
            scores.append(float(score))
        results[model_name] = {
            "mean_pr_auc": float(np.mean(scores)),
            "std_pr_auc": float(np.std(scores)),
            "folds": scores,
        }
    return results


def evaluate_leakage_risks(df, X, y, X_train, X_test, y_train):
    train_vectors = set(map(tuple, X_train.round(8).to_numpy()))
    test_vectors = set(map(tuple, X_test.round(8).to_numpy()))
    shared_vectors = len(train_vectors.intersection(test_vectors))

    vector_label_counts = df.groupby(FEATURE_COLUMNS)["label"].nunique()
    conflicting_vectors = int((vector_label_counts > 1).sum())

    univariate = []
    for feature in FEATURE_COLUMNS:
        values = X[feature].to_numpy()
        pr_pos = average_precision_score(y, values)
        pr_neg = average_precision_score(y, -values)
        univariate.append(
            {
                "feature": feature,
                "best_direction": "positive" if pr_pos >= pr_neg else "negative",
                "best_pr_auc": float(max(pr_pos, pr_neg)),
            }
        )
    univariate = sorted(univariate, key=lambda r: r["best_pr_auc"], reverse=True)

    shuffle_sanity = run_label_shuffle_sanity(X_train, y_train)
    positive_rate = float(y.mean())

    flags = []
    if shared_vectors > 0:
        flags.append(f"Shared train/test feature vectors detected: {shared_vectors}")
    if univariate and univariate[0]["best_pr_auc"] > 0.98:
        flags.append(
            f"A single feature nearly separates classes (top {univariate[0]['feature']} PR-AUC={univariate[0]['best_pr_auc']:.4f})"
        )
    for model_name, payload in shuffle_sanity.items():
        if payload["mean_pr_auc"] > max(positive_rate + 0.12, 0.65):
            flags.append(
                f"Label-shuffle sanity high for {model_name}: mean PR-AUC={payload['mean_pr_auc']:.4f}"
            )

    return {
        "positive_rate": positive_rate,
        "n_rows": int(len(df)),
        "duplicate_ageb_ids": int(df["ageb_id"].duplicated().sum()),
        "shared_train_test_feature_vectors": shared_vectors,
        "conflicting_label_vectors": conflicting_vectors,
        "top_univariate_pr_auc": univariate[:6],
        "label_shuffle_sanity": shuffle_sanity,
        "risk_flags": flags,
    }


def save_leakage_report(run_id, leakage_report, output_dir):
    metrics_dir = output_dir / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    leak_file = metrics_dir / f"{run_id}_leakage_checks.json"
    with open(leak_file, "w", encoding="utf-8") as fh:
        json.dump(leakage_report, fh, indent=2)
    return leak_file


def save_artifacts(run_id, models, metrics_df, test_metrics_df, output_dir):
    models_dir = output_dir / "models"
    metrics_dir = output_dir / "metrics"
    models_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths = {}
    for model_name, payload in models.items():
        artifact_file = models_dir / f"{run_id}_{model_name}.pkl"
        with open(artifact_file, "wb") as fh:
            pickle.dump(
                {
                    "model_name": model_name,
                    "feature_columns": FEATURE_COLUMNS,
                    "threshold": payload["threshold"],
                    "trained_at": datetime.now(UTC).isoformat(),
                    "model": payload["model"],
                },
                fh,
            )
        artifact_paths[model_name] = str(artifact_file)

    cv_file = metrics_dir / f"{run_id}_cv_metrics.csv"
    test_file = metrics_dir / f"{run_id}_test_metrics.csv"
    metrics_df.to_csv(cv_file, index=False)
    test_metrics_df.to_csv(test_file, index=False)

    latest_file = models_dir / "latest_run.json"
    with open(latest_file, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "run_id": run_id,
                "feature_columns": FEATURE_COLUMNS,
                "artifacts": artifact_paths,
                "metrics_cv_csv": str(cv_file),
                "metrics_test_csv": str(test_file),
            },
            fh,
            indent=2,
        )

    return artifact_paths


def persist_metrics(engine, run_id, cv_metrics_df, test_metrics_df):
    payload = pd.concat([cv_metrics_df, test_metrics_df], ignore_index=True)
    payload.insert(0, "run_id", run_id)

    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM features.model_metrics WHERE run_id = :run_id"),
            {"run_id": run_id},
        )

    payload.to_sql(
        "model_metrics",
        engine,
        schema="features",
        if_exists="append",
        index=False,
        chunksize=1000,
    )


def build_test_metrics(models, X_test, y_test):
    rows = []
    for model_name, payload in models.items():
        y_prob = payload["model"].predict_proba(X_test)[:, 1]
        metrics = compute_metrics(y_test, y_prob, payload["threshold"])
        rows.append(
            {
                "model_name": model_name,
                "split_name": "test",
                "fold": 0,
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def main():
    args = parse_args()
    run_id = args.run_id

    print("\n" + "=" * 70)
    print("PHASE 2: MODEL TRAINING")
    print("=" * 70)
    print(f"Run ID: {run_id}")

    engine = create_engine(PG_URI)
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "outputs" / "phase2"

    try:
        upsert_run_status(engine, run_id, "training", "Phase 2 training started")

        df, X, y = load_training_data(engine)
        print(f"Loaded training rows: {len(df)}")

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
            stratify=y,
        )

        print("Running leakage and sanity diagnostics...")
        leakage_report = evaluate_leakage_risks(df, X, y, X_train, X_test, y_train)
        leak_file = save_leakage_report(run_id, leakage_report, output_dir)
        print(f"Saved: {leak_file}")

        print("Running 5-fold cross-validation...")
        cv_metrics_df = run_cross_validation(X_train.reset_index(drop=True), y_train.reset_index(drop=True))

        print("Training final models...")
        models = train_final_models(X_train, y_train)

        print("Evaluating test split...")
        test_metrics_df = build_test_metrics(models, X_test, y_test)

        artifact_paths = save_artifacts(run_id, models, cv_metrics_df, test_metrics_df, output_dir)
        persist_metrics(engine, run_id, cv_metrics_df, test_metrics_df)

        summary = (
            test_metrics_df[["model_name", "pr_auc", "roc_auc", "f1", "precision", "recall", "threshold"]]
            .sort_values("pr_auc", ascending=False)
            .to_string(index=False)
        )
        print("\nTest metrics (primary metric: PR-AUC):")
        print(summary)

        if leakage_report["risk_flags"]:
            print("\nLeakage risk flags:")
            for flag in leakage_report["risk_flags"]:
                print(f"  - {flag}")
        else:
            print("\nLeakage risk flags: none")

        upsert_run_status(
            engine,
            run_id,
            "trained",
            notes=f"Training finished. Artifacts: {artifact_paths}; Leakage: {leak_file}",
            finish=False,
        )

        print("\n[OK] Phase 2 training complete")
        return True

    except Exception as exc:
        upsert_run_status(engine, run_id, "failed", notes=f"Training failed: {exc}", finish=True)
        print(f"[ERR] Training failed: {exc}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        engine.dispose()


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
