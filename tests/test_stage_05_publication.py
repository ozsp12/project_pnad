from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_05_publication as publication
from src import stage_03_pnad_analysis as analysis


def test_exclusive_income_statistics_are_computed_in_stage03():
    values = range(1, 1001)
    record = analysis.compute_exclusive_income_statistics(values)
    assert record["income_observation_n"] == 1000
    assert record["p90_p99_population_n"] == 90
    assert record["p99_p999_population_n"] == 9
    assert record["p999_p100_population_n"] == 1


def test_gompertz_paper_schema_does_not_report_fixed_A_standard_error_or_correlation_proxy():
    annual = pd.DataFrame([{
        "year": 2005,
        "gompertz_A": 1.527,
        "gompertz_B": .34,
        "gompertz_B_bootstrap_se": .01,
        "gompertz_boundary_A_free": 1.54,
        "gompertz_A_free_bootstrap_se": .01,
        "gompertz_boundary_B_free": .33,
        "gompertz_B_free_bootstrap_se": .01,
        "gompertz_x_gmax": 7.4,
        "transition_x_t": 7.4,
        "gompertz_r2": .99,
        "gompertz_population_pct": 98.8,
        "gompertz_income_share_pct": 86.2,
        "bootstrap_reps": 1000,
    }])
    result = publication.build_gompertz_table(annual)
    assert "gompertz_A_bootstrap_se" not in result.columns
    assert "gompertz_A_free_bootstrap_se" in result.columns
    assert "gompertz_correlation_coefficient" not in result.columns


def test_metadata_table_documents_all_data_columns_and_tables():
    gompertz = pd.DataFrame(columns=["year", "gompertz_A", "gompertz_B"])
    metadata = publication.build_metadata_table({publication.GOMPERTZ_OUT.name: gompertz})
    documented = set(zip(metadata["table_name"], metadata["column_name"]))
    assert all((publication.GOMPERTZ_OUT.name, c) in documented for c in gompertz.columns)
    assert {
        "table_name", "table_description", "column_name", "description", "unit", "source"
    }.issubset(metadata.columns)
    descriptions = metadata.loc[
        metadata["table_name"] == publication.GOMPERTZ_OUT.name, "table_description"
    ]
    assert descriptions.notna().all()
    assert descriptions.str.len().gt(0).all()


def test_validate_tables_rejects_inconsistent_regime_shares():
    gompertz = pd.DataFrame({"year": [2005], "gompertz_income_share_pct": [86.0]})
    pareto = pd.DataFrame({"year": [2005], "pareto_income_share_pct": [13.0]})
    economic = pd.DataFrame({"year": [2005]})
    with pytest.raises(AssertionError, match="sum to 100%"):
        publication.validate_tables(gompertz, pareto, economic)
