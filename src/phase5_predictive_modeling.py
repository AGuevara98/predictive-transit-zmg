"""
Phase 5: Predictive Modeling & Interpretability
================================================
Trains Random Forest and XGBoost classifiers to predict Phase 4 transit suitability 
typologies using the 16 normalized NPP-V features. 
Uses SHAP for multi-class model interpretability.
"""

import sys
import pickle
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import shap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sqlalchemy import create_engine
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)

def load_data():
    print("[Step 1] Loading features and cluster labels from DB...")
    query = """
        SELECT 
            f.cve_ageb,
            f.n_intersections_n, f.n_street_density_n, f.n_intersection_density_n,
            f.p_poi_density_n, f.p_employment_proxy_n, f.p_retail_density_n, f.p_service_density_n, f.p_land_use_mix_n,
            f.pe_population_n, f.pe_pop_density_n, f.pe_marginacion_n, f.pe_rezago_n, f.pe_dep_ratio_n, f.pe_youth_share_n,
            f.v_ntl_median_n, f.v_ridership_annual_n,
            c.cluster_id,
            c.typology_name
        FROM features.nppv_features f
        JOIN features.nppv_clusters c ON f.cve_ageb = c.cve_ageb
    """
    df = pd.read_sql(query, ENGINE)
    
    feature_cols = [col for col in df.columns if col.endswith('_n')]
    X = df[feature_cols].copy()
    
    # Ensure cluster_id starts from 0 for XGBoost
    unique_clusters = sorted(df['cluster_id'].unique())
    cluster_mapping = {old_id: new_id for new_id, old_id in enumerate(unique_clusters)}
    y = df['cluster_id'].map(cluster_mapping)
    
    # Save the mapping so we know what class corresponds to what typology
    mapping_df = df[['cluster_id', 'typology_name']].drop_duplicates().sort_values('cluster_id')
    mapping_df['model_class_id'] = mapping_df['cluster_id'].map(cluster_mapping)
    
    print(f"  [OK] Loaded {len(df)} rows, {len(feature_cols)} features.")
    print(f"  Class Mapping: \n{mapping_df}")
    
    return X, y, feature_cols, mapping_df

def train_and_evaluate_models(X, y):
    print("\n[Step 2] Evaluating models via 5-Fold Cross-Validation...")
    
    models = {
        "RandomForest": RandomForestClassifier(n_estimators=300, max_depth=16, random_state=42, n_jobs=-1),
        "XGBoost": XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42, n_jobs=-1, objective='multi:softmax')
    }
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = {
        'accuracy': 'accuracy',
        'macro_precision': 'precision_macro',
        'macro_recall': 'recall_macro',
        'macro_f1': 'f1_macro'
    }
    
    metrics = []
    trained_models = {}
    
    for name, model in models.items():
        print(f"  Cross-validating {name}...")
        scores = cross_validate(model, X, y, cv=cv, scoring=scoring, n_jobs=-1)
        
        mets = {
            "model_name": name,
            "accuracy": float(scores['test_accuracy'].mean()),
            "macro_precision": float(scores['test_macro_precision'].mean()),
            "macro_recall": float(scores['test_macro_recall'].mean()),
            "macro_f1": float(scores['test_macro_f1'].mean())
        }
        metrics.append(mets)
        print(f"    -> Mean Macro F1: {mets['macro_f1']:.4f}")
        
        print(f"  Training final {name} on full dataset...")
        model.fit(X, y)
        trained_models[name] = model
        
    return trained_models, metrics

def normalize_multiclass_shap_values(shap_values_list):
    # SHAP TreeExplainer for multi-class returns a list of arrays (one for each class)
    # We want to aggregate to get mean absolute SHAP per feature per class
    if isinstance(shap_values_list, list):
        # SHAP version < 0.40 behavior for multi-class RF/XGB
        return np.array(shap_values_list)
    elif hasattr(shap_values_list, 'values'):
        # Explanation object (SHAP >= 0.40)
        # shape is usually (n_samples, n_features, n_classes) for XGBoost multi-class
        if len(shap_values_list.values.shape) == 3:
            # Transpose to (n_classes, n_samples, n_features) for consistency
            return np.transpose(shap_values_list.values, (2, 0, 1))
        return shap_values_list.values
    else:
        # Fallback for standard numpy arrays
        arr = np.asarray(shap_values_list)
        if len(arr.shape) == 3:
             # Transpose to (n_classes, n_samples, n_features) if it's (samples, features, classes)
             if arr.shape[2] <= 10 and arr.shape[0] > arr.shape[2]: # crude heuristic
                 return np.transpose(arr, (2, 0, 1))
        return arr

def run_shap_analysis(models, X_full, feature_cols, mapping_df, out_dir):
    print("\n[Step 3] Running SHAP Interpretability...")
    
    shap_results = {}
    
    # We use a subset if X is too large to speed up SHAP, but 2000 rows is small enough.
    X_sample = X_full.sample(n=min(len(X_full), 1000), random_state=42) if len(X_full) > 1000 else X_full
    
    class_names = mapping_df.sort_values('model_class_id')['typology_name'].tolist()
    
    for name, model in models.items():
        print(f"  Computing SHAP for {name}...")
        explainer = shap.TreeExplainer(model)
        
        # Some models require check_additivity=False if there are minor rounding differences
        try:
            shap_vals = explainer.shap_values(X_sample)
        except Exception:
            shap_vals = explainer.shap_values(X_sample, check_additivity=False)
            
        shap_array = normalize_multiclass_shap_values(shap_vals)
        
        # shap_array should be shape: (n_classes, n_samples, n_features)
        
        # Ensure we have a list of arrays for the summary plot
        if len(shap_array.shape) == 3:
            shap_list_for_plot = [shap_array[i, :, :] for i in range(shap_array.shape[0])]
        else:
            # Binary classification or unexpected shape fallback
            shap_list_for_plot = shap_array
            
        # Summary Plot (Multi-class creates a stacked bar chart)
        plt.figure(figsize=(10, 6))
        shap.summary_plot(shap_list_for_plot, X_sample, feature_names=feature_cols, class_names=class_names, show=False)
        plt.title(f"SHAP Feature Importance ({name})")
        plt.tight_layout()
        plt.savefig(out_dir / f"shap_summary_{name}.png", dpi=300)
        plt.close()
        
        # Calculate mean absolute SHAP for each feature per class, and total
        mean_abs_shap = {}
        for feature_idx, feature in enumerate(feature_cols):
            feature_impact = {"total": 0}
            if len(shap_array.shape) == 3:
                for class_idx, class_name in enumerate(class_names):
                    impact = float(np.abs(shap_array[class_idx, :, feature_idx]).mean())
                    feature_impact[class_name] = impact
                    feature_impact["total"] += impact
            else:
                # Binary fallback
                impact = float(np.abs(shap_array[:, feature_idx]).mean())
                feature_impact["total"] = impact
                
            mean_abs_shap[feature] = feature_impact
            
        # Create a DF for easier reporting
        imp_df = pd.DataFrame.from_dict(mean_abs_shap, orient='index')
        imp_df.index.name = 'feature'
        imp_df = imp_df.sort_values('total', ascending=False).reset_index()
        imp_df.to_csv(out_dir / f"shap_importance_{name}.csv", index=False)
        
        shap_results[name] = imp_df
        
    return shap_results

def save_artifacts(models, metrics, mapping_df, out_dir):
    print("\n[Step 4] Saving artifacts...")
    
    # Save Metrics
    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(out_dir / "model_metrics.csv", index=False)
    
    # Save mapping
    mapping_df.to_csv(out_dir / "class_mapping.csv", index=False)
    
    # Save Models
    models_dir = out_dir / "models"
    models_dir.mkdir(exist_ok=True, parents=True)
    for name, model in models.items():
        with open(models_dir / f"{name}.pkl", 'wb') as f:
            pickle.dump(model, f)
            
    print("  [OK] Artifacts saved.")

if __name__ == "__main__":
    out_dir = Path("outputs/phase5")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    X, y, feature_cols, mapping_df = load_data()
    
    models, metrics = train_and_evaluate_models(X, y)
    shap_results = run_shap_analysis(models, X, feature_cols, mapping_df, out_dir)
    save_artifacts(models, metrics, mapping_df, out_dir)
    
    print("\n[DONE] Phase 5 Predictive Modeling Complete!")
