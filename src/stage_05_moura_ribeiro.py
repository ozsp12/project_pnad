"""Trusted-data replication and extension of Moura Jr. & Ribeiro (2009).

This publication stage uses only the trusted PNAD layer. It preserves the
scientific order of the four tables and fifteen figure families in the 2009
paper, extends the annual series through 2025, attaches bootstrap uncertainties
to the fitted parameters, and produces publication figures in a monochrome
style. Multi-year figure families are split into groups of at most 12 panels
(3 columns x 4 rows) per full-page LaTeX figure.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import LogFormatterMathtext, LogLocator, NullFormatter

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES_ANALYSIS = REPO_ROOT / "assets" / "tables_analysis_trusted"
TABLES_PAPER = REPO_ROOT / "assets" / "tables_paper"
FIGURES_PAPER = REPO_ROOT / "assets" / "figures_paper"
TRUSTED_DATA = REPO_ROOT / "data" / "trusted"
METADATA_PATH = REPO_ROOT / "data" / "metadata" / "df_metadata.xlsx"
GDP_GROWTH_PATH = REPO_ROOT / "data" / "auxiliary" / "gdp_growth_brazil_1978_2025.csv"

START_YEAR = 1978
END_YEAR = 2025
BOOTSTRAP_REPS = int(os.environ.get("PNAD_BOOTSTRAP_REPS", "1000"))
BOOTSTRAP_SEED = 20090101
MAX_PANELS = 12
GRID_ROWS = 4
GRID_COLS = 3
LATEX_PAGE_FIGSIZE = (7.0, 9.5)
SINGLE_FIGSIZE = (7.0, 4.5)
PNG_DPI = 300

STATS_PATH = TABLES_ANALYSIS / "trusted_analysis_statistics_annual.csv"
CCDF_PATH = TABLES_ANALYSIS / "trusted_analysis_ccdf_empirical.csv"
LORENZ_PATH = TABLES_ANALYSIS / "trusted_analysis_lorenz.csv"
REGIME_ANNUAL_PATH = TABLES_ANALYSIS / "trusted_analysis_gompertz_pareto_annual.csv"
REGIME_CURVES_PATH = TABLES_ANALYSIS / "trusted_analysis_regime_curves.csv"

mpl.rcParams.update({
    "font.family": "serif",
    "font.size": 8.5,
    "axes.titlesize": 9,
    "axes.labelsize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 6.5,
    "axes.edgecolor": "0.20",
    "axes.linewidth": 0.7,
    "xtick.color": "0.15",
    "ytick.color": "0.15",
    "text.color": "0.10",
    "axes.labelcolor": "0.10",
    "xtick.direction": "out",
    "ytick.direction": "out",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


def _filtered_years(values):
    return sorted(int(y) for y in values if START_YEAR <= int(y) <= END_YEAR)


def _year_groups(years, size=MAX_PANELS):
    years = list(years)
    return [years[i:i + size] for i in range(0, len(years), size)]


def _prepare_figure_directory():
    """Remove obsolete generated formats before rebuilding canonical PNGs."""
    FIGURES_PAPER.mkdir(parents=True, exist_ok=True)
    for path in FIGURES_PAPER.iterdir():
        if path.is_file() and path.suffix.lower() in {".png", ".svg", ".pdf"}:
            path.unlink()


def _save_figure(fig, stem: str):
    """Save one canonical, print-resolution paper-figure format: PNG."""
    FIGURES_PAPER.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.025, 0.025, 0.995, 0.995))
    fig.savefig(
        FIGURES_PAPER / f"{stem}.png",
        format="png",
        dpi=PNG_DPI,
        pil_kwargs={"compress_level": 9},
    )
    plt.close(fig)


def _grid(n):
    if n > MAX_PANELS:
        raise ValueError(f"At most {MAX_PANELS} panels are allowed per image.")
    nrows = min(GRID_ROWS, int(math.ceil(n / GRID_COLS)))
    return plt.subplots(
        nrows,
        GRID_COLS,
        figsize=LATEX_PAGE_FIGSIZE,
        squeeze=False,
    )


def _style_axis(ax, *, log_grid=False):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("bottom", "left"):
        ax.spines[side].set_color("0.25")
        ax.spines[side].set_linewidth(0.7)
    ax.tick_params(axis="both", which="major", length=3.0, width=0.65, pad=2.5)
    ax.tick_params(axis="both", which="minor", length=1.8, width=0.45)
    ax.grid(
        True,
        which="both" if log_grid else "major",
        color="0.90",
        linewidth=0.42,
        linestyle="-",
        zorder=0,
    )
    if log_grid:
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(LogLocator(base=10, numticks=6))
            axis.set_major_formatter(LogFormatterMathtext(base=10, labelOnlyBase=True))
            axis.set_minor_locator(
                LogLocator(base=10, subs=np.arange(2, 10) * 0.1, numticks=100)
            )
            axis.set_minor_formatter(NullFormatter())


def _finish_grid(fig, axes, used, stem, xlabel=None, ylabel=None):
    for ax in axes.ravel()[used:]:
        ax.remove()
    if xlabel:
        fig.supxlabel(xlabel, fontsize=9.5, y=0.005)
    if ylabel:
        fig.supylabel(ylabel, fontsize=9.5, x=0.006)
    _save_figure(fig, stem)


def _annotation(ax, text, loc=(0.04, 0.96), *, ha="left", va="top"):
    ax.text(
        loc[0],
        loc[1],
        text,
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=6.7,
        linespacing=1.22,
        zorder=10,
        bbox=dict(
            boxstyle="round,pad=0.26",
            facecolor="white",
            edgecolor="0.45",
            linewidth=0.55,
            alpha=0.94,
        ),
    )


def _compact_legend(ax, loc="lower right"):
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return
    ax.legend(
        handles,
        labels,
        loc=loc,
        frameon=True,
        facecolor="white",
        edgecolor="0.65",
        framealpha=0.92,
        fancybox=False,
        borderpad=0.28,
        labelspacing=0.25,
        handlelength=2.2,
        handletextpad=0.45,
    )


def _linear_fit(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size < 2 or np.ptp(x) <= 0:
        return np.nan, np.nan, np.nan
    xm = x.mean(); ym = y.mean()
    den = np.sum((x - xm) ** 2)
    if den <= 0:
        return np.nan, np.nan, np.nan
    slope = np.sum((x - xm) * (y - ym)) / den
    intercept = ym - slope * xm
    fitted = intercept + slope * x
    tss = np.sum((y - ym) ** 2)
    sse = np.sum((y - fitted) ** 2)
    r2 = np.nan if tss <= 0 else 1.0 - sse / tss
    return float(intercept), float(slope), float(r2)


def _bootstrap_line(x, y, rng, reps=BOOTSTRAP_REPS):
    """Pairs bootstrap for a fitted straight line, as in the 2009 LS error analysis."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]; y = y[mask]
    n = x.size
    if n < 3:
        return np.full(reps, np.nan), np.full(reps, np.nan)
    idx = rng.integers(0, n, size=(reps, n))
    xb = x[idx]; yb = y[idx]
    xm = xb.mean(axis=1); ym = yb.mean(axis=1)
    dx = xb - xm[:, None]
    den = np.sum(dx * dx, axis=1)
    num = np.sum(dx * (yb - ym[:, None]), axis=1)
    slope = np.divide(num, den, out=np.full(reps, np.nan), where=den > 0)
    intercept = ym - slope * xm
    return intercept, slope


def _r2_log_observed_fitted(observed, fitted):
    observed = np.asarray(observed, float); fitted = np.asarray(fitted, float)
    mask = np.isfinite(observed) & np.isfinite(fitted) & (observed > 0) & (fitted > 0)
    if mask.sum() < 2:
        return np.nan
    y = np.log(observed[mask]); yh = np.log(fitted[mask])
    tss = np.sum((y - y.mean()) ** 2)
    sse = np.sum((y - yh) ** 2)
    return float(np.nan if tss <= 0 else 1.0 - sse / tss)


def _load_tables():
    stats = pd.read_csv(STATS_PATH)
    ccdf = pd.read_csv(CCDF_PATH)
    lorenz = pd.read_csv(LORENZ_PATH)
    annual = pd.read_csv(REGIME_ANNUAL_PATH)
    curves = pd.read_csv(REGIME_CURVES_PATH)
    metadata = pd.read_excel(METADATA_PATH).rename(
        columns={"ano": "year", "Currency": "currency", "Exchange": "exchange"}
    )
    for frame in (stats, ccdf, lorenz, annual, curves, metadata):
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    filt = lambda d: d[(d["year"] >= START_YEAR) & (d["year"] <= END_YEAR)].copy()
    return filt(stats), filt(ccdf), filt(lorenz), filt(annual), filt(curves), filt(metadata)


def _load_normalized_income(year):
    path = TRUSTED_DATA / f"pnad_trusted_{year}.parquet"
    frame = pd.read_parquet(path, columns=["renda"])
    x = pd.to_numeric(frame["renda"], errors="coerce").to_numpy(float)
    x = x[np.isfinite(x) & (x > 0)]
    if x.size == 0:
        raise ValueError(f"{year}: no positive trusted income observations")
    return x / float(np.mean(x))


def _continuity_beta(alpha, x_t, A, B):
    F_t = float(np.exp(np.exp(A - B * x_t)))
    return float(F_t * x_t ** alpha)


def build_bootstrap_uncertainties(curves, annual):
    """Compute 1000-replicate bootstrap errors for fitted Gompertz and Pareto parameters.

    LS errors use a pairs bootstrap on the selected cumulative fitting coordinates,
    matching the replacement bootstrap described by Moura Jr. & Ribeiro (2009).
    Direct-MLE errors use a nonparametric bootstrap of the trusted tail observations
    at the empirically selected annual threshold.
    """
    rows = []
    annual_i = annual.set_index("year")
    years = _filtered_years(annual["year"].dropna().astype(int))
    for year in years:
        fit = annual_i.loc[year]
        rng = np.random.default_rng(BOOTSTRAP_SEED + int(year))

        xg = float(fit["gompertz_x_gmax"])
        gd = curves[(curves["year"] == year) & (curves["income_normalized"] <= xg) & curves["gompertz_transform"].notna()]
        gi, gs = _bootstrap_line(gd["income_normalized"], gd["gompertz_transform"], rng)
        A_boot = gi
        B_boot = -gs

        xp = float(fit["pareto_x_pmin"])
        pd_tail = curves[(curves["year"] == year) & (curves["income_normalized"] >= xp) & (curves["empirical_ccdf_percent"] > 0)]
        pi, ps = _bootstrap_line(np.log(pd_tail["income_normalized"]), np.log(pd_tail["empirical_ccdf_percent"]), rng)
        alpha_ls_boot = -ps
        beta_ls_boot = np.exp(pi)

        xt = float(fit["transition_x_t"])
        x = _load_normalized_income(year)
        tail = x[x >= xt]
        z = np.log(tail / xt)
        n = len(z)
        if n < 2:
            alpha_mle_boot = np.full(BOOTSTRAP_REPS, np.nan)
        else:
            idx = rng.integers(0, n, size=(BOOTSTRAP_REPS, n))
            sums = z[idx].sum(axis=1)
            alpha_mle_boot = np.divide(n, sums, out=np.full(BOOTSTRAP_REPS, np.nan), where=sums > 0)
        beta_mle_boot = np.array([
            _continuity_beta(a, xt, float(fit["gompertz_A"]), float(fit["gompertz_B"]))
            if np.isfinite(a) else np.nan for a in alpha_mle_boot
        ])

        def sd(v):
            v = np.asarray(v, float); v = v[np.isfinite(v)]
            return float(np.std(v, ddof=1)) if v.size > 1 else np.nan

        rows.append({
            "year": year,
            "bootstrap_reps": BOOTSTRAP_REPS,
            "gompertz_A_bootstrap_se": sd(A_boot),
            "gompertz_B_bootstrap_se": sd(B_boot),
            "pareto_alpha_ls_bootstrap_se": sd(alpha_ls_boot),
            "pareto_beta_ls_bootstrap_se": sd(beta_ls_boot),
            "pareto_alpha_mle_bootstrap_se": sd(alpha_mle_boot),
            "pareto_beta_mle_bootstrap_se": sd(beta_mle_boot),
        })
    out = pd.DataFrame(rows)
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_bootstrap_uncertainties_trusted_1978_2025.csv", index=False)
    return out


def build_table_01(stats, metadata):
    t = metadata[["year", "currency", "exchange"]].merge(stats[["year", "mean_nominal"]], on="year", how="inner")
    t["mean_income_current_usd"] = t["mean_nominal"] / t["exchange"]
    out = t.rename(columns={"currency": "currency_name_symbol", "exchange": "local_currency_units_per_usd"})[[
        "year", "currency_name_symbol", "local_currency_units_per_usd", "mean_income_current_usd"
    ]]
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_table_01_currency_mean_income_trusted_1978_2025.csv", index=False)
    return out


def build_table_02(annual, boot):
    t = annual.merge(boot, on="year", how="left")
    t["correlation_coefficient"] = np.sqrt(np.clip(pd.to_numeric(t["gompertz_r2"], errors="coerce"), 0.0, 1.0))
    out = t[[
        "year", "gompertz_A", "gompertz_A_bootstrap_se", "gompertz_B", "gompertz_B_bootstrap_se",
        "gompertz_x_gmax", "correlation_coefficient", "gompertz_population_pct"
    ]].copy()
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_table_02_gompertz_parameters_trusted_1978_2025.csv", index=False)
    return out


def build_table_03(annual, curves, boot):
    t = annual.merge(boot, on="year", how="left").copy()
    t["ls_correlation_coefficient"] = np.sqrt(np.clip(pd.to_numeric(t["pareto_ls_r2"], errors="coerce"), 0.0, 1.0))
    mle_r2 = []
    for _, row in t.iterrows():
        year = int(row["year"]); xt = float(row["transition_x_t"])
        d = curves[(curves["year"] == year) & (curves["income_normalized"] >= xt) & (curves["empirical_ccdf_percent"] > 0)]
        mle_r2.append(_r2_log_observed_fitted(d["empirical_ccdf_percent"], d["pareto_fitted_ccdf_percent_mle"]))
    t["pareto_mle_r2_diagnostic"] = mle_r2
    out = t[[
        "year", "pareto_x_pmin", "transition_x_t", "transition_delta_x_t",
        "pareto_alpha_ls", "pareto_alpha_ls_bootstrap_se", "pareto_beta_ls", "pareto_beta_ls_bootstrap_se",
        "pareto_alpha_mle", "pareto_alpha_mle_bootstrap_se", "pareto_beta_mle_continuity", "pareto_beta_mle_bootstrap_se",
        "ls_correlation_coefficient", "pareto_mle_r2_diagnostic", "pareto_population_pct",
    ]].copy()
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_table_03_pareto_parameters_trusted_1978_2025.csv", index=False)
    return out


def build_table_04(stats, annual):
    stats_i = stats.set_index("year"); annual_i = annual.set_index("year")
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
        records.append({
            "year": year,
            "gompertz_income_share_pct": 100.0 * g,
            "pareto_income_share_pct": 100.0 * p,
            "gini_coefficient": float(stats_i.loc[year, "Gini"]),
            "pietra_index": float(stats_i.loc[year, "Pietra"]),
            "kolkata_index": float(stats_i.loc[year, "Kolkata"]),
            "zanardi_index": float(stats_i.loc[year, "Zanardi"]),
        })
    out = pd.DataFrame(records)
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_table_04_income_shares_gini_trusted_1978_2025.csv", index=False)
    return out


def build_exponential_fits(curves, annual):
    annual_i = annual.set_index("year"); rows = []
    for year in _filtered_years(annual["year"].dropna().astype(int)):
        xg = float(annual_i.loc[year, "gompertz_x_gmax"])
        d = curves[(curves["year"] == year) & (curves["income_normalized"] <= xg) & (curves["empirical_ccdf_percent"] > 0)]
        intercept, slope, r2 = _linear_fit(d["income_normalized"], np.log(d["empirical_ccdf_percent"]))
        rows.append({"year": year, "exp_intercept": intercept, "exp_alpha": -slope, "exp_r2": r2, "x_max": xg})
    out = pd.DataFrame(rows)
    out.to_csv(TABLES_PAPER / "moura_ribeiro_2009_exponential_fit_diagnostics_trusted_1978_2025.csv", index=False)
    return out


def _plot_grouped(years, prefix, plot_group):
    stems = []
    groups = _year_groups(years)
    for i, group in enumerate(groups, 1):
        stem = f"{prefix}_part_{i:02d}"
        plot_group(group, stem)
        stems.append(stem)
    return stems


def plot_ccdf(curves, annual, years):
    annual_i = annual.set_index("year")

    def group_plot(group, stem):
        fig, axes = _grid(len(group))
        for ax, year in zip(axes.ravel(), group):
            fit = annual_i.loc[year]
            xt = float(fit["transition_x_t"])
            d = curves[
                (curves["year"] == year)
                & (curves["income_normalized"] > 0)
                & (curves["empirical_ccdf_percent"] > 0)
            ]
            ax.plot(
                d["income_normalized"],
                d["empirical_ccdf_percent"],
                color="0.08",
                linewidth=1.05,
            )
            ax.axvline(xt, color="0.40", linestyle="--", linewidth=0.9)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(str(year), fontweight="semibold")
            _style_axis(ax, log_grid=True)
            _annotation(ax, rf"$x_t = {xt:.3f}$", loc=(0.05, 0.10), va="bottom")
        _finish_grid(
            fig,
            axes,
            len(group),
            stem,
            "Normalized individual income, $x$",
            "CCDF, $F(x)$ (%)",
        )

    return _plot_grouped(years, "moura_ribeiro_2009_ccdf_trusted", group_plot)


def plot_lorenz_geometry(lorenz, stats, years):
    stats_i = stats.set_index("year")

    def group_plot(group, stem):
        fig, axes = _grid(len(group))
        for ax, year in zip(axes.ravel(), group):
            d = lorenz[lorenz["year"] == year]
            row = stats_i.loc[year]
            p = 100.0 * d["population_share"].to_numpy(float)
            L = 100.0 * d["income_share"].to_numpy(float)
            ax.fill_between(p, 0, L, facecolor="0.94", edgecolor="none", zorder=1)
            ax.plot(p, L, color="0.10", linewidth=1.35, label="Lorenz curve", zorder=3)
            ax.plot(
                [0, 100],
                [0, 100],
                color="0.45",
                linestyle="--",
                linewidth=0.9,
                label="Equality line",
                zorder=2,
            )
            k = 100.0 * float(row["Kolkata"])
            q = 100.0 - k
            ax.plot([k, k], [0, q], color="0.35", linestyle=":", linewidth=0.85)
            ax.plot([0, k], [q, q], color="0.35", linestyle=":", linewidth=0.85)
            ax.scatter(
                [k],
                [q],
                marker="o",
                facecolors="white",
                edgecolors="0.10",
                s=20,
                linewidths=0.8,
                zorder=4,
            )
            diff = p - L
            ip = int(np.argmax(diff))
            px = p[ip]
            py = L[ip]
            ax.plot([px, px], [py, px], color="0.25", linestyle="-.", linewidth=0.85)
            ax.scatter(
                [px],
                [py],
                marker="s",
                facecolors="white",
                edgecolors="0.10",
                s=16,
                linewidths=0.8,
                zorder=4,
            )
            ax.set_title(str(year), fontweight="semibold")
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 100)
            ax.set_aspect("equal", adjustable="box")
            _style_axis(ax)
            _annotation(
                ax,
                "\n".join([
                    rf"Gini: $G = {float(row['Gini']):.3f}$",
                    rf"Kolkata: $k = {k:.2f}\%$",
                    rf"Zanardi: $Z = {float(row['Zanardi']):.3f}$",
                    rf"Pietra: $P = {100.0 * float(row['Pietra']):.2f}\%$",
                ]),
            )
            _compact_legend(ax, loc="lower right")
        _finish_grid(
            fig,
            axes,
            len(group),
            stem,
            "Cumulative population (%)",
            "Cumulative income (%)",
        )

    return _plot_grouped(years, "moura_ribeiro_2009_lorenz_geometry_trusted", group_plot)


def plot_gini(stats):
    d = stats.sort_values("year")
    fig, ax = plt.subplots(figsize=SINGLE_FIGSIZE)
    ax.plot(
        d["year"],
        d["Gini"],
        color="0.08",
        marker="o",
        markerfacecolor="white",
        markeredgecolor="0.08",
        markersize=4,
        linewidth=1.2,
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("Gini coefficient")
    _style_axis(ax)
    _save_figure(fig, "moura_ribeiro_2009_figure_05_gini_trusted_1978_2025")


def plot_exponential(curves, expfits, years):
    fit_i = expfits.set_index("year")

    def group_plot(group, stem):
        fig, axes = _grid(len(group))
        for ax, year in zip(axes.ravel(), group):
            fit = fit_i.loc[year]
            d = curves[
                (curves["year"] == year)
                & (curves["income_normalized"] <= fit["x_max"])
                & (curves["empirical_ccdf_percent"] > 0)
            ]
            x = d["income_normalized"].to_numpy(float)
            y = np.log(d["empirical_ccdf_percent"].to_numpy(float))
            ax.scatter(
                x,
                y,
                marker="o",
                facecolors="white",
                edgecolors="0.15",
                s=12,
                linewidths=0.6,
                label="Empirical",
            )
            order = np.argsort(x)
            x = x[order]
            ax.plot(
                x,
                float(fit["exp_intercept"]) - float(fit["exp_alpha"]) * x,
                color="0.10",
                linewidth=1.05,
                label="Exponential fit",
            )
            ax.set_title(str(year), fontweight="semibold")
            _style_axis(ax)
            _annotation(
                ax,
                "\n".join([
                    rf"$\alpha = {float(fit['exp_alpha']):.3f}$",
                    rf"$R^2 = {float(fit['exp_r2']):.3f}$",
                ]),
            )
            _compact_legend(ax, loc="lower left")
        _finish_grid(
            fig,
            axes,
            len(group),
            stem,
            "Normalized individual income, $x$",
            r"$\ln F(x)$",
        )

    return _plot_grouped(years, "moura_ribeiro_2009_exponential_trusted", group_plot)


def plot_gompertz(curves, annual, boot, years):
    fit_i = annual.set_index("year")
    boot_i = boot.set_index("year")

    def group_plot(group, stem):
        fig, axes = _grid(len(group))
        for ax, year in zip(axes.ravel(), group):
            fit = fit_i.loc[year]
            b = boot_i.loc[year]
            xg = float(fit["gompertz_x_gmax"])
            d = curves[
                (curves["year"] == year)
                & (curves["income_normalized"] <= xg)
                & curves["gompertz_transform"].notna()
            ]
            x = d["income_normalized"].to_numpy(float)
            y = d["gompertz_transform"].to_numpy(float)
            ax.scatter(
                x,
                y,
                marker="o",
                facecolors="white",
                edgecolors="0.15",
                s=12,
                linewidths=0.6,
                label="Empirical",
            )
            order = np.argsort(x)
            xline = x[order]
            ax.plot(
                xline,
                float(fit["gompertz_A"]) - float(fit["gompertz_B"]) * xline,
                color="0.08",
                linewidth=1.15,
                label="Gompertz LS",
            )
            ax.axvline(
                xg,
                color="0.45",
                linestyle="--",
                linewidth=0.8,
                label=r"$x_{G,\max}$",
            )
            ax.set_title(str(year), fontweight="semibold")
            _style_axis(ax)
            _annotation(
                ax,
                "\n".join([
                    rf"$A = {float(fit['gompertz_A']):.3f} \pm {float(b['gompertz_A_bootstrap_se']):.3f}$",
                    rf"$B = {float(fit['gompertz_B']):.3f} \pm {float(b['gompertz_B_bootstrap_se']):.3f}$",
                    rf"$R^2 = {float(fit['gompertz_r2']):.3f}$",
                    rf"$x_{{G,\max}} = {xg:.3f}$",
                ]),
            )
            _compact_legend(ax, loc="lower left")
        _finish_grid(
            fig,
            axes,
            len(group),
            stem,
            "Normalized individual income, $x$",
            r"$\ln[\ln F(x)]$",
        )

    return _plot_grouped(years, "moura_ribeiro_2009_gompertz_trusted", group_plot)


def plot_pareto(curves, annual, boot, years, method):
    fit_i = annual.set_index("year")
    boot_i = boot.set_index("year")

    def group_plot(group, stem):
        fig, axes = _grid(len(group))
        for ax, year in zip(axes.ravel(), group):
            fit = fit_i.loc[year]
            b = boot_i.loc[year]
            xt = float(fit["transition_x_t"])
            xp = float(fit["pareto_x_pmin"])
            if method == "ls":
                xmin = xp
                fitted_col = "pareto_fitted_ccdf_percent_ls"
                alpha = float(fit["pareto_alpha_ls"])
                ase = float(b["pareto_alpha_ls_bootstrap_se"])
                beta = float(fit["pareto_beta_ls"])
                r2 = float(fit["pareto_ls_r2"])
                linestyle = "-"
                fit_label = "Pareto LS"
                alpha_symbol = r"\alpha_{\mathrm{LS}}"
                beta_symbol = r"\beta_{\mathrm{LS}}"
                r2_symbol = r"R^2_{\mathrm{LS}}"
            else:
                xmin = xt
                fitted_col = "pareto_fitted_ccdf_percent_mle"
                alpha = float(fit["pareto_alpha_mle"])
                ase = float(b["pareto_alpha_mle_bootstrap_se"])
                beta = float(fit["pareto_beta_mle_continuity"])
                linestyle = "--"
                fit_label = "Pareto MLE"
                alpha_symbol = r"\alpha_{\mathrm{MLE}}"
                beta_symbol = r"\beta_{\mathrm{MLE}}"
                r2_symbol = r"R^2_{\mathrm{MLE}}"
                d0 = curves[
                    (curves["year"] == year)
                    & (curves["income_normalized"] >= xmin)
                    & (curves["empirical_ccdf_percent"] > 0)
                ]
                r2 = _r2_log_observed_fitted(
                    d0["empirical_ccdf_percent"],
                    d0[fitted_col],
                )
            d = curves[
                (curves["year"] == year)
                & (curves["income_normalized"] >= xmin)
                & (curves["empirical_ccdf_percent"] > 0)
            ]
            ax.scatter(
                d["income_normalized"],
                d["empirical_ccdf_percent"],
                marker="o",
                facecolors="white",
                edgecolors="0.15",
                s=12,
                linewidths=0.6,
                label="Empirical",
            )
            ax.plot(
                d["income_normalized"],
                d[fitted_col],
                color="0.08",
                linestyle=linestyle,
                linewidth=1.15,
                label=fit_label,
            )
            ax.axvline(
                xt,
                color="0.45",
                linestyle=":",
                linewidth=0.85,
                label=r"$x_t$",
            )
            if method == "ls" and not np.isclose(xp, xt):
                ax.axvline(
                    xp,
                    color="0.60",
                    linestyle="--",
                    linewidth=0.75,
                    label=r"$x_{P,\min}$",
                )
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(str(year), fontweight="semibold")
            _style_axis(ax, log_grid=True)
            annotation_lines = [
                rf"${alpha_symbol} = {alpha:.3f} \pm {ase:.3f}$",
                rf"${beta_symbol} = {beta:.2e}$",
                rf"${r2_symbol} = {r2:.3f}$",
            ]
            if method == "ls":
                annotation_lines.append(rf"$x_{{P,\min}} = {xp:.3f}$")
            annotation_lines.append(rf"$x_t = {xt:.3f}$")
            _annotation(ax, "\n".join(annotation_lines))
            _compact_legend(ax, loc="lower left")
        _finish_grid(
            fig,
            axes,
            len(group),
            stem,
            "Normalized individual income, $x$",
            "CCDF, $F(x)$ (%)",
        )

    prefix = (
        "moura_ribeiro_2009_pareto_ls_trusted"
        if method == "ls"
        else "moura_ribeiro_2009_pareto_mle_trusted"
    )
    return _plot_grouped(years, prefix, group_plot)


def plot_pareto_share(table04, annual):
    d = table04.sort_values("year"); a = annual.set_index("year")
    yerr_lo = []; yerr_hi = []
    for _, row in d.iterrows():
        year = int(row["year"]); x = _load_normalized_income(year); total = x.sum()
        xg = float(a.loc[year, "gompertz_x_gmax"]); xp = float(a.loc[year, "pareto_x_pmin"])
        s_at_xg = 100.0 * x[x >= xg].sum() / total
        s_at_xp = 100.0 * x[x >= xp].sum() / total
        center = float(row["pareto_income_share_pct"])
        lo = min(s_at_xg, s_at_xp, center); hi = max(s_at_xg, s_at_xp, center)
        yerr_lo.append(center - lo); yerr_hi.append(hi - center)
    fig, ax = plt.subplots(figsize=SINGLE_FIGSIZE)
    ax.errorbar(
        d["year"],
        d["pareto_income_share_pct"],
        yerr=np.vstack([yerr_lo, yerr_hi]),
        fmt="o-",
        color="0.08",
        ecolor="0.45",
        markerfacecolor="white",
        markeredgecolor="0.08",
        markersize=4,
        linewidth=1.15,
        elinewidth=0.8,
        capsize=2.0,
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("Pareto share of total income (%)")
    _style_axis(ax)
    _save_figure(fig, "moura_ribeiro_2009_figure_14_pareto_income_share_trusted_1978_2025")


def load_world_bank_gdp_growth():
    gdp = pd.read_csv(GDP_GROWTH_PATH)
    gdp["year"] = pd.to_numeric(gdp["year"], errors="raise").astype(int)
    gdp["gdp_growth_pct"] = pd.to_numeric(gdp["gdp_growth_pct"], errors="raise")
    out = gdp[(gdp["year"] >= START_YEAR) & (gdp["year"] <= END_YEAR)].sort_values("year").reset_index(drop=True)
    out[["year", "gdp_growth_pct"]].to_csv(TABLES_PAPER / "moura_ribeiro_2009_figure_15_gdp_growth_1978_2025.csv", index=False)
    return out


def plot_gdp_growth(gdp):
    fig, ax = plt.subplots(figsize=SINGLE_FIGSIZE)
    ax.plot(
        gdp["year"],
        gdp["gdp_growth_pct"],
        color="0.08",
        marker="s",
        markerfacecolor="white",
        markeredgecolor="0.08",
        markersize=3.5,
        linewidth=1.1,
    )
    ax.axhline(0.0, color="0.45", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Year")
    ax.set_ylabel("Real GDP growth (%)")
    _style_axis(ax)
    _save_figure(fig, "moura_ribeiro_2009_figure_15_gdp_growth_1978_2025")


def validate(table02, table03, table04, groups):
    merged = table02[["year", "gompertz_x_gmax"]].merge(table03[["year", "pareto_x_pmin", "transition_x_t"]], on="year", how="inner")
    bad = merged[(merged["transition_x_t"] < merged["gompertz_x_gmax"] - 1e-12) | (merged["transition_x_t"] > merged["pareto_x_pmin"] + 1e-12)]
    if not bad.empty:
        raise AssertionError("Threshold ordering failed: " + ", ".join(map(str, bad["year"])))
    if not np.allclose(table04["gompertz_income_share_pct"] + table04["pareto_income_share_pct"], 100.0, atol=1e-8):
        raise AssertionError("Income shares must sum to 100%")
    for g in groups:
        if len(g) > MAX_PANELS:
            raise AssertionError("A multi-panel image exceeds 12 annual panels")


def main():
    TABLES_PAPER.mkdir(parents=True, exist_ok=True)
    _prepare_figure_directory()
    stats, ccdf, lorenz, annual, curves, metadata = _load_tables()
    years = _filtered_years(annual["year"].dropna().astype(int)); groups = _year_groups(years)

    boot = build_bootstrap_uncertainties(curves, annual)
    table01 = build_table_01(stats, metadata)
    table02 = build_table_02(annual, boot)
    table03 = build_table_03(annual, curves, boot)
    table04 = build_table_04(stats, annual)
    expfits = build_exponential_fits(curves, annual)

    figure_stems = []
    figure_stems += plot_ccdf(curves, annual, years)
    figure_stems += plot_lorenz_geometry(lorenz, stats, years)
    plot_gini(stats); figure_stems.append("moura_ribeiro_2009_figure_05_gini_trusted_1978_2025")
    figure_stems += plot_exponential(curves, expfits, years)
    figure_stems += plot_gompertz(curves, annual, boot, years)
    figure_stems += plot_pareto(curves, annual, boot, years, method="ls")
    figure_stems += plot_pareto(curves, annual, boot, years, method="mle")
    plot_pareto_share(table04, annual); figure_stems.append("moura_ribeiro_2009_figure_14_pareto_income_share_trusted_1978_2025")
    gdp = load_world_bank_gdp_growth(); plot_gdp_growth(gdp); figure_stems.append("moura_ribeiro_2009_figure_15_gdp_growth_1978_2025")

    validate(table02, table03, table04, groups)

    manifest_rows = []
    for stem in figure_stems:
        manifest_rows.append({"asset_type": "figure", "stem": stem, "png": f"{stem}.png"})
    for name in [
        "moura_ribeiro_2009_table_01_currency_mean_income_trusted_1978_2025.csv",
        "moura_ribeiro_2009_table_02_gompertz_parameters_trusted_1978_2025.csv",
        "moura_ribeiro_2009_table_03_pareto_parameters_trusted_1978_2025.csv",
        "moura_ribeiro_2009_table_04_income_shares_gini_trusted_1978_2025.csv",
        "moura_ribeiro_2009_bootstrap_uncertainties_trusted_1978_2025.csv",
    ]:
        manifest_rows.append({"asset_type": "table", "stem": Path(name).stem, "png": ""})
    pd.DataFrame(manifest_rows).to_csv(TABLES_PAPER / "moura_ribeiro_2009_replication_manifest_trusted.csv", index=False)

    print(f"Trusted Moura-Ribeiro assets: {len(years)} annual surveys, {len(groups)} pages per multi-year figure family.")
    print(f"Bootstrap: {BOOTSTRAP_REPS} resamples per year; seed base={BOOTSTRAP_SEED}.")
    print(f"Table 1 rows={len(table01)}, Table 4 rows={len(table04)}.")


if __name__ == "__main__":
    main()
