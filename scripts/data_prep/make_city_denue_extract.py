"""Slim a raw INEGI DENUE state CSV into a committed ZM extract, for any W9
transfer city. Parameterized replacement for make_mty_denue_extract.py.

The raw state DENUE export (~40 address/contact columns, gitignored) is filtered
to the city's ZM municipios and slimmed to the 6 columns w9_run_tier1.py needs.

Usage:
    python scripts/data_prep/make_city_denue_extract.py --city tol   # or ags, mty
    python scripts/data_prep/make_city_denue_extract.py --city ags --src path/to/denue.csv
"""
import argparse
import importlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

CITY_CONFIGS = {
    "mty": "src.w9_city_config",
    "tol": "src.w9_city_config_tol",
    "ags": "src.w9_city_config_ags",
}
KEEP = ["cve_ent", "cve_mun", "cve_loc", "ageb", "codigo_act", "per_ocu"]


def find_src(cfg) -> Path | None:
    """Locate a raw DENUE CSV for the state under data/ (glob over date suffixes)."""
    ent = cfg.CVE_ENT
    cands = sorted(ROOT.glob(f"data/denue_{ent}_*/conjunto_de_datos/denue_inegi_{ent}_.csv"))
    cands += sorted(ROOT.glob(f"data/denue_{ent}_*_csv/conjunto_de_datos/*.csv"))
    return cands[0] if cands else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True, choices=list(CITY_CONFIGS))
    ap.add_argument("--src", default=None, help="Raw state DENUE CSV (default: glob under data/)")
    args = ap.parse_args()
    cfg = importlib.import_module(CITY_CONFIGS[args.city])

    src = Path(args.src) if args.src else find_src(cfg)
    out = ROOT / "data" / "raw" / "denue" / f"{cfg.CITY_KEY}_denue_combined.csv"

    if src is None or not src.exists():
        print(f"[ERR] Raw DENUE CSV not found for state {cfg.CVE_ENT}.")
        print(f"      Download the state extract from https://www.inegi.org.mx/app/descarga/?ti=6")
        print(f"      (or the masiva path https://www.inegi.org.mx/contenidos/masiva/denue/), then")
        print(f"      pass it with --src.")
        sys.exit(1)

    df = pd.read_csv(src, dtype=str, encoding="latin-1", usecols=lambda c: c.lower() in KEEP)
    df.columns = [c.lower() for c in df.columns]
    df = df[df["cve_ent"].str.strip().str.zfill(2) == cfg.CVE_ENT].copy()
    df["cve_mun"] = df["cve_mun"].str.strip().str.zfill(3)
    df = df[df["cve_mun"].isin(cfg.ZM_MUNICIPALITIES)].copy()
    df = df[KEEP]

    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"[{args.city}] {len(df):,} establishments in {df['cve_mun'].nunique()} municipios -> {out}")


if __name__ == "__main__":
    main()
