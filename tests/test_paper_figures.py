from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.ticker import NullFormatter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import paper_figures
from src import stage_05_moura_ribeiro as stage_05


def test_year_groups_use_at_most_twelve_panels():
    groups = stage_05._year_groups(range(1978, 2003))

    assert [len(group) for group in groups] == [12, 12, 1]
    assert all(len(group) <= stage_05.MAX_PANELS for group in groups)


def test_grid_is_three_columns_by_four_rows_at_full_capacity():
    fig, axes = stage_05._grid(stage_05.MAX_PANELS)

    try:
        assert axes.shape == (4, 3)
        assert tuple(fig.get_size_inches()) == pytest.approx(stage_05.LATEX_PAGE_FIGSIZE)
    finally:
        plt.close(fig)


def test_grid_rejects_more_than_twelve_panels():
    with pytest.raises(ValueError, match="At most 12 panels"):
        stage_05._grid(13)


def test_log_grid_suppresses_minor_tick_labels():
    fig, ax = plt.subplots()
    ax.set_xscale("log")
    ax.set_yscale("log")

    try:
        stage_05._style_axis(ax, log_grid=True)
        assert isinstance(ax.xaxis.get_minor_formatter(), NullFormatter)
        assert isinstance(ax.yaxis.get_minor_formatter(), NullFormatter)
    finally:
        plt.close(fig)


def test_save_figure_writes_only_png(tmp_path, monkeypatch):
    monkeypatch.setattr(stage_05, "FIGURES_PAPER", tmp_path)
    fig, ax = plt.subplots(figsize=(1.0, 1.0))
    ax.plot([0, 1], [0, 1])

    stage_05._save_figure(fig, "example")

    assert (tmp_path / "example.png").is_file()
    assert not (tmp_path / "example.svg").exists()


def test_prepare_figure_directory_removes_obsolete_formats(tmp_path, monkeypatch):
    monkeypatch.setattr(stage_05, "FIGURES_PAPER", tmp_path)
    for name in ("old.svg", "old.pdf", "old.png", ".gitkeep"):
        (tmp_path / name).write_bytes(b"placeholder")

    stage_05._prepare_figure_directory()

    assert sorted(path.name for path in tmp_path.iterdir()) == [".gitkeep"]


def test_normalize_paper_figure_names_removes_legacy_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(paper_figures, "FIGURES_PAPER", tmp_path)
    legacy = tmp_path / "moura_ribeiro_2009_ccdf_trusted_part_01.png"
    legacy.write_bytes(b"png")

    paper_figures.normalize_paper_figure_names()

    assert not legacy.exists()
    assert (tmp_path / "ccdf_trusted_part_01.png").is_file()
