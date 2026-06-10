import requests
import pandas as pd
from pathlib import Path
import sys
import time

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import INEGI_TOKEN

# INEGI Municipality Codes (Jalisco = 14)
ZMG_MUNI_CODES = {
    "Acatlán de Juárez": "14002",
    "El Salto": "14070",
    "Guadalajara": "14039",
    "Ixtlahuacán de los Membrillos": "14044",
    "Juanacatlán": "14051",
    "San Pedro Tlaquepaque": "14098",
    "Tlajomulco de Zúñiga": "14097",
    "Tonalá": "14101",
    "Zapopan": "14120",
    "Zapotlanejo": "14124"
}

def fetch_denue_for_municipality(muni_name, muni_code, token, output_dir="data/raw/denue"):
    """
    Fetch all establishments for a specific municipality from DENUE API.
    """
    base_url = "https://www.inegi.org.mx/app/api/denue/v1/consulta/buscarAreaAct"
    
    # Correct URL pattern with 14 parameters:
    # {entidad}/{municipio}/{localidad}/{ageb}/{manzana}/{sector}/{subsector}/{rama}/{clase}/{nombre}/{inicio}/{final}/{id}/{token}
    # Using '0' for all filters except entidad and municipio.
    
    ent_id = muni_code[:2]
    muni_id = muni_code[2:]
    
    keyword = "0" # nombre
    localidad = "0"
    ageb = "0"
    manzana = "0"
    sector = "0"
    subsector = "0"
    rama = "0"
    clase = "0"
    establishment_id = "0"
    
    page_size = 1000
    all_data = []
    
    print(f"Fetching DENUE data for {muni_name} ({muni_code})...")
    
    start_range = 1
    end_range = page_size
    
    while True:
        url = f"{base_url}/{ent_id}/{muni_id}/{localidad}/{ageb}/{manzana}/{sector}/{subsector}/{rama}/{clase}/{keyword}/{start_range}/{end_range}/{establishment_id}/{token}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if not data or not isinstance(data, list):
                break
            
            all_data.extend(data)
            print(f"  [OK] Records {start_range} to {len(all_data)}")
            
            if len(data) < page_size:
                break
                
            start_range += page_size
            end_range += page_size
            
            # Avoid hitting rate limits
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  [ERR] Failed at range {start_range}-{end_range}: {e}")
            break
            
    if all_data:
        df = pd.DataFrame(all_data)
        out_file = Path(output_dir) / f"{muni_name.replace(' ', '_').lower()}.csv"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_file, index=False)
        print(f"  [DONE] Saved {len(df)} records to {out_file}")
        return df
    
    return None

def main():
    print("\n" + "="*70)
    print("PHASE 1: DENUE DATA ACQUISITION")
    print("="*70)
    
    if not INEGI_TOKEN or INEGI_TOKEN == "cd679f19-87f5-4298-b938-fcdc43257359":
        # Check if it was replaced in config.py. The default value is what the user gave.
        # But if it's still the default, it's fine as the user gave it to me.
        pass
    
    all_dfs = []
    for muni_name, muni_code in ZMG_MUNI_CODES.items():
        df = fetch_denue_for_municipality(muni_name, muni_code, INEGI_TOKEN)
        if df is not None:
            all_dfs.append(df)
            
    if all_dfs:
        full_df = pd.concat(all_dfs)
        out_path = Path("data/raw/denue/zmg_denue_combined.csv")
        full_df.to_csv(out_path, index=False)
        print(f"\n[OK] Combined DENUE data saved to {out_path} ({len(full_df)} total records)")
        return True
    
    print("\nERROR: No DENUE data fetched.")
    return False

if __name__ == "__main__":
    main()
