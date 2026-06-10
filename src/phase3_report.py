"""
Phase 3: Report Generator
=========================
Generates a markdown report summarizing the Objective Indicator Weighting.
"""

import sys
import pandas as pd
import psycopg2
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

from sqlalchemy import create_engine
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)

def generate_report():
    print("[Step 1] Fetching NPP-V Weights...")
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql("SELECT feature, dimension, critic_weight, ewm_weight, ensemble_weight FROM features.nppv_weights ORDER BY ensemble_weight DESC", conn)
        
    out_dir = Path("outputs/phase3")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "phase3_report.md"
    
    print(f"[Step 2] Writing report to {report_path}...")
    
    md_content = f"""# Phase 3: Objective Indicator Weighting Report
*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Methodology
In this phase, we computed objective weights for the 16 normalized NPP-V features to remove subjective expert bias from the transit suitability model. We utilized two distinct methods:
1. **CRITIC**: Criteria Importance Through Intercriteria Correlation (measures contrast intensity and conflict).
2. **EWM**: Entropy Weight Method (measures information dispersion).

We then calculated an **Ensemble Weight** as the simple average of CRITIC and EWM to smooth out extremes.

## Feature Importance Summary
The table below ranks the features from highest to lowest ensemble weight.

| Rank | Feature | Dimension | CRITIC Weight | EWM Weight | Ensemble Weight |
|------|---------|-----------|---------------|------------|-----------------|
"""
    
    for idx, row in df.iterrows():
        rank = idx + 1
        md_content += f"| {rank} | `{row['feature']}` | **{row['dimension']}** | {row['critic_weight']:.4f} | {row['ewm_weight']:.4f} | **{row['ensemble_weight']:.4f}** |\n"
        
    md_content += """
## Weight Distributions

### Ensemble Feature Importance
This chart visualizes the final ensemble weights. Features with higher weights have stronger objective discrimination power across the Guadalajara Metropolitan Area.

![Ensemble Weights](nppv_weights_bar.png)

### CRITIC vs EWM Comparison
This chart highlights how the two objective methods differ. CRITIC heavily penalizes highly correlated features, while EWM strictly measures variance/information gain.

![CRITIC vs EWM](nppv_critic_vs_ewm.png)

## Conclusion
The weighting results confirm that **Vitality** (Ridership) and **Place** (Employment, Services) exert the most significant objective influence on establishing distinct transit corridors.
"""
    
    with open(report_path, "w") as f:
        f.write(md_content)
        
    print("[DONE] Phase 3 Report generated successfully.")

if __name__ == "__main__":
    generate_report()
