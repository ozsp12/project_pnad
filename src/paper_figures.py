"""Publication-only figure post-processing for the PNAD paper assets.

This module does not alter datasets, fits, parameters, or numerical tables. It
adds publication figures derived from existing trusted analysis tables and
normalizes final paper-figure filenames and manifests after stage 05 generation.
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
PNG_DPI = 300
SINGLE_FIGSIZE = (7.0, 4.5)

FIGURE_NUMBER_BY_PREFIX = {
    "ccdf_trusted_part_": "1-2",
    "lorenz_geometry_trusted_part_": "3-4",
    "figure_05_gini_trusted_": "5",
    "exponential_trusted_part_": "6-7",
    "gompertz_trusted_part_": "8-9",
    "pareto_ls_trusted_part_": "10-11",
    "pareto_mle_trusted_part_": "12-13",
    "figure_14_pareto_income_share_trusted_": "14",
    "figure_15_gdp_growth_": "15",
    "figure_16_inequality_indices_trusted_": "16 (extension)",
}

TABLE_MANIFEST_ROWS = [
    ("1", "moura_ribeiro_2009_table_01_currency_mean_income_trusted_1978_2025.csv"),
    ("2", "moura_ribeiro_2009_table_02_gompertz_parameters_trusted_1978_2025.csv"),
    ("3", "moura_ribeiro_2009_table_03_pareto_parameters_trusted_1978_2025.csv"),
    ("4", "moura_ribeiro_2009_table_04_income_shares_gini_trusted_1978_2025.csv"),
]

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

    fig, ax = plt.subplots(figsize=SINGLE_FIGSIZE)

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
    out = FIGURES_PAPER / f"{INEQUALITY_STEM}.png"
    fig.savefig(
        out,
        format="png",
        dpi=PNG_DPI,
        pil_kwargs={"compress_level": 9},
    )
    plt.close(fig)
    return INEQUALITY_STEM


def normalize_paper_figure_names() -> None:
    """Remove the legacy Moura-Ribeiro prefix from final PNG figure filenames."""
    FIGURES_PAPER.mkdir(parents=True, exist_ok=True)
    for source in sorted(FIGURES_PAPER.glob(f"{LEGACY_PREFIX}*.png")):
        target = source.with_name(source.name.removeprefix(LEGACY_PREFIX))
        if target.exists():
            target.unlink()
        source.replace(target)


def update_manifests(extra_stem: str) -> None:
    """Keep manifest figure references synchronized with final prefixless PNG names."""
    TABLES_PAPER.mkdir(parents=True, exist_ok=True)
    for path in sorted(TABLES_PAPER.glob("*manifest_trusted.csv")):
        manifest = pd.read_csv(path, dtype=str).fillna("")
        if "svg" in manifest.columns:
            if "png" not in manifest.columns:
                manifest = manifest.rename(columns={"svg": "png"})
            else:
                manifest = manifest.drop(columns=["svg"])
        if "png" not in manifest.columns:
            manifest["png"] = ""
        for column in ("stem", "png"):
            if column in manifest.columns:
                manifest[column] = manifest[column].str.replace(
                    f"^{LEGACY_PREFIX}", "", regex=True
                )
        manifest["png"] = manifest["png"].str.replace(
            r"\.svg$", ".png", regex=True
        )
        if "asset_type" in manifest.columns and "stem" in manifest.columns:
            mask = (manifest["asset_type"] == "figure") & (manifest["stem"] == extra_stem)
            if not mask.any():
                row = {column: "" for column in manifest.columns}
                row["asset_type"] = "figure"
                row["stem"] = extra_stem
                row["png"] = f"{extra_stem}.png"
                manifest = pd.concat([manifest, pd.DataFrame([row])], ignore_index=True)
        manifest.to_csv(path, index=False)


def rebuild_replication_manifest() -> None:
    """Map original paper numbering to the canonical trusted PNG assets."""
    trusted_path = TABLES_PAPER / "moura_ribeiro_2009_replication_manifest_trusted.csv"
    trusted = pd.read_csv(trusted_path, dtype=str).fillna("")
    rows = [
        {"original_number": number, "asset_type": "table", "filename": filename}
        for number, filename in TABLE_MANIFEST_ROWS
    ]
    for row in trusted.loc[trusted["asset_type"] == "figure"].itertuples(index=False):
        stem = str(row.stem)
        original_number = next(
            (
                number
                for prefix, number in FIGURE_NUMBER_BY_PREFIX.items()
                if stem.startswith(prefix)
            ),
            "extension",
        )
        rows.append(
            {
                "original_number": original_number,
                "asset_type": "figure",
                "filename": str(row.png),
            }
        )
    replication_manifest = TABLES_PAPER / "moura_ribeiro_2009_replication_manifest.csv"
    pd.DataFrame(rows).to_csv(replication_manifest, index=False)


def main() -> None:
    normalize_paper_figure_names()
    stem = plot_inequality_indices_trusted()
    update_manifests(stem)
    rebuild_replication_manifest()
    print(f"Paper inequality figure: {stem}.png")


if __name__ == "__main__":
    main()
