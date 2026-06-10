import requests
import json
from pathlib import Path
import sys
import os

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import NASA_JWT, ZMG_BBOX

def fetch_viirs_data(output_dir="data/raw/viirs", year=2023):
    """
    Search and download VIIRS VNP46A3 (Monthly) data for ZMG.
    """
    print("\n" + "="*70)
    print("PHASE 1: VIIRS DATA ACQUISITION")
    print("="*70)
    
    if not NASA_JWT or "JWT" in NASA_JWT[:10]:
        print("ERROR: NASA_JWT not set or invalid.")
        return False
        
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # CMR Search URL
    # VNP46A3: VIIRS/NPP Daily Gridded Day/Night Band Off-nadir L3 Black Marble Monthly
    short_name = "VNP46A3"
    
    # GDL Bounding Box: xmin, ymin, xmax, ymax
    bbox = f"{ZMG_BBOX['xmin']},{ZMG_BBOX['ymin']},{ZMG_BBOX['xmax']},{ZMG_BBOX['ymax']}"
    temporal = f"{year}-01-01T00:00:00Z,{year}-12-31T23:59:59Z"
    
    search_url = f"https://cmr.earthdata.nasa.gov/search/granules.json?short_name={short_name}&temporal={temporal}&bounding_box={bbox}"
    
    print(f"Searching for {short_name} granules for {year} in ZMG...")
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()
        
        entries = data.get('feed', {}).get('entry', [])
        print(f"  [OK] Found {len(entries)} granules")
        
        if not entries:
            return False
            
        # Filter for h07v06 (covers GDL at -103.3)
        download_urls = []
        for entry in entries:
            # Check for tile ID in links or title
            title = entry.get('title', '')
            # Find download link
            links = entry.get('links', [])
            for link in links:
                href = link.get('href', '')
                if href.endswith('.h5') and 'prod-lads' in href and 'h07v06' in href:
                    download_urls.append(href)
                    break
        
        print(f"  [OK] Filtered to {len(download_urls)} relevant tile URLs")
        
        # Download
        headers = {"Authorization": f"Bearer {NASA_JWT}"}
        session = requests.Session()
        
        for url in download_urls:
            filename = url.split('/')[-1]
            target = out_path / filename
            
            if target.exists():
                print(f"  [SKIP] {filename} already exists")
                continue
                
            print(f"Downloading {filename}...")
            try:
                with session.get(url, headers=headers, stream=True) as r:
                    r.raise_for_status()
                    with open(target, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                print(f"  [OK] Downloaded: {filename}")
            except Exception as e:
                print(f"  [ERR] Failed to download {filename}: {e}")
                
        print("\n[OK] VIIRS acquisition complete!")
        return True
        
    except Exception as e:
        print(f"ERROR: CMR search failed: {e}")
        return False

if __name__ == "__main__":
    fetch_viirs_data()
