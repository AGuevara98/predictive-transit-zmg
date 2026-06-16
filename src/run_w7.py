"""
W7: Existing Route Audit -- Orchestrator
=========================================
Scores every SITEUR GTFS route against the W5 multi-objective function,
flags weak segments, and proposes modifications.

Pipeline:
  1. Run DB migration 007_w7_tables.sql
  2. Load GTFS route geometries (shapes.txt -> EPSG:6372)
  3. Score all routes with W5 objective + constraints + Pareto ranking
  4. Compute audit flags (Low demand / Indirect / Redundant)
  5. Generate modification proposals
  6. Write results to features.route_audit (DB) and outputs/w7/

Usage:
    python src/run_w7.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine, text

from config import PG_URI
from src.w7_gtfs_loader import load_gtfs_routes
from src.w7_modifications import propose_modifications
from src.w7_route_scorer import score_all_routes
from src.w5_types import W5Config

OUTPUT_DIR = Path("outputs/w7")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MIGRATION_PATH = Path("db_setup/migrations/007_w7_tables.sql")


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def run_migration(engine) -> None:
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    print("  [OK] Migration 007_w7_tables.sql applied")


# ---------------------------------------------------------------------------
# DB write
# ---------------------------------------------------------------------------

def write_to_db(engine, routes_gdf: gpd.GeoDataFrame, scored_df: pd.DataFrame) -> None:
    """Upsert scored route records into features.route_audit."""
    # Join geometry back to scored records
    geom_map = routes_gdf.set_index("route_id")["geometry"].to_dict()

    insert_sql = text("""
        INSERT INTO features.route_audit (
            route_id, route_short_name, route_km, n_stops, straight_line_km,
            detour_ratio, f1_demand_gain, f2_route_km, f3_equity,
            total_score, pareto_rank, flag, modification_type, overlap_route_id, geom
        ) VALUES (
            :route_id, :route_short_name, :route_km, :n_stops, :straight_line_km,
            :detour_ratio, :f1_demand_gain, :f2_route_km, :f3_equity,
            :total_score, :pareto_rank, :flag, :modification_type, :overlap_route_id,
            ST_GeomFromText(:geom_wkt, 6372)
        )
        ON CONFLICT (route_id) DO UPDATE SET
            route_short_name  = EXCLUDED.route_short_name,
            route_km          = EXCLUDED.route_km,
            n_stops           = EXCLUDED.n_stops,
            straight_line_km  = EXCLUDED.straight_line_km,
            detour_ratio      = EXCLUDED.detour_ratio,
            f1_demand_gain    = EXCLUDED.f1_demand_gain,
            f2_route_km       = EXCLUDED.f2_route_km,
            f3_equity         = EXCLUDED.f3_equity,
            total_score       = EXCLUDED.total_score,
            pareto_rank       = EXCLUDED.pareto_rank,
            flag              = EXCLUDED.flag,
            modification_type = EXCLUDED.modification_type,
            overlap_route_id  = EXCLUDED.overlap_route_id,
            geom              = ST_GeomFromText(:geom_wkt, 6372)
    """)

    with engine.begin() as conn:
        for _, row in scored_df.iterrows():
            rid = str(row["route_id"])
            geom = geom_map.get(rid)
            if geom is None:
                continue
            conn.execute(insert_sql, {
                "route_id": rid,
                "route_short_name": str(row.get("route_short_name", "")),
                "route_km": float(row["route_km"]),
                "n_stops": int(row["n_stops"]),
                "straight_line_km": float(row["straight_line_km"]),
                "detour_ratio": float(row["detour_ratio"]),
                "f1_demand_gain": float(row["f1_demand_gain"]),
                "f2_route_km": float(row["f2_route_km"]),
                "f3_equity": float(row["f3_equity"]),
                "total_score": float(row["total_score"]),
                "pareto_rank": int(row["pareto_rank"]),
                "flag": str(row["flag"]) if pd.notna(row.get("flag")) else None,
                "modification_type": None,   # filled from proposals separately
                "overlap_route_id": (
                    str(row["overlap_route_id"])
                    if pd.notna(row.get("overlap_route_id"))
                    else None
                ),
                "geom_wkt": geom.wkt,
            })

    print(f"  [OK] {len(scored_df)} routes written to features.route_audit")


def update_modification_types(engine, proposals: list) -> None:
    """Update modification_type in route_audit from proposals."""
    if not proposals:
        return
    update_sql = text("""
        UPDATE features.route_audit
        SET modification_type = :mod_type
        WHERE route_id = :route_id
    """)
    with engine.begin() as conn:
        for p in proposals:
            conn.execute(update_sql, {
                "route_id": p["route_id"],
                "mod_type": p["modification_type"],
            })
    print(f"  [OK] Modification types updated for {len(proposals)} routes")


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_scorecard_csv(scored_df: pd.DataFrame) -> None:
    cols = [
        "route_id", "route_short_name", "route_long_name",
        "route_km", "n_stops", "straight_line_km", "detour_ratio",
        "connects_to_existing", "n_served_agebs",
        "f1_demand_gain", "f2_route_km", "f3_equity",
        "composite_score", "total_score", "pareto_rank", "feasible",
        "flag", "overlap_route_id",
    ]
    out_cols = [c for c in cols if c in scored_df.columns]
    out = OUTPUT_DIR / "route_scorecard.csv"
    scored_df[out_cols].to_csv(out, index=False)
    print(f"  [OK] Scorecard CSV -> {out}")


def write_modifications_csv(proposals: list) -> None:
    df = pd.DataFrame(proposals)
    out = OUTPUT_DIR / "route_modifications.csv"
    df.to_csv(out, index=False)
    print(f"  [OK] Modifications CSV -> {out}")


def write_geojson(routes_gdf: gpd.GeoDataFrame, scored_df: pd.DataFrame) -> None:
    """Merge scores onto route geometries and write EPSG:4326 GeoJSON for QGIS."""
    score_cols = [
        "route_id", "route_short_name", "route_km", "n_stops",
        "detour_ratio", "f1_demand_gain", "f3_equity",
        "total_score", "pareto_rank", "feasible", "flag", "n_served_agebs",
    ]
    avail = [c for c in score_cols if c in scored_df.columns]
    merged = routes_gdf.merge(scored_df[avail], on="route_id", how="left")
    merged = merged.to_crs("EPSG:4326")
    out = OUTPUT_DIR / "route_audit.geojson"
    # Use only subset of columns for cleaner output
    keep = [
        "route_id", "route_short_name", "route_long_name",
        "route_km", "n_stops", "detour_ratio",
        "f1_demand_gain", "f3_equity", "total_score",
        "pareto_rank", "feasible", "flag", "n_served_agebs", "geometry",
    ]
    keep_avail = [c for c in keep if c in merged.columns]
    merged[keep_avail].to_file(out, driver="GeoJSON")
    print(f"  [OK] GeoJSON -> {out}")


def write_pareto_chart(scored_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 7))
    flag_colors = {
        "Low demand": "red",
        "Indirect": "orange",
        "Redundant": "purple",
        None: "steelblue",
    }
    for _, row in scored_df.iterrows():
        flag = row.get("flag", None)
        if pd.isna(flag):
            flag = None
        color = flag_colors.get(flag, "steelblue")
        ax.scatter(row["f2_route_km"], row["f1_demand_gain"],
                   c=color, s=60, alpha=0.7, zorder=3)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="steelblue", label="OK"),
        Patch(facecolor="red", label="Low demand"),
        Patch(facecolor="orange", label="Indirect"),
        Patch(facecolor="purple", label="Redundant"),
    ]
    ax.legend(handles=legend_elements, loc="upper right")
    ax.set_xlabel("f2: Route length (km) -- minimize")
    ax.set_ylabel("f1: Demand-weighted gain -- maximize")
    ax.set_title("W7 Existing Route Audit -- Pareto Space (f1 vs f2)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = OUTPUT_DIR / "pareto_space.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  [OK] Pareto chart -> {out}")


def write_score_distribution_chart(scored_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].hist(scored_df["total_score"].dropna(), bins=20, color="steelblue", edgecolor="white")
    axes[0].set_title("Total Score Distribution")
    axes[0].set_xlabel("total_score")
    axes[0].set_ylabel("Count")

    axes[1].hist(scored_df["detour_ratio"].dropna(), bins=20, color="coral", edgecolor="white")
    axes[1].axvline(1.5, color="red", linestyle="--", label="Indirect threshold (1.5)")
    axes[1].set_title("Detour Ratio Distribution")
    axes[1].set_xlabel("detour_ratio")
    axes[1].set_ylabel("Count")
    axes[1].legend()

    fig.tight_layout()
    out = OUTPUT_DIR / "score_distributions.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  [OK] Score distribution chart -> {out}")


def write_report(scored_df: pd.DataFrame, proposals: list) -> None:
    n_routes = len(scored_df)
    n_flagged = int(scored_df["flag"].notna().sum())
    n_low = int((scored_df["flag"] == "Low demand").sum())
    n_indirect = int((scored_df["flag"] == "Indirect").sum())
    n_redundant = int((scored_df["flag"] == "Redundant").sum())
    n_feasible = int(scored_df["feasible"].sum()) if "feasible" in scored_df.columns else "N/A"

    top10 = scored_df.nlargest(10, "total_score")[
        ["route_id", "route_short_name", "total_score", "f1_demand_gain", "f3_equity", "pareto_rank", "flag"]
    ]
    bottom10 = scored_df.nsmallest(10, "total_score")[
        ["route_id", "route_short_name", "total_score", "f1_demand_gain", "f3_equity", "pareto_rank", "flag"]
    ]

    flagged_table = scored_df[scored_df["flag"].notna()][
        ["route_id", "route_short_name", "total_score", "detour_ratio", "flag", "overlap_route_id"]
    ].sort_values("total_score")

    def df_to_md(df: pd.DataFrame) -> str:
        lines = ["| " + " | ".join(str(c) for c in df.columns) + " |"]
        lines.append("|" + "|".join(["---"] * len(df.columns)) + "|")
        for _, row in df.iterrows():
            lines.append("| " + " | ".join(
                str(round(v, 3) if isinstance(v, float) else v)
                for v in row
            ) + " |")
        return "\n".join(lines)

    mod_lines = []
    for p in proposals:
        mod_lines.append(
            f"- **{p['route_id']}** ({p['modification_type']}): {p['reason']}"
        )
        if p["proposed_score"] is not None:
            mod_lines.append(
                f"  - Current score: {p['current_score']:.3f} -> "
                f"Proposed score: {p['proposed_score']:.3f}"
            )
        if p.get("overlap_route_id"):
            mod_lines.append(f"  - Paired with: {p['overlap_route_id']}")

    lines = [
        "# W7 Existing Route Audit -- Report",
        "",
        "## Summary",
        "",
        f"- **Routes audited:** {n_routes}",
        f"- **Feasible routes:** {n_feasible}",
        f"- **Routes flagged:** {n_flagged} "
        f"({n_low} Low demand, {n_indirect} Indirect, {n_redundant} Redundant)",
        "",
        "## Methodology",
        "",
        "1. **GTFS loader:** Route geometries built from shapes.txt (EPSG:6372).",
        "   Fallback to stop-sequence reconstruction if shape_id unavailable.",
        "2. **Served AGEBs:** `ST_DWithin(ST_Centroid(ageb.geom), route_geom, 400m)`.",
        "3. **W5 objective:** f1 demand-gain, f2 route length (efficiency), f3 equity.",
        "4. **W5 constraints:** detour_ratio <= 1.8, stop spacing 300-1000m, "
        "   demand >= 500 trips/day, route_km <= 30km.",
        "5. **Pareto ranking:** Non-dominated sort on (-f1, f2, -f3).",
        "6. **Flags:**",
        "   - Low demand: f1 < 0.2 AND total_score < 0.3",
        "   - Indirect: detour_ratio > 1.5",
        "   - Redundant: Jaccard overlap of served AGEBs >= 60% with higher-scoring route",
        "",
        "## Score Distribution",
        "",
        f"- Mean total_score: {scored_df['total_score'].mean():.3f}",
        f"- Median total_score: {scored_df['total_score'].median():.3f}",
        f"- Mean detour_ratio: {scored_df['detour_ratio'].mean():.3f}",
        f"- Mean f1_demand_gain: {scored_df['f1_demand_gain'].mean():.3f}",
        f"- Mean f3_equity: {scored_df['f3_equity'].mean():.3f}",
        "",
        "## Top 10 Routes by Score",
        "",
        df_to_md(top10),
        "",
        "## Bottom 10 Routes by Score",
        "",
        df_to_md(bottom10),
        "",
        "## Flagged Routes",
        "",
        df_to_md(flagged_table) if not flagged_table.empty else "_No routes flagged._",
        "",
        "## Modification Proposals",
        "",
    ]
    if mod_lines:
        lines.extend(mod_lines)
    else:
        lines.append("_No modifications proposed._")

    lines += [
        "",
        "## W5 Config Used",
        "",
        "```",
        "w_demand_gain=0.50, w_efficiency=0.25, w_equity=0.25",
        "max_detour_ratio=1.8, min_stop_spacing=300m, max_stop_spacing=1000m",
        "min_daily_demand=500 trips/day, max_route_km=30km",
        "```",
    ]

    out = OUTPUT_DIR / "w7_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [OK] Report -> {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    SEP = "=" * 70
    print(f"\n{SEP}\n  W7: EXISTING ROUTE AUDIT\n{SEP}")

    cfg = W5Config()
    engine = create_engine(PG_URI)

    try:
        print("\n[Step 1] Applying DB migration...")
        run_migration(engine)

        print("\n[Step 2] Loading GTFS route geometries...")
        routes_gdf = load_gtfs_routes()
        print(f"  [OK] {len(routes_gdf)} routes loaded")

        if routes_gdf.empty:
            print("  [ERR] No route geometries could be built. Check GTFS data.")
            sys.exit(1)

        print("\n[Step 3] Scoring all routes with W5 objective function...")
        scored_df = score_all_routes(routes_gdf, engine, config=cfg)

        print("\n[Step 4] Generating modification proposals...")
        proposals = propose_modifications(scored_df, engine=engine, config=cfg)

        print("\n[Step 5] Writing to database...")
        write_to_db(engine, routes_gdf, scored_df)
        update_modification_types(engine, proposals)

        print("\n[Step 6] Writing output files...")
        write_scorecard_csv(scored_df)
        write_modifications_csv(proposals)
        write_geojson(routes_gdf, scored_df)
        write_pareto_chart(scored_df)
        write_score_distribution_chart(scored_df)
        write_report(scored_df, proposals)

        # Summary
        n_flagged = int(scored_df["flag"].notna().sum())
        flag_counts = scored_df["flag"].value_counts().to_dict()
        print(f"\n{SEP}")
        print("  W7 ROUTE AUDIT COMPLETE")
        print(f"{SEP}")
        print(f"\n  Routes loaded:  {len(routes_gdf)}")
        print(f"  Routes scored:  {len(scored_df)}")
        print(f"  Routes flagged: {n_flagged}")
        for flag_name, cnt in flag_counts.items():
            print(f"    - {flag_name}: {cnt}")
        print(f"  Proposals:      {len(proposals)}")
        print(f"\nOutputs: {OUTPUT_DIR}/")
        print("  route_scorecard.csv     -- all routes with W5 scores and flags")
        print("  route_modifications.csv -- proposed modifications")
        print("  route_audit.geojson     -- QGIS-ready GeoJSON (EPSG:4326)")
        print("  pareto_space.png        -- scatter f1 vs f2 colored by flag")
        print("  score_distributions.png -- histograms of score and detour_ratio")
        print("  w7_report.md            -- full audit report")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
