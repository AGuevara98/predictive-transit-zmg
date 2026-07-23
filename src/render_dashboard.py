"""
Ensambla el dashboard HTML final a partir de los insumos generados por
prep_validation_data.py. No requiere librerias externas.

Uso:
    python src/render_dashboard.py
Genera:
    outputs/w3_validation_dashboard/dashboard_validacion_zmg.html
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "outputs" / "w3_validation_dashboard"
TEMPLATE = Path(__file__).resolve().parent / "dashboard_template.html"


def main():
    agebs = json.loads((DATA_DIR / "agebs_layer.geojson").read_text())
    gt = json.loads((DATA_DIR / "ground_truth_points.geojson").read_text())
    summary = json.loads((DATA_DIR / "validation_summary.json").read_text())

    html = TEMPLATE.read_text()
    html = html.replace("__AGEBS_DATA__", json.dumps(agebs, separators=(",", ":")))
    html = html.replace("__GT_DATA__", json.dumps(gt, separators=(",", ":")))
    html = html.replace("__SUMMARY_DATA__", json.dumps(summary))

    out_path = DATA_DIR / "dashboard_validacion_zmg.html"
    out_path.write_text(html)
    print(f"Dashboard escrito en {out_path}")


if __name__ == "__main__":
    main()
