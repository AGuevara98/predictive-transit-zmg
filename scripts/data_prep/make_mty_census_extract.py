"""One-off: slim the Nuevo Leon CPV2020 AGEB-urbana CSV to a committed
ZM-Monterrey-only extract (mirrors make_census_extract.py for ZMG).
Source lives at data/ageb_mza_urbana_19_cpv2020_csv/... (downloaded per
src/w9_city_config.py:CENSUS_ZIP_URL, gitignored — too close to GitHub's
100MB limit once extracted). Run once locally; the OUTPUT csv is the
committed artifact."""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.w9_city_config import ZM_MUNICIPALITIES, CENSUS_DIR_NAME, CENSUS_CSV_NAME

SRC = Path("data") / CENSUS_DIR_NAME / "conjunto_de_datos" / CENSUS_CSV_NAME
OUT = Path("data/raw/census/ageb_urbana_19_cpv2020_mty.csv")
KEEP = ["POBTOT", "POB0_14", "POB15_64", "POB65_MAS", "P_15A17", "P_18A24",
        "VPH_AUTOM", "VIVPAR_HAB"]

def main():
    if not SRC.exists():
        print(f"[ERR] Source census CSV not found at {SRC}")
        sys.exit(1)
    df = pd.read_csv(SRC, dtype=str, encoding="utf-8-sig")
    df = df[(df["MZA"] == "000") & (df["MUN"].isin(ZM_MUNICIPALITIES))].copy()
    df["cve_ageb"] = (df["ENTIDAD"].str.zfill(2) + df["MUN"].str.zfill(3)
                      + df["LOC"].str.zfill(4) + df["AGEB"].str.zfill(4))
    for c in KEEP:
        if c not in df.columns:
            df[c] = "0"
    out = df[["cve_ageb"] + KEEP].copy()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"[OK] wrote {len(out):,} rows to {OUT}")

if __name__ == "__main__":
    main()
