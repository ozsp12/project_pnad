from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_05_publication as stage_05


def test_paper_lorenz_geometry_contains_all_inequality_indices(monkeypatch):
    year = 2017
    lorenz = pd.DataFrame(
        {
            "year": [year] * 5,
            "population_share": [0.0, 0.25, 0.50, 0.75, 1.0],
            "income_share": [0.0, 0.10, 0.28, 0.55, 1.0],
        }
    )
    stats = pd.DataFrame(
        {
            "year": [year],
            "Gini": [0.535],
            "Pietra": [0.220],
            "Kolkata": [0.693],
            "Zanardi": [0.386],
        }
    )

    captured = {}

    def fake_family(years, stem, draw, xlabel, ylabel, legend=False, ncol=3):
        fig, ax = plt.subplots()
        draw(ax, year)
        captured["stem"] = stem
        captured["labels"] = ax.get_legend_handles_labels()[1]
        captured["aspect"] = ax.get_aspect()
        captured["collections"] = len(ax.collections)
        captured["lines"] = len(ax.lines)
        plt.close(fig)

    monkeypatch.setattr(stage_05, "family", fake_family)
    stage_05.plot_lorenz(lorenz, stats, [year])

    labels = captured["labels"]
    assert captured["stem"] == "lorenz_geometry"
    assert "Area B" in labels
    assert "Lorenz curve" in labels
    assert "Equality line" in labels
    assert any(label.startswith("k:") for label in labels)
    assert any(label.startswith("G:") for label in labels)
    assert any(label.startswith("Z:") for label in labels)
    assert any(label.startswith("p:") for label in labels)
    assert captured["aspect"] == 1.0
    assert captured["collections"] >= 3
    assert captured["lines"] >= 7
