"""Canonical Stage-05 publication layer for trusted PNAD outputs.

Stage 05 consumes only persisted scientific results produced by Stage 03 plus
trusted microdata needed for descriptive publication graphics.  It does not
estimate model parameters, bootstrap uncertainties, likelihood widths, regime
shares, or other scientific diagnostics.

Multi-year figure families use at most 12 panels (3 x 4) per image.
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import LogFormatterMathtext, LogLocator, NullFormatter

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "assets" / "tables_analysis_trusted"
PAPER_TABLES = ROOT / "assets" / "tables_paper"
FIGURES = ROOT / "assets" / "figures_paper"
TRUSTED = ROOT / "data" / "trusted"
METADATA = ROOT / "data" / "metadata" / "df_metadata.xlsx"
GDP = ROOT / "data" / "auxiliary" / "gdp_growth_brazil_1978_2025.csv"

START_YEAR, END_YEAR = 1978, 2025
MAX_PANELS = 12
PAGE_SIZE = (7.0, 9.5)
SINGLE_SIZE = (7.0, 4.5)
DPI = 300

mpl.rcParams.update({
    "font.family": "serif", "font.size": 8.5, "axes.titlesize": 9,
    "axes.labelsize": 9, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7, "axes.edgecolor": "0.20", "axes.linewidth": 0.7,
    "xtick.color": "0.15", "ytick.color": "0.15", "text.color": "0.10",
    "axes.labelcolor": "0.10", "xtick.direction": "out", "ytick.direction": "out",
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})


def years_of(values):
    return sorted(int(y) for y in values if START_YEAR <= int(y) <= END_YEAR)


def groups(years):
    years = list(years)
    return [years[i:i + MAX_PANELS] for i in range(0, len(years), MAX_PANELS)]


def load_inputs():
    """Load the persisted Stage-03 trusted tables used by publication figures."""
    stats = pd.read_csv(TABLES / "statistics_annual.csv")
    lorenz = pd.read_csv(TABLES / "lorenz.csv")
    gompertz = pd.read_csv(TABLES / "gompertz_annual.csv")
    pareto = pd.read_csv(TABLES / "pareto_annual.csv")
    curves = pd.read_csv(TABLES / "gompertz_pareto_curves.csv")
    meta = pd.read_excel(METADATA).rename(columns={"ano": "year", "Exchange": "exchange"})
    annual = gompertz.merge(
        pareto,
        on="year",
        validate="one_to_one",
        suffixes=("", "_pareto"),
    )
    frames = [stats, lorenz, annual, curves, meta]
    for frame in frames:
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
        frame.drop(
            frame[(frame["year"] < START_YEAR) | (frame["year"] > END_YEAR)].index,
            inplace=True,
        )
    return stats, lorenz, annual, curves, meta


def income(year, positive=True):
    x = pd.to_numeric(
        pd.read_parquet(
            TRUSTED / f"pnad_trusted_{year}.parquet",
            columns=["renda"],
        )["renda"],
        errors="coerce",
    ).to_numpy(float)
    x = x[np.isfinite(x)]
    return x[x > 0] if positive else x


def adjusted_income(year, meta_i, positive=True):
    x = income(year, positive)
    row = meta_i.loc[year]
    return x / float(row["exchange"]) * float(row["Inflation"])


def clean_figures():
    FIGURES.mkdir(parents=True, exist_ok=True)
    for path in FIGURES.iterdir():
        if path.is_file() and path.suffix.lower() in {".png", ".svg", ".pdf"}:
            path.unlink()


def style(ax, log=False):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, which="both" if log else "major", color="0.90", lw=0.42)
    if log:
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(LogLocator(base=10, numticks=6))
            axis.set_major_formatter(LogFormatterMathtext(base=10, labelOnlyBase=True))
            axis.set_minor_locator(
                LogLocator(base=10, subs=np.arange(2, 10) * 0.1, numticks=100)
            )
            axis.set_minor_formatter(NullFormatter())


def annotation(ax, text, x=0.05, y=0.08, ha="left"):
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha=ha,
        va="bottom",
        fontsize=6.7,
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="white",
            edgecolor="0.55",
            alpha=0.94,
        ),
    )


def save(fig, stem, top=0.985):
    fig.tight_layout(rect=(0.025, 0.025, 0.995, top))
    fig.savefig(FIGURES / f"{stem}.png", dpi=DPI, pil_kwargs={"compress_level": 9})
    plt.close(fig)


def grid(n):
    if n > MAX_PANELS:
        raise ValueError(f"At most {MAX_PANELS} panels are allowed per image.")
    rows = min(4, math.ceil(n / 3))
    return plt.subplots(rows, 3, figsize=PAGE_SIZE, squeeze=False)


def global_legend(fig, axes, used, ncol=4):
    handles, labels, seen = [], [], set()
    for ax in axes.ravel()[:used]:
        for handle, label in zip(*ax.get_legend_handles_labels()):
            if label and label not in seen:
                handles.append(handle)
                labels.append(label)
                seen.add(label)
    if handles:
        fig.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.982),
            ncol=min(ncol, len(handles)),
            frameon=False,
            handlelength=2.8,
        )


def finish_grid(fig, axes, used, stem, xlabel, ylabel, legend=False, ncol=4):
    for ax in axes.ravel()[used:]:
        ax.remove()
    fig.supxlabel(xlabel, fontsize=9.5, y=0.005)
    fig.supylabel(ylabel, fontsize=9.5, x=0.006)
    if legend:
        global_legend(fig, axes, used, ncol)
    save(fig, stem, 0.92 if legend else 0.985)


def family(years, stem, draw, xlabel, ylabel, legend=False, ncol=4):
    out = []
    for part, group in enumerate(groups(years), 1):
        name = f"{stem}_part_{part:02d}"
        fig, axes = grid(len(group))
        for ax, year in zip(axes.ravel(), group):
            draw(ax, year)
            ax.set_title(str(year), fontweight="semibold")
        finish_grid(fig, axes, len(group), name, xlabel, ylabel, legend, ncol)
        out.append(name)
    return out


def plot_histograms(years, meta):
    def draw(ax, year):
        x = income(year, positive=False)
        x = x[x >= 0]
        counts, edges = np.histogram(x, bins=100)
        ax.bar(
            edges[:-1],
            counts,
            width=np.diff(edges),
            align="edge",
            facecolor="white",
            edgecolor="0.12",
            linewidth=0.35,
        )
        ax.set_yscale("log")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, axis="y", which="major", color="0.90", lw=0.42)

    return family(years, "histograms", draw, "Income", "Frequency (log)")


def plot_income_statistics(stats, years, meta):
    meta_i = meta.set_index("year")
    minimum = {
        year: float(adjusted_income(year, meta_i, False).min())
        for year in years
    }
    data = stats[stats.year.isin(years)].sort_values("year").copy()
    data["std_mean_ratio"] = data["std"] / data["mean"]
    data["xmin"] = data["year"].map(minimum)
    panels = [
        ("mean", "Mean", "2025 US$"),
        ("median", "Median", "2025 US$"),
        ("std", "Standard deviation", "2025 US$"),
        ("std_mean_ratio", r"Dispersion $\sigma/\mu$", r"$\sigma/\mu$"),
        ("xmax", "Maximum", "2025 US$"),
        ("xmin", "Minimum (sanity check)", "2025 US$"),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(7, 6.6), sharex=True)
    for ax, (column, title, ylabel) in zip(axes.ravel(), panels):
        ax.plot(
            data.year,
            data[column],
            color="0.08",
            marker="o",
            markerfacecolor="white",
            ms=3.2,
            lw=1.05,
        )
        if column == "xmin":
            ax.axhline(0, color="0.55", ls="--", lw=0.8)
        ax.set_title(title, fontweight="semibold")
        ax.set_ylabel(ylabel)
        style(ax)
    for ax in axes[-1]:
        ax.set_xlabel("Year")
    save(fig, "income_statistics")


def plot_ccdf(curves, annual, years):
    annual_i = annual.set_index("year")

    def draw(ax, year):
        x_t = float(annual_i.loc[year, "transition_x_t"])
        data = curves[
            (curves.year == year)
            & (curves.income_normalized > 0)
            & (curves.empirical_ccdf_percent > 0)
        ]
        ax.plot(
            data.income_normalized,
            data.empirical_ccdf_percent,
            color="0.08",
            lw=1.05,
            label="Empirical CCDF",
        )
        ax.axvline(x_t, color="0.45", ls=":", lw=0.9, label=r"$x_t$")
        ax.set_xscale("log")
        ax.set_yscale("log")
        style(ax, True)
        annotation(ax, rf"$x_t={x_t:.3f}$")

    return family(
        years,
        "ccdf_loglog",
        draw,
        "Normalized individual income, $x$",
        "CCDF, $F(x)$ (%)",
        True,
        2,
    )


def plot_lorenz(lorenz, stats, years):
    stats_i = stats.set_index("year")

    def draw(ax, year):
        data = lorenz[lorenz.year == year]
        row = stats_i.loc[year]
        p_unit = data.population_share.to_numpy(float)
        l_unit = data.income_share.to_numpy(float)
        p = 100 * p_unit
        l_value = 100 * l_unit
        aulc = float(np.trapezoid(l_unit, p_unit))
        ax.fill_between(p, 0, l_value, color="0.95")
        ax.plot(p, l_value, color="0.08", lw=1.35, label="Lorenz curve")
        ax.plot([0, 100], [0, 100], color="0.50", ls="--", lw=0.9, label="Equality line")
        k = 100 * float(row["Kolkata"])
        q = 100 - k
        ax.plot([k, k], [0, q], color="0.35", ls=":", lw=0.85, label="Kolkata construction")
        ax.plot([0, k], [q, q], color="0.35", ls=":", lw=0.85)
        index = int(np.argmax(p - l_value))
        ax.plot(
            [p[index], p[index]],
            [l_value[index], p[index]],
            color="0.25",
            ls="-.",
            lw=0.85,
            label="Pietra construction",
        )
        ax.plot([], [], color="none", label="AULC = area under Lorenz curve")
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_aspect("equal")
        style(ax)
        text = "\n".join([
            f"Gini     = {float(row['Gini']):.3f}",
            f"Kolkata  = {k:.2f}%",
            f"Zanardi  = {float(row['Zanardi']):.3f}",
            f"Pietra   = {100.0 * float(row['Pietra']):.2f}%",
            f"AULC     = {aulc:.3f}",
        ])
        ax.text(
            0.04,
            0.96,
            text,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=6.6,
            fontfamily="monospace",
            linespacing=1.18,
            zorder=10,
            bbox=dict(
                boxstyle="round,pad=0.25",
                facecolor="white",
                edgecolor="0.55",
                alpha=0.94,
            ),
        )

    return family(
        years,
        "lorenz_geometry",
        draw,
        "Cumulative population (%)",
        "Cumulative income (%)",
        True,
        3,
    )


def plot_exponential(curves, fits, years):
    fits_i = fits.set_index("year")

    def draw(ax, year):
        fit = fits_i.loc[year]
        data = curves[
            (curves.year == year)
            & (curves.income_normalized <= fit.xg)
            & (curves.empirical_ccdf_percent > 0)
        ]
        x = data.income_normalized.to_numpy(float)
        transformed = np.log(data.empirical_ccdf_percent.to_numpy(float))
        ax.scatter(x, transformed, s=12, facecolors="white", edgecolors="0.15", label="Empirical")
        ax.plot(
            x,
            float(fit.intercept) - float(fit.alpha) * x,
            color="0.08",
            lw=1.1,
            label="Exponential fit",
        )
        style(ax)
        annotation(
            ax,
            rf"$\alpha={float(fit.alpha):.3f}$"
            + "\n"
            + rf"$R^2={float(fit.r2):.3f}$",
        )

    return family(
        years,
        "exponential_fit",
        draw,
        "Normalized individual income, $x$",
        r"$\ln F(x)$",
        True,
        2,
    )


def plot_gompertz(curves, annual, years):
    annual_i = annual.set_index("year")

    def draw(ax, year):
        fit = annual_i.loc[year]
        x_gmax = float(fit["gompertz_x_gmax"])
        data = curves[
            (curves.year == year)
            & (curves.income_normalized <= x_gmax)
            & curves.gompertz_transform.notna()
        ]
        x = data.income_normalized.to_numpy(float)
        transformed = data.gompertz_transform.to_numpy(float)
        ax.scatter(x, transformed, s=12, facecolors="white", edgecolors="0.20", label="Empirical transform")
        ax.plot(
            x,
            float(fit["gompertz_A"]) - float(fit["gompertz_B"]) * x,
            color="0.05",
            lw=1.25,
            label="Fixed-A Gompertz fit",
        )
        a_free = float(fit.get("gompertz_boundary_A_free", np.nan))
        b_free = float(fit.get("gompertz_boundary_B_free", np.nan))
        if np.isfinite(a_free) and np.isfinite(b_free):
            ax.plot(
                x,
                a_free - b_free * x,
                color="0.45",
                ls="--",
                lw=1.05,
                label="Free-intercept LSF",
            )
        style(ax)
        annotation(
            ax,
            rf"$A={float(fit['gompertz_A']):.3f}$"
            + "\n"
            + rf"$B={float(fit['gompertz_B']):.3f}\pm{float(fit['gompertz_B_bootstrap_se']):.3f}$"
            + "\n"
            + rf"$R^2={float(fit['gompertz_r2']):.3f}$",
        )

    return family(
        years,
        "gompertz_ls_fit",
        draw,
        "Normalized individual income, $x$",
        r"$\ln[\ln F(x)]$",
        True,
        3,
    )


def plot_pareto(curves, annual, years, method):
    annual_i = annual.set_index("year")

    def draw(ax, year):
        fit = annual_i.loc[year]
        x_t = float(fit["transition_x_t"])
        x_pmin = float(fit["pareto_x_pmin"])
        if method == "ls":
            fitted_column = "pareto_fitted_ccdf_percent_ls"
            alpha = float(fit["pareto_alpha_ls"])
            alpha_se = float(fit["pareto_alpha_ls_bootstrap_se"])
            beta = float(fit["pareto_beta_ls"])
            beta_se = float(fit["pareto_beta_ls_bootstrap_se"])
            r2 = float(fit["pareto_ls_r2"])
            xmin = min(x_t, x_pmin)
            label = "Pareto LSF"
            line_style = "--"
            alpha_label = r"\alpha_{\rm LS}"
            beta_label = r"\beta_{\rm LS}"
            r2_label = r"R^2_{\rm LS}"
        else:
            fitted_column = "pareto_fitted_ccdf_percent_mle"
            alpha = float(fit["pareto_alpha_mle"])
            alpha_se = float(fit["pareto_alpha_mle_bootstrap_se"])
            beta = float(fit["pareto_beta_mle_continuity"])
            beta_se = float(fit["pareto_beta_mle_bootstrap_se"])
            r2 = float(fit["pareto_mle_r2"])
            xmin = x_t
            label = "Pareto MLE"
            line_style = "-"
            alpha_label = r"\alpha_{\rm MLE}"
            beta_label = r"\beta_{\rm MLE}"
            r2_label = r"R^2_{\rm MLE}"

        data = curves[
            (curves.year == year)
            & (curves.income_normalized >= xmin)
            & (curves.empirical_ccdf_percent > 0)
        ]
        ax.scatter(
            data.income_normalized,
            data.empirical_ccdf_percent,
            s=12,
            facecolors="white",
            edgecolors="0.20",
            label="Empirical CCDF",
        )
        mask = np.isfinite(pd.to_numeric(data[fitted_column], errors="coerce"))
        ax.plot(
            data.loc[mask, "income_normalized"],
            data.loc[mask, fitted_column],
            color="0.05",
            ls=line_style,
            lw=1.2,
            label=label,
        )
        ax.axvline(x_t, color="0.50", ls=":", lw=0.9, label=r"$x_t$")
        ax.set_xscale("log")
        ax.set_yscale("log")
        style(ax, True)
        annotation(
            ax,
            rf"${alpha_label}={alpha:.3f}\pm{alpha_se:.3f}$"
            + "\n"
            + rf"${beta_label}={beta:.2e}\pm{beta_se:.2e}$"
            + "\n"
            + rf"${r2_label}={r2:.3f}$",
        )

    return family(
        years,
        "pareto_ls_fit" if method == "ls" else "pareto_mle_fit",
        draw,
        "Normalized individual income, $x$",
        "CCDF, $F(x)$ (%)",
        True,
        3,
    )


def line_figure(stats, stem, series, ylabel, scale=1.0):
    data = stats.sort_values("year")
    fig, ax = plt.subplots(figsize=SINGLE_SIZE)
    styles = ["-", "--", ":", "-."]
    markers = ["o", "s", "^", "D"]
    grays = ["0.05", "0.30", "0.50", "0.65"]
    for index, (column, label) in enumerate(series):
        ax.plot(
            data.year,
            scale * data[column],
            color=grays[index % 4],
            ls=styles[index % 4],
            marker=markers[index % 4],
            markerfacecolor="white",
            ms=3.2,
            lw=1.1,
            label=label,
        )
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    style(ax)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.13),
        ncol=min(4, len(series)),
        frameon=False,
    )
    save(fig, stem, 0.90)


def plot_inequality_grid(stats):
    data = stats.sort_values("year")
    fig, axes = plt.subplots(2, 2, figsize=(7, 6.6), sharex=True)
    specifications = [
        ("Gini", "Gini", 1),
        ("Zanardi", "Zanardi", 1),
        ("Kolkata", "Kolkata", 100),
        ("Pietra", "Pietra", 100),
    ]
    for ax, (column, title, scale) in zip(axes.ravel(), specifications):
        ax.plot(
            data.year,
            scale * data[column],
            color="0.08",
            marker="o",
            markerfacecolor="white",
            ms=3.2,
            lw=1.1,
        )
        ax.set_title(title)
        style(ax)
    save(fig, "inequality_indices_grid")


def plot_gini_validation(stats):
    data = stats.sort_values("year")
    fig, ax = plt.subplots(figsize=SINGLE_SIZE)
    ax.plot(
        data.year,
        data.Gini,
        color="0.05",
        lw=1.25,
        marker="o",
        markerfacecolor="white",
        ms=3.5,
        label="PNAD",
    )
    for column, label, line_style, gray in [
        ("IPEA", "IPEA", "--", "0.35"),
        ("Banco_Mundial", "World Bank", ":", "0.55"),
    ]:
        if column in data:
            valid = data.dropna(subset=[column])
            ax.plot(
                valid.year,
                valid[column],
                color=gray,
                ls=line_style,
                lw=1.05,
                label=label,
            )
    ax.set_xlabel("Year")
    ax.set_ylabel("Gini coefficient")
    style(ax)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.13),
        ncol=3,
        frameon=False,
    )
    save(fig, "gini_validation", 0.90)


def plot_top_combined(stats):
    data = stats.sort_values("year")
    fig, axes = plt.subplots(2, 1, figsize=(7, 7), sharex=True)
    axes[0].plot(data.year, data["mean"], color="0.08", label="Mean")
    axes[0].plot(data.year, data["median"], color="0.45", ls="--", label="Median")
    style(axes[0])
    axes[0].legend(frameon=False, ncol=2)
    for column, label, line_style, gray in [
        ("top_10", "Top 10%", "-", "0.08"),
        ("top_1", "Top 1%", "--", "0.35"),
        ("top_01", "Top 0.1%", ":", "0.55"),
    ]:
        axes[1].plot(
            data.year,
            100 * data[column],
            color=gray,
            ls=line_style,
            label=label,
        )
    style(axes[1])
    axes[1].legend(frameon=False, ncol=3)
    axes[1].set_xlabel("Year")
    save(fig, "top_income_shares_mean_median")


def plot_pareto_share(shares):
    fig, ax = plt.subplots(figsize=SINGLE_SIZE)
    ax.plot(
        shares.year,
        shares.pareto_income_share_pct,
        color="0.08",
        marker="o",
        markerfacecolor="white",
        lw=1.15,
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("Pareto share of total income (%)")
    style(ax)
    save(fig, "pareto_income_share")


def plot_gdp():
    data = pd.read_csv(GDP)
    data = data[(data.year >= START_YEAR) & (data.year <= END_YEAR)]
    fig, ax = plt.subplots(figsize=SINGLE_SIZE)
    ax.plot(
        data.year,
        data.gdp_growth_pct,
        color="0.08",
        marker="s",
        markerfacecolor="white",
        lw=1.1,
    )
    ax.axhline(0, color="0.45", ls="--", lw=0.8)
    ax.set_xlabel("Year")
    ax.set_ylabel("Real GDP growth (%)")
    style(ax)
    save(fig, "gdp_growth")

# --- Paper-table formatting features ---

TABLES_TRUSTED = ROOT / "assets" / "tables_analysis_trusted"

TABLES_PAPER = ROOT / "assets" / "tables_paper"

GDP_PATH = ROOT / "data" / "auxiliary" / "gdp_growth_brazil_1978_2025.csv"

GOMPERTZ_OUT = TABLES_PAPER / "table_01_gompertz_annual.csv"

PARETO_OUT = TABLES_PAPER / "table_02_pareto_annual.csv"

ECONOMIC_OUT = TABLES_PAPER / "table_03_economic_inequality_annual.csv"

METADATA_OUT = TABLES_PAPER / "table_04_metadata.csv"

CANONICAL_TABLES = {
    GOMPERTZ_OUT.name,
    PARETO_OUT.name,
    ECONOMIC_OUT.name,
    METADATA_OUT.name,
}

TABLE_DESCRIPTIONS = {
    GOMPERTZ_OUT.name: (
        "Annual Gompertz-regime estimates, including the canonical fixed-A fit "
        "and the unconstrained least-squares A/B diagnostic."
    ),
    PARETO_OUT.name: (
        "Annual Pareto-tail estimates from log-log least squares and direct "
        "maximum likelihood, including transition and uncertainty diagnostics."
    ),
    ECONOMIC_OUT.name: (
        "Annual income, inequality, external-validation, and top-income-band "
        "statistics used in the paper."
    ),
    METADATA_OUT.name: (
        "Data dictionary describing the canonical paper tables, their columns, "
        "units, and primary derivations."
    ),
}

COLUMN_DESCRIPTIONS = {
    "year": "Survey/reference year.",
    "gompertz_A": "Canonical Gompertz A fixed at ln[ln(100)].",
    "gompertz_B": "Canonical Gompertz B estimated by least squares with A fixed.",
    "gompertz_B_bootstrap_se": "Bootstrap standard error of canonical fixed-A Gompertz B.",
    "gompertz_boundary_A_free": "Gompertz A from the unconstrained least-squares fit used as a boundary/replication diagnostic.",
    "gompertz_A_free_bootstrap_se": "Bootstrap standard error of unconstrained Gompertz A.",
    "gompertz_boundary_B_free": "Gompertz B from the unconstrained least-squares fit used as a boundary/replication diagnostic.",
    "gompertz_B_free_bootstrap_se": "Bootstrap standard error of unconstrained Gompertz B.",
    "gompertz_x_gmax": "Upper normalized-income boundary of the selected Gompertz regime.",
    "transition_x_t": "Normalized-income transition threshold between Gompertz and Pareto regimes.",
    "transition_delta_x_t": "Half-width of the Gompertz-Pareto transition interval when the regime boundaries differ.",
    "gompertz_r2": "Coefficient of determination for the canonical Gompertz fit.",
    "gompertz_correlation_coefficient": "Correlation coefficient associated with the canonical Gompertz fit.",
    "gompertz_population_pct": "Percentage of observations assigned to the Gompertz regime.",
    "gompertz_income_share_pct": "Percentage of total income below the Gompertz-Pareto transition threshold.",
    "pareto_x_pmin": "Selected lower normalized-income boundary of the Pareto fit.",
    "pareto_selection_status": "Operational status returned by the Pareto-tail selection rule.",
    "pareto_supported": "Whether the selected Pareto tail satisfies the configured support criterion.",
    "pareto_alpha_ls": "Pareto exponent alpha estimated by log-log least squares.",
    "pareto_alpha_ls_bootstrap_se": "Bootstrap standard error of the least-squares Pareto alpha.",
    "pareto_beta_ls": "Pareto amplitude beta estimated by log-log least squares.",
    "pareto_beta_ls_bootstrap_se": "Bootstrap standard error of the least-squares Pareto beta.",
    "pareto_ls_r2": "Coefficient of determination for the log-log least-squares Pareto fit.",
    "pareto_ls_correlation_coefficient": "Correlation coefficient associated with the log-log Pareto fit.",
    "pareto_alpha_mle": "Pareto exponent alpha estimated by direct maximum likelihood above x_t.",
    "pareto_alpha_mle_fisher_se": "Fisher-information standard error of direct-MLE Pareto alpha.",
    "pareto_alpha_mle_likelihood_se": "Likelihood-width standard error of direct-MLE Pareto alpha following the 2009 prescription.",
    "pareto_alpha_mle_bootstrap_se": "Bootstrap standard error of direct-MLE Pareto alpha.",
    "pareto_beta_mle_continuity": "Pareto amplitude beta obtained by imposing Gompertz-Pareto continuity at x_t.",
    "pareto_beta_mle_likelihood_se": "Uncertainty propagated to continuity-based Pareto beta from the likelihood-width alpha error.",
    "pareto_beta_mle_bootstrap_se": "Bootstrap standard error of continuity-based Pareto beta.",
    "pareto_mle_r2": "Coefficient of determination for the direct-MLE Pareto curve against the empirical CCDF.",
    "pareto_mle_correlation_coefficient": "Correlation coefficient associated with the direct-MLE Pareto fit.",
    "pareto_population_pct": "Percentage of observations assigned to the Pareto regime.",
    "pareto_income_share_pct": "Percentage of total income at or above the Gompertz-Pareto transition threshold.",
    "bootstrap_reps": "Number of bootstrap replications.",
    "gdp_growth_pct": "Annual Brazilian real GDP growth rate.",
    "income_observation_n": "Number of positive trusted income observations used in the annual summary.",
    "income_mean_2025_usd": "Mean annual income converted to 2025 US dollars.",
    "income_median_2025_usd": "Median annual income converted to 2025 US dollars.",
    "income_std_2025_usd": "Standard deviation of annual income converted to 2025 US dollars.",
    "gini_pnad": "Gini coefficient estimated from the PNAD income sample.",
    "pietra_pnad": "Pietra inequality index estimated from the PNAD income sample.",
    "kolkata_pnad": "Kolkata inequality index estimated from the PNAD income sample.",
    "zanardi_pnad": "Zanardi inequality index estimated from the PNAD income sample.",
    "gini_ipea": "External annual Gini reference from IPEA when available.",
    "gini_world_bank": "External annual Gini reference from the World Bank when available.",
}

def _year_filter(frame):
    out = frame.copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    return out[(out["year"] >= START_YEAR) & (out["year"] <= END_YEAR)].copy()

def load_annual_fits():
    gompertz = _year_filter(pd.read_csv(TABLES_TRUSTED / "gompertz_annual.csv"))
    pareto = _year_filter(pd.read_csv(TABLES_TRUSTED / "pareto_annual.csv"))
    annual = gompertz.merge(
        pareto,
        on="year",
        how="inner",
        validate="one_to_one",
        suffixes=("", "_pareto"),
    )
    if "bootstrap_reps_pareto" in annual:
        if not np.array_equal(
            annual["bootstrap_reps"].to_numpy(),
            annual["bootstrap_reps_pareto"].to_numpy(),
        ):
            raise AssertionError("Gompertz and Pareto bootstrap replication counts differ")
        annual = annual.drop(columns=["bootstrap_reps_pareto"])
    return annual

def build_gompertz_table(annual):
    t = annual.copy()
    t["gompertz_correlation_coefficient"] = np.sqrt(
        np.clip(pd.to_numeric(t["gompertz_r2"], errors="coerce"), 0, 1)
    )
    columns = [
        "year",
        "gompertz_A",
        "gompertz_B",
        "gompertz_B_bootstrap_se",
        "gompertz_boundary_A_free",
        "gompertz_A_free_bootstrap_se",
        "gompertz_boundary_B_free",
        "gompertz_B_free_bootstrap_se",
        "gompertz_x_gmax",
        "transition_x_t",
        "gompertz_r2",
        "gompertz_correlation_coefficient",
        "gompertz_population_pct",
        "gompertz_income_share_pct",
        "bootstrap_reps",
    ]
    return t[columns].sort_values("year").reset_index(drop=True)

def build_pareto_table(annual):
    t = annual.copy()
    t["pareto_ls_correlation_coefficient"] = np.sqrt(
        np.clip(pd.to_numeric(t["pareto_ls_r2"], errors="coerce"), 0, 1)
    )
    t["pareto_mle_correlation_coefficient"] = np.sqrt(
        np.clip(pd.to_numeric(t["pareto_mle_r2"], errors="coerce"), 0, 1)
    )
    columns = [
        "year",
        "pareto_x_pmin",
        "transition_x_t",
        "transition_delta_x_t",
        "pareto_selection_status",
        "pareto_supported",
        "pareto_alpha_ls",
        "pareto_alpha_ls_bootstrap_se",
        "pareto_beta_ls",
        "pareto_beta_ls_bootstrap_se",
        "pareto_ls_r2",
        "pareto_ls_correlation_coefficient",
        "pareto_alpha_mle",
        "pareto_alpha_mle_fisher_se",
        "pareto_alpha_mle_likelihood_se",
        "pareto_alpha_mle_bootstrap_se",
        "pareto_beta_mle_continuity",
        "pareto_beta_mle_likelihood_se",
        "pareto_beta_mle_bootstrap_se",
        "pareto_mle_r2",
        "pareto_mle_correlation_coefficient",
        "pareto_population_pct",
        "pareto_income_share_pct",
        "bootstrap_reps",
    ]
    return t[columns].sort_values("year").reset_index(drop=True)

def _column_metadata(table_name, column):
    source = "Stage-05 consolidation"
    unit = "dimensionless"
    description = COLUMN_DESCRIPTIONS.get(
        column, column.replace("_", " ").capitalize() + "."
    )

    if column == "year":
        unit, source = "year", "PNAD / annual series"
    elif column == "pareto_selection_status":
        unit, source = "text", "Stage-03 analytical diagnostics"
    elif column == "pareto_supported":
        unit, source = "boolean", "Stage-03 analytical diagnostics"
    elif column.endswith("_pct"):
        unit = "%"
    elif column.endswith("_n") or column == "bootstrap_reps":
        unit = "count"
    elif "2025_usd" in column:
        unit = "2025 US$"
    elif column in {
        "gompertz_x_gmax",
        "pareto_x_pmin",
        "transition_x_t",
        "transition_delta_x_t",
    }:
        unit = "normalized income"
    elif "beta" in column:
        unit = "CCDF-percent scale"

    return description, unit, source

def build_metadata_table(tables):
    rows = []
    for table_name, frame in tables.items():
        table_description = TABLE_DESCRIPTIONS[table_name]
        for column in frame.columns:
            description, unit, source = _column_metadata(table_name, column)
            rows.append(
                {
                    "table_name": table_name,
                    "table_description": table_description,
                    "column_name": column,
                    "description": description,
                    "unit": unit,
                    "source": source,
                }
            )

    metadata_columns = {
        "table_name": "Canonical paper table containing the documented field.",
        "table_description": "Human-readable description of the table as a whole.",
        "column_name": "Column documented by this metadata row.",
        "description": "Human-readable definition of the column.",
        "unit": "Measurement unit or scale.",
        "source": "Primary source or derivation.",
    }
    for column, description in metadata_columns.items():
        rows.append(
            {
                "table_name": METADATA_OUT.name,
                "table_description": TABLE_DESCRIPTIONS[METADATA_OUT.name],
                "column_name": column,
                "description": description,
                "unit": "text",
                "source": "paper table schema",
            }
        )
    return pd.DataFrame(rows)

def validate_tables(gompertz, pareto, economic):
    merged = gompertz[["year", "gompertz_income_share_pct"]].merge(
        pareto[["year", "pareto_income_share_pct"]],
        on="year",
        validate="one_to_one",
    )
    if not np.allclose(
        merged["gompertz_income_share_pct"] + merged["pareto_income_share_pct"],
        100.0,
        atol=1e-8,
    ):
        raise AssertionError("Gompertz and Pareto income shares must sum to 100%")
    for frame in (gompertz, pareto, economic):
        if frame["year"].duplicated().any():
            raise AssertionError("Annual paper tables must have unique years")

def _clean_paper_csvs():
    TABLES_PAPER.mkdir(parents=True, exist_ok=True)
    for path in TABLES_PAPER.glob("*.csv"):
        path.unlink()

PAPER_ECONOMIC_COLUMNS = [
    "year", "gdp_growth_pct", "income_observation_n",
    "income_mean_2025_usd", "income_median_2025_usd", "income_std_2025_usd",
    "gini_pnad", "pietra_pnad", "kolkata_pnad", "zanardi_pnad",
    "gini_ipea", "gini_world_bank",
    "p90_p99_population_n", "p90_p99_income_share_pct",
    "p90_p99_mean_income_2025_usd", "p90_p99_median_income_2025_usd", "p90_p99_std_income_2025_usd",
    "p99_p999_population_n", "p99_p999_income_share_pct",
    "p99_p999_mean_income_2025_usd", "p99_p999_median_income_2025_usd", "p99_p999_std_income_2025_usd",
    "p999_p100_population_n", "p999_p100_income_share_pct",
    "p999_p100_mean_income_2025_usd", "p999_p100_median_income_2025_usd", "p999_p100_std_income_2025_usd",
]


def build_economic_table(stats):
    """Format persisted Stage-03 statistics as the paper economic table."""
    data = _year_filter(stats)
    gdp = _year_filter(pd.read_csv(GDP_PATH))[["year", "gdp_growth_pct"]]
    data = data.merge(gdp, on="year", how="left", validate="one_to_one")
    data = data.rename(columns={
        "Gini": "gini_pnad",
        "Pietra": "pietra_pnad",
        "Kolkata": "kolkata_pnad",
        "Zanardi": "zanardi_pnad",
        "IPEA": "gini_ipea",
        "Banco_Mundial": "gini_world_bank",
    })
    for column in PAPER_ECONOMIC_COLUMNS:
        if column not in data:
            data[column] = np.nan
    return data[PAPER_ECONOMIC_COLUMNS].sort_values("year").reset_index(drop=True)


def build_paper_tables():
    stats = _year_filter(pd.read_csv(TABLES_TRUSTED / "statistics_annual.csv"))
    annual = load_annual_fits()
    economic = build_economic_table(stats)
    gompertz = build_gompertz_table(annual)
    pareto = build_pareto_table(annual)
    validate_tables(gompertz, pareto, economic)
    metadata_table = build_metadata_table({
        GOMPERTZ_OUT.name: gompertz,
        PARETO_OUT.name: pareto,
        ECONOMIC_OUT.name: economic,
    })
    _clean_paper_csvs()
    outputs = (
        (GOMPERTZ_OUT, gompertz),
        (PARETO_OUT, pareto),
        (ECONOMIC_OUT, economic),
        (METADATA_OUT, metadata_table),
    )
    for path, frame in outputs:
        frame.to_csv(path, index=False)
    generated = {path.name for path in TABLES_PAPER.glob("*.csv")}
    if generated != CANONICAL_TABLES:
        raise AssertionError(f"Unexpected paper tables: {sorted(generated)}")
    return {path.name: frame for path, frame in outputs}


def main():
    """Generate publication figures and tables from persisted Stage-03 results."""
    PAPER_TABLES.mkdir(parents=True, exist_ok=True)
    clean_figures()
    stats, lorenz, annual, curves, meta = load_inputs()
    years = years_of(annual["year"].dropna())
    exponential = annual[[
        "year", "exponential_intercept", "exponential_alpha",
        "exponential_r2", "gompertz_x_gmax",
    ]].rename(columns={
        "exponential_intercept": "intercept",
        "exponential_alpha": "alpha",
        "exponential_r2": "r2",
        "gompertz_x_gmax": "xg",
    })
    shares = annual[["year", "gompertz_income_share_pct", "pareto_income_share_pct"]].copy()

    plot_histograms(years, meta)
    plot_income_statistics(stats, years, meta)
    plot_ccdf(curves, annual, years)
    plot_lorenz(lorenz, stats, years)
    line_figure(stats, "gini", [("Gini", "Gini")], "Gini coefficient")
    plot_exponential(curves, exponential, years)
    plot_gompertz(curves, annual, years)
    plot_pareto(curves, annual, years, "ls")
    plot_pareto(curves, annual, years, "mle")
    line_figure(stats, "top_income_shares", [("top_10", "Top 10%"), ("top_1", "Top 1%"), ("top_01", "Top 0.1%")], "Share of total income (%)", 100)
    exclusive = stats.copy()
    exclusive["p90_p99"] = exclusive.top_10 - exclusive.top_1
    exclusive["p99_p999"] = exclusive.top_1 - exclusive.top_01
    exclusive["p999_p100"] = exclusive.top_01
    line_figure(exclusive, "top_income_exclusive_shares", [("p90_p99", "90-99%"), ("p99_p999", "99-99.9%"), ("p999_p100", "99.9-100%")], "Share of total income (%)", 100)
    plot_top_combined(stats)
    line_figure(stats, "inequality_indices", [("Gini", "Gini"), ("Pietra", "Pietra"), ("Kolkata", "Kolkata"), ("Zanardi", "Zanardi")], "Inequality index")
    plot_inequality_grid(stats)
    plot_gini_validation(stats)
    plot_pareto_share(shares)
    plot_gdp()
    generated = build_paper_tables()
    print(f"Stage 05 publication assets generated for {len(years)} survey years.")
    return generated


if __name__ == "__main__":
    main()
