"""One-off: slim the 62MB Jalisco CPV2020 AGEB-urbana CSV to a committed
ZMG-only extract (~<1MB). Source lives outside the repo at ../gdl/...
Run once locally; the OUTPUT csv is the committed artifact."""
import sys
from pathlib import Path
import pandas as pd

SRC = Path("../gdl/ageb_mza_urbana_14_cpv2020_csv/ageb_mza_urbana_14_cpv2020/"
           "conjunto_de_datos/conjunto_de_datos_ageb_urbana_14_cpv2020.csv")
OUT = Path("data/raw/census/ageb_urbana_14_cpv2020_zmg.csv")
ZMG_MUNS = ["039", "120", "098", "101", "097", "070", "044", "051", "124", "002"]
KEEP = ["POBTOT", "POB0_14", "POB15_64", "POB65_MAS", "P_15A17", "P_18A24",
        "VPH_AUTOM", "VIVPAR_HAB"]

def main():
    if not SRC.exists():
        print(f"[ERR] Source census CSV not found at {SRC}")
        sys.exit(1)
    df = pd.read_csv(SRC, dtype=str, encoding="latin-1")
    df = df[(df["MZA"] == "000") & (df["MUN"].isin(ZMG_MUNS))].copy()
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
