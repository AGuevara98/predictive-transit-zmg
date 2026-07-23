"""
Publication-quality thesis figures -> thesis/common/figures/*.pdf (vector).

Maps come from the live gdl_metro DB (base.ageb geometries + coverage gap +
corridors); charts come from committed CSVs in outputs/. Each figure is guarded
so one failure does not abort the rest. Re-run any time:

    python thesis/figures_src/make_thesis_figures.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
FIGDIR = ROOT / "thesis" / "common" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

# --- consistent, colorblind-safe style ----------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "pdf.fonttype": 42,
})
GAP_COLORS = {"High-gap": "#D55E00", "Medium-gap": "#CCCCCC", "Low-gap": "#0072B2"}
DIM_COLORS = {"NODE": "#0072B2", "PLACE": "#E69F00", "PEOPLE": "#009E73"}


def _save(fig, name):
    out = FIGDIR / name
    fig.savefig(out)
    plt.close(fig)
    print(f"  [OK] {out.relative_to(ROOT)}")


def _engine():
    from config import PG_URI
    from sqlalchemy import create_engine
    return create_engine(PG_URI)


# --- F1: pipeline overview -----------------------------------------------------
def fig_pipeline():
    stages = [
        ("W1", "Transit-demand\nsurface"), ("W2", "Survey\ncalibration"),
        ("W3", "Supply &\ncoverage gap"), ("W4", "NPP--People\nprioritization"),
        ("W5", "Multi-objective\nfunction"), ("W6", "Corridor\ngeneration"),
        ("W7", "Existing-route\naudit"), ("W8", "Validation"),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.axis("off")
    positions = [(0, 3), (1, 3), (2, 3), (3, 3), (3, 1.4), (2, 1.4), (1, 1.4), (0, 1.4)]
    w, h = 0.86, 0.92
    boxes = {}
    for (tag, label), (x, y) in zip(stages, positions):
        color = "#0072B2" if tag in ("W1", "W2", "W3", "W4") else "#CC79A7"
        box = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                             boxstyle="round,pad=0.02,rounding_size=0.08",
                             linewidth=1.2, edgecolor=color, facecolor=color + "22")
        ax.add_patch(box)
        ax.text(x, y + 0.18, tag, ha="center", va="center", fontweight="bold", fontsize=11, color=color)
        ax.text(x, y - 0.18, label, ha="center", va="center", fontsize=8)
        boxes[tag] = (x, y)
    order = ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"]
    for a, b in zip(order[:-1], order[1:]):
        (x0, y0), (x1, y1) = boxes[a], boxes[b]
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1),
                     arrowstyle="-|>", mutation_scale=12, shrinkA=26, shrinkB=26,
                     linewidth=1.0, color="#555555"))
    ax.text(1.5, 3.95, "Diagnostic layer", ha="center", fontsize=9, style="italic", color="#0072B2")
    ax.text(1.5, 0.42, "Generative \\& validation layer", ha="center", fontsize=9, style="italic", color="#CC79A7")
    ax.set_xlim(-0.7, 3.7); ax.set_ylim(0.2, 4.2)
    _save(fig, "pipeline.pdf")


# --- F2/F3: coverage-gap map (+ corridors overlay) -----------------------------
def fig_maps():
    import geopandas as gpd
    eng = _engine()
    with eng.connect() as c:
        agebs = gpd.read_postgis(
            "SELECT a.cvegeo, a.geom, g.gap_category "
            "FROM base.ageb a LEFT JOIN features.ageb_coverage_gap g ON g.cve_ageb=a.cvegeo",
            c, geom_col="geom")
        corr = gpd.read_postgis(
            "SELECT candidate_id, feasible, geom FROM features.route_candidates",
            c, geom_col="geom")
    agebs["color"] = agebs["gap_category"].map(GAP_COLORS).fillna("#EEEEEE")

    def _legend(ax):
        from matplotlib.patches import Patch
        ax.legend(handles=[Patch(facecolor=GAP_COLORS[k], edgecolor="white", label=k)
                           for k in ["High-gap", "Medium-gap", "Low-gap"]],
                  loc="lower left", frameon=False, fontsize=8)

    # F2 -- gap only
    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    agebs.plot(ax=ax, color=agebs["color"], edgecolor="white", linewidth=0.05)
    ax.set_axis_off(); _legend(ax)
    ax.set_title("Coverage-gap diagnosis, Guadalajara Metropolitan Area")
    _save(fig, "zmg_coverage_gap.pdf")

    # F3 -- gap + feasible corridors
    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    agebs.plot(ax=ax, color=agebs["color"], edgecolor="white", linewidth=0.05)
    feas = corr[corr["feasible"].astype(bool)]
    feas.plot(ax=ax, color="#111111", linewidth=2.4)
    for _, r in feas.iterrows():
        pt = r.geom.interpolate(0.5, normalized=True)
        ax.annotate(r["candidate_id"].replace("W6_", ""), (pt.x, pt.y),
                    fontsize=7, fontweight="bold", color="#111111",
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.8))
    ax.set_axis_off(); _legend(ax)
    ax.set_title("Generated feasible corridors over the coverage gap")
    _save(fig, "zmg_corridors.pdf")


# --- F4: W4 CRITIC/EWM weights -------------------------------------------------
def fig_weights():
    d = pd.read_csv(ROOT / "outputs/w4/nppv_w4_weights.csv").sort_values("ensemble_weight")
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    colors = d["dimension"].map(DIM_COLORS).fillna("#888888")
    ax.barh(d["feature"].str.replace("_n$", "", regex=True), d["ensemble_weight"], color=colors)
    ax.set_xlabel("Ensemble weight (CRITIC $\\times$ EWM)")
    ax.set_title("Node--Place--People objective weights")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=DIM_COLORS[k], label=k) for k in DIM_COLORS],
              loc="lower right", frameon=False, fontsize=8)
    _save(fig, "w4_weights.pdf")


# --- F5: W6 Pareto / feasibility ----------------------------------------------
def fig_pareto():
    d = pd.read_csv(ROOT / "outputs/w6/corridor_scores.csv")
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    for feas, sub in d.groupby("feasible"):
        ax.scatter(sub["route_km"], sub["f1_demand_gain"],
                   s=90, alpha=0.85,
                   color="#009E73" if feas else "#D55E00",
                   edgecolor="white", label="feasible" if feas else "infeasible")
    for _, r in d.iterrows():
        ax.annotate(r["candidate_id"].replace("W6_", ""), (r["route_km"], r["f1_demand_gain"]),
                    fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("Route length $f_2$ (km) -- minimize")
    ax.set_ylabel("Demand-weighted gain $f_1$ -- maximize")
    ax.set_title("Corridor candidates in objective space")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(alpha=0.25)
    _save(fig, "w6_pareto.pdf")


# --- F6: transfer comparison ---------------------------------------------------
def fig_transfer():
    d = pd.read_csv(ROOT / "outputs/w9/w9_w3_comparison.csv")
    d["short"] = d["city"].str.replace(r"\s*\(.*\)", "", regex=True)
    x = np.arange(len(d)); w = 0.26
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    ax.bar(x - w, d["high_gap_pct"], w, label="High-gap \\%", color="#D55E00")
    ax.bar(x, d["unserved_pct"], w, label="Unserved \\%", color="#999999")
    ax.bar(x + w, d["mean_vehicle_rate"] * 100, w, label="Vehicle rate \\%", color="#0072B2")
    ax.set_xticks(x); ax.set_xticklabels(d["short"])
    ax.set_ylabel("Percent")
    ax.set_title("Diagnostic transfer across three metropolitan areas")
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.10))
    _save(fig, "transfer_highgap.pdf")


def main():
    print("Generating thesis figures ->", FIGDIR.relative_to(ROOT))
    for fn in (fig_pipeline, fig_weights, fig_pareto, fig_transfer, fig_maps):
        try:
            fn()
        except Exception as e:
            print(f"  [ERR] {fn.__name__}: {e!r}")
    print("Done.")


if __name__ == "__main__":
    main()
