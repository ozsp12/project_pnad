"""Augment the canonical Stage-03 tables with Moura Jr.--Ribeiro diagnostics.

The baseline (refined) and benchmark (trusted) analytical layers deliberately
share the same table names and schemas. This module computes the bootstrap,
likelihood-width and reproduction diagnostics required by the 2009 method, but
stores them directly in ``gompertz_annual.csv`` and ``pareto_annual.csv``.
No separate bootstrap or reproduction CSV is persisted.

Each analytical layer therefore contains the same six scientific tables plus a
``metadata.csv`` data dictionary.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data" / "metadata" / "df_metadata.xlsx"

START_YEAR, END_YEAR = 1978, 2025
BOOTSTRAP_REPS = int(os.environ.get("PNAD_BOOTSTRAP_REPS", "1000"))
BOOTSTRAP_SEED = 20090101
LIKELIHOOD_GRID_SIZE = 12001

LAYER_CONFIG = {
    "refined": {
        "role": "baseline",
        "data": ROOT / "data" / "refined",
        "tables": ROOT / "assets" / "tables_analysis_refined",
        "pattern": "pnad_refined_{year}.parquet",
    },
    "trusted": {
        "role": "benchmark",
        "data": ROOT / "data" / "trusted",
        "tables": ROOT / "assets" / "tables_analysis_trusted",
        "pattern": "pnad_trusted_{year}.parquet",
    },
}

ANALYSIS_TABLES = (
    "statistics_annual.csv",
    "geometric_bins.csv",
    "gompertz_annual.csv",
    "pareto_annual.csv",
    "gompertz_pareto_curves.csv",
    "lorenz.csv",
)
METADATA_FILE = "metadata.csv"
CANONICAL_FILES = set(ANALYSIS_TABLES) | {METADATA_FILE}

TABLE_DESCRIPTIONS = {
    "statistics_annual.csv": (
        "Annual sample counts, nominal and 2025-US$ income statistics, inequality "
        "indices, top-income shares, and external Gini comparisons."
    ),
    "geometric_bins.csv": (
        "Geometric-bin summaries of annual income expressed in constant 2025 US$, "
        "using the canonical multiplicative bin ratio 1.10."
    ),
    "gompertz_annual.csv": (
        "Annual Gompertz-body estimates, free-intercept diagnostics, bootstrap "
        "uncertainties, exponential comparison diagnostics, and body population/income shares."
    ),
    "pareto_annual.csv": (
        "Annual Pareto-tail boundaries and estimates from log-log least squares and "
        "direct maximum likelihood, with Fisher, likelihood-width, and bootstrap uncertainties."
    ),
    "gompertz_pareto_curves.csv": (
        "Binned empirical CCDF coordinates and fitted Gompertz/Pareto curves used for "
        "regime selection, estimation, diagnostics, and publication figures."
    ),
    "lorenz.csv": (
        "Annual Lorenz-curve coordinates giving cumulative population and income shares."
    ),
    METADATA_FILE: (
        "Data dictionary describing every canonical Stage-03 analytical table and column."
    ),
}

GOMPERTZ_DIAGNOSTIC_COLUMNS = [
    "bootstrap_reps",
    "gompertz_B_bootstrap_se",
    "gompertz_A_free_bootstrap_se",
    "gompertz_B_free_bootstrap_se",
    "exponential_intercept",
    "exponential_alpha",
    "exponential_r2",
    "gompertz_income_share_pct",
]

PARETO_DIAGNOSTIC_COLUMNS = [
    "bootstrap_reps",
    "pareto_alpha_ls_bootstrap_se",
    "pareto_beta_ls_bootstrap_se",
    "pareto_alpha_mle_likelihood_se",
    "pareto_alpha_mle_bootstrap_se",
    "pareto_beta_mle_likelihood_se",
    "pareto_beta_mle_bootstrap_se",
    "pareto_mle_r2",
    "pareto_supported",
    "pareto_income_share_pct",
]

COLUMN_DESCRIPTIONS = {
    "year": "PNAD or PNAD Contínua survey/reference year.",
    "N": "Total number of observations in the analytical annual sample.",
    "N_valid": "Number of observations with valid finite income values used in annual statistics.",
    "n_nan": "Number of observations with missing or non-numeric income.",
    "n_zero": "Number of observations with zero income.",
    "n_negative": "Number of observations with negative income.",
    "xmin_positive_nominal": "Smallest strictly positive income in the original nominal monetary scale.",
    "xmax_nominal": "Largest income in the original nominal monetary scale.",
    "mean_nominal": "Arithmetic mean income in the original nominal monetary scale.",
    "median_nominal": "Median income in the original nominal monetary scale.",
    "std_nominal": "Sample standard deviation of income in the original nominal monetary scale.",
    "income_sum_nominal": "Sum of income in the original nominal monetary scale.",
    "xmin_positive": "Smallest strictly positive income converted to constant 2025 US$.",
    "xmax": "Largest income converted to constant 2025 US$.",
    "mean": "Arithmetic mean income converted to constant 2025 US$.",
    "median": "Median income converted to constant 2025 US$.",
    "std": "Sample standard deviation of income converted to constant 2025 US$.",
    "income_sum": "Sum of income converted to constant 2025 US$.",
    "Gini": "Gini coefficient computed from the annual analytical income distribution.",
    "Pietra": "Pietra index computed from the annual Lorenz curve.",
    "Kolkata": "Kolkata index as a population fraction, defined by the Lorenz-curve crossing condition.",
    "Kolkata_pct": "Kolkata index expressed as a percentage of the population.",
    "Zanardi": "Zanardi inequality index computed from the annual income distribution.",
    "top_10": "Fraction of total income received by the top 10% of observations ranked by income.",
    "top_1": "Fraction of total income received by the top 1% of observations ranked by income.",
    "top_01": "Fraction of total income received by the top 0.1% of observations ranked by income.",
    "IPEA": "External IPEA Gini coefficient for the corresponding year, when available.",
    "Banco_Mundial": "External World Bank Gini coefficient for the corresponding year, when available.",
    "diff_IPEA": "Difference between the Stage-03 Gini estimate and the IPEA Gini value.",
    "diff_Banco_Mundial": "Difference between the Stage-03 Gini estimate and the World Bank Gini value.",
    "bin_left": "Lower boundary of the geometric income bin in constant 2025 US$.",
    "bin_right": "Upper boundary of the geometric income bin in constant 2025 US$.",
    "bin_center_geo": "Geometric center of the income bin in constant 2025 US$.",
    "N_bin": "Number of observations assigned to the geometric income bin.",
    "geometric_mean": "Geometric mean income within the bin in constant 2025 US$.",
    "ccdf": "Empirical complementary cumulative distribution evaluated at the bin threshold as a probability.",
    "log_bin_ratio": "Multiplicative ratio between consecutive geometric-bin boundaries; fixed at 1.10 in the canonical analysis.",
    "normalization_mean_income_adj_2025_usd": "Annual positive-income mean in constant 2025 US$, used to normalize income before regime fitting.",
    "positive_income_observation_n": "Number of strictly positive income observations entering the normalized distribution analysis.",
    "gompertz_A": "Canonical Gompertz parameter A fixed by G(0)=100, so A=ln[ln(100)].",
    "gompertz_B": "Canonical Gompertz slope parameter B estimated by least squares with A fixed.",
    "gompertz_r2": "Coefficient of determination of the selected fixed-A Gompertz fit in transformed coordinates.",
    "gompertz_sse": "Sum of squared residuals of the selected fixed-A Gompertz fit in transformed coordinates.",
    "gompertz_x_gmax": "Upper normalized-income boundary of the selected Gompertz regime.",
    "gompertz_point_n": "Number of binned CCDF points used in the selected Gompertz fit.",
    "gompertz_selection_status": "Rule/status describing how the upper Gompertz boundary was selected.",
    "gompertz_boundary_A_free": "Intercept A from the unconstrained Gompertz linearization used as a boundary and 2009-method diagnostic.",
    "gompertz_boundary_B_free": "Slope parameter B from the unconstrained Gompertz linearization used as a boundary and 2009-method diagnostic.",
    "gompertz_boundary_r2_free": "Coefficient of determination of the unconstrained free-intercept Gompertz diagnostic fit.",
    "gompertz_population_n": "Number of observations assigned below the Gompertz-Pareto transition threshold.",
    "gompertz_population_pct": "Percentage of observations assigned below the Gompertz-Pareto transition threshold.",
    "gompertz_ccdf_at_x_t_percent": "Gompertz CCDF evaluated at the transition threshold, expressed in percent.",
    "bootstrap_reps": "Number of bootstrap resamples used to estimate the reported bootstrap standard errors.",
    "gompertz_B_bootstrap_se": "Bootstrap standard error of the canonical fixed-A Gompertz B estimate.",
    "gompertz_A_free_bootstrap_se": "Bootstrap standard error of the free-intercept Gompertz A diagnostic.",
    "gompertz_B_free_bootstrap_se": "Bootstrap standard error of the free-intercept Gompertz B diagnostic.",
    "exponential_intercept": "Intercept of the comparison fit ln F(x)=c-alpha x over the selected Gompertz interval.",
    "exponential_alpha": "Positive decay coefficient alpha of the comparison exponential-body fit.",
    "exponential_r2": "Coefficient of determination of the comparison exponential-body fit.",
    "gompertz_income_share_pct": "Percentage of total income received by observations below the transition threshold.",
    "pareto_x_pmin": "Lower normalized-income boundary selected for the Pareto tail.",
    "pareto_selection_alpha": "Pareto exponent from the candidate tail fit used during threshold selection.",
    "pareto_selection_r2": "Coefficient of determination of the candidate log-log Pareto fit used during threshold selection.",
    "pareto_selection_status": "Rule/status describing how the lower Pareto boundary was selected.",
    "transition_x_t": "Normalized-income threshold joining the Gompertz body and Pareto tail.",
    "transition_delta_x_t": "Half-width of the gap between selected Gompertz and Pareto boundaries when they do not coincide.",
    "transition_rule": "Rule used to define x_t from the selected Gompertz and Pareto boundaries.",
    "pareto_population_n": "Number of observations assigned at or above the Pareto transition threshold.",
    "pareto_population_pct": "Percentage of observations assigned at or above the Pareto transition threshold.",
    "pareto_alpha_ls": "Pareto exponent alpha estimated by log-log least squares.",
    "pareto_beta_ls": "Pareto amplitude beta estimated by log-log least squares on the percent-scale CCDF.",
    "pareto_ls_r2": "Coefficient of determination of the selected log-log least-squares Pareto fit.",
    "pareto_ls_sse": "Sum of squared residuals of the selected log-log least-squares Pareto fit.",
    "pareto_alpha_mle": "Pareto exponent alpha estimated directly by maximum likelihood above x_t.",
    "pareto_alpha_mle_fisher_se": "Asymptotic Fisher-information standard error of the direct-MLE Pareto exponent.",
    "pareto_beta_mle_continuity": "Pareto amplitude beta determined by enforcing Gompertz-Pareto continuity at x_t.",
    "cutoff_normalized": "Normalized-income cutoff associated with the selected transition/tail analysis.",
    "cutoff_income_adj": "Monetary value of the cutoff converted to constant 2025 US$.",
    "pareto_alpha": "Compatibility field for the canonical Pareto exponent retained in the Stage-03 output.",
    "pareto_r2": "Compatibility field for the canonical Pareto goodness-of-fit statistic retained in the Stage-03 output.",
    "pareto_alpha_ls_bootstrap_se": "Bootstrap standard error of the log-log least-squares Pareto exponent.",
    "pareto_beta_ls_bootstrap_se": "Bootstrap standard error of the log-log least-squares Pareto amplitude.",
    "pareto_alpha_mle_bootstrap_se": "Bootstrap standard error of the direct-MLE Pareto exponent.",
    "pareto_beta_mle_bootstrap_se": "Bootstrap standard error of the continuity-based direct-MLE Pareto amplitude.",
    "pareto_alpha_mle_likelihood_se": "Likelihood-width standard error of the direct-MLE Pareto exponent following the 2009 prescription.",
    "pareto_beta_mle_likelihood_se": "Uncertainty in continuity-based Pareto beta propagated from the likelihood-width alpha uncertainty.",
    "pareto_mle_r2": "Log-scale coefficient of determination of the direct-MLE Pareto curve against the empirical CCDF.",
    "pareto_supported": "Whether the selected Pareto tail satisfies the configured support criterion.",
    "pareto_income_share_pct": "Percentage of total income received by observations at or above the transition threshold.",
    "income_normalized": "Income divided by the annual mean of strictly positive income observations.",
    "bin_right_normalized": "Upper boundary of the corresponding geometric bin expressed in normalized-income units.",
    "observations_in_bin": "Number of observations represented by the binned CCDF point.",
    "empirical_ccdf_probability": "Empirical complementary cumulative distribution as a probability in [0,1].",
    "empirical_ccdf_percent": "Empirical complementary cumulative distribution expressed in percent.",
    "gompertz_transform": "Double-log Gompertz transform ln[ln F(x)] using F on the percent scale.",
    "regime": "Regime label identifying whether the binned point belongs to the Gompertz body, transition, or Pareto tail.",
    "income_adj_2025_usd": "Income coordinate of the binned point converted to constant 2025 US$.",
    "gompertz_fitted_transform": "Fitted fixed-A Gompertz relation A-Bx in double-log transformed coordinates.",
    "pareto_fitted_ccdf_percent_ls": "Pareto CCDF fitted by log-log least squares, expressed in percent.",
    "pareto_fitted_ccdf_percent_mle": "Pareto CCDF fitted with the direct-MLE exponent and continuity amplitude, expressed in percent.",
    "pareto_fitted_ccdf_percent": "Canonical Pareto fitted CCDF retained for compatibility, expressed in percent.",
    "population_share": "Cumulative share of observations along the Lorenz curve.",
    "income_share": "Cumulative share of total income along the Lorenz curve.",
}

COLUMN_UNITS = {
    "year": "year",
    "N": "count",
    "N_valid": "count",
    "n_nan": "count",
    "n_zero": "count",
    "n_negative": "count",
    "xmin_positive_nominal": "nominal currency units",
    "xmax_nominal": "nominal currency units",
    "mean_nominal": "nominal currency units",
    "median_nominal": "nominal currency units",
    "std_nominal": "nominal currency units",
    "income_sum_nominal": "nominal currency units",
    "xmin_positive": "2025 US$",
    "xmax": "2025 US$",
    "mean": "2025 US$",
    "median": "2025 US$",
    "std": "2025 US$",
    "income_sum": "2025 US$",
    "Gini": "dimensionless",
    "Pietra": "dimensionless",
    "Kolkata": "fraction",
    "Kolkata_pct": "%",
    "Zanardi": "dimensionless",
    "top_10": "fraction",
    "top_1": "fraction",
    "top_01": "fraction",
    "IPEA": "dimensionless",
    "Banco_Mundial": "dimensionless",
    "diff_IPEA": "dimensionless",
    "diff_Banco_Mundial": "dimensionless",
    "bin_left": "2025 US$",
    "bin_right": "2025 US$",
    "bin_center_geo": "2025 US$",
    "N_bin": "count",
    "geometric_mean": "2025 US$",
    "ccdf": "fraction",
    "log_bin_ratio": "dimensionless",
    "normalization_mean_income_adj_2025_usd": "2025 US$",
    "positive_income_observation_n": "count",
    "gompertz_point_n": "count",
    "gompertz_selection_status": "text",
    "gompertz_population_n": "count",
    "gompertz_population_pct": "%",
    "gompertz_ccdf_at_x_t_percent": "%",
    "bootstrap_reps": "count",
    "gompertz_income_share_pct": "%",
    "pareto_selection_status": "text",
    "transition_rule": "text",
    "pareto_population_n": "count",
    "pareto_population_pct": "%",
    "pareto_beta_ls": "CCDF-percent scale",
    "pareto_beta_mle_continuity": "CCDF-percent scale",
    "cutoff_income_adj": "2025 US$",
    "pareto_beta_ls_bootstrap_se": "CCDF-percent scale",
    "pareto_beta_mle_bootstrap_se": "CCDF-percent scale",
    "pareto_beta_mle_likelihood_se": "CCDF-percent scale",
    "pareto_supported": "boolean",
    "pareto_income_share_pct": "%",
    "income_normalized": "normalized income",
    "bin_right_normalized": "normalized income",
    "observations_in_bin": "count",
    "empirical_ccdf_probability": "fraction",
    "empirical_ccdf_percent": "%",
    "regime": "text",
    "gompertz_x_gmax": "normalized income",
    "pareto_x_pmin": "normalized income",
    "transition_x_t": "normalized income",
    "transition_delta_x_t": "normalized income",
    "cutoff_normalized": "normalized income",
    "income_adj_2025_usd": "2025 US$",
    "pareto_fitted_ccdf_percent_ls": "%",
    "pareto_fitted_ccdf_percent_mle": "%",
    "pareto_fitted_ccdf_percent": "%",
    "population_share": "fraction",
    "income_share": "fraction",
}


def years_of(values) -> list[int]:
    return sorted(
        int(year)
        for year in values
        if pd.notna(year) and START_YEAR <= int(year) <= END_YEAR
    )


def r2_log(observed, fitted) -> float:
    observed = np.asarray(observed, float)
    fitted = np.asarray(fitted, float)
    mask = (
        np.isfinite(observed)
        & np.isfinite(fitted)
        & (observed > 0)
        & (fitted > 0)
    )
    if mask.sum() < 2:
        return np.nan
    y = np.log(observed[mask])
    yh = np.log(fitted[mask])
    tss = float(np.sum((y - y.mean()) ** 2))
    if tss <= 0:
        return np.nan
    return float(1.0 - np.sum((y - yh) ** 2) / tss)


def bootstrap_line(x, y, rng, reps=BOOTSTRAP_REPS):
    """Bootstrap an unconstrained line ``y = intercept + slope*x``."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3:
        nan = np.full(reps, np.nan)
        return nan.copy(), nan.copy()

    idx = rng.integers(0, len(x), size=(reps, len(x)))
    xb, yb = x[idx], y[idx]
    xm, ym = xb.mean(axis=1), yb.mean(axis=1)
    den = ((xb - xm[:, None]) ** 2).sum(axis=1)
    slope = np.divide(
        ((xb - xm[:, None]) * (yb - ym[:, None])).sum(axis=1),
        den,
        out=np.full(reps, np.nan),
        where=den > 0,
    )
    return ym - slope * xm, slope


def bootstrap_fixed_gompertz_B(x, y, A, rng, reps=BOOTSTRAP_REPS):
    """Bootstrap ``B`` in ``y=A-Bx`` while preserving the theoretical fixed A."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3:
        return np.full(reps, np.nan)

    idx = rng.integers(0, len(x), size=(reps, len(x)))
    xb, yb = x[idx], y[idx]
    den = (xb**2).sum(axis=1)
    num = (xb * (float(A) - yb)).sum(axis=1)
    return np.divide(
        num,
        den,
        out=np.full(reps, np.nan),
        where=den > 0,
    )


def likelihood_alpha_se(tail, x_t, grid_size=LIKELIHOOD_GRID_SIZE) -> float:
    """Numerically reproduce the likelihood-width error used in the 2009 paper."""
    tail = np.asarray(tail, float)
    tail = tail[np.isfinite(tail) & (tail >= x_t)]
    n = int(tail.size)
    if n < 2 or not np.isfinite(x_t) or x_t <= 0:
        return np.nan

    c = float(np.log(tail / x_t).sum())
    if c <= 0:
        return np.nan

    alpha_hat = float(n / c)
    fisher = alpha_hat / np.sqrt(n)
    upper = max(8.0, alpha_hat + 14.0 * max(fisher, 0.05))
    alpha = np.linspace(1.0, upper, int(grid_size))
    logw = n * np.log(alpha) - c * alpha
    logw -= np.max(logw)
    weight = np.exp(logw)
    norm = float(np.trapezoid(weight, alpha))
    if not np.isfinite(norm) or norm <= 0:
        return np.nan

    mean = float(np.trapezoid(alpha * weight, alpha) / norm)
    mean2 = float(np.trapezoid(alpha * alpha * weight, alpha) / norm)
    return float(np.sqrt(max(0.0, mean2 - mean * mean)))


def _load_layer(layer: str):
    if layer not in LAYER_CONFIG:
        raise ValueError(f"Unknown layer: {layer}")
    cfg = LAYER_CONFIG[layer]
    tables = cfg["tables"]

    gompertz = pd.read_csv(tables / "gompertz_annual.csv")
    pareto = pd.read_csv(tables / "pareto_annual.csv")
    curves = pd.read_csv(tables / "gompertz_pareto_curves.csv")
    annual = gompertz.merge(
        pareto,
        on="year",
        how="inner",
        validate="one_to_one",
        suffixes=("", "_pareto"),
    )
    metadata = pd.read_excel(METADATA).rename(columns={"ano": "year"})

    for frame in (gompertz, pareto, annual, curves, metadata):
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")

    years = years_of(annual["year"].dropna())
    return cfg, gompertz, pareto, annual, curves, metadata, years


def _income(year: int, cfg, positive=True) -> np.ndarray:
    path = cfg["data"] / cfg["pattern"].format(year=year)
    frame = pd.read_parquet(path, columns=["renda"])
    income = pd.to_numeric(frame["renda"], errors="coerce").to_numpy(float)
    income = income[np.isfinite(income)]
    return income[income > 0] if positive else income


def _normalized_income(year: int, cfg) -> np.ndarray:
    x = _income(year, cfg, positive=True)
    mean = float(np.mean(x))
    if x.size == 0 or not np.isfinite(mean) or mean <= 0:
        raise ValueError(f"{year}: invalid positive-income sample")
    return x / mean


def build_bootstrap_uncertainties(layer: str) -> pd.DataFrame:
    """Compute annual bootstrap uncertainties without persisting a separate CSV."""
    cfg, _, _, annual, curves, _, years = _load_layer(layer)
    annual_i = annual.set_index("year")
    rows = []

    for year in years:
        fit = annual_i.loc[year]
        rng = np.random.default_rng(BOOTSTRAP_SEED + year)

        x_gmax = float(fit["gompertz_x_gmax"])
        g = curves[
            (curves["year"] == year)
            & (curves["income_normalized"] <= x_gmax)
            & curves["gompertz_transform"].notna()
        ]
        xg = g["income_normalized"].to_numpy(float)
        yg = g["gompertz_transform"].to_numpy(float)
        fixed_B = bootstrap_fixed_gompertz_B(
            xg, yg, float(fit["gompertz_A"]), rng
        )
        free_A, free_slope = bootstrap_line(xg, yg, rng)
        free_B = -free_slope

        x_pmin = float(fit["pareto_x_pmin"])
        p = curves[
            (curves["year"] == year)
            & (curves["income_normalized"] >= x_pmin)
            & (curves["empirical_ccdf_percent"] > 0)
        ]
        ls_intercept, ls_slope = bootstrap_line(
            np.log(p["income_normalized"].to_numpy(float)),
            np.log(p["empirical_ccdf_percent"].to_numpy(float)),
            rng,
        )

        x_t = float(fit["transition_x_t"])
        x = _normalized_income(year, cfg)
        z = np.log(x[x >= x_t] / x_t)
        n = int(len(z))
        if n < 2:
            alpha_mle = np.full(BOOTSTRAP_REPS, np.nan)
        else:
            idx = rng.integers(0, n, size=(BOOTSTRAP_REPS, n))
            sums = z[idx].sum(axis=1)
            alpha_mle = np.divide(
                n,
                sums,
                out=np.full(BOOTSTRAP_REPS, np.nan),
                where=sums > 0,
            )

        f_t = float(
            np.exp(
                np.exp(
                    float(fit["gompertz_A"])
                    - float(fit["gompertz_B"]) * x_t
                )
            )
        )
        beta_mle = f_t * x_t**alpha_mle

        def sd(values):
            return float(np.nanstd(values, ddof=1))

        rows.append(
            {
                "year": year,
                "bootstrap_reps": BOOTSTRAP_REPS,
                "gompertz_B_bootstrap_se": sd(fixed_B),
                "gompertz_A_free_bootstrap_se": sd(free_A),
                "gompertz_B_free_bootstrap_se": sd(free_B),
                "pareto_alpha_ls_bootstrap_se": sd(-ls_slope),
                "pareto_beta_ls_bootstrap_se": sd(np.exp(ls_intercept)),
                "pareto_alpha_mle_bootstrap_se": sd(alpha_mle),
                "pareto_beta_mle_bootstrap_se": sd(beta_mle),
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def _exponential_diagnostics(curves, fit, year):
    x_gmax = float(fit["gompertz_x_gmax"])
    data = curves[
        (curves["year"] == year)
        & (curves["income_normalized"] <= x_gmax)
        & (curves["empirical_ccdf_percent"] > 0)
    ]
    x = data["income_normalized"].to_numpy(float)
    y = np.log(data["empirical_ccdf_percent"].to_numpy(float))
    if len(x) < 2 or np.unique(x).size < 2:
        return np.nan, np.nan, np.nan
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    tss = float(np.sum((y - y.mean()) ** 2))
    r2 = np.nan if tss <= 0 else float(1.0 - np.sum((y - fitted) ** 2) / tss)
    return float(intercept), float(-slope), r2


def _mle_r2(curves, fit, year):
    x_t = float(fit["transition_x_t"])
    data = curves[
        (curves["year"] == year)
        & (curves["income_normalized"] >= x_t)
        & (curves["empirical_ccdf_percent"] > 0)
    ]
    return r2_log(
        data["empirical_ccdf_percent"],
        data["pareto_fitted_ccdf_percent_mle"],
    )


def build_diagnostics_annual(layer: str) -> pd.DataFrame:
    """Compute non-bootstrap annual diagnostics required downstream."""
    cfg, _, _, annual, curves, _, years = _load_layer(layer)
    annual_i = annual.set_index("year")
    rows = []

    for year in years:
        fit = annual_i.loc[year]
        x = _normalized_income(year, cfg)
        x_t = float(fit["transition_x_t"])
        tail = x[x >= x_t]
        total_income = float(np.sum(x))
        gompertz_income_share = 100.0 * float(np.sum(x[x < x_t])) / total_income
        pareto_income_share = 100.0 - gompertz_income_share

        likelihood_se = likelihood_alpha_se(tail, x_t)
        beta_mle = float(fit["pareto_beta_mle_continuity"])
        beta_likelihood_se = (
            abs(beta_mle * np.log(x_t) * likelihood_se)
            if np.isfinite(likelihood_se) and x_t > 0
            else np.nan
        )
        exp_intercept, exp_alpha, exp_r2 = _exponential_diagnostics(
            curves, fit, year
        )
        pareto_supported = (
            str(fit["pareto_selection_status"])
            == "earliest_tail_start_with_r2_ge_0.98"
        )

        rows.append(
            {
                "year": year,
                "exponential_intercept": exp_intercept,
                "exponential_alpha": exp_alpha,
                "exponential_r2": exp_r2,
                "gompertz_income_share_pct": gompertz_income_share,
                "pareto_alpha_mle_likelihood_se": likelihood_se,
                "pareto_beta_mle_likelihood_se": beta_likelihood_se,
                "pareto_mle_r2": _mle_r2(curves, fit, year),
                "pareto_supported": bool(pareto_supported),
                "pareto_income_share_pct": pareto_income_share,
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def _description(column: str) -> str:
    if column in COLUMN_DESCRIPTIONS:
        return COLUMN_DESCRIPTIONS[column]
    if column.endswith("_r2") or column.endswith("_r2_free"):
        return "Coefficient of determination for the indicated fitted model."
    if column.endswith("_sse"):
        return "Sum of squared residuals for the indicated fitted model."
    if column.endswith("_pct"):
        return column.replace("_", " ").capitalize() + "."
    return column.replace("_", " ").capitalize() + "."


def _unit(column: str) -> str:
    if column in COLUMN_UNITS:
        return COLUMN_UNITS[column]
    if column.endswith("_n"):
        return "count"
    if column.endswith("_pct"):
        return "%"
    if "2025_usd" in column or column.endswith("_income_adj"):
        return "2025 US$"
    if column.endswith("_status") or column.endswith("_rule"):
        return "text"
    if "beta" in column and "gompertz" not in column:
        return "CCDF-percent scale"
    return "dimensionless"


def _source(column: str) -> str:
    if column in {"IPEA", "diff_IPEA"}:
        return "IPEA auxiliary Gini series + Stage 03 analytical pipeline"
    if column in {"Banco_Mundial", "diff_Banco_Mundial"}:
        return "World Bank auxiliary Gini series + Stage 03 analytical pipeline"
    if "bootstrap" in column:
        return "Stage 03 Moura–Ribeiro bootstrap diagnostics"
    if "likelihood" in column:
        return "Stage 03 Moura–Ribeiro likelihood-width diagnostics"
    if column.startswith("exponential_"):
        return "Stage 03 exponential-vs-Gompertz diagnostic"
    return "Stage 03 analytical pipeline"


def build_metadata_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for table_name in ANALYSIS_TABLES:
        frame = frames[table_name]
        for column in frame.columns:
            rows.append(
                {
                    "table_name": table_name,
                    "table_description": TABLE_DESCRIPTIONS[table_name],
                    "column_name": column,
                    "description": _description(column),
                    "unit": _unit(column),
                    "source": _source(column),
                }
            )

    metadata_columns = {
        "table_name": "Canonical Stage-03 table containing the documented field.",
        "table_description": "Scientific description of the table as a whole.",
        "column_name": "Column documented by this metadata row.",
        "description": "Scientific definition of the column.",
        "unit": "Measurement unit, scale, or data type.",
        "source": "Primary data source or computational derivation of the field.",
    }
    for column, description in metadata_columns.items():
        rows.append(
            {
                "table_name": METADATA_FILE,
                "table_description": TABLE_DESCRIPTIONS[METADATA_FILE],
                "column_name": column,
                "description": description,
                "unit": "text",
                "source": "Stage 03 metadata schema",
            }
        )
    return pd.DataFrame(rows)


def run_layer(layer: str):
    cfg, gompertz, pareto, _, _, _, _ = _load_layer(layer)
    bootstrap = build_bootstrap_uncertainties(layer)
    diagnostics = build_diagnostics_annual(layer)

    g_extra = bootstrap[
        [
            "year",
            "bootstrap_reps",
            "gompertz_B_bootstrap_se",
            "gompertz_A_free_bootstrap_se",
            "gompertz_B_free_bootstrap_se",
        ]
    ].merge(
        diagnostics[
            [
                "year",
                "exponential_intercept",
                "exponential_alpha",
                "exponential_r2",
                "gompertz_income_share_pct",
            ]
        ],
        on="year",
        validate="one_to_one",
    )
    p_extra = bootstrap[
        [
            "year",
            "bootstrap_reps",
            "pareto_alpha_ls_bootstrap_se",
            "pareto_beta_ls_bootstrap_se",
            "pareto_alpha_mle_bootstrap_se",
            "pareto_beta_mle_bootstrap_se",
        ]
    ].merge(
        diagnostics[
            [
                "year",
                "pareto_alpha_mle_likelihood_se",
                "pareto_beta_mle_likelihood_se",
                "pareto_mle_r2",
                "pareto_supported",
                "pareto_income_share_pct",
            ]
        ],
        on="year",
        validate="one_to_one",
    )

    gompertz = (
        gompertz.drop(columns=GOMPERTZ_DIAGNOSTIC_COLUMNS, errors="ignore")
        .merge(g_extra, on="year", how="left", validate="one_to_one")
        .sort_values("year")
        .reset_index(drop=True)
    )
    pareto = (
        pareto.drop(columns=PARETO_DIAGNOSTIC_COLUMNS, errors="ignore")
        .merge(p_extra, on="year", how="left", validate="one_to_one")
        .sort_values("year")
        .reset_index(drop=True)
    )

    tables = cfg["tables"]
    tables.mkdir(parents=True, exist_ok=True)
    gompertz.to_csv(tables / "gompertz_annual.csv", index=False)
    pareto.to_csv(tables / "pareto_annual.csv", index=False)

    for path in tables.glob("*.csv"):
        if path.name not in CANONICAL_FILES:
            path.unlink()

    frames = {
        name: (
            gompertz
            if name == "gompertz_annual.csv"
            else pareto
            if name == "pareto_annual.csv"
            else pd.read_csv(tables / name)
        )
        for name in ANALYSIS_TABLES
    }
    metadata = build_metadata_table(frames)
    metadata.to_csv(tables / METADATA_FILE, index=False)

    return {"gompertz": gompertz, "pareto": pareto, "metadata": metadata}


def validate_parallel_schemas():
    """Require baseline and benchmark analytical directories to be structurally identical."""
    refined = LAYER_CONFIG["refined"]["tables"]
    trusted = LAYER_CONFIG["trusted"]["tables"]
    refined_names = {p.name for p in refined.glob("*.csv")}
    trusted_names = {p.name for p in trusted.glob("*.csv")}
    if refined_names != CANONICAL_FILES or trusted_names != CANONICAL_FILES:
        raise AssertionError(
            "Refined/trusted analytical file sets must equal the canonical set: "
            f"refined={sorted(refined_names)}, trusted={sorted(trusted_names)}"
        )
    for name in sorted(CANONICAL_FILES):
        refined_columns = list(pd.read_csv(refined / name, nrows=0).columns)
        trusted_columns = list(pd.read_csv(trusted / name, nrows=0).columns)
        if refined_columns != trusted_columns:
            raise AssertionError(
                f"Schema mismatch for {name}: {refined_columns} != {trusted_columns}"
            )


def main():
    results = {layer: run_layer(layer) for layer in ("trusted", "refined")}
    validate_parallel_schemas()
    for layer, result in results.items():
        print(
            f"Stage 03 diagnostics ({layer}, {LAYER_CONFIG[layer]['role']}): "
            f"{len(result['gompertz'])} survey years; canonical schemas validated."
        )
    return results


if __name__ == "__main__":
    main()
