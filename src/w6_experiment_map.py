"""
Render an interactive SVG map of the W6 *frontier* anchor-mode corridors, shaped by
the MST-diameter trunk shaper (corridor_trunk_diameter) so the geometry is a real
single road path -- no phantom straight jumps, no branch loops -- over the AGEB
coverage-gap choropleth.

Corridors are judged by the STANDARD W5 endpoint detour_ratio (cap 1.80), which is
trustworthy again now that endpoints are the true ends of a path (the earlier
MST-directness workaround is retired). Amber = feasible; dashed grey = infeasible
(too circuitous).

Self-contained HTML (inline SVG + CSS + JS, no external hosts) for publishing as a
Claude Artifact.

Run (venv active): python src/w6_experiment_map.py
Output: outputs/w6_experiment/frontier_corridor_map.html
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geopandas as gpd
import json
from shapely.geometry import LineString
from sqlalchemy import create_engine

from config import PG_URI
from src.w5_constraints import check_constraints
from src.w5_types import W5Config
from src.w5_objective import load_ageb_context
from src.w6_anchors import load_gap_agebs, load_gtfs_stops, network_connected_agebs
from src.w6_candidates import build_route_candidate
from src.w6_graph import corridor_trunk_diameter, load_or_download_osm, project_to_6372
from src.w6_anchor_experiment import build_anchor_terminals, CONNECT_M
from src.w8_corridor_merit import build_merit_baselines, score_corridor

OUT = Path(__file__).resolve().parent.parent / "outputs" / "w6_experiment" / "frontier_corridor_map.html"
METRO_HI = 20.7
DETOUR_CAP = 1.8


def main():
    eng = create_engine(PG_URI)
    cfg = W5Config()
    baselines = build_merit_baselines(eng)
    ageb = baselines.ageb  # geom, gap_category, coverage_gap_n, transit_demand, final_score

    gap = load_gap_agebs(eng)
    conn = network_connected_agebs(eng, radius_m=CONNECT_M)
    stops = load_gtfs_stops(eng)
    G = project_to_6372(load_or_download_osm())
    terminals, _ = build_anchor_terminals("frontier", gap, conn, stops, G)

    corridors = []  # (cid, geom_6372, stats dict, served_ids)
    for gid in sorted(terminals):
        geom, km = corridor_trunk_diameter(G, terminals[gid])
        if geom is None or km <= 0.01:
            continue
        cid = f"G{gid:02d}"
        rc = build_route_candidate(cid, geom, eng, config=cfg, route_km_override=km)
        if rc is None:
            continue
        ctxs = load_ageb_context(rc.served_ageb_ids, eng)
        cr = check_constraints(rc, ctxs, cfg)
        td = float(ageb.loc[ageb["cve_ageb"].isin(rc.served_ageb_ids), "transit_demand"].sum())
        merit = score_corridor(geom, km, td, baselines)
        detour = rc.route_km / rc.straight_line_km if rc.straight_line_km else float("inf")
        corridors.append((cid, geom, dict(
            route_km=km, n_served=len(rc.served_ageb_ids), total_demand=td,
            hi_share=merit["hi_share"], dpk_pct=merit["dpk_pct"], detour=detour,
            feasible=bool(cr.feasible)), sorted(rc.served_ageb_ids)))
    eng.dispose()

    # --- projection: EPSG:6372 metres -> SVG viewBox pixels ---
    minx, miny, maxx, maxy = ageb.total_bounds
    W = 900.0
    H = W * (maxy - miny) / (maxx - minx)
    scale = W / (maxx - minx)

    def to_xy(x, y):
        return ((x - minx) * scale, (maxy - y) * scale)

    def ring(coords):
        return "M" + " L".join(f"{to_xy(x, y)[0]:.1f},{to_xy(x, y)[1]:.1f}" for x, y in coords) + " Z"

    def poly_path(geom):
        parts = []
        for p in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
            parts.append(ring(p.exterior.coords))
            for it in p.interiors:
                parts.append(ring(it.coords))
        return " ".join(parts)

    def line_path(geom):
        pts = [to_xy(x, y) for x, y in geom.coords]
        return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)

    GAP_CLASS = {"High-gap": "gap-hi", "Medium-gap": "gap-med", "Low-gap": "gap-lo", None: "gap-med"}
    ageb_s = ageb.copy()
    ageb_s["geom"] = ageb_s.geometry.simplify(12, preserve_topology=True)
    ageb_svg = [f'<path class="ageb {GAP_CLASS.get(r.gap_category,"gap-med")}" data-a="{r.cve_ageb}" '
                f'd="{poly_path(r.geom)}"/>' for _, r in ageb_s.iterrows()]

    cor_svg, label_svg, cards = [], [], []
    served_map = {}
    n_feas = 0
    for cid, geom, s, served in corridors:
        served_map[cid] = served
        n_feas += s["feasible"]
        fclass = "feas" if s["feasible"] else "infeas"
        gsimpl = geom.simplify(5, preserve_topology=True)
        d = line_path(gsimpl)
        cor_svg.append(
            f'<g class="cor-g {fclass}" data-id="{cid}" tabindex="0" role="button" '
            f'aria-label="Corridor {cid}"><path class="cor-halo" d="{d}"/>'
            f'<path class="cor {fclass}" d="{d}"/></g>')
        mid = geom.interpolate(0.5, normalized=True)
        lx, ly = to_xy(mid.x, mid.y)
        label_svg.append(
            f'<g class="lbl {fclass}" data-id="{cid}"><circle cx="{lx:.0f}" cy="{ly:.0f}" r="10"/>'
            f'<text x="{lx:.0f}" y="{ly:.0f}" dy="3.5">{cid[1:]}</text></g>')
        hi = s["hi_share"] * 100
        badge = "Feasible" if s["feasible"] else "Too circuitous"
        cards.append(f"""
        <article class="card {fclass}" data-id="{cid}" tabindex="0" role="button" aria-label="Corridor {cid} details">
          <header><span class="dot"></span><h3>{cid}</h3><span class="badge">{badge}</span></header>
          <dl>
            <div><dt>Length</dt><dd>{s['route_km']:.1f} km</dd></div>
            <div><dt>AGEBs served</dt><dd>{s['n_served']}</dd></div>
            <div><dt>Total demand</dt><dd>{s['total_demand']:,.0f}<span class="u">/day</span></dd></div>
            <div><dt>High-gap share</dt><dd>{hi:.0f}%<span class="u">metro {METRO_HI:.0f}%</span></dd></div>
            <div><dt>Demand / km</dt><dd>{s['dpk_pct']:.0f}th<span class="u">pct vs routes</span></dd></div>
            <div><dt>Detour ratio</dt><dd class="det {fclass}">{s['detour']:.2f}<span class="u">cap {DETOUR_CAP:.2f}</span></dd></div>
          </dl>
        </article>""")

    html = _TEMPLATE.format(
        W=W, H=H, ageb="\n".join(ageb_svg), corridors="\n".join(cor_svg),
        labels="\n".join(label_svg), cards="\n".join(cards),
        served_json=json.dumps(served_map), n_feas=n_feas, n_total=len(corridors),
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"[OK] wrote {OUT}  ({len(html):,} bytes; {n_feas}/{len(corridors)} feasible "
          f"under standard endpoint detour, diameter-trunk shaper)")


_TEMPLATE = """<div id="app">
<style>
  :root {{
    --bg:#f5f6f8; --surface:#ffffff; --ink:#1a2230; --muted:#5d6b7e; --line:#dde2e9;
    --gap-lo:#e4ebf1; --gap-med:#9fb6cb; --gap-hi:#39597b; --gap-stroke:#ffffff;
    --feas:#e0891c; --feas-ink:#8a5109; --infeas:#8c96a4; --accent-soft:#fbe7c9;
  }}
  @media (prefers-color-scheme:dark) {{
    :root {{
      --bg:#0f1318; --surface:#171c23; --ink:#e7ecf3; --muted:#93a1b3; --line:#2a323d;
      --gap-lo:#222c35; --gap-med:#3f5a72; --gap-hi:#8fb6da; --gap-stroke:#0f1318;
      --feas:#f0a63e; --feas-ink:#f7c987; --infeas:#69727f; --accent-soft:#3a2c14;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg:#0f1318; --surface:#171c23; --ink:#e7ecf3; --muted:#93a1b3; --line:#2a323d;
    --gap-lo:#222c35; --gap-med:#3f5a72; --gap-hi:#8fb6da; --gap-stroke:#0f1318;
    --feas:#f0a63e; --feas-ink:#f7c987; --infeas:#69727f; --accent-soft:#3a2c14;
  }}
  :root[data-theme="light"] {{
    --bg:#f5f6f8; --surface:#ffffff; --ink:#1a2230; --muted:#5d6b7e; --line:#dde2e9;
    --gap-lo:#e4ebf1; --gap-med:#9fb6cb; --gap-hi:#39597b; --gap-stroke:#ffffff;
    --feas:#e0891c; --feas-ink:#8a5109; --infeas:#8c96a4; --accent-soft:#fbe7c9;
  }}
  * {{ box-sizing:border-box; }}
  #app {{
    background:var(--bg); color:var(--ink); padding:24px; min-height:100%;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    font-variant-numeric:tabular-nums; line-height:1.45;
  }}
  .head {{ max-width:1180px; margin:0 auto 18px; }}
  .eyebrow {{ text-transform:uppercase; letter-spacing:.09em; font-size:12px; font-weight:600;
    color:var(--feas-ink); margin:0 0 4px; }}
  h1 {{ margin:0 0 6px; font-size:26px; line-height:1.15; text-wrap:balance; }}
  .sub {{ margin:0; color:var(--muted); font-size:15px; max-width:72ch; }}
  .grid {{ display:grid; grid-template-columns:minmax(0,1.7fr) minmax(260px,1fr); gap:20px;
    max-width:1180px; margin:0 auto; align-items:start; }}
  @media (max-width:840px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .mapwrap {{ background:var(--surface); border:1px solid var(--line); border-radius:12px;
    padding:12px; overflow:hidden; }}
  svg {{ width:100%; height:auto; display:block; }}
  .ageb {{ stroke:var(--gap-stroke); stroke-width:.3; transition:opacity .12s; }}
  .gap-lo {{ fill:var(--gap-lo); }} .gap-med {{ fill:var(--gap-med); }} .gap-hi {{ fill:var(--gap-hi); }}
  .ageb.served {{ opacity:1; stroke:var(--feas); stroke-width:1.1; }}
  #map.dim .ageb:not(.served) {{ opacity:.45; }}
  .cor-halo {{ fill:none; stroke:var(--surface); stroke-width:6.5; stroke-linecap:round; stroke-linejoin:round; }}
  .cor {{ fill:none; stroke-width:3.2; stroke-linecap:round; stroke-linejoin:round; }}
  .cor.feas {{ stroke:var(--feas); }}
  .cor.infeas {{ stroke:var(--infeas); stroke-dasharray:2 5; stroke-width:2.6; }}
  .cor-g {{ cursor:pointer; outline:none; }}
  .cor-g.active .cor {{ stroke-width:5; }} .cor-g.active .cor-halo {{ stroke-width:9; }}
  .cor-g:focus-visible .cor {{ stroke-width:5; }}
  .lbl circle {{ fill:var(--feas); stroke:var(--surface); stroke-width:1.5; }}
  .lbl.infeas circle {{ fill:var(--infeas); }}
  .lbl text {{ fill:#fff; font-size:11px; font-weight:700; text-anchor:middle; pointer-events:none; }}
  .legend {{ display:flex; flex-wrap:wrap; gap:14px 18px; margin:12px 2px 0; font-size:12.5px; color:var(--muted); }}
  .legend span {{ display:inline-flex; align-items:center; gap:6px; }}
  .sw {{ width:14px; height:14px; border-radius:3px; border:1px solid var(--line); }}
  .ln {{ width:20px; height:0; border-top:3px solid var(--feas); border-radius:2px; }}
  .ln.d {{ border-top:2.5px dashed var(--infeas); }}
  aside {{ display:flex; flex-direction:column; gap:10px; }}
  .tally {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:14px 16px; }}
  .tally b {{ font-size:30px; color:var(--feas-ink); }}
  .tally p {{ margin:4px 0 0; color:var(--muted); font-size:13px; }}
  .card {{ background:var(--surface); border:1px solid var(--line); border-radius:12px;
    padding:12px 14px; cursor:pointer; transition:border-color .12s, box-shadow .12s; outline:none; }}
  .card:hover, .card.active, .card:focus-visible {{ border-color:var(--feas);
    box-shadow:0 0 0 3px var(--accent-soft); }}
  .card.infeas.active, .card.infeas:hover {{ border-color:var(--infeas); box-shadow:0 0 0 3px transparent; }}
  .card header {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }}
  .card h3 {{ margin:0; font-size:16px; }}
  .card .dot {{ width:11px; height:11px; border-radius:50%; background:var(--feas); }}
  .card.infeas .dot {{ background:var(--infeas); }}
  .badge {{ margin-left:auto; font-size:11px; font-weight:600; text-transform:uppercase;
    letter-spacing:.04em; padding:2px 8px; border-radius:20px; background:var(--accent-soft); color:var(--feas-ink); }}
  .card.infeas .badge {{ background:transparent; border:1px solid var(--line); color:var(--muted); }}
  dl {{ margin:0; display:grid; grid-template-columns:1fr 1fr; gap:7px 14px; }}
  dt {{ font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.03em; }}
  dd {{ margin:1px 0 0; font-size:15px; font-weight:600; }}
  dd .u {{ display:block; font-size:10.5px; font-weight:400; color:var(--muted); letter-spacing:.02em; }}
  dd.det.infeas {{ color:var(--infeas); }} dd.det.feas {{ color:var(--feas-ink); }}
  .foot {{ max-width:1180px; margin:16px auto 0; color:var(--muted); font-size:12px; }}
  @media (prefers-reduced-motion:reduce) {{ * {{ transition:none !important; }} }}
</style>

<div class="head">
  <p class="eyebrow">W6 corridor generation &middot; frontier anchors &middot; diameter-trunk shaper</p>
  <h1>Frontier corridors, honestly shaped</h1>
  <p class="sub">Each corridor is the longest leaf-to-leaf path of its anchors' spanning tree,
  stitched from real road segments &mdash; no phantom straight jumps, no branch loops. Judged by
  the standard end-to-end detour ratio (route length &divide; straight-line distance between the
  two ends, cap 1.80). Amber clears the cap; dashed grey is too circuitous. Hover a corridor to
  light up the AGEBs it serves.</p>
</div>

<div class="grid">
  <div class="mapwrap">
    <svg viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Map of frontier corridors over AGEB coverage-gap choropleth">
      <g id="map">
        <g id="agebs">{ageb}</g>
        <g id="cors">{corridors}</g>
        <g id="labels">{labels}</g>
      </g>
    </svg>
    <div class="legend">
      <span><i class="sw" style="background:var(--gap-hi)"></i>High gap</span>
      <span><i class="sw" style="background:var(--gap-med)"></i>Medium</span>
      <span><i class="sw" style="background:var(--gap-lo)"></i>Low gap</span>
      <span><i class="ln"></i>Feasible (detour &le; 1.80)</span>
      <span><i class="ln d"></i>Too circuitous</span>
    </div>
  </div>
  <aside>
    <div class="tally"><b>{n_feas} / {n_total}</b><p>feasible under the standard detour cap.
    With honest geometry only the short 2-anchor stub qualifies; the rest genuinely wander
    ~2&ndash;2.8&times; their end-to-end distance.</p></div>
    {cards}
  </aside>
</div>
<p class="foot">Choropleth: AGEB coverage-gap category (demand vs GTFS accessibility, W3).
Corridors: W6 frontier anchors shaped by the MST-diameter trunk (src/w6_graph.corridor_trunk_diameter).
Detour ratio = road length &divide; straight-line end-to-end distance. Generated by src/w6_experiment_map.py.</p>

<script>
(function() {{
  var served = {served_json};
  var map = document.getElementById('map');
  var agebs = {{}};
  document.querySelectorAll('.ageb').forEach(function(p) {{ agebs[p.getAttribute('data-a')] = p; }});
  function setActive(id, on) {{
    document.querySelectorAll('[data-id="'+id+'"]').forEach(function(el) {{ el.classList.toggle('active', on); }});
    if (on) {{
      map.classList.add('dim');
      (served[id]||[]).forEach(function(a) {{ if (agebs[a]) agebs[a].classList.add('served'); }});
    }} else {{
      map.classList.remove('dim');
      document.querySelectorAll('.ageb.served').forEach(function(p) {{ p.classList.remove('served'); }});
    }}
  }}
  document.querySelectorAll('.cor-g, .card').forEach(function(el) {{
    var id = el.getAttribute('data-id');
    el.addEventListener('mouseenter', function() {{ setActive(id, true); }});
    el.addEventListener('mouseleave', function() {{ setActive(id, false); }});
    el.addEventListener('focus', function() {{ setActive(id, true); }});
    el.addEventListener('blur', function() {{ setActive(id, false); }});
  }});
}})();
</script>
</div>"""


if __name__ == "__main__":
    main()
