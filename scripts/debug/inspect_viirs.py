"""Inspect VIIRS h5 file structure and sample ZMG pixel values (h5py only)."""
import sys
import h5py
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import ZMG_BBOX

viirs_dir = Path("data/raw/viirs")
h5_files = sorted(viirs_dir.glob("*.h5"))
print(f"Found {len(h5_files)} h5 files\n")

DATASET_PATH = "HDFEOS/GRIDS/VNP_Grid_DNB/Data Fields/DNB_BRDF-Corrected_NTL"

for h5_path in h5_files[:2]:
    print(f"=== {h5_path.name} ===")
    with h5py.File(h5_path, "r") as hf:
        if DATASET_PATH not in hf:
            print(f"  [WARN] Dataset not found at: {DATASET_PATH}")
            print("  All datasets:")
            hf.visititems(lambda n, o: print(f"    {n}") if isinstance(o, h5py.Dataset) else None)
            continue

        data = hf[DATASET_PATH][:]
        ds_attrs = dict(hf[DATASET_PATH].attrs)
        print(f"  shape={data.shape}  dtype={data.dtype}")
        print(f"  dataset attrs:")
        for k, v in ds_attrs.items():
            print(f"    {k}: {v}")

        grid = hf["HDFEOS/GRIDS/VNP_Grid_DNB"]
        grid_attrs = dict(grid.attrs)
        print(f"  grid attrs:")
        for k, v in grid_attrs.items():
            print(f"    {k}: {v}")

        xmin = grid_attrs.get("WestBoundingCoordinate", "MISSING")
        xmax = grid_attrs.get("EastBoundingCoordinate", "MISSING")
        ymin = grid_attrs.get("SouthBoundingCoordinate", "MISSING")
        ymax = grid_attrs.get("NorthBoundingCoordinate", "MISSING")
        print(f"\n  bounds: W={xmin} E={xmax} S={ymin} N={ymax}")

        fill_val = ds_attrs.get("_FillValue", ds_attrs.get("fill_value", None))
        scale    = ds_attrs.get("scale_factor", 1.0)
        print(f"  fill_value={fill_val}  scale_factor={scale}")

        nrows, ncols = data.shape
        # Manually compute pixel indices for ZMG bbox
        if xmin != "MISSING":
            res_x = (xmax - xmin) / ncols
            res_y = (ymax - ymin) / nrows
            col_lo = int((ZMG_BBOX["xmin"] - xmin) / res_x)
            col_hi = int((ZMG_BBOX["xmax"] - xmin) / res_x)
            row_lo = int((ymax - ZMG_BBOX["ymax"]) / res_y)
            row_hi = int((ymax - ZMG_BBOX["ymin"]) / res_y)
            col_lo, col_hi = sorted([col_lo, col_hi])
            row_lo, row_hi = sorted([row_lo, row_hi])
            col_lo = max(0, col_lo); col_hi = min(ncols, col_hi)
            row_lo = max(0, row_lo); row_hi = min(nrows, row_hi)
            print(f"  ZMG pixel window: rows {row_lo}-{row_hi}, cols {col_lo}-{col_hi}")
            zmg = data[row_lo:row_hi, col_lo:col_hi]
            print(f"  ZMG slice shape: {zmg.shape}")
            print(f"  ZMG raw range: min={zmg.min()} max={zmg.max()} mean={zmg.mean():.2f}")
            if fill_val is not None:
                valid = zmg[zmg != fill_val]
                print(f"  ZMG valid pixels (excl fill): {len(valid)}, mean={valid.mean():.4f}" if len(valid) else "  ZMG valid pixels: 0")
            nonzero = zmg[zmg > 0]
            print(f"  ZMG non-zero pixels: {len(nonzero)}")
    print()
