"""Publication-only figure finishing for the Moura-Ribeiro stage.

This helper runs after ``stage_05_moura_ribeiro.py``. It keeps paper figures
monochrome, adds the trusted inequality-index time series requested for the
manuscript, and removes the historical ``moura_ribeiro_2009_`` filename prefix
from every figure asset without changing the underlying numerical results.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
FIGURES_PAPER = REPO_ROOT / "assets" / "figures_paper"
TABLES_PAPER = REPO_ROOT / "assets" / "tables_paper"
TABLES_ANALYSIS_TRUSTED = REPO_ROOT / "assets" / "tables_analysis_trusted"

LEGACY_PREFIX = "moura_ribeiro_2009_"
START_YEAR = 1978
END_YEAR = 2025
PNAD_CONTINUOUS_BOUNDARY = 2015.5

mpl.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 9.5,
        "axes.labelsize": 10.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9.2,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "text.color": "0.10",
        "axes.labelcolor": "0.10",
        "xtick.color": "0.15",
        "ytick.color": "0.15",
    }
)


def _load_inequality_table() -> pd.DataFrame:
    """Load the trusted inequality indices, preferring the paper table."""
    candidates = [
        TABLES_PAPER / "income_shares_inequality.csv",
        TABLES_PAPER / "moura_ribeiro_2009_table_04_income_shares_gini_trusted_1978_2025.csv",
    ]
    for path in candidates:
        if path.exists():
            data = pd.read_csv(path)
            required = {
                "year",
                "gini_coefficient",
                "pietra_index",
                "kolkata_index",
                "zanardi_index",
            }
            if required.issubset(data.columns):
                break
    else:
        path = TABLES_ANALYSIS_TRUSTED / "trusted_analysis_statistics_annual.csv"
        data = pd.read_csv(path).rename(
            columns={
                "Gini": "gini_coefficient",
                "Pietra": "pietra_index",
                "Kolkata": "kolkata_index",
                "Zanardi": "zanardi_index",
            }
        )

    required = [
        "year",
        "gini_coefficient",
        "pietra_index",
        "kolkata_index",
        "zanardi_index",
    ]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Missing inequality columns: {missing}")

    data = data[required].copy()
    data["year"] = pd.to_numeric(data["year"], errors="raise").astype(int)
    for column in required[1:]:
        data[column] = pd.to_numeric(data[column], errors="raise")
    return (
        data[(data["year"] >= START_YEAR) & (data["year"] <= END_YEAR)]
        .sort_values("year")
        .reset_index(drop=True)
    )


def plot_inequality_indices() -> Path:
    """Plot Gini, Pietra, Kolkata and Zanardi from the trusted annual series."""
    data = _load_inequality_table()
    fig, ax = plt.subplots(figsize=(9.4, 5.4))

    styles = [
        ("gini_coefficient", "Gini", "0.05", "-", "o"),
        ("pietra_index", "Pietra", "0.25", "--", "s"),
        ("kolkata_index", "Kolkata", "0.12", ":", "^"),
        ("zanardi_index", "Zanardi", "0.45", "-.", "D"),
    ]
    for column, label, gray, linestyle, marker in styles:
        ax.plot(
            data["year"],
            data[column],
            label=label,
            color=gray,
            linestyle=linestyle,
            linewidth=1.25,
            marker=marker,
            markersize=4.0,
            markerfacecolor="white",
            markeredgecolor=gray,
            markeredgewidth=0.85,
        )

    ax.axvline(
        PNAD_CONTINUOUS_BOUNDARY,
        color="0.50",
        linestyle=(0, (5, 3)),
        linewidth=0.95,
        zorder=0,
    )
    ax.annotate(
        "PNAD → PNAD-C",
        xy=(PNAD_CONTINUOUS_BOUNDARY, 1.0),
        xycoords=("data", "axes fraction"),
        xytext=(0, 7),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=8.8,
        color="0.25",
    )

    ax.set_xlabel("Year")
    ax.set_ylabel("Inequality index")
    ax.set_xlim(float(data["year"].min()) - 1.0, float(data["year"].max()) + 1.0)
    ax.set_ylim(0.0, 0.82)
    ax.grid(True, which="major", color="0.88", linestyle=":", linewidth=0.55)

    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_color("0.25")
        ax.spines[side].set_linewidth(0.75)
    ax.tick_params(axis="both", direction="out", length=3.5, width=0.7, color="0.25")

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.03),
        ncol=4,
        frameon=False,
        handlelength=3.2,
        columnspacing=1.6,
    )

    FIGURES_PAPER.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.02, 0.02, 0.995, 0.95))
    output = FIGURES_PAPER / "inequality_indices_trusted_1978_2025.svg"
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    return output


def strip_legacy_figure_prefix() -> list[Path]:
    """Rename every paper figure by removing the historical filename prefix."""
    FIGURES_PAPER.mkdir(parents=True, exist_ok=True)
    renamed: list[Path] = []
    for source in sorted(FIGURES_PAPER.glob(f"{LEGACY_PREFIX}*")):
        if not source.is_file():
            continue
        target = source.with_name(source.name.removeprefix(LEGACY_PREFIX))
        if target.exists():
            target.unlink()
        source.replace(target)
        renamed.append(target)
    return renamed


def main() -> None:
    renamed = strip_legacy_figure_prefix()
    output = plot_inequality_indices()
    print(f"Removed legacy prefix from {len(renamed)} paper figure files.")
    print(f"Generated {output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
