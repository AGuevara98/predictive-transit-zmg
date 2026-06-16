"""Diagnostic script for w1_trip_generation row count issue."""
import sys
import pandas as pd
import geopandas as gpd
from pathlib import Path
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import PG_URI, CRS_CANONICAL

ENGINE = create_engine(PG_URI)
ZMG_MUNS = {"039", "120", "098", "101", "097", "070", "044", "051", "124", "002"}

# Step 1: load_agebs
with ENGINE.raw_connection() as conn:
    gdf = gpd.read_postgis(
        "SELECT cvegeo AS cve_ageb, geom FROM base.ageb",
        conn, geom_col="geom", crs=CRS_CANONICAL
    )
gdf["area_km2"] = gdf.geometry.area / 1e6
agebs = gdf[["cve_ageb", "area_km2"]]
print(f"After load_agebs: {len(agebs)} rows")
dup = agebs["cve_ageb"].duplicated().sum()
print(f"  Duplicate cve_ageb in agebs: {dup}")

# Step 2: load_census_population
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
print(f"After load_census_population: {len(pop_df)} rows")
dup2 = pop_df["cve_ageb"].duplicated().sum()
print(f"  Duplicate cve_ageb in pop_df: {dup2}")
if dup2 > 0:
    dup_vals = pop_df[pop_df["cve_ageb"].duplicated(keep=False)]["cve_ageb"].unique()
    print(f"  Example dup cve_agebs: {dup_vals[:5]}")
    # Check why — look at LOC values for these
    dup_census = census[census["cve_ageb"].isin(dup_vals[:3])]
    print("  LOC values for duplicate agebs:")
    print(dup_census[["cve_ageb", "LOC", "AGEB", "MUN"]].head(10).to_string())

# Step 3: load_place_features
with ENGINE.raw_connection() as conn:
    place_df = pd.read_sql(
        "SELECT cve_ageb, p_employment_proxy, p_poi_density, p_retail_density FROM features.nppv_features",
        conn
    )
print(f"After load_place_features: {len(place_df)} rows")
dup3 = place_df["cve_ageb"].duplicated().sum()
print(f"  Duplicate cve_ageb in place_df: {dup3}")

# Merges
merged = agebs.merge(pop_df, on="cve_ageb", how="left")
print(f"After merge with pop_df: {len(merged)} rows")

merged2 = merged.merge(place_df, on="cve_ageb", how="left").fillna(0)
print(f"After merge with place_df: {len(merged2)} rows")

merged3 = merged2[~merged2["cve_ageb"].str.contains("A", na=False)].reset_index(drop=True)
print(f"After A-filter: {len(merged3)} rows")

# Check what AGEBs are in base.ageb but NOT in pop_df
agebs_set = set(agebs["cve_ageb"])
pop_set = set(pop_df["cve_ageb"])
missing_from_pop = agebs_set - pop_set
extra_in_pop = pop_set - agebs_set
print(f"\nAGEBs in base.ageb but NOT in pop_df: {len(missing_from_pop)}")
if missing_from_pop:
    print(f"  Examples: {list(missing_from_pop)[:5]}")
print(f"AGEBs in pop_df but NOT in base.ageb: {len(extra_in_pop)}")
if extra_in_pop:
    print(f"  Examples: {list(extra_in_pop)[:5]}")
