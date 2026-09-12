from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.ticker import NullFormatter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_05_moura_ribeiro as stage_05


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


def test_fixed_gompertz_bootstrap_keeps_A_and_recovers_B(monkeypatch):
    monkeypatch.setattr(stage_05, "BOOTSTRAP_REPS", 32)
    A = float(np.log(np.log(100.0)))
    B = 1.75
    x = np.linspace(0.2, 3.0, 20)
    y = A - B * x
    rng = np.random.default_rng(1234)

    draws = stage_05.bootstrap_fixed_gompertz_B(x, y, A, rng)

    assert draws.shape == (32,)
    assert np.allclose(draws, B, atol=1e-12)
