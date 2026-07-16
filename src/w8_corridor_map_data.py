import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import PG_URI
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
from shapely.geometry import mapping

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "w8"
OUT_DIR.mkdir(parents=True, exist_ok=True)

eng = create_engine(PG_URI)

ageb = gpd.read_postgis("""
    SELECT a.cvegeo AS cve_ageb, a.geom, cg.gap_category, cg.coverage_gap_n, te.transit_demand
    FROM base.ageb a
    LEFT JOIN features.ageb_coverage_gap cg ON cg.cve_ageb = a.cvegeo
    LEFT JOIN features.ageb_trip_ends    te ON te.cve_ageb = a.cvegeo
""", eng, geom_col="geom")

w6 = gpd.read_postgis("""
    SELECT candidate_id, route_km, total_demand, n_served_agebs, mode_assignment, geom
    FROM features.route_candidates WHERE feasible = true ORDER BY candidate_id
""", eng, geom_col="geom")

routes = gpd.read_postgis(
    "SELECT route_id, route_km, geom FROM features.route_audit", eng, geom_col="geom"
)

BUFFER_M = 400.0


def served_ids(corridor_geom, buf=BUFFER_M):
    cbuf = corridor_geom.buffer(buf)
    hit = ageb.geometry.centroid.within(cbuf)
    return set(ageb.loc[hit, "cve_ageb"])


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


print("[Step] served-AGEB sets for GTFS routes (redundancy + demand/km baseline)...")
route_served = {}
demand_per_km = {}
for _, r in routes.iterrows():
    s = served_ids(r.geom)
    route_served[r.route_id] = s
    d = ageb.loc[ageb["cve_ageb"].isin(s), "transit_demand"].sum()
    if r.route_km and r.route_km > 0:
        demand_per_km[r.route_id] = d / r.route_km
baseline = pd.Series(demand_per_km)

corridor_stats = {}
corridor_served = {}
for _, c in w6.iterrows():
    cid = c.candidate_id
    served = served_ids(c.geom)
    corridor_served[cid] = served
    sub = ageb[ageb["cve_ageb"].isin(served)]
    hi_share = (sub["gap_category"] == "High-gap").mean() if len(sub) else 0.0
    med_share = (sub["gap_category"] == "Medium-gap").mean() if len(sub) else 0.0
    lo_share = (sub["gap_category"] == "Low-gap").mean() if len(sub) else 0.0
    demand_med = sub["transit_demand"].median() if len(sub) else float("nan")
    best_route, best_j = None, 0.0
    for rid, rserved in route_served.items():
        j = jaccard(served, rserved)
        if j > best_j:
            best_route, best_j = rid, j
    dpk = c.total_demand / c.route_km if c.route_km else float("nan")
    pct = (baseline < dpk).mean() * 100
    corridor_stats[cid] = dict(
        route_km=c.route_km, total_demand=c.total_demand, n_served=len(sub),
        hi_share=hi_share, med_share=med_share, lo_share=lo_share,
        demand_med=demand_med, metro_demand_med=ageb["transit_demand"].median(),
        best_route=best_route, best_j=best_j, dpk=dpk,
        baseline_med=baseline.median(), pct=pct, mode=c.mode_assignment,
    )
    print(cid, corridor_stats[cid])

# --- projection: EPSG:6372 metres -> SVG viewBox pixels ---
minx, miny, maxx, maxy = ageb.total_bounds
W = 900.0
H = W * (maxy - miny) / (maxx - minx)
scale = W / (maxx - minx)


def to_svg_xy(x, y):
    return ((x - minx) * scale, (maxy - y) * scale)  # flip y


def ring_to_path(coords):
    pts = [to_svg_xy(x, y) for x, y in coords]
    d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + " Z"
    return d


def polygon_path(geom):
    parts = []
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    for poly in polys:
        parts.append(ring_to_path(poly.exterior.coords))
        for interior in poly.interiors:
            parts.append(ring_to_path(interior.coords))
    return " ".join(parts)


def line_path(geom):
    lines = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
    parts = []
    for ln in lines:
        pts = [to_svg_xy(x, y) for x, y in ln.coords]
        parts.append("M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts))
    return " ".join(parts)


GAP_CLASS = {"High-gap": "gap-hi", "Medium-gap": "gap-med", "Low-gap": "gap-lo", None: "gap-med"}

ageb_simplified = ageb.copy()
ageb_simplified["geom"] = ageb_simplified.geometry.simplify(12, preserve_topology=True)

ageb_paths = []
for _, row in ageb_simplified.iterrows():
    cls = GAP_CLASS.get(row.gap_category, "gap-med")
    d = polygon_path(row.geom)
    ageb_paths.append((row.cve_ageb, cls, d))

corridor_colors = {"W6_G00": "c-g00", "W6_G03": "c-g03", "W6_G05": "c-g05"}
corridor_paths = []
w6_simplified = w6.copy()
w6_simplified["geom"] = w6_simplified.geometry.simplify(5, preserve_topology=True)
for _, row in w6_simplified.iterrows():
    d = line_path(row.geom)
    corridor_paths.append((row.candidate_id, corridor_colors[row.candidate_id], d))

# served-ageb id sets per corridor, for hover highlight
served_json = {cid: sorted(ids) for cid, ids in corridor_served.items()}

import json
with open(OUT_DIR / "corridor_map_data.json", "w") as f:
    json.dump({
        "ageb_paths": ageb_paths,
        "corridor_paths": corridor_paths,
        "served": served_json,
        "stats": corridor_stats,
        "W": W, "H": H,
    }, f)

print("wrote corridor_map_data.json")
print("ageb path chars:", sum(len(d) for _, _, d in ageb_paths))
print("corridor path chars:", sum(len(d) for _, _, d in corridor_paths))
