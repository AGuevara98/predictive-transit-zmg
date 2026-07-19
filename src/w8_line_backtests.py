"""
W8 -- Per-line masked backtests (route-level)
=============================================
Extends the single agency-level premium backtest to individual SITEUR lines, to
characterise WHICH line types the re-architected W6 generator does/does not trace.

Each line is masked at the ROUTE level via the aligned `run_backtest(route_ids=...)`
(frontier anchors on the masked served/unserved seam -> coverage_gap_n trim ->
MST-diameter-trunk shaper -> anchor-directness feasibility gate), so the overlap
numbers are directly citable for the canonical run_w6 generator (NOT the retired
build_corridor_path path used by the earlier scratchpad harnesses).

Line -> route_id sets. NOTE the two SITEUR agencies are DISTINCT services that happen
to share L1/L2/L3 numbering, they are NOT spatial duplicates (verified: MT_Lx vs ST_Lx
shape overlap < 0.10):
  - MT_* = Mi Tren tram / light-rail (agency MT, route_type=0, ~1 km stop spacing)
  - ST_* = SiTren feeder-bus network  (agency ST, route_type=3, ~85 m stop spacing)
Masking both per line mirrors the Line 3 precedent and removes the whole "line system"
(rail + its dedicated feeder); per-route overlap keeps the rail alignment distinct.

Usage:
    python src/w8_line_backtests.py            # runs Line 1 + Line 2 (default)
    python src/w8_line_backtests.py L1 L2 L3   # explicit subset
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sqlalchemy import create_engine

from config import PG_URI
from src.db_preflight import ensure_nppv_features
from src.w8_backtest import run_backtest

OUTPUT_DIR = Path("outputs/w8")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Line -> route_id set (mask rail + SiTren feeder together, per the Line 3 precedent)
LINE_ROUTES = {
    "L1": {"MT_L1", "ST_L1"},
    "L2": {"MT_L2", "ST_L2"},
    "L3": {"MT_L3", "ST_L3"},
}


def main() -> None:
    which = [a.upper() for a in sys.argv[1:]] or ["L1", "L2"]
    engine = create_engine(PG_URI)
    ensure_nppv_features(engine)

    summary_rows = []
    per_route_rows = []
    try:
        for line in which:
            route_ids = LINE_ROUTES[line]
            print(f"\n{'='*70}\n  BACKTEST -- {line} (mask {sorted(route_ids)})\n{'='*70}")
            res = run_backtest(engine, route_ids=route_ids)
            summary_rows.append({
                "line": line,
                "route_ids": ",".join(sorted(route_ids)),
                "n_stops_masked": res["n_excluded_stops"],
                "n_corridors_built": res.get("n_corridors_built"),
                "n_corridors_reproposed": res["n_corridors_reproposed"],
                "mean_overlap_fraction": res["mean_overlap_fraction"],
            })
            for r in res.get("per_route_overlap", []):
                per_route_rows.append({"line": line, **r})
    finally:
        engine.dispose()

    summary = pd.DataFrame(summary_rows)
    per_route = pd.DataFrame(per_route_rows)
    summary.to_csv(OUTPUT_DIR / "w8_line_backtests_summary.csv", index=False)
    if not per_route.empty:
        per_route.to_csv(OUTPUT_DIR / "w8_line_backtests_per_route.csv", index=False)

    print(f"\n{'='*70}\n  PER-LINE BACKTEST SUMMARY\n{'='*70}")
    print(summary.to_string(index=False))
    if not per_route.empty:
        print("\nPer-route overlap:")
        print(per_route.to_string(index=False))
    print(f"\n[OK] Wrote {OUTPUT_DIR}/w8_line_backtests_summary.csv")


if __name__ == "__main__":
    main()
