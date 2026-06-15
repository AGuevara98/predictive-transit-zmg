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
    assert set(result["priority_rank"]) == set(range(1, len(df) + 1))


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
