"""One-off: slim the Nuevo Leon DENUE CSV to the columns w9_run_tier1.py
actually needs, restricted to ZM Monterrey municipalities (mirrors the
intent of make_census_extract.py for ZMG). Source lives at
data/denue_19_0420_csv/... (downloaded manually, gitignored — the full
export carries ~40 columns of address/contact detail not needed here).
Run once locally; the OUTPUT csv is the committed artifact."""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.w9_city_config import CVE_ENT, ZM_MUNICIPALITIES

SRC = Path("data/denue_19_0420_csv/conjunto_de_datos/denue_inegi_19_.csv")
OUT = Path("data/raw/denue/mty_denue_combined.csv")
KEEP = ["cve_ent", "cve_mun", "cve_loc", "ageb", "codigo_act", "per_ocu"]

def main():
    if not SRC.exists():
        print(f"[ERR] Source DENUE CSV not found at {SRC}")
        sys.exit(1)
    df = pd.read_csv(SRC, dtype=str, encoding="latin-1", usecols=KEEP)
    df = df[df["cve_ent"].str.strip() == CVE_ENT].copy()
    df["cve_mun"] = df["cve_mun"].str.strip().str.zfill(3)
    df = df[df["cve_mun"].isin(ZM_MUNICIPALITIES)].copy()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"[OK] wrote {len(df):,} rows to {OUT}")

if __name__ == "__main__":
    main()
