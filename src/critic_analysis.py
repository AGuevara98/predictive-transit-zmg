"""
Phase 1: CRITIC Analysis - Feature Importance Ranking
=====================================================

This module loads CRITIC weights from the database and creates visualizations
of feature importance for the NP-RV suitability model.

References:
  - Diakoulaki et al. (1995): CRITIC method
  - Bertolini (1996): Node-Place Model foundation
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI


def load_critic_weights(engine):
    """
    Load CRITIC weights from the database.
    
    Returns:
        DataFrame with columns: feature, weight_normalized, feature_rank, variance, avg_abs_correlation
    """
    query = """
    SELECT 
        feature,
        variance,
        avg_abs_correlation,
        weight_unnormalized,
        weight_normalized,
        feature_rank
    FROM features.v_critic_weights
    ORDER BY feature_rank;
    """
    return pd.read_sql(text(query), engine)


def visualize_critic_weights(weights_df, output_dir="outputs/phase1"):
    """
    Create visualizations of CRITIC weights and feature importance.
    
    Parameters:
        weights_df: DataFrame with CRITIC weights
        output_dir: Directory to save visualizations
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure numeric columns are safe for plotting
    plot_df = weights_df.copy()
    for col in ['weight_normalized', 'variance', 'avg_abs_correlation']:
        plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce').fillna(0.0)

    # Figure 1: Feature Importance (Horizontal Bar Chart)
    fig, ax = plt.subplots(figsize=(10, 6))
    weights_sorted = plot_df.sort_values('weight_normalized', ascending=True)
    
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.8, len(weights_sorted)))
    bars = ax.barh(weights_sorted['feature'], weights_sorted['weight_normalized'], color=colors)
    
    ax.set_xlabel('CRITIC Weight (Normalized)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Feature', fontsize=12, fontweight='bold')
    ax.set_title('CRITIC Feature Importance Ranking\nNP-RV Suitability Model', fontsize=14, fontweight='bold')
    ax.set_xlim(0, weights_sorted['weight_normalized'].max() * 1.1)
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2, f'{width:.4f}', 
                ha='left', va='center', fontweight='bold', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'critic_weights_barplot.png', dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir / 'critic_weights_barplot.png'}")
    plt.close()
    
    # Figure 2: Variance vs Correlation (Scatter Plot)
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(plot_df['avg_abs_correlation'], plot_df['variance'], 
                        s=plot_df['weight_normalized']*1000, 
                        c=plot_df['weight_normalized'],
                        cmap='viridis', alpha=0.6, edgecolors='black', linewidth=1.5)
    
    # Add feature labels
    for idx, row in plot_df.iterrows():
        ax.annotate(row['feature'], 
                   (row['avg_abs_correlation'], row['variance']),
                   fontsize=9, fontweight='bold',
                   ha='center', va='center')
    
    ax.set_xlabel('Average Absolute Correlation (Lower = More Independent)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Variance (Higher = More Discrimination Power)', fontsize=11, fontweight='bold')
    ax.set_title('Feature Variance vs Correlation\n(Bubble size = CRITIC weight)', fontsize=13, fontweight='bold')
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('CRITIC Weight', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'critic_variance_correlation.png', dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir / 'critic_variance_correlation.png'}")
    plt.close()
    
    # Figure 3: Weight Distribution (Pie Chart)
    fig, ax = plt.subplots(figsize=(10, 8))
    colors_pie = plt.cm.Set3(np.linspace(0, 1, len(weights_df)))
    wedges, texts, autotexts = ax.pie(plot_df['weight_normalized'], 
                                        labels=plot_df['feature'],
                                        autopct='%1.2f%%',
                                        colors=colors_pie,
                                        startangle=90,
                                        textprops={'fontsize': 10, 'fontweight': 'bold'})
    
    ax.set_title('Feature Weight Distribution (CRITIC Method)\nNP-RV Model Components', 
                fontsize=13, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'critic_weights_pie.png', dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir / 'critic_weights_pie.png'}")
    plt.close()


def save_weights_to_csv(weights_df, output_dir="outputs/phase1"):
    """
    Save CRITIC weights to CSV for reference.
    
    Parameters:
        weights_df: DataFrame with CRITIC weights
        output_dir: Directory to save CSV
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'critic_weights.csv'
    weights_df.to_csv(output_file, index=False)
    print(f"[OK] Saved: {output_file}")
    
    return output_file


def print_weights_summary(weights_df):
    """
    Print summary statistics of CRITIC weights.
    
    Parameters:
        weights_df: DataFrame with CRITIC weights
    """
    print("\n" + "="*70)
    print("CRITIC WEIGHTS SUMMARY")
    print("="*70)
    print("\nFeature Ranking by Importance:")
    print("-"*70)
    
    summary = weights_df[['feature', 'weight_normalized', 'variance', 'avg_abs_correlation', 'feature_rank']].copy()
    summary.columns = ['Feature', 'Weight', 'Variance', 'Avg Correlation', 'Rank']
    summary = summary.sort_values('Rank')
    
    for idx, row in summary.iterrows():
        bar = "#" * int(row['Weight'] * 100)
        print(f"{int(row['Rank']):2d}. {row['Feature']:25s} {row['Weight']:7.4f} {bar:50s}")
    
    print("-"*70)
    print(f"Total Weight: {weights_df['weight_normalized'].sum():.4f} (should be 1.0000)")
    print(f"Number of Features: {len(weights_df)}")
    print("="*70 + "\n")


def main():
    """Main execution."""
    print("\n" + "="*70)
    print("PHASE 1: CRITIC ANALYSIS - FEATURE IMPORTANCE")
    print("="*70)
    
    # Connect to database
    print("\nConnecting to PostgreSQL...")
    engine = create_engine(PG_URI)
    
    try:
        # Load CRITIC weights
        print("Loading CRITIC weights from database...")
        weights_df = load_critic_weights(engine)
        
        if weights_df.empty:
            print("ERROR: No CRITIC weights found. Run db_setup/10_critic_weights_view.sql first.")
            return False
        
        print(f"[OK] Loaded {len(weights_df)} features")
        
        # Print summary
        print_weights_summary(weights_df)
        
        # Create visualizations
        print("Creating visualizations...")
        visualize_critic_weights(weights_df)
        
        # Save to CSV
        print("Saving weights to CSV...")
        save_weights_to_csv(weights_df)
        
        print("\n[OK] Phase 1 CRITIC analysis complete!")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        engine.dispose()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
