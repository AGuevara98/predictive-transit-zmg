"""
Phase 1: Balanced Station Selection - Create Training Dataset
==============================================================

This module creates a training dataset for Phase 2 ML model by:
1. Using existing transit stops as positive examples (suitable)
2. Sampling underserved AGEBs as negative examples (unsuitable)
3. Stratifying by accessibility and employment quartiles for balanced coverage

The resulting features.training_labels table feeds Phase 2 (ML training).
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI


def create_training_labels(engine, positive_ratio=0.5, random_seed=42):
    """
    Create balanced training dataset: existing stops (positive) + underserved AGEBs (negative).
    
    Strategy:
    - Positive examples: All existing GTFS stops (suitable for new routes nearby)
    - Negative examples: Random AGEBs with low accessibility + low employment
      (underserved areas less suitable for route placement based on current data)
    - Stratification: Ensure both positive and negative classes cover full spectrum
      of accessibility and employment quartiles
    
    Parameters:
        engine: SQLAlchemy engine for database connection
        positive_ratio: Ratio of positive to total examples (default 0.5 for balanced)
        random_seed: Random seed for reproducibility
    
    Returns:
        DataFrame with training_labels
    """
    
    print("\n" + "="*70)
    print("PHASE 1: BALANCED STATION SELECTION")
    print("="*70)
    
    # Step 1: Load existing stations and create positive examples
    print("\nStep 1: Loading existing transit stops (positive examples)...")
    query_stations = """
    SELECT 
        a.cvegeo AS ageb_id,
        1 AS label,
        'existing_station' AS stratum,
        acc.stops_400m,
        acc.stops_800m,
        emp.employment_proxy,
        NTILE(4) OVER (ORDER BY acc.stops_400m + acc.stops_800m) AS accessibility_quartile,
        NTILE(4) OVER (ORDER BY emp.employment_proxy) AS employment_quartile
    FROM base.gtfs_stops s
    JOIN base.ageb a ON ST_Within(s.geom, a.geom)
    JOIN features.ageb_accessibility acc ON a.cvegeo = acc.ageb_id
    JOIN features.ageb_employment emp ON a.cvegeo = emp.ageb_id
    GROUP BY a.cvegeo, acc.stops_400m, acc.stops_800m, emp.employment_proxy;
    """
    
    positive_df = pd.read_sql(text(query_stations), engine)
    n_positive = len(positive_df)
    print(f"[OK] Found {n_positive} unique AGEBs with existing stations")
    
    # Step 2: Load all AGEBs and identify candidates for negative examples
    print("\nStep 2: Identifying negative examples (underserved AGEBs)...")
    query_all_agebs = """
    SELECT 
        a.cvegeo AS ageb_id,
        0 AS label,
        acc.stops_400m,
        acc.stops_800m,
        emp.employment_proxy,
        NTILE(4) OVER (ORDER BY acc.stops_400m + acc.stops_800m) AS accessibility_quartile,
        NTILE(4) OVER (ORDER BY emp.employment_proxy) AS employment_quartile
    FROM base.ageb a
    LEFT JOIN features.ageb_accessibility acc ON a.cvegeo = acc.ageb_id
    LEFT JOIN features.ageb_employment emp ON a.cvegeo = emp.ageb_id
    WHERE a.cvegeo NOT IN (
        SELECT DISTINCT cvegeo FROM base.ageb a2 
        JOIN base.gtfs_stops s ON ST_Within(s.geom, a2.geom)
    );
    """
    
    all_agebs_df = pd.read_sql(text(query_all_agebs), engine)
    n_all = len(all_agebs_df)
    print(f"[OK] Total AGEBs without existing stations: {n_all}")
    
    # Step 3: Stratified sampling of negative examples
    # Ensure coverage across accessibility and employment quartiles
    print("\nStep 3: Stratified sampling of negative examples...")
    
    np.random.seed(random_seed)
    
    # Calculate number of negative examples to balance dataset
    n_negative = int(n_positive / positive_ratio) - n_positive
    print(f"  Target negative examples: {n_negative}")
    
    # Sample from each stratum (accessibility x employment quartile)
    negative_samples = []
    stratums_covered = set()
    
    for acc_q in range(1, 5):
        for emp_q in range(1, 5):
            stratum_data = all_agebs_df[
                (all_agebs_df['accessibility_quartile'] == acc_q) & 
                (all_agebs_df['employment_quartile'] == emp_q)
            ]
            
            if len(stratum_data) > 0:
                # Sample proportionally from each stratum
                n_stratum = max(1, int(n_negative / 16))  # 16 stratums (4x4)
                sampled = stratum_data.sample(
                    n=min(n_stratum, len(stratum_data)), 
                    random_state=random_seed + acc_q*4 + emp_q
                )
                sampled['stratum'] = f'underserved_q{acc_q}_{emp_q}'
                negative_samples.append(sampled)
                stratums_covered.add((acc_q, emp_q))
    
    if negative_samples:
        negative_df = pd.concat(negative_samples, ignore_index=True)
        print(f"[OK] Sampled {len(negative_df)} negative examples across {len(stratums_covered)} stratums")
    else:
        print("WARNING: No negative examples sampled; creating fallback dataset")
        negative_df = all_agebs_df.sample(n=min(n_negative, len(all_agebs_df)), random_state=random_seed)
        negative_df['stratum'] = 'underserved_mixed'
    
    # Step 4: Combine and balance
    print("\nStep 4: Combining and balancing training data...")
    
    training_df = pd.concat([positive_df, negative_df], ignore_index=True)
    
    # Add quartiles
    training_df['label_str'] = training_df['label'].map({1: 'suitable', 0: 'unsuitable'})
    
    print(f"  Total training examples: {len(training_df)}")
    print(f"  Positive (suitable): {(training_df['label'] == 1).sum()}")
    print(f"  Negative (unsuitable): {(training_df['label'] == 0).sum()}")
    print(f"  Class balance: {(training_df['label'] == 1).sum() / len(training_df) * 100:.1f}% positive")
    
    return training_df


def save_training_labels_to_db(engine, training_df):
    """
    Save training labels to database for use in Phase 2.
    
    Parameters:
        engine: SQLAlchemy engine
        training_df: DataFrame with training labels
    """
    print("\nSaving training labels to database...")
    
    # Create table
    query_create = """
    DROP TABLE IF EXISTS features.training_labels CASCADE;
    CREATE TABLE features.training_labels (
        ageb_id VARCHAR(20) PRIMARY KEY,
        label SMALLINT NOT NULL CHECK (label IN (0, 1)),
        label_str VARCHAR(20),
        stratum VARCHAR(50),
        stops_400m INT,
        stops_800m INT,
        employment_proxy INT,
        accessibility_quartile INT,
        employment_quartile INT
    );
    """
    
    with engine.begin() as connection:
        connection.execute(text(query_create))
    
    # Insert via pandas to_sql for efficiency
    training_df.to_sql(
        'training_labels',
        engine,
        schema='features',
        if_exists='append',
        index=False,
        chunksize=1000
    )
    
    # Create indexes
    query_indexes = """
    CREATE INDEX idx_training_labels_label ON features.training_labels (label);
    CREATE INDEX idx_training_labels_stratum ON features.training_labels (stratum);
    CREATE INDEX idx_training_labels_accessibility ON features.training_labels (accessibility_quartile);
    ANALYZE features.training_labels;
    """
    
    with engine.begin() as connection:
        for stmt in query_indexes.split('\n'):
            if stmt.strip():
                connection.execute(text(stmt))
    
    print("[OK] Training labels saved to features.training_labels")


def save_training_labels_to_csv(training_df, output_dir="outputs/phase1"):
    """
    Save training labels to CSV for reference.
    
    Parameters:
        training_df: DataFrame with training labels
        output_dir: Directory to save CSV
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'training_labels.csv'
    training_df.to_csv(output_file, index=False)
    print(f"[OK] Saved: {output_file}")
    
    return output_file


def print_training_summary(training_df, engine):
    """
    Print summary of training dataset.
    
    Parameters:
        training_df: DataFrame with training labels
        engine: SQLAlchemy engine for additional queries
    """
    print("\n" + "="*70)
    print("TRAINING DATASET SUMMARY")
    print("="*70)
    
    print(f"\nTotal Examples: {len(training_df)}")
    print(f"  Positive (Suitable):   {(training_df['label'] == 1).sum():5d} ({(training_df['label'] == 1).sum()/len(training_df)*100:5.1f}%)")
    print(f"  Negative (Unsuitable): {(training_df['label'] == 0).sum():5d} ({(training_df['label'] == 0).sum()/len(training_df)*100:5.1f}%)")
    
    print("\nAccessibility-Employment Stratification:")
    print("-"*70)
    stratum_summary = training_df.groupby('stratum').agg({
        'label': ['count', 'sum'],
        'stops_400m': 'mean',
        'employment_proxy': 'mean'
    }).round(2)
    stratum_summary.columns = ['Total', 'Positive', 'Avg Stops 400m', 'Avg Employment']
    print(stratum_summary.to_string())
    
    print("\nFeature Statistics by Label:")
    print("-"*70)
    feature_stats = training_df.groupby('label_str')[
        ['stops_400m', 'stops_800m', 'employment_proxy']
    ].describe().round(2)
    print(feature_stats.to_string())
    
    print("="*70 + "\n")


def main():
    """Main execution."""
    
    # Connect to database
    print("Connecting to PostgreSQL...")
    engine = create_engine(PG_URI)
    
    try:
        # Create training labels
        training_df = create_training_labels(engine, positive_ratio=0.5, random_seed=42)
        
        # Print summary
        print_training_summary(training_df, engine)
        
        # Save to database
        save_training_labels_to_db(engine, training_df)
        
        # Save to CSV
        save_training_labels_to_csv(training_df)
        
        print("\n[OK] Phase 1 balanced station selection complete!")
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
