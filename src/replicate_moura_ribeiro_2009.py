"""Reproduce Moura Jr. & Ribeiro (2009) from existing refined PNAD assets.

This module is deliberately downstream of the main PNAD pipeline. It does not
re-estimate the Gompertz--Pareto regime parameters already produced by
``stage_03_pnad_analysis.py``. Instead it consumes the refined analytical CSVs
and annual refined Parquet files to compose the four paper tables, the fifteen
paper-equivalent figures, the missing lower-region exponential diagnostic, and
the mutually exclusive income-share decomposition requested for the
1978--2025 extension.

Ground truth:
    N. J. Moura Jr. and M. B. Ribeiro, Eur. Phys. J. B 67, 101--120 (2009).
    DOI: 10.1140/epjb/e2008-00469-1
    arXiv:0812.2664
"""

from __future__ import annotations

import json
import math
import warnings
from pathlib import Path
from urllib.request import urlopen

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
REFINED_DATA_DIR = REPO_ROOT / "data" / "refined"
METADATA_PATH = REPO_ROOT / "data" / "metadata" / "df_metadata.xlsx"
TABLES_ANALYSIS_DIR = REPO_ROOT / "assets" / "tables_analysis_refined"
TABLES_PAPER_DIR = REPO_ROOT / "assets" / "tables_paper"
FIGURES_PAPER_DIR = REPO_ROOT / "assets" / "figures_paper"
GDP_PATH = (
    REPO_ROOT
    / "data"
    / "auxiliary"
    / "brazil_real_gdp_growth_bcb_sgs_7326_1978_2025.csv"
)

STATS_PATH = TABLES_ANALYSIS_DIR / "refined_analysis_statistics_annual.csv"
CCDF_PATH = TABLES_ANALYSIS_DIR / "refined_analysis_ccdf_empirical.csv"
LORENZ_PATH = TABLES_ANALYSIS_DIR / "refined_analysis_lorenz.csv"
REGIME_FITS_PATH = (
    TABLES_ANALYSIS_DIR / "refined_analysis_gompertz_pareto_annual.csv"
)
REGIME_CURVES_PATH = TABLES_ANALYSIS_DIR / "refined_analysis_regime_curves.csv"

START_YEAR = 1978
END_YEAR = 2025
ORIGINAL_SPLIT_YEAR = 1990
LOG_BIN_RATIO = 1.10
EXPONENTIAL_MIN_POINTS = 5

BCB_GDP_SERIES_ID = 7326
BCB_GDP_SERIES_NAME = "Produto Interno Bruto - Taxa de variacao real no ano"
BCB_GDP_API = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.7326/dados"
    "?formato=json&dataInicial=01/01/1978&dataFinal=31/12/2025"
)

TABLE_FILENAMES = {
    "table_01": "table_01_currency_mean_income_1978_2025.csv",
    "table_02": "table_02_gompertz_parameters_1978_2025.csv",
    "table_03": "table_03_pareto_parameters_1978_2025.csv",
    "table_04": "table_04_income_shares_gini_1978_2025.csv",
}

FIGURE_STEMS = {
    1: "figure_01_ccdf_part_1_1978_2025",
    2: "figure_02_ccdf_part_2_1978_2025",
    3: "figure_03_lorenz_part_1_1978_2025",
    4: "figure_04_lorenz_part_2_1978_2025",
    5: "figure_05_gini_1978_2025",
    6: "figure_06_exponential_part_1_1978_2025",
    7: "figure_07_exponential_part_2_1978_2025",
    8: "figure_08_gompertz_linearization_part_1_1978_2025",
    9: "figure_09_gompertz_linearization_part_2_1978_2025",
    10: "figure_10_pareto_ls_part_1_1978_2025",
    11: "figure_11_pareto_ls_part_2_1978_2025",
    12: "figure_12_pareto_mle_part_1_1978_2025",
    13: "figure_13_pareto_mle_part_2_1978_2025",
    14: "figure_14_pareto_income_share_1978_2025",
    15: "figure_15_real_gdp_growth_1978_2025",
}

# Published central values used only by tests/diagnostics; the replication
# outputs themselves are always computed from the repository data.
PUBLISHED_TABLE_2 = pd.DataFrame(
    [
        (1978, 1.52, 0.46, 6.606, 98.9),
        (1979, 1.54, 0.44, 6.920, 98.9),
        (1981, 1.55, 0.34, 7.533, 98.9),
        (1982, 1.55, 0.34, 7.473, 98.9),
        (1983, 1.54, 0.33, 6.910, 98.7),
        (1984, 1.55, 0.33, 7.388, 98.9),
        (1985, 1.54, 0.33, 7.490, 98.9),
        (1986, 1.55, 0.34, 7.112, 98.8),
        (1987, 1.55, 0.34, 7.626, 98.9),
        (1988, 1.54, 0.32, 8.140, 98.9),
        (1989, 1.53, 0.32, 7.856, 98.8),
        (1990, 1.54, 0.34, 8.074, 98.9),
        (1992, 1.56, 0.36, 7.635, 99.0),
        (1993, 1.54, 0.33, 7.674, 98.8),
        (1995, 1.54, 0.33, 7.887, 98.9),
        (1996, 1.55, 0.35, 8.163, 99.0),
        (1997, 1.55, 0.34, 7.935, 99.0),
        (1998, 1.54, 0.33, 7.628, 98.8),
        (1999, 1.54, 0.33, 7.811, 98.9),
        (2001, 1.54, 0.34, 7.774, 98.9),
        (2002, 1.55, 0.34, 7.878, 99.0),
        (2003, 1.54, 0.33, 7.374, 98.8),
        (2004, 1.55, 0.34, 7.653, 98.9),
        (2005, 1.54, 0.33, 7.403, 98.8),
    ],
    columns=[
        "year",
        "published_A",
        "published_B",
        "published_x_gmax",
        "published_gompertz_population_pct",
    ],
)

PUBLISHED_TABLE_3 = pd.DataFrame(
    [
        (1978, 40.000, 23.300, 2.44, 2.94, 1.1),
        (1979, 40.000, 23.500, 3.09, 3.09, 1.1),
        (1981, 7.533, 7.533, 3.52, 2.84, 1.1),
        (1982, 7.473, 7.473, 2.53, 2.68, 1.1),
        (1983, 6.910, 6.910, 3.03, 2.64, 1.3),
        (1984, 7.388, 7.388, 3.50, 2.84, 1.1),
        (1985, 7.490, 7.490, 3.15, 2.66, 1.1),
        (1986, 7.112, 7.112, 2.11, 2.57, 1.2),
        (1987, 7.626, 7.626, 2.43, 2.72, 1.1),
        (1988, 8.140, 8.140, 3.06, 2.87, 1.1),
        (1989, 7.856, 7.856, 2.22, 2.78, 1.2),
        (1990, 8.074, 8.074, 2.27, 2.64, 1.1),
        (1992, 7.635, 7.635, 2.12, 2.64, 1.0),
        (1993, 7.674, 7.674, 2.41, 2.57, 1.2),
        (1995, 7.887, 7.887, 3.21, 2.78, 1.1),
        (1996, 8.163, 8.163, 3.20, 2.75, 1.0),
        (1997, 7.935, 7.935, 2.79, 2.62, 1.0),
        (1998, 7.628, 7.628, 2.94, 2.68, 1.2),
        (1999, 7.811, 7.811, 3.10, 2.78, 1.1),
        (2001, 7.774, 7.774, 3.23, 2.72, 1.1),
        (2002, 7.878, 7.878, 2.93, 2.78, 1.0),
        (2003, 7.374, 7.374, 3.18, 2.78, 1.2),
        (2004, 7.653, 7.653, 3.89, 3.10, 1.1),
        (2005, 7.403, 7.403, 2.59, 2.84, 1.2),
    ],
    columns=[
        "year",
        "published_x_pmin",
        "published_x_t",
        "published_alpha_ls",
        "published_alpha_mle",
        "published_pareto_population_pct",
    ],
)

PUBLISHED_TABLE_4_GINI = pd.DataFrame(
    [
        (1978, 0.739), (1979, 0.711), (1981, 0.574), (1982, 0.581),
        (1983, 0.584), (1984, 0.576), (1985, 0.589), (1986, 0.580),
        (1987, 0.592), (1988, 0.609), (1989, 0.628), (1990, 0.605),
        (1992, 0.578), (1993, 0.599), (1995, 0.596), (1996, 0.598),
        (1997, 0.598), (1998, 0.597), (1999, 0.590), (2001, 0.592),
        (2002, 0.586), (2003, 0.579), (2004, 0.577), (2005, 0.580),
    ],
    columns=["year", "published_gini"],
)


def _require_columns(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns.difference(frame.columns)
    if missing:
        raise ValueError(f"{name}: missing columns: {', '.join(sorted(missing))}")


def load_replication_inputs() -> dict[str, pd.DataFrame]:
    """Load only the refined assets already produced by the main pipeline."""
    stats = pd.read_csv(STATS_PATH)
    ccdf = pd.read_csv(CCDF_PATH)
    lorenz = pd.read_csv(LORENZ_PATH)
    fits = pd.read_csv(REGIME_FITS_PATH)
    curves = pd.read_csv(REGIME_CURVES_PATH)
    metadata = pd.read_excel(METADATA_PATH)

    _require_columns(stats, {"year", "mean_nominal", "Gini"}, "statistics")
    _require_columns(ccdf, {"year", "x", "ccdf", "ccdf_pct"}, "empirical CCDF")
    _require_columns(
        lorenz, {"year", "population_share", "income_share"}, "Lorenz"
    )
    _require_columns(
        fits,
        {
            "year",
            "log_bin_ratio",
            "gompertz_A",
            "gompertz_B",
            "gompertz_r2",
            "gompertz_x_gmax",
            "pareto_x_pmin",
            "transition_x_t",
            "transition_delta_x_t",
            "gompertz_population_pct",
            "pareto_population_pct",
            "pareto_alpha_ls",
            "pareto_beta_ls",
            "pareto_ls_r2",
            "pareto_alpha_mle",
            "pareto_beta_mle_continuity",
        },
        "Gompertz-Pareto annual fits",
    )
    _require_columns(
        curves,
        {
            "year",
            "income_normalized",
            "empirical_ccdf_percent",
            "gompertz_transform",
        },
        "regime curves",
    )
    _require_columns(metadata, {"ano", "Currency", "Exchange"}, "metadata")

    frames = {
        "stats": stats,
        "ccdf": ccdf,
        "lorenz": lorenz,
        "fits": fits,
        "curves": curves,
    }
    for key, frame in frames.items():
        frame["year"] = pd.to_numeric(frame["year"], errors="raise").astype(int)
        frames[key] = frame.loc[
            frame["year"].between(START_YEAR, END_YEAR)
        ].copy()

    metadata["ano"] = pd.to_numeric(metadata["ano"], errors="raise").astype(int)
    metadata = metadata.loc[
        metadata["ano"].between(START_YEAR, END_YEAR)
    ].copy()

    fits = frames["fits"].sort_values("year").reset_index(drop=True)
    if not np.allclose(
        fits["log_bin_ratio"].to_numpy(float),
        LOG_BIN_RATIO,
        rtol=0.0,
        atol=1.0e-12,
    ):
        raise AssertionError("Replication requires the paper's geometric ratio r=1.10.")

    expected_years = fits["year"].tolist()
    for key in ("stats", "ccdf", "lorenz", "curves"):
        available = sorted(frames[key]["year"].unique().tolist())
        if available != expected_years:
            raise AssertionError(
                f"{key} survey years do not match refined Gompertz-Pareto years."
            )

    return {**frames, "fits": fits, "metadata": metadata}


def load_refined_positive_income(year: int) -> np.ndarray:
    """Load positive finite refined income records for one survey year."""
    path = REFINED_DATA_DIR / f"pnad_refined_{int(year)}.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"Missing refined PNAD dataset: {path}")
    frame = pd.read_parquet(path, columns=["renda"])
    values = pd.to_numeric(frame["renda"], errors="coerce").to_numpy(float)
    values = values[np.isfinite(values) & (values > 0)]
    if values.size == 0:
        raise ValueError(f"{year}: no positive finite refined income values.")
    return values


def partition_income_shares(
    income: np.ndarray, transition_x_t: float
) -> tuple[float, float]:
    """Return mutually exclusive Gompertz/Pareto shares of total income."""
    x = np.asarray(income, dtype=float)
    x = x[np.isfinite(x) & (x > 0)]
    if x.size == 0:
        raise ValueError("Income-share decomposition requires positive income.")
    if not np.isfinite(transition_x_t) or transition_x_t <= 0:
        raise ValueError("transition_x_t must be positive and finite.")

    normalized = x / float(np.mean(x))
    total = float(np.sum(normalized))
    gompertz_share = float(
        np.sum(normalized[normalized < transition_x_t]) / total
    )
    pareto_share = float(
        np.sum(normalized[normalized >= transition_x_t]) / total
    )

    if not np.isclose(gompertz_share + pareto_share, 1.0, atol=1.0e-12):
        raise AssertionError("Gompertz and Pareto income shares must sum to one.")
    return gompertz_share, pareto_share


def build_income_share_table(
    fits: pd.DataFrame, stats: pd.DataFrame
) -> pd.DataFrame:
    """Compute the Table-4 decomposition missing from stage 03."""
    stats_index = stats.set_index("year")
    records: list[dict[str, float | int]] = []
    for row in fits.itertuples(index=False):
        year = int(row.year)
        income = load_refined_positive_income(year)
        share_g, share_p = partition_income_shares(
            income, float(row.transition_x_t)
        )
        records.append(
            {
                "year": year,
                "gompertz_income_share": share_g,
                "pareto_income_share": share_p,
                "gini": float(stats_index.loc[year, "Gini"]),
            }
        )
    return pd.DataFrame(records).sort_values("year").reset_index(drop=True)


def fit_exponential_lower_region(
    curve_year: pd.DataFrame, gompertz_x_gmax: float
) -> dict[str, float]:
    """Fit ln F = ln C - lambda*x over the same x<=x_G,max lower region.

    Figures 6-7 of Moura Jr. & Ribeiro deliberately include the very-low-income
    observations to show that a single exponential is inadequate. Their text
    notes that apparent linearity improves only after x<=2 is removed; that
    truncation is therefore not applied to this diagnostic fit.
    """
    data = curve_year.loc[
        (curve_year["income_normalized"] > 0)
        & (curve_year["income_normalized"] <= gompertz_x_gmax)
        & (curve_year["empirical_ccdf_percent"] > 0)
    ].copy()
    if "observations_in_bin" in data.columns:
        data = data.loc[data["observations_in_bin"] > 0]

    if len(data) < EXPONENTIAL_MIN_POINTS:
        raise ValueError("Insufficient points for lower-region exponential fit.")

    x = data["income_normalized"].to_numpy(float)
    y = np.log(data["empirical_ccdf_percent"].to_numpy(float))
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    residual = y - fitted
    sse = float(np.sum(residual**2))
    tss = float(np.sum((y - np.mean(y)) ** 2))
    r2 = np.nan if tss == 0.0 else float(1.0 - sse / tss)

    return {
        "C": float(np.exp(intercept)),
        "lambda": float(-slope),
        "r2": r2,
        "sse": sse,
    }


def build_table_01(
    stats: pd.DataFrame, metadata: pd.DataFrame, years: list[int]
) -> pd.DataFrame:
    """Reproduce Table 1 using current project metadata and nominal means."""
    meta = metadata.rename(columns={"ano": "year"})
    result = (
        pd.DataFrame({"year": years})
        .merge(meta[["year", "Currency", "Exchange"]], on="year", how="left")
        .merge(stats[["year", "mean_nominal"]], on="year", how="left")
    )
    result = result.rename(
        columns={
            "Currency": "currency",
            "Exchange": "exchange_rate_local_currency_per_usd",
        }
    )
    result["mean_income_usd"] = (
        result["mean_nominal"]
        / result["exchange_rate_local_currency_per_usd"]
    )
    result = result[
        [
            "year",
            "currency",
            "exchange_rate_local_currency_per_usd",
            "mean_income_usd",
        ]
    ]
    if result.isna().any().any():
        missing = result.loc[result.isna().any(axis=1), "year"].tolist()
        raise ValueError(f"Table 1 has missing metadata for survey years: {missing}")
    return result


def build_table_02(fits: pd.DataFrame) -> pd.DataFrame:
    return (
        fits[
            [
                "year",
                "gompertz_A",
                "gompertz_B",
                "gompertz_x_gmax",
                "gompertz_r2",
                "gompertz_population_pct",
            ]
        ]
        .rename(
            columns={
                "gompertz_A": "A",
                "gompertz_B": "B",
                "gompertz_x_gmax": "x_G_max",
                "gompertz_r2": "R2",
                "gompertz_population_pct": "gompertz_population_pct",
            }
        )
        .reset_index(drop=True)
    )


def build_table_03(fits: pd.DataFrame) -> pd.DataFrame:
    return (
        fits[
            [
                "year",
                "pareto_x_pmin",
                "transition_x_t",
                "transition_delta_x_t",
                "pareto_alpha_ls",
                "pareto_beta_ls",
                "pareto_alpha_mle",
                "pareto_beta_mle_continuity",
                "pareto_ls_r2",
                "pareto_population_pct",
            ]
        ]
        .rename(
            columns={
                "pareto_x_pmin": "x_P_min",
                "transition_x_t": "x_t",
                "transition_delta_x_t": "delta_x_t",
                "pareto_alpha_ls": "alpha_LS",
                "pareto_beta_ls": "beta_LS",
                "pareto_alpha_mle": "alpha_MLE",
                "pareto_beta_mle_continuity": "beta_MLE",
                "pareto_ls_r2": "R2_LS",
            }
        )
        .reset_index(drop=True)
    )


def refresh_official_gdp_snapshot(path: Path = GDP_PATH) -> bool:
    """Refresh the checked-in BCB SGS 7326 snapshot; return False offline."""
    try:
        with urlopen(BCB_GDP_API, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = []
        for item in payload:
            date = pd.to_datetime(item["data"], format="%d/%m/%Y")
            year = int(date.year)
            if START_YEAR <= year <= END_YEAR:
                rows.append(
                    {
                        "year": year,
                        "gdp_real_growth_pct": float(
                            str(item["valor"]).replace(",", ".")
                        ),
                    }
                )
        frame = pd.DataFrame(rows).drop_duplicates("year").sort_values("year")
        expected = list(range(START_YEAR, END_YEAR + 1))
        if frame["year"].tolist() != expected:
            raise ValueError("BCB SGS 7326 response has incomplete 1978-2025 coverage.")
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        return True
    except Exception as exc:  # network is optional for reproducible offline runs
        warnings.warn(
            f"Could not refresh BCB SGS 7326; using checked-in snapshot: {exc}",
            RuntimeWarning,
        )
        return False


def load_gdp_series(refresh: bool = True) -> pd.DataFrame:
    if refresh:
        refresh_official_gdp_snapshot()
    if not GDP_PATH.is_file():
        raise FileNotFoundError(f"Missing GDP snapshot: {GDP_PATH}")
    frame = pd.read_csv(GDP_PATH)
    _require_columns(
        frame, {"year", "gdp_real_growth_pct"}, "BCB SGS 7326 GDP"
    )
    frame["year"] = pd.to_numeric(frame["year"], errors="raise").astype(int)
    frame["gdp_real_growth_pct"] = pd.to_numeric(
        frame["gdp_real_growth_pct"], errors="raise"
    )
    frame = frame.loc[
        frame["year"].between(START_YEAR, END_YEAR)
    ].sort_values("year").reset_index(drop=True)
    expected = list(range(START_YEAR, END_YEAR + 1))
    if frame["year"].tolist() != expected:
        raise AssertionError("GDP series must contain every year from 1978 to 2025.")
    if not np.isfinite(frame["gdp_real_growth_pct"]).all():
        raise AssertionError("GDP series contains invalid values.")
    return frame


def _save_figure(fig: plt.Figure, stem: str) -> None:
    """Save SVG for inspection and PDF for direct LaTeX inclusion."""
    FIGURES_PAPER_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for extension in ("svg", "pdf"):
        fig.savefig(
            FIGURES_PAPER_DIR / f"{stem}.{extension}",
            bbox_inches="tight",
            dpi=220,
        )
    plt.close(fig)


def _grid(n: int, ncols: int = 4, width: float = 3.2, height: float = 2.6):
    nrows = int(math.ceil(n / ncols))
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(width * ncols, height * nrows),
        squeeze=False,
    )
    return fig, axes.ravel()


def _finish_grid(fig: plt.Figure, axes, used: int, stem: str) -> None:
    for ax in axes[used:]:
        fig.delaxes(ax)
    _save_figure(fig, stem)


def split_survey_years(years: list[int]) -> tuple[list[int], list[int]]:
    first = [year for year in years if year <= ORIGINAL_SPLIT_YEAR]
    second = [year for year in years if year > ORIGINAL_SPLIT_YEAR]
    if first + second != years:
        raise AssertionError("Survey-year split changed year ordering.")
    return first, second


def plot_ccdf_pair(curves: pd.DataFrame, first: list[int], second: list[int]) -> None:
    for figure_no, years in ((1, first), (2, second)):
        fig, axes = _grid(len(years))
        for ax, year in zip(axes, years):
            temp = curves.loc[
                (curves["year"] == year)
                & (curves["income_normalized"] > 0)
                & (curves["empirical_ccdf_percent"] > 0)
            ]
            ax.plot(
                temp["income_normalized"],
                temp["empirical_ccdf_percent"],
                linewidth=1.0,
            )
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(str(year))
            ax.set_xlabel("x")
            ax.set_ylabel("F(x) [%]")
        _finish_grid(fig, axes, len(years), FIGURE_STEMS[figure_no])


def plot_lorenz_pair(
    lorenz: pd.DataFrame, first: list[int], second: list[int]
) -> None:
    for figure_no, years in ((3, first), (4, second)):
        fig, axes = _grid(len(years))
        for ax, year in zip(axes, years):
            temp = lorenz.loc[lorenz["year"] == year]
            ax.plot(
                100.0 * temp["population_share"],
                100.0 * temp["income_share"],
                linewidth=1.1,
            )
            ax.plot([0, 100], [0, 100], linestyle="--", linewidth=0.8)
            ax.set_title(str(year))
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 100)
            ax.set_xlabel("Cumulative population [%]")
            ax.set_ylabel("Cumulative income [%]")
        _finish_grid(fig, axes, len(years), FIGURE_STEMS[figure_no])


def _plot_gapped_series(
    ax: plt.Axes, frame: pd.DataFrame, value_column: str, ylabel: str
) -> None:
    full = pd.DataFrame({"year": np.arange(START_YEAR, END_YEAR + 1)})
    plotted = full.merge(frame[["year", value_column]], on="year", how="left")
    ax.plot(
        plotted["year"],
        plotted[value_column],
        marker="o",
        markersize=3,
        linewidth=1.2,
    )
    ax.set_xlim(START_YEAR, END_YEAR)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)


def plot_gini(stats: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    _plot_gapped_series(ax, stats, "Gini", "Gini coefficient")
    _save_figure(fig, FIGURE_STEMS[5])


def plot_exponential_pair(
    curves: pd.DataFrame,
    fits: pd.DataFrame,
    first: list[int],
    second: list[int],
) -> None:
    fits_index = fits.set_index("year")
    for figure_no, years in ((6, first), (7, second)):
        fig, axes = _grid(len(years))
        for ax, year in zip(axes, years):
            row = fits_index.loc[year]
            x_gmax = float(row["gompertz_x_gmax"])
            temp = curves.loc[
                (curves["year"] == year)
                & (curves["income_normalized"] > 0)
                & (curves["income_normalized"] <= x_gmax)
                & (curves["empirical_ccdf_percent"] > 0)
            ].copy()
            diag = fit_exponential_lower_region(temp, x_gmax)
            x = temp["income_normalized"].to_numpy(float)
            y = np.log(temp["empirical_ccdf_percent"].to_numpy(float))
            order = np.argsort(x)
            ax.scatter(x, y, s=8)
            ax.plot(
                x[order],
                np.log(diag["C"]) - diag["lambda"] * x[order],
                linestyle="--",
                linewidth=1.0,
            )
            ax.set_title(
                rf"{year}: $\lambda={diag['lambda']:.3f}$, $R^2={diag['r2']:.3f}$"
            )
            ax.set_xlabel("x")
            ax.set_ylabel(r"$\ln F(x)$")
        _finish_grid(fig, axes, len(years), FIGURE_STEMS[figure_no])


def plot_gompertz_pair(
    curves: pd.DataFrame,
    fits: pd.DataFrame,
    first: list[int],
    second: list[int],
) -> None:
    fits_index = fits.set_index("year")
    for figure_no, years in ((8, first), (9, second)):
        fig, axes = _grid(len(years))
        for ax, year in zip(axes, years):
            row = fits_index.loc[year]
            x_gmax = float(row["gompertz_x_gmax"])
            temp = curves.loc[
                (curves["year"] == year)
                & (curves["income_normalized"] <= x_gmax)
                & curves["gompertz_transform"].notna()
            ].copy()
            x = temp["income_normalized"].to_numpy(float)
            y = temp["gompertz_transform"].to_numpy(float)
            order = np.argsort(x)
            ax.scatter(x, y, s=8)
            ax.plot(
                x[order],
                float(row["gompertz_A"])
                - float(row["gompertz_B"]) * x[order],
                linestyle="--",
                linewidth=1.0,
            )
            ax.axvline(x_gmax, linestyle=":", linewidth=0.8)
            ax.set_title(
                rf"{year}: $A={row['gompertz_A']:.3f}$, "
                rf"$B={row['gompertz_B']:.3f}$"
            )
            ax.set_xlabel("x")
            ax.set_ylabel(r"$\ln[\ln F(x)]$")
        _finish_grid(fig, axes, len(years), FIGURE_STEMS[figure_no])


def _plot_pareto_pair(
    curves: pd.DataFrame,
    fits: pd.DataFrame,
    first: list[int],
    second: list[int],
    method: str,
) -> None:
    fits_index = fits.set_index("year")
    pairs = ((10, first), (11, second)) if method == "LS" else ((12, first), (13, second))

    for figure_no, years in pairs:
        fig, axes = _grid(len(years))
        for ax, year in zip(axes, years):
            row = fits_index.loc[year]
            x_pmin = float(row["pareto_x_pmin"])
            x_t = float(row["transition_x_t"])
            lower = x_pmin if method == "LS" else x_t
            temp = curves.loc[
                (curves["year"] == year)
                & (curves["income_normalized"] >= lower)
                & (curves["empirical_ccdf_percent"] > 0)
            ].copy()
            x = temp["income_normalized"].to_numpy(float)
            empirical = temp["empirical_ccdf_percent"].to_numpy(float)
            if method == "LS":
                alpha = float(row["pareto_alpha_ls"])
                beta = float(row["pareto_beta_ls"])
                r2 = float(row["pareto_ls_r2"])
            else:
                alpha = float(row["pareto_alpha_mle"])
                beta = float(row["pareto_beta_mle_continuity"])
                r2 = float(row["pareto_ls_r2"])

            order = np.argsort(x)
            fitted = beta * np.power(x, -alpha)
            ax.scatter(np.log(x), np.log(empirical), s=8)
            ax.plot(
                np.log(x[order]),
                np.log(fitted[order]),
                linewidth=1.0,
            )
            ax.axvline(np.log(x_t), linestyle=":", linewidth=0.8)
            if not np.isclose(x_t, x_pmin):
                ax.axvline(np.log(x_pmin), linestyle="--", linewidth=0.8)
            suffix = rf", $R^2_{{LS}}={r2:.3f}$" if method == "LS" else ""
            ax.set_title(rf"{year}: $\alpha_{{{method}}}={alpha:.3f}$" + suffix)
            ax.set_xlabel(r"$\ln x$")
            ax.set_ylabel(r"$\ln F(x)$")
        _finish_grid(fig, axes, len(years), FIGURE_STEMS[figure_no])


def plot_pareto_income_share(table_04: pd.DataFrame) -> None:
    data = table_04.assign(
        pareto_income_share_pct=100.0 * table_04["pareto_income_share"]
    )
    fig, ax = plt.subplots(figsize=(10, 4.8))
    _plot_gapped_series(
        ax, data, "pareto_income_share_pct", "Pareto share of total income [%]"
    )
    _save_figure(fig, FIGURE_STEMS[14])


def plot_real_gdp_growth(gdp: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(
        gdp["year"],
        gdp["gdp_real_growth_pct"],
        marker="o",
        markersize=3,
        linewidth=1.2,
    )
    ax.axhline(0.0, linewidth=0.8)
    ax.set_xlim(START_YEAR, END_YEAR)
    ax.set_xlabel("Year")
    ax.set_ylabel("Real GDP growth [%]")
    ax.grid(True, alpha=0.25)
    _save_figure(fig, FIGURE_STEMS[15])


def validate_replication_tables(tables: dict[str, pd.DataFrame]) -> None:
    """Assert cross-table year coverage and scientific partition invariants."""
    year_sets = {
        name: tuple(frame["year"].astype(int).tolist())
        for name, frame in tables.items()
    }
    unique = set(year_sets.values())
    if len(unique) != 1:
        raise AssertionError(f"Paper tables have inconsistent survey years: {year_sets}")

    table_02 = tables["table_02"]
    table_03 = tables["table_03"]
    table_04 = tables["table_04"]

    population_sum = (
        table_02["gompertz_population_pct"].to_numpy(float)
        + table_03["pareto_population_pct"].to_numpy(float)
    )
    if not np.allclose(population_sum, 100.0, atol=1.0e-10, rtol=0.0):
        raise AssertionError("Gompertz and Pareto population percentages must sum to 100%.")

    shares = (
        table_04["gompertz_income_share"].to_numpy(float)
        + table_04["pareto_income_share"].to_numpy(float)
    )
    if not np.allclose(shares, 1.0, atol=1.0e-12, rtol=0.0):
        raise AssertionError("Gompertz and Pareto income shares must sum to one.")

    boundary = table_02[["year", "x_G_max"]].merge(
        table_03[["year", "x_P_min", "x_t"]], on="year"
    )
    if not (
        (boundary["x_G_max"] <= boundary["x_t"] + 1.0e-12)
        & (boundary["x_t"] <= boundary["x_P_min"] + 1.0e-12)
    ).all():
        raise AssertionError("Expected x_G,max <= x_t <= x_P,min for every year.")

    numeric_nonnegative = {
        "table_02": ["A", "B", "x_G_max", "R2", "gompertz_population_pct"],
        "table_03": [
            "x_P_min",
            "x_t",
            "delta_x_t",
            "alpha_LS",
            "beta_LS",
            "alpha_MLE",
            "beta_MLE",
            "R2_LS",
            "pareto_population_pct",
        ],
        "table_04": ["gompertz_income_share", "pareto_income_share", "gini"],
    }
    for table_name, columns in numeric_nonnegative.items():
        values = tables[table_name][columns].to_numpy(float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise AssertionError(f"{table_name} contains negative or invalid metrics.")


def historical_replication_diagnostics(
    fits: pd.DataFrame, stats: pd.DataFrame
) -> dict[str, float]:
    """Return robust errors against the published 1978--2005 central values."""
    historical_fits = fits.loc[fits["year"] <= 2005].copy()
    t2 = historical_fits.merge(PUBLISHED_TABLE_2, on="year", how="inner")
    t3 = historical_fits.merge(PUBLISHED_TABLE_3, on="year", how="inner")
    tg = (
        stats.loc[stats["year"].between(START_YEAR, 2005), ["year", "Gini"]]
        .merge(PUBLISHED_TABLE_4_GINI, on="year", how="inner")
    )
    return {
        "median_abs_A_error": float(
            np.median(np.abs(t2["gompertz_A"] - t2["published_A"]))
        ),
        "median_abs_B_error": float(
            np.median(np.abs(t2["gompertz_B"] - t2["published_B"]))
        ),
        "median_abs_x_gmax_error": float(
            np.median(np.abs(t2["gompertz_x_gmax"] - t2["published_x_gmax"]))
        ),
        "median_abs_alpha_mle_error": float(
            np.median(np.abs(t3["pareto_alpha_mle"] - t3["published_alpha_mle"]))
        ),
        "median_abs_gini_error": float(
            np.median(np.abs(tg["Gini"] - tg["published_gini"]))
        ),
    }


def write_tables(tables: dict[str, pd.DataFrame]) -> None:
    TABLES_PAPER_DIR.mkdir(parents=True, exist_ok=True)
    for key, filename in TABLE_FILENAMES.items():
        tables[key].to_csv(TABLES_PAPER_DIR / filename, index=False)


def assert_figure_outputs() -> None:
    expected = {
        FIGURES_PAPER_DIR / f"{stem}.{extension}"
        for stem in FIGURE_STEMS.values()
        for extension in ("svg", "pdf")
    }
    missing = sorted(str(path) for path in expected if not path.is_file())
    if missing:
        raise AssertionError("Missing paper figure outputs: " + ", ".join(missing))


def run_replication(refresh_gdp: bool = True) -> dict[str, pd.DataFrame]:
    inputs = load_replication_inputs()
    fits = inputs["fits"]
    stats = inputs["stats"].sort_values("year").reset_index(drop=True)
    years = fits["year"].astype(int).tolist()
    first, second = split_survey_years(years)

    table_01 = build_table_01(stats, inputs["metadata"], years)
    table_02 = build_table_02(fits)
    table_03 = build_table_03(fits)
    table_04 = build_income_share_table(fits, stats)
    tables = {
        "table_01": table_01,
        "table_02": table_02,
        "table_03": table_03,
        "table_04": table_04,
    }
    validate_replication_tables(tables)
    write_tables(tables)

    gdp = load_gdp_series(refresh=refresh_gdp)
    plot_ccdf_pair(inputs["curves"], first, second)
    plot_lorenz_pair(inputs["lorenz"], first, second)
    plot_gini(stats)
    plot_exponential_pair(inputs["curves"], fits, first, second)
    plot_gompertz_pair(inputs["curves"], fits, first, second)
    _plot_pareto_pair(inputs["curves"], fits, first, second, method="LS")
    _plot_pareto_pair(inputs["curves"], fits, first, second, method="MLE")
    plot_pareto_income_share(table_04)
    plot_real_gdp_growth(gdp)
    assert_figure_outputs()

    diagnostics = historical_replication_diagnostics(fits, stats)
    print("Moura-Ribeiro 2009 replication diagnostics:")
    for key, value in diagnostics.items():
        print(f"  {key}: {value:.6g}")

    return {**tables, "gdp": gdp}


def main() -> None:
    run_replication(refresh_gdp=True)


if __name__ == "__main__":
    main()
