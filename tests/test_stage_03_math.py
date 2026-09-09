import numpy as np
import pytest

from src.stage_03_pnad_analysis import (
    empirical_ccdf,
    geometric_edges,
    inequality_geometry,
    lorenz_curve,
    top_share,
)


def test_empirical_ccdf_exact_values():
    values = np.array([1.0, 2.0, 3.0, 4.0])
    thresholds = np.array([1.0, 2.5, 4.0, 5.0])

    result = empirical_ccdf(values, thresholds)

    np.testing.assert_allclose(result, [1.0, 0.5, 0.25, 0.0])


def test_geometric_edges_are_monotone_and_cover_maximum():
    edges = geometric_edges(1.0, 10.0, ratio=2.0)

    assert edges[0] == pytest.approx(1.0)
    assert np.all(np.diff(edges) > 0)
    assert edges[-1] > 10.0


@pytest.mark.parametrize(
    ("xmin", "xmax"),
    [
        (0.0, 1.0),
        (-1.0, 1.0),
        (1.0, 0.0),
        (2.0, 1.0),
    ],
)
def test_geometric_edges_reject_invalid_intervals(xmin, xmax):
    with pytest.raises(ValueError):
        geometric_edges(xmin, xmax)


def test_lorenz_curve_for_equal_distribution_matches_equality_line():
    population_share, income_share = lorenz_curve([1.0, 1.0, 1.0, 1.0])

    expected = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    np.testing.assert_allclose(population_share, expected)
    np.testing.assert_allclose(income_share, expected)


def test_inequality_geometry_for_equal_distribution():
    population_share, income_share = lorenz_curve([1.0, 1.0, 1.0, 1.0])

    result = inequality_geometry(population_share, income_share)

    assert result["Gini"] == pytest.approx(0.0, abs=1e-12)
    assert result["Pietra"] == pytest.approx(0.0, abs=1e-12)
    assert result["Kolkata"] == pytest.approx(0.5, abs=1e-12)


def test_top_share_simple_distribution():
    population_share, income_share = lorenz_curve([1.0, 3.0])

    result = top_share(population_share, income_share, 0.5)

    assert result == pytest.approx(0.75, abs=1e-12)
