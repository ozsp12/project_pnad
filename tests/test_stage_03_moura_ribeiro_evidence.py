from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_03_pnad_analysis as evidence


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
    q = (np.arange(n, dtype=float) + 0.5) / n
    tail = xt * (1.0 - q) ** (-1.0 / alpha)
    alpha_hat = n / np.log(tail / xt).sum()
    fisher = alpha_hat / np.sqrt(n)
    likelihood = evidence.likelihood_alpha_se(tail, xt)
    assert likelihood == pytest.approx(fisher, rel=0.04)


def test_analysis_metadata_documents_all_six_canonical_tables():
    frames = {
        name: pd.DataFrame(columns=["year", f"field_{i}"])
        for i, name in enumerate(evidence.ANALYSIS_TABLES)
    }
    metadata = evidence.build_metadata_table(frames)
    documented_tables = set(metadata["table_name"])
    assert set(evidence.ANALYSIS_TABLES).issubset(documented_tables)
    assert evidence.METADATA_FILE in documented_tables
    assert {
        "table_name", "table_description", "column_name",
        "description", "unit", "source",
    } == set(metadata.columns)


def test_canonical_analysis_file_set_is_six_tables_plus_metadata():
    assert len(evidence.ANALYSIS_TABLES) == 6
    assert evidence.CANONICAL_FILES == set(evidence.ANALYSIS_TABLES) | {"metadata.csv"}


def test_metadata_uses_scientific_definitions_and_units():
    assert evidence._description("Gini") == (
        "Gini coefficient computed from the annual analytical income distribution."
    )
    assert evidence._description("mean") == (
        "Arithmetic mean income converted to constant 2025 US$."
    )
    assert evidence._description("gompertz_ccdf_at_x_t_percent").startswith(
        "Gompertz CCDF evaluated at the transition threshold"
    )
    assert evidence._unit("mean") == "2025 US$"
    assert evidence._unit("bin_left") == "2025 US$"
    assert evidence._unit("n_zero") == "count"
    assert evidence._unit("gompertz_ccdf_at_x_t_percent") == "%"
    assert evidence._unit("pareto_fitted_ccdf_percent_mle") == "%"


def test_metadata_sources_distinguish_external_and_inference_fields():
    assert "IPEA" in evidence._source("IPEA")
    assert "World Bank" in evidence._source("Banco_Mundial")
    assert "bootstrap" in evidence._source("gompertz_B_bootstrap_se").lower()
    assert "likelihood" in evidence._source("pareto_alpha_mle_likelihood_se").lower()
