"""
W9 corridor-proposal map (self-contained HTML, no external deps)
================================================================
Renders an interactive inline-SVG map of the W6 corridor proposals for the
transfer cities (Toluca + Aguascalientes) over their AGEB coverage-gap
choropleth, with a city toggle and per-corridor stat cards. Mirrors the ZMG
w8_corridor_map approach but file-based (reads outputs/w9/*), for any city.

Output: outputs/w9/w9_corridor_map.html  (publishable as a Claude Artifact)

Usage:
    python src/w9_corridor_map.py
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from src.w9_run_tier1 import load_city_config, resolve_paths, _first_existing

OUT = ROOT / "outputs" / "w9"
CRS = "EPSG:6372"
TARGET_W = 820.0
SIMPLIFY_M = 25.0          # AGEB polygon simplification tolerance (metres)
CORRIDOR_COLORS = ["#2563eb", "#0891b2", "#7c3aed", "#059669", "#db2777"]
GAP_CLASS = {"High-gap": "hi", "Medium-gap": "md", "Low-gap": "lo"}


def _ageb_gdf(cfg, paths):
    gap = pd.read_csv(OUT / f"{cfg.CITY_KEY}_coverage_gap.csv", dtype={"cve_ageb": str})
    shp = gpd.read_file(_first_existing(paths["shp"])).to_crs(CRS)
    shp["cve_ageb"] = (shp["CVEGEO"].astype(str).str.strip() if "CVEGEO" in shp.columns
                       else (shp["CVE_ENT"].astype(str).str.zfill(2) + shp["CVE_MUN"].astype(str).str.zfill(3)
                             + shp["CVE_LOC"].astype(str).str.zfill(4) + shp["CVE_AGEB"].astype(str).str.zfill(4)))
    g = shp.merge(gap[["cve_ageb", "gap_category", "coverage_gap_n"]], on="cve_ageb", how="inner")
    g["geometry"] = g.geometry.simplify(SIMPLIFY_M, preserve_topology=True)
    return g


def _ring_d(coords, proj):
    pts = [proj(x, y) for x, y in coords]
    if len(pts) < 3:
        return ""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    d += "".join(f"L{x:.1f},{y:.1f}" for x, y in pts[1:])
    return d + "Z"


def _poly_paths(geom, proj):
    out = []
    if geom.geom_type == "Polygon":
        polys = [geom]
    elif geom.geom_type == "MultiPolygon":
        polys = list(geom.geoms)
    else:
        return out
    for p in polys:
        d = _ring_d(list(p.exterior.coords), proj)
        if d:
            out.append(d)
    return out


def _line_d(geom, proj):
    lines = [geom] if geom.geom_type == "LineString" else list(geom.geoms)
    parts = []
    for ln in lines:
        pts = [proj(x, y) for x, y in ln.coords]
        if len(pts) < 2:
            continue
        parts.append(f"M{pts[0][0]:.1f},{pts[0][1]:.1f}" + "".join(f"L{x:.1f},{y:.1f}" for x, y in pts[1:]))
    return " ".join(parts)


def build_city(key: str) -> dict:
    cfg = load_city_config(key)
    paths = resolve_paths(cfg)
    ageb = _ageb_gdf(cfg, paths)
    corr = gpd.read_file(OUT / f"{key}_corridor_candidates.geojson").to_crs(CRS)

    # Frame on the CORRIDORS (the proposals), padded -- ZM Toluca/Aguascalientes
    # span 100km/46km incl. semi-rural municipios, so a full-extent view buries the
    # corridors in empty map. Far AGEBs are still drawn but clip to the SVG viewport.
    cminx, cminy, cmaxx, cmaxy = corr.total_bounds
    pad = max(0.35 * max(cmaxx - cminx, cmaxy - cminy), 3000.0)
    minx, miny, maxx, maxy = cminx - pad, cminy - pad, cmaxx + pad, cmaxy + pad
    scale = TARGET_W / (maxx - minx)
    H = (maxy - miny) * scale

    def proj(x, y):
        return ((x - minx) * scale, (maxy - y) * scale)

    ageb_paths = []
    for _, r in ageb.iterrows():
        cls = GAP_CLASS.get(r["gap_category"], "md")
        for d in _poly_paths(r.geometry, proj):
            ageb_paths.append([r["cve_ageb"], cls, d])

    # served AGEBs per feasible corridor (centroid within 400m)
    cents = gpd.GeoDataFrame(ageb[["cve_ageb"]].copy(), geometry=ageb.geometry.centroid, crs=CRS)

    corridors, stats = [], {}
    ci = 0
    for _, r in corr.sort_values(["feasible", "total_demand"], ascending=[False, False]).iterrows():
        cid = str(r["candidate_id"])
        is_feas = bool(r["feasible"])
        color = CORRIDOR_COLORS[ci % len(CORRIDOR_COLORS)] if is_feas else "#94a3b8"
        if is_feas:
            ci += 1
        served = set(cents.loc[cents.geometry.within(r.geometry.buffer(400.0)), "cve_ageb"]) if is_feas else set()
        corridors.append({"id": cid, "feasible": is_feas, "color": color,
                          "d": _line_d(r.geometry, proj), "served": sorted(served)})
        stats[cid] = {
            "route_km": float(r["route_km"]), "n_served": int(r["n_served_agebs"]),
            "demand": float(r["total_demand"]), "directness": float(r["directness"]),
            "mode": str(r["mode_assignment"]), "feasible": is_feas, "color": color,
        }

    hi = int((ageb["gap_category"] == "High-gap").sum())
    return {
        "name": cfg.CITY_NAME, "W": round(TARGET_W, 1), "H": round(H, 1),
        "n_agebs": len(ageb), "hi_pct": round(hi / len(ageb) * 100, 1),
        "n_feas": int(corr["feasible"].fillna(False).sum()),
        "ageb_paths": ageb_paths, "corridors": corridors, "stats": stats,
    }


def render(cities: dict) -> str:
    data_json = json.dumps(cities, separators=(",", ":"))
    return _TEMPLATE.replace("/*__DATA__*/", data_json)


_TEMPLATE = r"""<title>W9 Corridor Proposals — Toluca &amp; Aguascalientes</title>
<div id="app">
<style>
  :root{
    --bg:#eef2f3; --surface:#ffffff; --ink:#0e1a20; --muted:#5c6f79; --line:#d3dde1;
    --hi:#d7301f; --md:#fdbb84; --lo:#fdece0; --ageb-stroke:#ffffff;
    --accent:#0f766e; --card:#ffffff; --shadow:0 1px 2px rgba(16,32,40,.06),0 4px 16px rgba(16,32,40,.06);
  }
  @media (prefers-color-scheme:dark){:root{
    --bg:#0b1418; --surface:#101c22; --ink:#e7eff3; --muted:#8fa3ad; --line:#1e2f37;
    --hi:#f4512c; --md:#e0965a; --lo:#3a2a24; --ageb-stroke:#0b1418;
    --card:#101c22; --accent:#4fd1c5; --shadow:0 1px 2px rgba(0,0,0,.4),0 6px 20px rgba(0,0,0,.35);
  }}
  :root[data-theme="light"]{--bg:#eef2f3;--surface:#ffffff;--ink:#0e1a20;--muted:#5c6f79;--line:#d3dde1;--hi:#d7301f;--md:#fdbb84;--lo:#fdece0;--ageb-stroke:#ffffff;--accent:#0f766e;--card:#ffffff;}
  :root[data-theme="dark"]{--bg:#0b1418;--surface:#101c22;--ink:#e7eff3;--muted:#8fa3ad;--line:#1e2f37;--hi:#f4512c;--md:#e0965a;--lo:#3a2a24;--ageb-stroke:#0b1418;--accent:#4fd1c5;--card:#101c22;}
  #app{background:var(--bg);color:var(--ink);font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
    line-height:1.5;padding:clamp(16px,3vw,32px);min-height:100%;}
  #app *{box-sizing:border-box;}
  .wrap{max-width:1180px;margin:0 auto;}
  header.top{margin-bottom:18px;}
  .eyebrow{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:var(--accent);font-weight:600;}
  h1{font-size:clamp(22px,3.2vw,30px);margin:.15em 0 .1em;text-wrap:balance;font-weight:700;letter-spacing:-.01em;}
  .sub{color:var(--muted);max-width:60ch;font-size:15px;}
  .toggle{display:inline-flex;gap:4px;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:4px;margin:16px 0 8px;}
  .toggle button{appearance:none;border:0;background:transparent;color:var(--muted);font:inherit;font-weight:600;
    padding:8px 16px;border-radius:7px;cursor:pointer;transition:.15s;}
  .toggle button[aria-selected="true"]{background:var(--accent);color:#fff;}
  .toggle button:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
  .layout{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(260px,1fr);gap:20px;align-items:start;}
  @media (max-width:860px){.layout{grid-template-columns:1fr;}}
  .mapcard{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px;box-shadow:var(--shadow);}
  svg{width:100%;height:auto;display:block;border-radius:8px;overflow:hidden;background:var(--surface);}
  .ageb{stroke:var(--ageb-stroke);stroke-width:.4;}
  .ageb.hi{fill:var(--hi);} .ageb.md{fill:var(--md);} .ageb.lo{fill:var(--lo);}
  .ageb.served{stroke:var(--ink);stroke-width:1.1;}
  .corridor-halo{fill:none;stroke:var(--surface);stroke-width:7;stroke-linecap:round;stroke-linejoin:round;opacity:.9;}
  .corridor{fill:none;stroke-width:3.4;stroke-linecap:round;stroke-linejoin:round;transition:stroke-width .12s;}
  .corridor.infeas{stroke-width:2;stroke-dasharray:3 5;opacity:.65;}
  .corridor-group{cursor:pointer;} .corridor-group.dim{opacity:.28;}
  .corridor-group.active .corridor{stroke-width:6;}
  .legend{display:flex;flex-wrap:wrap;gap:12px 18px;margin-top:10px;font-size:12.5px;color:var(--muted);}
  .legend .k{display:inline-flex;align-items:center;gap:6px;}
  .sw{width:14px;height:14px;border-radius:3px;display:inline-block;border:1px solid rgba(0,0,0,.12);}
  .sw.line{width:18px;height:0;border:0;border-top:3px solid;border-radius:2px;}
  .panel{display:flex;flex-direction:column;gap:12px;}
  .summary{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow);}
  .summary .big{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums;}
  .summary .row{display:flex;justify-content:space-between;gap:10px;font-size:13px;color:var(--muted);margin-top:4px;}
  .summary .row b{color:var(--ink);font-variant-numeric:tabular-nums;font-weight:600;}
  .card{background:var(--card);border:1px solid var(--line);border-left-width:4px;border-radius:12px;padding:12px 14px;
    box-shadow:var(--shadow);cursor:pointer;transition:transform .12s,box-shadow .12s;}
  .card:hover,.card.active{transform:translateY(-1px);}
  .card:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
  .card h3{margin:0;font-size:15px;display:flex;align-items:center;gap:8px;justify-content:space-between;}
  .badge{font-size:10.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:2px 7px;border-radius:999px;
    background:var(--accent);color:#fff;white-space:nowrap;}
  .badge.rej{background:transparent;color:var(--muted);border:1px solid var(--line);}
  .metrics{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;margin-top:9px;}
  .metrics div{display:flex;flex-direction:column;}
  .metrics dt{font-size:10.5px;letter-spacing:.03em;text-transform:uppercase;color:var(--muted);}
  .metrics dd{margin:0;font-size:15px;font-weight:650;font-variant-numeric:tabular-nums;}
  .foot{color:var(--muted);font-size:12px;margin-top:16px;max-width:75ch;}
  .foot code{background:var(--surface);padding:1px 5px;border-radius:4px;border:1px solid var(--line);}
</style>

<div class="wrap">
  <header class="top">
    <div class="eyebrow">W9 transferability &middot; demand-driven corridor generation</div>
    <h1>Proposed transit corridors over the coverage-gap map</h1>
    <p class="sub">W6 candidate corridors for two transfer metros, drawn over each AGEB's transit
      demand&ndash;supply gap. Hover a corridor card to trace its alignment and the AGEBs it would serve.</p>
    <div class="toggle" role="tablist" aria-label="City">
      <button role="tab" data-city="tol" aria-selected="true">Toluca &mdash; large metro</button>
      <button role="tab" data-city="ags" aria-selected="false">Aguascalientes &mdash; compact</button>
    </div>
  </header>

  <div class="layout">
    <div class="mapcard">
      <svg id="map" role="img" aria-label="Coverage-gap choropleth with proposed corridors"></svg>
      <div class="legend">
        <span class="k"><span class="sw" style="background:var(--hi)"></span>High gap</span>
        <span class="k"><span class="sw" style="background:var(--md)"></span>Medium gap</span>
        <span class="k"><span class="sw" style="background:var(--lo)"></span>Low gap</span>
        <span class="k"><span class="sw line" style="border-color:#2563eb"></span>Proposed (feasible)</span>
        <span class="k"><span class="sw line" style="border-color:#94a3b8;border-top-style:dashed"></span>Generated, rejected on directness</span>
      </div>
    </div>
    <div class="panel" id="panel"></div>
  </div>

  <p class="foot">High gap = top-2 demand quintile &cap; bottom-2 accessibility quintile. Corridors from the
    re-architected W6 generator (frontier anchors &rarr; MST-diameter trunk &rarr; anchor-directness gate, cap 1.8).
    Source: <code>outputs/w9/{key}_corridor_candidates.geojson</code>. Demand = modeled transit trips/day.</p>
</div>

<script>
const DATA = /*__DATA__*/;
const map = document.getElementById('map');
const panel = document.getElementById('panel');
let cur = 'tol';

function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function fmt(n){return Math.round(n).toLocaleString('en-US');}

function draw(key){
  cur = key;
  const c = DATA[key];
  map.setAttribute('viewBox', `-8 -8 ${c.W+16} ${c.H+16}`);
  let s = '<g>';
  for(const [cve,cls,d] of c.ageb_paths) s += `<path class="ageb ${cls}" data-a="${cve}" d="${d}"/>`;
  s += '</g><g>';
  for(const co of c.corridors){
    const cls = co.feasible ? 'corridor' : 'corridor infeas';
    s += `<g class="corridor-group" data-id="${co.id}" tabindex="0" role="button" aria-label="Corridor ${co.id}">`
       + (co.feasible ? `<path class="corridor-halo" d="${co.d}"/>` : '')
       + `<path class="${cls}" style="stroke:${co.color}" d="${co.d}"/></g>`;
  }
  s += '</g>';
  map.innerHTML = s;

  // summary + cards
  let html = `<div class="summary"><div class="big">${c.n_feas} feasible</div>`
    + `<div class="row"><span>Corridors generated</span><b>${c.corridors.length}</b></div>`
    + `<div class="row"><span>AGEBs mapped</span><b>${fmt(c.n_agebs)}</b></div>`
    + `<div class="row"><span>High-gap share</span><b>${c.hi_pct}%</b></div></div>`;
  for(const co of c.corridors){
    const st = c.stats[co.id];
    const badge = st.feasible ? `<span class="badge" style="background:${co.color}">${esc(st.mode)}</span>`
                              : `<span class="badge rej">rejected</span>`;
    html += `<article class="card" data-id="${co.id}" tabindex="0" role="button"
        style="border-left-color:${co.color}" aria-label="${co.id} details">
      <h3><span>${co.id}</span>${badge}</h3>
      <dl class="metrics">
        <div><dt>Length</dt><dd>${st.route_km.toFixed(1)} km</dd></div>
        <div><dt>AGEBs served</dt><dd>${st.n_served}</dd></div>
        <div><dt>Demand / day</dt><dd>${fmt(st.demand)}</dd></div>
        <div><dt>Directness</dt><dd>${st.directness.toFixed(2)}${st.feasible?'':' &gt;1.8'}</dd></div>
      </dl></article>`;
  }
  panel.innerHTML = html;
  wire(c);
}

function wire(c){
  const groups = [...map.querySelectorAll('.corridor-group')];
  const cards = [...panel.querySelectorAll('.card')];
  const servedMap = Object.fromEntries(c.corridors.map(co=>[co.id, new Set(co.served)]));
  function focus(id){
    groups.forEach(g=>{const on=g.dataset.id===id;g.classList.toggle('active',on);g.classList.toggle('dim',id&&!on);});
    cards.forEach(cd=>cd.classList.toggle('active',cd.dataset.id===id));
    const set = id?servedMap[id]:null;
    map.querySelectorAll('.ageb').forEach(p=>p.classList.toggle('served',!!set&&set.has(p.dataset.a)));
  }
  function clear(){focus(null);}
  groups.forEach(g=>{g.onmouseenter=()=>focus(g.dataset.id);g.onmouseleave=clear;g.onfocus=()=>focus(g.dataset.id);g.onblur=clear;});
  cards.forEach(cd=>{cd.onmouseenter=()=>focus(cd.dataset.id);cd.onmouseleave=clear;cd.onfocus=()=>focus(cd.dataset.id);cd.onblur=clear;});
}

document.querySelectorAll('.toggle button').forEach(b=>{
  b.onclick=()=>{
    document.querySelectorAll('.toggle button').forEach(x=>x.setAttribute('aria-selected', x===b));
    draw(b.dataset.city);
  };
});
draw('tol');
</script>
</div>"""


def main():
    cities = {"tol": build_city("tol"), "ags": build_city("ags")}
    html = render(cities)
    out = OUT / "w9_corridor_map.html"
    out.write_text(html, encoding="utf-8")
    kb = len(html.encode()) / 1024
    print(f"[OK] {out}  ({kb:.0f} KB)")
    for k, c in cities.items():
        print(f"  {c['name']}: {c['n_agebs']} AGEBs, {len(c['corridors'])} corridors, {c['n_feas']} feasible")


if __name__ == "__main__":
    main()
