"""
Phase 2: Predict Suitability Surface

Scores all AGEBs using trained RandomForest and LightGBM models and writes
outputs to PostgreSQL, CSV, and GeoJSON for QGIS.

Usage:
    python src/phase2_predict_surface.py --run-id <run_id>
"""

import argparse
import json
import pickle
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI


def parse_args():
    parser = argparse.ArgumentParser(description="Predict AGEB suitability surface")
    parser.add_argument("--run-id", required=True, help="Run identifier from training")
    return parser.parse_args()


def load_model_artifact(run_id, model_name, models_dir):
    artifact_path = models_dir / f"{run_id}_{model_name}.pkl"
    if not artifact_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {artifact_path}")

    with open(artifact_path, "rb") as fh:
        return pickle.load(fh)


def load_prediction_frame(engine, feature_columns):
    cols = ", ".join(feature_columns)
    query = f"""
    SELECT ageb_id, {cols}
    FROM features.master_suitability
    ORDER BY ageb_id;
    """
    df = pd.read_sql(text(query), engine)
    if df.empty:
        raise ValueError("features.master_suitability returned 0 rows")

    for col in feature_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df


def persist_predictions(engine, run_id, df_out):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM features.ageb_suitability_predictions WHERE run_id = :run_id"),
            {"run_id": run_id},
        )

    df_out.to_sql(
        "ageb_suitability_predictions",
        engine,
        schema="features",
        if_exists="append",
        index=False,
        chunksize=1000,
    )


def export_predictions_geojson(engine, run_id, out_geojson):
    query = """
    SELECT
        p.run_id,
        p.ageb_id,
        p.score_rf,
        p.score_lgbm,
        p.class_rf,
        p.class_lgbm,
        p.threshold_rf,
        p.threshold_lgbm,
        ST_AsGeoJSON(ST_Transform(a.geom, 4326)) AS geometry_json
    FROM features.ageb_suitability_predictions p
    JOIN base.ageb a ON a.cvegeo = p.ageb_id
    WHERE p.run_id = :run_id
    ORDER BY p.ageb_id;
    """

    rows = pd.read_sql(text(query), engine, params={"run_id": run_id})
    if rows.empty:
        raise ValueError("No prediction rows available for GeoJSON export")

    features = []
    for _, row in rows.iterrows():
        geometry = json.loads(row["geometry_json"])
        props = {
            "run_id": row["run_id"],
            "ageb_id": row["ageb_id"],
            "score_rf": float(row["score_rf"]),
            "score_lgbm": float(row["score_lgbm"]),
            "class_rf": int(row["class_rf"]),
            "class_lgbm": int(row["class_lgbm"]),
            "threshold_rf": float(row["threshold_rf"]),
            "threshold_lgbm": float(row["threshold_lgbm"]),
        }
        features.append({"type": "Feature", "geometry": geometry, "properties": props})

    fc = {"type": "FeatureCollection", "features": features}
    with open(out_geojson, "w", encoding="utf-8") as fh:
        json.dump(fc, fh)


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
    print("PHASE 2: PREDICT SUITABILITY SURFACE")
    print("=" * 70)
    print(f"Run ID: {run_id}")

    engine = create_engine(PG_URI)
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "outputs" / "phase2" / "models"
    pred_dir = project_root / "outputs" / "phase2" / "predictions"
    pred_dir.mkdir(parents=True, exist_ok=True)

    try:
        rf_artifact = load_model_artifact(run_id, "random_forest", models_dir)
        lgbm_artifact = load_model_artifact(run_id, "lightgbm", models_dir)

        feature_columns = rf_artifact["feature_columns"]
        if feature_columns != lgbm_artifact["feature_columns"]:
            raise ValueError("Feature mismatch between random_forest and lightgbm artifacts")

        df = load_prediction_frame(engine, feature_columns)
        X = df[feature_columns]

        score_rf = rf_artifact["model"].predict_proba(X)[:, 1]
        score_lgbm = lgbm_artifact["model"].predict_proba(X)[:, 1]

        thr_rf = float(rf_artifact["threshold"])
        thr_lgbm = float(lgbm_artifact["threshold"])

        df_out = pd.DataFrame(
            {
                "run_id": run_id,
                "ageb_id": df["ageb_id"],
                "score_rf": score_rf,
                "score_lgbm": score_lgbm,
                "class_rf": (score_rf >= thr_rf).astype(int),
                "class_lgbm": (score_lgbm >= thr_lgbm).astype(int),
                "threshold_rf": thr_rf,
                "threshold_lgbm": thr_lgbm,
            }
        )

        persist_predictions(engine, run_id, df_out)

        out_csv = pred_dir / f"{run_id}_ageb_predictions.csv"
        df_out.to_csv(out_csv, index=False)

        summary = pd.DataFrame(
            {
                "model": ["random_forest", "lightgbm"],
                "min_score": [df_out["score_rf"].min(), df_out["score_lgbm"].min()],
                "max_score": [df_out["score_rf"].max(), df_out["score_lgbm"].max()],
                "mean_score": [df_out["score_rf"].mean(), df_out["score_lgbm"].mean()],
                "positive_rate": [df_out["class_rf"].mean(), df_out["class_lgbm"].mean()],
            }
        )
        summary_file = pred_dir / f"{run_id}_prediction_summary.csv"
        summary.to_csv(summary_file, index=False)

        geojson_file = pred_dir / f"{run_id}_ageb_predictions.geojson"
        export_predictions_geojson(engine, run_id, geojson_file)

        update_run_status(
            engine,
            run_id,
            "predicted",
            notes=f"Prediction complete. CSV: {out_csv}; GeoJSON: {geojson_file}",
            finish=False,
        )

        print(f"Scored AGEB rows: {len(df_out)}")
        print(f"Saved: {out_csv}")
        print(f"Saved: {summary_file}")
        print(f"Saved: {geojson_file}")
        print("\n[OK] Phase 2 prediction complete")
        return True

    except Exception as exc:
        update_run_status(engine, run_id, "failed", f"Prediction failed: {exc}", finish=True)
        print(f"[ERR] Prediction failed: {exc}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        engine.dispose()


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
