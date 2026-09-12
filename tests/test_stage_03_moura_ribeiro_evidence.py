from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_03_moura_ribeiro_evidence as evidence


def test_fixed_gompertz_bootstrap_recovers_exact_B():
    A, B = 1.53, 0.41
    x = np.linspace(0.2, 4.0, 30)
    y = A - B * x
    draws = evidence.bootstrap_fixed_gompertz_B(
        x, y, A, np.random.default_rng(10), reps=32
    )
    assert draws.shape == (32,)
    assert np.allclose(draws, B, atol=1e-12)


def test_free_line_bootstrap_recovers_exact_A_and_B():
    A, B = 1.55, 0.36
    x = np.linspace(0.2, 4.0, 30)
    y = A - B * x
    intercept, slope = evidence.bootstrap_line(
        x, y, np.random.default_rng(20), reps=32
    )
    assert np.allclose(intercept, A, atol=1e-12)
    assert np.allclose(-slope, B, atol=1e-12)


def test_likelihood_width_agrees_with_large_sample_fisher_limit():
    n, alpha, xt = 400, 2.5, 3.0
    # Deterministic quantiles from the Pareto survival law avoid Monte Carlo noise.
    q = (np.arange(n, dtype=float) + 0.5) / n
    tail = xt * (1.0 - q) ** (-1.0 / alpha)
    alpha_hat = n / np.log(tail / xt).sum()
    fisher = alpha_hat / np.sqrt(n)
    likelihood = evidence.likelihood_alpha_se(tail, xt)
    assert likelihood == pytest.approx(fisher, rel=0.04)


def test_comparison_fields_reports_paper_difference():
    difference, relative, within = evidence._comparison_fields(
        estimate=2.95,
        paper_value=3.00,
        standard_error=0.04,
        paper_se=0.10,
    )
    assert difference == pytest.approx(-0.05)
    assert relative == pytest.approx(-100.0 * 0.05 / 3.0)
    assert bool(within)
