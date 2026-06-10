"""
Phase 5: Report Generator
=========================
Generates a markdown report summarizing the predictive models' 
performance and SHAP feature importance.
"""

import sys
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

def generate_report():
    out_dir = Path("outputs/phase5")
    
    print("[Step 1] Loading metrics and SHAP results...")
    metrics_df = pd.read_csv(out_dir / "model_metrics.csv")
    rf_shap = pd.read_csv(out_dir / "shap_importance_RandomForest.csv")
    xgb_shap = pd.read_csv(out_dir / "shap_importance_XGBoost.csv")
    mapping_df = pd.read_csv(out_dir / "class_mapping.csv")
    
    print("[Step 2] Loading Phase 3 weights for comparison...")
    engine = create_engine(PG_URI)
    weights_df = pd.read_sql("SELECT feature, ensemble_weight FROM features.nppv_weights", engine)
    # Map weights back to normalized feature names
    weights_df['feature_n'] = weights_df['feature'] + '_n'
    weights_dict = dict(zip(weights_df['feature_n'], weights_df['ensemble_weight']))
    
    print("[Step 3] Generating Markdown Report...")
    report_lines = [
        "# Phase 5: Predictive Modeling & Interpretability Report",
        "",
        "This report summarizes the performance of the predictive models trained to classify the Phase 4 transit suitability typologies.",
        "",
        "## 1. Model Evaluation Metrics",
        "",
        "The models were evaluated using 5-Fold Cross-Validation. The target variable is the transit suitability typology. Metrics represent the mean across all 5 folds.",
        ""
    ]
    
    # Format metrics table
    report_lines.append("| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 |")
    report_lines.append("|-------|----------|-----------------|--------------|----------|")
    for _, row in metrics_df.iterrows():
        report_lines.append(f"| {row['model_name']} | {row['accuracy']:.4f} | {row['macro_precision']:.4f} | {row['macro_recall']:.4f} | {row['macro_f1']:.4f} |")
    
    report_lines.append("")
    report_lines.append("## 2. SHAP Feature Importance (XGBoost)")
    report_lines.append("")
    report_lines.append("The following table presents the top 10 driving features identified by XGBoost's SHAP values, compared against the objective weights assigned in Phase 3.")
    report_lines.append("")
    
    # Class names for SHAP table
    classes = [c for c in mapping_df['typology_name'].tolist()]
    headers = ["Feature", "Total SHAP"] + classes + ["Phase 3 Weight"]
    report_lines.append("| " + " | ".join(headers) + " |")
    report_lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    
    for i, row in xgb_shap.head(10).iterrows():
        feat = row['feature']
        total = row['total']
        class_vals = [f"{row.get(c, 0):.4f}" for c in classes]
        p3_weight = f"{weights_dict.get(feat, 0):.4f}"
        
        row_str = f"| `{feat}` | **{total:.4f}** | " + " | ".join(class_vals) + f" | {p3_weight} |"
        report_lines.append(row_str)
        
    report_lines.append("")
    report_lines.append("## 3. Typology Drivers")
    report_lines.append("")
    
    # For each class, find the top 3 features
    for c in classes:
        report_lines.append(f"### {c}")
        if c in xgb_shap.columns:
            top_for_class = xgb_shap.sort_values(c, ascending=False).head(3)
            report_lines.append(f"The primary predictive drivers for **{c}** are:")
            for _, r in top_for_class.iterrows():
                report_lines.append(f"- `{r['feature']}` (SHAP magnitude: {r[c]:.4f})")
        report_lines.append("")
        
    report_lines.append("## 4. Visualizations")
    report_lines.append("")
    report_lines.append("- [XGBoost SHAP Summary](shap_summary_XGBoost.png)")
    report_lines.append("- [Random Forest SHAP Summary](shap_summary_RandomForest.png)")
    
    report_path = out_dir / "phase5_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"  [OK] Report saved to {report_path}")

if __name__ == "__main__":
    generate_report()
