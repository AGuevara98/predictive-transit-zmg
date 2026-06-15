# W4 — NPP Prioritization Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the W4 NPP prioritization layer — re-run CRITIC/EWM on 14 NODE+PLACE+PEOPLE features, compute an equity-adjusted prioritization score per AGEB, and produce a DB table, GeoJSON, charts, cluster profiles, and a markdown report.

**Architecture:** New `src/w4_prioritization.py` module with pure computation functions (CRITIC, EWM, score assembly) and output writers. `src/run_w4.py` orchestrator runs a DDL migration then calls the module, matching the W1/W2/W3 pattern. `features.nppv_weights` (Phase 3 historical record) is untouched; W4 writes its own `features.nppv_w4_weights` and `features.nppv_prioritization` tables.

**Tech Stack:** Python 3.9+, pandas, numpy, matplotlib, geopandas, psycopg2, sqlalchemy, pytest. All credentials via `config.PG_URI`.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `db_setup/migrations/005_w4_tables.sql` | DDL for nppv_w4_weights + nppv_prioritization |
| Create | `src/w4_prioritization.py` | All computation + DB write + file output logic |
| Create | `src/run_w4.py` | Orchestrator: migration → module |
| Create | `tests/test_w4_prioritization.py` | Unit tests for pure functions |
| Create | `outputs/w4/` | All output files (auto-created by script) |

---

## Task 1: DB Migration

**Files:**
- Create: `db_setup/migrations/005_w4_tables.sql`

- [ ] **Step 1: Write the migration SQL**

Create `db_setup/migrations/005_w4_tables.sql`:

```sql
-- 005_w4_tables.sql
-- W4 NPP Prioritization Layer -- output tables

DROP TABLE IF EXISTS features.nppv_prioritization CASCADE;
DROP TABLE IF EXISTS features.nppv_w4_weights CASCADE;

CREATE TABLE features.nppv_w4_weights (
    feature          VARCHAR(50) PRIMARY KEY,
    dimension        VARCHAR(20),
    critic_weight    NUMERIC,
    ewm_weight       NUMERIC,
    ensemble_weight  NUMERIC
);

CREATE TABLE features.nppv_prioritization (
    cve_ageb          TEXT PRIMARY KEY REFERENCES base.ageb(cvegeo),
    npp_score         NUMERIC,
    equity_score      NUMERIC,
    final_score       NUMERIC,
    priority_rank     INTEGER,
    priority_quintile INTEGER
);

CREATE INDEX nppv_prioritization_final_score_idx
    ON features.nppv_prioritization (final_score DESC);

ANALYZE features.nppv_prioritization;
```

- [ ] **Step 2: Apply migration and verify**

```bash
psql -h localhost -d gdl_metro -f db_setup/migrations/005_w4_tables.sql
```

Expected output:
```
DROP TABLE
DROP TABLE
CREATE TABLE
CREATE TABLE
CREATE INDEX
ANALYZE
```

Then verify:
```bash
psql -h localhost -d gdl_metro -c "\d features.nppv_prioritization"
```

Expected: table with columns cve_ageb, npp_score, equity_score, final_score, priority_rank, priority_quintile.

- [ ] **Step 3: Commit**

```bash
git add db_setup/migrations/005_w4_tables.sql
git commit -m "feat(w4): add DDL migration for nppv_w4_weights and nppv_prioritization tables"
```

---

## Task 2: Pure Computation Functions (TDD)

**Files:**
- Create: `tests/test_w4_prioritization.py`
- Create: `src/w4_prioritization.py` (pure functions only at this stage)

- [ ] **Step 1: Write failing tests**

Create `tests/test_w4_prioritization.py`:

```python
import numpy as np
import pandas as pd
import pytest


FEATURES_14 = [
    "n_intersections_n", "n_street_density_n", "n_intersection_density_n",
    "p_poi_density_n", "p_employment_proxy_n", "p_retail_density_n",
    "p_service_density_n", "p_land_use_mix_n",
    "pe_population_n", "pe_pop_density_n", "pe_marginacion_n", "pe_rezago_n",
    "pe_dep_ratio_n", "pe_youth_share_n",
]


def make_synthetic_df(n=50, seed=42):
    rng = np.random.default_rng(seed)
    data = {f: rng.uniform(0, 1, n) for f in FEATURES_14}
    data["cve_ageb"] = [f"AGEB{i:04d}" for i in range(n)]
    return pd.DataFrame(data)


def test_critic_weights_sum_to_one():
    from src.w4_prioritization import compute_critic_weights
    df = make_synthetic_df()
    weights = compute_critic_weights(df[FEATURES_14])
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_critic_weights_all_positive():
    from src.w4_prioritization import compute_critic_weights
    df = make_synthetic_df()
    weights = compute_critic_weights(df[FEATURES_14])
    assert all(v > 0 for v in weights.values())


def test_critic_weights_covers_all_features():
    from src.w4_prioritization import compute_critic_weights
    df = make_synthetic_df()
    weights = compute_critic_weights(df[FEATURES_14])
    assert set(weights.keys()) == set(FEATURES_14)


def test_ewm_weights_sum_to_one():
    from src.w4_prioritization import compute_ewm_weights
    df = make_synthetic_df()
    weights = compute_ewm_weights(df[FEATURES_14])
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_ewm_weights_all_positive():
    from src.w4_prioritization import compute_ewm_weights
    df = make_synthetic_df()
    weights = compute_ewm_weights(df[FEATURES_14])
    assert all(v > 0 for v in weights.values())


def test_ensemble_weights_sum_to_one():
    from src.w4_prioritization import compute_critic_weights, compute_ewm_weights, compute_ensemble_weights
    df = make_synthetic_df()
    critic_w = compute_critic_weights(df[FEATURES_14])
    ewm_w = compute_ewm_weights(df[FEATURES_14])
    ensemble = compute_ensemble_weights(critic_w, ewm_w)
    assert abs(sum(ensemble.values()) - 1.0) < 1e-9


def test_scores_alpha_zero_equals_npp():
    """With alpha=0, final_score must equal npp_score exactly."""
    from src.w4_prioritization import compute_critic_weights, compute_ewm_weights, compute_ensemble_weights, compute_scores
    df = make_synthetic_df()
    critic_w = compute_critic_weights(df[FEATURES_14])
    ewm_w = compute_ewm_weights(df[FEATURES_14])
    ensemble = compute_ensemble_weights(critic_w, ewm_w)
    result = compute_scores(df, ensemble, alpha=0.0)
    pd.testing.assert_series_equal(result["final_score"], result["npp_score"], check_names=False)


def test_scores_alpha_one_equals_equity():
    """With alpha=1, final_score must equal equity_score exactly."""
    from src.w4_prioritization import compute_critic_weights, compute_ewm_weights, compute_ensemble_weights, compute_scores
    df = make_synthetic_df()
    critic_w = compute_critic_weights(df[FEATURES_14])
    ewm_w = compute_ewm_weights(df[FEATURES_14])
    ensemble = compute_ensemble_weights(critic_w, ewm_w)
    result = compute_scores(df, ensemble, alpha=1.0)
    pd.testing.assert_series_equal(result["final_score"], result["equity_score"], check_names=False)


def test_scores_priority_rank_range():
    """priority_rank must span 1..n with no gaps."""
    from src.w4_prioritization import compute_critic_weights, compute_ewm_weights, compute_ensemble_weights, compute_scores
    df = make_synthetic_df()
    critic_w = compute_critic_weights(df[FEATURES_14])
    ewm_w = compute_ewm_weights(df[FEATURES_14])
    ensemble = compute_ensemble_weights(critic_w, ewm_w)
    result = compute_scores(df, ensemble, alpha=0.20)
    assert result["priority_rank"].min() == 1
    assert result["priority_rank"].max() == len(df)


def test_scores_priority_quintile_values():
    """priority_quintile must only contain values in {1,2,3,4,5}."""
    from src.w4_prioritization import compute_critic_weights, compute_ewm_weights, compute_ensemble_weights, compute_scores
    df = make_synthetic_df()
    critic_w = compute_critic_weights(df[FEATURES_14])
    ewm_w = compute_ewm_weights(df[FEATURES_14])
    ensemble = compute_ensemble_weights(critic_w, ewm_w)
    result = compute_scores(df, ensemble, alpha=0.20)
    assert set(result["priority_quintile"].unique()).issubset({1, 2, 3, 4, 5})


def test_scores_output_columns():
    """Result must have exactly the expected columns."""
    from src.w4_prioritization import compute_critic_weights, compute_ewm_weights, compute_ensemble_weights, compute_scores
    df = make_synthetic_df()
    critic_w = compute_critic_weights(df[FEATURES_14])
    ewm_w = compute_ewm_weights(df[FEATURES_14])
    ensemble = compute_ensemble_weights(critic_w, ewm_w)
    result = compute_scores(df, ensemble, alpha=0.20)
    expected_cols = {"cve_ageb", "npp_score", "equity_score", "final_score", "priority_rank", "priority_quintile"}
    assert set(result.columns) == expected_cols
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd c:/Users/aguev/Documents/Maestria_UDG/tesis/predictive-transit-zmg
.venv/Scripts/python -m pytest tests/test_w4_prioritization.py -v 2>&1 | head -30
```

Expected: all tests fail with `ModuleNotFoundError` or `ImportError` for `src.w4_prioritization`.

- [ ] **Step 3: Implement pure functions in `src/w4_prioritization.py`**

Create `src/w4_prioritization.py` with these constants and functions only (no DB code yet):

```python
"""
W4 -- NPP Prioritization Layer
===============================
Repositions the NPP-V framework as a multi-criteria place-characteristics
prioritization index, decoupled from demand estimation.

Vitality dimension (v_ridership_annual_n) is excluded -- it is a
municipality-level proxy with no AGEB-level discrimination power.
Demand signal lives exclusively in W1/W3.

Score formula:
    npp_score    = sum(feature_i * ensemble_weight_i)    [CRITIC+EWM, 14 features]
    equity_score = mean(pe_marginacion_n, pe_rezago_n)
    final_score  = (1 - ALPHA) * npp_score + ALPHA * equity_score
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2.extras
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI

ENGINE = create_engine(PG_URI)
PROJECT_ROOT = Path(__file__).parent.parent

ALPHA = 0.20  # equity bonus weight; sensitivity tested at 0.10, 0.20, 0.30

NPP_FEATURES = [
    "n_intersections_n", "n_street_density_n", "n_intersection_density_n",
    "p_poi_density_n", "p_employment_proxy_n", "p_retail_density_n",
    "p_service_density_n", "p_land_use_mix_n",
    "pe_population_n", "pe_pop_density_n", "pe_marginacion_n", "pe_rezago_n",
    "pe_dep_ratio_n", "pe_youth_share_n",
]
EQUITY_FEATURES = ["pe_marginacion_n", "pe_rezago_n"]
DIMENSIONS = {
    "n_intersections_n": "NODE",
    "n_street_density_n": "NODE",
    "n_intersection_density_n": "NODE",
    "p_poi_density_n": "PLACE",
    "p_employment_proxy_n": "PLACE",
    "p_retail_density_n": "PLACE",
    "p_service_density_n": "PLACE",
    "p_land_use_mix_n": "PLACE",
    "pe_population_n": "PEOPLE",
    "pe_pop_density_n": "PEOPLE",
    "pe_marginacion_n": "PEOPLE",
    "pe_rezago_n": "PEOPLE",
    "pe_dep_ratio_n": "PEOPLE",
    "pe_youth_share_n": "PEOPLE",
}


# ---------------------------------------------------------------------------
# Pure computation functions (no DB, fully testable)
# ---------------------------------------------------------------------------

def compute_critic_weights(df: pd.DataFrame) -> dict:
    """CRITIC weights: contrast intensity x conflict across features."""
    std_dev = df.std()
    corr_matrix = df.corr()
    conflict = (1 - corr_matrix).sum()
    c_j = std_dev * conflict
    w = c_j / c_j.sum()
    return w.to_dict()


def compute_ewm_weights(df: pd.DataFrame) -> dict:
    """Entropy Weight Method weights: information dispersion across features."""
    n = len(df)
    shifted = df + 1e-6
    p_ij = shifted / shifted.sum()
    k = 1.0 / np.log(n)
    e_j = -k * (p_ij * np.log(p_ij)).sum()
    d_j = 1 - e_j
    w = d_j / d_j.sum()
    return w.to_dict()


def compute_ensemble_weights(critic_w: dict, ewm_w: dict) -> dict:
    """Average of CRITIC and EWM, re-normalized to sum to 1."""
    features = list(critic_w.keys())
    raw = {f: (critic_w[f] + ewm_w[f]) / 2.0 for f in features}
    total = sum(raw.values())
    return {f: v / total for f, v in raw.items()}


def compute_scores(df: pd.DataFrame, ensemble_w: dict, alpha: float = ALPHA) -> pd.DataFrame:
    """
    Compute npp_score, equity_score, final_score, priority_rank, priority_quintile.

    df must contain 'cve_ageb' plus all NPP_FEATURES columns.
    ensemble_w keys must cover all NPP_FEATURES.
    """
    npp_score = sum(df[f] * w for f, w in ensemble_w.items())
    equity_score = df[EQUITY_FEATURES].mean(axis=1)
    final_score = (1 - alpha) * npp_score + alpha * equity_score

    priority_rank = final_score.rank(ascending=False, method="min").astype(int)
    try:
        priority_quintile = pd.qcut(final_score, q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    except ValueError:
        priority_quintile = pd.cut(final_score, bins=5, labels=[1, 2, 3, 4, 5]).astype(int)

    return pd.DataFrame({
        "cve_ageb": df["cve_ageb"].values,
        "npp_score": npp_score.values,
        "equity_score": equity_score.values,
        "final_score": final_score.values,
        "priority_rank": priority_rank.values,
        "priority_quintile": priority_quintile.values,
    })
```

- [ ] **Step 4: Run tests and confirm they all pass**

```bash
.venv/Scripts/python -m pytest tests/test_w4_prioritization.py -v
```

Expected output:
```
tests/test_w4_prioritization.py::test_critic_weights_sum_to_one PASSED
tests/test_w4_prioritization.py::test_critic_weights_all_positive PASSED
tests/test_w4_prioritization.py::test_critic_weights_covers_all_features PASSED
tests/test_w4_prioritization.py::test_ewm_weights_sum_to_one PASSED
tests/test_w4_prioritization.py::test_ewm_weights_all_positive PASSED
tests/test_w4_prioritization.py::test_ensemble_weights_sum_to_one PASSED
tests/test_w4_prioritization.py::test_scores_alpha_zero_equals_npp PASSED
tests/test_w4_prioritization.py::test_scores_alpha_one_equals_equity PASSED
tests/test_w4_prioritization.py::test_scores_priority_rank_range PASSED
tests/test_w4_prioritization.py::test_scores_priority_quintile_values PASSED
tests/test_w4_prioritization.py::test_scores_output_columns PASSED
11 passed in ...
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_w4_prioritization.py src/w4_prioritization.py
git commit -m "feat(w4): implement and test pure CRITIC/EWM/score computation functions"
```

---

## Task 3: DB Load, DB Write, and CSV Outputs

**Files:**
- Modify: `src/w4_prioritization.py` (add load, write, csv functions + `main()`)

- [ ] **Step 1: Add DB loader, DB writers, CSV exports, and `main()` to `src/w4_prioritization.py`**

Append the following to `src/w4_prioritization.py` (after the pure functions):

```python
# ---------------------------------------------------------------------------
# DB I/O
# ---------------------------------------------------------------------------

def load_npp_features() -> pd.DataFrame:
    print("[Step 1] Loading 14 NPP features from features.nppv_features...")
    cols = ", ".join(["cvegeo"] + NPP_FEATURES)
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(
            f"SELECT {cols} FROM features.nppv_features f "
            f"JOIN base.ageb a ON a.cvegeo = f.ageb_id",
            conn,
        )
    # Fallback: try direct join if above fails due to column naming
    if df.empty or "cvegeo" not in df.columns:
        with ENGINE.raw_connection() as conn:
            df = pd.read_sql(
                "SELECT ageb_id AS cve_ageb, " + ", ".join(NPP_FEATURES) +
                " FROM features.nppv_features",
                conn,
            )
    else:
        df = df.rename(columns={"cvegeo": "cve_ageb"})
    print(f"  [OK] {len(df):,} AGEBs loaded with {len(NPP_FEATURES)} features")
    return df


def write_weights_to_db(critic_w: dict, ewm_w: dict, ensemble_w: dict):
    print("[Step 5] Writing weights to features.nppv_w4_weights...")
    records = [
        (f, DIMENSIONS[f], float(critic_w[f]), float(ewm_w[f]), float(ensemble_w[f]))
        for f in NPP_FEATURES
    ]
    with ENGINE.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE features.nppv_w4_weights")
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO features.nppv_w4_weights "
                "(feature, dimension, critic_weight, ewm_weight, ensemble_weight) VALUES %s",
                records,
            )
        conn.commit()
    print(f"  [OK] {len(records)} feature weights written")


def write_scores_to_db(scores_df: pd.DataFrame):
    print("[Step 6] Writing scores to features.nppv_prioritization...")
    cols = ["cve_ageb", "npp_score", "equity_score", "final_score",
            "priority_rank", "priority_quintile"]
    rows = list(scores_df[cols].itertuples(index=False, name=None))
    with ENGINE.raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM features.nppv_prioritization")
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO features.nppv_prioritization "
                "(cve_ageb, npp_score, equity_score, final_score, "
                "priority_rank, priority_quintile) VALUES %s",
                rows, page_size=500,
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("ANALYZE features.nppv_prioritization")
        conn.commit()
    print(f"  [OK] {len(rows):,} AGEB rows written")


def export_csvs(weights_df: pd.DataFrame, scores_df: pd.DataFrame, out_dir: Path):
    print("[Step 7] Exporting CSVs...")
    weights_df.to_csv(out_dir / "nppv_w4_weights.csv", index=False)
    scores_df.to_csv(out_dir / "nppv_prioritization.csv", index=False)
    print(f"  [OK] outputs/w4/nppv_w4_weights.csv")
    print(f"  [OK] outputs/w4/nppv_prioritization.csv")
```

Then add the `main()` function skeleton that calls only Steps 1–7 for now:

```python
def main():
    print("\n" + "="*70)
    print(" W4: NPP PRIORITIZATION LAYER")
    print("="*70)

    out_dir = PROJECT_ROOT / "outputs" / "w4"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load
    features_df = load_npp_features()

    # Compute weights
    print("[Step 2] Computing CRITIC weights...")
    critic_w = compute_critic_weights(features_df[NPP_FEATURES])
    print(f"  [OK] CRITIC computed for {len(critic_w)} features")

    print("[Step 3] Computing EWM weights...")
    ewm_w = compute_ewm_weights(features_df[NPP_FEATURES])
    print(f"  [OK] EWM computed for {len(ewm_w)} features")

    print("[Step 4] Computing NPP + equity scores...")
    ensemble_w = compute_ensemble_weights(critic_w, ewm_w)
    scores_df = compute_scores(features_df, ensemble_w, alpha=ALPHA)
    print(f"  [OK] Scores computed for {len(scores_df):,} AGEBs")
    print(f"    npp_score   : mean={scores_df['npp_score'].mean():.4f}")
    print(f"    equity_score: mean={scores_df['equity_score'].mean():.4f}")
    print(f"    final_score : mean={scores_df['final_score'].mean():.4f}")

    # Build weights DataFrame for CSV/DB
    weights_df = pd.DataFrame([
        {
            "feature": f,
            "dimension": DIMENSIONS[f],
            "critic_weight": critic_w[f],
            "ewm_weight": ewm_w[f],
            "ensemble_weight": ensemble_w[f],
        }
        for f in NPP_FEATURES
    ]).sort_values("ensemble_weight", ascending=False)

    # DB writes
    write_weights_to_db(critic_w, ewm_w, ensemble_w)
    write_scores_to_db(scores_df)

    # CSVs
    export_csvs(weights_df, scores_df, out_dir)

    print("\n" + "="*70)
    print(" W4 STEP 1-7 COMPLETE -- DB + CSVs written")
    print("="*70)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Fix the DB loader**

The `features.nppv_features` table uses `ageb_id` as the key column (not `cvegeo`). Replace the `load_npp_features` function body with the correct single query:

```python
def load_npp_features() -> pd.DataFrame:
    print("[Step 1] Loading 14 NPP features from features.nppv_features...")
    cols = ", ".join(["ageb_id AS cve_ageb"] + NPP_FEATURES)
    with ENGINE.raw_connection() as conn:
        df = pd.read_sql(
            f"SELECT {cols} FROM features.nppv_features",
            conn,
        )
    for col in NPP_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    print(f"  [OK] {len(df):,} AGEBs loaded with {len(NPP_FEATURES)} features")
    return df
```

(To confirm the column name, run: `psql -h localhost -d gdl_metro -c "\d features.nppv_features" | head -10`)

- [ ] **Step 3: Run script through Step 7 and verify**

```bash
.venv/Scripts/python src/w4_prioritization.py
```

Expected:
```
W4: NPP PRIORITIZATION LAYER
...
[Step 1] Loading 14 NPP features from features.nppv_features...
  [OK] 2,068 AGEBs loaded with 14 features
[Step 2] Computing CRITIC weights...
  [OK] CRITIC computed for 14 features
[Step 3] Computing EWM weights...
  [OK] EWM computed for 14 features
[Step 4] Computing NPP + equity scores...
  [OK] Scores computed for 2,068 AGEBs
...
[Step 5] Writing weights to features.nppv_w4_weights...
  [OK] 14 feature weights written
[Step 6] Writing scores to features.nppv_prioritization...
  [OK] 2,068 AGEB rows written
[Step 7] Exporting CSVs...
  [OK] outputs/w4/nppv_w4_weights.csv
  [OK] outputs/w4/nppv_prioritization.csv
```

Verify DB row counts:
```bash
psql -h localhost -d gdl_metro -c "SELECT COUNT(*) FROM features.nppv_prioritization;"
```
Expected: `2068`

```bash
psql -h localhost -d gdl_metro -c "SELECT COUNT(*) FROM features.nppv_w4_weights;"
```
Expected: `14`

- [ ] **Step 4: Commit**

```bash
git add src/w4_prioritization.py
git commit -m "feat(w4): add DB load/write and CSV export to w4_prioritization"
```

---

## Task 4: GeoJSON Output

**Files:**
- Modify: `src/w4_prioritization.py` (add `export_geojson` + wire into `main`)

- [ ] **Step 1: Add `export_geojson` function**

Add this function to `src/w4_prioritization.py` after `export_csvs`:

```python
def export_geojson(out_dir: Path):
    print("[Step 8] Exporting GeoJSON (joining base.ageb geometry)...")
    import geopandas as gpd
    query = """
        SELECT a.cvegeo, a.geom AS geometry,
               p.npp_score, p.equity_score, p.final_score,
               p.priority_rank, p.priority_quintile
        FROM base.ageb a
        JOIN features.nppv_prioritization p ON a.cvegeo = p.cve_ageb
    """
    with ENGINE.raw_connection() as conn:
        gdf = gpd.read_postgis(query, conn, geom_col="geometry")
    gdf = gdf.to_crs("EPSG:4326")
    out_path = out_dir / "nppv_prioritization.geojson"
    gdf.to_file(str(out_path), driver="GeoJSON")
    print(f"  [OK] {len(gdf):,} features -> outputs/w4/nppv_prioritization.geojson")
```

- [ ] **Step 2: Wire into `main()` after `export_csvs`**

In the `main()` function, add this line after `export_csvs(weights_df, scores_df, out_dir)`:

```python
    export_geojson(out_dir)
```

And update the final print block:
```python
    print(" W4 STEP 1-8 COMPLETE -- DB + CSVs + GeoJSON written")
```

- [ ] **Step 3: Check the geometry column name**

Before running, confirm the geometry column name in `base.ageb`:
```bash
psql -h localhost -d gdl_metro -c "\d base.ageb" | grep geom
```

If the column is named `geometry` (not `geom`), update the query in `export_geojson`:
```python
        SELECT a.cvegeo, a.geometry,
```

- [ ] **Step 4: Run and verify**

```bash
.venv/Scripts/python src/w4_prioritization.py
```

Check file exists and has correct feature count:
```bash
python -c "import json; d=json.load(open('outputs/w4/nppv_prioritization.geojson')); print(len(d['features']), 'features')"
```
Expected: `2068 features`

- [ ] **Step 5: Commit**

```bash
git add src/w4_prioritization.py
git commit -m "feat(w4): add GeoJSON export joining base.ageb geometry"
```

---

## Task 5: Charts

**Files:**
- Modify: `src/w4_prioritization.py` (add `generate_charts` + wire into `main`)

- [ ] **Step 1: Add `generate_charts` function**

Add after `export_geojson` in `src/w4_prioritization.py`:

```python
def generate_charts(weights_df: pd.DataFrame, scores_df: pd.DataFrame, out_dir: Path):
    print("[Step 9] Generating charts...")
    import matplotlib.pyplot as plt

    # Chart 1: Horizontal bar of 14 ensemble weights
    df_plot = weights_df.sort_values("ensemble_weight", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(df_plot)))
    bars = ax.barh(df_plot["feature"], df_plot["ensemble_weight"], color=colors)
    ax.set_xlabel("Ensemble Weight (50% CRITIC / 50% EWM)")
    ax.set_title("W4 NPP Feature Importance Weights (14 features, Vitality excluded)")
    for bar in bars:
        ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height() / 2,
                f"{bar.get_width():.4f}", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "nppv_w4_weights_bar.png", dpi=300)
    plt.close()
    print("  [OK] nppv_w4_weights_bar.png")

    # Chart 2: Scatter npp_score vs equity_score, colored by final_score
    # Join transit_demand for point sizing
    with ENGINE.raw_connection() as conn:
        demand_df = pd.read_sql(
            "SELECT cve_ageb, transit_demand FROM features.ageb_trip_ends", conn
        )
    merged = scores_df.merge(demand_df, on="cve_ageb", how="left")
    merged["transit_demand"] = merged["transit_demand"].fillna(0.0)

    # Normalize size: 20..200 pt range
    td = merged["transit_demand"]
    sizes = 20 + 180 * (td - td.min()) / (td.max() - td.min() + 1e-9)

    fig, ax = plt.subplots(figsize=(10, 8))
    sc = ax.scatter(
        merged["npp_score"], merged["equity_score"],
        c=merged["final_score"], s=sizes,
        cmap="YlOrRd", alpha=0.6, linewidths=0.2, edgecolors="grey",
    )
    plt.colorbar(sc, ax=ax, label="final_score")
    ax.set_xlabel("NPP Score (CRITIC+EWM weighted, 14 features)")
    ax.set_ylabel("Equity Score (mean marginacion + rezago)")
    ax.set_title("W4 NPP Score vs Equity Score\n(point size = transit demand, color = final score)")
    plt.tight_layout()
    plt.savefig(out_dir / "nppv_score_vs_equity.png", dpi=300)
    plt.close()
    print("  [OK] nppv_score_vs_equity.png")
```

- [ ] **Step 2: Wire into `main()` after `export_geojson`**

```python
    generate_charts(weights_df, scores_df, out_dir)
```

Update final print: `" W4 STEP 1-9 COMPLETE"`

- [ ] **Step 3: Run and verify both PNG files exist**

```bash
.venv/Scripts/python src/w4_prioritization.py
```

```bash
ls outputs/w4/*.png
```
Expected:
```
outputs/w4/nppv_score_vs_equity.png
outputs/w4/nppv_w4_weights_bar.png
```

- [ ] **Step 4: Commit**

```bash
git add src/w4_prioritization.py
git commit -m "feat(w4): add weight bar chart and npp-vs-equity scatter plot"
```

---

## Task 6: Cluster Profile Update

**Files:**
- Modify: `src/w4_prioritization.py` (add `generate_cluster_profiles` + wire into `main`)

- [ ] **Step 1: Check cluster table column name**

```bash
psql -h localhost -d gdl_metro -c "\d features.nppv_clusters" | head -15
```

Note the column names for `ageb_id` and `cluster` (or `cluster_label`). Use them in the query below.

- [ ] **Step 2: Add `generate_cluster_profiles` function**

Add after `generate_charts` in `src/w4_prioritization.py`:

```python
def generate_cluster_profiles(scores_df: pd.DataFrame, out_dir: Path):
    print("[Step 10] Generating cluster priority profiles...")
    with ENGINE.raw_connection() as conn:
        clusters_df = pd.read_sql(
            "SELECT ageb_id AS cve_ageb, cluster_label AS cluster "
            "FROM features.nppv_clusters",
            conn,
        )
    merged = scores_df.merge(clusters_df, on="cve_ageb", how="left")
    missing = merged["cluster"].isna().sum()
    if missing > 0:
        print(f"  [WARN] {missing} AGEBs have no cluster label -- will be excluded from profile")

    profile = (
        merged.dropna(subset=["cluster"])
        .groupby("cluster")[["npp_score", "equity_score", "final_score"]]
        .agg(["mean", "median", "count"])
    )
    profile.columns = ["_".join(c) for c in profile.columns]
    profile = profile.reset_index()
    out_path = out_dir / "cluster_priority_profiles.csv"
    profile.to_csv(out_path, index=False)
    print(f"  [OK] cluster_priority_profiles.csv ({len(profile)} clusters)")
    print(profile.to_string(index=False))
```

- [ ] **Step 3: Check the actual column names from Step 1**

If the cluster table uses `cluster` instead of `cluster_label`, update the query:
```python
"SELECT ageb_id AS cve_ageb, cluster FROM features.nppv_clusters",
```

- [ ] **Step 4: Wire into `main()` after `generate_charts`**

```python
    generate_cluster_profiles(scores_df, out_dir)
```

Update final print: `" W4 STEP 1-10 COMPLETE"`

- [ ] **Step 5: Run and verify**

```bash
.venv/Scripts/python src/w4_prioritization.py
```

```bash
cat outputs/w4/cluster_priority_profiles.csv
```

Expected: a CSV with one row per cluster (A, B, C) and mean/median/count columns for npp_score, equity_score, final_score.

- [ ] **Step 6: Commit**

```bash
git add src/w4_prioritization.py
git commit -m "feat(w4): add cluster priority profile output (mean scores per cluster)"
```

---

## Task 7: Markdown Report

**Files:**
- Modify: `src/w4_prioritization.py` (add `write_report` + wire into `main`)

- [ ] **Step 1: Add `write_report` function**

Add after `generate_cluster_profiles` in `src/w4_prioritization.py`:

```python
def write_report(weights_df: pd.DataFrame, scores_df: pd.DataFrame,
                 cluster_profile_path: Path, out_dir: Path):
    print("[Step 11] Writing w4_report.md...")
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    top10 = scores_df.sort_values("final_score", ascending=False).head(10)
    top10_md = top10[["cve_ageb", "npp_score", "equity_score", "final_score",
                       "priority_rank", "priority_quintile"]].to_markdown(index=False)

    weights_md = weights_df.to_markdown(index=False)

    q5_count = (scores_df["priority_quintile"] == 5).sum()
    q1_count = (scores_df["priority_quintile"] == 1).sum()

    # Sensitivity: compute Spearman rank correlation across alpha values
    from scipy.stats import spearmanr
    with ENGINE.raw_connection() as conn:
        feat_df = pd.read_sql(
            "SELECT ageb_id AS cve_ageb, " + ", ".join(NPP_FEATURES) +
            " FROM features.nppv_features", conn
        )
    critic_w = compute_critic_weights(feat_df[NPP_FEATURES])
    ewm_w = compute_ewm_weights(feat_df[NPP_FEATURES])
    ensemble_w = compute_ensemble_weights(critic_w, ewm_w)

    sensitivity_rows = []
    base_ranks = scores_df.set_index("cve_ageb")["priority_rank"]
    for alpha_val in [0.10, 0.20, 0.30]:
        alt = compute_scores(feat_df, ensemble_w, alpha=alpha_val)
        alt_ranks = alt.set_index("cve_ageb")["priority_rank"]
        aligned = base_ranks.align(alt_ranks, join="inner")
        rho, _ = spearmanr(aligned[0], aligned[1])
        sensitivity_rows.append(f"| {alpha_val} | {rho:.4f} |")
    sensitivity_md = "\n".join(sensitivity_rows)

    report = f"""# W4 NPP Prioritization Layer Report
*Generated: {now}*

## Methodology

W4 repositions the NPP-V indicator set as a multi-criteria place-characteristics
prioritization index, decoupled from demand estimation. The Vitality dimension
(`v_ridership_annual_n`) is excluded because it is a municipality-level proxy with
no AGEB-level discrimination. Demand lives in W1/W3.

**Score formula:**
- `npp_score = sum(feature_i * ensemble_weight_i)` over 14 NODE+PLACE+PEOPLE features
- `equity_score = mean(pe_marginacion_n, pe_rezago_n)`
- `final_score = {1 - ALPHA:.2f} * npp_score + {ALPHA:.2f} * equity_score`

CRITIC and EWM weights are computed independently and averaged (ensemble).

## Feature Weights (14 features)

{weights_md}

## Score Summary (2,068 AGEBs)

| Metric | npp_score | equity_score | final_score |
|---|---|---|---|
| Mean | {scores_df['npp_score'].mean():.4f} | {scores_df['equity_score'].mean():.4f} | {scores_df['final_score'].mean():.4f} |
| Std  | {scores_df['npp_score'].std():.4f} | {scores_df['equity_score'].std():.4f} | {scores_df['final_score'].std():.4f} |
| Min  | {scores_df['npp_score'].min():.4f} | {scores_df['equity_score'].min():.4f} | {scores_df['final_score'].min():.4f} |
| Max  | {scores_df['npp_score'].max():.4f} | {scores_df['equity_score'].max():.4f} | {scores_df['final_score'].max():.4f} |

Priority quintile 5 (highest priority): **{q5_count:,} AGEBs**
Priority quintile 1 (lowest priority): **{q1_count:,} AGEBs**

## Top 10 Highest-Priority AGEBs

{top10_md}

## Equity Sensitivity (Spearman rank correlation vs alpha=0.20 baseline)

| alpha | Spearman rho |
|---|---|
{sensitivity_md}

A rho close to 1.0 indicates that changing alpha has little effect on the
priority ranking — the NPP and equity dimensions agree on which areas rank highest.

## Methodological Note

`pe_marginacion_n` and `pe_rezago_n` contribute to both `npp_score` (via CRITIC/EWM)
and `equity_score`. This mild double-count slightly amplifies their influence on
`final_score`. If this becomes overinfluential, the equity_score operationalization
can be changed to use other equity indicators.

## Outputs

- `features.nppv_w4_weights` — 14 feature weights (DB)
- `features.nppv_prioritization` — 2,068 AGEB scores + ranks (DB)
- `outputs/w4/nppv_w4_weights.csv`
- `outputs/w4/nppv_prioritization.csv`
- `outputs/w4/nppv_prioritization.geojson` (QGIS-ready, EPSG:4326)
- `outputs/w4/nppv_w4_weights_bar.png`
- `outputs/w4/nppv_score_vs_equity.png`
- `outputs/w4/cluster_priority_profiles.csv`
"""
    (out_dir / "w4_report.md").write_text(report, encoding="utf-8")
    print(f"  [OK] outputs/w4/w4_report.md")
```

- [ ] **Step 2: Wire into `main()` after `generate_cluster_profiles`**

```python
    write_report(weights_df, scores_df,
                 out_dir / "cluster_priority_profiles.csv", out_dir)
```

Update final print block to the final version:

```python
    print("\n" + "="*70)
    print(" [OK] W4 NPP PRIORITIZATION LAYER COMPLETE")
    print("="*70)
    print("DB outputs:")
    print("  features.nppv_w4_weights        -- 14 feature weights")
    print("  features.nppv_prioritization    -- 2,068 AGEB scores + ranks")
    print("File outputs (outputs/w4/):")
    print("  nppv_w4_weights.csv")
    print("  nppv_prioritization.csv")
    print("  nppv_prioritization.geojson")
    print("  nppv_w4_weights_bar.png")
    print("  nppv_score_vs_equity.png")
    print("  cluster_priority_profiles.csv")
    print("  w4_report.md")
```

- [ ] **Step 3: Install tabulate if needed (for `.to_markdown()`)**

```bash
.venv/Scripts/pip show tabulate || .venv/Scripts/pip install tabulate
```

- [ ] **Step 4: Run and verify report**

```bash
.venv/Scripts/python src/w4_prioritization.py
```

```bash
python -c "print(open('outputs/w4/w4_report.md').read()[:500])"
```

Expected: markdown header, date, feature weight table visible in first 500 chars.

- [ ] **Step 5: Commit**

```bash
git add src/w4_prioritization.py
git commit -m "feat(w4): add markdown report with weights, top-10, sensitivity analysis"
```

---

## Task 8: Orchestrator `run_w4.py`

**Files:**
- Create: `src/run_w4.py`

- [ ] **Step 1: Create orchestrator**

Create `src/run_w4.py`:

```python
"""
W4: NPP Prioritization Layer -- Master Execution Script
=======================================================
Runs W4 in sequence:
  1. Apply DDL migration 005_w4_tables.sql (idempotent -- DROP/CREATE)
  2. w4_prioritization.py  -- CRITIC/EWM weights, scores, all outputs

Usage:
    python src/run_w4.py
"""

import subprocess
import sys
import traceback
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PG_URI


def run_sql_file(engine, sql_file: Path, description: str) -> bool:
    print(f"\n{'='*70}\n  {description}\n{'='*70}")
    try:
        sql_text = sql_file.read_text(encoding="utf-8")
        statements = [s.strip() for s in sql_text.split(";") if s.strip()]
        with engine.begin() as conn:
            for stmt in statements:
                print(f"  Executing: {stmt[:80]}...")
                conn.execute(text(stmt))
        print(f"  [OK] {description} -- COMPLETE")
        return True
    except Exception as e:
        print(f"  [ERR] {description}: {e}")
        traceback.print_exc()
        return False


def run_python_script(_engine, script: Path, description: str, timeout: int = 3600) -> bool:
    print(f"\n{'='*70}\n  {description}\n{'='*70}")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.stdout:
            print(result.stdout)
        if result.returncode != 0:
            print(f"  [ERR] {description}:")
            if result.stderr:
                print(result.stderr)
            return False
        print(f"  [OK] {description} -- COMPLETE")
        return True
    except subprocess.TimeoutExpired:
        print(f"  [ERR] TIMEOUT ({timeout}s) in {description}")
        return False
    except Exception as e:
        print(f"  [ERR] {description}: {e}")
        return False


def main():
    print("\n" + "="*70)
    print(" W4: NPP PRIORITIZATION LAYER")
    print("="*70)

    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    mig_dir = project_root / "db_setup" / "migrations"

    print("\nConnecting to PostgreSQL...")
    engine = create_engine(PG_URI)

    steps = [
        (run_sql_file,      engine, mig_dir / "005_w4_tables.sql",      "Step 1: DDL -- W4 output tables"),
        (run_python_script, None,   src_dir / "w4_prioritization.py",   "Step 2: W4 -- NPP prioritization scores + outputs"),
    ]

    for fn, *args in steps:
        if not fn(*args):
            print(f"\n[ERR] W4 pipeline aborted.")
            engine.dispose()
            sys.exit(1)

    print("\n" + "="*70)
    print(" [OK] W4 NPP PRIORITIZATION LAYER COMPLETE")
    print("="*70)
    print("DB outputs:")
    print("  features.nppv_w4_weights     -- 14 feature weights")
    print("  features.nppv_prioritization -- 2,068 AGEB scores + ranks")
    print("File outputs: outputs/w4/")
    engine.dispose()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the orchestrator end-to-end**

```bash
.venv/Scripts/python src/run_w4.py
```

Expected final line: `[OK] W4 NPP PRIORITIZATION LAYER COMPLETE`

- [ ] **Step 3: Verify all outputs exist**

```bash
python -c "
from pathlib import Path
expected = [
    'outputs/w4/nppv_w4_weights.csv',
    'outputs/w4/nppv_prioritization.csv',
    'outputs/w4/nppv_prioritization.geojson',
    'outputs/w4/nppv_w4_weights_bar.png',
    'outputs/w4/nppv_score_vs_equity.png',
    'outputs/w4/cluster_priority_profiles.csv',
    'outputs/w4/w4_report.md',
]
for p in expected:
    status = '[OK]' if Path(p).exists() else '[MISSING]'
    print(status, p)
"
```

Expected: all 7 files show `[OK]`.

- [ ] **Step 4: Run full test suite to confirm no regressions**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: all tests pass (11 W4 + 5 W1 = 16 total).

- [ ] **Step 5: Update CLAUDE.md workstream status**

In `CLAUDE.md`, change:
```
- W4 (Reposition NPP-V): 📋 Next
```
to:
```
- W4 (Reposition NPP-V): ✅ Complete -- features.nppv_prioritization in DB; 14 NODE+PLACE+PEOPLE features; final_score=(0.80*npp_score)+(0.20*equity_score); see W4 section below
```

- [ ] **Step 6: Final commit**

```bash
git add src/run_w4.py src/w4_prioritization.py CLAUDE.md outputs/w4/
git commit -m "feat(w4): complete NPP prioritization layer -- scores, GeoJSON, charts, report"
```
