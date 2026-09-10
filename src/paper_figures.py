"""Publication-only figure post-processing for the PNAD paper assets.

This module does not alter datasets, fits, parameters, or numerical tables. It
adds publication figures derived from existing trusted analysis tables and
normalizes final paper-figure filenames after stage 05 generation.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
FIGURES_PAPER = REPO_ROOT / "assets" / "figures_paper"
TABLES_PAPER = REPO_ROOT / "assets" / "tables_paper"
TRUSTED_STATS = (
    REPO_ROOT
    / "assets"
    / "tables_analysis_trusted"
    / "trusted_analysis_statistics_annual.csv"
)

LEGACY_PREFIX = "moura_ribeiro_2009_"
INEQUALITY_STEM = "figure_16_inequality_indices_trusted_1976_2025"

mpl.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8.5,
        "axes.edgecolor": "0.20",
        "axes.linewidth": 0.75,
        "xtick.color": "0.15",
        "ytick.color": "0.15",
        "text.color": "0.10",
        "axes.labelcolor": "0.10",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "svg.fonttype": "none",
    }
)


def _style_axis(ax: plt.Axes) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("bottom", "left"):
        ax.spines[side].set_color("0.25")
        ax.spines[side].set_linewidth(0.75)
    ax.tick_params(axis="both", which="major", direction="out", length=3.2, width=0.65)
    ax.grid(True, which="major", color="0.90", linewidth=0.45, linestyle="-")
    ax.set_axisbelow(True)


def plot_inequality_indices_trusted() -> str:
    """Plot Gini, Pietra, Kolkata and Zanardi from the trusted annual table."""
    stats = pd.read_csv(TRUSTED_STATS)
    required = ["year", "Gini", "Pietra", "Kolkata", "Zanardi"]
    missing = [name for name in required if name not in stats.columns]
    if missing:
        raise ValueError(f"Missing trusted inequality columns: {missing}")

    d = stats[required].copy()
    for column in required:
        d[column] = pd.to_numeric(d[column], errors="coerce")
    d = d.dropna(subset=required).sort_values("year")
    d = d[(d["year"] >= 1976) & (d["year"] <= 2025)]
    if d.empty:
        raise ValueError("No trusted inequality observations available for 1976-2025")

    fig, ax = plt.subplots(figsize=(8.6, 5.1))

    series = [
        ("Gini", "Gini", "0.05", "-", "o", True, 1.35),
        ("Pietra", "Pietra", "0.30", (0, (6, 2.5)), "s", False, 1.20),
        ("Kolkata", "Kolkata", "0.12", (0, (1.2, 2.0)), "^", True, 1.20),
        ("Zanardi", "Zanardi", "0.48", "-.", "D", False, 1.10),
    ]

    for column, label, gray, linestyle, marker, filled, linewidth in series:
        markerface = gray if filled else "white"
        ax.plot(
            d["year"],
            d[column],
            color=gray,
            linestyle=linestyle,
            linewidth=linewidth,
            marker=marker,
            markersize=3.6,
            markerfacecolor=markerface,
            markeredgecolor=gray,
            markeredgewidth=0.75,
            label=label,
            zorder=3,
        )

    ax.set_xlabel("Year")
    ax.set_ylabel("Inequality index")
    ax.set_xlim(float(d["year"].min()) - 1.0, float(d["year"].max()) + 1.0)
    ymax = float(np.nanmax(d[["Gini", "Pietra", "Kolkata", "Zanardi"]].to_numpy()))
    ax.set_ylim(0.0, min(1.0, ymax + 0.055))
    ax.set_xticks(np.arange(1980, 2026, 5))
    _style_axis(ax)

    legend = ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.015),
        ncol=4,
        frameon=False,
        handlelength=2.7,
        handletextpad=0.55,
        columnspacing=1.6,
        borderaxespad=0.0,
    )
    for handle in legend.legend_handles:
        handle.set_linewidth(1.25)

    fig.subplots_adjust(left=0.10, right=0.985, bottom=0.12, top=0.88)
    FIGURES_PAPER.mkdir(parents=True, exist_ok=True)
    out = FIGURES_PAPER / f"{INEQUALITY_STEM}.svg"
    fig.savefig(out, format="svg", bbox_inches="tight")
    plt.close(fig)
    return INEQUALITY_STEM


def normalize_paper_figure_names() -> None:
    """Remove the legacy Moura-Ribeiro prefix from final SVG figure filenames."""
    FIGURES_PAPER.mkdir(parents=True, exist_ok=True)
    for source in sorted(FIGURES_PAPER.glob(f"{LEGACY_PREFIX}*.svg")):
        target = source.with_name(source.name.removeprefix(LEGACY_PREFIX))
        if target.exists():
            target.unlink()
        source.replace(target)


def update_manifests(extra_stem: str) -> None:
    """Keep manifest figure references synchronized with final prefixless SVG names."""
    TABLES_PAPER.mkdir(parents=True, exist_ok=True)
    for path in sorted(TABLES_PAPER.glob("*manifest*.csv")):
        manifest = pd.read_csv(path, dtype=str).fillna("")
        for column in ("stem", "svg"):
            if column in manifest.columns:
                manifest[column] = manifest[column].str.replace(
                    f"^{LEGACY_PREFIX}", "", regex=True
                )
        if "asset_type" in manifest.columns and "stem" in manifest.columns:
            mask = (manifest["asset_type"] == "figure") & (manifest["stem"] == extra_stem)
            if not mask.any():
                row = {column: "" for column in manifest.columns}
                row["asset_type"] = "figure"
                row["stem"] = extra_stem
                if "svg" in manifest.columns:
                    row["svg"] = f"{extra_stem}.svg"
                manifest = pd.concat([manifest, pd.DataFrame([row])], ignore_index=True)
        manifest.to_csv(path, index=False)


def main() -> None:
    normalize_paper_figure_names()
    stem = plot_inequality_indices_trusted()
    update_manifests(stem)
    print(f"Paper inequality figure: {stem}.svg")


if __name__ == "__main__":
    main()
