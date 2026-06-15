"""
W4 -- NPP Prioritization Layer
===============================
Repositions the NPP-V framework as a multi-criteria place-characteristics
prioritization index, decoupled from demand estimation.

Vitality dimension (v_ridership_annual_n) is excluded -- it is a
municipality-level proxy with no AGEB-level discrimination power.
Demand signal lives exclusively in W1/W3.

Score formula:
    npp_score    = sum(feature_i * ensemble_weight_i)    [CRITIC+EWM, 14 features]
    equity_score = mean(pe_marginacion_n, pe_rezago_n)
    final_score  = (1 - ALPHA) * npp_score + ALPHA * equity_score
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2.extras
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

PROJECT_ROOT = Path(__file__).parent.parent

ALPHA = 0.20  # equity bonus weight; sensitivity tested at 0.10, 0.20, 0.30

NPP_FEATURES = [
    "n_intersections_n", "n_street_density_n", "n_intersection_density_n",
    "p_poi_density_n", "p_employment_proxy_n", "p_retail_density_n",
    "p_service_density_n", "p_land_use_mix_n",
    "pe_population_n", "pe_pop_density_n", "pe_marginacion_n", "pe_rezago_n",
    "pe_dep_ratio_n", "pe_youth_share_n",
]
EQUITY_FEATURES = ["pe_marginacion_n", "pe_rezago_n"]
DIMENSIONS = {
    "n_intersections_n": "NODE",
    "n_street_density_n": "NODE",
    "n_intersection_density_n": "NODE",
    "p_poi_density_n": "PLACE",
    "p_employment_proxy_n": "PLACE",
    "p_retail_density_n": "PLACE",
    "p_service_density_n": "PLACE",
    "p_land_use_mix_n": "PLACE",
    "pe_population_n": "PEOPLE",
    "pe_pop_density_n": "PEOPLE",
    "pe_marginacion_n": "PEOPLE",
    "pe_rezago_n": "PEOPLE",
    "pe_dep_ratio_n": "PEOPLE",
    "pe_youth_share_n": "PEOPLE",
}


def compute_critic_weights(df: pd.DataFrame) -> dict:
    """CRITIC weights: contrast intensity x conflict across features."""
    std_dev = df.std()
    corr_matrix = df.corr()
    conflict = (1 - corr_matrix).sum()
    c_j = std_dev * conflict
    w = c_j / c_j.sum()
    return w.to_dict()


def compute_ewm_weights(df: pd.DataFrame) -> dict:
    """Entropy Weight Method weights: information dispersion across features."""
    n = len(df)
    shifted = df + 1e-6
    p_ij = shifted / shifted.sum()
    k = 1.0 / np.log(n)
    e_j = -k * (p_ij * np.log(p_ij)).sum()
    d_j = 1 - e_j
    w = d_j / d_j.sum()
    return w.to_dict()


def compute_ensemble_weights(critic_w: dict, ewm_w: dict) -> dict:
    """Average of CRITIC and EWM, re-normalized to sum to 1."""
    features = list(critic_w.keys())
    raw = {f: (critic_w[f] + ewm_w[f]) / 2.0 for f in features}
    total = sum(raw.values())
    return {f: v / total for f, v in raw.items()}


def compute_scores(df: pd.DataFrame, ensemble_w: dict, alpha: float = ALPHA) -> pd.DataFrame:
    """
    Compute npp_score, equity_score, final_score, priority_rank, priority_quintile.

    df must contain 'cve_ageb' plus all NPP_FEATURES columns.
    ensemble_w keys must cover all NPP_FEATURES.
    """
    npp_score = sum(df[f] * w for f, w in ensemble_w.items())
    equity_score = df[EQUITY_FEATURES].mean(axis=1)
    final_score = (1 - alpha) * npp_score + alpha * equity_score

    priority_rank = final_score.rank(ascending=False, method="min").astype(int)
    try:
        priority_quintile = pd.qcut(final_score, q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    except ValueError:
        priority_quintile = pd.cut(final_score, bins=5, labels=[1, 2, 3, 4, 5]).astype(int)

    return pd.DataFrame({
        "cve_ageb": df["cve_ageb"].values,
        "npp_score": npp_score.values,
        "equity_score": equity_score.values,
        "final_score": final_score.values,
        "priority_rank": priority_rank.values,
        "priority_quintile": priority_quintile.values,
    })


_ENGINE = None


def _get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(PG_URI)
    return _ENGINE


# ---------------------------------------------------------------------------
# DB I/O
# ---------------------------------------------------------------------------

def load_npp_features() -> pd.DataFrame:
    print("[Step 1] Loading 14 NPP features from features.nppv_features...")
    engine = _get_engine()
    cols = ", ".join(["cve_ageb"] + NPP_FEATURES)
    with engine.raw_connection() as conn:
        df = pd.read_sql(
            f"SELECT {cols} FROM features.nppv_features",
            conn,
        )
    for col in NPP_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    print(f"  [OK] {len(df):,} AGEBs loaded with {len(NPP_FEATURES)} features")
    return df


def write_weights_to_db(critic_w: dict, ewm_w: dict, ensemble_w: dict):
    print("[Step 5] Writing weights to features.nppv_w4_weights...")
    engine = _get_engine()
    records = [
        (f, DIMENSIONS[f], float(critic_w[f]), float(ewm_w[f]), float(ensemble_w[f]))
        for f in NPP_FEATURES
    ]
    with engine.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE features.nppv_w4_weights")
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO features.nppv_w4_weights "
                "(feature, dimension, critic_weight, ewm_weight, ensemble_weight) VALUES %s",
                records,
            )
        conn.commit()
    print(f"  [OK] {len(records)} feature weights written")


def write_scores_to_db(scores_df: pd.DataFrame):
    print("[Step 6] Writing scores to features.nppv_prioritization...")
    engine = _get_engine()
    cols = ["cve_ageb", "npp_score", "equity_score", "final_score",
            "priority_rank", "priority_quintile"]
    rows = list(scores_df[cols].itertuples(index=False, name=None))
    with engine.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM features.nppv_prioritization")
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO features.nppv_prioritization "
                "(cve_ageb, npp_score, equity_score, final_score, "
                "priority_rank, priority_quintile) VALUES %s",
                rows, page_size=500,
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("ANALYZE features.nppv_prioritization")
        conn.commit()
    print(f"  [OK] {len(rows):,} AGEB rows written")


def export_csvs(weights_df: pd.DataFrame, scores_df: pd.DataFrame, out_dir: Path):
    print("[Step 7] Exporting CSVs...")
    weights_df.to_csv(out_dir / "nppv_w4_weights.csv", index=False)
    scores_df.to_csv(out_dir / "nppv_prioritization.csv", index=False)
    print(f"  [OK] outputs/w4/nppv_w4_weights.csv")
    print(f"  [OK] outputs/w4/nppv_prioritization.csv")


def export_geojson(out_dir: Path):
    print("[Step 8] Exporting GeoJSON (joining base.ageb geometry)...")
    import geopandas as gpd
    engine = _get_engine()
    query = """
        SELECT a.cvegeo, a.geom AS geometry,
               p.npp_score, p.equity_score, p.final_score,
               p.priority_rank, p.priority_quintile
        FROM base.ageb a
        JOIN features.nppv_prioritization p ON a.cvegeo = p.cve_ageb
    """
    with engine.raw_connection() as conn:
        gdf = gpd.read_postgis(query, conn, geom_col="geometry")
    gdf = gdf.to_crs("EPSG:4326")
    out_path = out_dir / "nppv_prioritization.geojson"
    gdf.to_file(str(out_path), driver="GeoJSON")
    print(f"  [OK] {len(gdf):,} features -> outputs/w4/nppv_prioritization.geojson")


def generate_charts(weights_df: pd.DataFrame, scores_df: pd.DataFrame, out_dir: Path):
    print("[Step 9] Generating charts...")
    import matplotlib.pyplot as plt

    # Chart 1: Horizontal bar of 14 ensemble weights
    df_plot = weights_df.sort_values("ensemble_weight", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(df_plot)))
    bars = ax.barh(df_plot["feature"], df_plot["ensemble_weight"], color=colors)
    ax.set_xlabel("Ensemble Weight (50% CRITIC / 50% EWM)")
    ax.set_title("W4 NPP Feature Importance Weights (14 features, Vitality excluded)")
    for bar in bars:
        ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height() / 2,
                f"{bar.get_width():.4f}", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "nppv_w4_weights_bar.png", dpi=300)
    plt.close()
    print("  [OK] nppv_w4_weights_bar.png")

    # Chart 2: Scatter npp_score vs equity_score, colored by final_score, sized by transit_demand
    engine = _get_engine()
    with engine.raw_connection() as conn:
        demand_df = pd.read_sql(
            "SELECT cve_ageb, transit_demand FROM features.ageb_trip_ends", conn
        )
    merged = scores_df.merge(demand_df, on="cve_ageb", how="left")
    merged["transit_demand"] = merged["transit_demand"].fillna(0.0)

    td = merged["transit_demand"]
    sizes = 20 + 180 * (td - td.min()) / (td.max() - td.min() + 1e-9)

    fig, ax = plt.subplots(figsize=(10, 8))
    sc = ax.scatter(
        merged["npp_score"], merged["equity_score"],
        c=merged["final_score"], s=sizes,
        cmap="YlOrRd", alpha=0.6, linewidths=0.2, edgecolors="grey",
    )
    plt.colorbar(sc, ax=ax, label="final_score")
    ax.set_xlabel("NPP Score (CRITIC+EWM weighted, 14 features)")
    ax.set_ylabel("Equity Score (mean marginacion + rezago)")
    ax.set_title("W4 NPP Score vs Equity Score\n(point size = transit demand, color = final score)")
    plt.tight_layout()
    plt.savefig(out_dir / "nppv_score_vs_equity.png", dpi=300)
    plt.close()
    print("  [OK] nppv_score_vs_equity.png")


def generate_cluster_profiles(scores_df: pd.DataFrame, out_dir: Path):
    print("[Step 10] Generating cluster priority profiles...")
    engine = _get_engine()
    with engine.raw_connection() as conn:
        clusters_df = pd.read_sql(
            "SELECT cve_ageb, cluster_id AS cluster FROM features.nppv_clusters",
            conn,
        )
    merged = scores_df.merge(clusters_df, on="cve_ageb", how="left")
    missing = merged["cluster"].isna().sum()
    if missing > 0:
        print(f"  [WARN] {missing} AGEBs have no cluster label")

    profile = (
        merged.dropna(subset=["cluster"])
        .groupby("cluster")[["npp_score", "equity_score", "final_score"]]
        .agg(["mean", "median", "count"])
    )
    profile.columns = ["_".join(c) for c in profile.columns]
    profile = profile.reset_index()
    out_path = out_dir / "cluster_priority_profiles.csv"
    profile.to_csv(out_path, index=False)
    print(f"  [OK] cluster_priority_profiles.csv ({len(profile)} clusters)")
    print(profile.to_string(index=False))


def write_report(weights_df: pd.DataFrame, scores_df: pd.DataFrame, out_dir: Path):
    print("[Step 11] Writing w4_report.md...")
    import datetime
    from scipy.stats import spearmanr
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    top10 = scores_df.sort_values("final_score", ascending=False).head(10)
    top10_md = top10[["cve_ageb", "npp_score", "equity_score", "final_score",
                       "priority_rank", "priority_quintile"]].to_markdown(index=False)

    weights_md = weights_df.to_markdown(index=False)

    q5_count = int((scores_df["priority_quintile"] == 5).sum())
    q1_count = int((scores_df["priority_quintile"] == 1).sum())

    # Sensitivity: Spearman rank correlation for alpha values vs alpha=0.20
    engine = _get_engine()
    with engine.raw_connection() as conn:
        feat_df = pd.read_sql(
            "SELECT cve_ageb, " + ", ".join(NPP_FEATURES) +
            " FROM features.nppv_features", conn
        )
    for col in NPP_FEATURES:
        feat_df[col] = pd.to_numeric(feat_df[col], errors="coerce").fillna(0.0)

    critic_w = compute_critic_weights(feat_df[NPP_FEATURES])
    ewm_w = compute_ewm_weights(feat_df[NPP_FEATURES])
    ensemble_w = compute_ensemble_weights(critic_w, ewm_w)

    base_scores = compute_scores(feat_df, ensemble_w, alpha=0.20)
    base_ranks = base_scores.set_index("cve_ageb")["priority_rank"]

    sensitivity_rows = []
    for alpha_val in [0.10, 0.20, 0.30]:
        alt = compute_scores(feat_df, ensemble_w, alpha=alpha_val)
        alt_ranks = alt.set_index("cve_ageb")["priority_rank"]
        aligned_base, aligned_alt = base_ranks.align(alt_ranks, join="inner")
        rho, _ = spearmanr(aligned_base, aligned_alt)
        sensitivity_rows.append(f"| {alpha_val} | {rho:.4f} |")
    sensitivity_md = "\n".join(sensitivity_rows)

    report = f"""# W4 NPP Prioritization Layer Report
*Generated: {now}*

## Methodology

W4 repositions the NPP-V indicator set as a multi-criteria place-characteristics
prioritization index, decoupled from demand estimation. The Vitality dimension
(`v_ridership_annual_n`) is excluded because it is a municipality-level proxy with
no AGEB-level discrimination. Demand lives in W1/W3.

**Score formula:**
- `npp_score = sum(feature_i * ensemble_weight_i)` over 14 NODE+PLACE+PEOPLE features
- `equity_score = mean(pe_marginacion_n, pe_rezago_n)`
- `final_score = {1 - ALPHA:.2f} * npp_score + {ALPHA:.2f} * equity_score`

CRITIC and EWM weights are computed independently and averaged (ensemble).

## Feature Weights (14 features)

{weights_md}

## Score Summary (2,068 AGEBs)

| Metric | npp_score | equity_score | final_score |
|---|---|---|---|
| Mean | {scores_df['npp_score'].mean():.4f} | {scores_df['equity_score'].mean():.4f} | {scores_df['final_score'].mean():.4f} |
| Std  | {scores_df['npp_score'].std():.4f} | {scores_df['equity_score'].std():.4f} | {scores_df['final_score'].std():.4f} |
| Min  | {scores_df['npp_score'].min():.4f} | {scores_df['equity_score'].min():.4f} | {scores_df['final_score'].min():.4f} |
| Max  | {scores_df['npp_score'].max():.4f} | {scores_df['equity_score'].max():.4f} | {scores_df['final_score'].max():.4f} |

Priority quintile 5 (highest priority): **{q5_count:,} AGEBs**
Priority quintile 1 (lowest priority): **{q1_count:,} AGEBs**

## Top 10 Highest-Priority AGEBs

{top10_md}

## Equity Sensitivity (Spearman rank correlation vs alpha=0.20 baseline)

| alpha | Spearman rho |
|---|---|
{sensitivity_md}

A rho close to 1.0 indicates that changing alpha has little effect on the
priority ranking.

## Methodological Note

`pe_marginacion_n` and `pe_rezago_n` contribute to both `npp_score` (via CRITIC/EWM)
and `equity_score`. This mild double-count slightly amplifies their influence on
`final_score`. If this becomes overinfluential, the equity_score operationalization
can be changed to use other equity indicators.

## Outputs

- `features.nppv_w4_weights` -- 14 feature weights (DB)
- `features.nppv_prioritization` -- 2,068 AGEB scores + ranks (DB)
- `outputs/w4/nppv_w4_weights.csv`
- `outputs/w4/nppv_prioritization.csv`
- `outputs/w4/nppv_prioritization.geojson` (QGIS-ready, EPSG:4326)
- `outputs/w4/nppv_w4_weights_bar.png`
- `outputs/w4/nppv_score_vs_equity.png`
- `outputs/w4/cluster_priority_profiles.csv`
"""
    (out_dir / "w4_report.md").write_text(report, encoding="utf-8")
    print(f"  [OK] outputs/w4/w4_report.md")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\n" + "="*70)
    print(" W4: NPP PRIORITIZATION LAYER")
    print("="*70)

    out_dir = PROJECT_ROOT / "outputs" / "w4"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load
    features_df = load_npp_features()

    # Compute weights
    print("[Step 2] Computing CRITIC weights...")
    critic_w = compute_critic_weights(features_df[NPP_FEATURES])
    print(f"  [OK] CRITIC computed for {len(critic_w)} features")

    print("[Step 3] Computing EWM weights...")
    ewm_w = compute_ewm_weights(features_df[NPP_FEATURES])
    print(f"  [OK] EWM computed for {len(ewm_w)} features")

    print("[Step 4] Computing NPP + equity scores...")
    ensemble_w = compute_ensemble_weights(critic_w, ewm_w)
    scores_df = compute_scores(features_df, ensemble_w, alpha=ALPHA)
    print(f"  [OK] Scores computed for {len(scores_df):,} AGEBs")
    print(f"    npp_score   : mean={scores_df['npp_score'].mean():.4f}")
    print(f"    equity_score: mean={scores_df['equity_score'].mean():.4f}")
    print(f"    final_score : mean={scores_df['final_score'].mean():.4f}")

    # Build weights DataFrame for CSV/DB
    weights_df = pd.DataFrame([
        {
            "feature": f,
            "dimension": DIMENSIONS[f],
            "critic_weight": critic_w[f],
            "ewm_weight": ewm_w[f],
            "ensemble_weight": ensemble_w[f],
        }
        for f in NPP_FEATURES
    ]).sort_values("ensemble_weight", ascending=False)

    # DB writes
    write_weights_to_db(critic_w, ewm_w, ensemble_w)
    write_scores_to_db(scores_df)

    # CSVs
    export_csvs(weights_df, scores_df, out_dir)

    # GeoJSON
    export_geojson(out_dir)

    # Charts
    generate_charts(weights_df, scores_df, out_dir)

    # Cluster profiles
    generate_cluster_profiles(scores_df, out_dir)

    # Report
    write_report(weights_df, scores_df, out_dir)

    print("\n" + "="*70)
    print(" [OK] W4 NPP PRIORITIZATION LAYER COMPLETE")
    print("="*70)
    print("DB outputs:")
    print("  features.nppv_w4_weights        -- 14 feature weights")
    print("  features.nppv_prioritization    -- 2,068 AGEB scores + ranks")
    print("File outputs (outputs/w4/):")
    print("  nppv_w4_weights.csv")
    print("  nppv_prioritization.csv")
    print("  nppv_prioritization.geojson")
    print("  nppv_w4_weights_bar.png")
    print("  nppv_score_vs_equity.png")
    print("  cluster_priority_profiles.csv")
    print("  w4_report.md")


if __name__ == "__main__":
    main()
