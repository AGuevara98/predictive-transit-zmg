"""
W9 NPP feature build for a transfer city (CSV-based, no DB)
==========================================================
Builds the 14-feature NODE+PLACE+PEOPLE indicator set (the W4 input) for a
transfer city, mirroring src/build_nppv_features.py but file-based and
parameterized. Vitality is dropped (as in ZMG W4).

Inputs (per city, --city {tol,ags}):
  NODE   -> OSM drive graph  (cfg.OSM_NETWORK_CACHE; downloaded via osmnx)
  PLACE  -> slim INEGI DENUE (data/raw/denue/{key}_denue_combined.csv; aggregated
            by the AGEB code already present, no spatial join needed)
  PEOPLE -> slim census extract + equity indicators
            (data/raw/census/{key}_indicators_combined.csv: IM_2020, IRS_2020)
  GEOM   -> AGEB polygons from the committed shapefile (area + intersection joins)

The AGEB universe is the same as the Tier-1 demand surface (real urban AGEBs).

Output: outputs/w9/{key}_nppv_features.csv (14 raw + 14 normalized `_n` columns)

Usage:
    python src/w9_build_nppv.py --city ags     # fast
    python src/w9_build_nppv.py --city tol      # larger OSM graph
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import EMPLOYMENT_PROXY_MAP  # noqa: E402
# Reuse the ZMG feature helpers (importing build_nppv_features does NOT open a DB
# connection -- the engine is created inside build(), not at module load).
from src.build_nppv_features import (
    normalize_feature, sector_label, land_use_entropy, dep_ratio, youth_share,
)
from src.w9_run_tier1 import load_city_config, resolve_paths, _first_existing

OUTPUT_DIR = ROOT / "outputs" / "w9"
CRS = "EPSG:6372"

# 14 NPP features (NODE 3 + PLACE 5 + PEOPLE 6); vitality dropped.
NODE = ["n_intersections", "n_intersection_density", "n_street_density"]
PLACE = ["p_poi_density", "p_employment_proxy", "p_retail_density",
         "p_service_density", "p_land_use_mix"]
PEOPLE = ["pe_population", "pe_pop_density", "pe_marginacion", "pe_rezago",
          "pe_dep_ratio", "pe_youth_share"]
NPP14 = NODE + PLACE + PEOPLE


def load_agebs(cfg, paths) -> gpd.GeoDataFrame:
    print("[0] AGEB polygons...")
    gdf = gpd.read_file(_first_existing(paths["shp"])).to_crs(CRS)
    if "CVEGEO" in gdf.columns:
        gdf["cve_ageb"] = gdf["CVEGEO"].astype(str).str.strip()
    else:
        gdf["cve_ageb"] = (gdf["CVE_ENT"].astype(str).str.zfill(2) + gdf["CVE_MUN"].astype(str).str.zfill(3)
                           + gdf["CVE_LOC"].astype(str).str.zfill(4) + gdf["CVE_AGEB"].astype(str).str.zfill(4))
    # Restrict to the demand-surface AGEB universe (real urban AGEBs)
    demand = pd.read_csv(OUTPUT_DIR / f"{cfg.CITY_KEY}_demand_surface.csv", dtype={"cve_ageb": str})
    gdf = gdf[gdf["cve_ageb"].isin(set(demand["cve_ageb"]))].copy()
    gdf = gdf[["cve_ageb", "geometry"]].reset_index(drop=True)
    gdf["area_km2"] = gdf.geometry.area / 1e6
    print(f"  [OK] {len(gdf):,} AGEBs")
    return gdf


def compute_node(cfg, agebs) -> pd.DataFrame:
    print("[1] NODE (OSM drive graph)...")
    import osmnx as ox
    G = ox.load_graphml(filepath=str(ROOT / cfg.OSM_NETWORK_CACHE))
    nodes = ox.graph_to_gdfs(G, nodes=True, edges=False).to_crs(CRS)
    edges = ox.graph_to_gdfs(G, nodes=False, edges=True).to_crs(CRS)
    nodes["street_count"] = pd.to_numeric(nodes.get("street_count", 0), errors="coerce").fillna(0)
    ints = nodes[nodes["street_count"] >= 3][["street_count", "geometry"]].reset_index(drop=True)
    ji = gpd.sjoin(ints, agebs[["cve_ageb", "geometry"]], how="inner", predicate="within")
    nc = ji.groupby("cve_ageb").agg(n_int=("street_count", "count"),
                                    n_4way=("street_count", lambda x: (x >= 4).sum())).reset_index()
    if "length" not in edges.columns:
        edges["length"] = edges.geometry.length
    edges["length"] = pd.to_numeric(edges["length"], errors="coerce").fillna(0)
    ep = edges.copy()
    ep["geometry"] = ep.geometry.interpolate(0.5, normalized=True)
    je = gpd.sjoin(ep[["length", "geometry"]].reset_index(drop=True),
                   agebs[["cve_ageb", "geometry"]], how="inner", predicate="within")
    sl = je.groupby("cve_ageb")["length"].sum().reset_index().rename(columns={"length": "street_len_m"})
    nf = agebs[["cve_ageb", "area_km2"]].merge(nc, on="cve_ageb", how="left").merge(sl, on="cve_ageb", how="left").fillna(0)
    a = nf["area_km2"].clip(lower=0.01)
    nf["n_intersections"] = nf["n_int"] / a
    nf["n_intersection_density"] = nf["n_4way"] / a
    nf["n_street_density"] = nf["street_len_m"] / a
    print(f"  [OK] node features for {len(nf):,} AGEBs")
    return nf[["cve_ageb"] + NODE]


def compute_place(cfg, paths, agebs) -> pd.DataFrame:
    print("[2] PLACE (INEGI DENUE)...")
    d = pd.read_csv(_first_existing(paths["denue"]), dtype=str)
    d.columns = [c.lower() for c in d.columns]
    d["cve_ageb"] = (d["cve_ent"].str.strip().str.zfill(2) + d["cve_mun"].str.strip().str.zfill(3)
                     + d["cve_loc"].str.strip().str.zfill(4) + d["ageb"].str.strip().str.zfill(4))
    d["emp_proxy"] = d["per_ocu"].str.strip().map(EMPLOYMENT_PROXY_MAP).fillna(0)
    d["sector_label"] = d["codigo_act"].str.strip().apply(sector_label)
    place = d.groupby("cve_ageb").agg(
        p_poi_count=("codigo_act", "count"),
        p_emp_total=("emp_proxy", "sum"),
        p_retail_count=("sector_label", lambda x: (x == "retail").sum()),
        p_service_count=("sector_label", lambda x: x.isin(["health", "education", "government"]).sum()),
        p_land_use_mix=("sector_label", land_use_entropy),
    ).reset_index()
    pf = agebs[["cve_ageb", "area_km2"]].merge(place, on="cve_ageb", how="left").fillna(0)
    a = pf["area_km2"].clip(lower=0.01)
    pf["p_poi_density"] = pf["p_poi_count"] / a
    pf["p_employment_proxy"] = pf["p_emp_total"]
    pf["p_retail_density"] = pf["p_retail_count"] / a
    pf["p_service_density"] = pf["p_service_count"] / a
    print(f"  [OK] place features for {len(pf):,} AGEBs")
    return pf[["cve_ageb"] + PLACE]


def compute_people(cfg, paths, agebs) -> pd.DataFrame:
    print("[3] PEOPLE (census + CONAPO/CONEVAL equity)...")
    c = pd.read_csv(_first_existing(paths["census"]), dtype=str)
    c["cve_ageb"] = c["cve_ageb"].astype(str).str.zfill(13)
    for col in ["POBTOT", "POB0_14", "POB15_64", "POB65_MAS", "P_15A17", "P_18A24"]:
        c[col] = pd.to_numeric(c.get(col), errors="coerce").fillna(0)
    c["pop_15_29"] = c["P_15A17"] + c["P_18A24"]

    ind_path = ROOT / "data" / "raw" / "census" / f"{cfg.CITY_KEY}_indicators_combined.csv"
    ind = pd.read_csv(ind_path, dtype=str)
    ind["cve_ageb"] = ind["cve_ageb"].astype(str).str.zfill(13)
    ind["IM_2020"] = pd.to_numeric(ind["IM_2020"], errors="coerce")
    ind["IRS_2020"] = pd.to_numeric(ind["IRS_2020"], errors="coerce")

    pf = agebs[["cve_ageb", "area_km2"]].merge(
        c[["cve_ageb", "POBTOT", "POB0_14", "POB15_64", "POB65_MAS", "pop_15_29"]],
        on="cve_ageb", how="left")
    pf = pf.merge(ind[["cve_ageb", "IM_2020", "IRS_2020"]], on="cve_ageb", how="left")
    for col in ["POBTOT", "POB0_14", "POB15_64", "POB65_MAS", "pop_15_29"]:
        pf[col] = pf[col].fillna(0)
    a = pf["area_km2"].clip(lower=0.01)
    pf["pe_population"] = pf["POBTOT"]
    pf["pe_pop_density"] = pf["POBTOT"] / a
    pf["pe_dep_ratio"] = pf.apply(lambda r: dep_ratio(r["POB0_14"], r["POB65_MAS"], r["POB15_64"]), axis=1)
    pf["pe_youth_share"] = pf.apply(lambda r: youth_share(r["pop_15_29"], r["POBTOT"]), axis=1)
    # Raw stays official index; median-impute gaps (skipna). marginacion direction
    # corrected in normalize_feature (INVERTED_FEATURES -> pe_marginacion_n = 1-minmax).
    pf["pe_marginacion"] = pf["IM_2020"].fillna(pf["IM_2020"].median())
    pf["pe_rezago"] = pf["IRS_2020"].fillna(pf["IRS_2020"].median())
    print(f"  [OK] people features for {len(pf):,} AGEBs "
          f"(marginacion missing {pf['IM_2020'].isna().sum()}, rezago missing {pf['IRS_2020'].isna().sum()})")
    return pf[["cve_ageb"] + PEOPLE]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True, choices=["tol", "ags"])
    city = ap.parse_args().city
    cfg = load_city_config(city)
    paths = resolve_paths(cfg)
    print("\n" + "=" * 70)
    print(f"W9 NPP FEATURE BUILD -- {cfg.CITY_NAME.upper()} ({city})")
    print("=" * 70)

    agebs = load_agebs(cfg, paths)
    feat = agebs[["cve_ageb"]].copy()
    for df in [compute_node(cfg, agebs), compute_place(cfg, paths, agebs), compute_people(cfg, paths, agebs)]:
        feat = feat.merge(df, on="cve_ageb", how="left")
    feat = feat.fillna(0)

    for col in NPP14:
        feat[f"{col}_n"] = normalize_feature(feat[col], col)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"{city}_nppv_features.csv"
    feat[["cve_ageb"] + NPP14 + [f"{c}_n" for c in NPP14]].to_csv(out, index=False)
    print("\n" + "=" * 70)
    print(f"NPP BUILD COMPLETE ({cfg.CITY_NAME}) -> {out}")
    print("=" * 70)
    print(feat[[f"{c}_n" for c in NPP14]].describe().loc[["mean", "std", "max"]].T.to_string())


if __name__ == "__main__":
    main()
