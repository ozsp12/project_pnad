from pathlib import Path
import inspect
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from src import stage_02_build_trusted_pnad as stage_02
from src import stage_03_pnad_analysis as stage_03
from src import stage_05_publication as stage_05


def _frame(year, values):
    return pd.DataFrame({"ano": [year] * len(values), "renda": np.asarray(values, float)})


def test_p99_exception_applies_only_to_configured_years():
    values = np.arange(1.0, 101.0)
    trusted, audit, _ = stage_02.trim_refined_year(_frame(1985, values), 1985, threshold=50.0)
    assert audit["cutoff_rule"] == "min_log_mad_p99_exception"
    assert audit["p99_exception_cutoff"] == pytest.approx(np.quantile(values, 0.99))
    assert audit["n_statistical_outlier"] == 1
    assert trusted["renda"].max() < 100.0

    trusted_regular, regular, _ = stage_02.trim_refined_year(
        _frame(1986, values), 1986, threshold=50.0
    )
    assert regular["cutoff_rule"] == "log_mad"
    assert np.isnan(regular["p99_exception_cutoff"])
    assert regular["n_statistical_outlier"] == 0
    assert trusted_regular["renda"].max() == pytest.approx(100.0)


def test_p99_ties_at_cutoff_are_retained():
    values = np.array(list(range(1, 99)) + [100, 100], dtype=float)
    trusted, audit, _ = stage_02.trim_refined_year(_frame(1990, values), 1990, threshold=50.0)
    assert audit["p99_exception_cutoff"] == pytest.approx(100.0)
    assert audit["n_statistical_outlier"] == 0
    assert int((trusted["renda"] == 100.0).sum()) == 2


def test_stage03_marks_insufficient_pareto_tail_as_unsupported(monkeypatch):
    gompertz = {
        "gompertz_A": stage_03.GOMPERTZ_A_THEORY,
        "gompertz_B": 0.5,
        "gompertz_r2": 0.99,
        "gompertz_sse": 0.01,
        "gompertz_x_gmax": 2.0,
        "gompertz_point_n": 10,
        "gompertz_selection_status": "test",
        "gompertz_boundary_A_free": 1.52,
        "gompertz_boundary_B_free": 0.5,
        "gompertz_boundary_r2_free": 0.99,
    }
    monkeypatch.setattr(stage_03, "select_gompertz_region", lambda curve: gompertz)

    def _raise(*args, **kwargs):
        raise ValueError("Insufficient Pareto-tail points.")

    monkeypatch.setattr(stage_03, "select_pareto_region", _raise)
    fit, curve = stage_03.fit_year_regime(1990, np.geomspace(0.1, 3.0, 100), 1.0)

    assert fit["pareto_selection_status"] == "unsupported_insufficient_tail_points"
    assert np.isnan(fit["transition_x_t"])
    assert np.isnan(fit["pareto_alpha_mle"])
    assert curve["pareto_fitted_ccdf_percent_mle"].isna().all()
    assert set(curve["regime"]) == {"gompertz_body"}


def test_stage03_inequality_grid_does_not_interpolate_missing_years():
    source = inspect.getsource(stage_03.plot_inequality_indices_grid)
    assert ".interpolate(" not in source
    assert ".reindex(" in source


def test_stage05_annual_plot_frame_preserves_missing_years_as_nan():
    source = pd.DataFrame({"year": [1985, 1987], "Gini": [0.55, 0.57]})
    plotted = stage_05.annual_plot_frame(source).set_index("year")
    assert plotted.loc[1985, "Gini"] == pytest.approx(0.55)
    assert np.isnan(plotted.loc[1986, "Gini"])
    assert plotted.loc[1987, "Gini"] == pytest.approx(0.57)


def test_analysis_workflow_contains_no_runtime_pareto_monkeypatch():
    workflow = Path(".github/workflows/run_analysis.yml").read_text(encoding="utf-8")
    assert "MIN_PARETO_POINTS = 4" not in workflow
    assert "fit_year_regime_with_p99_fallback" not in workflow
    assert "python src/stage_03_pnad_analysis.py" in workflow


def test_stage03_source_contains_no_disallowed_control_characters():
    source_text = Path("src/stage_03_pnad_analysis.py").read_text(encoding="utf-8")
    controls = [
        ch for ch in source_text
        if ord(ch) < 32 and ch not in {"\n", "\r", "\t"}
    ]
    assert controls == []
