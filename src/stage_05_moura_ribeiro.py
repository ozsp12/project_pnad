"""Reproduce and extend Moura Jr. & Ribeiro (EPJ B 67, 101-120, 2009).

This stage builds publication assets in the same scientific order as the four
original tables and fifteen original figures, extending the available PNAD
series through 2025. It consumes the refined analysis layer produced by stage 03
and reads refined annual Parquet files only for the income-share decomposition.
No upstream data-cleaning or regime-selection logic is duplicated here.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES_ANALYSIS = REPO_ROOT / "assets" / "tables_analysis_refined"
TABLES_PAPER = REPO_ROOT / "assets" / "tables_paper"
FIGURES_PAPER = REPO_ROOT / "assets" / "figures_paper"
REFINED_DATA = REPO_ROOT / "data" / "refined"
METADATA_PATH = REPO_ROOT / "data" / "metadata" / "df_metadata.xlsx"
GDP_GROWTH_PATH = REPO_ROOT / "data" / "auxiliary" / "gdp_growth_brazil_1978_2025.csv"

START_YEAR = 1978
END_YEAR = 2025
EARLY_END_YEAR = 1990
LATE_START_YEAR = 1992

STATS_PATH = TABLES_ANALYSIS / "refined_analysis_statistics_annual.csv"
CCDF_PATH = TABLES_ANALYSIS / "refined_analysis_ccdf_empirical.csv"
LORENZ_PATH = TABLES_ANALYSIS / "refined_analysis_lorenz.csv"
REGIME_ANNUAL_PATH = TABLES_ANALYSIS / "refined_analysis_gompertz_pareto_annual.csv"
REGIME_CURVES_PATH = TABLES_ANALYSIS / "refined_analysis_regime_curves.csv"


def _filtered_years(values):
    return sorted(int(y) for y in values if START_YEAR <= int(y) <= END_YEAR)


def _split_years(years):
    return [y for y in years if y <= EARLY_END_YEAR], [y for y in years if y >= LATE_START_YEAR]


def _save_figure(fig, stem: str):
    FIGURES_PAPER.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGURES_PAPER / f"{stem}.svg", bbox_inches="tight", dpi=250)
    plt.close(fig)


def _grid(n, ncols, width=2.7, height=2.1):
    nrows = int(math.ceil(n / ncols))
    return plt.subplots(nrows, ncols, figsize=(width * ncols, height * nrows), squeeze=False)


def _finish_grid(fig, axes, used, stem, xlabel=None, ylabel=None):
    for ax in axes.ravel()[used:]:
        ax.remove()
    if xlabel:
        fig.supxlabel(xlabel, fontsize=10)
    if ylabel:
        fig.supylabel(ylabel, fontsize=10)
    _save_figure(fig, stem)


def _load_tables():
    stats = pd.read_csv(STATS_PATH)
    ccdf = pd.read_csv(CCDF_PATH)
    lorenz = pd.read_csv(LORENZ_PATH)
    annual = pd.read_csv(REGIME_ANNUAL_PATH)
    curves = pd.read_csv(REGIME_CURVES_PATH)
    metadata = pd.read_excel(METADATA_PATH).rename(
        columns={"ano": "year", "Currency": "currency", "Exchange": "exchange"}
    )
    required_metadata = {"year", "currency", "exchange"}
    missing_metadata = required_metadata.difference(metadata.columns)
    if missing_metadata:
        raise ValueError(
            "Canonical metadata is missing required stage-05 fields: "
            + ", ".join(sorted(missing_metadata))
        )
    for frame in (stats, ccdf, lorenz, annual, curves, metadata):
        if "year" in frame.columns:
            frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    filt = lambda d: d[(d["year"] >= START_YEAR) & (d["year"] <= END_YEAR)].copy()
    return filt(stats), filt(ccdf), filt(lorenz), filt(annual), filt(curves), filt(metadata)


def build_table_01(stats, metadata):
    t = metadata[["year", "currency", "exchange"]].merge(stats[["year", "mean_nominal"]], on="year", how="inner")
    t["mean_income_current_usd"] = t["mean_nominal"] / t["exchange"]
    out = t.rename(columns={"currency": "currency_name_symbol", "exchange": "local_currency_units_per_usd"})[[
        "year", "currency_name_symbol", "local_currency_units_per_usd", "mean_income_current_usd"
    ]]
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_table_01_currency_mean_income_1978_2025.csv", index=False)
    return out


def build_table_02(annual):
    t = annual.copy()
    t["correlation_coefficient"] = np.sqrt(np.clip(pd.to_numeric(t["gompertz_r2"], errors="coerce"), 0.0, 1.0))
    out = t[["year", "gompertz_A", "gompertz_B", "gompertz_x_gmax", "correlation_coefficient", "gompertz_population_pct"]].copy()
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_table_02_gompertz_parameters_1978_2025.csv", index=False)
    return out


def build_table_03(annual):
    t = annual.copy()
    t["ls_correlation_coefficient"] = np.sqrt(np.clip(pd.to_numeric(t["pareto_ls_r2"], errors="coerce"), 0.0, 1.0))
    out = t[[
        "year", "pareto_x_pmin", "transition_x_t", "transition_delta_x_t",
        "pareto_alpha_ls", "pareto_beta_ls", "pareto_alpha_mle",
        "pareto_alpha_mle_fisher_se", "pareto_beta_mle_continuity",
        "ls_correlation_coefficient", "pareto_population_pct",
    ]].copy()
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_table_03_pareto_parameters_1978_2025.csv", index=False)
    return out


def _load_normalized_income(year):
    path = REFINED_DATA / f"pnad_refined_{year}.parquet"
    frame = pd.read_parquet(path)
    x = pd.to_numeric(frame["renda"], errors="coerce").to_numpy(float)
    x = x[np.isfinite(x) & (x > 0)]
    if x.size == 0:
        raise ValueError(f"{year}: no positive income observations")
    return x / float(np.mean(x))


def build_table_04(stats, annual):
    stats_i = stats.set_index("year")
    annual_i = annual.set_index("year")
    records = []
    for year in _filtered_years(annual["year"].dropna().astype(int)):
        if year not in stats_i.index:
            continue
        xt = float(annual_i.loc[year, "transition_x_t"])
        x = _load_normalized_income(year)
        total = float(np.sum(x))
        g = float(np.sum(x[x < xt])) / total
        p = float(np.sum(x[x >= xt])) / total
        if not np.isclose(g + p, 1.0, atol=1e-12):
            raise AssertionError(f"{year}: income shares do not sum to one")
        records.append({"year": year, "gompertz_income_share_pct": 100.0 * g, "pareto_income_share_pct": 100.0 * p, "gini_coefficient": float(stats_i.loc[year, "Gini"])})
    out = pd.DataFrame(records)
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_table_04_income_shares_gini_1978_2025.csv", index=False)
    return out


def plot_ccdf(curves, years, stem, ncols):
    fig, axes = _grid(len(years), ncols)
    for ax, year in zip(axes.ravel(), years):
        d = curves[(curves["year"] == year) & (curves["income_normalized"] > 0) & (curves["empirical_ccdf_percent"] > 0)]
        ax.plot(d["income_normalized"], d["empirical_ccdf_percent"], linewidth=1.0)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(str(year), fontsize=8)
        ax.tick_params(labelsize=6)
        ax.grid(True, which="both", alpha=0.2)
    _finish_grid(fig, axes, len(years), stem, "Normalized individual income, $x$", "Complementary cumulative distribution, $F(x)$ (%)")


def plot_lorenz(lorenz, years, stem, ncols):
    fig, axes = _grid(len(years), ncols, width=2.5, height=2.3)
    for ax, year in zip(axes.ravel(), years):
        d = lorenz[lorenz["year"] == year]
        ax.plot(100.0 * d["population_share"], 100.0 * d["income_share"], linewidth=1.1)
        ax.plot([0, 100], [0, 100], linestyle="--", linewidth=0.8)
        ax.set_title(str(year), fontsize=8)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.tick_params(labelsize=6)
        ax.grid(True, alpha=0.15)
    _finish_grid(fig, axes, len(years), stem, "Cumulative population (%)", "Cumulative income (%)")


def plot_gini(stats):
    d = stats.sort_values("year")
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    ax.plot(d["year"], d["Gini"], marker="x", markersize=4, linewidth=1.0)
    ax.set_xlabel("Year")
    ax.set_ylabel("Gini coefficient")
    ax.grid(True, alpha=0.25)
    _save_figure(fig, "moura_ribeiro_2009_figure_05_gini_1978_2025")


def _linear_fit(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y); x = x[mask]; y = y[mask]
    if len(x) < 2:
        return np.nan, np.nan, np.nan
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    tss = np.sum((y - np.mean(y)) ** 2); sse = np.sum((y - fitted) ** 2)
    return float(intercept), float(slope), float(np.nan if tss == 0 else 1.0 - sse / tss)


def build_exponential_fits(curves, annual):
    annual_i = annual.set_index("year")
    rows = []
    for year in _filtered_years(annual["year"].dropna().astype(int)):
        xg = float(annual_i.loc[year, "gompertz_x_gmax"])
        d = curves[(curves["year"] == year) & (curves["income_normalized"] <= xg) & (curves["empirical_ccdf_percent"] > 0)].copy()
        intercept, slope, r2 = _linear_fit(d["income_normalized"], np.log(d["empirical_ccdf_percent"]))
        rows.append({"year": year, "exp_intercept": intercept, "exp_lambda": -slope, "exp_r2": r2, "x_max": xg})
    out = pd.DataFrame(rows)
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_exponential_fit_diagnostics_1978_2025.csv", index=False)
    return out


def plot_exponential(curves, expfits, years, stem, ncols):
    fit_i = expfits.set_index("year")
    fig, axes = _grid(len(years), ncols)
    for ax, year in zip(axes.ravel(), years):
        fit = fit_i.loc[year]
        d = curves[(curves["year"] == year) & (curves["income_normalized"] <= fit["x_max"]) & (curves["empirical_ccdf_percent"] > 0)].copy()
        x = d["income_normalized"].to_numpy(float); y = np.log(d["empirical_ccdf_percent"].to_numpy(float))
        ax.scatter(x, y, s=7)
        ax.plot(x, fit["exp_intercept"] - fit["exp_lambda"] * x, linewidth=1.0)
        ax.set_title(str(year), fontsize=8); ax.tick_params(labelsize=6); ax.grid(True, alpha=0.2)
    _finish_grid(fig, axes, len(years), stem, "Normalized individual income, $x$", "$\ln F(x)$")


def plot_gompertz(curves, annual, years, stem, ncols):
    annual_i = annual.set_index("year")
    fig, axes = _grid(len(years), ncols)
    for ax, year in zip(axes.ravel(), years):
        fit = annual_i.loc[year]; xg = float(fit["gompertz_x_gmax"])
        d = curves[(curves["year"] == year) & (curves["income_normalized"] <= xg) & curves["gompertz_transform"].notna()].copy()
        x = d["income_normalized"].to_numpy(float)
        ax.scatter(x, d["gompertz_transform"], s=7)
        ax.plot(x, float(fit["gompertz_A"]) - float(fit["gompertz_B"]) * x, linewidth=1.0)
        ax.set_title(str(year), fontsize=8); ax.tick_params(labelsize=6); ax.grid(True, alpha=0.2)
    _finish_grid(fig, axes, len(years), stem, "Normalized individual income, $x$", "$\ln[\ln F(x)]$")


def plot_pareto(curves, annual, years, stem, ncols, method):
    annual_i = annual.set_index("year")
    fig, axes = _grid(len(years), ncols)
    for ax, year in zip(axes.ravel(), years):
        fit = annual_i.loc[year]
        if method == "ls":
            xmin = float(fit["pareto_x_pmin"]); fitted_col = "pareto_fitted_ccdf_percent_ls"
        else:
            xmin = float(fit["transition_x_t"]); fitted_col = "pareto_fitted_ccdf_percent_mle"
        d = curves[(curves["year"] == year) & (curves["income_normalized"] >= xmin) & (curves["empirical_ccdf_percent"] > 0)].copy()
        ax.scatter(d["income_normalized"], d["empirical_ccdf_percent"], s=7)
        ax.plot(d["income_normalized"], d[fitted_col], linewidth=1.0)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_title(str(year), fontsize=8)
        ax.tick_params(labelsize=6); ax.grid(True, which="both", alpha=0.2)
    _finish_grid(fig, axes, len(years), stem, "Normalized individual income, $x$", "Complementary cumulative distribution, $F(x)$ (%)")


def plot_pareto_share(table04):
    d = table04.sort_values("year")
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    ax.plot(d["year"], d["pareto_income_share_pct"], marker="x", markersize=4, linewidth=1.0)
    ax.set_xlabel("Year"); ax.set_ylabel("Pareto share of total income (%)"); ax.grid(True, alpha=0.25)
    _save_figure(fig, "moura_ribeiro_2009_figure_14_pareto_income_share_1978_2025")


def load_world_bank_gdp_growth():
    gdp = pd.read_csv(GDP_GROWTH_PATH)
    required = {"year", "gdp_growth_pct", "indicator", "source"}
    missing = required.difference(gdp.columns)
    if missing:
        raise ValueError("GDP auxiliary series is missing required fields: " + ", ".join(sorted(missing)))
    gdp["year"] = pd.to_numeric(gdp["year"], errors="raise").astype(int)
    gdp["gdp_growth_pct"] = pd.to_numeric(gdp["gdp_growth_pct"], errors="raise")
    if not (gdp["indicator"] == "NY.GDP.MKTP.KD.ZG").all():
        raise ValueError("Unexpected GDP indicator in local auxiliary series.")
    out = gdp[(gdp["year"] >= START_YEAR) & (gdp["year"] <= END_YEAR)].sort_values("year").reset_index(drop=True)
    out[["year", "gdp_growth_pct"]].to_csv(TABLES_PAPER / "moura_ribeiro_2009_figure_15_gdp_growth_1978_2025.csv", index=False)
    return out


def plot_gdp_growth(gdp):
    if gdp.empty:
        return
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    ax.plot(gdp["year"], gdp["gdp_growth_pct"], marker="x", markersize=4, linewidth=1.0)
    ax.axhline(0.0, linewidth=0.7); ax.set_xlabel("Year"); ax.set_ylabel("GDP growth (%)"); ax.grid(True, alpha=0.25)
    _save_figure(fig, "moura_ribeiro_2009_figure_15_gdp_growth_1978_2025")


def validate(table02, table03, table04):
    merged = table02[["year", "gompertz_x_gmax"]].merge(table03[["year", "pareto_x_pmin", "transition_x_t"]], on="year", how="inner")
    bad = merged[(merged["transition_x_t"] < merged["gompertz_x_gmax"] - 1e-12) | (merged["transition_x_t"] > merged["pareto_x_pmin"] + 1e-12)]
    if not bad.empty:
        raise AssertionError("Threshold ordering failed for years: " + ", ".join(map(str, bad["year"].tolist())))
    if not np.allclose(table04["gompertz_income_share_pct"] + table04["pareto_income_share_pct"], 100.0, atol=1e-8):
        raise AssertionError("Income shares must sum to 100%")


def main():
    TABLES_PAPER.mkdir(parents=True, exist_ok=True); FIGURES_PAPER.mkdir(parents=True, exist_ok=True)
    stats, ccdf, lorenz, annual, curves, metadata = _load_tables()
    years = _filtered_years(annual["year"].dropna().astype(int)); early, late = _split_years(years)

    table01 = build_table_01(stats, metadata)
    plot_ccdf(curves, early, "moura_ribeiro_2009_figure_01_ccdf_1978_1990", ncols=3)
    plot_ccdf(curves, late, "moura_ribeiro_2009_figure_02_ccdf_1992_2025", ncols=5)
    plot_lorenz(lorenz, early, "moura_ribeiro_2009_figure_03_lorenz_1978_1990", ncols=3)
    plot_lorenz(lorenz, late, "moura_ribeiro_2009_figure_04_lorenz_1992_2025", ncols=5)
    plot_gini(stats)

    expfits = build_exponential_fits(curves, annual)
    plot_exponential(curves, expfits, early, "moura_ribeiro_2009_figure_06_exponential_1978_1990", ncols=3)
    plot_exponential(curves, expfits, late, "moura_ribeiro_2009_figure_07_exponential_1992_2025", ncols=5)

    table02 = build_table_02(annual)
    plot_gompertz(curves, annual, early, "moura_ribeiro_2009_figure_08_gompertz_1978_1990", ncols=3)
    plot_gompertz(curves, annual, late, "moura_ribeiro_2009_figure_09_gompertz_1992_2025", ncols=5)

    table03 = build_table_03(annual)
    plot_pareto(curves, annual, early, "moura_ribeiro_2009_figure_10_pareto_ls_1978_1990", ncols=3, method="ls")
    plot_pareto(curves, annual, late, "moura_ribeiro_2009_figure_11_pareto_ls_1992_2025", ncols=5, method="ls")
    plot_pareto(curves, annual, early, "moura_ribeiro_2009_figure_12_pareto_mle_1978_1990", ncols=3, method="mle")
    plot_pareto(curves, annual, late, "moura_ribeiro_2009_figure_13_pareto_mle_1992_2025", ncols=5, method="mle")

    table04 = build_table_04(stats, annual); plot_pareto_share(table04)
    gdp = load_world_bank_gdp_growth(); plot_gdp_growth(gdp)
    validate(table02, table03, table04)

    manifest = pd.DataFrame([
        (1, "table", "moura_ribeiro_2009_table_01_currency_mean_income_1978_2025.csv"),
        (1, "figure", "moura_ribeiro_2009_figure_01_ccdf_1978_1990.svg"),
        (2, "figure", "moura_ribeiro_2009_figure_02_ccdf_1992_2025.svg"),
        (3, "figure", "moura_ribeiro_2009_figure_03_lorenz_1978_1990.svg"),
        (4, "figure", "moura_ribeiro_2009_figure_04_lorenz_1992_2025.svg"),
        (5, "figure", "moura_ribeiro_2009_figure_05_gini_1978_2025.svg"),
        (6, "figure", "moura_ribeiro_2009_figure_06_exponential_1978_1990.svg"),
        (7, "figure", "moura_ribeiro_2009_figure_07_exponential_1992_2025.svg"),
        (2, "table", "moura_ribeiro_2009_table_02_gompertz_parameters_1978_2025.csv"),
        (8, "figure", "moura_ribeiro_2009_figure_08_gompertz_1978_1990.svg"),
        (9, "figure", "moura_ribeiro_2009_figure_09_gompertz_1992_2025.svg"),
        (3, "table", "moura_ribeiro_2009_table_03_pareto_parameters_1978_2025.csv"),
        (10, "figure", "moura_ribeiro_2009_figure_10_pareto_ls_1978_1990.svg"),
        (11, "figure", "moura_ribeiro_2009_figure_11_pareto_ls_1992_2025.svg"),
        (12, "figure", "moura_ribeiro_2009_figure_12_pareto_mle_1978_1990.svg"),
        (13, "figure", "moura_ribeiro_2009_figure_13_pareto_mle_1992_2025.svg"),
        (4, "table", "moura_ribeiro_2009_table_04_income_shares_gini_1978_2025.csv"),
        (14, "figure", "moura_ribeiro_2009_figure_14_pareto_income_share_1978_2025.svg"),
        (15, "figure", "moura_ribeiro_2009_figure_15_gdp_growth_1978_2025.svg"),
    ], columns=["original_number", "asset_type", "filename"])
    manifest.to_csv(TABLES_PAPER / "moura_ribeiro_2009_replication_manifest.csv", index=False)
    print(f"Generated Moura-Ribeiro replication assets for {len(years)} survey years ({years[0]}-{years[-1]}).")
    print(f"Table 1 rows: {len(table01)}; Table 4 rows: {len(table04)}")


if __name__ == "__main__":
    main()
