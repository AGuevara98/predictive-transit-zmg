import pandas as pd
import requests
import zipfile
import io
from pathlib import Path
import sys

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

ETUP_URL = "https://www.inegi.org.mx/contenidos/programas/transporteurbano/datosabiertos/conjunto_de_datos_etup_mensual_csv.zip"

def fetch_ridership_data(output_dir="data/raw/ridership"):
    """
    Download and extract SITEUR ridership data from INEGI ETUP.
    """
    print("\n" + "="*70)
    print("PHASE 1: RIDERSHIP DATA ACQUISITION")
    print("="*70)
    
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading ETUP ridership data from INEGI...")
    try:
        response = requests.get(ETUP_URL)
        response.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # Find the main CSV
            csv_files = [f for f in z.namelist() if 'conjunto_de_datos' in f and f.endswith('.csv')]
            if not csv_files:
                print("  [ERR] No dataset CSV found in ETUP ZIP")
                return False
            
            print(f"  Extracting {csv_files[0]}...")
            with z.open(csv_files[0]) as f:
                df = pd.read_csv(f)
            
            # Filter for Jalisco (Entidad 14)
            gdl_df = df[df['CVE_ENT'] == 14]
            
            print(f"  [OK] Filtered {len(gdl_df)} records for Jalisco systems")
            
            # Map specific transport modes if needed (Tren Eléctrico, Macrobús, etc.)
            out_file = out_path / "jalisco_ridership_etup.csv"
            gdl_df.to_csv(out_file, index=False)
            print(f"[OK] Ridership data saved to {out_file}")
            return True
            
    except Exception as e:
        print(f"ERROR: Ridership acquisition failed: {e}")
        return False

if __name__ == "__main__":
    fetch_ridership_data()
