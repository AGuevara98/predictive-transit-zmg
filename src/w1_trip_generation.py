"""
W1.1 — Trip Generation
======================
Computes AGEB-level trip productions (from population) and attractions
(from employment/POI) using Tier-1 data only.

Output: features.ageb_trip_ends  (productions, attractions columns;
        vehicle_rate/transit_demand columns filled by w1_demand_surface.py)

Trip rate reference: INEGI MOTIV 2017 ZMG — avg 2.5 motorized trips/person/day.
"""
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI, CRS_CANONICAL

ENGINE = create_engine(PG_URI)

TRIP_RATE_PER_PERSON = 2.5
YOUTH_ADJ            = 0.10
EMPLOY_WEIGHT        = 1.8
POI_WEIGHT           = 0.5
RETAIL_WEIGHT        = 0.8

ZMG_MUNS = {"039", "120", "098", "101", "097", "070", "044", "051", "124", "002"}


def load_agebs() -> pd.DataFrame:
    print("[Step 1] Loading AGEB list...")
    with ENGINE.raw_connection() as conn:
        gdf = gpd.read_postgis(
            "SELECT cvegeo AS cve_ageb, geom FROM base.ageb",
            conn, geom_col="geom", crs=CRS_CANONICAL
        )
    gdf["area_km2"] = gdf.geometry.area / 1e6
    print(f"  [OK] {len(gdf):,} AGEBs loaded")
    return gdf[["cve_ageb", "area_km2"]]


def load_census_population(census_path: Path) -> pd.DataFrame:
    print("[Step 2] Loading census population data...")
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

    out = census[["cve_ageb"]].copy()
    out["pe_population"] = census["POBTOT"]
    out["pe_youth_share"] = census["P_15A29"] / census["POBTOT"].clip(lower=1)
    print(f"  [OK] Census data for {len(out):,} AGEBs")
    return out


def load_place_features() -> pd.DataFrame:
    # Raw (non-normalized) columns required: p_poi_density and p_retail_density are
    # in units of POIs/km2; compute_attractions() multiplies by area_km2 to recover counts.
    print("[Step 3] Loading place features from nppv_features...")
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(
            """SELECT cve_ageb, p_employment_proxy, p_poi_density, p_retail_density
               FROM features.nppv_features""",
            conn
        )
    print(f"  [OK] Place features for {len(df):,} AGEBs")
    return df


def compute_productions(merged: pd.DataFrame) -> pd.Series:
    rate = TRIP_RATE_PER_PERSON * (1 + YOUTH_ADJ * merged["pe_youth_share"])
    return (merged["pe_population"] * rate).clip(lower=0)


def compute_attractions(merged: pd.DataFrame) -> pd.Series:
    return (
        EMPLOY_WEIGHT  * merged["p_employment_proxy"]
        + POI_WEIGHT   * merged["p_poi_density"]    * merged["area_km2"]
        + RETAIL_WEIGHT * merged["p_retail_density"] * merged["area_km2"]
    ).clip(lower=0)


def write_trip_ends(df: pd.DataFrame):
    print("[Step 5] Writing trip ends to database...")  # Step 5 in main(): 1=load_agebs, 2=load_census, 3=load_place, 4=compute, 5=write
    records = df[["cve_ageb", "productions", "attractions"]].to_dict("records")
    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM features.ageb_trip_ends"))
        conn.execute(
            text("""INSERT INTO features.ageb_trip_ends (cve_ageb, productions, attractions)
                    VALUES (:cve_ageb, :productions, :attractions)"""),
            records
        )
    print(f"  [OK] {len(records):,} rows written to features.ageb_trip_ends")


def main():
    project_root = Path(__file__).parent.parent
    census_path = (
        project_root.parent / "gdl" / "ageb_mza_urbana_14_cpv2020_csv"
        / "ageb_mza_urbana_14_cpv2020" / "conjunto_de_datos"
        / "conjunto_de_datos_ageb_urbana_14_cpv2020.csv"
    )

    print("\n" + "="*70)
    print("W1.1 -- TRIP GENERATION")
    print("="*70)

    agebs    = load_agebs()
    pop_df   = load_census_population(census_path)
    place_df = load_place_features()

    print("[Step 4] Computing productions & attractions...")
    merged = agebs.merge(pop_df, on="cve_ageb", how="left")
    merged = merged.merge(place_df, on="cve_ageb", how="left").fillna(0)
    # NOTE: no A-suffix filter here. base.ageb is the authoritative AGEB list and already
    # contains the correct 2,068 rows (some legitimate INEGI AGEBs have cve_ageb ending in
    # 'A', e.g. '005A'). Filtering by 'A' would silently drop 187 valid AGEBs.

    merged["productions"] = compute_productions(merged)
    merged["attractions"] = compute_attractions(merged)

    # Scale attractions to equal total productions (required for doubly-constrained gravity)
    total_prod = merged["productions"].sum()
    total_attr = merged["attractions"].sum()
    if total_attr > 0:
        merged["attractions"] *= total_prod / total_attr

    print(f"  [OK] Total productions : {total_prod:,.0f}")
    print(f"  [OK] Total attractions : {merged['attractions'].sum():,.0f}")
    print(f"  [OK] Mean productions  : {merged['productions'].mean():,.1f}")

    write_trip_ends(merged)

    out_path = project_root / "outputs" / "w1"
    out_path.mkdir(parents=True, exist_ok=True)
    merged[["cve_ageb", "productions", "attractions"]].to_csv(
        out_path / "ageb_trip_ends.csv", index=False
    )
    print(f"  [OK] CSV -> outputs/w1/ageb_trip_ends.csv")

    print("\n" + "="*70)
    print("W1.1 TRIP GENERATION COMPLETE")
    print("="*70)
    print(merged[["productions", "attractions"]].describe().to_string())


if __name__ == "__main__":
    main()
