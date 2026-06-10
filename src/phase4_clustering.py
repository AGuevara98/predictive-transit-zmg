"""
Phase 4: Unsupervised Machine Learning (Clustering)
===================================================
Applies the Phase 3 ensemble weights to the Phase 2 features and
clusters the 2,068 AGEBs into transit suitability typologies using K-Means++.
"""

import sys
import pandas as pd
import numpy as np
import psycopg2
import psycopg2.extras
from pathlib import Path
from urllib.parse import urlparse
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

from sqlalchemy import create_engine
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)

def load_data():
    print("[Step 1] Loading Features and Weights...")
    with ENGINE.raw_connection() as conn:
        features_df = pd.read_sql("SELECT * FROM features.nppv_features", conn)
        weights_df = pd.read_sql("SELECT feature, ensemble_weight FROM features.nppv_weights", conn)
    
    # Create weight dictionary
    weights = dict(zip(weights_df['feature'], weights_df['ensemble_weight']))
    
    # Separate identifiers and geometry from modeling features
    meta_cols = ['cve_ageb', 'area_km2', 'geom']
    feature_cols = [c for c in features_df.columns if c not in meta_cols and c.endswith('_n')]
    
    # Store cve_ageb index
    cve_ageb = features_df['cve_ageb'].values
    
    # Extract only modeling features
    X = features_df[feature_cols].copy()
    
    print(f"  [OK] Loaded {len(X)} AGEBs with {len(feature_cols)} features.")
    return cve_ageb, X, weights, feature_cols

def apply_weights(X, weights, feature_cols):
    print("[Step 2] Applying Ensemble Weights to Features...")
    X_weighted = X.copy()
    for col in feature_cols:
        if col in weights:
            X_weighted[col] = X_weighted[col] * weights[col]
    
    # Fill any NaNs that might have sneaked through with 0
    X_weighted = X_weighted.fillna(0)
    print("  [OK] Weights applied.")
    return X_weighted

def determine_optimal_k(X_weighted, min_k=3, max_k=8):
    print(f"[Step 3] Evaluating optimal K ({min_k} to {max_k}) via Silhouette Score...")
    best_k = min_k
    best_score = -1
    scores = {}
    
    # Use fixed random state for reproducibility
    for k in range(min_k, max_k + 1):
        kmeans = KMeans(n_clusters=k, init='k-means++', n_init=10, random_state=42)
        labels = kmeans.fit_predict(X_weighted)
        score = silhouette_score(X_weighted, labels)
        scores[k] = score
        print(f"  K={k}: Silhouette={score:.4f}")
        if score > best_score:
            best_score = score
            best_k = k
            
    print(f"  [OK] Optimal K is {best_k} (Score: {best_score:.4f})")
    
    # Plot Silhouette Scores
    out_dir = Path("outputs/phase4")
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    plt.plot(list(scores.keys()), list(scores.values()), marker='o', linestyle='-', color='b')
    plt.title('Silhouette Score by Number of Clusters (K)')
    plt.xlabel('Number of Clusters (K)')
    plt.ylabel('Silhouette Score')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.axvline(x=best_k, color='r', linestyle='--')
    plt.tight_layout()
    plt.savefig(out_dir / "silhouette_scores.png", dpi=300)
    plt.close()
    
    return best_k

def run_clustering(X_weighted, k):
    print(f"\n[Step 4] Running final K-Means++ with K={k}...")
    kmeans = KMeans(n_clusters=k, init='k-means++', n_init=10, random_state=42)
    labels = kmeans.fit_predict(X_weighted)
    print("  [OK] Clustering complete.")
    return labels, kmeans

def save_clusters_to_db(cve_ageb, labels):
    print("\n[Step 5] Saving cluster assignments to database...")
    
    records = []
    # Create simple typologies A, B, C, D...
    typology_map = {i: f"Typology {chr(65+i)}" for i in set(labels)}
    
    for cve, label in zip(cve_ageb, labels):
        records.append((cve, int(label), typology_map[label]))
        
    ddl = """
    CREATE TABLE IF NOT EXISTS features.nppv_clusters (
        cve_ageb VARCHAR(13) PRIMARY KEY,
        cluster_id INTEGER,
        typology_name VARCHAR(50)
    );
    """
    
    with ENGINE.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            cur.execute("TRUNCATE TABLE features.nppv_clusters")
            query = "INSERT INTO features.nppv_clusters (cve_ageb, cluster_id, typology_name) VALUES %s"
            psycopg2.extras.execute_values(cur, query, records)
        conn.commit()
    print("  [OK] Clusters saved to features.nppv_clusters.")

def plot_clusters_pca(X_weighted, labels):
    print("\n[Step 6] Generating PCA Scatter Plot...")
    pca = PCA(n_components=2, random_state=42)
    components = pca.fit_transform(X_weighted)
    
    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(components[:, 0], components[:, 1], c=labels, cmap='viridis', alpha=0.6, s=20)
    plt.colorbar(scatter, label='Cluster ID')
    plt.title('Transit Suitability Typologies (PCA Projection)')
    plt.xlabel(f'Principal Component 1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
    plt.ylabel(f'Principal Component 2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
    
    out_dir = Path("outputs/phase4")
    plt.tight_layout()
    plt.savefig(out_dir / "cluster_pca.png", dpi=300)
    plt.close()
    print("  [OK] PCA plot saved.")

if __name__ == "__main__":
    print("="*70)
    print("PHASE 4: UNSUPERVISED CLUSTERING (K-MEANS++)")
    print("="*70)
    
    # To use a hardcoded K instead of auto-determination, change this value
    HARDCODED_K = None 
    
    cve_ageb, X, weights, feature_cols = load_data()
    X_weighted = apply_weights(X, weights, feature_cols)
    
    if HARDCODED_K:
        k = HARDCODED_K
        print(f"\n[INFO] Using hardcoded K = {k}")
    else:
        k = determine_optimal_k(X_weighted, min_k=3, max_k=8)
        
    labels, model = run_clustering(X_weighted, k)
    save_clusters_to_db(cve_ageb, labels)
    plot_clusters_pca(X_weighted, labels)
    
    # Calculate Cluster Profiles
    X_original = X.copy()
    X_original['Cluster'] = labels
    profiles = X_original.groupby('Cluster').mean()
    
    # Save profiles to CSV for the report generator
    out_dir = Path("outputs/phase4")
    profiles.to_csv(out_dir / "cluster_profiles.csv")
    
    print("\n[DONE] Phase 4 Complete.")
