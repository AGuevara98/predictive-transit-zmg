"""
W9 W4 -- NPP prioritization for a transfer city (CSV-based, no DB)
=================================================================
Runs the W4 CRITIC/EWM + equity prioritization on a transfer city's NPP features
(outputs/w9/{key}_nppv_features.csv from w9_build_nppv.py), reusing the pure ZMG
W4 weighting/scoring functions.

  npp_score    = sum(feature_i * ensemble_weight_i)      [CRITIC+EWM, 14 features]
  equity_score = mean(pe_marginacion_n, pe_rezago_n)
  final_score  = 0.80 * npp_score + 0.20 * equity_score

Output: outputs/w9/{key}_w4_weights.csv, {key}_prioritization.csv

Usage:
    python src/w9_run_w4.py --city ags     # or tol
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Pure W4 functions (importing w4_prioritization does not open a DB connection --
# its engine is lazy via _get_engine()).
from src.w4_prioritization import (
    NPP_FEATURES, EQUITY_FEATURES, DIMENSIONS, ALPHA,
    compute_critic_weights, compute_ewm_weights, compute_ensemble_weights, compute_scores,
)
from src.w9_run_tier1 import load_city_config

OUTPUT_DIR = ROOT / "outputs" / "w9"


def run_city(city_key: str) -> None:
    cfg = load_city_config(city_key)
    print("\n" + "=" * 70)
    print(f"W9 W4 -- NPP PRIORITIZATION for {cfg.CITY_NAME.upper()} ({city_key})")
    print("=" * 70)

    feat = pd.read_csv(OUTPUT_DIR / f"{city_key}_nppv_features.csv", dtype={"cve_ageb": str})
    for c in NPP_FEATURES:
        feat[c] = pd.to_numeric(feat[c], errors="coerce").fillna(0.0)
    print(f"[1] {len(feat):,} AGEBs x {len(NPP_FEATURES)} NPP features")

    critic = compute_critic_weights(feat[NPP_FEATURES])
    ewm = compute_ewm_weights(feat[NPP_FEATURES])
    ens = compute_ensemble_weights(critic, ewm)
    scores = compute_scores(feat, ens, alpha=ALPHA)

    weights = pd.DataFrame([
        {"feature": f, "dimension": DIMENSIONS[f], "critic_weight": critic[f],
         "ewm_weight": ewm[f], "ensemble_weight": ens[f]}
        for f in NPP_FEATURES
    ]).sort_values("ensemble_weight", ascending=False)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    weights.to_csv(OUTPUT_DIR / f"{city_key}_w4_weights.csv", index=False)
    scores.to_csv(OUTPUT_DIR / f"{city_key}_prioritization.csv", index=False)

    print("\n[2] Top-5 ensemble weights:")
    for _, r in weights.head(5).iterrows():
        print(f"    {r['feature']:<26} {r['dimension']:<7} {r['ensemble_weight']:.4f}")
    print(f"\n[3] Scores ({len(scores):,} AGEBs): "
          f"npp mean={scores['npp_score'].mean():.4f}, "
          f"equity mean={scores['equity_score'].mean():.4f}, "
          f"final mean={scores['final_score'].mean():.4f}")
    print(f"  [OK] outputs/w9/{city_key}_w4_weights.csv, {city_key}_prioritization.csv")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True, choices=["tol", "ags"])
    run_city(ap.parse_args().city)


if __name__ == "__main__":
    main()
