"""Synthetic LS-versus-MLE experiment used by the manuscript.

This module contains only the deterministic synthetic experiment migrated from
project_ls_vs_mle. A single pseudo-random U(0,1) stream is generated with the
fixed manuscript seed, and every reported sample is a prefix of that stream.
No PNAD or Gompertz-Pareto analysis is performed here.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BETA = 10.0
ALPHA0 = 2.5
X_T = 1.0
DESIGN_X_MIN = 1.0
DESIGN_X_MAX = 20.0
RANDOM_SEED = 20260902
TABLE_1_SIZE = 50
SAMPLE_SIZES = (50, 100, 200, 500, 1000)

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES_DIR = REPO_ROOT / "assets" / "tables_synthetic"
FIGURES_DIR = REPO_ROOT / "assets" / "figures_synthetic"


def generate_uniform_stream() -> np.ndarray:
    """Generate the single authoritative pseudo-random stream."""
    if RANDOM_SEED != 20260902:
        raise AssertionError("Unexpected random seed.")
    rng = np.random.default_rng(RANDOM_SEED)
    return rng.random(max(SAMPLE_SIZES))


def construct_variables(u: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Construct design coordinates, deterministic response, and Pareto sample."""
    u = np.asarray(u, dtype=float)
    x = DESIGN_X_MIN + (DESIGN_X_MAX - DESIGN_X_MIN) * u
    y = BETA * x ** (-ALPHA0)
    X = X_T * (1.0 - u) ** (-1.0 / ALPHA0)
    return x, y, X


def fit_log_log_ls(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Estimate alpha and beta from log(y)=log(beta)-alpha log(x)."""
    slope, intercept = np.polyfit(np.log(x), np.log(y), 1)
    return float(-slope), float(np.exp(intercept))


def corrected_mle_alpha(values: np.ndarray, x_t: float = X_T) -> float:
    """Return the finite-sample corrected Pareto-form estimator."""
    values = np.asarray(values, dtype=float)
    n = values.size
    if n <= 1 or np.any(values < x_t):
        raise ValueError("Require n > 1 and all values >= x_t.")
    denominator = float(np.log(values / x_t).sum())
    if denominator <= 0:
        raise ValueError("Log-ratio sum must be positive.")
    return float((n - 1) / denominator)


def build_table_1(u_stream: np.ndarray) -> pd.DataFrame:
    """Build the n=50 observation table sorted by x_i and numbered 1,...,50."""
    u = np.asarray(u_stream[:TABLE_1_SIZE], dtype=float)
    x, y, X = construct_variables(u)

    table = pd.DataFrame(
        {
            "i": np.arange(1, TABLE_1_SIZE + 1, dtype=int),
            "x_i": x,
            "y_i": y,
            "U_i": u,
            "X_i": X,
            "ln(X_i/x_t)": np.log(X / X_T),
            "ln(x_i/x_t)": np.log(x / X_T),
        }
    )
    table = table.sort_values("x_i", kind="mergesort").reset_index(drop=True)
    table["i"] = np.arange(1, TABLE_1_SIZE + 1, dtype=int)
    return table


def build_nested_samples(u_stream: np.ndarray) -> dict[int, np.ndarray]:
    """Return nested prefixes of the single authoritative U stream."""
    return {n: np.asarray(u_stream[:n], dtype=float).copy() for n in SAMPLE_SIZES}


def build_table_2(u_stream: np.ndarray) -> pd.DataFrame:
    """Build the sample-size comparison table from nested stream prefixes."""
    nested = build_nested_samples(u_stream)
    rows = []

    for n in SAMPLE_SIZES:
        u = nested[n]
        x, y, X = construct_variables(u)
        ls_alpha, ls_beta = fit_log_log_ls(x, y)

        if not np.isclose(ls_alpha, ALPHA0, rtol=0.0, atol=1e-12):
            raise AssertionError(f"LS alpha mismatch for n={n}: {ls_alpha}")
        if not np.isclose(ls_beta, BETA, rtol=0.0, atol=1e-12):
            raise AssertionError(f"LS beta mismatch for n={n}: {ls_beta}")

        rows.append(
            {
                "n": n,
                "ls_alpha": ls_alpha,
                "pareto_mle_corrected_alpha": corrected_mle_alpha(X),
                "direct_design_mle_corrected_alpha": corrected_mle_alpha(x),
            }
        )

    return pd.DataFrame(rows)


def validate_outputs(
    u_stream: np.ndarray,
    table_1: pd.DataFrame,
    table_2: pd.DataFrame,
) -> None:
    """Validate all manuscript invariants before writing outputs."""
    if RANDOM_SEED != 20260902:
        raise AssertionError("Seed validation failed.")
    if u_stream.size != max(SAMPLE_SIZES):
        raise AssertionError("Unexpected stream length.")
    if np.any((u_stream < 0.0) | (u_stream >= 1.0)):
        raise AssertionError("Uniform stream outside [0, 1).")

    x, y, X = construct_variables(u_stream)
    np.testing.assert_allclose(x, 1.0 + 19.0 * u_stream, rtol=0.0, atol=1e-14)
    np.testing.assert_allclose(y, BETA * x ** (-ALPHA0), rtol=0.0, atol=1e-14)
    np.testing.assert_allclose(
        X,
        X_T * (1.0 - u_stream) ** (-1.0 / ALPHA0),
        rtol=0.0,
        atol=1e-14,
    )

    if len(table_1) != TABLE_1_SIZE:
        raise AssertionError("Table 1 must contain exactly 50 rows.")
    if not table_1["x_i"].is_monotonic_increasing:
        raise AssertionError("Table 1 must be sorted by x_i.")
    np.testing.assert_array_equal(
        table_1["i"].to_numpy(),
        np.arange(1, TABLE_1_SIZE + 1, dtype=int),
    )
    if table_1.isna().any().any() or table_2.isna().any().any():
        raise AssertionError("Synthetic tables must not contain NaN values.")
    if not np.isfinite(table_1.select_dtypes(include=[np.number]).to_numpy()).all():
        raise AssertionError("Table 1 contains non-finite values.")
    if not np.isfinite(table_2.select_dtypes(include=[np.number]).to_numpy()).all():
        raise AssertionError("Table 2 contains non-finite values.")

    # Sorting and display renumbering must preserve the same first 50 draws.
    np.testing.assert_array_equal(
        table_1["U_i"].to_numpy(),
        np.sort(u_stream[:TABLE_1_SIZE]),
    )

    nested = build_nested_samples(u_stream)
    previous_n = None
    for n in SAMPLE_SIZES:
        if previous_n is not None:
            np.testing.assert_array_equal(nested[n][:previous_n], nested[previous_n])
        previous_n = n

    row_50 = table_2.loc[table_2["n"] == TABLE_1_SIZE]
    if len(row_50) != 1:
        raise AssertionError("Table 2 must contain exactly one n=50 row.")

    x50 = table_1["x_i"].to_numpy()
    y50 = table_1["y_i"].to_numpy()
    X50 = table_1["X_i"].to_numpy()
    ls_alpha_50, ls_beta_50 = fit_log_log_ls(x50, y50)

    if not np.isclose(ls_alpha_50, ALPHA0, rtol=0.0, atol=1e-12):
        raise AssertionError("Table 1 LS alpha does not recover alpha0.")
    if not np.isclose(ls_beta_50, BETA, rtol=0.0, atol=1e-12):
        raise AssertionError("Table 1 LS beta does not recover beta.")

    np.testing.assert_allclose(
        row_50["ls_alpha"].iloc[0], ls_alpha_50, rtol=0.0, atol=1e-14
    )
    np.testing.assert_allclose(
        row_50["pareto_mle_corrected_alpha"].iloc[0],
        corrected_mle_alpha(X50),
        rtol=0.0,
        atol=1e-14,
    )
    np.testing.assert_allclose(
        row_50["direct_design_mle_corrected_alpha"].iloc[0],
        corrected_mle_alpha(x50),
        rtol=0.0,
        atol=1e-14,
    )


def main() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate, validate, and persist Tables 1 and 2."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    u_stream = generate_uniform_stream()
    table_1 = build_table_1(u_stream)
    table_2 = build_table_2(u_stream)
    validate_outputs(u_stream, table_1, table_2)

    table_1.to_csv(TABLES_DIR / "table_1.csv", index=False)
    table_2.to_csv(TABLES_DIR / "table_2.csv", index=False)
    return table_1, table_2


if __name__ == "__main__":
    main()
