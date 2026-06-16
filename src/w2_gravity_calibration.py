"""
W2.2/W2.3/W2.4 -- Gravity Model Calibration
=============================================
Calibrates the W1 gravity model beta parameter against EOD 2022 observed
OD desire lines.

Steps:
  W2.2  Spatial join EOD zones -> base.ageb; aggregate modeled AGEB OD
        flows to zone level.
  W2.3  Fit beta via scipy.optimize.minimize_scalar minimising sum of
        squared log-errors on zone-pair flows.
  W2.4  Write outputs:
          outputs/w2/calibration_report.md
          outputs/w2/zone_od_comparison.csv
          features.w2_calibration (DB row)

Resolution note: EOD zones are larger than AGEBs (typically 10-50 AGEBs
per zone). AGEB-level modeled flows are summed to zone level for comparison.
This introduces an aggregation bias that is documented in the report.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.optimize import minimize_scalar
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI, CRS_CANONICAL

ENGINE = create_engine(PG_URI)

BETA_W1           = 2.0
MIN_OBSERVED_FLOW = 100   # zone pairs below this are too noisy for log-error fitting
BETA_SEARCH_LO    = 0.5
BETA_SEARCH_HI    = 5.0
LOG_ERR_FLOOR     = 1e-6  # prevents log(0) in objective


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_eod_zones() -> gpd.GeoDataFrame:
    print("[Step 1] Loading EOD zones from raw.eod_zones...")
    with ENGINE.raw_connection() as conn:
        gdf = gpd.read_postgis(
            "SELECT zone_id, zone_name, productions, attractions, geom FROM raw.eod_zones",
            conn, geom_col="geom", crs=CRS_CANONICAL
        )
    if gdf.empty:
        raise RuntimeError("raw.eod_zones is empty -- run w2_eod_ingest.py first")
    print(f"  [OK] {len(gdf)} zones loaded")
    return gdf


def load_desire_lines() -> pd.DataFrame:
    print("[Step 2] Loading observed desire lines from raw.eod_desire_lines...")
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(
            "SELECT origin_zone, dest_zone, observed_flow FROM raw.eod_desire_lines",
            conn
        )
    if df.empty:
        raise RuntimeError("raw.eod_desire_lines is empty -- run w2_eod_ingest.py first")
    print(f"  [OK] {len(df)} OD pairs; total flow = {df['observed_flow'].sum():,.0f}")
    return df


def load_ageb_od() -> pd.DataFrame:
    print("[Step 3] Loading W1 AGEB OD matrix...")
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(
            """SELECT origin_cve_ageb, dest_cve_ageb, dist_m, modeled_flow
               FROM features.ageb_od_matrix""",
            conn
        )
    if df.empty:
        raise RuntimeError("features.ageb_od_matrix is empty -- run run_w1.py first")
    print(f"  [OK] {len(df):,} AGEB OD pairs loaded")
    return df


def load_ageb_trip_ends() -> pd.DataFrame:
    print("[Step 4] Loading AGEB trip ends...")
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(
            "SELECT cve_ageb, productions, attractions FROM features.ageb_trip_ends",
            conn
        )
    print(f"  [OK] {len(df):,} AGEBs")
    return df


def load_ageb_centroids() -> gpd.GeoDataFrame:
    print("[Step 5] Loading AGEB centroids...")
    with ENGINE.raw_connection() as conn:
        gdf = gpd.read_postgis(
            "SELECT cvegeo AS cve_ageb, ST_Centroid(geom) AS geom FROM base.ageb",
            conn, geom_col="geom", crs=CRS_CANONICAL
        )
    print(f"  [OK] {len(gdf)} centroids")
    return gdf


# ---------------------------------------------------------------------------
# W2.2 -- Zone-AGEB spatial join and flow aggregation
# ---------------------------------------------------------------------------

def build_zone_ageb_lookup(
    zones: gpd.GeoDataFrame,
    ageb_centroids: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """
    Spatial join: assign each AGEB centroid to the EOD zone that contains it.
    Returns a DataFrame with columns [cve_ageb, zone_id].

    AGEBs that fall outside all zones (edge cases) are dropped with a WARN.
    """
    print("\n[Step 6] Spatial join: AGEB centroids -> EOD zones...")

    # gpd.sjoin requires both frames to have the same active geometry column name
    zones_for_join = zones[["zone_id", "geom"]].copy().set_geometry("geom")

    joined = gpd.sjoin(
        ageb_centroids,
        zones_for_join,
        how="left",
        predicate="within",
    )
    unmatched = joined["zone_id"].isna().sum()
    if unmatched > 0:
        print(f"  [WARN] {unmatched} AGEB centroids fall outside all EOD zones and will be excluded")
    joined = joined.dropna(subset=["zone_id"])
    print(f"  [OK] {len(joined)} AGEBs matched to {joined['zone_id'].nunique()} zones")
    return joined[["cve_ageb", "zone_id"]].reset_index(drop=True)


def aggregate_od_to_zones(
    ageb_od: pd.DataFrame,
    lookup: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate AGEB-level modeled OD flows to zone level.
    T_zone(i,j) = sum of T_ageb(a,b) for all AGEBs a in zone i, b in zone j.
    Also compute mean centroid-to-centroid dist_m for each zone pair.
    """
    print("\n[Step 7] Aggregating AGEB flows to zone level...")
    od = ageb_od.merge(
        lookup.rename(columns={"cve_ageb": "origin_cve_ageb", "zone_id": "origin_zone"}),
        on="origin_cve_ageb", how="inner"
    )
    od = od.merge(
        lookup.rename(columns={"cve_ageb": "dest_cve_ageb", "zone_id": "dest_zone"}),
        on="dest_cve_ageb", how="inner"
    )
    # Drop intra-zone flows (not relevant for inter-zonal calibration)
    od = od[od["origin_zone"] != od["dest_zone"]]

    zone_od = od.groupby(["origin_zone", "dest_zone"]).agg(
        modeled_flow_w1=("modeled_flow", "sum"),
        mean_dist_m=("dist_m", "mean"),
    ).reset_index()

    print(f"  [OK] {len(zone_od):,} zone-pair flows aggregated "
          f"(mean modeled flow = {zone_od['modeled_flow_w1'].mean():,.1f})")
    return zone_od


def merge_observed_modeled(
    zone_od: pd.DataFrame,
    desire_lines: pd.DataFrame,
) -> pd.DataFrame:
    """
    Inner join observed desire lines with aggregated modeled flows.
    Only pairs with observed_flow >= MIN_OBSERVED_FLOW are kept for fitting.
    """
    print("\n[Step 8] Merging observed and modeled zone OD...")
    combined = desire_lines.merge(zone_od, on=["origin_zone", "dest_zone"], how="inner")
    before = len(combined)
    combined = combined[combined["observed_flow"] >= MIN_OBSERVED_FLOW]
    print(f"  [OK] {len(combined)} zone pairs available for calibration "
          f"(dropped {before - len(combined)} pairs below {MIN_OBSERVED_FLOW} trip threshold)")
    if len(combined) < 10:
        print(f"  [WARN] Very few calibration pairs ({len(combined)}); "
              "beta estimate may be unreliable. Check zone ID alignment between "
              "raw.eod_zones and raw.eod_desire_lines.")
    return combined.reset_index(drop=True)


# ---------------------------------------------------------------------------
# W2.3 -- Zone-level gravity model and beta calibration
# ---------------------------------------------------------------------------

def zone_productions_attractions(
    trip_ends: pd.DataFrame,
    lookup: pd.DataFrame,
) -> tuple:
    """
    Sum AGEB productions/attractions to zone level using the zone-AGEB lookup.
    Returns (zone_productions, zone_attractions) as pd.Series indexed by zone_id.
    """
    ageb_zones = trip_ends.merge(lookup, on="cve_ageb", how="inner")
    zone_prod = ageb_zones.groupby("zone_id")["productions"].sum()
    zone_attr = ageb_zones.groupby("zone_id")["attractions"].sum()
    return zone_prod, zone_attr


def modeled_zone_flow_beta(
    dist_km: np.ndarray,
    prod_i: np.ndarray,
    attr_j: np.ndarray,
    beta: float,
) -> np.ndarray:
    """
    Compute unconstrained gravity model flows at zone level for a given beta.

    T_ij = P_i * d_ij^(-beta) * A_j

    This is the singly-unconstrained form. Because we cannot easily re-run
    Furness IPF at zone level with partial zone-pair coverage, we use the
    proportional (unconstrained) form for calibration and scale the result
    so that sum(T_ij_model) == sum(T_ij_observed) across calibration pairs.
    The objective is the log-ratio, so the scaling constant cancels out when
    comparing shapes; the fit captures the decay slope (beta), not the level.

    dist_km: array of inter-zone centroid distances in km (must be > 0)
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        f = np.where(dist_km > 0, dist_km ** (-beta), 0.0)
    return prod_i * f * attr_j


def log_sse_objective(
    beta: float,
    dist_km: np.ndarray,
    prod_i: np.ndarray,
    attr_j: np.ndarray,
    obs: np.ndarray,
) -> float:
    """
    Sum of squared log-errors: sum((log(T_model_scaled) - log(T_obs))^2).

    The raw model T_ij = P_i * d^(-beta) * A_j uses absolute trip-end volumes,
    producing flows 10^5 larger than observed zone-pair flows (because productions
    and attractions are not normalized to match the observed total). This creates
    a constant log-level offset (~12 log units) that dominates the SSE and drives
    the optimizer to the beta upper boundary regardless of shape fit.

    Fix: normalize T_model to the same total as T_obs before comparing in log-space.
    This isolates the SHAPE of the distance-decay (what beta controls) from the
    LEVEL (which is absorbed by the doubly-constrained Furness balancing in W1 and
    is not a function of beta).
    """
    t_model = modeled_zone_flow_beta(dist_km, prod_i, attr_j, beta)
    total_model = t_model.sum()
    if total_model > 0:
        t_model = t_model * (obs.sum() / total_model)
    mask = (t_model > LOG_ERR_FLOOR) & (obs > LOG_ERR_FLOOR)
    if mask.sum() == 0:
        return 1e12
    log_err = np.log(t_model[mask]) - np.log(obs[mask])
    return float(np.sum(log_err ** 2))


def calibrate_beta(
    combined: pd.DataFrame,
    zone_prod: pd.Series,
    zone_attr: pd.Series,
) -> dict:
    """
    Fit beta to minimise log-SSE. Returns a dict with calibrated beta and
    goodness-of-fit metrics.
    """
    print("\n[Step 9] Calibrating beta via scipy.optimize.minimize_scalar...")

    combined = combined.copy()
    combined["prod_i"] = combined["origin_zone"].map(zone_prod).fillna(1.0)
    combined["attr_j"] = combined["dest_zone"].map(zone_attr).fillna(1.0)
    combined["dist_km"] = combined["mean_dist_m"] / 1000.0

    # Guard against zero distances (same centroid edge case)
    combined = combined[combined["dist_km"] > 0.01]
    if combined.empty:
        raise RuntimeError("All zone-pair distances are zero; cannot calibrate beta.")

    dist_km = combined["dist_km"].values
    prod_i  = combined["prod_i"].values
    attr_j  = combined["attr_j"].values
    obs     = combined["observed_flow"].values

    result = minimize_scalar(
        log_sse_objective,
        bounds=(BETA_SEARCH_LO, BETA_SEARCH_HI),
        method="bounded",
        args=(dist_km, prod_i, attr_j, obs),
    )

    beta_cal = float(result.x)
    print(f"  [OK] Calibrated beta = {beta_cal:.4f}  (W1 prior = {BETA_W1})")

    if abs(beta_cal - BETA_W1) > 0.5:
        print(f"  [WARN] Calibrated beta differs from W1 prior by "
              f"{abs(beta_cal - BETA_W1):.2f}. Consider rerunning W1.2 with "
              f"BETA = {beta_cal:.2f} in src/w1_gravity_model.py.")
    else:
        print(f"  [OK] Calibrated beta is close to W1 prior "
              f"(diff={abs(beta_cal - BETA_W1):.3f}); W1 estimates remain valid.")

    # Goodness-of-fit at calibrated and W1 betas
    t_cal = modeled_zone_flow_beta(dist_km, prod_i, attr_j, beta_cal)
    t_w1  = modeled_zone_flow_beta(dist_km, prod_i, attr_j, BETA_W1)

    mask_pos = (t_cal > 0) & (t_w1 > 0) & (obs > 0)
    n_pairs  = int(mask_pos.sum())

    # Scale modeled to observed totals for RMSE (removes level offset, isolates shape)
    def scale_to_obs(t, o):
        s = o.sum() / t.sum() if t.sum() > 0 else 1.0
        return t * s

    t_cal_s = scale_to_obs(t_cal[mask_pos], obs[mask_pos])
    t_w1_s  = scale_to_obs(t_w1[mask_pos],  obs[mask_pos])
    obs_pos = obs[mask_pos]

    rmse_cal = float(np.sqrt(np.mean((t_cal_s - obs_pos) ** 2)))
    rmse_w1  = float(np.sqrt(np.mean((t_w1_s  - obs_pos) ** 2)))

    ss_res = np.sum((obs_pos - t_cal_s) ** 2)
    ss_tot = np.sum((obs_pos - obs_pos.mean()) ** 2)
    r2     = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    print(f"  Calibrated: RMSE={rmse_cal:,.1f}  R²={r2:.4f}  n_pairs={n_pairs}")
    print(f"  W1 (beta=2.0): RMSE={rmse_w1:,.1f}")

    comparison = combined[mask_pos][
        ["origin_zone", "dest_zone", "dist_km", "observed_flow"]
    ].copy()
    comparison["modeled_flow_beta20"]     = t_w1_s
    comparison["modeled_flow_calibrated"] = t_cal_s

    return {
        "beta_calibrated" : beta_cal,
        "beta_w1"         : BETA_W1,
        "n_pairs"         : n_pairs,
        "rmse_log_sse"    : float(result.fun),
        "rmse_cal"        : rmse_cal,
        "rmse_w1"         : rmse_w1,
        "r2"              : r2,
        "comparison_df"   : comparison,
    }


# ---------------------------------------------------------------------------
# W2.4 -- Write outputs
# ---------------------------------------------------------------------------

def write_calibration_to_db(metrics: dict):
    print("\n[Step 10] Writing calibration result to features.w2_calibration...")
    with ENGINE.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO features.w2_calibration
                    (beta_w1, beta_calibrated, n_pairs, rmse_log, r2, notes)
                VALUES
                    (:beta_w1, :beta_calibrated, :n_pairs, :rmse_log, :r2, :notes)
            """),
            {
                "beta_w1"         : metrics["beta_w1"],
                "beta_calibrated" : metrics["beta_calibrated"],
                "n_pairs"         : metrics["n_pairs"],
                "rmse_log"        : metrics["rmse_log_sse"],
                "r2"              : metrics["r2"],
                "notes"           : (
                    f"W1 prior beta={metrics['beta_w1']}; "
                    f"calibrated against {metrics['n_pairs']} EOD 2022 zone OD pairs "
                    f"(flow >= {MIN_OBSERVED_FLOW} trips); "
                    f"RMSE (scaled) cal={metrics['rmse_cal']:.1f} "
                    f"vs W1={metrics['rmse_w1']:.1f}"
                ),
            }
        )
    print("  [OK] Calibration result persisted")


def write_comparison_csv(comparison: pd.DataFrame, out_dir: Path):
    csv_path = out_dir / "zone_od_comparison.csv"
    comparison.to_csv(csv_path, index=False, float_format="%.2f")
    print(f"  [OK] Comparison CSV -> {csv_path}")


def write_calibration_report(metrics: dict, n_zones: int, n_desire_pairs: int, out_dir: Path):
    beta_cal = metrics["beta_calibrated"]
    delta    = abs(beta_cal - BETA_W1)
    if delta <= 0.3:
        verdict = (
            f"The calibrated beta ({beta_cal:.4f}) is close to the W1 prior (2.0). "
            "The W1 demand surface is validated; rerunning W1.2 is not necessary."
        )
    else:
        verdict = (
            f"The calibrated beta ({beta_cal:.4f}) differs from the W1 prior ({BETA_W1}) by "
            f"{delta:.2f}. This indicates ZMG commuters travel longer distances (weaker "
            f"distance decay) than the W1 prior assumed. Consider rerunning W1.2 with "
            f"`BETA = {beta_cal:.2f}` in `src/w1_gravity_model.py` for a calibrated demand "
            f"surface, then rerunning W3 and downstream workstreams. "
            f"The relative prioritization ordering (W4/W6/W7) is robust to this change "
            f"since it depends on demand ratios, not absolute values."
        )

    report = f"""# W2 Gravity Model Calibration Report

## Summary

| Metric | Value |
|--------|-------|
| W1 prior beta | {BETA_W1} |
| Calibrated beta | {beta_cal:.4f} |
| Delta (|cal - prior|) | {delta:.4f} |
| Zone-pair calibration pairs | {metrics['n_pairs']} |
| Log-space SSE at calibrated beta | {metrics['rmse_log_sse']:.4f} |
| RMSE (scaled, calibrated) | {metrics['rmse_cal']:,.1f} trips |
| RMSE (scaled, W1 beta=2.0) | {metrics['rmse_w1']:,.1f} trips |
| R² (calibrated) | {metrics['r2']:.4f} |

## Verdict

{verdict}

## Data Sources

- **EOD 2022 zones:** {n_zones} survey zones from `Zonificacion de la Encuesta Origen-Destino.zip`
- **Observed desire lines:** {n_desire_pairs} zone OD pairs from the two desire-line zips
  (range 5,000-47,555 trips per pair; only pairs >= {MIN_OBSERVED_FLOW} trips used for fitting)
- **Modeled OD:** `features.ageb_od_matrix` (W1 doubly-constrained gravity, Euclidean distances)

## Methodology

1. **Zone-AGEB spatial join** (W2.2): Each AGEB centroid was assigned to the EOD survey zone
   containing it. AGEB-level modeled flows were summed to zone level (`T_zone(i,j) = sum T_ageb`).

2. **Beta fitting** (W2.3): `scipy.optimize.minimize_scalar` (bounded Brent method) minimised
   the sum of squared log-errors across zone OD pairs:

   `min_beta sum[ log(T_ij_model_scaled(beta)) - log(T_ij_observed) ]^2`

   The log-space objective treats proportional errors equally across low- and high-flow pairs.
   The unconstrained gravity formula `T_ij = P_i x d_ij^(-beta) x A_j` was used at zone level
   (Furness IPF balancing is omitted at zone level due to partial zone-pair coverage). Before
   computing log-errors, **T_ij_model is rescaled so that sum(T_model) == sum(T_observed)**.
   This normalization is essential: the raw unconstrained model produces flows 10^5 larger than
   observed zone OD pairs (because AGEB-level productions are absolute trip volumes, not
   normalized to match zone-pair counts). Without this step the optimizer sees a constant
   ~12 log-unit level offset and drives beta to the search boundary regardless of shape fit.
   The scaling isolates the SHAPE of the distance decay (which is what beta controls) from
   the LEVEL (which is handled by the doubly-constrained Furness balancing in W1).
   Both scaled modeled and observed flows are also used for RMSE and R² computation.

3. **Distance metric:** Mean Euclidean centroid-to-centroid distance (metres, EPSG:6372) across
   all AGEB pairs in each zone pair. This is the same metric used in W1.

## Caveats and Limitations

- **Resolution mismatch:** EOD zones are survey aggregations containing 10-50 AGEBs each.
  Zone-level modeled flows are sums of AGEB-level flows, not a zone-native gravity model.
  This aggregation bias means the calibrated beta may absorb zone-size effects. A proper
  calibration would rerun Furness IPF at zone resolution (feasible once zone trip ends
  are confirmed from the tabular EOD files).

- **Euclidean proxy:** W1 and W2 both use Euclidean (straight-line) distances. EOD surveys
  record actual travel times. If network travel time data becomes available (e.g. OSRM or
  osmnx routing), the calibration should be repeated with time-based impedance.

- **Total trips (all modes):** Observed desire-line flows include all motorised modes (transit,
  car, taxi, etc.). This is correct because the gravity model distributes total person trips;
  W1.3 then applies zone-level transit propensity weights derived from vehicle ownership.

- **Desire-line threshold:** Only zone pairs with >= {MIN_OBSERVED_FLOW} observed trips are used
  for fitting. Low-flow pairs are excluded because their log-errors are dominated by noise
  relative to the structural distance-decay signal.

## Comparison CSV

`outputs/w2/zone_od_comparison.csv` contains one row per calibration pair with columns:
`origin_zone`, `dest_zone`, `dist_km`, `observed_flow`,
`modeled_flow_beta20`, `modeled_flow_calibrated`.
"""

    report_path = out_dir / "calibration_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  [OK] Calibration report -> {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\n" + "="*70)
    print("W2.2/W2.3/W2.4 -- GRAVITY MODEL CALIBRATION")
    print("="*70)

    zones     = load_eod_zones()
    desire    = load_desire_lines()
    ageb_od   = load_ageb_od()
    trip_ends = load_ageb_trip_ends()
    centroids = load_ageb_centroids()

    lookup   = build_zone_ageb_lookup(zones, centroids)
    zone_od  = aggregate_od_to_zones(ageb_od, lookup)
    combined = merge_observed_modeled(zone_od, desire)

    zone_prod, zone_attr = zone_productions_attractions(trip_ends, lookup)

    metrics = calibrate_beta(combined, zone_prod, zone_attr)

    out_dir = Path(__file__).parent.parent / "outputs" / "w2"
    out_dir.mkdir(parents=True, exist_ok=True)

    write_calibration_to_db(metrics)
    write_comparison_csv(metrics["comparison_df"], out_dir)
    write_calibration_report(
        metrics,
        n_zones=len(zones),
        n_desire_pairs=len(desire),
        out_dir=out_dir,
    )

    print("\n" + "="*70)
    print("W2 GRAVITY MODEL CALIBRATION COMPLETE")
    print("="*70)
    print(f"  Calibrated beta     : {metrics['beta_calibrated']:.4f}")
    print(f"  W1 prior            : {BETA_W1}")
    print(f"  R² (calibrated)     : {metrics['r2']:.4f}")
    print(f"  n calibration pairs : {metrics['n_pairs']}")


if __name__ == "__main__":
    main()
