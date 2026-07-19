"""Slim the national CONAPO marginacion + CONEVAL rezago AGEB databases into a
committed per-city equity-indicators extract (mirrors the ZMG
zmg_indicators_combined.csv: cve_ageb, IM_2020, IRS_2020).

Sources (national, ~16MB each, gitignored under data/raw/indicators_src/):
  - CONAPO Indice de Marginacion Urbana 2020 (IMU_2020.xls)
      https://conapo.segob.gob.mx/work/models/CONAPO/Datos_Abiertos/Marginacion/IMU_2020.zip
      -> continuous IM_2020 ("Indice de marginacion, 2020"); higher = LESS marginalized
  - CONEVAL Grado de Rezago Social a nivel AGEB urbana 2020 (GRS_AGEB_urbana_2020.xlsx)
      https://www.coneval.org.mx/Medicion/Documents/GRS_AGEB_2020/GRS_AGEB_urbana_2020.zip
      -> categorical "Grado de Rezago Social" (Muy bajo..Muy alto). The continuous IRS
         index is not published at AGEB level, so we map the grade to an ORDINAL 0..4
         (higher = more rezago, matching the ZMG IRS_2020 direction) as IRS_2020. This is
         a documented approximation of the ZMG continuous index -- direction preserved.

Output: data/raw/census/{key}_indicators_combined.csv  (cve_ageb, IM_2020, IRS_2020)

Usage:
    python scripts/data_prep/make_city_indicators_extract.py --city tol   # or ags
"""
import argparse
import importlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

CITY_CONFIGS = {"mty": "src.w9_city_config", "tol": "src.w9_city_config_tol",
                "ags": "src.w9_city_config_ags"}
SRC_DIR = ROOT / "data" / "raw" / "indicators_src"
IMU_XLS = SRC_DIR / "IMU_2020.xls"
GRS_XLSX = SRC_DIR / "GRS_AGEB_urbana_2020.xlsx"
REZAGO_ORDINAL = {"Muy bajo": 0, "Bajo": 1, "Medio": 2, "Alto": 3, "Muy alto": 4}


def load_marginacion(ent: str) -> pd.DataFrame:
    df = pd.read_excel(IMU_XLS, dtype=str, skiprows=3)  # title banner rows 0-2
    df = df.rename(columns={
        "Clave geográfica": "cve_ageb",
        "Clave de la entidad federativa": "ent",
        "Índice de marginación, 2020": "IM_2020",
    })
    df = df[(df["ent"] == ent) & df["cve_ageb"].notna()]
    return df[["cve_ageb", "IM_2020"]].copy()


def load_rezago(ent: str) -> pd.DataFrame:
    # Positional parse: data starts at row 6; col 0=ent, col 7=clave AGEB, col 27=grado
    df = pd.read_excel(GRS_XLSX, dtype=str, header=None, skiprows=6, engine="openpyxl")
    df = df.rename(columns={0: "ent", 7: "cve_ageb", 27: "grado"})
    df = df[(df["ent"] == ent) & df["cve_ageb"].notna()]
    df["IRS_2020"] = df["grado"].str.strip().map(REZAGO_ORDINAL)
    return df[["cve_ageb", "IRS_2020"]].copy()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True, choices=list(CITY_CONFIGS))
    args = ap.parse_args()
    cfg = importlib.import_module(CITY_CONFIGS[args.city])
    ent = cfg.CVE_ENT

    if not IMU_XLS.exists() or not GRS_XLSX.exists():
        print(f"[ERR] Missing source files under {SRC_DIR}:")
        print(f"      IMU_2020.xls (CONAPO marginacion) + GRS_AGEB_urbana_2020.xlsx (CONEVAL rezago)")
        print(f"      Download: conapo.segob.gob.mx .../Marginacion/IMU_2020.zip  and")
        print(f"               coneval.org.mx .../GRS_AGEB_2020/GRS_AGEB_urbana_2020.zip")
        sys.exit(1)

    marg = load_marginacion(ent)
    rez = load_rezago(ent)
    out = marg.merge(rez, on="cve_ageb", how="outer")
    dst = ROOT / "data" / "raw" / "census" / f"{cfg.CITY_KEY}_indicators_combined.csv"
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dst, index=False)
    print(f"[{args.city}] state {ent}: {len(marg)} marginacion, {len(rez)} rezago -> "
          f"{len(out)} merged -> {dst}")
    print(f"  IM_2020 non-null {out['IM_2020'].notna().sum()}, "
          f"IRS_2020 (ordinal grade) non-null {out['IRS_2020'].notna().sum()}")


if __name__ == "__main__":
    main()
