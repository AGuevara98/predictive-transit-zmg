import pandas as pd
from pathlib import Path
import requests
import zipfile
import io
import sys

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

# Local Paths
MARGINACION_CSV = "C:/Users/aguev/Documents/Maestria_UDG/tesis/gdl/indice_marginacion_jalisco.csv"
CENSUS_DIR = "C:/Users/aguev/Documents/Maestria_UDG/tesis/gdl/ageb_mza_urbana_14_cpv2020_csv/ageb_mza_urbana_14_cpv2020/conjunto_de_datos"
REZAGO_URL = "https://www.coneval.org.mx/Medicion/Documents/GRS_AGEB_2020/GRS_AGEB_urbana_2020.zip"

def process_indicators(output_dir="data/raw/census"):
    """
    Download Rezago Social and combine with local Marginación data.
    """
    print("\n" + "="*70)
    print("PHASE 1: CENSUS & INDICATORS INGESTION")
    print("="*70)
    
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Marginación (Local)
    print(f"Loading local Marginación data: {MARGINACION_CSV}")
    try:
        marginacion_df = pd.read_csv(MARGINACION_CSV)
        # Ensure CVE_AGEB is string and 13 chars
        marginacion_df['cve_ageb'] = marginacion_df['CVE_AGEB'].astype(str).str.zfill(13)
        print(f"  [OK] Loaded {len(marginacion_df)} records")
    except Exception as e:
        print(f"  [ERR] Failed to load Marginación: {e}")
        marginacion_df = None

    # 2. Download Rezago Social (CONEVAL)
    print(f"Downloading Rezago Social data from CONEVAL...")
    try:
        response = requests.get(REZAGO_URL)
        response.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # Find the Excel file in the zip
            excel_files = [f for f in z.namelist() if f.endswith('.xlsx')]
            if not excel_files:
                print("  [ERR] No Excel found in Rezago ZIP")
                rezago_df = None
            else:
                print(f"  Extracting {excel_files[0]}...")
                with z.open(excel_files[0]) as f:
                    # Read without header first to find the right row
                    full_df = pd.read_excel(f, header=None)
                
                # The data starts at row 5 (0-indexed)
                # Headers are at row 2
                headers = full_df.iloc[2].tolist()
                data_df = full_df.iloc[5:].copy()
                data_df.columns = headers
                
                # Extract data using direct indices from full_df
                # Index 0: ENT, Index 7: AGEB, Index 21: IRS, Index 27: GRS
                jalisco_mask = pd.to_numeric(full_df.iloc[:, 0], errors='coerce') == 14
                rezago_jalisco = full_df[jalisco_mask].copy()
                
                rezago_df = pd.DataFrame({
                    'cve_ageb': rezago_jalisco.iloc[:, 7].astype(str).str.zfill(13),
                    'IRS_2020': pd.to_numeric(rezago_jalisco.iloc[:, 21], errors='coerce'),
                    'GRS_2020': rezago_jalisco.iloc[:, 27]
                })
                
                print(f"  [OK] Loaded and filtered {len(rezago_df)} Rezago records for Jalisco")
                
    except Exception as e:
        print(f"  [ERR] Failed to fetch Rezago Social: {e}")
        rezago_df = None
        
    # 3. Combine and Save
    if marginacion_df is not None and rezago_df is not None:
        print("\nCombining indicators...")
        # Merge on cve_ageb
        combined = pd.merge(
            marginacion_df[['cve_ageb', 'IM_2020', 'GM_2020']],
            rezago_df[['cve_ageb', 'IRS_2020', 'GRS_2020']], # Names based on CONEVAL 2020 standard
            on='cve_ageb',
            how='outer'
        )
        
        out_file = out_path / "zmg_indicators_combined.csv"
        combined.to_csv(out_file, index=False)
        print(f"[OK] Combined indicators saved to {out_file}")
        return True
        
    return False

if __name__ == "__main__":
    process_indicators()
