from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
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


def test_publication_palette_is_strictly_monochrome():
    colors = matplotlib.rcParams["axes.prop_cycle"].by_key()["color"]
    assert tuple(colors) == stage_05.MONOCHROME_COLORS
    for color in colors:
        red, green, blue = to_rgb(color)
        assert red == pytest.approx(green)
        assert green == pytest.approx(blue)


def test_series_template_uses_distinct_nonchromatic_encodings():
    assert len(set(stage_05.LINE_STYLES)) == len(stage_05.LINE_STYLES)
    assert len(set(stage_05.MARKERS)) == len(stage_05.MARKERS)
    for index in range(len(stage_05.MONOCHROME_COLORS)):
        spec = stage_05.series_style(index)
        assert spec["markerfacecolor"] == "white"
        red, green, blue = to_rgb(spec["color"])
        assert red == pytest.approx(green)
        assert green == pytest.approx(blue)


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
