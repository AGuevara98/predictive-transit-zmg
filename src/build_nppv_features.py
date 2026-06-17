"""Build features.nppv_features (post-W0) from committed source inputs.

Replaces the deleted phase2_db_setup.py + phase2_feature_engineering.py.
Corrections vs the deleted version:
  - drops v_ntl_median entirely (W0.1)
  - log1p+minmax for count/economic features, plain minmax for ratios (W0.3)
  - reads committed slim ZMG census extract (no ../gdl dependency)
  - reuses committed INEGI_DENUE_UTF8.csv (derives sector_id from scian_codigo)
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.stats import entropy as sp_entropy
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (  # noqa: E402
    PG_URI, CRS_CANONICAL, ZMG_BBOX,
    EMPLOYMENT_PROXY_MAP, SCIAN_SECTORS,
)

# Committed source inputs (relative to repo root)
ROOT = Path(__file__).parent.parent
DENUE_CSV = ROOT / "data" / "raw" / "denue" / "zmg_denue_combined.csv"
CENSUS_CSV = ROOT / "data" / "raw" / "census" / "ageb_urbana_14_cpv2020_zmg.csv"
INDICATORS_CSV = ROOT / "data" / "raw" / "census" / "zmg_indicators_combined.csv"
RIDERSHIP_CSV = ROOT / "data" / "raw" / "ridership" / "jalisco_ridership_etup.csv"
OSM_CACHE = ROOT / "data" / "raw" / "osm" / "zmg_drive.graphml"
SNAPSHOT_CSV = ROOT / "outputs" / "build" / "nppv_features.csv"

RAW_FEATURES = [
    "n_intersections", "n_intersection_density", "n_street_density",
    "p_poi_density", "p_employment_proxy", "p_retail_density",
    "p_service_density", "p_land_use_mix",
    "pe_population", "pe_pop_density", "pe_dep_ratio", "pe_youth_share",
    "pe_marginacion", "pe_rezago", "v_ridership_annual",
]
# Bounded ratios keep plain min-max (W0.3); everything else is count/economic -> log1p+minmax
BOUNDED_FEATURES = ["pe_marginacion", "pe_rezago", "pe_dep_ratio",
                    "pe_youth_share", "p_land_use_mix"]
LOG_FEATURES = [f for f in RAW_FEATURES if f not in BOUNDED_FEATURES]


def minmax(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series(0.0, index=s.index)
    return (s - lo) / (hi - lo)


def normalize_feature(s: pd.Series, name: str) -> pd.Series:
    if name in LOG_FEATURES:
        return minmax(np.log1p(s.clip(lower=0)))
    return minmax(s)


def scian_sector(scian_codigo) -> str:
    if scian_codigo is None:
        return ""
    return str(scian_codigo)[:2] if str(scian_codigo).strip() else ""


def sector_label(sector_id) -> str:
    if not sector_id:
        return "other"
    for name, codes in SCIAN_SECTORS.items():
        if any(str(sector_id).startswith(c) for c in codes):
            return name
    return "other"


def land_use_entropy(labels: pd.Series) -> float:
    counts = labels.value_counts()
    if len(counts) <= 1:
        return 0.0
    return float(sp_entropy(counts.values))


def dep_ratio(p0_14, p65, p15_64) -> float:
    return float(min((p0_14 + p65) / max(p15_64, 1), 5.0))


def youth_share(p15_29, pop_total) -> float:
    return float(p15_29 / pop_total) if pop_total else 0.0


# ---------------------------------------------------------------------------
# 0. Load AGEB geometries
# ---------------------------------------------------------------------------

def load_agebs(engine) -> gpd.GeoDataFrame:
    """Load the 2,068 ZMG AGEB polygons from raw.ageb, projected to 6372."""
    print("[Step 0] Loading AGEB geometries...")
    with engine.raw_connection() as conn:
        gdf = gpd.read_postgis(
            "SELECT cvegeo AS cve_ageb, geom AS geometry FROM raw.ageb",
            conn, geom_col="geometry",
        )
    gdf = gdf.to_crs(CRS_CANONICAL)
    gdf["cve_ageb"] = gdf["cve_ageb"].astype(str)
    gdf["area_km2"] = gdf.geometry.area / 1e6
    print(f"  [OK] {len(gdf):,} AGEBs loaded, CRS={gdf.crs}")
    return gdf


# ---------------------------------------------------------------------------
# 1. NODE dimension (osmnx)
# ---------------------------------------------------------------------------

def _load_osm_graph():
    """Load the cached ZMG drive graph or download it via osmnx (2.1.0)."""
    import osmnx as ox
    OSM_CACHE.parent.mkdir(parents=True, exist_ok=True)
    if OSM_CACHE.exists():
        print(f"  [OK] Loading OSM graph from cache: {OSM_CACHE}")
        return ox.load_graphml(filepath=str(OSM_CACHE))
    print("  [..] Downloading ZMG drive graph from OSM (may take several min)...")
    bbox = (ZMG_BBOX["xmin"], ZMG_BBOX["ymin"], ZMG_BBOX["xmax"], ZMG_BBOX["ymax"])
    G = ox.graph_from_bbox(bbox=bbox, network_type="drive")
    ox.save_graphml(G, filepath=str(OSM_CACHE))
    print(f"  [OK] OSM graph cached to {OSM_CACHE}")
    return G


def compute_node_features(agebs: gpd.GeoDataFrame, engine=None) -> pd.DataFrame:
    print("\n[Step 1] Computing NODE features (osmnx)...")
    import osmnx as ox

    G = _load_osm_graph()

    nodes = ox.graph_to_gdfs(G, nodes=True, edges=False)
    edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
    nodes = nodes.to_crs(CRS_CANONICAL)
    edges = edges.to_crs(CRS_CANONICAL)

    # Intersections: street_count >= 3; 4-way: street_count >= 4
    nodes["street_count"] = pd.to_numeric(
        nodes.get("street_count", 0), errors="coerce"
    ).fillna(0)
    ints = nodes[nodes["street_count"] >= 3].copy()
    ints = ints[["street_count", "geometry"]].reset_index(drop=True)

    joined_ints = gpd.sjoin(
        ints, agebs[["cve_ageb", "geometry"]], how="inner", predicate="within"
    )
    node_counts = joined_ints.groupby("cve_ageb").agg(
        n_int=("street_count", "count"),
        n_4way=("street_count", lambda x: (x >= 4).sum()),
    ).reset_index()

    # Street length per AGEB via edge midpoints
    if "length" not in edges.columns:
        edges["length"] = edges.geometry.length
    edges["length"] = pd.to_numeric(edges["length"], errors="coerce").fillna(0)
    edge_pts = edges.copy()
    edge_pts["geometry"] = edge_pts.geometry.interpolate(0.5, normalized=True)
    edge_pts = edge_pts[["length", "geometry"]].reset_index(drop=True)
    joined_edges = gpd.sjoin(
        edge_pts, agebs[["cve_ageb", "geometry"]], how="inner", predicate="within"
    )
    street_len = joined_edges.groupby("cve_ageb")["length"].sum().reset_index()
    street_len.columns = ["cve_ageb", "street_len_m"]

    nf = agebs[["cve_ageb", "area_km2"]].merge(node_counts, on="cve_ageb", how="left")
    nf = nf.merge(street_len, on="cve_ageb", how="left").fillna(0)
    area_clip = nf["area_km2"].clip(lower=0.01)

    nf["n_intersections"] = nf["n_int"] / area_clip
    nf["n_intersection_density"] = nf["n_4way"] / area_clip
    nf["n_street_density"] = nf["street_len_m"] / area_clip

    print(f"  [OK] Node features computed for {len(nf):,} AGEBs.")
    return nf[["cve_ageb", "n_intersections",
               "n_intersection_density", "n_street_density"]]


# ---------------------------------------------------------------------------
# 2. PLACE dimension (committed DENUE)
# ---------------------------------------------------------------------------

def compute_place_features(agebs: gpd.GeoDataFrame, engine=None) -> pd.DataFrame:
    print("\n[Step 2] Computing PLACE features (full ZMG DENUE)...")

    # Encoding check: default (utf-8) read must align with EMPLOYMENT_PROXY_MAP
    # keys; fall back to latin-1 if Estrato values don't match the map.
    denue = pd.read_csv(DENUE_CSV, dtype=str)
    unmapped = denue["Estrato"].map(EMPLOYMENT_PROXY_MAP).isna().sum()
    if unmapped > 0:
        print(f"  [..] {unmapped:,} unmapped Estrato values under default encoding, "
              f"retrying with latin-1...")
        denue = pd.read_csv(DENUE_CSV, dtype=str, encoding="latin-1")
        unmapped = denue["Estrato"].map(EMPLOYMENT_PROXY_MAP).isna().sum()
    print(f"  [OK] Encoding check: {unmapped:,} unmapped Estrato values "
          f"of {len(denue):,} rows")

    denue["emp_proxy"] = denue["Estrato"].map(EMPLOYMENT_PROXY_MAP).fillna(0)
    if denue["emp_proxy"].sum() == 0:
        print("  [ERR] emp_proxy is all-zero -- Estrato mapping failed!")
    else:
        print(f"  [OK] emp_proxy sum={denue['emp_proxy'].sum():,.0f} "
              f"(non-zero, mapping succeeded)")

    denue["sector_id"] = denue["SECTOR_ACTIVIDAD_ID"]
    denue["sector_label"] = denue["sector_id"].apply(sector_label)

    lon = pd.to_numeric(denue["Longitud"], errors="coerce")
    lat = pd.to_numeric(denue["Latitud"], errors="coerce")
    gdf = gpd.GeoDataFrame(
        denue, geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326"
    )
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].to_crs(CRS_CANONICAL)

    joined = gpd.sjoin(
        gdf[["emp_proxy", "sector_id", "sector_label", "geometry"]],
        agebs[["cve_ageb", "geometry"]], how="inner", predicate="within",
    )

    place = joined.groupby("cve_ageb").agg(
        p_poi_count=("sector_id", "count"),
        p_emp_total=("emp_proxy", "sum"),
        p_retail_count=("sector_label", lambda x: (x == "retail").sum()),
        p_service_count=("sector_label",
                         lambda x: x.isin(["health", "education", "government"]).sum()),
        p_land_use_mix=("sector_label", land_use_entropy),
    ).reset_index()

    pf = agebs[["cve_ageb", "area_km2"]].merge(place, on="cve_ageb", how="left").fillna(0)
    area_clip = pf["area_km2"].clip(lower=0.01)

    pf["p_poi_density"] = pf["p_poi_count"] / area_clip
    pf["p_employment_proxy"] = pf["p_emp_total"]
    pf["p_retail_density"] = pf["p_retail_count"] / area_clip
    pf["p_service_density"] = pf["p_service_count"] / area_clip

    print(f"  [OK] Place features computed for {len(pf):,} AGEBs.")
    return pf[["cve_ageb", "p_poi_density", "p_employment_proxy",
               "p_retail_density", "p_service_density", "p_land_use_mix"]]


# ---------------------------------------------------------------------------
# 3. PEOPLE dimension (committed census + indicators)
# ---------------------------------------------------------------------------

def compute_people_features(agebs: gpd.GeoDataFrame) -> pd.DataFrame:
    print("\n[Step 3] Computing PEOPLE features (census)...")

    census = pd.read_csv(CENSUS_CSV, dtype=str)
    census["cve_ageb"] = census["cve_ageb"].astype(str).str.zfill(13)
    for c in ["POBTOT", "POB0_14", "POB15_64", "POB65_MAS", "P_15A17", "P_18A24"]:
        census[c] = pd.to_numeric(census[c], errors="coerce").fillna(0)
    census["pop_15_29"] = census["P_15A17"] + census["P_18A24"]

    ind = pd.read_csv(INDICATORS_CSV, dtype=str)
    ind["cve_ageb"] = ind["cve_ageb"].astype(str).str.zfill(13)
    ind["IM_2020"] = pd.to_numeric(ind["IM_2020"], errors="coerce").fillna(0)
    ind["IRS_2020"] = pd.to_numeric(ind["IRS_2020"], errors="coerce").fillna(0)

    pf = agebs[["cve_ageb", "area_km2"]].merge(
        census[["cve_ageb", "POBTOT", "POB0_14", "POB15_64",
                "POB65_MAS", "pop_15_29"]],
        on="cve_ageb", how="left",
    )
    pf = pf.merge(ind[["cve_ageb", "IM_2020", "IRS_2020"]],
                  on="cve_ageb", how="left").fillna(0)

    area_clip = pf["area_km2"].clip(lower=0.01)
    pf["pe_population"] = pf["POBTOT"]
    pf["pe_pop_density"] = pf["POBTOT"] / area_clip
    pf["pe_dep_ratio"] = pf.apply(
        lambda r: dep_ratio(r["POB0_14"], r["POB65_MAS"], r["POB15_64"]), axis=1
    )
    pf["pe_youth_share"] = pf.apply(
        lambda r: youth_share(r["pop_15_29"], r["POBTOT"]), axis=1
    )
    pf["pe_marginacion"] = pf["IM_2020"]
    pf["pe_rezago"] = pf["IRS_2020"]

    print(f"  [OK] People features computed for {len(pf):,} AGEBs.")
    return pf[["cve_ageb", "pe_population", "pe_pop_density", "pe_dep_ratio",
               "pe_youth_share", "pe_marginacion", "pe_rezago"]]


# ---------------------------------------------------------------------------
# 4. VITALITY dimension (committed ridership; NO NTL)
# ---------------------------------------------------------------------------

def compute_vitality_features(agebs: gpd.GeoDataFrame) -> pd.DataFrame:
    print("\n[Step 4] Computing VITALITY features (ridership)...")

    rid = pd.read_csv(RIDERSHIP_CSV, dtype=str)
    rid["VALOR"] = pd.to_numeric(rid["VALOR"], errors="coerce").fillna(0)
    rid["ANIO"] = pd.to_numeric(rid["ANIO"], errors="coerce")
    rid["VARIABLE"] = rid["VARIABLE"].astype(str)

    # Annual boarded passengers for 2023, matching the original's
    # '%pasajero%' (ILIKE) aggregation. Only mun 39 (GDL/SITEUR) has data,
    # so after normalisation this is a binary 'has-SITEUR' flag regardless
    # of the absolute value.
    mask = (rid["ANIO"] == 2023) & rid["VARIABLE"].str.contains(
        "pasajero", case=False, na=False
    )
    agg = (rid[mask].assign(mun=rid["CVE_MUN"].astype(str).str.zfill(3))
           .groupby("mun")["VALOR"].sum().reset_index())
    agg["mun_code"] = "14" + agg["mun"]

    vf = agebs[["cve_ageb"]].copy()
    vf["mun_code"] = vf["cve_ageb"].str[:5]
    vf = vf.merge(agg[["mun_code", "VALOR"]], on="mun_code", how="left")
    vf["v_ridership_annual"] = vf["VALOR"].fillna(0)

    print(f"  [OK] Vitality features computed for {len(vf):,} AGEBs.")
    return vf[["cve_ageb", "v_ridership_annual"]]


# ---------------------------------------------------------------------------
# 5. Assemble, normalise, write
# ---------------------------------------------------------------------------

def assemble_and_save(agebs, dfs, engine) -> pd.DataFrame:
    print("\n[Step 5] Assembling feature table and normalising...")

    feat = agebs[["cve_ageb"]].copy()
    for df in dfs:
        feat = feat.merge(df, on="cve_ageb", how="left")
    feat = feat.fillna(0)

    for c in RAW_FEATURES:
        feat[f"{c}_n"] = normalize_feature(feat[c], c)

    # Write snapshot (NOT data/raw/nppv_features.csv -- that is the Task 9 oracle)
    SNAPSHOT_CSV.parent.mkdir(parents=True, exist_ok=True)
    feat.to_csv(SNAPSHOT_CSV, index=False)
    print(f"  [OK] Snapshot written to {SNAPSHOT_CSV}")

    # Explicit column order: raw features then normalized features
    cols = ["cve_ageb"] + RAW_FEATURES + [f"{c}_n" for c in RAW_FEATURES]
    db = feat[cols].replace({np.nan: None})
    placeholders = ",".join(["%s"] * len(cols))
    insert_sql = (
        f"INSERT INTO features.nppv_features ({','.join(cols)}) "
        f"VALUES ({placeholders})"
    )
    rows = [tuple(r) for r in db.itertuples(index=False, name=None)]

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            cur.execute("DELETE FROM features.nppv_features")
            cur.executemany(insert_sql, rows)
            # Populate geom (MultiPolygon, 6372) from raw.ageb
            cur.execute(
                "UPDATE features.nppv_features f "
                "SET geom = ST_Multi(ST_Transform(a.geom, 6372)) "
                "FROM raw.ageb a WHERE a.cvegeo = f.cve_ageb"
            )
        raw_conn.commit()
    finally:
        raw_conn.close()

    print(f"  [OK] {len(feat):,} AGEBs written to features.nppv_features")
    return feat


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build(engine=None):
    """Run all steps and populate features.nppv_features. Returns the feature frame."""
    if engine is None:
        engine = create_engine(PG_URI)

    agebs = load_agebs(engine)
    node_f = compute_node_features(agebs, engine)
    place_f = compute_place_features(agebs, engine)
    people_f = compute_people_features(agebs)
    vitality_f = compute_vitality_features(agebs)

    feat = assemble_and_save(agebs, [node_f, place_f, people_f, vitality_f], engine)

    print("\n" + "=" * 70)
    print("NPPV FEATURE BUILD COMPLETE")
    print("=" * 70)
    return feat


def main():
    build()


if __name__ == "__main__":
    main()
