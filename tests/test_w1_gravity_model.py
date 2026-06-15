import numpy as np
import pytest


def test_furness_balances_rows():
    """After IPF, row sums must equal target productions."""
    from src.w1_gravity_model import furness_ipf

    prods = np.array([100.0, 200.0, 150.0])
    attrs = np.array([150.0, 100.0, 200.0])
    dist_m = np.array([
        [0.0, 500.0, 1000.0],
        [500.0, 0.0, 800.0],
        [1000.0, 800.0, 0.0],
    ])
    T = furness_ipf(prods, attrs, dist_m, beta=2.0, max_iter=200, tol=1e-6)
    np.testing.assert_allclose(T.sum(axis=1), prods, rtol=1e-4,
                               err_msg="Row sums must match productions")


def test_furness_balances_cols():
    """After IPF, column sums must equal target attractions."""
    from src.w1_gravity_model import furness_ipf

    prods = np.array([100.0, 200.0, 150.0])
    attrs = np.array([150.0, 100.0, 200.0])
    dist_m = np.array([
        [0.0, 500.0, 1000.0],
        [500.0, 0.0, 800.0],
        [1000.0, 800.0, 0.0],
    ])
    T = furness_ipf(prods, attrs, dist_m, beta=2.0, max_iter=200, tol=1e-6)
    np.testing.assert_allclose(T.sum(axis=0), attrs, rtol=1e-4,
                               err_msg="Column sums must match attractions")


def test_furness_no_self_flows():
    """Diagonal of the OD matrix must be zero (no intra-AGEB flows)."""
    from src.w1_gravity_model import furness_ipf

    prods = np.array([100.0, 200.0, 150.0])
    attrs = np.array([150.0, 100.0, 200.0])
    dist_m = np.array([
        [0.0, 500.0, 1000.0],
        [500.0, 0.0, 800.0],
        [1000.0, 800.0, 0.0],
    ])
    T = furness_ipf(prods, attrs, dist_m, beta=2.0, max_iter=200, tol=1e-6)
    np.testing.assert_array_equal(np.diag(T), 0.0)


def test_furness_total_flow_conserved():
    """Total flow equals total productions (= total attractions after balancing)."""
    from src.w1_gravity_model import furness_ipf

    rng = np.random.default_rng(42)
    n = 10
    prods = rng.uniform(50, 300, n)
    attrs = prods.sum() * rng.dirichlet(np.ones(n))  # same total, different distribution
    dist_m = rng.uniform(100, 5000, (n, n))
    np.fill_diagonal(dist_m, 0.0)
    T = furness_ipf(prods, attrs, dist_m, beta=2.0, max_iter=500, tol=1e-6)
    assert abs(T.sum() - prods.sum()) / prods.sum() < 1e-3
