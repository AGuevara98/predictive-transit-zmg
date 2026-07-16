"""
W8 probe -- Line 4 out-of-sample check.

The GTFS in data/gtfs/ is a 2024 snapshot, predating Line 4's 2025-12-15 opening, so
the W3 accessibility / coverage-gap layer treats the Tlajomulco->GDL corridor as
UNSERVED. Question: does the demand / coverage-gap surface already flag the real
Line 4 alignment as high-priority BEFORE the line existed? If corridor AGEBs skew
High-gap / high-demand vs the metro baseline, the framework was independently pointing
at Line 4 -- out-of-sample corroboration of the core claim (does not prove optimality;
Line 4 was a long-planned project, so this is revealed-preference agreement).

This is a PROBE, not the full backtest. If it lights up, the next step is the W6
re-proposal test (does W6 generate a corridor matching data/linea_4.geojson).

Run (WSL, venv active): python src/w8_line4_probe.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geopandas as gpd
from shapely.ops import unary_union
from sqlalchemy import create_engine
from config import PG_URI

BUFFER_M = 800
L4_PATH = Path(__file__).resolve().parent.parent / "data" / "linea_4.geojson"


def main():
    eng = create_engine(PG_URI)

    # --- Line 4 corridor envelope (prefer track lines; fall back to all geoms) ---
    l4 = gpd.read_file(L4_PATH)
    if l4.crs is None:
        l4 = l4.set_crs(4326)          # OSM export default
    l4 = l4.to_crs(6372)
    lines = l4[l4.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    src = lines if len(lines) else l4
    corridor = unary_union(list(src.geometry)).buffer(BUFFER_M)
    print(f"[Line 4] {len(l4)} geojson features; {len(lines)} line geoms used; "
          f"buffer {BUFFER_M} m")

    # --- AGEBs + demand / gap / priority metrics ---
    q = """
        SELECT a.cvegeo AS cve_ageb, a.geom,
               cg.gap_category, cg.coverage_gap_n,
               te.transit_demand,
               pr.final_score, pr.npp_score, pr.equity_score
        FROM base.ageb a
        LEFT JOIN features.ageb_coverage_gap   cg ON cg.cve_ageb = a.cvegeo
        LEFT JOIN features.ageb_trip_ends      te ON te.cve_ageb = a.cvegeo
        LEFT JOIN features.nppv_prioritization pr ON pr.cve_ageb = a.cvegeo
    """
    ag = gpd.read_postgis(q, eng, geom_col="geom")     # EPSG:6372
    ag["in_corridor"] = ag.geometry.centroid.within(corridor)
    corr = ag[ag["in_corridor"]]
    print(f"[AGEBs] {len(ag)} total; {len(corr)} within Line 4 corridor\n")

    def share(df, cat):
        return (df["gap_category"] == cat).mean()

    print("gap_category share      corridor    metro")
    for cat in ["High-gap", "Medium-gap", "Low-gap"]:
        print(f"  {cat:<12} {share(corr, cat):>9.1%} {share(ag, cat):>9.1%}")

    print("\nmetric              corridor_median    metro_median")
    for col in ["transit_demand", "coverage_gap_n", "final_score",
                "npp_score", "equity_score"]:
        print(f"  {col:<16} {corr[col].median():>13.3f} {ag[col].median():>15.3f}")

    hi_c, hi_m = share(corr, "High-gap"), share(ag, "High-gap")
    ratio = f"{hi_c / hi_m:.1f}x" if hi_m else "n/a"
    print(f"\n[VERDICT] High-gap share: corridor {hi_c:.1%} vs metro {hi_m:.1%} ({ratio}). "
          f"Corridor demand median {corr['transit_demand'].median():.0f} vs "
          f"metro {ag['transit_demand'].median():.0f}.")


if __name__ == "__main__":
    main()
