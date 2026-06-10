"""
Phase 2: SHAP Interpretability

Computes SHAP-based global feature importance for RandomForest and LightGBM
models, writes outputs to CSV/PNG, and persists rankings to PostgreSQL.

Usage:
    python src/phase2_shap_analysis.py --run-id <run_id>
"""

import argparse
import pickle
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sqlalchemy import create_engine, text

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI


MAX_SHAP_ROWS = 500


def parse_args():
    parser = argparse.ArgumentParser(description="Run SHAP interpretability for Phase 2")
    parser.add_argument("--run-id", required=True, help="Run identifier from training")
    return parser.parse_args()


def load_model_artifact(run_id, model_name, models_dir):
    artifact_path = models_dir / f"{run_id}_{model_name}.pkl"
    if not artifact_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {artifact_path}")

    with open(artifact_path, "rb") as fh:
        return pickle.load(fh)


def load_training_features(engine, feature_columns):
    cols = ", ".join(f"m.{col}" for col in feature_columns)
    query = f"""
    SELECT {cols}
    FROM features.training_labels t
    JOIN features.master_suitability m ON m.ageb_id = t.ageb_id
    ORDER BY t.ageb_id;
    """
    df = pd.read_sql(text(query), engine)
    if df.empty:
        raise ValueError("No rows available for SHAP analysis")

    for col in feature_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if len(df) > MAX_SHAP_ROWS:
        df = df.sample(n=MAX_SHAP_ROWS, random_state=42).reset_index(drop=True)

    return df


def normalize_shap_values(raw_values):
    if isinstance(raw_values, list):
        if len(raw_values) == 2:
            return np.asarray(raw_values[1])
        return np.asarray(raw_values[0])

    arr = np.asarray(raw_values)
    if arr.ndim == 3:
        return arr[:, :, 1]
    return arr


def compute_importance(model, X):
    explainer = shap.TreeExplainer(model)
    shap_values = normalize_shap_values(explainer.shap_values(X))
    mean_abs = np.abs(shap_values).mean(axis=0)
    return shap_values, mean_abs


def save_summary_plot(shap_values, X, out_file, title):
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X, show=False, plot_size=(10, 6))
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_file, dpi=200, bbox_inches="tight")
    plt.close()


def persist_importance(engine, run_id, model_name, importance_df):
    payload = importance_df.copy()
    payload.insert(0, "model_name", model_name)
    payload.insert(0, "run_id", run_id)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM features.model_feature_importance
                WHERE run_id = :run_id AND model_name = :model_name
                """
            ),
            {"run_id": run_id, "model_name": model_name},
        )

    payload.to_sql(
        "model_feature_importance",
        engine,
        schema="features",
        if_exists="append",
        index=False,
        chunksize=1000,
    )


def update_run_status(engine, run_id, status, notes, finish=False):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE features.model_runs
                SET status = :status,
                    notes = :notes
                WHERE run_id = :run_id
                """
            ),
            {"run_id": run_id, "status": status, "notes": notes},
        )
        if finish:
            conn.execute(
                text("UPDATE features.model_runs SET finished_at = NOW() WHERE run_id = :run_id"),
                {"run_id": run_id},
            )


def main():
    args = parse_args()
    run_id = args.run_id

    print("\n" + "=" * 70)
    print("PHASE 2: SHAP INTERPRETABILITY")
    print("=" * 70)
    print(f"Run ID: {run_id}")

    engine = create_engine(PG_URI)
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "outputs" / "phase2" / "models"
    shap_dir = project_root / "outputs" / "phase2" / "shap"
    shap_dir.mkdir(parents=True, exist_ok=True)

    try:
        rf_artifact = load_model_artifact(run_id, "random_forest", models_dir)
        lgbm_artifact = load_model_artifact(run_id, "lightgbm", models_dir)
        feature_columns = rf_artifact["feature_columns"]

        X = load_training_features(engine, feature_columns)

        for model_name, artifact in (
            ("random_forest", rf_artifact),
            ("lightgbm", lgbm_artifact),
        ):
            print(f"Computing SHAP for {model_name}...")
            shap_values, mean_abs = compute_importance(artifact["model"], X)

            importance_df = pd.DataFrame(
                {
                    "feature_name": feature_columns,
                    "mean_abs_shap": mean_abs,
                }
            ).sort_values("mean_abs_shap", ascending=False)
            importance_df["rank_position"] = np.arange(1, len(importance_df) + 1)
            importance_df = importance_df[["feature_name", "mean_abs_shap", "rank_position"]]

            out_csv = shap_dir / f"{run_id}_{model_name}_importance.csv"
            importance_df.to_csv(out_csv, index=False)

            out_png = shap_dir / f"{run_id}_{model_name}_summary.png"
            save_summary_plot(shap_values, X, out_png, f"SHAP Summary - {model_name}")

            persist_importance(engine, run_id, model_name, importance_df)
            print(f"Saved: {out_csv}")
            print(f"Saved: {out_png}")

        update_run_status(
            engine,
            run_id,
            "completed",
            notes="SHAP analysis completed; run ready for Phase 3 handoff",
            finish=True,
        )

        print("\n[OK] Phase 2 SHAP analysis complete")
        return True

    except Exception as exc:
        update_run_status(engine, run_id, "failed", f"SHAP failed: {exc}", finish=True)
        print(f"[ERR] SHAP failed: {exc}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        engine.dispose()


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
