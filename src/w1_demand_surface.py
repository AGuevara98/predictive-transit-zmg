"""
W1.3 -- Transit-Demand Surface
==============================
Down-weights modeled OD demand in high vehicle-ownership zones using
CPV2020 VPH_AUTOM / VIVPAR_HAB data per AGEB.

Output: updates features.ageb_trip_ends with
        vehicle_rate, transit_propensity, transit_demand.
"""
import sys
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)
ZMG_MUNS = {"039", "120", "098", "101", "097", "070", "044", "051", "124", "002"}


def load_vehicle_ownership(census_path: Path) -> pd.DataFrame:
    # VPH_AUTOM = dwellings with automobile; VIVPAR_HAB = occupied private dwellings
    print("[Step 1] Loading vehicle-ownership data from CPV2020...")
    census = pd.read_csv(census_path, dtype=str, encoding="latin-1")
    census = census[census["MZA"] == "000"].copy()
    census["cve_ageb"] = (
        census["ENTIDAD"].str.zfill(2)
        + census["MUN"].str.zfill(3)
        + census["LOC"].str.zfill(4)
        + census["AGEB"].str.zfill(4)
    )
    census = census[census["MUN"].isin(ZMG_MUNS)].copy()

    for col in ["VPH_AUTOM", "VIVPAR_HAB"]:
        if col not in census.columns:
            print(f"  [WARN] Column {col} not found in CPV2020 CSV; defaulting to 0")
            census[col] = "0"
        census[col] = pd.to_numeric(census[col], errors="coerce").fillna(0)

    out = census[["cve_ageb"]].copy()
    out["vehicle_rate"] = (
        census["VPH_AUTOM"] / census["VIVPAR_HAB"].clip(lower=1)
    ).clip(0, 1)

    print(f"  [OK] {len(out):,} AGEBs, mean vehicle_rate={out['vehicle_rate'].mean():.3f}")
    return out[["cve_ageb", "vehicle_rate"]]


def aggregate_od_to_ageb() -> pd.DataFrame:
    print("[Step 2] Aggregating OD matrix flows to AGEB level...")
    with ENGINE.raw_connection() as conn:
        produced = pd.read_sql(
            "SELECT origin_cve_ageb AS cve_ageb, SUM(modeled_flow) AS produced_flow "
            "FROM features.ageb_od_matrix GROUP BY origin_cve_ageb", conn
        )
        attracted = pd.read_sql(
            "SELECT dest_cve_ageb AS cve_ageb, SUM(modeled_flow) AS attracted_flow "
            "FROM features.ageb_od_matrix GROUP BY dest_cve_ageb", conn
        )
        base = pd.read_sql("SELECT cve_ageb FROM features.ageb_trip_ends", conn)

    df = (
        base
        .merge(produced,  on="cve_ageb", how="left")
        .merge(attracted, on="cve_ageb", how="left")
        .fillna(0)
    )
    df["total_demand"] = df["produced_flow"] + df["attracted_flow"]
    print(f"  [OK] Mean total demand per AGEB: {df['total_demand'].mean():,.1f}")
    return df[["cve_ageb", "total_demand"]]


def compute_transit_demand(demand_df: pd.DataFrame, vehicle_df: pd.DataFrame) -> pd.DataFrame:
    merged = demand_df.merge(vehicle_df, on="cve_ageb", how="left")
    fill_rate = merged["vehicle_rate"].mean()
    merged["vehicle_rate"]       = merged["vehicle_rate"].fillna(fill_rate)
    merged["transit_propensity"] = (1.0 - merged["vehicle_rate"]).clip(0, 1)
    merged["transit_demand"]     = merged["total_demand"] * merged["transit_propensity"]
    return merged


def write_demand_surface(df: pd.DataFrame):
    print("[Step 4] Updating features.ageb_trip_ends...")
    records = df[["vehicle_rate", "transit_propensity", "transit_demand", "cve_ageb"]].to_dict("records")
    with ENGINE.begin() as conn:
        conn.execute(
            text("""UPDATE features.ageb_trip_ends
                    SET vehicle_rate       = :vehicle_rate,
                        transit_propensity = :transit_propensity,
                        transit_demand     = :transit_demand
                    WHERE cve_ageb = :cve_ageb"""),
            records
        )
        updated = conn.execute(
            text("SELECT COUNT(*) FROM features.ageb_trip_ends WHERE transit_demand IS NOT NULL")
        ).scalar()
    if updated != len(records):
        raise RuntimeError(f"Expected {len(records)} rows updated, but only {updated} have transit_demand set.")
    print(f"  [OK] {updated:,} rows updated")


def main():
    project_root = Path(__file__).parent.parent
    census_path = (
        project_root.parent / "gdl" / "ageb_mza_urbana_14_cpv2020_csv"
        / "ageb_mza_urbana_14_cpv2020" / "conjunto_de_datos"
        / "conjunto_de_datos_ageb_urbana_14_cpv2020.csv"
    )

    print("\n" + "="*70)
    print("W1.3 -- TRANSIT-DEMAND SURFACE")
    print("="*70)

    vehicle_df = load_vehicle_ownership(census_path)
    demand_df  = aggregate_od_to_ageb()

    print("[Step 3] Computing transit demand...")
    result = compute_transit_demand(demand_df, vehicle_df)
    print(f"  [OK] Mean transit_propensity : {result['transit_propensity'].mean():.3f}")
    print(f"  [OK] Mean transit_demand     : {result['transit_demand'].mean():,.1f}")

    write_demand_surface(result)

    out_path = project_root / "outputs" / "w1"
    out_path.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path / "ageb_demand_surface.csv", index=False)
    print(f"  [OK] CSV -> outputs/w1/ageb_demand_surface.csv")

    print("\n" + "="*70)
    print("W1.3 TRANSIT DEMAND SURFACE COMPLETE")
    print("="*70)
    print(result[["total_demand", "vehicle_rate", "transit_propensity", "transit_demand"]].describe().to_string())


if __name__ == "__main__":
    main()
