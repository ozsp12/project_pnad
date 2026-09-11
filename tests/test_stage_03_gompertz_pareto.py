from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.stage_03_pnad_analysis import (
    BIN_RATIO,
    GOMPERTZ_ANNUAL_COLUMNS,
    GOMPERTZ_A_THEORY,
    PARETO_ANNUAL_COLUMNS,
    build_regime_ccdf,
    determine_threshold,
    direct_pareto_mle,
    fit_pareto_ls,
    linear_fit,
    select_gompertz_region,
    split_regime_annual,
)


def test_default_geometric_ratio_matches_moura_ribeiro():
    assert BIN_RATIO == pytest.approx(1.10)


def test_linear_fit_accepts_distinct_small_abscissae():
    x = np.geomspace(1.0e-5, 2.0e-4, 12)
    y = 1.53 - 0.35 * x

    fit = linear_fit(x, y)

    assert fit["intercept"] == pytest.approx(1.53, abs=1e-12)
    assert fit["slope"] == pytest.approx(-0.35, abs=1e-10)
    assert fit["fit_r2"] == pytest.approx(1.0, abs=1e-10)


def test_gompertz_final_fit_fixes_A_and_recovers_B():
    A = GOMPERTZ_A_THEORY
    B = 0.35
    x = np.geomspace(0.1, 6.0, 18)
    F = np.exp(np.exp(A - B * x))
    regime = pd.DataFrame({
        "income_normalized": x,
        "bin_right_normalized": x * BIN_RATIO,
        "observations_in_bin": np.ones_like(x, dtype=int),
        "empirical_ccdf_probability": F / 100.0,
        "empirical_ccdf_percent": F,
        "gompertz_transform": np.log(np.log(F)),
    })

    result = select_gompertz_region(regime)

    assert result["gompertz_A"] == pytest.approx(GOMPERTZ_A_THEORY, abs=1e-12)
    assert result["gompertz_B"] == pytest.approx(B, abs=1e-10)
    assert result["gompertz_r2"] == pytest.approx(1.0, abs=1e-12)
    assert 1.4 <= result["gompertz_boundary_A_free"] <= 1.6


def test_transition_threshold_uses_boundary_midpoint():
    x_t, delta, rule = determine_threshold(6.0, 8.0)

    assert x_t == pytest.approx(7.0)
    assert delta == pytest.approx(1.0)
    assert rule == "midpoint_between_regime_bounds"


def test_transition_threshold_is_exact_when_boundaries_coincide():
    x_t, delta, rule = determine_threshold(7.4, 7.4)

    assert x_t == pytest.approx(7.4)
    assert delta == pytest.approx(0.0)
    assert rule == "coincident_regime_bounds"


def test_direct_pareto_mle_matches_closed_form():
    x_t = 2.0
    tail = np.array([2.0, 3.0, 4.0, 8.0, 10.0])
    alpha, _, n = direct_pareto_mle(tail, x_t)
    expected = n / np.log(tail / x_t).sum()

    assert n == 5
    assert alpha == pytest.approx(expected)


def test_pareto_ls_recovers_power_law_slope():
    alpha = 2.5
    beta = 40.0
    x = np.geomspace(2.0, 20.0, 12)
    F = beta * x ** (-alpha)
    regime = pd.DataFrame({
        "income_normalized": x,
        "observations_in_bin": np.ones_like(x, dtype=int),
        "empirical_ccdf_percent": F,
    })

    fitted_alpha, fitted_beta, r2, _ = fit_pareto_ls(regime, 2.0)

    assert fitted_alpha == pytest.approx(alpha, abs=1e-10)
    assert fitted_beta == pytest.approx(beta, abs=1e-10)
    assert r2 == pytest.approx(1.0, abs=1e-12)


def test_regime_ccdf_uses_geometric_thresholds_and_percentage_ccdf():
    income = np.geomspace(0.1, 20.0, 500)
    regime = build_regime_ccdf(income)
    thresholds = regime["income_normalized"].to_numpy(float)
    ratios = thresholds[1:] / thresholds[:-1]

    assert ratios.size > 0
    np.testing.assert_allclose(ratios, BIN_RATIO, rtol=1e-12, atol=1e-12)
    assert regime["empirical_ccdf_percent"].max() <= 100.0
    assert regime["empirical_ccdf_percent"].max() > 1.0


def test_regime_annual_output_is_split_into_gompertz_and_pareto_tables():
    columns = list(dict.fromkeys(GOMPERTZ_ANNUAL_COLUMNS + PARETO_ANNUAL_COLUMNS))
    row = {column: 1.0 for column in columns}
    row["year"] = 2025
    regime_fits = pd.DataFrame([row])

    gompertz, pareto = split_regime_annual(regime_fits)

    assert list(gompertz.columns) == GOMPERTZ_ANNUAL_COLUMNS
    assert list(pareto.columns) == PARETO_ANNUAL_COLUMNS
    assert set(gompertz.columns).intersection(pareto.columns) == {"year"}
