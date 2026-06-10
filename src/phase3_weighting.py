"""
Phase 3: Objective Indicator Weighting (CRITIC & EWM)
=====================================================

Calculates objective weights for the 16 NPP-V features using:
1. CRITIC (Criteria Importance Through Intercriteria Correlation)
2. EWM (Entropy Weight Method)

Results are written to PostgreSQL table `features.nppv_weights`.
"""

import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import psycopg2
import psycopg2.extras
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)

NPPV_FEATURES = [
    "n_intersections_n", "n_street_density_n", "n_intersection_density_n",
    "p_poi_density_n", "p_employment_proxy_n", "p_retail_density_n",
    "p_service_density_n", "p_land_use_mix_n",
    "pe_population_n", "pe_pop_density_n", "pe_marginacion_n", "pe_rezago_n",
    "pe_dep_ratio_n", "pe_youth_share_n",
    "v_ntl_median_n", "v_ridership_annual_n"
]

def load_features():
    print("[Step 1] Loading normalized NPP-V features...")
    query = f"SELECT {', '.join(NPPV_FEATURES)} FROM features.nppv_features"
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(query, conn)
    print(f"  [OK] Loaded {len(df)} AGEB records with {len(NPPV_FEATURES)} features.")
    return df


def calculate_critic(df):
    print("\n[Step 2] Calculating CRITIC weights...")
    # Standard deviation (contrast intensity)
    std_dev = df.std()
    
    # Correlation matrix
    corr_matrix = df.corr()
    
    # Conflict (1 - correlation)
    conflict = (1 - corr_matrix).sum()
    
    # Information emission
    c_j = std_dev * conflict
    
    # Objective weights
    w_j = c_j / c_j.sum()
    return w_j.to_dict()


def calculate_ewm(df):
    print("\n[Step 3] Calculating EWM (Entropy) weights...")
    n = len(df)
    
    # Shift values slightly to avoid log(0)
    shifted_df = df + 1e-6
    
    # Calculate proportion P_ij
    p_ij = shifted_df / shifted_df.sum()
    
    # Calculate entropy E_j
    k = 1 / np.log(n)
    e_j = -k * (p_ij * np.log(p_ij)).sum()
    
    # Calculate diversity D_j (1 - E_j)
    d_j = 1 - e_j
    
    # Objective weights
    w_j = d_j / d_j.sum()
    return w_j.to_dict()


def save_to_db(critic_w, ewm_w):
    print("\n[Step 4] Saving weights to features.nppv_weights...")
    
    records = []
    for feature in NPPV_FEATURES:
        dimension = feature.split('_')[0].upper()
        if dimension == 'PE': dimension = 'PEOPLE'
        elif dimension == 'N': dimension = 'NODE'
        elif dimension == 'P': dimension = 'PLACE'
        elif dimension == 'V': dimension = 'VITALITY'
        
        cw = float(critic_w[feature])
        ew = float(ewm_w[feature])
        ensemble = (cw + ew) / 2.0
        
        records.append((feature, dimension, cw, ew, ensemble))
    
    ddl = """
    CREATE TABLE IF NOT EXISTS features.nppv_weights (
        feature VARCHAR(50) PRIMARY KEY,
        dimension VARCHAR(20),
        critic_weight NUMERIC,
        ewm_weight NUMERIC,
        ensemble_weight NUMERIC
    );
    """
    
    with ENGINE.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            cur.execute("TRUNCATE TABLE features.nppv_weights")
            query = "INSERT INTO features.nppv_weights (feature, dimension, critic_weight, ewm_weight, ensemble_weight) VALUES %s"
            psycopg2.extras.execute_values(cur, query, records)
        conn.commit()
    print("  [OK] Weights saved successfully.")
    
    return pd.DataFrame(records, columns=["feature", "dimension", "critic_weight", "ewm_weight", "ensemble_weight"])


def plot_weights(df_weights):
    print("\n[Step 5] Generating visualization plots...")
    out_dir = Path("outputs/phase3")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    df_weights = df_weights.sort_values("ensemble_weight", ascending=True)
    
    # 1. Horizontal Bar Chart of Ensemble Weights
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(df_weights)))
    bars = ax.barh(df_weights['feature'], df_weights['ensemble_weight'], color=colors)
    ax.set_xlabel('Ensemble Weight (50% CRITIC / 50% EWM)')
    ax.set_title('NPP-V Feature Importance Weights')
    
    for i, bar in enumerate(bars):
        ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height()/2, 
                f"{bar.get_width():.4f}", va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(out_dir / "nppv_weights_bar.png", dpi=300)
    plt.close()
    
    # 2. Grouped Bar Chart (CRITIC vs EWM)
    df_weights = df_weights.sort_values("dimension")
    x = np.arange(len(df_weights))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x - width/2, df_weights['critic_weight'], width, label='CRITIC')
    ax.bar(x + width/2, df_weights['ewm_weight'], width, label='EWM')
    ax.set_xticks(x)
    ax.set_xticklabels(df_weights['feature'], rotation=45, ha='right')
    ax.set_ylabel('Weight')
    ax.set_title('CRITIC vs EWM Weights by Feature')
    ax.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "nppv_critic_vs_ewm.png", dpi=300)
    plt.close()
    
    print(f"  [OK] Plots saved to {out_dir}")


if __name__ == "__main__":
    print("="*70)
    print("PHASE 3: CRITIC & EWM WEIGHTING")
    print("="*70)
    df = load_features()
    critic_weights = calculate_critic(df)
    ewm_weights = calculate_ewm(df)
    
    df_w = save_to_db(critic_weights, ewm_weights)
    plot_weights(df_w)
    
    print("\nSummary of Ensemble Weights:")
    print(df_w.sort_values("ensemble_weight", ascending=False).to_string(index=False))
    print("\n[DONE] Phase 3 Complete.")
