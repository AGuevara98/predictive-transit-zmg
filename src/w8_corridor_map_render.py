import json
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "w8"

with open(OUT_DIR / "corridor_map_data.json") as f:
    data = json.load(f)

W, H = data["W"], data["H"]
PAD = 16
VBW, VBH = W + PAD * 2, H + PAD * 2

ageb_svg = []
for cve, cls, d in data["ageb_paths"]:
    ageb_svg.append(f'<path class="ageb {cls}" data-ageb="{cve}" d="{d}" transform="translate({PAD},{PAD})"/>')

CORRIDOR_LABEL = {"W6_G00": "G00 (red)", "W6_G03": "G03 (green)", "W6_G05": "G05 (violet)"}
CORRIDOR_SHORT = {"W6_G00": "G00", "W6_G03": "G03", "W6_G05": "G05"}

corridor_svg = []
for cid, cls, d in data["corridor_paths"]:
    corridor_svg.append(
        f'<g class="corridor-group" data-id="{cid}" tabindex="0" role="button" '
        f'aria-label="Corridor {cid}">'
        f'<path class="corridor-halo" d="{d}" transform="translate({PAD},{PAD})"/>'
        f'<path class="corridor {cls}" data-id="{cid}" d="{d}" transform="translate({PAD},{PAD})"/>'
        f'</g>'
    )

ageb_svg_str = "\n".join(ageb_svg)
corridor_svg_str = "\n".join(corridor_svg)

stats = data["stats"]
served = data["served"]

def fmt(n):
    return f"{n:,.0f}"

def pct(n):
    return f"{n:.0f}%"

card_html = []
for cid in ["W6_G00", "W6_G03", "W6_G05"]:
    s = stats[cid]
    card_html.append(f"""
      <article class="stat-card" data-id="{cid}" tabindex="0" role="button" aria-label="Corridor {cid} details">
        <header>
          <span class="swatch {cid.lower().replace('w6_','c-')}"></span>
          <h3>{cid}</h3>
          <span class="mode-badge">{s['mode']}</span>
        </header>
        <dl>
          <div><dt>Route length</dt><dd>{s['route_km']:.1f} km</dd></div>
          <div><dt>AGEBs served</dt><dd>{s['n_served']}</dd></div>
          <div><dt>High-gap share</dt><dd>{pct(s['hi_share']*100)} <span class="muted">(metro {pct(20.7)})</span></dd></div>
          <div><dt>Demand / km</dt><dd>{fmt(s['dpk'])} <span class="muted">({s['pct']:.0f}th pct. of existing routes)</span></dd></div>
          <div><dt>Redundancy</dt><dd>{s['best_j']:.2f} Jaccard <span class="muted">vs {s['best_route'] or 'no route'}</span></dd></div>
        </dl>
      </article>""")
card_html_str = "\n".join(card_html)

table_rows = []
for cid in ["W6_G00", "W6_G03", "W6_G05"]:
    s = stats[cid]
    table_rows.append(
        f"<tr><td>{cid}</td><td>{s['mode']}</td><td>{s['route_km']:.1f}</td>"
        f"<td>{s['n_served']}</td><td>{pct(s['hi_share']*100)}</td>"
        f"<td>{fmt(s['demand_med'])}</td><td>{fmt(s['dpk'])}</td>"
        f"<td>{s['best_j']:.2f} ({s['best_route'] or '—'})</td></tr>"
    )
table_rows_str = "\n".join(table_rows)

served_json_str = json.dumps(served)

html = f"""<title>W6 Feasible Corridors — Question B</title>
<style>
  .viz-root {{
    --surface-1: #fcfcfb; --page: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --muted: #898781; --hairline: #e1e0d9;
    --gap-lo: #86b6ef; --gap-med: #3987e5; --gap-hi: #1c5cab;
    --c-g00: #e34948; --c-g03: #008300; --c-g05: #4a3aa7;
    --border: rgba(11,11,11,0.10);
  }}
  @media (prefers-color-scheme: dark) {{
    .viz-root {{
      --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #ffffff;
      --text-secondary: #c3c2b7; --muted: #898781; --hairline: #2c2c2a;
      --gap-lo: #184f95; --gap-med: #2a78d6; --gap-hi: #6da7ec;
      --c-g00: #e66767; --c-g03: #008300; --c-g05: #9085e9;
      --border: rgba(255,255,255,0.10);
    }}
  }}
  :root[data-theme="dark"] .viz-root {{
    --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #ffffff;
    --text-secondary: #c3c2b7; --muted: #898781; --hairline: #2c2c2a;
    --gap-lo: #184f95; --gap-med: #2a78d6; --gap-hi: #6da7ec;
    --c-g00: #e66767; --c-g03: #008300; --c-g05: #9085e9;
    --border: rgba(255,255,255,0.10);
  }}
  :root[data-theme="light"] .viz-root {{
    --surface-1: #fcfcfb; --page: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --muted: #898781; --hairline: #e1e0d9;
    --gap-lo: #86b6ef; --gap-med: #3987e5; --gap-hi: #1c5cab;
    --c-g00: #e34948; --c-g03: #008300; --c-g05: #4a3aa7;
    --border: rgba(11,11,11,0.10);
  }}

  * {{ box-sizing: border-box; }}
  body {{ margin: 0; }}
  .viz-root {{
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: var(--page); color: var(--text-primary);
    padding: 24px; max-width: 1180px; margin: 0 auto;
  }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .subtitle {{ color: var(--text-secondary); font-size: 14px; margin: 0 0 20px; max-width: 760px; }}

  .layout {{ display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start; }}
  .map-panel {{
    background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px;
    padding: 12px; flex: 1 1 520px; min-width: 320px;
  }}
  svg {{ width: 100%; height: auto; display: block; }}

  path.ageb {{ stroke: var(--surface-1); stroke-width: 0.4; transition: opacity .15s; }}
  path.ageb.gap-lo {{ fill: var(--gap-lo); }}
  path.ageb.gap-med {{ fill: var(--gap-med); }}
  path.ageb.gap-hi {{ fill: var(--gap-hi); }}
  path.ageb.dim {{ opacity: 0.25; }}
  path.ageb.served-highlight {{ stroke: var(--text-primary); stroke-width: 1.6; opacity: 1; }}

  .corridor-group {{ cursor: pointer; outline: none; }}
  path.corridor-halo {{ fill: none; stroke: var(--surface-1); stroke-width: 6.5; stroke-linecap: round; opacity: 0.9; }}
  path.corridor {{ fill: none; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }}
  path.corridor.c-g00 {{ stroke: var(--c-g00); }}
  path.corridor.c-g03 {{ stroke: var(--c-g03); }}
  path.corridor.c-g05 {{ stroke: var(--c-g05); }}
  .corridor-group.inactive path.corridor {{ opacity: 0.25; }}
  .corridor-group.inactive path.corridor-halo {{ opacity: 0.2; }}
  .corridor-group:hover path.corridor, .corridor-group:focus-visible path.corridor {{ stroke-width: 6; }}
  .corridor-group:focus-visible path.corridor-halo {{ stroke: var(--text-primary); opacity: 0.4; }}

  .legend {{ display: flex; flex-wrap: wrap; gap: 16px; margin-top: 12px; font-size: 12px; color: var(--text-secondary); }}
  .legend-group {{ display: flex; align-items: center; gap: 10px; }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; }}
  .legend-swatch {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}
  .legend-line {{ width: 16px; height: 3px; border-radius: 2px; display: inline-block; }}

  .side-panel {{ flex: 1 1 340px; min-width: 300px; display: flex; flex-direction: column; gap: 12px; }}
  .stat-card {{
    background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px;
    padding: 12px 14px; cursor: pointer; transition: border-color .15s, opacity .15s;
  }}
  .stat-card.inactive {{ opacity: 0.45; }}
  .stat-card.active {{ border-color: var(--text-primary); }}
  .stat-card header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }}
  .stat-card h3 {{ font-size: 14px; margin: 0; font-weight: 600; }}
  .mode-badge {{
    margin-left: auto; font-size: 10px; text-transform: uppercase; letter-spacing: .04em;
    color: var(--text-secondary); border: 1px solid var(--border); border-radius: 4px; padding: 2px 6px;
  }}
  .swatch {{ width: 10px; height: 10px; border-radius: 50%; flex: none; }}
  .swatch.c-g00 {{ background: var(--c-g00); }}
  .swatch.c-g03 {{ background: var(--c-g03); }}
  .swatch.c-g05 {{ background: var(--c-g05); }}
  .stat-card dl {{ margin: 0; display: grid; gap: 5px; }}
  .stat-card dl > div {{ display: flex; justify-content: space-between; gap: 12px; font-size: 12.5px; }}
  .stat-card dt {{ color: var(--text-secondary); }}
  .stat-card dd {{ margin: 0; font-weight: 600; text-align: right; }}
  .stat-card .muted {{ font-weight: 400; color: var(--muted); font-size: 11px; }}

  table.data-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12.5px; }}
  table.data-table caption {{ text-align: left; font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }}
  table.data-table th, table.data-table td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--hairline); }}
  table.data-table th {{ color: var(--text-secondary); font-weight: 500; }}
  table.data-table td:not(:first-child), table.data-table th:not(:first-child) {{ font-variant-numeric: tabular-nums; }}
</style>

<div class="viz-root">
  <h1>W6 feasible corridors, evaluated on their own merits</h1>
  <p class="subtitle">
    The 3 corridors that passed W5/W6 feasibility (of 6 generated), over the AGEB coverage-gap
    surface. Hover or focus a corridor (on the map, in the legend, or in the cards) to see how
    much genuine need it serves, whether it overlaps existing SITEUR routes, and how much demand
    it captures per kilometre versus the existing 247-route system.
  </p>

  <div class="layout">
    <div class="map-panel">
      <svg viewBox="0 0 {VBW:.1f} {VBH:.1f}" role="img" aria-label="Map of ZMG AGEBs colored by coverage-gap severity, with the 3 feasible W6 corridors overlaid">
        <g class="ageb-layer">
          {ageb_svg_str}
        </g>
        <g class="corridor-layer">
          {corridor_svg_str}
        </g>
      </svg>
      <div class="legend">
        <div class="legend-group">
          <span class="muted" style="color:var(--muted)">Coverage gap:</span>
          <span class="legend-item"><span class="legend-swatch" style="background:var(--gap-lo)"></span>Low</span>
          <span class="legend-item"><span class="legend-swatch" style="background:var(--gap-med)"></span>Medium</span>
          <span class="legend-item"><span class="legend-swatch" style="background:var(--gap-hi)"></span>High</span>
        </div>
        <div class="legend-group">
          <span class="muted" style="color:var(--muted)">Corridors:</span>
          <span class="legend-item"><span class="legend-line" style="background:var(--c-g00)"></span>W6_G00</span>
          <span class="legend-item"><span class="legend-line" style="background:var(--c-g03)"></span>W6_G03</span>
          <span class="legend-item"><span class="legend-line" style="background:var(--c-g05)"></span>W6_G05</span>
        </div>
      </div>
    </div>

    <div class="side-panel">
      {card_html_str}
    </div>
  </div>

  <table class="data-table">
    <caption>Full comparison — feasible W6 corridors vs. metro / existing-system baselines</caption>
    <thead>
      <tr><th>Corridor</th><th>Mode</th><th>km</th><th>AGEBs</th><th>High-gap share</th>
          <th>Demand median</th><th>Demand/km</th><th>Best overlap (route)</th></tr>
    </thead>
    <tbody>
      {table_rows_str}
    </tbody>
  </table>
</div>

<script>
(function() {{
  var served = {served_json_str};
  var groups = document.querySelectorAll('.corridor-group');
  var cards = document.querySelectorAll('.stat-card');
  var agebPaths = document.querySelectorAll('path.ageb');
  var agebById = {{}};
  agebPaths.forEach(function(p) {{ agebById[p.getAttribute('data-ageb')] = p; }});

  function setActive(id) {{
    groups.forEach(function(g) {{
      g.classList.toggle('inactive', id && g.getAttribute('data-id') !== id);
    }});
    cards.forEach(function(c) {{
      c.classList.toggle('inactive', id && c.getAttribute('data-id') !== id);
      c.classList.toggle('active', id && c.getAttribute('data-id') === id);
    }});
    agebPaths.forEach(function(p) {{ p.classList.remove('served-highlight'); p.classList.remove('dim'); }});
    if (id && served[id]) {{
      agebPaths.forEach(function(p) {{ p.classList.add('dim'); }});
      served[id].forEach(function(cve) {{
        var p = agebById[cve];
        if (p) {{ p.classList.remove('dim'); p.classList.add('served-highlight'); }}
      }});
    }}
  }}

  function clear() {{ setActive(null); }}

  function wire(el) {{
    var id = el.getAttribute('data-id');
    el.addEventListener('mouseenter', function() {{ setActive(id); }});
    el.addEventListener('focus', function() {{ setActive(id); }});
    el.addEventListener('mouseleave', clear);
    el.addEventListener('blur', clear);
  }}
  groups.forEach(wire);
  cards.forEach(wire);
}})();
</script>
"""

out_path = OUT_DIR / "w6_corridor_map.html"
with open(out_path, "w") as f:
    f.write(html)
print("wrote", out_path, len(html), "bytes")
