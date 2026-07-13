"""
W8 probe -- does a W6-generated corridor reconstruct the real Line 4?

W6 ran on the 2024 (pre-Line-4) supply state and wrote candidates to
outputs/w6/corridor_candidates.geojson. This measures how well each candidate's
alignment overlaps the real Line 4 trace (data/linea_4.geojson), annotated by
feasibility.

Metrics per candidate (buffer BUF metres):
  recall    = fraction of Line 4 length lying within BUF of the candidate  (did we cover it?)
  precision = fraction of candidate length lying within BUF of Line 4      (is the candidate on it?)
  iou       = area IoU of the two BUF-buffered footprints
  min_dist  = closest approach (m)

High recall on a FEASIBLE candidate  = framework reconstructed Line 4 blind (headline result).
High recall on an INFEASIBLE candidate = it found the corridor but rejected it (e.g. 30 km cap) --
                                         a different, still-informative finding.

Run (WSL, venv active): python src/w8_line4_overlap.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geopandas as gpd
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
W6_PATH = ROOT / "outputs" / "w6" / "corridor_candidates.geojson"
L4_PATH = ROOT / "data" / "linea_4.geojson"
BUF = 400   # metres; walk-catchment scale. Bump to 800 for a looser match.


def to6372(gdf):
    """Return gdf in EPSG:6372, inferring CRS from coordinate magnitude if missing."""
    if gdf.crs is not None:
        return gdf.to_crs(6372)
    minx, miny, maxx, maxy = gdf.total_bounds
    if abs(maxx) <= 180 and abs(maxy) <= 90:          # looks like lon/lat
        return gdf.set_crs(4326).to_crs(6372)
    return gdf.set_crs(6372)                            # already projected metres


def main():
    # --- Line 4 real alignment (line geoms only) ---
    l4 = to6372(gpd.read_file(L4_PATH))
    l4_lines = l4[l4.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    l4u = unary_union(list((l4_lines if len(l4_lines) else l4).geometry))
    l4_buf = l4u.buffer(BUF)
    print(f"[Line 4] length {l4u.length / 1000:.1f} km; buffer {BUF} m")

    # --- W6 candidates ---
    w6 = to6372(gpd.read_file(W6_PATH))
    print(f"[W6] {len(w6)} candidates; columns: {list(w6.columns)}\n")

    feas_col = next((c for c in w6.columns if "feas" in c.lower()), None)
    id_col = next((c for c in w6.columns
                   if c.lower() in ("group_id", "corridor_id", "id", "name", "group")), None)

    rows = []
    for i, r in w6.iterrows():
        g = r.geometry
        if g is None or g.is_empty:
            continue
        recall = l4u.intersection(g.buffer(BUF)).length / l4u.length if l4u.length else 0.0
        precision = g.intersection(l4_buf).length / g.length if g.length else 0.0
        gbuf = g.buffer(BUF)
        union = gbuf.union(l4_buf).area
        iou = gbuf.intersection(l4_buf).area / union if union else 0.0
        rows.append({
            "id": r[id_col] if id_col else i,
            "feasible": r[feas_col] if feas_col else "?",
            "len_km": g.length / 1000,
            "recall": recall,
            "precision": precision,
            "iou": iou,
            "min_dist_m": g.distance(l4u),
        })

    rows.sort(key=lambda x: x["recall"], reverse=True)
    print(f"{'id':<10}{'feas':<7}{'len_km':>7}{'recall':>8}{'prec':>7}{'iou':>7}{'dist_m':>9}")
    for x in rows:
        print(f"{str(x['id']):<10}{str(x['feasible']):<7}{x['len_km']:>7.1f}"
              f"{x['recall']:>8.2f}{x['precision']:>7.2f}{x['iou']:>7.2f}{x['min_dist_m']:>9.0f}")

    if rows:
        b = rows[0]
        print(f"\n[VERDICT] best match: {b['id']} (feasible={b['feasible']}) recovers "
              f"{b['recall']:.0%} of Line 4 within {BUF} m; closest approach {b['min_dist_m']:.0f} m.")


if __name__ == "__main__":
    main()
