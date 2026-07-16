"""
Render an interactive SVG map of the W6 *frontier* anchor-mode corridors over the
AGEB coverage-gap choropleth, styled by feasibility under the prototype MST-aware
directness metric (see scratchpad w6_mst_directness.py / directness.json).

Self-contained HTML (inline SVG + CSS + JS, no external hosts) so it can be
published as a Claude Artifact. Reuses the projection approach from
w8_corridor_map_data.py.

Run (venv active): python src/w6_experiment_map.py
Output: outputs/w6_experiment/frontier_corridor_map.html
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine

from config import PG_URI

EXP = Path(__file__).resolve().parent.parent / "outputs" / "w6_experiment" / "frontier"
OUT = Path(__file__).resolve().parent.parent / "outputs" / "w6_experiment" / "frontier_corridor_map.html"
METRO_HI = 20.7  # metro-wide High-gap share (%), the need baseline
BUFFER_M = 400.0


def main():
    eng = create_engine(PG_URI)
    ageb = gpd.read_postgis(
        """
        SELECT a.cvegeo AS cve_ageb, a.geom, cg.gap_category
        FROM base.ageb a
        LEFT JOIN features.ageb_coverage_gap cg ON cg.cve_ageb = a.cvegeo
        """,
        eng, geom_col="geom",
    )
    eng.dispose()

    corridors = gpd.read_file(EXP / "corridor_candidates.geojson").to_crs(ageb.crs)
    scores = pd.read_csv(EXP / "corridor_scores.csv").set_index("candidate_id")
    directness = json.loads((EXP / "directness.json").read_text())

    # --- served-AGEB sets per corridor (for hover highlight) ---
    centroids = ageb.geometry.centroid
    served = {}
    for _, c in corridors.iterrows():
        buf = c.geometry.buffer(BUFFER_M)
        hit = centroids.within(buf)
        served[c.candidate_id] = sorted(ageb.loc[hit, "cve_ageb"])

    # --- projection: EPSG:6372 metres -> SVG viewBox pixels ---
    minx, miny, maxx, maxy = ageb.total_bounds
    W = 900.0
    H = W * (maxy - miny) / (maxx - minx)
    scale = W / (maxx - minx)

    def to_xy(x, y):
        return ((x - minx) * scale, (maxy - y) * scale)  # flip y

    def ring(coords):
        pts = [to_xy(x, y) for x, y in coords]
        return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + " Z"

    def poly_path(geom):
        parts = []
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for p in polys:
            parts.append(ring(p.exterior.coords))
            for it in p.interiors:
                parts.append(ring(it.coords))
        return " ".join(parts)

    def line_path(geom):
        lines = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
        parts = []
        for ln in lines:
            pts = [to_xy(x, y) for x, y in ln.coords]
            parts.append("M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts))
        return " ".join(parts)

    GAP_CLASS = {"High-gap": "gap-hi", "Medium-gap": "gap-med",
                 "Low-gap": "gap-lo", None: "gap-med"}

    ageb_s = ageb.copy()
    ageb_s["geom"] = ageb_s.geometry.simplify(12, preserve_topology=True)
    ageb_svg = []
    for _, r in ageb_s.iterrows():
        cls = GAP_CLASS.get(r.gap_category, "gap-med")
        ageb_svg.append(f'<path class="ageb {cls}" data-a="{r.cve_ageb}" d="{poly_path(r.geom)}"/>')

    cor_s = corridors.copy()
    cor_s["geom"] = cor_s.geometry.simplify(5, preserve_topology=True)
    cor_svg, cards, label_svg = [], [], []
    order = sorted(cor_s["candidate_id"])
    for cid in order:
        row = cor_s[cor_s["candidate_id"] == cid].iloc[0]
        d = line_path(row.geom)
        dj = directness[cid]
        feas = dj["new_feasible"]
        fclass = "feas" if feas else "infeas"
        cor_svg.append(
            f'<g class="cor-g {fclass}" data-id="{cid}" tabindex="0" role="button" '
            f'aria-label="Corridor {cid}">'
            f'<path class="cor-halo" d="{d}"/><path class="cor {fclass}" d="{d}"/></g>'
        )
        # label at corridor midpoint
        mid = row.geometry.interpolate(0.5, normalized=True)
        lx, ly = to_xy(mid.x, mid.y)
        short = cid.replace("frontier_", "")
        label_svg.append(
            f'<g class="lbl {fclass}" data-id="{cid}"><circle cx="{lx:.0f}" cy="{ly:.0f}" r="10"/>'
            f'<text x="{lx:.0f}" y="{ly:.0f}" dy="3.5">{short[1:]}</text></g>'
        )
        s = scores.loc[cid]
        hi = float(s["hi_share"]) * 100
        badge = ("Feasible" if feas else "Infeasible")
        cards.append(f"""
        <article class="card {fclass}" data-id="{cid}" tabindex="0" role="button" aria-label="Corridor {cid} details">
          <header><span class="dot"></span><h3>{short}</h3><span class="badge">{badge}</span></header>
          <dl>
            <div><dt>Length</dt><dd>{float(s['route_km']):.1f} km</dd></div>
            <div><dt>AGEBs served</dt><dd>{int(s['n_served_agebs'])}</dd></div>
            <div><dt>Total demand</dt><dd>{float(s['total_demand']):,.0f}<span class="u">/day</span></dd></div>
            <div><dt>High-gap share</dt><dd>{hi:.0f}%<span class="u">metro {METRO_HI:.0f}%</span></dd></div>
            <div><dt>Demand / km</dt><dd>{float(s['dpk_pct']):.0f}th<span class="u">pct vs routes</span></dd></div>
            <div class="span"><dt>Circuitry</dt><dd class="circ"><span class="old">{dj['old_detour']:.2f}</span><span class="arr">&rarr;</span><span class="new">{dj['new_directness']:.2f}</span><span class="u">endpoint &rarr; MST directness (cap 1.80)</span></dd></div>
          </dl>
        </article>""")

    n_feas = sum(1 for cid in order if directness[cid]["new_feasible"])
    served_json = json.dumps(served)
    html = _TEMPLATE.format(
        W=W, H=H, ageb="\n".join(ageb_svg), corridors="\n".join(cor_svg),
        labels="\n".join(label_svg), cards="\n".join(cards),
        served_json=served_json, n_feas=n_feas, n_total=len(order),
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"[OK] wrote {OUT}  ({len(html):,} bytes; {n_feas}/{len(order)} feasible under MST directness)")


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
  .sub {{ margin:0; color:var(--muted); font-size:15px; max-width:70ch; }}
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
  .tally p {{ margin:2px 0 0; color:var(--muted); font-size:13px; }}
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
  dl .span {{ grid-column:1 / -1; }}
  dt {{ font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.03em; }}
  dd {{ margin:1px 0 0; font-size:15px; font-weight:600; }}
  dd .u {{ display:block; font-size:10.5px; font-weight:400; color:var(--muted); letter-spacing:.02em; }}
  .circ {{ display:flex; align-items:baseline; gap:7px; flex-wrap:wrap; }}
  .circ .old {{ color:var(--muted); text-decoration:line-through; }}
  .circ .arr {{ color:var(--muted); }} .circ .new {{ color:var(--feas-ink); }}
  .circ .u {{ flex-basis:100%; }}
  .foot {{ max-width:1180px; margin:16px auto 0; color:var(--muted); font-size:12px; }}
  @media (prefers-reduced-motion:reduce) {{ * {{ transition:none !important; }} }}
</style>

<div class="head">
  <p class="eyebrow">W6 corridor generation &middot; frontier anchor mode</p>
  <h1>Frontier corridors on the coverage-gap surface</h1>
  <p class="sub">Anchors restricted to the served/unserved seam, then re-judged with an
  MST-aware directness metric instead of endpoint detour. Amber corridors clear the 1.80
  circuitry cap; dashed grey does not. Hover a corridor to light up the AGEBs it serves.</p>
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
      <span><i class="ln"></i>Feasible (MST directness)</span>
      <span><i class="ln d"></i>Still infeasible</span>
    </div>
  </div>
  <aside>
    <div class="tally"><b>{n_feas} / {n_total}</b><p>feasible under MST-aware directness
    (was 1 / {n_total} under endpoint detour)</p></div>
    {cards}
  </aside>
</div>
<p class="foot">Choropleth: AGEB coverage-gap category (demand vs GTFS accessibility, W3).
Corridors: W6 frontier anchor mode. Circuitry = route length &divide; straight-line spanning
length of the corridor's anchors; the old endpoint-detour metric inflated branching corridors.
Generated by src/w6_experiment_map.py.</p>

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
