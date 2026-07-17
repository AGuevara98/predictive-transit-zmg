"""Slim a raw INEGI CPV2020 AGEB-urbana state CSV into a committed ZM extract,
for any W9 transfer city. Parameterized replacement for make_mty_census_extract.py.

The raw state census (downloaded manually from the INEGI CPV2020 portal --
direct URLs 404, use the interactive picker; the extracted CSV is gitignored,
too large) is filtered to AGEB-level rows (MZA=="000") in the city's ZM
municipios, slimmed to the columns w9_run_tier1.py needs, and written to the
committed slim path.

Sanity check: asserts the number of DISTINCT municipios matched equals the
config's expected count (16 for Toluca, 3 for Aguascalientes, 12 for Monterrey),
and prints the per-municipio AGEB counts -- so a wrong CVE_MUN code surfaces
immediately instead of silently dropping/adding a municipality.

Usage:
    python scripts/data_prep/make_city_census_extract.py --city tol   # or ags, mty
    python scripts/data_prep/make_city_census_extract.py --city tol --src path/to/raw.csv
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
KEEP = ["POBTOT", "POB0_14", "POB15_64", "POB65_MAS", "P_15A17", "P_18A24",
        "VPH_AUTOM", "VIVPAR_HAB"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True, choices=list(CITY_CONFIGS))
    ap.add_argument("--src", default=None,
                    help="Raw state census CSV (default: derive from config CENSUS_DIR/NAME)")
    args = ap.parse_args()
    cfg = importlib.import_module(CITY_CONFIGS[args.city])

    src = Path(args.src) if args.src else (
        ROOT / "data" / cfg.CENSUS_DIR_NAME / "conjunto_de_datos" / cfg.CENSUS_CSV_NAME)
    out = ROOT / "data" / "raw" / "census" / f"ageb_urbana_{cfg.CVE_ENT}_cpv2020_{cfg.CITY_KEY}.csv"

    if not src.exists():
        print(f"[ERR] Raw census CSV not found at:\n    {src}")
        print(f"      Download the state-{cfg.CVE_ENT} CPV2020 AGEB-urbana CSV from:")
        print(f"      {cfg.CENSUS_ZIP_URL}  (Microdatos > AGEB y manzana urbana > state {cfg.CVE_ENT})")
        print(f"      then pass it with --src, or extract under data/{cfg.CENSUS_DIR_NAME}/")
        sys.exit(1)

    df = pd.read_csv(src, dtype=str, encoding="utf-8-sig")
    df = df[(df["MZA"] == "000") & (df["MUN"].str.zfill(3).isin(cfg.ZM_MUNICIPALITIES))].copy()
    df["MUN"] = df["MUN"].str.zfill(3)
    df["cve_ageb"] = (df["ENTIDAD"].str.zfill(2) + df["MUN"]
                      + df["LOC"].str.zfill(4) + df["AGEB"].str.zfill(4))
    for c in KEEP:
        if c not in df.columns:
            print(f"  [WARN] column {c} absent; filling 0")
            df[c] = "0"

    # --- sanity check: exact municipio coverage ---
    found = sorted(df["MUN"].unique())
    expected = sorted(cfg.ZM_MUNICIPALITIES)
    counts = df.groupby("MUN")["cve_ageb"].count().to_dict()
    print(f"[{args.city}] municipios matched: {len(found)} / {len(expected)} expected")
    for m in expected:
        flag = "" if m in counts else "  <-- MISSING (check CVE_MUN code!)"
        print(f"    {m}: {counts.get(m, 0):>4} AGEBs{flag}")
    extra = set(found) - set(expected)
    if extra:
        print(f"  [WARN] unexpected municipios present: {sorted(extra)}")
    if set(found) != set(expected):
        print("  [ERR] municipio set != config ZM_MUNICIPALITIES -- fix codes before using.")
        sys.exit(2)

    out.parent.mkdir(parents=True, exist_ok=True)
    df[["cve_ageb"] + KEEP].to_csv(out, index=False)
    print(f"[OK] wrote {len(df):,} AGEB rows to {out}")


if __name__ == "__main__":
    main()
