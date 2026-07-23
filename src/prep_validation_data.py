"""
Genera los insumos del dashboard de validacion de coverage-gap / accesibilidad.

Combina:
  - data/ageb_zmg_2020_v2.gpkg              (geometria de las 2,068 AGEB)
  - outputs/w3/ageb_coverage_gap.csv        (indice de brecha de cobertura, W3)
  - outputs/w3/ageb_accessibility.csv       (accesibilidad a empleo, W3)
  - ground_truth_60ageb.csv                 (validacion manual Semanas 2-3)

Salidas (en outputs/w3_validation_dashboard/):
  - agebs_layer.geojson           capa de AGEBs con color precalculado
  - ground_truth_points.geojson   puntos de la validacion manual, geolocalizados
  - validation_summary.json       resumen para la tarjeta de "matriz de confusion"

Uso:
    python src/prep_validation_data.py
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import set_precision

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "outputs" / "w3_validation_dashboard"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GAP_COLOR = {"High-gap": "#c0392b", "Medium-gap": "#e8a33d", "Low-gap": "#2e8b57"}


def acc_color(v):
    if pd.isna(v):
        return "#cccccc"
    if v <= 0.05:
        return "#7f1d1d"
    if v <= 0.2:
        return "#c0392b"
    if v <= 0.4:
        return "#e8a33d"
    if v <= 0.65:
        return "#7fb3d5"
    return "#1c5cab"


def main():
    agebs = gpd.read_file(REPO / "data" / "ageb_zmg_2020_v2.gpkg")
    agebs = agebs.rename(columns={"CVEGEO": "cve_ageb"})
    agebs["cve_ageb"] = agebs["cve_ageb"].astype(str)

    cov = pd.read_csv(REPO / "outputs" / "w3" / "ageb_coverage_gap.csv", dtype={"cve_ageb": str})
    acc = pd.read_csv(REPO / "outputs" / "w3" / "ageb_accessibility.csv", dtype={"cve_ageb": str})

    merged = agebs.merge(cov, on="cve_ageb", how="left").merge(
        acc[["cve_ageb", "accessibility_n"]], on="cve_ageb", how="left"
    )

    # Solo las AGEB que W3 realmente analizo (1,881 de la ZMG)
    valid = merged[merged["gap_category"].notna()].copy()
    valid["geometry"] = valid["geometry"].simplify(0.0004, preserve_topology=True)
    valid["geometry"] = valid["geometry"].apply(lambda g: set_precision(g, 0.00001))

    valid["gap_color"] = valid["gap_category"].map(GAP_COLOR)
    valid["acc_color"] = valid["accessibility_n"].apply(acc_color)

    cols = ["cve_ageb", "geometry", "coverage_gap_n", "gap_category", "gap_color",
            "accessibility_n", "acc_color"]
    valid[cols].to_file(OUT_DIR / "agebs_layer.geojson", driver="GeoJSON")

    # --- Ground truth (validacion manual Semanas 2-3) ---
    gt_path = REPO / "outputs" / "w3_validation_dashboard" / "ground_truth_60ageb.csv"
    gt = pd.read_csv(gt_path, dtype={"cve_ageb": str})

    geom_lookup = agebs[["cve_ageb", "geometry"]].copy()
    geom_lookup["rep_point"] = geom_lookup.geometry.representative_point()
    gt_geo = gt.merge(geom_lookup[["cve_ageb", "rep_point"]], on="cve_ageb", how="left")

    features = []
    n_unmatched = 0
    for _, row in gt_geo.iterrows():
        if pd.isna(row["rep_point"]):
            n_unmatched += 1
            continue
        pt = row["rep_point"]
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [pt.x, pt.y]},
            "properties": {
                "cve_ageb": row["cve_ageb"],
                "municipio": row["Municipio"],
                "transporte_400m": row["¿Transporte a <400 m?"],
                "distancia": row["Distancia aprox."],
                "resultado": row["Resultado"],
                "obs": row["Observaciones"],
            },
        })

    with open(OUT_DIR / "ground_truth_points.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)

    # --- Resumen de validacion (cifras oficialmente reportadas en campo) ---
    n_sample = len(gt)
    correct = int((gt["Resultado"] == "Correcto").sum())
    false_pos = int((gt["Resultado"] == "Falso positivo").sum())
    summary = {
        "n_sample": n_sample,
        "correct": correct,
        "false_pos": false_pos,
        "precision": round(correct / n_sample, 4),
        "fpr": round(false_pos / n_sample, 4),
        "n_flagged_total": 671,  # AGEB con accessibility_score = 0 (ver Semana 2)
        "n_mapped": len(features),
        "n_unmatched": n_unmatched,
    }
    with open(OUT_DIR / "validation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"AGEBs en capa de mapa: {len(valid)}")
    print(f"Puntos de ground-truth geolocalizados: {len(features)} / {n_sample}"
          f" ({n_unmatched} no coinciden con la corrida vigente del pipeline)")
    print(f"Resumen: {summary}")


if __name__ == "__main__":
    main()
