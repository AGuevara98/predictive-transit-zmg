"""
Phase 2 – Step 2: AGEB-Level Feature Engineering
=================================================
Spatially joins all raw sources to the 2,068 ZMG AGEBs and
computes the 16 NPP-V indicators at the AGEB grain.

NPP-V Dimensions:
  Node    – street network metrics
  Place   – POI/economic activity metrics
  People  – socioeconomic vulnerability metrics
  Vitality– nighttime lights + ridership
"""

import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask as rio_mask
from pathlib import Path
from sqlalchemy import create_engine, text
from scipy.stats import entropy as sp_entropy
import h5py

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI, CRS_CANONICAL, EMPLOYMENT_PROXY_MAP, SCIAN_SECTORS

ENGINE = create_engine(PG_URI)


# ---------------------------------------------------------------------------
# 0. Load AGEB geometries
# ---------------------------------------------------------------------------

def load_agebs():
    """Load ZMG AGEB polygons from raw.ageb (EPSG:6372)."""
    print("[Step 0] Loading AGEB geometries…")
    with ENGINE.raw_connection() as conn:
        gdf = gpd.read_postgis(
            "SELECT cvegeo AS cve_ageb, geom AS geometry FROM raw.ageb",
            conn, geom_col="geometry"
        )
    # Reproject from its native CRS (4326) to 6372
    gdf = gdf.to_crs(CRS_CANONICAL)
    gdf["area_km2"] = gdf.geometry.area / 1e6
    print(f"  [OK] {len(gdf):,} AGEBs loaded, CRS={gdf.crs}")
    return gdf


# ---------------------------------------------------------------------------
# 1. NODE dimension
# ---------------------------------------------------------------------------

def compute_node_features(agebs: gpd.GeoDataFrame) -> pd.DataFrame:
    print("\n[Step 1] Computing NODE features…")

    with ENGINE.raw_connection() as conn:
        ints = gpd.read_postgis(
            "SELECT osmid, street_count, geom FROM raw.osm_intersections",
            conn, geom_col="geom", crs=CRS_CANONICAL
        )
        edges = gpd.read_postgis(
            "SELECT id, length, geom FROM raw.osm_edges",
            conn, geom_col="geom", crs=CRS_CANONICAL
        )

    # Spatial join intersections → AGEBs
    joined_ints = gpd.sjoin(ints, agebs[["cve_ageb", "area_km2", "geometry"]],
                             how="left", predicate="within")

    node_counts = joined_ints.groupby("cve_ageb").agg(
        n_intersections=("osmid", "count"),
        n_4way_intersections=("street_count", lambda x: (x >= 4).sum())
    ).reset_index()

    # Street length per AGEB via spatial join of edge midpoints
    edges["midpoint"] = edges.geometry.interpolate(0.5, normalized=True)
    edge_pts = gpd.GeoDataFrame(edges, geometry="midpoint", crs=CRS_CANONICAL)
    joined_edges = gpd.sjoin(edge_pts, agebs[["cve_ageb", "geometry"]],
                              how="left", predicate="within")
    street_len = joined_edges.groupby("cve_ageb")["length"].sum().reset_index()
    street_len.columns = ["cve_ageb", "total_street_length_m"]

    # Merge and normalise by area
    nf = agebs[["cve_ageb", "area_km2"]].merge(node_counts, on="cve_ageb", how="left")
    nf = nf.merge(street_len, on="cve_ageb", how="left")
    nf = nf.fillna(0)

    nf["n_intersections"]       = nf["n_intersections"]       / nf["area_km2"].clip(lower=0.01)
    nf["n_intersection_density"] = nf["n_4way_intersections"] / nf["area_km2"].clip(lower=0.01)
    nf["n_street_density"]       = nf["total_street_length_m"] / nf["area_km2"].clip(lower=0.01)

    print(f"  [OK] Node features computed for {len(nf):,} AGEBs.")
    return nf[["cve_ageb", "n_intersections", "n_intersection_density", "n_street_density"]]


# ---------------------------------------------------------------------------
# 2. PLACE dimension
# ---------------------------------------------------------------------------

def compute_place_features(agebs: gpd.GeoDataFrame) -> pd.DataFrame:
    print("\n[Step 2] Computing PLACE features…")

    with ENGINE.raw_connection() as conn:
        denue = gpd.read_postgis(
            "SELECT ageb_cve, clase_actividad, estrato, sector_id, geom FROM raw.denue_nppv WHERE geom IS NOT NULL",
            conn, geom_col="geom", crs=CRS_CANONICAL
        )

    # Map employment proxy
    denue["emp_proxy"] = denue["estrato"].map(EMPLOYMENT_PROXY_MAP).fillna(0)

    # Sector flags
    def sector_label(sid):
        if sid is None:
            return "other"
        for name, codes in SCIAN_SECTORS.items():
            if any(str(sid).startswith(c) for c in codes):
                return name
        return "other"

    denue["sector_label"] = denue["sector_id"].apply(sector_label)

    # Spatial join POIs → AGEBs
    joined = gpd.sjoin(denue, agebs[["cve_ageb", "area_km2", "geometry"]],
                        how="left", predicate="within")

    def land_use_entropy(s):
        counts = s.value_counts()
        if len(counts) <= 1:
            return 0.0
        return float(sp_entropy(counts.values))

    place = joined.groupby("cve_ageb").agg(
        p_poi_count    = ("sector_id", "count"),
        p_emp_total    = ("emp_proxy", "sum"),
        p_retail_count = ("sector_label", lambda x: (x == "retail").sum()),
        p_service_count= ("sector_label", lambda x: (x.isin(["health","education","government"])).sum()),
        p_land_use_mix = ("sector_label", land_use_entropy)
    ).reset_index()

    pf = agebs[["cve_ageb", "area_km2"]].merge(place, on="cve_ageb", how="left").fillna(0)
    area_clip = pf["area_km2"].clip(lower=0.01)

    pf["p_poi_density"]     = pf["p_poi_count"]     / area_clip
    pf["p_employment_proxy"]= pf["p_emp_total"]
    pf["p_retail_density"]  = pf["p_retail_count"]  / area_clip
    pf["p_service_density"] = pf["p_service_count"] / area_clip

    print(f"  [OK] Place features computed for {len(pf):,} AGEBs.")
    return pf[["cve_ageb", "p_poi_density", "p_employment_proxy",
               "p_retail_density", "p_service_density", "p_land_use_mix"]]


# ---------------------------------------------------------------------------
# 3. PEOPLE dimension
# ---------------------------------------------------------------------------

def compute_people_features(agebs: gpd.GeoDataFrame) -> pd.DataFrame:
    print("\n[Step 3] Computing PEOPLE features…")

    with ENGINE.raw_connection() as conn:
        ind = pd.read_sql("SELECT cve_ageb, im_2020, irs_2020 FROM raw.indicators", conn)
    ind["cve_ageb"] = ind["cve_ageb"].astype(str).str.zfill(13)

    # Census demographics from raw file
    base_dir = Path(__file__).parent.parent.parent
    census_path = (
        base_dir / "gdl" / "ageb_mza_urbana_14_cpv2020_csv" /
        "ageb_mza_urbana_14_cpv2020" / "conjunto_de_datos" /
        "conjunto_de_datos_ageb_urbana_14_cpv2020.csv"
    )
    census = pd.read_csv(census_path, dtype=str, encoding='latin-1')

    # Keep only AGEB-level rows (MZA == 000)
    census = census[census["MZA"] == "000"].copy()

    # Construct 13-char CVE_AGEB
    census["cve_ageb"] = (
        census["ENTIDAD"].str.zfill(2)
        + census["MUN"].str.zfill(3)
        + census["LOC"].str.zfill(4)
        + census["AGEB"].str.zfill(4)
    )

    # Keep ZMG municipalities
    ZMG_MUNS = ["039", "120", "098", "101", "097", "070", "044", "051", "124", "002"]
    census = census[census["MUN"].isin(ZMG_MUNS)].copy()

    cols = {
        "POBTOT": "pop_total",
        "POB0_14": "pop_0_14",
        "POB15_64": "pop_15_64",
        "POB65_MAS": "pop_65plus",
        "P_15A29": "pop_15_29"
    }
    # P_15A29 may not exist; build from P_15A17 + P_18A24
    if "P_15A29" not in census.columns:
        for c in ["P_15A17", "P_18A24"]:
            census[c] = pd.to_numeric(census[c], errors="coerce").fillna(0)
        census["P_15A29"] = census["P_15A17"] + census["P_18A24"]

    for orig, alias in cols.items():
        if orig in census.columns:
            census[alias] = pd.to_numeric(census[orig], errors="coerce").fillna(0)
        else:
            census[alias] = 0

    census = census[["cve_ageb"] + list(cols.values())].copy()

    # Merge
    pf = agebs[["cve_ageb", "area_km2"]].merge(census, on="cve_ageb", how="left")
    pf = pf.merge(ind, on="cve_ageb", how="left").fillna(0)

    area_clip = pf["area_km2"].clip(lower=0.01)
    pf["pe_population"]  = pf["pop_total"]
    pf["pe_pop_density"] = pf["pop_total"] / area_clip

    # Dependency ratio = (0-14 + 65+) / (15-64)  (cap at 5 for outliers)
    pf["pe_dep_ratio"]   = ((pf["pop_0_14"] + pf["pop_65plus"])
                             / pf["pop_15_64"].clip(lower=1)).clip(upper=5)

    # Youth share = 15-29 / total
    pf["pe_youth_share"] = pf["pop_15_29"] / pf["pop_total"].clip(lower=1)

    pf["pe_marginacion"] = pd.to_numeric(pf["im_2020"],  errors="coerce").fillna(0)
    pf["pe_rezago"]      = pd.to_numeric(pf["irs_2020"], errors="coerce").fillna(0)

    print(f"  [OK] People features computed for {len(pf):,} AGEBs.")
    return pf[["cve_ageb", "pe_population", "pe_pop_density",
               "pe_dep_ratio", "pe_youth_share", "pe_marginacion", "pe_rezago"]]


# ---------------------------------------------------------------------------
# 4. VITALITY dimension
# ---------------------------------------------------------------------------

def compute_vitality_features(agebs: gpd.GeoDataFrame) -> pd.DataFrame:
    print("\n[Step 4] Computing VITALITY features…")

    # 4a. Nighttime Lights (VIIRS VNP46A3 – median over 2023 monthly tiles)
    viirs_dir = Path("data/raw/viirs")
    h5_files  = sorted(viirs_dir.glob("*.h5"))

    ntl_records = {}  # cve_ageb → list of values

    if h5_files:
        for h5_path in h5_files:
            try:
                with h5py.File(h5_path, "r") as hf:
                    # VIIRS Black Marble NTL path
                    dataset_path = "HDFEOS/GRIDS/VNP_Grid_DNB/Data Fields/DNB_BRDF-Corrected_NTL"
                    if dataset_path not in hf:
                        continue
                    data = hf[dataset_path][:]
                    attrs = hf[dataset_path].attrs

                    # Get geotransform from global attributes
                    root = hf["HDFEOS/GRIDS/VNP_Grid_DNB"]
                    xmin = root.attrs.get("WestBoundingCoordinate", -180)
                    xmax = root.attrs.get("EastBoundingCoordinate", 180)
                    ymin = root.attrs.get("SouthBoundingCoordinate", -90)
                    ymax = root.attrs.get("NorthBoundingCoordinate", 90)

                    nrows, ncols = data.shape
                    res_x = (xmax - xmin) / ncols
                    res_y = (ymax - ymin) / nrows

                    transform = rasterio.transform.from_bounds(xmin, ymin, xmax, ymax, ncols, nrows)

                    # Clip to ZMG AGEBs (reproject AGEBs to WGS84 for clipping)
                    agebs_wgs = agebs.to_crs("EPSG:4326")

                    for _, row in agebs_wgs.iterrows():
                        cve = row["cve_ageb"]
                        try:
                            out_img, _ = rio_mask(
                                rasterio.MemoryFile(
                                    # build in-memory raster
                                ).open(
                                    driver="GTiff", dtype=data.dtype,
                                    count=1, width=ncols, height=nrows,
                                    crs="EPSG:4326", transform=transform
                                ),
                                [row.geometry.__geo_interface__],
                                crop=True
                            )
                            vals = out_img.flatten()
                            vals = vals[vals > 0]
                            if len(vals):
                                ntl_records.setdefault(cve, []).extend(vals.tolist())
                        except Exception:
                            pass
            except Exception as e:
                print(f"  [WARN] Could not read {h5_path.name}: {e}")

    ntl_df = pd.DataFrame([
        {"cve_ageb": k, "v_ntl_median": float(np.median(v)),
         "v_ntl_mean": float(np.mean(v)), "v_ntl_max": float(np.max(v))}
        for k, v in ntl_records.items()
    ]) if ntl_records else pd.DataFrame(columns=["cve_ageb","v_ntl_median"])

    with ENGINE.raw_connection() as conn:
        rid = pd.read_sql(
            """SELECT cve_mun, SUM(valor) AS annual_passengers
               FROM raw.ridership
               WHERE anio = 2023
                 AND variable ILIKE '%pasajero%'
               GROUP BY cve_mun""",
            conn
        )
    # Map municipality code to AGEB cve_ageb prefix (first 5 chars = ent+mun)
    rid["cve_mun_str"] = "14" + rid["cve_mun"].astype(str).str.zfill(3)

    agebs_mun = agebs.copy()
    agebs_mun["mun_code"] = agebs_mun["cve_ageb"].str[:5]  # e.g. '14039'
    agebs_mun = agebs_mun.merge(
        rid.rename(columns={"cve_mun_str": "mun_code"}),
        on="mun_code", how="left"
    )
    rid_df = agebs_mun[["cve_ageb", "annual_passengers"]].rename(
        columns={"annual_passengers": "v_ridership_annual"}
    )

    # Merge vitality
    vf = agebs[["cve_ageb"]].merge(ntl_df[["cve_ageb","v_ntl_median"]] if not ntl_df.empty else pd.DataFrame({"cve_ageb":[], "v_ntl_median":[]}), on="cve_ageb", how="left")
    vf = vf.merge(rid_df, on="cve_ageb", how="left").fillna(0)

    print(f"  [OK] Vitality features computed for {len(vf):,} AGEBs.")
    return vf[["cve_ageb", "v_ntl_median", "v_ridership_annual"]]


# ---------------------------------------------------------------------------
# 5. Assemble & normalise
# ---------------------------------------------------------------------------

def minmax(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.0, index=series.index)
    return (series - lo) / (hi - lo)


RAW_FEATURES = [
    "n_intersections", "n_street_density", "n_intersection_density",
    "p_poi_density", "p_employment_proxy", "p_retail_density",
    "p_service_density", "p_land_use_mix",
    "pe_population", "pe_pop_density", "pe_marginacion", "pe_rezago",
    "pe_dep_ratio", "pe_youth_share",
    "v_ntl_median", "v_ridership_annual"
]


def assemble_and_save(agebs, node_f, place_f, people_f, vitality_f):
    print("\n[Step 5] Assembling feature table & normalising…")

    feat = agebs[["cve_ageb", "geometry"]].copy()
    for df in [node_f, place_f, people_f, vitality_f]:
        feat = feat.merge(df, on="cve_ageb", how="left")

    feat = feat.fillna(0)

    # Min-max normalisation
    for col in RAW_FEATURES:
        if col in feat.columns:
            feat[f"{col}_n"] = minmax(feat[col])

    # Convert geometry to WKB
    feat_db = feat.copy()
    feat_db["geom_wkb"] = feat_db.geometry.apply(lambda g: g.wkb_hex if g else None)
    feat_db = feat_db.drop(columns=["geometry"])

    # Write to database using psycopg2 directly to avoid SQLAlchemy 2.0 pandas bugs
    import psycopg2.extras

    # Convert to list of tuples, replace NaNs with None
    feat_db = feat_db.replace({np.nan: None})
    cols = list(feat_db.columns)
    query = f"INSERT INTO features.nppv_features ({','.join(cols)}) VALUES %s"
    values = [tuple(x) for x in feat_db.values]

    with ENGINE.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM features.nppv_features")
            cur.execute("ALTER TABLE features.nppv_features DROP COLUMN IF EXISTS geom_wkb")
            
            # Create the geom_wkb column temporarily
            cur.execute("ALTER TABLE features.nppv_features ADD COLUMN geom_wkb TEXT")
            
            psycopg2.extras.execute_values(cur, query, values, page_size=500)
            
            # Update geom from wkb
            cur.execute("UPDATE features.nppv_features SET geom = ST_SetSRID(geom_wkb::geometry, 6372) WHERE geom_wkb IS NOT NULL")
            cur.execute("ALTER TABLE features.nppv_features DROP COLUMN geom_wkb")
        conn.commit()

    # Also write a CSV snapshot
    feat.drop(columns="geometry").to_csv(
        "data/raw/nppv_features.csv", index=False
    )

    print(f"  [OK] {len(feat):,} AGEBs written to features.nppv_features")
    return feat


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agebs     = load_agebs()
    node_f    = compute_node_features(agebs)
    place_f   = compute_place_features(agebs)
    people_f  = compute_people_features(agebs)
    vitality_f= compute_vitality_features(agebs)
    feat      = assemble_and_save(agebs, node_f, place_f, people_f, vitality_f)

    print("\n" + "="*70)
    print("PHASE 2 FEATURE ENGINEERING COMPLETE")
    print("="*70)
    print(feat[RAW_FEATURES].describe().to_string())
