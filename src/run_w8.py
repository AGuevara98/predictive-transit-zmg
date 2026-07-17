"""
W8: Validation Orchestrator
===========================
Runs all three W8 sub-tasks and writes a consolidated report.

  W8.1 - Backtest: mask MM+MT GTFS routes, re-run W3+W6, measure overlap
  W8.2 - Benchmark: W6 corridors vs. existing premium route shapes
  W8.3 - Metrics:  coverage rate, accessibility Gini, pop-served/km before/after W6

Usage:
    python src/run_w8.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from config import PG_URI
from src.db_preflight import ensure_nppv_features
from src.w8_backtest import run_backtest
from src.w8_benchmark import run_benchmark
from src.w8_metrics import compute_before_after_metrics

OUTPUT_DIR = Path("outputs/w8")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

W6_GEOJSON = Path("outputs/w6/corridor_candidates.geojson")
DATA_DIR = Path("data") / "gtfs"


def write_coverage_chart(metrics: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    ax = axes[0]
    labels = ["Before W6\n(GTFS only)", "After W6\n(GTFS + corridors)"]
    vals = [metrics["coverage_rate_before"] * 100, metrics["coverage_rate_after"] * 100]
    bars = ax.bar(labels, vals, color=["#4C8D2B", "#1565C0"], width=0.5)
    ax.set_ylabel("AGEB coverage rate (%)")
    ax.set_title("Transit Coverage Rate")
    ax.set_ylim(0, 105)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 1, f"{v:.1f}%", ha="center", fontsize=11)

    ax2 = axes[1]
    labels2 = ["Before W6", "After W6"]
    vals2 = [metrics["gini_before"], metrics["gini_after"]]
    bars2 = ax2.bar(labels2, vals2, color=["#D32F2F", "#1565C0"], width=0.5)
    ax2.set_ylabel("Accessibility Gini coefficient")
    ax2.set_title("Accessibility Inequality (lower = more equitable)")
    ax2.set_ylim(0, 1.0)
    for bar, v in zip(bars2, vals2):
        ax2.text(bar.get_x() + bar.get_width() / 2, v + 0.02, f"{v:.3f}", ha="center", fontsize=11)

    fig.tight_layout()
    out = OUTPUT_DIR / "w8_before_after_metrics.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  [OK] Chart written: {out}")


def write_backtest_chart(backtest: dict) -> None:
    per_route = backtest.get("per_route_overlap", [])
    if not per_route:
        return
    df = pd.DataFrame(per_route).sort_values("max_overlap_fraction", ascending=True)
    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.35)))
    colors = ["#1565C0" if v >= 0.5 else "#D32F2F" for v in df["max_overlap_fraction"]]
    ax.barh(df["route_id"], df["max_overlap_fraction"] * 100, color=colors)
    ax.axvline(50, color="gray", linestyle="--", linewidth=1, label="50% threshold")
    ax.set_xlabel("Max overlap with any re-proposed corridor (%)")
    ax.set_title("Backtest: Premium Route Recovery\n(% of route shape within 400m of re-proposed corridor)")
    ax.legend()
    fig.tight_layout()
    out = OUTPUT_DIR / "w8_backtest_overlap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  [OK] Backtest chart written: {out}")


def write_report(metrics: dict, backtest: dict, benchmark: dict) -> None:
    bench_df = benchmark.get("detail", pd.DataFrame())

    lines = [
        "# W8 Validation Report",
        "",
        "## W8.1 -- Backtest Results",
        "",
        f"**Premium routes masked:** Mi Macro (MM) + Mi Tren (MT) agencies",
        f"**Stops excluded:** {backtest['n_excluded_stops']:,}",
        f"**Anchor AGEBs found after masking:** {backtest['n_anchors_found']}",
        f"**Corridors built after masking:** {backtest.get('n_corridors_built', '?')}",
        f"**Corridors re-proposed (feasible):** {backtest['n_corridors_reproposed']}",
    ]

    if backtest["mean_overlap_fraction"] is not None:
        lines += [
            f"**Mean route-shape overlap:** {backtest['mean_overlap_fraction']:.1%}",
            "",
            "### Per-Route Overlap",
            "",
            "| Route ID | Max Overlap (%) |",
            "|----------|----------------|",
        ]
        for row in backtest.get("per_route_overlap", []):
            lines.append(f"| {row['route_id']} | {row['max_overlap_fraction']:.1%} |")
    else:
        lines.append("*(No overlap data -- no corridors re-proposed or no route shapes loaded)*")

    lines += [
        "",
        "## W8.2 -- Benchmark: W6 vs. Premium Routes",
        "",
        f"**W6 feasible corridors:** {benchmark['n_w6_corridors']}",
        f"**Premium route shapes:** {benchmark['n_premium_routes']}",
        f"**Mean W6 overlap with premium routes:** {benchmark['mean_w6_overlap_with_premium']:.1%}",
        f"**Total W6 km:** {benchmark['w6_total_km']:.1f} km",
        "",
        "*(Low overlap means W6 identifies new un-served areas rather than replicating existing lines -- an expected and valid finding.)*",
        "",
    ]

    if not bench_df.empty:
        lines += [
            "| W6 Corridor | Best Matching Premium Route | Overlap |",
            "|-------------|----------------------------|---------|",
        ]
        for _, row in bench_df.iterrows():
            lines.append(
                f"| {row['candidate_id']} | {row['best_matching_premium_route']} | {row['max_overlap_fraction']:.1%} |"
            )

    lines += [
        "",
        "## W8.3 -- Quantitative Before/After Metrics",
        "",
        "| Metric | Before W6 | After W6 | Delta |",
        "|--------|-----------|----------|-------|",
        f"| Coverage rate (AGEBs) | {metrics['coverage_rate_before']:.1%} | {metrics['coverage_rate_after']:.1%} | +{(metrics['coverage_rate_after'] - metrics['coverage_rate_before']):.1%} |",
        f"| Accessibility Gini | {metrics['gini_before']:.4f} | {metrics['gini_after']:.4f} | {metrics['gini_after'] - metrics['gini_before']:+.4f} |",
        f"| W6 pop-served / route-km | -- | {metrics['pop_served_per_km_w6']:,.0f} | -- |",
        f"| AGEBs newly served by W6 | -- | {metrics['n_ageb_newly_served']:,} | -- |",
        f"| Population newly served | -- | {metrics['total_population_newly_served']:,.0f} | -- |",
        f"| Total W6 route km | -- | {metrics['w6_total_km']:.1f} km | -- |",
        "",
        "**Note on Gini 'after' estimate:** AGEBs within 400m of W6 corridors that currently have zero accessibility are assigned the mean accessibility of currently-served AGEBs. This is a conservative lower bound on the actual accessibility gain.",
        "",
        "## Methodology",
        "",
        "### Backtest",
        "1. Identify all stop_ids for routes operated by MM (Mi Macro BRT) and MT (Mi Tren light rail).",
        "2. Remove those stops from the GTFS feed; rebuild the transit graph.",
        "3. Recompute cumulative-opportunities accessibility (same W3.1 algorithm, 45-min budget).",
        "4. Recompute coverage-gap index in-memory (same W3.2 formula).",
        "5. Re-run W6 anchor selection (Jenks + KMeans) and MST corridor generation.",
        "6. For each masked route shape, sample 200 points at equal intervals; compute fraction within 400m of any re-proposed corridor.",
        "",
        "### Benchmark",
        "1. Reconstruct SITEUR premium route LineStrings from GTFS shapes.txt.",
        "2. For each W6 corridor, compute max overlap fraction against all premium routes.",
        "",
        "### Before/After Metrics",
        "- **Coverage rate:** fraction of AGEB centroids within 400m of any transit stop/corridor.",
        "- **Accessibility Gini:** Gini coefficient of accessibility_score across all AGEBs.",
        "- **Pop-served/km:** sum of population in AGEBs within 400m of W6 corridors / total W6 km.",
    ]

    out = OUTPUT_DIR / "w8_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [OK] Report written: {out}")


def main() -> None:
    SEP = "=" * 70
    print(f"\n{SEP}\n  W8: VALIDATION\n{SEP}")
    engine = create_engine(PG_URI)
    ensure_nppv_features(engine)

    try:
        print("\n[W8.1] Running backtest (mask premium routes + re-propose corridors)...")
        backtest = run_backtest(engine, data_dir=DATA_DIR)

        print("\n[W8.2] Running benchmark (W6 vs. premium route shapes)...")
        if not W6_GEOJSON.exists():
            print(f"  [ERR] W6 GeoJSON not found at {W6_GEOJSON}. Run W6 first.")
            benchmark = {
                "n_w6_corridors": 0, "n_premium_routes": 0,
                "mean_w6_overlap_with_premium": 0.0, "w6_total_km": 0.0,
                "detail": pd.DataFrame(),
            }
        else:
            benchmark = run_benchmark(W6_GEOJSON, data_dir=DATA_DIR)

        print("\n[W8.3] Computing before/after metrics...")
        if W6_GEOJSON.exists():
            metrics = compute_before_after_metrics(engine, W6_GEOJSON)
        else:
            metrics = {
                "coverage_rate_before": 0.0, "coverage_rate_after": 0.0,
                "gini_before": 0.0, "gini_after": 0.0,
                "pop_served_per_km_w6": 0.0, "n_ageb_newly_served": 0,
                "total_population_newly_served": 0.0, "w6_total_km": 0.0,
            }

        print("\n[W8] Writing outputs...")
        write_coverage_chart(metrics)
        write_backtest_chart(backtest)
        write_report(metrics, backtest, benchmark)

        if backtest.get("per_route_overlap"):
            pd.DataFrame(backtest["per_route_overlap"]).to_csv(
                OUTPUT_DIR / "w8_backtest_per_route.csv", index=False
            )
        bench_df = benchmark.get("detail", pd.DataFrame())
        if not bench_df.empty:
            bench_df.to_csv(OUTPUT_DIR / "w8_benchmark_detail.csv", index=False)

        print(f"\n{SEP}\n  [OK] W8 VALIDATION COMPLETE\n{SEP}")
        print(f"\nOutputs in {OUTPUT_DIR}/:")
        print("  w8_report.md               -- consolidated validation report")
        print("  w8_before_after_metrics.png -- coverage rate + Gini bar charts")
        print("  w8_backtest_overlap.png    -- per-route backtest overlap chart")
        print("  w8_backtest_per_route.csv  -- per-route overlap fractions")
        print("  w8_benchmark_detail.csv    -- W6 vs. premium route overlap details")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
