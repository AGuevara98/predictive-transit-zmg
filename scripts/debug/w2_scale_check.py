"""Diagnostic: W2 calibration scale analysis and fix simulation"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.optimize import minimize_scalar
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)

df = pd.read_csv("outputs/w2/zone_od_comparison.csv")
print("N pairs:", len(df))

print()
print("=== SHAPE QUALITY AT BETA=2.0 ===")
log_ratio = np.log(df.modeled_flow_beta20 + 1) - np.log(df.observed_flow + 1)
print("log-ratio mean={:.4f} std={:.4f}".format(log_ratio.mean(), log_ratio.std()))
print("Corr (log obs vs log mod_beta20):", round(float(np.corrcoef(
    np.log(df.observed_flow + 1), np.log(df.modeled_flow_beta20 + 1))[0, 1]), 4))
print("Corr (linear):", round(df[["observed_flow","modeled_flow_beta20"]].corr().iloc[0,1], 4))

print()
df["dist_bin"] = pd.cut(df.dist_km, bins=[0, 3, 6, 10, 20, 100],
                         labels=["0-3km", "3-6km", "6-10km", "10-20km", "20+km"])
print("=== BY DISTANCE BIN ===")
g = df.groupby("dist_bin").agg(
    n=("observed_flow", "count"),
    obs_mean=("observed_flow", "mean"),
    mod_mean=("modeled_flow_beta20", "mean"),
)
g["ratio_mod_obs"] = g["mod_mean"] / g["obs_mean"]
print(g.to_string())

# Now reconstruct the unscaled flows to show the scale bug
# The calibration uses: T_model = prod_i * dist^(-beta) * attr_j (unscaled)
# We need zone productions/attractions used in calibration
with ENGINE.raw_connection() as conn:
    trip_ends = pd.read_sql(
        "SELECT cve_ageb, productions, attractions FROM features.ageb_trip_ends", conn)
    centroids = pd.read_sql(
        "SELECT cvegeo AS cve_ageb, zone_id FROM base.ageb ba "
        "JOIN raw.eod_zones ez ON ST_Within(ST_Centroid(ba.geom), ez.geom) "
        "WHERE ez.zone_id IS NOT NULL", conn)

# Aggregate AGEB productions to zone level (as done in calibration)
if not centroids.empty:
    ageb_zones = trip_ends.merge(centroids, on="cve_ageb", how="inner")
    zone_prod = ageb_zones.groupby("zone_id")["productions"].sum()
    zone_attr = ageb_zones.groupby("zone_id")["attractions"].sum()

    print()
    print("=== ZONE PRODUCTIONS (aggregated from AGEB W1) ===")
    print("Count:", len(zone_prod))
    print("Min={:.0f} Max={:.0f} Mean={:.0f} Sum={:.0f}".format(
        zone_prod.min(), zone_prod.max(), zone_prod.mean(), zone_prod.sum()))

    # Compute example unscaled T_ij for a sample pair
    sample = df.head(10).copy()
    P = sample["origin_zone"].map(zone_prod).fillna(1.0)
    A = sample["dest_zone"].map(zone_attr).fillna(1.0)
    d_km = sample["dist_km"]
    T_raw = P.values * (d_km.values ** -2.0) * A.values
    T_obs = sample["observed_flow"].values

    print()
    print("=== RAW (UNSCALED) FLOW SCALE FOR FIRST 10 PAIRS ===")
    for i in range(min(5, len(sample))):
        print(f"  pair {i}: P={P.iloc[i]:.0f} A={A.iloc[i]:.0f} d={d_km.iloc[i]:.2f}km "
              f"T_raw={T_raw[i]:.0e} T_obs={T_obs[i]:.0f} ratio={T_raw[i]/T_obs[i]:.0f}x")

    print()
    print("=== THE BUG: LOG-LEVEL OFFSET ===")
    mask = (T_raw > 0) & (T_obs > 0)
    if mask.any():
        log_level_offset = np.log(T_raw[mask]) - np.log(T_obs[mask])
        print("log(T_raw) - log(T_obs): mean={:.2f} (should be ~0 for shape-only fit)".format(
            log_level_offset.mean()))
        print("This constant offset ({:.1f} log units) dominates the SSE,".format(log_level_offset.mean()))
        print("pushing optimizer to increase beta to reduce T_raw, hitting boundary at 5.0.")

# Simulate calibration WITH fix (scaled log-SSE)
print()
print("=== SIMULATING CALIBRATION WITH FIX (scaled log-SSE) ===")
# Use the already-scaled modeled flows (modeled_flow_beta20) as a shape proxy
# Re-scale at different betas
obs = df["observed_flow"].values
dist = df["dist_km"].values

# Use shape from modeled_flow_beta20 divided by d^(-2.0) to get P*A, then recompute at new beta
# proxy: T_shape = T_beta20_scaled * d^2.0  (remove old beta=2 decay)
T_beta20_scaled = df["modeled_flow_beta20"].values
PA_proxy = T_beta20_scaled * (dist ** 2.0)  # undo old beta=2 decay

LOG_ERR_FLOOR = 1e-6

def log_sse_fixed(beta, PA, d, obs_arr):
    t_model = PA * (d ** (-beta))
    total = t_model.sum()
    if total > 0:
        t_model = t_model * (obs_arr.sum() / total)
    mask = (t_model > LOG_ERR_FLOOR) & (obs_arr > LOG_ERR_FLOOR)
    if mask.sum() == 0:
        return 1e12
    log_err = np.log(t_model[mask]) - np.log(obs_arr[mask])
    return float(np.sum(log_err ** 2))

# Scan beta to see the objective landscape
betas = np.arange(0.5, 5.01, 0.25)
sse_vals = [log_sse_fixed(b, PA_proxy, dist, obs) for b in betas]

print("Beta  -> log-SSE (fixed/scaled objective):")
for b, s in zip(betas, sse_vals):
    marker = " <-- minimum" if s == min(sse_vals) else ""
    print(f"  beta={b:.2f}  SSE={s:.1f}{marker}")

result = minimize_scalar(log_sse_fixed, bounds=(0.5, 5.0), method="bounded",
                          args=(PA_proxy, dist, obs))
print()
print("Optimized beta (scaled objective):", round(result.x, 4))
print("W1 prior beta: 2.0")
print("Original buggy calibration beta: 5.0")
