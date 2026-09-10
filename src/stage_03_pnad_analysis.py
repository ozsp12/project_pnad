"""Run the complete PNAD analysis with Moura--Ribeiro Gompertz--Pareto fitting.

The general descriptive, Lorenz, inequality and visualization routines remain in
``stage_03_pnad_analysis_core.py``. This module refactors the income-regime
analysis to follow Moura Jr. and Ribeiro (EPJ B 67, 101--120, 2009): normalized
individual income, logarithmic spacing with ratio 1.10, free least-squares
estimation of the Gompertz parameters A and B, explicit x_G,max and x_P,min
boundaries, midpoint transition x_t when the boundaries differ, Pareto LS for
comparison, and direct Pareto maximum likelihood on individual observations.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from . import stage_03_pnad_analysis_core as core
    from .stage_03_pnad_analysis_core import *  # noqa: F401,F403
except ImportError:  # direct execution: python src/stage_03_pnad_analysis.py
    import stage_03_pnad_analysis_core as core
    from stage_03_pnad_analysis_core import *  # noqa: F401,F403


BIN_RATIO = 1.10
GOMPERTZ_A_THEORY = math.log(math.log(100.0))
GOMPERTZ_A_MIN = 1.4
GOMPERTZ_A_MAX = 1.6
MIN_GOMPERTZ_POINTS = 8
MIN_PARETO_POINTS = 5
PARETO_MIN_R2 = 0.98


def geometric_edges(xmin, xmax, ratio=BIN_RATIO):
    """Return geometric edges, using the paper's 10% logarithmic spacing by default."""
    return core.geometric_edges(xmin, xmax, ratio=ratio)


def linear_fit(x, y):
    """Ordinary least-squares fit y = intercept + slope*x with R^2 and SSE."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size < 2 or np.unique(x).size < 2:
        raise ValueError("Linear fit requires at least two distinct finite abscissae.")

    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    residual = y - fitted
    sse = float(np.sum(residual ** 2))
    tss = float(np.sum((y - y.mean()) ** 2))
    r2 = np.nan if tss == 0.0 else float(1.0 - sse / tss)
    return {
        "intercept": float(intercept),
        "slope": float(slope),
        "fit_r2": r2,
        "fit_sse": sse,
    }


def load_normalized_individual_income(parquet_path: Path, metadata_row: pd.Series):
    """Load positive adjusted income and normalize it by that year's positive mean."""
    frame = pd.read_parquet(parquet_path)
    if "renda" not in frame.columns:
        raise ValueError(f"{parquet_path.name}: missing renda column")

    nominal = pd.to_numeric(frame["renda"], errors="coerce").to_numpy(float)
    nominal = nominal[np.isfinite(nominal) & (nominal > 0)]
    if nominal.size == 0:
        raise ValueError(f"{parquet_path.name}: no positive finite income")

    exchange = float(metadata_row["Exchange"])
    inflation = float(metadata_row["Inflation"])
    if not np.isfinite(exchange) or exchange <= 0:
        raise ValueError(f"{parquet_path.name}: invalid Exchange")
    if not np.isfinite(inflation) or inflation <= 0:
        raise ValueError(f"{parquet_path.name}: invalid Inflation")

    adjusted = nominal / exchange * inflation
    normalization_mean = float(np.mean(adjusted))
    if not np.isfinite(normalization_mean) or normalization_mean <= 0:
        raise ValueError(f"{parquet_path.name}: invalid annual mean income")

    normalized = adjusted / normalization_mean
    return normalized, normalization_mean


def build_regime_ccdf(income_normalized):
    """Evaluate the empirical CCDF on x_j = x_min * 1.1^j logarithmic thresholds."""
    X = np.sort(np.asarray(income_normalized, dtype=float))
    X = X[np.isfinite(X) & (X > 0)]
    if X.size < 2:
        raise ValueError("Regime fitting requires at least two positive observations.")

    edges = geometric_edges(float(X[0]), float(X[-1]), ratio=BIN_RATIO)
    thresholds = edges[:-1]
    right_edges = edges[1:]

    left_index = np.searchsorted(X, thresholds, side="left")
    right_index = np.searchsorted(X, right_edges, side="left")
    observations_in_bin = right_index - left_index
    ccdf_probability = (X.size - left_index) / X.size
    ccdf_percent = 100.0 * ccdf_probability

    transform = np.full(ccdf_percent.shape, np.nan, dtype=float)
    valid = ccdf_percent > 1.0
    transform[valid] = np.log(np.log(ccdf_percent[valid]))

    return pd.DataFrame({
        "income_normalized": thresholds,
        "bin_right_normalized": right_edges,
        "observations_in_bin": observations_in_bin,
        "empirical_ccdf_probability": ccdf_probability,
        "empirical_ccdf_percent": ccdf_percent,
        "gompertz_transform": transform,
    })


def select_gompertz_region(regime_ccdf):
    """Find x_G,max as the largest fitted range whose free intercept satisfies A≈1.5."""
    valid = regime_ccdf.loc[
        np.isfinite(regime_ccdf["gompertz_transform"])
        & (regime_ccdf["empirical_ccdf_percent"] > 1.0)
        & (regime_ccdf["observations_in_bin"] > 0)
    ].reset_index(drop=True)
    if len(valid) < MIN_GOMPERTZ_POINTS:
        raise ValueError("Insufficient Gompertz-region points.")

    candidates = []
    for end in range(MIN_GOMPERTZ_POINTS, len(valid) + 1):
        block = valid.iloc[:end]
        fit = linear_fit(block["income_normalized"], block["gompertz_transform"])
        A = float(fit["intercept"])
        B = float(-fit["slope"])
        candidates.append({
            "end": end,
            "gompertz_x_gmax": float(block["income_normalized"].iloc[-1]),
            "gompertz_A": A,
            "gompertz_B": B,
            "gompertz_r2": float(fit["fit_r2"]),
            "gompertz_sse": float(fit["fit_sse"]),
            "admissible": bool(GOMPERTZ_A_MIN <= A <= GOMPERTZ_A_MAX and B > 0),
        })

    frame = pd.DataFrame(candidates)
    admissible = frame[frame["admissible"]]
    if not admissible.empty:
        chosen = admissible.iloc[-1]
        status = "largest_range_with_A_in_1.4_to_1.6"
    else:
        frame["A_distance"] = (frame["gompertz_A"] - GOMPERTZ_A_THEORY).abs()
        chosen = frame.sort_values(["A_distance", "gompertz_x_gmax"]).iloc[0]
        status = "fallback_closest_A_to_ln_ln_100"

    return {
        "gompertz_A": float(chosen["gompertz_A"]),
        "gompertz_B": float(chosen["gompertz_B"]),
        "gompertz_r2": float(chosen["gompertz_r2"]),
        "gompertz_sse": float(chosen["gompertz_sse"]),
        "gompertz_x_gmax": float(chosen["gompertz_x_gmax"]),
        "gompertz_point_n": int(chosen["end"]),
        "gompertz_selection_status": status,
    }


def select_pareto_region(regime_ccdf, gompertz_x_gmax):
    """Find x_P,min as the earliest log-log tail with a stable positive Pareto slope."""
    valid = regime_ccdf.loc[
        (regime_ccdf["income_normalized"] >= gompertz_x_gmax)
        & (regime_ccdf["empirical_ccdf_percent"] > 0)
        & (regime_ccdf["observations_in_bin"] > 0)
    ].reset_index(drop=True)
    if len(valid) < MIN_PARETO_POINTS:
        raise ValueError("Insufficient Pareto-tail points.")

    candidates = []
    for start in range(0, len(valid) - MIN_PARETO_POINTS + 1):
        tail = valid.iloc[start:]
        fit = linear_fit(
            np.log(tail["income_normalized"]),
            np.log(tail["empirical_ccdf_percent"]),
        )
        alpha = float(-fit["slope"])
        candidates.append({
            "start": start,
            "pareto_x_pmin": float(tail["income_normalized"].iloc[0]),
            "pareto_selection_alpha": alpha,
            "pareto_selection_r2": float(fit["fit_r2"]),
            "admissible": bool(np.isfinite(alpha) and alpha > 0 and fit["fit_r2"] >= PARETO_MIN_R2),
        })

    frame = pd.DataFrame(candidates)
    admissible = frame[frame["admissible"]]
    if not admissible.empty:
        chosen = admissible.iloc[0]
        status = "earliest_tail_start_with_r2_ge_0.98"
    else:
        chosen = frame.sort_values(
            ["pareto_selection_r2", "pareto_x_pmin"],
            ascending=[False, True],
        ).iloc[0]
        status = "fallback_highest_tail_r2"

    return {
        "pareto_x_pmin": float(chosen["pareto_x_pmin"]),
        "pareto_selection_alpha": float(chosen["pareto_selection_alpha"]),
        "pareto_selection_r2": float(chosen["pareto_selection_r2"]),
        "pareto_selection_status": status,
    }


def determine_threshold(gompertz_x_gmax, pareto_x_pmin):
    """Return x_t and delta x_t from the two regime boundaries, following Eq. (26)."""
    if np.isclose(gompertz_x_gmax, pareto_x_pmin, rtol=1.0e-12, atol=0.0):
        return float(gompertz_x_gmax), 0.0, "coincident_regime_bounds"
    x_t = 0.5 * (gompertz_x_gmax + pareto_x_pmin)
    delta_x_t = 0.5 * abs(pareto_x_pmin - gompertz_x_gmax)
    return float(x_t), float(delta_x_t), "midpoint_between_regime_bounds"


def fit_pareto_ls(regime_ccdf, pareto_x_pmin):
    """Least-squares Pareto fit on the identified log-binned tail."""
    tail = regime_ccdf.loc[
        (regime_ccdf["income_normalized"] >= pareto_x_pmin)
        & (regime_ccdf["empirical_ccdf_percent"] > 0)
        & (regime_ccdf["observations_in_bin"] > 0)
    ]
    if len(tail) < MIN_PARETO_POINTS:
        raise ValueError("Insufficient Pareto points for least squares.")

    fit = linear_fit(
        np.log(tail["income_normalized"]),
        np.log(tail["empirical_ccdf_percent"]),
    )
    alpha = float(-fit["slope"])
    beta = float(np.exp(fit["intercept"]))
    if not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("Pareto LS returned a non-positive exponent.")
    return alpha, beta, float(fit["fit_r2"]), float(fit["fit_sse"])


def direct_pareto_mle(income_normalized, x_t):
    """Direct Pareto MLE from individual observations x_i >= x_t, as in Eq. (31)."""
    X = np.asarray(income_normalized, dtype=float)
    tail = X[np.isfinite(X) & (X >= x_t)]
    n_tail = int(tail.size)
    if n_tail < 2:
        raise ValueError("Pareto MLE requires at least two tail observations.")
    log_sum = float(np.log(tail / x_t).sum())
    if log_sum <= 0:
        raise ValueError("Pareto MLE logarithmic sum must be positive.")
    alpha = float(n_tail / log_sum)
    fisher_se = float(alpha / np.sqrt(n_tail))
    return alpha, fisher_se, n_tail


def continuity_beta(alpha, x_t, gompertz_A, gompertz_B):
    """Set beta from the Gompertz--Pareto continuity condition at x_t."""
    F_t = float(np.exp(np.exp(gompertz_A - gompertz_B * x_t)))
    beta = float(F_t * x_t ** alpha)
    return beta, F_t


def fit_year_regime(year, income_normalized, normalization_mean):
    regime_ccdf = build_regime_ccdf(income_normalized)
    gompertz = select_gompertz_region(regime_ccdf)
    pareto = select_pareto_region(regime_ccdf, gompertz["gompertz_x_gmax"])
    x_t, delta_x_t, threshold_rule = determine_threshold(
        gompertz["gompertz_x_gmax"], pareto["pareto_x_pmin"]
    )

    alpha_ls, beta_ls, pareto_ls_r2, pareto_ls_sse = fit_pareto_ls(
        regime_ccdf, pareto["pareto_x_pmin"]
    )
    alpha_mle, alpha_mle_se, pareto_population_n = direct_pareto_mle(
        income_normalized, x_t
    )
    beta_mle, F_t = continuity_beta(
        alpha_mle, x_t, gompertz["gompertz_A"], gompertz["gompertz_B"]
    )

    n_total = int(len(income_normalized))
    gompertz_population_n = n_total - pareto_population_n
    pareto_population_pct = 100.0 * pareto_population_n / n_total
    gompertz_population_pct = 100.0 - pareto_population_pct

    fit = {
        "year": int(year),
        "log_bin_ratio": BIN_RATIO,
        "normalization_mean_income_adj_2025_usd": float(normalization_mean),
        "positive_income_observation_n": n_total,
        "gompertz_A": gompertz["gompertz_A"],
        "gompertz_B": gompertz["gompertz_B"],
        "gompertz_r2": gompertz["gompertz_r2"],
        "gompertz_sse": gompertz["gompertz_sse"],
        "gompertz_x_gmax": gompertz["gompertz_x_gmax"],
        "gompertz_point_n": gompertz["gompertz_point_n"],
        "gompertz_selection_status": gompertz["gompertz_selection_status"],
        "pareto_x_pmin": pareto["pareto_x_pmin"],
        "pareto_selection_r2": pareto["pareto_selection_r2"],
        "pareto_selection_status": pareto["pareto_selection_status"],
        "transition_x_t": x_t,
        "transition_delta_x_t": delta_x_t,
        "transition_rule": threshold_rule,
        "gompertz_population_n": gompertz_population_n,
        "pareto_population_n": pareto_population_n,
        "gompertz_population_pct": gompertz_population_pct,
        "pareto_population_pct": pareto_population_pct,
        "pareto_alpha_ls": alpha_ls,
        "pareto_beta_ls": beta_ls,
        "pareto_ls_r2": pareto_ls_r2,
        "pareto_ls_sse": pareto_ls_sse,
        "pareto_alpha_mle": alpha_mle,
        "pareto_alpha_mle_fisher_se": alpha_mle_se,
        "pareto_beta_mle_continuity": beta_mle,
        "gompertz_ccdf_at_x_t_percent": F_t,
        "cutoff_normalized": x_t,
        "cutoff_income_adj": x_t * normalization_mean,
        "pareto_alpha": alpha_mle,
        "pareto_r2": pareto_ls_r2,
    }

    curve = regime_ccdf.copy()
    curve.insert(0, "year", int(year))
    x = curve["income_normalized"].to_numpy(float)
    curve["regime"] = np.where(x < x_t, "gompertz_body", "pareto_tail")
    curve["gompertz_x_gmax"] = gompertz["gompertz_x_gmax"]
    curve["pareto_x_pmin"] = pareto["pareto_x_pmin"]
    curve["cutoff_normalized"] = x_t
    curve["cutoff_income_adj"] = x_t * normalization_mean
    curve["income_adj_2025_usd"] = x * normalization_mean
    curve["gompertz_fitted_transform"] = np.where(
        x <= gompertz["gompertz_x_gmax"],
        gompertz["gompertz_A"] - gompertz["gompertz_B"] * x,
        np.nan,
    )
    curve["pareto_fitted_ccdf_percent_ls"] = np.where(
        x >= pareto["pareto_x_pmin"], beta_ls * x ** (-alpha_ls), np.nan
    )
    curve["pareto_fitted_ccdf_percent_mle"] = np.where(
        x >= x_t, beta_mle * x ** (-alpha_mle), np.nan
    )
    curve["pareto_fitted_ccdf_percent"] = curve["pareto_fitted_ccdf_percent_mle"]

    return fit, curve


def build_regime_datasets(files_by_year, df_metadata):
    fits = []
    curves = []
    metadata_index = df_metadata.set_index("ano")

    for year in sorted(files_by_year):
        income_normalized, normalization_mean = load_normalized_individual_income(
            files_by_year[year], metadata_index.loc[year]
        )
        fit, curve = fit_year_regime(year, income_normalized, normalization_mean)
        fits.append(fit)
        curves.append(curve)

    fit_table = pd.DataFrame(fits).sort_values("year").reset_index(drop=True)
    if not np.allclose(
        fit_table["gompertz_population_pct"] + fit_table["pareto_population_pct"],
        100.0,
        rtol=0.0,
        atol=1.0e-10,
    ):
        raise AssertionError("Gompertz and Pareto population percentages must sum to 100%.")

    curve_table = (
        pd.concat(curves, ignore_index=True)
        .sort_values(["year", "income_normalized"])
        .reset_index(drop=True)
    )
    return fit_table, curve_table


def plot_gompertz_regime_fits(df_regime_curves, df_regime_fits, years,
                              output_path, ncols=4, figsize=None):
    fits_index = df_regime_fits.set_index("year")
    fig, axes = core.make_grid(len(years), cols=ncols, figsize=figsize)

    for i, year in enumerate(years):
        fit = fits_index.loc[year]
        x_gmax = float(fit["gompertz_x_gmax"])
        temp = df_regime_curves[
            (df_regime_curves["year"] == year)
            & (df_regime_curves["income_normalized"] <= x_gmax)
            & df_regime_curves["gompertz_transform"].notna()
        ]
        ax = axes.ravel()[i]
        ax.scatter(temp["income_normalized"], temp["gompertz_transform"], s=12, alpha=0.7)
        ax.plot(temp["income_normalized"], temp["gompertz_fitted_transform"], linewidth=1.8)
        ax.axvline(x_gmax, linestyle="--", linewidth=1.0)
        ax.set_title(
            fr"{year} - $A={fit['gompertz_A']:.3f}$, $B={fit['gompertz_B']:.3f}$, $R^2={fit['gompertz_r2']:.3f}$"
        )
        ax.set_xlabel("Normalized individual income")
        ax.set_ylabel(r"$\ln[\ln(F)]$")
        ax.grid(True, alpha=0.3)

    core.finish_grid(
        fig, axes, len(years),
        "Gompertz region - Moura-Ribeiro least-squares fits",
        output_path,
    )


def plot_pareto_regime_fits(df_regime_curves, df_regime_fits, years,
                            output_path, ncols=4, figsize=None):
    fits_index = df_regime_fits.set_index("year")
    fig, axes = core.make_grid(len(years), cols=ncols, figsize=figsize)

    for i, year in enumerate(years):
        fit = fits_index.loc[year]
        x_pmin = float(fit["pareto_x_pmin"])
        x_t = float(fit["transition_x_t"])
        temp = df_regime_curves[
            (df_regime_curves["year"] == year)
            & (df_regime_curves["income_normalized"] >= min(x_t, x_pmin))
        ]
        ax = axes.ravel()[i]
        ax.scatter(temp["income_normalized"], temp["empirical_ccdf_percent"], s=12, alpha=0.7)
        ax.plot(temp["income_normalized"], temp["pareto_fitted_ccdf_percent_mle"], linewidth=1.8)
        ax.plot(
            temp["income_normalized"], temp["pareto_fitted_ccdf_percent_ls"],
            linewidth=1.2, linestyle="--"
        )
        ax.axvline(x_t, linestyle=":", linewidth=1.0)
        ax.axvline(x_pmin, linestyle="--", linewidth=1.0)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(
            fr"{year} - $\alpha_{{MLE}}={fit['pareto_alpha_mle']:.3f}$, $R^2_{{LS}}={fit['pareto_ls_r2']:.3f}$"
        )
        ax.set_xlabel("Normalized individual income")
        ax.set_ylabel("CCDF (%)")
        ax.grid(True, alpha=0.3)

    core.finish_grid(
        fig, axes, len(years),
        "Pareto region - direct MLE and log-binned CCDF LS",
        output_path,
    )


def run_analysis_layer(layer, data_path, file_pattern, tables_path, figures_path):
    tables_path.mkdir(parents=True, exist_ok=True)
    figures_path.mkdir(parents=True, exist_ok=True)

    results = core.pipeline(
        data_path=data_path,
        file_pattern=file_pattern,
        layer=layer,
        bin_ratio=BIN_RATIO,
    )
    years = results["years"]
    files_by_year = results["files_by_year"]
    df_stats_year = results["df_stats_year"]
    df_ccdf = results["df_ccdf"]
    df_bins = results["df_bins"]
    df_lorenz = results["df_lorenz"]

    df_histograms = core.build_histogram_dataset(files_by_year, years, bins=100)
    df_gini_validation = core.build_gini_validation(df_stats_year)
    df_regime_fits, df_regime_curves = build_regime_datasets(
        files_by_year, results["df_metadata"]
    )

    prefix = f"{layer}_analysis"
    tables = {
        f"{prefix}_statistics_annual.csv": df_stats_year,
        f"{prefix}_ccdf_empirical.csv": df_ccdf,
        f"{prefix}_geometric_bins.csv": df_bins,
        f"{prefix}_lorenz.csv": df_lorenz,
        f"{prefix}_histograms.csv": df_histograms,
        f"{prefix}_gini_validation_vs_ipea_wb_annual.csv": df_gini_validation,
        f"{prefix}_gompertz_pareto_annual.csv": df_regime_fits,
        f"{prefix}_regime_curves.csv": df_regime_curves,
    }
    for filename, frame in tables.items():
        core.save_table(frame, filename, tables_path)

    core.plot_histograms(df_histograms, years, figures_path / f"{prefix}_histograms.svg", ncols=4)
    core.plot_income_mean_median(df_stats_year, figures_path / f"{prefix}_income_mean_median.svg")
    core.plot_ccdf_loglog(df_ccdf, years, figures_path / f"{prefix}_ccdf_loglog.svg", ncols=4)
    core.plot_ccdf_lnln(df_ccdf, years, figures_path / f"{prefix}_ccdf_lnln.svg", ncols=4)
    core.plot_lorenz_indices_pretty(
        df_lorenz, df_stats_year, years,
        figures_path / f"{prefix}_lorenz_geometry.svg", ncols=3
    )
    core.plot_top_shares(df_stats_year, figures_path / f"{prefix}_top_income_shares.svg")
    core.plot_top_shares_mean_median(
        df_stats_year, figures_path / f"{prefix}_top_income_shares_mean_median.svg"
    )
    core.plot_inequality_indices(df_stats_year, figures_path / f"{prefix}_inequality_indices.svg")
    core.plot_inequality_indices_grid(
        df_stats_year, figures_path / f"{prefix}_inequality_indices_2x2.svg"
    )
    core.plot_gini_validation(df_gini_validation, figures_path / f"{prefix}_gini_validation.svg")
    plot_gompertz_regime_fits(
        df_regime_curves, df_regime_fits, years,
        figures_path / f"{prefix}_regime_fits_gompertz_ccdf_empirical.svg",
        ncols=4, figsize=(20, 60)
    )
    plot_pareto_regime_fits(
        df_regime_curves, df_regime_fits, years,
        figures_path / f"{prefix}_regime_fits_pareto_ccdf_empirical.svg",
        ncols=4, figsize=(20, 60)
    )

    return {
        **results,
        "df_histograms": df_histograms,
        "df_gini_validation": df_gini_validation,
        "df_regime_fits": df_regime_fits,
        "df_regime_curves": df_regime_curves,
    }


def run_analysis():
    trusted = run_analysis_layer(
        layer="trusted",
        data_path=core.TRUSTED_DATA_PATH,
        file_pattern="pnad_trusted_*.parquet",
        tables_path=core.TABLES_ANALYSIS_TRUSTED_PATH,
        figures_path=core.FIGURES_ANALYSIS_TRUSTED_PATH,
    )
    refined = run_analysis_layer(
        layer="refined",
        data_path=core.REFINED_DATA_PATH,
        file_pattern="pnad_refined_*.parquet",
        tables_path=core.TABLES_ANALYSIS_REFINED_PATH,
        figures_path=core.FIGURES_ANALYSIS_REFINED_PATH,
    )
    return {"trusted": trusted, "refined": refined}


def main():
    results = run_analysis()
    for layer in ("trusted", "refined"):
        layer_results = results[layer]
        print(f"{layer.capitalize()} processed years: {len(layer_results['years'])}")
        print(layer_results["df_regime_fits"].to_string(index=False))
        print()


if __name__ == "__main__":
    main()