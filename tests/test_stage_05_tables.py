from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_05_tables as tables


def test_band_record_is_nonoverlapping_summary():
    values = np.array([90.0, 95.0, 99.0])
    record = tables._band_record(values, total=1000.0, prefix="p90_p99")
    assert record["p90_p99_population_n"] == 3
    assert record["p90_p99_income_share_pct"] == pytest.approx(28.4)
    assert record["p90_p99_mean_income_2025_usd"] == pytest.approx(values.mean())
    assert record["p90_p99_median_income_2025_usd"] == pytest.approx(np.median(values))


def test_gompertz_paper_schema_does_not_report_fixed_A_standard_error():
    annual = pd.DataFrame([{
        "year": 2005, "gompertz_A": 1.527, "gompertz_B": .34,
        "gompertz_boundary_A_free": 1.54, "gompertz_boundary_B_free": .33,
        "gompertz_x_gmax": 7.4, "transition_x_t": 7.4,
        "gompertz_r2": .99, "gompertz_population_pct": 98.8,
    }])
    bootstrap = pd.DataFrame([{
        "year": 2005, "bootstrap_reps": 1000, "gompertz_B_bootstrap_se": .01,
        "gompertz_A_free_bootstrap_se": .01, "gompertz_B_free_bootstrap_se": .01,
    }])
    regime = pd.DataFrame([{
        "year": 2005, "gompertz_income_share_pct": 86.2,
        "pareto_income_share_pct": 13.8,
    }])
    result = tables.build_gompertz_table(annual, bootstrap, regime)
    assert "gompertz_A_bootstrap_se" not in result.columns
    assert "gompertz_A_free_bootstrap_se" in result.columns


def test_metadata_table_documents_all_data_columns():
    evidence = pd.DataFrame(columns=[
        "year", "layer", "paper_table", "test", "estimator", "parameter",
        "estimate", "standard_error", "fit_metric", "fit_value", "criterion",
        "passed", "evidence_status", "paper_2009_value",
        "paper_2009_standard_error", "difference_from_2009",
        "relative_difference_pct", "within_paper_1se",
    ])
    metadata = tables.build_metadata_table({tables.EVIDENCE_OUT.name: evidence})
    documented = set(zip(metadata["table_name"], metadata["column_name"]))
    assert all((tables.EVIDENCE_OUT.name, c) in documented for c in evidence.columns)
    assert {"description", "unit", "source"}.issubset(metadata.columns)


def test_validate_tables_requires_both_evidence_layers():
    gompertz = pd.DataFrame({"year": [2005], "gompertz_income_share_pct": [86.0]})
    pareto = pd.DataFrame({"year": [2005], "pareto_income_share_pct": [14.0]})
    economic = pd.DataFrame({"year": [2005]})
    evidence = pd.DataFrame({
        "year": [2005], "layer": ["trusted"], "test": ["gompertz"],
        "estimator": ["free_lsf"], "parameter": ["A"], "estimate": [1.54],
        "criterion": ["test"], "evidence_status": ["supported"],
        "paper_2009_value": [1.54], "difference_from_2009": [0.0],
    })
    with pytest.raises(AssertionError, match="refined and trusted"):
        tables.validate_tables(gompertz, pareto, economic, evidence)
