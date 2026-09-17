from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.colors import to_rgb
from matplotlib.ticker import NullFormatter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_05_publication as stage_05


def test_year_groups_use_at_most_twelve_panels():
    year_groups = stage_05.groups(range(1978, 2003))

    assert [len(group) for group in year_groups] == [12, 12, 1]
    assert all(len(group) <= stage_05.MAX_PANELS for group in year_groups)


def test_grid_is_three_columns_by_four_rows_at_full_capacity():
    fig, axes = stage_05.grid(stage_05.MAX_PANELS)

    try:
        assert axes.shape == (4, 3)
        assert tuple(fig.get_size_inches()) == pytest.approx(stage_05.PAGE_SIZE)
    finally:
        plt.close(fig)


def test_log_grid_suppresses_minor_tick_labels():
    fig, ax = plt.subplots()
    ax.set_xscale("log")
    ax.set_yscale("log")

    try:
        stage_05.style(ax, log=True)
        assert isinstance(ax.xaxis.get_minor_formatter(), NullFormatter)
        assert isinstance(ax.yaxis.get_minor_formatter(), NullFormatter)
    finally:
        plt.close(fig)


def test_publication_palette_is_colored_and_canonical():
    colors = matplotlib.rcParams["axes.prop_cycle"].by_key()["color"]
    assert tuple(colors) == stage_05.PUBLICATION_COLORS
    assert len(set(colors)) == len(colors)
    for color in colors:
        red, green, blue = to_rgb(color)
        assert not (red == pytest.approx(green) and green == pytest.approx(blue))


def test_series_template_uses_color_line_and_marker_encodings():
    assert len(set(stage_05.LINE_STYLES)) == len(stage_05.LINE_STYLES)
    assert len(set(stage_05.MARKERS)) == len(stage_05.MARKERS)
    for index, color in enumerate(stage_05.PUBLICATION_COLORS[: len(stage_05.MARKERS)]):
        spec = stage_05.series_style(index)
        assert spec["color"] == color
        assert spec["markerfacecolor"] == color
        assert spec["markeredgecolor"] == color


def test_adjusted_income_uses_metadata_scale(monkeypatch):
    monkeypatch.setattr(
        stage_05,
        "income",
        lambda year, positive=True: np.array([100.0, 200.0]),
    )
    metadata = pd.DataFrame(
        {"exchange": [2.0], "Inflation": [3.0]}, index=pd.Index([2000], name="year")
    )

    adjusted = stage_05.adjusted_income(2000, metadata)

    assert adjusted.tolist() == pytest.approx([150.0, 300.0])


def test_lorenz_geometry_contains_area_and_inequality_annotations(monkeypatch):
    lorenz = pd.DataFrame(
        {
            "year": [2000, 2000, 2000, 2000],
            "population_share": [0.0, 0.5, 0.7, 1.0],
            "income_share": [0.0, 0.2, 0.3, 1.0],
        }
    )
    stats = pd.DataFrame(
        {
            "year": [2000],
            "Gini": [0.50],
            "Kolkata": [0.70],
            "Zanardi": [0.02],
            "Pietra": [0.40],
        }
    )
    captured = {}

    def fake_family(years, stem, draw, xlabel, ylabel, legend=False, ncol=3):
        fig, ax = plt.subplots()
        try:
            draw(ax, 2000)
            captured["stem"] = stem
            captured["xlabel"] = xlabel
            captured["ylabel"] = ylabel
            captured["labels"] = ax.get_legend_handles_labels()[1]
            captured["line_colors"] = [line.get_color() for line in ax.lines]
        finally:
            plt.close(fig)

    monkeypatch.setattr(stage_05, "family", fake_family)
    stage_05.plot_lorenz(lorenz, stats, [2000])

    assert captured["stem"] == "lorenz_geometry"
    assert captured["xlabel"] == "Households (%)"
    assert captured["ylabel"] == "Income (%)"
    assert "area B" in captured["labels"]
    assert "equality line" in captured["labels"]
    assert any(label.startswith("k:") for label in captured["labels"])
    assert any(label.startswith("G:") for label in captured["labels"])
    assert any(label.startswith("Z:") for label in captured["labels"])
    assert any(label.startswith("p:") for label in captured["labels"])
    assert stage_05.PURPLE in captured["line_colors"]
    assert stage_05.RED in captured["line_colors"]
    assert stage_05.ROYAL_BLUE in captured["line_colors"]


def test_save_figure_writes_only_png(tmp_path, monkeypatch):
    monkeypatch.setattr(stage_05, "FIGURES", tmp_path)
    fig, ax = plt.subplots(figsize=(1.0, 1.0))
    ax.plot([0, 1], [0, 1])

    stage_05.save(fig, "example")

    assert (tmp_path / "example.png").is_file()
    assert not (tmp_path / "example.svg").exists()


def test_clean_figures_removes_obsolete_formats(tmp_path, monkeypatch):
    monkeypatch.setattr(stage_05, "FIGURES", tmp_path)
    for name in ("old.svg", "old.pdf", "old.png", ".gitkeep"):
        (tmp_path / name).write_bytes(b"placeholder")

    stage_05.clean_figures()

    assert sorted(path.name for path in tmp_path.iterdir()) == [".gitkeep"]


def test_stage_05_contains_no_scientific_reestimation_routines():
    forbidden = {
        "bootstrap",
        "bootstrap_line",
        "bootstrap_fixed_gompertz_B",
        "exponential_fits",
        "regime_shares",
        "r2_log",
    }
    assert forbidden.isdisjoint(vars(stage_05))
