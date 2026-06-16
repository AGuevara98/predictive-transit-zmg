"""Examine the A-filter more carefully."""
import sys
import pandas as pd
import geopandas as gpd
from pathlib import Path
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import PG_URI, CRS_CANONICAL

ENGINE = create_engine(PG_URI)
ZMG_MUNS = {"039", "120", "098", "101", "097", "070", "044", "051", "124", "002"}

# Reproduce the merged state before A-filter
with ENGINE.raw_connection() as conn:
    gdf = gpd.read_postgis(
        "SELECT cvegeo AS cve_ageb, geom FROM base.ageb",
        conn, geom_col="geom", crs=CRS_CANONICAL
    )
gdf["area_km2"] = gdf.geometry.area / 1e6
agebs = gdf[["cve_ageb", "area_km2"]]

census_path = (
    Path(__file__).parent.parent.parent.parent
    / "gdl" / "ageb_mza_urbana_14_cpv2020_csv"
    / "ageb_mza_urbana_14_cpv2020" / "conjunto_de_datos"
    / "conjunto_de_datos_ageb_urbana_14_cpv2020.csv"
)
census = pd.read_csv(census_path, dtype=str, encoding="latin-1")
census = census[census["MZA"] == "000"].copy()
census["cve_ageb"] = (
    census["ENTIDAD"].str.zfill(2)
    + census["MUN"].str.zfill(3)
    + census["LOC"].str.zfill(4)
    + census["AGEB"].str.zfill(4)
)
census = census[census["MUN"].isin(ZMG_MUNS)].copy()
for col in ["POBTOT", "POB0_14", "POB15_64", "POB65_MAS"]:
    census[col] = pd.to_numeric(census[col], errors="coerce").fillna(0)
if "P_15A29" not in census.columns:
    for c in ["P_15A17", "P_18A24"]:
        if c not in census.columns:
            census[c] = 0
        census[c] = pd.to_numeric(census[c], errors="coerce").fillna(0)
    census["P_15A29"] = census["P_15A17"] + census["P_18A24"]
else:
    census["P_15A29"] = pd.to_numeric(census["P_15A29"], errors="coerce").fillna(0)

pop_df = census[["cve_ageb"]].copy()
pop_df["pe_population"] = census["POBTOT"].values
pop_df["pe_youth_share"] = (census["P_15A29"] / census["POBTOT"].clip(lower=1)).values

with ENGINE.raw_connection() as conn:
    place_df = pd.read_sql(
        "SELECT cve_ageb, p_employment_proxy, p_poi_density, p_retail_density FROM features.nppv_features",
        conn
    )

merged = agebs.merge(pop_df, on="cve_ageb", how="left")
merged = merged.merge(place_df, on="cve_ageb", how="left").fillna(0)
print(f"Before A-filter: {len(merged)} rows")

# Show which rows would be removed
has_A = merged["cve_ageb"].str.contains("A", na=False)
print(f"Rows that CONTAIN 'A' (would be removed): {has_A.sum()}")
print("Sample cve_ageb values being removed:")
print(merged[has_A]["cve_ageb"].head(20).to_list())
print()

# What character positions have 'A'?
removed = merged[has_A]["cve_ageb"].head(30)
for v in removed:
    positions = [i for i, c in enumerate(str(v)) if c == 'A']
    print(f"  {v}  ->  A at positions {positions}")

# The cve_ageb structure: ENTIDAD(2) + MUN(3) + LOC(4) + AGEB(4) = 13 chars
# AGEB field is last 4 chars (positions 9-12).
# 'A' in AGEB means it's an area-level (non-urban) AGEB
print()
print("Length of cve_ageb values with A:", merged[has_A]["cve_ageb"].str.len().unique().tolist())
print("Length of cve_ageb values without A:", merged[~has_A]["cve_ageb"].str.len().unique().tolist())
