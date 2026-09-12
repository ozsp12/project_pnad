"""Moura Jr.--Ribeiro (2009) reproduction diagnostics for Stage 03.

This module belongs to the analytical layer. It does not generate publication
figures. It reads the canonical Stage-03 outputs for the refined and trusted
layers, reproduces the main statistical quantities used by Moura Jr. and
Ribeiro (EPJ B 67, 101--120, 2009), quantifies uncertainty, and writes
layer-symmetric evidence tables.

Three files are produced in each Stage-03 table directory:

- ``moura_ribeiro_bootstrap_annual.csv``: current-model bootstrap uncertainties
  plus free-intercept Gompertz bootstrap diagnostics;
- ``moura_ribeiro_reproduction_annual.csv``: one annual row collecting the
  quantities needed to reproduce the published tables and main fit tests;
- ``moura_ribeiro_evidence_annual.csv``: long-form evidence table comparing the
  refined/trusted reconstruction with the values reported in the 2009 paper.

The current project model keeps A = ln[ln(100)] fixed. The free-intercept
Gompertz estimates are retained separately because the 2009 paper reports A and
B from an unconstrained least-squares fit after using A approximately 1.53 as a
boundary diagnostic.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data" / "metadata" / "df_metadata.xlsx"
PAPER_REFERENCE = ROOT / "data" / "auxiliary" / "moura_ribeiro_2009_reference.csv"

START_YEAR, END_YEAR = 1978, 2025
BOOTSTRAP_REPS = int(os.environ.get("PNAD_BOOTSTRAP_REPS", "1000"))
BOOTSTRAP_SEED = 20090101
LIKELIHOOD_GRID_SIZE = 12001

LAYER_CONFIG = {
    "refined": {
        "data": ROOT / "data" / "refined",
        "tables": ROOT / "assets" / "tables_analysis_refined",
        "pattern": "pnad_refined_{year}.parquet",
    },
    "trusted": {
        "data": ROOT / "data" / "trusted",
        "tables": ROOT / "assets" / "tables_analysis_trusted",
        "pattern": "pnad_trusted_{year}.parquet",
    },
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
    """Bootstrap an unconstrained line y = intercept + slope*x."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3:
        nan = np.full(reps, np.nan)
        return nan.copy(), nan.copy()

    idx = rng.integers(0, len(x), size=(reps, len(x)))
    xb = x[idx]
    yb = y[idx]
    xm = xb.mean(axis=1)
    ym = yb.mean(axis=1)
    den = ((xb - xm[:, None]) ** 2).sum(axis=1)
    slope = np.divide(
        ((xb - xm[:, None]) * (yb - ym[:, None])).sum(axis=1),
        den,
        out=np.full(reps, np.nan),
        where=den > 0,
    )
    intercept = ym - slope * xm
    return intercept, slope


def bootstrap_fixed_gompertz_B(x, y, A, rng, reps=BOOTSTRAP_REPS):
    """Bootstrap B in y=A-Bx while preserving the theoretical fixed A."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3:
        return np.full(reps, np.nan)

    idx = rng.integers(0, len(x), size=(reps, len(x)))
    xb = x[idx]
    yb = y[idx]
    den = (xb ** 2).sum(axis=1)
    num = (xb * (float(A) - yb)).sum(axis=1)
    return np.divide(
        num,
        den,
        out=np.full(reps, np.nan),
        where=den > 0,
    )


def likelihood_alpha_se(tail, x_t, grid_size=LIKELIHOOD_GRID_SIZE) -> float:
    """Numerically reproduce the likelihood-width error used in the 2009 paper.

    Apart from alpha-independent factors, Eqs. (32)--(37) imply

        L(alpha) proportional to alpha**n * exp[-c alpha],  alpha >= 1,

    with c = sum(log(x_i/x_t)). The variance is evaluated numerically on a
    dense grid, matching the paper's prescription without adding SciPy.
    """
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
    variance = max(0.0, mean2 - mean * mean)
    return float(np.sqrt(variance))


def _load_layer(layer: str):
    if layer not in LAYER_CONFIG:
        raise ValueError(f"Unknown layer: {layer}")
    cfg = LAYER_CONFIG[layer]
    tables = cfg["tables"]

    stats = pd.read_csv(tables / "statistics_annual.csv")
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
    reference = pd.read_csv(PAPER_REFERENCE)

    for frame in (stats, annual, curves, metadata, reference):
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")

    years = years_of(annual["year"].dropna())
    return cfg, stats, annual, curves, metadata, reference, years


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
    """Build annual uncertainty diagnostics for one Stage-03 data layer."""
    cfg, _, annual, curves, _, _, years = _load_layer(layer)
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
            xg,
            yg,
            float(fit["gompertz_A"]),
            rng,
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
        beta_mle = f_t * x_t ** alpha_mle

        def sd(values):
            return float(np.nanstd(values, ddof=1))

        rows.append(
            {
                "year": year,
                "layer": layer,
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
    d = curves[
        (curves["year"] == year)
        & (curves["income_normalized"] <= x_gmax)
        & (curves["empirical_ccdf_percent"] > 0)
    ]
    x = d["income_normalized"].to_numpy(float)
    y = np.log(d["empirical_ccdf_percent"].to_numpy(float))
    if len(x) < 2 or np.unique(x).size < 2:
        return np.nan, np.nan, np.nan
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    tss = float(np.sum((y - y.mean()) ** 2))
    r2 = np.nan if tss <= 0 else float(1.0 - np.sum((y - fitted) ** 2) / tss)
    return float(intercept), float(-slope), r2


def _mle_r2(curves, fit, year):
    x_t = float(fit["transition_x_t"])
    d = curves[
        (curves["year"] == year)
        & (curves["income_normalized"] >= x_t)
        & (curves["empirical_ccdf_percent"] > 0)
    ]
    return r2_log(
        d["empirical_ccdf_percent"],
        d["pareto_fitted_ccdf_percent_mle"],
    )


def build_reproduction_annual(layer: str, bootstrap=None) -> pd.DataFrame:
    """Collect the annual quantities required for a 2009-paper reproduction."""
    cfg, stats, annual, curves, metadata, _, years = _load_layer(layer)
    if bootstrap is None:
        bootstrap = build_bootstrap_uncertainties(layer)

    annual_i = annual.set_index("year")
    stats_i = stats.set_index("year")
    metadata_i = metadata.set_index("year")
    boot_i = bootstrap.set_index("year")
    rows = []

    for year in years:
        fit = annual_i.loc[year]
        stat = stats_i.loc[year]
        meta = metadata_i.loc[year]
        boot = boot_i.loc[year]

        nominal = _income(year, cfg, positive=True)
        exchange = float(meta["Exchange"])
        if not np.isfinite(exchange) or exchange <= 0:
            raise ValueError(f"{year}: invalid Exchange")
        mean_income_usd_current_date = float(np.mean(nominal) / exchange)

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
        mle_r2 = _mle_r2(curves, fit, year)

        free_A = float(fit["gompertz_boundary_A_free"])
        free_B = float(fit["gompertz_boundary_B_free"])
        free_r2 = float(fit["gompertz_boundary_r2_free"])
        free_corr = np.sqrt(np.clip(free_r2, 0.0, 1.0))
        ls_r2 = float(fit["pareto_ls_r2"])
        ls_corr = np.sqrt(np.clip(ls_r2, 0.0, 1.0))
        pareto_supported = (
            str(fit["pareto_selection_status"])
            == "earliest_tail_start_with_r2_ge_0.98"
        )

        rows.append(
            {
                "year": year,
                "layer": layer,
                "mean_income_usd_current_date": mean_income_usd_current_date,
                "exponential_intercept": exp_intercept,
                "exponential_alpha": exp_alpha,
                "exponential_r2": exp_r2,
                "gompertz_A_fixed": float(fit["gompertz_A"]),
                "gompertz_B_fixed": float(fit["gompertz_B"]),
                "gompertz_B_fixed_bootstrap_se": float(
                    boot["gompertz_B_bootstrap_se"]
                ),
                "gompertz_A_free": free_A,
                "gompertz_A_free_bootstrap_se": float(
                    boot["gompertz_A_free_bootstrap_se"]
                ),
                "gompertz_B_free": free_B,
                "gompertz_B_free_bootstrap_se": float(
                    boot["gompertz_B_free_bootstrap_se"]
                ),
                "gompertz_x_gmax": float(fit["gompertz_x_gmax"]),
                "gompertz_free_r2": free_r2,
                "gompertz_free_correlation_coefficient": float(free_corr),
                "gompertz_population_pct": float(
                    fit["gompertz_population_pct"]
                ),
                "pareto_x_pmin": float(fit["pareto_x_pmin"]),
                "transition_x_t": x_t,
                "transition_delta_x_t": float(
                    fit["transition_delta_x_t"]
                ),
                "pareto_alpha_ls": float(fit["pareto_alpha_ls"]),
                "pareto_alpha_ls_bootstrap_se": float(
                    boot["pareto_alpha_ls_bootstrap_se"]
                ),
                "pareto_beta_ls": float(fit["pareto_beta_ls"]),
                "pareto_beta_ls_bootstrap_se": float(
                    boot["pareto_beta_ls_bootstrap_se"]
                ),
                "pareto_ls_r2": ls_r2,
                "pareto_ls_correlation_coefficient": float(ls_corr),
                "pareto_alpha_mle": float(fit["pareto_alpha_mle"]),
                "pareto_alpha_mle_fisher_se": float(
                    fit["pareto_alpha_mle_fisher_se"]
                ),
                "pareto_alpha_mle_likelihood_se": likelihood_se,
                "pareto_alpha_mle_bootstrap_se": float(
                    boot["pareto_alpha_mle_bootstrap_se"]
                ),
                "pareto_beta_mle_continuity": beta_mle,
                "pareto_beta_mle_likelihood_se": beta_likelihood_se,
                "pareto_beta_mle_bootstrap_se": float(
                    boot["pareto_beta_mle_bootstrap_se"]
                ),
                "pareto_mle_r2": mle_r2,
                "pareto_population_pct": float(
                    fit["pareto_population_pct"]
                ),
                "pareto_supported": bool(pareto_supported),
                "gompertz_income_share_pct": gompertz_income_share,
                "pareto_income_share_pct": pareto_income_share,
                "gini": float(stat["Gini"]),
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def _comparison_fields(estimate, paper_value, standard_error, paper_se):
    estimate = float(estimate) if pd.notna(estimate) else np.nan
    paper_value = float(paper_value) if pd.notna(paper_value) else np.nan
    standard_error = (
        float(standard_error) if pd.notna(standard_error) else np.nan
    )
    paper_se = float(paper_se) if pd.notna(paper_se) else np.nan

    difference = (
        estimate - paper_value
        if np.isfinite(estimate) and np.isfinite(paper_value)
        else np.nan
    )
    relative = (
        100.0 * difference / paper_value
        if np.isfinite(difference) and not np.isclose(paper_value, 0.0)
        else np.nan
    )
    within_1se = (
        abs(difference) <= paper_se
        if np.isfinite(difference) and np.isfinite(paper_se)
        else np.nan
    )
    return difference, relative, within_1se


def build_evidence_table(
    layer: str,
    reproduction: pd.DataFrame,
    reference: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Create a long-form evidence table for refined/trusted reproduction."""
    if reference is None:
        reference = pd.read_csv(PAPER_REFERENCE)
    reference_i = reference.set_index("year")
    rows = []

    specs = [
        ("table_1", "annual_income", "descriptive", "mean_income_usd", "mean_income_usd_current_date", None, "paper_mean_income_usd", None, None),
        ("table_2", "gompertz", "free_lsf", "A", "gompertz_A_free", "gompertz_A_free_bootstrap_se", "paper_gompertz_A", "paper_gompertz_A_se", "gompertz_free_correlation_coefficient"),
        ("table_2", "gompertz", "free_lsf", "B", "gompertz_B_free", "gompertz_B_free_bootstrap_se", "paper_gompertz_B", "paper_gompertz_B_se", "gompertz_free_correlation_coefficient"),
        ("table_2", "gompertz", "boundary", "x_gmax", "gompertz_x_gmax", None, "paper_gompertz_x_gmax", None, "gompertz_free_correlation_coefficient"),
        ("table_2", "gompertz", "free_lsf", "correlation_coefficient", "gompertz_free_correlation_coefficient", None, "paper_gompertz_corr", None, "gompertz_free_correlation_coefficient"),
        ("table_2", "gompertz", "population", "population_pct", "gompertz_population_pct", None, "paper_gompertz_population_pct", None, "gompertz_free_correlation_coefficient"),
        ("table_3", "pareto", "boundary", "x_pmin", "pareto_x_pmin", None, "paper_pareto_x_pmin", None, "pareto_ls_r2"),
        ("table_3", "transition", "boundary", "x_t", "transition_x_t", None, "paper_transition_x_t", "paper_transition_x_t_se", "pareto_ls_r2"),
        ("table_3", "pareto", "lsf", "alpha", "pareto_alpha_ls", "pareto_alpha_ls_bootstrap_se", "paper_pareto_alpha_ls", "paper_pareto_alpha_ls_se", "pareto_ls_r2"),
        ("table_3", "pareto", "lsf", "beta", "pareto_beta_ls", "pareto_beta_ls_bootstrap_se", "paper_pareto_beta_ls", "paper_pareto_beta_ls_se", "pareto_ls_r2"),
        ("table_3", "pareto", "mle", "alpha", "pareto_alpha_mle", "pareto_alpha_mle_likelihood_se", "paper_pareto_alpha_mle", "paper_pareto_alpha_mle_se", "pareto_mle_r2"),
        ("table_3", "pareto", "mle_continuity", "beta", "pareto_beta_mle_continuity", "pareto_beta_mle_likelihood_se", "paper_pareto_beta_mle", "paper_pareto_beta_mle_se", "pareto_mle_r2"),
        ("table_3", "pareto", "lsf", "correlation_coefficient", "pareto_ls_correlation_coefficient", None, "paper_pareto_corr_lsf", None, "pareto_ls_r2"),
        ("table_3", "pareto", "population", "population_pct", "pareto_population_pct", None, "paper_pareto_population_pct", None, "pareto_ls_r2"),
        ("table_4", "income_share", "gompertz", "share_pct", "gompertz_income_share_pct", None, "paper_gompertz_income_share_pct", None, None),
        ("table_4", "income_share", "pareto", "share_pct", "pareto_income_share_pct", None, "paper_pareto_income_share_pct", None, None),
        ("table_4", "inequality", "lorenz", "gini", "gini", None, "paper_gini", None, None),
    ]

    for _, record in reproduction.iterrows():
        year = int(record["year"])
        paper = reference_i.loc[year] if year in reference_i.index else None

        delta_r2 = float(record["gompertz_free_r2"] - record["exponential_r2"])
        rows.append(
            {
                "year": year,
                "layer": layer,
                "paper_table": "model_test",
                "test": "gompertz_vs_exponential",
                "estimator": "r2_comparison",
                "parameter": "delta_r2",
                "estimate": delta_r2,
                "standard_error": np.nan,
                "fit_metric": "delta_r2",
                "fit_value": delta_r2,
                "criterion": "gompertz_free_r2 > exponential_r2",
                "passed": bool(np.isfinite(delta_r2) and delta_r2 > 0),
                "evidence_status": (
                    "supported" if np.isfinite(delta_r2) and delta_r2 > 0 else "rejected"
                ),
                "paper_2009_value": np.nan,
                "paper_2009_standard_error": np.nan,
                "difference_from_2009": np.nan,
                "relative_difference_pct": np.nan,
                "within_paper_1se": np.nan,
            }
        )

        for (
            paper_table,
            test,
            estimator,
            parameter,
            estimate_col,
            se_col,
            paper_col,
            paper_se_col,
            fit_col,
        ) in specs:
            estimate = record[estimate_col]
            se = record[se_col] if se_col else np.nan
            paper_value = (
                paper[paper_col]
                if paper is not None and paper_col is not None
                else np.nan
            )
            paper_se = (
                paper[paper_se_col]
                if paper is not None and paper_se_col is not None
                else np.nan
            )
            fit_value = record[fit_col] if fit_col else np.nan

            if test == "gompertz":
                criterion = "correlation_coefficient >= 0.98"
                passed = bool(
                    np.isfinite(record["gompertz_free_correlation_coefficient"])
                    and record["gompertz_free_correlation_coefficient"] >= 0.98
                )
                status = "supported" if passed else "weak"
            elif test == "pareto" and estimator in {"lsf", "boundary", "population"}:
                criterion = "pareto_ls_r2 >= 0.98 and selected tail supported"
                passed = bool(
                    np.isfinite(record["pareto_ls_r2"])
                    and record["pareto_ls_r2"] >= 0.98
                    and bool(record["pareto_supported"])
                )
                status = "supported" if passed else "fallback"
            elif test == "pareto" and estimator.startswith("mle"):
                criterion = "finite direct MLE on observations x >= x_t"
                passed = bool(np.isfinite(record["pareto_alpha_mle"]))
                status = "supported" if passed else "rejected"
            else:
                criterion = "descriptive reproduction quantity"
                passed = np.nan
                status = "descriptive"

            difference, relative, within_1se = _comparison_fields(
                estimate,
                paper_value,
                se,
                paper_se,
            )
            rows.append(
                {
                    "year": year,
                    "layer": layer,
                    "paper_table": paper_table,
                    "test": test,
                    "estimator": estimator,
                    "parameter": parameter,
                    "estimate": estimate,
                    "standard_error": se,
                    "fit_metric": fit_col if fit_col else "",
                    "fit_value": fit_value,
                    "criterion": criterion,
                    "passed": passed,
                    "evidence_status": status,
                    "paper_2009_value": paper_value,
                    "paper_2009_standard_error": paper_se,
                    "difference_from_2009": difference,
                    "relative_difference_pct": relative,
                    "within_paper_1se": within_1se,
                }
            )

    return pd.DataFrame(rows).sort_values(
        ["year", "paper_table", "test", "estimator", "parameter"]
    ).reset_index(drop=True)


def run_layer(layer: str):
    cfg, _, _, _, _, reference, _ = _load_layer(layer)
    bootstrap = build_bootstrap_uncertainties(layer)
    reproduction = build_reproduction_annual(layer, bootstrap)
    evidence = build_evidence_table(layer, reproduction, reference)

    tables = cfg["tables"]
    tables.mkdir(parents=True, exist_ok=True)
    bootstrap.to_csv(tables / "moura_ribeiro_bootstrap_annual.csv", index=False)
    reproduction.to_csv(
        tables / "moura_ribeiro_reproduction_annual.csv", index=False
    )
    evidence.to_csv(
        tables / "moura_ribeiro_evidence_annual.csv", index=False
    )
    return {
        "bootstrap": bootstrap,
        "reproduction": reproduction,
        "evidence": evidence,
    }


def main():
    results = {layer: run_layer(layer) for layer in ("trusted", "refined")}
    for layer, result in results.items():
        years = result["reproduction"]["year"]
        print(
            f"Stage 03 Moura-Ribeiro evidence ({layer}): "
            f"{len(years)} survey years, "
            f"{len(result['evidence'])} evidence rows."
        )
    return results


if __name__ == "__main__":
    main()
