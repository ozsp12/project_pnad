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


def test_metadata_table_documents_all_data_columns_and_tables():
    gompertz = pd.DataFrame(columns=["year", "gompertz_A", "gompertz_B"])
    metadata = tables.build_metadata_table({tables.GOMPERTZ_OUT.name: gompertz})
    documented = set(zip(metadata["table_name"], metadata["column_name"]))
    assert all((tables.GOMPERTZ_OUT.name, c) in documented for c in gompertz.columns)
    assert {
        "table_name", "table_description", "column_name", "description", "unit", "source"
    }.issubset(metadata.columns)
    descriptions = metadata.loc[
        metadata["table_name"] == tables.GOMPERTZ_OUT.name, "table_description"
    ]
    assert descriptions.notna().all()
    assert descriptions.str.len().gt(0).all()


def test_validate_tables_rejects_inconsistent_regime_shares():
    gompertz = pd.DataFrame({"year": [2005], "gompertz_income_share_pct": [86.0]})
    pareto = pd.DataFrame({"year": [2005], "pareto_income_share_pct": [13.0]})
    economic = pd.DataFrame({"year": [2005]})
    with pytest.raises(AssertionError, match="sum to 100%"):
        tables.validate_tables(gompertz, pareto, economic)
