"""Stage 05: presentation-only figures and paper tables from Stage-03 outputs."""

from pathlib import Path
import math

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from cycler import cycler
from matplotlib.ticker import LogFormatterMathtext, LogLocator, NullFormatter

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "assets" / "tables_analysis_trusted"
FIGURES = ROOT / "assets" / "figures_paper"
TABLES_PAPER = ROOT / "assets" / "tables_paper"
TRUSTED = ROOT / "data" / "trusted"
METADATA = ROOT / "data" / "metadata" / "df_metadata.xlsx"
GDP = ROOT / "data" / "auxiliary" / "gdp_growth_brazil_1978_2025.csv"

START_YEAR, END_YEAR, MAX_PANELS, DPI = 1978, 2025, 12, 300
PAGE_SIZE, SINGLE_SIZE = (7.0, 9.5), (7.0, 4.5)

GOMPERTZ_OUT = TABLES_PAPER / "table_01_gompertz_annual.csv"
PARETO_OUT = TABLES_PAPER / "table_02_pareto_annual.csv"
ECONOMIC_OUT = TABLES_PAPER / "table_03_economic_inequality_annual.csv"
METADATA_OUT = TABLES_PAPER / "table_04_metadata.csv"
CANONICAL_TABLES = {
    p.name for p in (GOMPERTZ_OUT, PARETO_OUT, ECONOMIC_OUT, METADATA_OUT)
}

# Publication template: grayscale only. Series are distinguished by line style
# and marker geometry, never by chromatic color.
MONOCHROME_COLORS = ("0.05", "0.30", "0.50", "0.68")
LINE_STYLES = ("-", "--", ":", "-.")
MARKERS = ("o", "s", "^", "D")

mpl.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 8.5,
        "axes.titlesize": 9.0,
        "axes.labelsize": 9.0,
        "axes.edgecolor": "0.20",
        "axes.labelcolor": "0.10",
        "axes.linewidth": 0.70,
        "axes.prop_cycle": cycler(color=MONOCHROME_COLORS),
        "xtick.labelsize": 7.0,
        "ytick.labelsize": 7.0,
        "xtick.color": "0.15",
        "ytick.color": "0.15",
        "xtick.direction": "out",
        "ytick.direction": "out",
        "legend.fontsize": 7.0,
        "legend.frameon": False,
        "text.color": "0.10",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.edgecolor": "white",
    }
)


def years_of(values):
    return sorted(int(y) for y in values if START_YEAR <= int(y) <= END_YEAR)


def groups(years):
    years = list(years)
    return [years[i : i + MAX_PANELS] for i in range(0, len(years), MAX_PANELS)]


def grid(n):
    if n > MAX_PANELS:
        raise ValueError(f"At most {MAX_PANELS} panels are allowed per image.")
    return plt.subplots(min(4, math.ceil(n / 3)), 3, figsize=PAGE_SIZE, squeeze=False)


def series_style(index, linewidth=1.10):
    i = index % len(MONOCHROME_COLORS)
    color = MONOCHROME_COLORS[i]
    return {
        "color": color,
        "ls": LINE_STYLES[i],
        "marker": MARKERS[i],
        "markerfacecolor": "white",
        "markeredgecolor": color,
        "markeredgewidth": 0.75,
        "ms": 3.2,
        "lw": linewidth,
    }


def scatter_style(edge="0.18", size=10):
    return {
        "s": size,
        "facecolors": "white",
        "edgecolors": edge,
        "linewidths": 0.55,
        "zorder": 3,
    }


def style(ax, log=False):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("0.20")
    ax.spines["bottom"].set_color("0.20")
    ax.tick_params(which="major", width=0.65, length=3.0)
    ax.tick_params(which="minor", width=0.45, length=2.0)
    ax.grid(True, which="major", color="0.88", lw=0.45, zorder=0)
    if log:
        ax.grid(True, which="minor", color="0.95", lw=0.30, zorder=0)
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(LogLocator(base=10, numticks=6))
            axis.set_major_formatter(LogFormatterMathtext(base=10, labelOnlyBase=True))
            axis.set_minor_locator(
                LogLocator(base=10, subs=np.arange(2, 10) * 0.1, numticks=100)
            )
            axis.set_minor_formatter(NullFormatter())


def annotation(ax, text, x=0.05, y=0.06):
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=6.6,
        bbox={
            "boxstyle": "round,pad=0.22",
            "facecolor": "white",
            "edgecolor": "0.65",
            "linewidth": 0.5,
            "alpha": 0.96,
        },
    )


def save(fig, stem, top=0.985):
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.025, 0.025, 0.995, top))
    fig.savefig(
        FIGURES / f"{stem}.png",
        dpi=DPI,
        pil_kwargs={"compress_level": 9},
    )
    plt.close(fig)


def clean_figures():
    FIGURES.mkdir(parents=True, exist_ok=True)
    for path in FIGURES.iterdir():
        if path.is_file() and path.suffix.lower() in {".png", ".svg", ".pdf"}:
            path.unlink()


def global_legend(fig, axes, used, ncol=3):
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
            bbox_to_anchor=(0.5, 0.985),
            ncol=min(ncol, len(handles)),
            handlelength=2.6,
            columnspacing=1.4,
        )


def family(years, stem, draw, xlabel, ylabel, legend=False, ncol=3):
    for part, block in enumerate(groups(years), 1):
        fig, axes = grid(len(block))
        for ax, year in zip(axes.ravel(), block):
            draw(ax, year)
            ax.set_title(str(year), fontweight="semibold")
        for ax in axes.ravel()[len(block) :]:
            ax.remove()
        fig.supxlabel(xlabel, fontsize=9.3, y=0.006)
        fig.supylabel(ylabel, fontsize=9.3, x=0.006)
        if legend:
            global_legend(fig, axes, len(block), ncol=ncol)
        save(fig, f"{stem}_part_{part:02d}", top=0.925 if legend else 0.985)


def _year_filter(df):
    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df[(df.year >= START_YEAR) & (df.year <= END_YEAR)].copy()


def load_inputs():
    stats = _year_filter(pd.read_csv(TABLES / "statistics_annual.csv"))
    lorenz = _year_filter(pd.read_csv(TABLES / "lorenz.csv"))
    g = _year_filter(pd.read_csv(TABLES / "gompertz_annual.csv"))
    p = _year_filter(pd.read_csv(TABLES / "pareto_annual.csv"))
    curves = _year_filter(pd.read_csv(TABLES / "gompertz_pareto_curves.csv"))
    meta = _year_filter(
        pd.read_excel(METADATA).rename(columns={"ano": "year", "Exchange": "exchange"})
    )
    annual = g.merge(p, on="year", validate="one_to_one", suffixes=("", "_pareto"))
    if "bootstrap_reps_pareto" in annual:
        if not np.array_equal(annual.bootstrap_reps, annual.bootstrap_reps_pareto):
            raise AssertionError("Bootstrap replication counts differ")
        annual = annual.drop(columns="bootstrap_reps_pareto")
    return stats, lorenz, annual, curves, meta


def income(year, positive=True):
    x = pd.to_numeric(
        pd.read_parquet(
            TRUSTED / f"pnad_trusted_{year}.parquet", columns=["renda"]
        )["renda"],
        errors="coerce",
    ).to_numpy(float)
    x = x[np.isfinite(x)]
    return x[x > 0] if positive else x


def line_figure(df, stem, series, ylabel, scale=1.0):
    data = df.sort_values("year")
    fig, ax = plt.subplots(figsize=SINGLE_SIZE)
    for index, (column, label) in enumerate(series):
        ax.plot(
            data.year,
            scale * data[column],
            label=label,
            **series_style(index),
        )
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    style(ax)
    if len(series) > 1:
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, 1.13),
            ncol=min(4, len(series)),
            handlelength=2.5,
        )
        save(fig, stem, top=0.90)
    else:
        save(fig, stem)


def plot_histograms(years):
    def draw(ax, year):
        x = income(year, False)
        x = x[x >= 0]
        counts, edges = np.histogram(x, bins=100)
        ax.bar(
            edges[:-1],
            counts,
            width=np.diff(edges),
            align="edge",
            facecolor="white",
            edgecolor="0.12",
            lw=0.35,
            zorder=2,
        )
        ax.set_yscale("log")
        style(ax)

    family(years, "histograms", draw, "Income", "Frequency (log)")


def plot_ccdf(curves, annual, years):
    fit = annual.set_index("year")

    def draw(ax, year):
        data = curves[
            (curves.year == year)
            & (curves.income_normalized > 0)
            & (curves.empirical_ccdf_percent > 0)
        ]
        x_t = float(fit.loc[year, "transition_x_t"])
        ax.plot(
            data.income_normalized,
            data.empirical_ccdf_percent,
            color="0.05",
            lw=1.15,
            label="Empirical CCDF",
        )
        ax.axvline(x_t, color="0.52", ls=":", lw=0.9, label=r"$x_t$")
        ax.set_xscale("log")
        ax.set_yscale("log")
        style(ax, True)
        annotation(ax, rf"$x_t={x_t:.3f}$")

    family(
        years,
        "ccdf_loglog",
        draw,
        "Normalized income",
        "CCDF (%)",
        legend=True,
        ncol=2,
    )


def plot_lorenz(lorenz, years):
    def draw(ax, year):
        data = lorenz[lorenz.year == year]
        population = 100 * data.population_share
        income_share = 100 * data.income_share
        ax.fill_between(population, 0, income_share, color="0.965", zorder=0)
        ax.plot(
            population,
            income_share,
            color="0.05",
            lw=1.30,
            label="Lorenz curve",
        )
        ax.plot(
            [0, 100],
            [0, 100],
            color="0.50",
            ls="--",
            lw=0.95,
            label="Equality line",
        )
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        style(ax)

    family(
        years,
        "lorenz_geometry",
        draw,
        "Cumulative population (%)",
        "Cumulative income (%)",
        legend=True,
        ncol=2,
    )


def plot_model_families(curves, annual, years):
    fit = annual.set_index("year")

    def exp(ax, year):
        row = fit.loc[year]
        data = curves[
            (curves.year == year)
            & (curves.income_normalized <= row.gompertz_x_gmax)
            & (curves.empirical_ccdf_percent > 0)
        ]
        x = data.income_normalized.to_numpy(float)
        ax.scatter(x, np.log(data.empirical_ccdf_percent), label="Empirical", **scatter_style())
        ax.plot(
            x,
            row.exponential_intercept - row.exponential_alpha * x,
            color="0.05",
            lw=1.15,
            label="Exponential fit",
        )
        style(ax)

    def gom(ax, year):
        row = fit.loc[year]
        data = curves[
            (curves.year == year)
            & (curves.income_normalized <= row.gompertz_x_gmax)
            & curves.gompertz_transform.notna()
        ]
        x = data.income_normalized.to_numpy(float)
        ax.scatter(
            x,
            data.gompertz_transform,
            label="Empirical transform",
            **scatter_style(),
        )
        ax.plot(
            x,
            row.gompertz_A - row.gompertz_B * x,
            color="0.05",
            lw=1.20,
            label="Fixed-A Gompertz",
        )
        ax.plot(
            x,
            row.gompertz_boundary_A_free - row.gompertz_boundary_B_free * x,
            color="0.48",
            ls="--",
            lw=1.05,
            label="Free-intercept LSF",
        )
        style(ax)

    family(
        years,
        "exponential_fit",
        exp,
        "Normalized income",
        r"$\ln F(x)$",
        legend=True,
        ncol=2,
    )
    family(
        years,
        "gompertz_ls_fit",
        gom,
        "Normalized income",
        r"$\ln[\ln F(x)]$",
        legend=True,
        ncol=3,
    )

    for method in ("ls", "mle"):
        def draw(ax, year, method=method):
            row = fit.loc[year]
            column = f"pareto_fitted_ccdf_percent_{method}"
            xmin = (
                min(row.transition_x_t, row.pareto_x_pmin)
                if method == "ls"
                else row.transition_x_t
            )
            data = curves[
                (curves.year == year)
                & (curves.income_normalized >= xmin)
                & (curves.empirical_ccdf_percent > 0)
            ]
            ax.scatter(
                data.income_normalized,
                data.empirical_ccdf_percent,
                label="Empirical CCDF",
                **scatter_style(),
            )
            ax.plot(
                data.income_normalized,
                data[column],
                color="0.05",
                ls="--" if method == "ls" else "-",
                lw=1.20,
                label="Pareto LSF" if method == "ls" else "Pareto MLE",
            )
            ax.axvline(
                float(row.transition_x_t),
                color="0.52",
                ls=":",
                lw=0.9,
                label=r"$x_t$",
            )
            ax.set_xscale("log")
            ax.set_yscale("log")
            style(ax, True)

        family(
            years,
            f"pareto_{method}_fit",
            draw,
            "Normalized income",
            "CCDF (%)",
            legend=True,
            ncol=3,
        )


def plot_income_stats(stats):
    line_figure(
        stats,
        "income_statistics",
        [("mean", "Mean"), ("median", "Median"), ("std", "Std")],
        "2025 US$",
    )


def plot_misc(stats, annual):
    line_figure(stats, "gini", [("Gini", "Gini")], "Gini coefficient")
    line_figure(
        stats,
        "top_income_shares",
        [("top_10", "Top 10%"), ("top_1", "Top 1%"), ("top_01", "Top 0.1%")],
        "Income share (%)",
        100,
    )
    exclusive = stats.assign(
        p90_p99=stats.top_10 - stats.top_1,
        p99_p999=stats.top_1 - stats.top_01,
        p999_p100=stats.top_01,
    )
    line_figure(
        exclusive,
        "top_income_exclusive_shares",
        [
            ("p90_p99", "90-99%"),
            ("p99_p999", "99-99.9%"),
            ("p999_p100", "99.9-100%"),
        ],
        "Income share (%)",
        100,
    )
    line_figure(
        stats,
        "inequality_indices",
        [("Gini", "Gini"), ("Pietra", "Pietra"), ("Kolkata", "Kolkata"), ("Zanardi", "Zanardi")],
        "Index",
    )
    line_figure(
        annual,
        "pareto_income_share",
        [("pareto_income_share_pct", "Pareto")],
        "Income share (%)",
    )
    line_figure(
        stats,
        "top_income_shares_mean_median",
        [("mean", "Mean"), ("median", "Median")],
        "2025 US$",
    )

    fig, axes = plt.subplots(2, 2, figsize=(7, 6.2), sharex=True)
    for ax, (column, scale) in zip(
        axes.ravel(),
        [("Gini", 1), ("Zanardi", 1), ("Kolkata", 100), ("Pietra", 100)],
    ):
        ax.plot(stats.year, scale * stats[column], **series_style(0))
        ax.set_title(column, fontweight="semibold")
        style(ax)
    for ax in axes[-1]:
        ax.set_xlabel("Year")
    save(fig, "inequality_indices_grid")

    # Reindex only the plotting copy. Missing survey/reference years remain NaN,
    # which makes Matplotlib break the lines instead of visually interpolating
    # across years with no observation. The underlying Stage-03 tables are unchanged.
    full_years = pd.Index(range(START_YEAR, END_YEAR + 1), name="year")
    gini_validation = (
        stats.set_index("year")
        .reindex(full_years)
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=SINGLE_SIZE)
    ax.plot(
        gini_validation.year,
        gini_validation.Gini,
        label="PNAD",
        color="0.05",
        lw=1.25,
        marker="o",
        markerfacecolor="white",
        markeredgecolor="0.05",
        ms=3.3,
    )
    for column, label, line_style, gray in [
        ("IPEA", "IPEA", "--", "0.35"),
        ("Banco_Mundial", "World Bank", ":", "0.58"),
    ]:
        ax.plot(
            gini_validation.year,
            gini_validation[column],
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
        handlelength=2.5,
    )
    save(fig, "gini_validation", top=0.90)

    gdp = _year_filter(pd.read_csv(GDP))
    line_figure(
        gdp,
        "gdp_growth",
        [("gdp_growth_pct", "GDP")],
        "Real GDP growth (%)",
    )


TABLE_DESCRIPTIONS = {
    GOMPERTZ_OUT.name: "Annual Gompertz estimates and free-A/B diagnostics.",
    PARETO_OUT.name: "Annual Pareto LS/MLE estimates and uncertainties.",
    ECONOMIC_OUT.name: "Annual income and inequality statistics.",
    METADATA_OUT.name: "Data dictionary for paper tables.",
}


def build_gompertz_table(a):
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
        "gompertz_population_pct",
        "gompertz_income_share_pct",
        "bootstrap_reps",
    ]
    return a[columns].sort_values("year").reset_index(drop=True)


def build_pareto_table(a):
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
        "pareto_alpha_mle",
        "pareto_alpha_mle_fisher_se",
        "pareto_alpha_mle_likelihood_se",
        "pareto_alpha_mle_bootstrap_se",
        "pareto_beta_mle_continuity",
        "pareto_beta_mle_likelihood_se",
        "pareto_beta_mle_bootstrap_se",
        "pareto_mle_r2",
        "pareto_population_pct",
        "pareto_income_share_pct",
        "bootstrap_reps",
    ]
    return a[columns].sort_values("year").reset_index(drop=True)


PAPER_ECONOMIC_COLUMNS = [
    "year",
    "gdp_growth_pct",
    "income_observation_n",
    "income_mean_2025_usd",
    "income_median_2025_usd",
    "income_std_2025_usd",
    "gini_pnad",
    "pietra_pnad",
    "kolkata_pnad",
    "zanardi_pnad",
    "gini_ipea",
    "gini_world_bank",
    "p90_p99_population_n",
    "p90_p99_income_share_pct",
    "p90_p99_mean_income_2025_usd",
    "p90_p99_median_income_2025_usd",
    "p90_p99_std_income_2025_usd",
    "p99_p999_population_n",
    "p99_p999_income_share_pct",
    "p99_p999_mean_income_2025_usd",
    "p99_p999_median_income_2025_usd",
    "p99_p999_std_income_2025_usd",
    "p999_p100_population_n",
    "p999_p100_income_share_pct",
    "p999_p100_mean_income_2025_usd",
    "p999_p100_median_income_2025_usd",
    "p999_p100_std_income_2025_usd",
]


def build_economic_table(stats):
    data = _year_filter(stats).merge(
        _year_filter(pd.read_csv(GDP))[["year", "gdp_growth_pct"]],
        on="year",
        how="left",
        validate="one_to_one",
    ).rename(
        columns={
            "Gini": "gini_pnad",
            "Pietra": "pietra_pnad",
            "Kolkata": "kolkata_pnad",
            "Zanardi": "zanardi_pnad",
            "IPEA": "gini_ipea",
            "Banco_Mundial": "gini_world_bank",
        }
    )
    for column in PAPER_ECONOMIC_COLUMNS:
        if column not in data:
            data[column] = np.nan
    return data[PAPER_ECONOMIC_COLUMNS].sort_values("year").reset_index(drop=True)


def _meta(table, column):
    unit = "dimensionless"
    if column == "year":
        unit = "year"
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
    elif column == "pareto_selection_status":
        unit = "text"
    elif column == "pareto_supported":
        unit = "boolean"
    return {
        "table_name": table,
        "table_description": TABLE_DESCRIPTIONS[table],
        "column_name": column,
        "description": column.replace("_", " ").capitalize() + ".",
        "unit": unit,
        "source": "Stage 03 / Stage 05 consolidation",
    }


def build_metadata_table(tables):
    rows = [_meta(table, column) for table, frame in tables.items() for column in frame.columns]
    for column in (
        "table_name",
        "table_description",
        "column_name",
        "description",
        "unit",
        "source",
    ):
        rows.append(
            {
                "table_name": METADATA_OUT.name,
                "table_description": TABLE_DESCRIPTIONS[METADATA_OUT.name],
                "column_name": column,
                "description": f"Metadata field {column}.",
                "unit": "text",
                "source": "paper table schema",
            }
        )
    return pd.DataFrame(rows)


def validate_tables(g, p, e):
    merged = g[["year", "gompertz_income_share_pct"]].merge(
        p[["year", "pareto_income_share_pct"]], on="year", validate="one_to_one"
    )
    if not np.allclose(
        merged.gompertz_income_share_pct + merged.pareto_income_share_pct,
        100.0,
        atol=1e-8,
    ):
        raise AssertionError("Gompertz and Pareto income shares must sum to 100%")
    if any(frame.year.duplicated().any() for frame in (g, p, e)):
        raise AssertionError("Annual paper tables must have unique years")


def build_paper_tables(stats=None, annual=None):
    if stats is None or annual is None:
        stats, _, annual, _, _ = load_inputs()
    g = build_gompertz_table(annual)
    p = build_pareto_table(annual)
    e = build_economic_table(stats)
    validate_tables(g, p, e)
    metadata = build_metadata_table(
        {GOMPERTZ_OUT.name: g, PARETO_OUT.name: p, ECONOMIC_OUT.name: e}
    )
    TABLES_PAPER.mkdir(parents=True, exist_ok=True)
    for path in TABLES_PAPER.glob("*.csv"):
        path.unlink()
    for path, frame in (
        (GOMPERTZ_OUT, g),
        (PARETO_OUT, p),
        (ECONOMIC_OUT, e),
        (METADATA_OUT, metadata),
    ):
        frame.to_csv(path, index=False)
    if {path.name for path in TABLES_PAPER.glob("*.csv")} != CANONICAL_TABLES:
        raise AssertionError("Unexpected paper table set")
    return {
        GOMPERTZ_OUT.name: g,
        PARETO_OUT.name: p,
        ECONOMIC_OUT.name: e,
        METADATA_OUT.name: metadata,
    }


def main():
    clean_figures()
    stats, lorenz, annual, curves, meta = load_inputs()
    years = years_of(annual.year.dropna())
    plot_histograms(years)
    plot_income_stats(stats)
    plot_ccdf(curves, annual, years)
    plot_lorenz(lorenz, years)
    plot_model_families(curves, annual, years)
    plot_misc(stats, annual)
    out = build_paper_tables(stats, annual)
    print(f"Stage 05 publication assets generated for {len(years)} survey years.")
    return out


if __name__ == "__main__":
    main()
