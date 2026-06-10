"""
Phase 4: Report Generator
=========================
Generates a markdown report summarizing the Clustering results.
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

def generate_report():
    print("[Step 1] Loading Cluster Profiles...")
    out_dir = Path("outputs/phase4")
    profiles_path = out_dir / "cluster_profiles.csv"
    
    if not profiles_path.exists():
        print("ERROR: Cluster profiles not found. Run phase4_clustering.py first.")
        return
        
    df = pd.read_csv(profiles_path)
    
    print(f"[Step 2] Writing report to {out_dir / 'phase4_report.md'}...")
    
    md_content = f"""# Phase 4: Unsupervised Transit Suitability Clustering
*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Methodology
In Phase 4, we applied the Phase 3 ensemble weights to the 16 normalized NPP-V features. Using Scikit-Learn's **K-Means++** algorithm, we grouped the 2,068 AGEBs in the Guadalajara Metropolitan Area (ZMG) into distinct transit suitability typologies. The optimal number of clusters ($K$) was selected by maximizing the Silhouette Score.

## Cluster Visualization

The following PCA (Principal Component Analysis) scatter plot shows how the different typologies group together in a 2D projection based on their weighted feature distances.

![PCA Clusters](cluster_pca.png)

## Typology Profiles
The table below shows the average normalized feature values for each cluster. Features closer to 1.0 indicate very high densities/values for that typology.

"""
    
    # Add markdown table
    md_content += "| Feature | " + " | ".join([f"Typology {chr(65+i)}" for i in df['Cluster']]) + " |\n"
    md_content += "|---------|" + "|".join(["---" for _ in range(len(df))]) + "|\n"
    
    # Iterate columns (skip Cluster col)
    for col in df.columns:
        if col == "Cluster": continue
        md_content += f"| `{col}` | " + " | ".join([f"{val:.4f}" for val in df[col]]) + " |\n"
        
    md_content += """
## Conclusion
These typologies directly translate into targeted urban transit policies. For example, a typology with high *Place/Vitality* but low *Node* connectivity represents a "Transit Desert" ripe for immediate BRT or Light Rail expansion.
"""
    
    report_path = out_dir / "phase4_report.md"
    with open(report_path, "w") as f:
        f.write(md_content)
        
    print("[DONE] Phase 4 Report generated successfully.")

if __name__ == "__main__":
    generate_report()
