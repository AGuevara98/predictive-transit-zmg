"""
W5: Multi-Objective Function -- Demo Orchestrator
==================================================
Proves the W5 evaluation framework end-to-end against three synthetic
route candidates built from real high-gap AGEBs in the database.

Usage:
    python src/run_w5.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import LineString, Point
from sqlalchemy import create_engine, text

from config import PG_URI
from src.w5_types import RouteCandidate, W5Config
from src.w5_objective import load_ageb_context, evaluate_objective
from src.w5_constraints import check_constraints
from src.w5_pareto import pareto_rank

OUTPUT_DIR = Path("outputs/w5")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_high_gap_ageb_info(engine, n: int = 10) -> pd.DataFrame:
    """Return top-n High-gap AGEBs with centroids, demand, and equity score."""
    query = text("""
        SELECT
            g.cve_ageb                             AS cvegeo,
            t.transit_demand,
            COALESCE(p.equity_score, 0)            AS equity_score,
            ST_X(ST_Centroid(a.geom))              AS cx,
            ST_Y(ST_Centroid(a.geom))              AS cy
        FROM features.ageb_coverage_gap g
        JOIN base.ageb a
            ON a.cvegeo = g.cve_ageb
        JOIN features.ageb_trip_ends t
            ON t.cve_ageb = g.cve_ageb
        LEFT JOIN features.nppv_prioritization p
            ON p.cve_ageb = g.cve_ageb
        WHERE g.gap_category = 'High-gap'
        ORDER BY t.transit_demand DESC
        LIMIT :n
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"n": n}).fetchall()
    df = pd.DataFrame(rows, columns=["cvegeo", "transit_demand", "equity_score", "cx", "cy"])
    df["transit_demand"] = pd.to_numeric(df["transit_demand"], errors="coerce").fillna(0.0)
    df["equity_score"] = pd.to_numeric(df["equity_score"], errors="coerce").fillna(0.0)
    df["cx"] = pd.to_numeric(df["cx"], errors="coerce")
    df["cy"] = pd.to_numeric(df["cy"], errors="coerce")
    return df


def build_candidate(cid: str, df: pd.DataFrame, connects: bool) -> RouteCandidate:
    """Construct a RouteCandidate from a subset of AGEB centroid rows."""
    pts = list(zip(df["cx"].tolist(), df["cy"].tolist()))
    if len(pts) < 2:
        pts = pts * 2
    line = LineString(pts)
    route_km = line.length / 1000.0
    straight_km = max(Point(pts[0]).distance(Point(pts[-1])) / 1000.0, 0.001)
    n_stops = max(2, math.ceil(route_km / 0.5) + 1)
    return RouteCandidate(
        candidate_id=cid,
        served_ageb_ids=df["cvegeo"].tolist(),
        route_km=route_km,
        n_stops=n_stops,
        straight_line_km=straight_km,
        connects_to_existing=connects,
    )


def write_spec(config: W5Config) -> None:
    lines = [
        "# W5 Multi-Objective Function Specification",
        "",
        "This document is the authoritative interface contract for W6 (corridor generation) and W7 (route audit).",
        "",
        "## Objective Terms",
        "",
        "| Term | Direction | Formula |",
        "|------|-----------|---------|",
        "| f1 demand gain | maximize | `sum(demand_i * gain_factor * unserved_fraction_i) / sum(demand_i)` |",
        "| f2 route cost  | minimize | `route_km` |",
        "| f3 equity      | maximize | `mean(equity_score_i)` for served AGEBs |",
        "",
        "Where:",
        f"- `gain_factor = {config.connected_gain_factor}` if route connects to existing SITEUR network, "
        f"else `{config.isolated_gain_factor}`",
        "- `unserved_fraction` = `coverage_gap_normalized` from `features.ageb_coverage_gap` (1=unserved, 0=well-served)",
        "- `equity_score` = from `features.nppv_prioritization` (mean of `pe_marginacion_n`, `pe_rezago_n`)",
        "",
        "## Transfer Penalty",
        "",
        f"Routes not connected to the existing SITEUR network incur a flat `{config.transfer_penalty}` deduction",
        "from the composite score, representing required transfers for riders.",
        "",
        "## Scalar Composite Score",
        "",
        "```",
        "efficiency  = max(0, 1 - route_km / max_route_km)",
        "f1_scaled   = f1_demand_gain / gain_factor   # rescale to [0, 1]",
        "composite   = w_demand_gain * f1_scaled + w_efficiency * efficiency + w_equity * f3",
        "total_score = composite - transfer_penalty",
        "```",
        "",
        "Default weights:",
        f"- `w_demand_gain = {config.w_demand_gain}`",
        f"- `w_efficiency  = {config.w_efficiency}`",
        f"- `w_equity      = {config.w_equity}`",
        f"- `max_route_km  = {config.max_route_km}`",
        "",
        "## Pareto Multi-Objective Mode",
        "",
        "For ranking a population of candidates, minimize the objective vector `(-f1, f2, -f3)`",
        "using fast non-dominated sort (NSGA-II style). Rank 1 = Pareto-optimal front.",
        "",
        "## Constraints",
        "",
        "All four constraints must pass for a candidate to be feasible:",
        "",
        "| Constraint | Limit |",
        "|---|---|",
        f"| detour_ratio = route_km / straight_line_km | <= {config.max_detour_ratio} |",
        f"| stop_spacing = route_km*1000 / (n_stops-1) | [{config.min_stop_spacing_m:.0f}, {config.max_stop_spacing_m:.0f}] m |",
        f"| sum(transit_demand) | >= {config.min_daily_demand:.0f} trips/day |",
        f"| route_km | <= {config.max_route_km:.0f} km |",
        "",
        "## RouteCandidate Interface",
        "",
        "W6 and W7 must populate a `RouteCandidate` with:",
        "",
        "```python",
        "RouteCandidate(",
        "    candidate_id      = str,         # unique identifier",
        "    served_ageb_ids   = List[str],   # cvegeo of AGEBs within 400m of route",
        "    route_km          = float,       # total route length in km",
        "    n_stops           = int,         # number of stops",
        "    straight_line_km  = float,       # endpoint-to-endpoint Euclidean distance km",
        "    connects_to_existing = bool,     # True if route joins SITEUR network",
        ")",
        "```",
        "",
        "Then call:",
        "",
        "```python",
        "from w5_objective import load_ageb_context, evaluate_objective",
        "from w5_constraints import check_constraints",
        "from w5_pareto import pareto_rank",
        "",
        "contexts   = load_ageb_context(candidate.served_ageb_ids, engine)",
        "objective  = evaluate_objective(candidate, contexts, config)",
        "constraint = check_constraints(candidate, contexts, config)",
        "```",
    ]
    (OUTPUT_DIR / "w5_spec.md").write_text("\n".join(lines), encoding="utf-8")
    print("  [OK] w5_spec.md written")


def write_report(candidates, objectives, constraints, ranks):
    cfg = W5Config()
    lines = [
        "# W5 Multi-Objective Function -- Demo Report",
        "",
        "Three synthetic route candidates were constructed from real high-gap AGEBs",
        "to validate the W5 evaluation framework end-to-end.",
        "",
        "## Candidate Summary",
        "",
        "| Candidate | AGEBs | km | Stops | Connected |",
        "|---|---|---|---|---|",
    ]
    for c in candidates:
        lines.append(
            f"| {c.candidate_id} | {len(c.served_ageb_ids)} "
            f"| {c.route_km:.2f} | {c.n_stops} | {c.connects_to_existing} |"
        )
    lines += [
        "",
        "## Objective Scores",
        "",
        "| Candidate | f1 gain | f2 km | f3 equity | Composite | Total | Pareto Rank | Feasible |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c, obj, cr, rank in zip(candidates, objectives, constraints, ranks):
        lines.append(
            f"| {c.candidate_id} | {obj.f1_demand_gain:.4f} | {obj.f2_route_km:.2f} "
            f"| {obj.f3_equity:.4f} | {obj.composite_score:.4f} "
            f"| {obj.total_score:.4f} | {rank} | {cr.feasible} |"
        )
    for c, cr in zip(candidates, constraints):
        if cr.violations:
            lines.append(f"\n**{c.candidate_id} violations:**")
            for v in cr.violations:
                lines.append(f"- {v.message}")
    lines += [
        "",
        "## W5 Config Used",
        "",
        "```",
        f"w_demand_gain         = {cfg.w_demand_gain}",
        f"w_efficiency          = {cfg.w_efficiency}",
        f"w_equity              = {cfg.w_equity}",
        f"connected_gain_factor = {cfg.connected_gain_factor}",
        f"isolated_gain_factor  = {cfg.isolated_gain_factor}",
        f"transfer_penalty      = {cfg.transfer_penalty}",
        f"max_detour_ratio      = {cfg.max_detour_ratio}",
        f"min_stop_spacing_m    = {cfg.min_stop_spacing_m}",
        f"max_stop_spacing_m    = {cfg.max_stop_spacing_m}",
        f"min_daily_demand      = {cfg.min_daily_demand}",
        f"max_route_km          = {cfg.max_route_km}",
        "```",
    ]
    (OUTPUT_DIR / "w5_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("  [OK] w5_report.md written")


def write_pareto_chart(objectives, ranks):
    fig, ax = plt.subplots(figsize=(8, 6))
    cmap = plt.cm.RdYlGn_r
    max_rank = max(ranks) if max(ranks) > 0 else 1
    for obj, rank in zip(objectives, ranks):
        color = cmap(rank / max_rank)
        ax.scatter(obj.f2_route_km, obj.f1_demand_gain, c=[color], s=160, zorder=3)
        ax.annotate(
            f"{obj.candidate_id}\n(rank {rank})",
            (obj.f2_route_km, obj.f1_demand_gain),
            textcoords="offset points", xytext=(8, 4), fontsize=9,
        )
    ax.set_xlabel("f2: Route length (km) - minimize")
    ax.set_ylabel("f1: Demand-weighted accessibility gain - maximize")
    ax.set_title("W5 Demo: Pareto space (f1 vs f2)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "w5_pareto_demo.png", dpi=150)
    plt.close(fig)
    print("  [OK] w5_pareto_demo.png written")


def main():
    print("\n" + "=" * 70)
    print("  W5: MULTI-OBJECTIVE FUNCTION DEMO")
    print("=" * 70)
    cfg = W5Config()

    print("\n[Step 1] Connecting to database...")
    engine = create_engine(PG_URI)

    print("[Step 2] Fetching top-10 high-gap AGEBs...")
    df = fetch_high_gap_ageb_info(engine, n=10)
    if df.empty:
        print("  [ERR] No High-gap AGEBs found. Run W3 first.")
        engine.dispose()
        sys.exit(1)
    print(f"  [OK] {len(df)} AGEBs loaded")

    print("[Step 3] Building synthetic route candidates...")
    cand_a = build_candidate("A_demand", df.nlargest(3, "transit_demand"), connects=True)
    cand_b = build_candidate("B_equity", df.nlargest(5, "equity_score"), connects=False)
    cand_c = build_candidate("C_broad", df.head(5), connects=True)
    candidates = [cand_a, cand_b, cand_c]
    for c in candidates:
        print(f"  {c.candidate_id}: {len(c.served_ageb_ids)} AGEBs, {c.route_km:.2f}km, "
              f"{c.n_stops} stops, connected={c.connects_to_existing}")

    print("[Step 4] Loading AGEB context from DB...")
    all_ids = list({aid for c in candidates for aid in c.served_ageb_ids})
    contexts_list = load_ageb_context(all_ids, engine)
    ctx_map = {ctx.cvegeo: ctx for ctx in contexts_list}
    print(f"  [OK] {len(ctx_map)} AGEBs with context loaded")

    print("[Step 5] Evaluating objectives and constraints...")
    objectives = []
    constraints_results = []
    for c in candidates:
        ctxs = [ctx_map[aid] for aid in c.served_ageb_ids if aid in ctx_map]
        obj = evaluate_objective(c, ctxs, cfg)
        cr = check_constraints(c, ctxs, cfg)
        objectives.append(obj)
        constraints_results.append(cr)
        print(f"  {c.candidate_id}: f1={obj.f1_demand_gain:.4f} f2={obj.f2_route_km:.2f}km "
              f"f3={obj.f3_equity:.4f} total={obj.total_score:.4f} feasible={cr.feasible}")
        for v in cr.violations:
            print(f"    [VIOLATION] {v.message}")

    print("[Step 6] Pareto ranking...")
    ranks = pareto_rank(objectives)
    for c, rank in zip(candidates, ranks):
        print(f"  {c.candidate_id}: Pareto rank {rank}")

    print("[Step 7] Writing outputs...")
    write_spec(cfg)
    write_report(candidates, objectives, constraints_results, ranks)
    write_pareto_chart(objectives, ranks)

    engine.dispose()
    print("\n" + "=" * 70)
    print("  [OK] W5 DEMO COMPLETE")
    print("=" * 70)
    print("File outputs: outputs/w5/")
    print("  w5_spec.md         -- interface contract for W6/W7")
    print("  w5_report.md       -- demo evaluation results")
    print("  w5_pareto_demo.png -- Pareto scatter plot")


if __name__ == "__main__":
    main()
