"""
W3.3 — Supervised Model Re-trained on Coverage-Gap Target
==========================================================
Re-points the Phase 2 binary classifier at the W3 coverage-gap target
(is_high_gap) instead of the circular stop-proximity label.

Binary target: is_high_gap = 1 if gap_category == 'High-gap' else 0

Features: 14 normalized NPP-V indicators from features.nppv_features.
  All transit-supply features (route_km_800m, stops_*) are excluded to
  prevent reintroducing the circularity that W3 was designed to remove.

Outputs:
  outputs/w3/models/w3_coverage_gap_v1_{model}.pkl
  outputs/w3/metrics/w3_coverage_gap_v1_cv_metrics.csv
  outputs/w3/metrics/w3_coverage_gap_v1_test_metrics.csv
  outputs/w3/metrics/w3_coverage_gap_v1_leakage_checks.json
  outputs/w3/shap/w3_coverage_gap_v1_{model}_importance.csv
  outputs/w3/shap/w3_coverage_gap_v1_{model}_summary.png
"""

import json
import pickle
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
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

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)
PROJECT_ROOT = Path(__file__).parent.parent

RUN_ID = "w3_coverage_gap_v1"

# 14 normalized NPP-V features — all transit-supply variables excluded
FEATURE_COLUMNS = [
    "n_intersections_n",
    "n_intersection_density_n",
    "n_street_density_n",
    "p_poi_density_n",
    "p_employment_proxy_n",
    "p_retail_density_n",
    "p_service_density_n",
    "p_land_use_mix_n",
    "pe_population_n",
    "pe_pop_density_n",
    "pe_marginacion_n",
    "pe_rezago_n",
    "pe_dep_ratio_n",
    "pe_youth_share_n",
]

MAX_SHAP_ROWS = 500


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_training_data() -> pd.DataFrame:
    print("[Step 1] Loading features and coverage-gap labels...")
    with ENGINE.raw_connection() as conn:
        features_df = pd.read_sql(
            f"SELECT cve_ageb, {', '.join(FEATURE_COLUMNS)} FROM features.nppv_features",
            conn,
        )
        labels_df = pd.read_sql(
            "SELECT cve_ageb, gap_category FROM features.ageb_coverage_gap",
            conn,
        )

    df = features_df.merge(labels_df, on="cve_ageb", how="inner")
    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["is_high_gap"] = (df["gap_category"] == "High-gap").astype(int)

    print(f"  [OK] {len(df):,} AGEBs with features and labels")
    print(f"  High-gap: {df['is_high_gap'].sum():,} ({df['is_high_gap'].mean():.1%})")
    return df


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def find_best_f1_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    if thresholds.size == 0:
        return 0.5
    precision = precision[:-1]
    recall = recall[:-1]
    denom = precision + recall
    f1_vals = np.where(denom > 0, 2 * precision * recall / denom, 0.0)
    return float(thresholds[np.argmax(f1_vals)])


def compute_metrics(y_true, y_prob, threshold) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "pr_auc":    float(average_precision_score(y_true, y_prob)),
        "roc_auc":   float(roc_auc_score(y_true, y_prob)),
        "f1":        float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall":    float(recall_score(y_true, y_pred, zero_division=0)),
        "threshold": float(threshold),
    }


# ---------------------------------------------------------------------------
# Model factories
# ---------------------------------------------------------------------------

def model_factories() -> dict:
    return {
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=300, max_depth=16, min_samples_leaf=2,
            random_state=42, n_jobs=-1,
        ),
        "lightgbm": lambda: LGBMClassifier(
            n_estimators=350, learning_rate=0.05, num_leaves=31,
            subsample=0.9, colsample_bytree=0.9,
            objective="binary", random_state=42, n_jobs=-1, verbosity=-1,
        ),
    }


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------

def run_cross_validation(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    print("[Step 3] Running 5-fold stratified CV...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    rows = []
    for model_name, factory in model_factories().items():
        for fold_id, (tr_idx, va_idx) in enumerate(cv.split(X, y), start=1):
            model = factory()
            model.fit(X.iloc[tr_idx], y.iloc[tr_idx])
            y_prob = model.predict_proba(X.iloc[va_idx])[:, 1]
            tr_prob = model.predict_proba(X.iloc[tr_idx])[:, 1]
            threshold = find_best_f1_threshold(y.iloc[tr_idx].to_numpy(), tr_prob)
            metrics = compute_metrics(y.iloc[va_idx].to_numpy(), y_prob, threshold)
            rows.append({"model_name": model_name, "split_name": "cv", "fold": fold_id, **metrics})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Leakage diagnostics
# ---------------------------------------------------------------------------

def run_leakage_checks(df: pd.DataFrame, X: pd.DataFrame, y: pd.Series,
                       X_train: pd.DataFrame, y_train: pd.Series) -> dict:
    print("[Step 4] Leakage diagnostics...")
    positive_rate = float(y.mean())
    train_vecs = set(map(tuple, X_train.round(8).to_numpy()))

    univariate = []
    for feat in FEATURE_COLUMNS:
        vals = X[feat].to_numpy()
        pr_pos = average_precision_score(y, vals)
        pr_neg = average_precision_score(y, -vals)
        univariate.append({
            "feature": feat,
            "best_direction": "positive" if pr_pos >= pr_neg else "negative",
            "best_pr_auc": float(max(pr_pos, pr_neg)),
        })
    univariate.sort(key=lambda r: r["best_pr_auc"], reverse=True)

    # Label-shuffle sanity: if shuffled labels still yield high PR-AUC, features leak target
    shuffled = y_train.sample(frac=1.0, random_state=42).reset_index(drop=True)
    X_tr_reset = X_train.reset_index(drop=True)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    shuffle_results = {}
    for model_name, factory in model_factories().items():
        scores = []
        for tr_idx, va_idx in cv.split(X_tr_reset, shuffled):
            m = factory()
            m.fit(X_tr_reset.iloc[tr_idx], shuffled.iloc[tr_idx])
            scores.append(float(
                average_precision_score(shuffled.iloc[va_idx],
                                        m.predict_proba(X_tr_reset.iloc[va_idx])[:, 1])
            ))
        shuffle_results[model_name] = {"mean_pr_auc": float(np.mean(scores)), "folds": scores}

    flags = []
    if univariate and univariate[0]["best_pr_auc"] > 0.98:
        flags.append(f"Single feature near-perfect separation: {univariate[0]['feature']} PR-AUC={univariate[0]['best_pr_auc']:.4f}")
    for mn, payload in shuffle_results.items():
        if payload["mean_pr_auc"] > max(positive_rate + 0.12, 0.65):
            flags.append(f"Label-shuffle sanity high for {mn}: {payload['mean_pr_auc']:.4f}")

    return {
        "positive_rate": positive_rate,
        "n_rows": len(df),
        "top_univariate_pr_auc": univariate[:6],
        "label_shuffle_sanity": shuffle_results,
        "risk_flags": flags,
    }


# ---------------------------------------------------------------------------
# Final model training
# ---------------------------------------------------------------------------

def train_final_models(X_train: pd.DataFrame, y_train: pd.Series) -> dict:
    print("[Step 5] Training final models on full train split...")
    trained = {}
    for model_name, factory in model_factories().items():
        model = factory()
        model.fit(X_train, y_train)
        tr_prob = model.predict_proba(X_train)[:, 1]
        threshold = find_best_f1_threshold(y_train.to_numpy(), tr_prob)
        trained[model_name] = {"model": model, "threshold": threshold}
        print(f"  [OK] {model_name} trained")
    return trained


def build_test_metrics(models: dict, X_test: pd.DataFrame, y_test: pd.Series) -> pd.DataFrame:
    rows = []
    for model_name, payload in models.items():
        y_prob = payload["model"].predict_proba(X_test)[:, 1]
        metrics = compute_metrics(y_test.to_numpy(), y_prob, payload["threshold"])
        rows.append({"model_name": model_name, "split_name": "test", "fold": 0, **metrics})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# SHAP analysis
# ---------------------------------------------------------------------------

def normalize_shap_values(raw):
    if isinstance(raw, list):
        return np.asarray(raw[1]) if len(raw) == 2 else np.asarray(raw[0])
    arr = np.asarray(raw)
    return arr[:, :, 1] if arr.ndim == 3 else arr


def run_shap(models: dict, X_train: pd.DataFrame, shap_dir: Path, run_id: str):
    print("[Step 7] SHAP interpretability...")
    X_shap = X_train.sample(n=min(MAX_SHAP_ROWS, len(X_train)), random_state=42).reset_index(drop=True)
    for model_name, payload in models.items():
        explainer = shap.TreeExplainer(payload["model"])
        raw_shap = explainer.shap_values(X_shap)
        shap_vals = normalize_shap_values(raw_shap)
        mean_abs = np.abs(shap_vals).mean(axis=0)

        importance_df = pd.DataFrame({
            "feature_name": FEATURE_COLUMNS,
            "mean_abs_shap": mean_abs,
        }).sort_values("mean_abs_shap", ascending=False)
        importance_df["rank_position"] = np.arange(1, len(importance_df) + 1)

        csv_path = shap_dir / f"{run_id}_{model_name}_importance.csv"
        importance_df.to_csv(csv_path, index=False)

        png_path = shap_dir / f"{run_id}_{model_name}_summary.png"
        plt.figure(figsize=(10, 6))
        shap.summary_plot(shap_vals, X_shap, show=False, plot_size=(10, 6))
        plt.title(f"SHAP Summary — {model_name} ({run_id})")
        plt.tight_layout()
        plt.savefig(png_path, dpi=200, bbox_inches="tight")
        plt.close()

        print(f"  [OK] {model_name} — top-5 SHAP features:")
        for _, row in importance_df.head(5).iterrows():
            print(f"    {int(row['rank_position']):2d}. {row['feature_name']:<35s} {row['mean_abs_shap']:.4f}")


# ---------------------------------------------------------------------------
# Artifact saving
# ---------------------------------------------------------------------------

def save_artifacts(run_id: str, models: dict, cv_df: pd.DataFrame,
                   test_df: pd.DataFrame, leakage: dict, out_dir: Path):
    models_dir = out_dir / "models"
    metrics_dir = out_dir / "metrics"
    models_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths = {}
    for model_name, payload in models.items():
        p = models_dir / f"{run_id}_{model_name}.pkl"
        with open(p, "wb") as fh:
            pickle.dump({
                "model_name": model_name,
                "feature_columns": FEATURE_COLUMNS,
                "threshold": payload["threshold"],
                "trained_at": datetime.now(UTC).isoformat(),
                "run_id": run_id,
                "model": payload["model"],
            }, fh)
        artifact_paths[model_name] = str(p)

    cv_df.to_csv(metrics_dir / f"{run_id}_cv_metrics.csv", index=False)
    test_df.to_csv(metrics_dir / f"{run_id}_test_metrics.csv", index=False)

    with open(metrics_dir / f"{run_id}_leakage_checks.json", "w") as fh:
        json.dump(leakage, fh, indent=2)

    with open(models_dir / f"{run_id}_latest.json", "w") as fh:
        json.dump({
            "run_id": run_id,
            "feature_columns": FEATURE_COLUMNS,
            "artifacts": artifact_paths,
        }, fh, indent=2)

    return artifact_paths


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\n" + "="*70)
    print("W3.3 -- SUPERVISED MODEL ON COVERAGE-GAP TARGET")
    print("="*70)
    print(f"Run ID: {RUN_ID}")

    out_dir = PROJECT_ROOT / "outputs" / "w3"
    shap_dir = out_dir / "shap"
    shap_dir.mkdir(parents=True, exist_ok=True)

    df = load_training_data()

    X = df[FEATURE_COLUMNS].reset_index(drop=True)
    y = df["is_high_gap"].reset_index(drop=True)

    print("[Step 2] Train/test split (70/30 stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y,
    )
    print(f"  Train: {len(X_train):,}  Test: {len(X_test):,}")

    cv_df = run_cross_validation(X_train.reset_index(drop=True), y_train.reset_index(drop=True))

    leakage = run_leakage_checks(df, X, y, X_train, y_train)

    models = train_final_models(X_train, y_train)

    print("[Step 6] Test evaluation...")
    test_df = build_test_metrics(models, X_test, y_test)

    run_shap(models, X_train, shap_dir, RUN_ID)

    artifact_paths = save_artifacts(RUN_ID, models, cv_df, test_df, leakage, out_dir)

    print("\n" + "="*70)
    print("W3.3 RETRAIN COMPLETE")
    print("="*70)
    print("\nTest metrics (primary metric: PR-AUC):")
    print(test_df[["model_name", "pr_auc", "roc_auc", "f1", "precision", "recall", "threshold"]]
          .sort_values("pr_auc", ascending=False).to_string(index=False))

    if leakage["risk_flags"]:
        print("\nLeakage risk flags:")
        for flag in leakage["risk_flags"]:
            print(f"  [WARN] {flag}")
    else:
        print("\nLeakage risk flags: none")

    print("\nCV mean metrics (across all folds):")
    print(cv_df.groupby("model_name")[["pr_auc", "roc_auc", "f1"]].mean().to_string())

    print(f"\nArtifacts saved to: outputs/w3/")
    ENGINE.dispose()


if __name__ == "__main__":
    main()
