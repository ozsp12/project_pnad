from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import paper_tables


def test_band_record_is_nonoverlapping_summary():
    values = np.array([90.0, 95.0, 99.0])
    record = paper_tables._band_record(values, total_income=1000.0, prefix="p90_p99")

    assert record["p90_p99_population_n"] == 3
    assert record["p90_p99_income_share_pct"] == pytest.approx(28.4)
    assert record["p90_p99_mean_income_2025_usd"] == pytest.approx(values.mean())
    assert record["p90_p99_median_income_2025_usd"] == pytest.approx(np.median(values))
    assert record["p90_p99_std_income_2025_usd"] == pytest.approx(np.std(values, ddof=1))


def test_metadata_table_documents_every_canonical_data_column():
    gompertz = pd.DataFrame(
        columns=[
            "year", "gompertz_A", "gompertz_A_bootstrap_se", "gompertz_B",
            "gompertz_B_bootstrap_se", "gompertz_x_gmax", "transition_x_t",
            "gompertz_r2", "gompertz_correlation_coefficient",
            "gompertz_population_pct", "gompertz_income_share_pct", "bootstrap_reps",
        ]
    )
    pareto = pd.DataFrame(
        columns=[
            "year", "pareto_x_pmin", "transition_x_t", "transition_delta_x_t",
            "pareto_alpha_ls", "pareto_alpha_ls_bootstrap_se", "pareto_beta_ls",
            "pareto_beta_ls_bootstrap_se", "pareto_ls_r2",
            "pareto_ls_correlation_coefficient", "pareto_alpha_mle",
            "pareto_alpha_mle_fisher_se", "pareto_alpha_mle_bootstrap_se",
            "pareto_beta_mle_continuity", "pareto_beta_mle_bootstrap_se",
            "pareto_mle_r2", "pareto_mle_correlation_coefficient",
            "pareto_population_pct", "pareto_income_share_pct", "bootstrap_reps",
        ]
    )
    economic = pd.DataFrame(
        columns=[
            "year", "gdp_growth_pct", "income_observation_n", "income_mean_2025_usd",
            "income_median_2025_usd", "income_std_2025_usd", "gini_pnad",
            "pietra_pnad", "kolkata_pnad", "zanardi_pnad", "gini_ipea",
            "gini_world_bank", "p90_p99_population_n", "p90_p99_income_share_pct",
            "p90_p99_mean_income_2025_usd", "p90_p99_median_income_2025_usd",
            "p90_p99_std_income_2025_usd", "p99_p999_population_n",
            "p99_p999_income_share_pct", "p99_p999_mean_income_2025_usd",
            "p99_p999_median_income_2025_usd", "p99_p999_std_income_2025_usd",
            "p999_p100_population_n", "p999_p100_income_share_pct",
            "p999_p100_mean_income_2025_usd", "p999_p100_median_income_2025_usd",
            "p999_p100_std_income_2025_usd",
        ]
    )
    tables = {
        paper_tables.GOMPERTZ_OUT.name: gompertz,
        paper_tables.PARETO_OUT.name: pareto,
        paper_tables.ECONOMIC_OUT.name: economic,
    }

    metadata = paper_tables.build_metadata_table(tables)
    documented = set(zip(metadata["table_name"], metadata["column_name"]))

    for table_name, frame in tables.items():
        assert all((table_name, column) in documented for column in frame.columns)
    assert {"description", "unit", "source"}.issubset(metadata.columns)


def test_clean_paper_csvs_removes_legacy_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(paper_tables, "TABLES_PAPER", tmp_path)
    (tmp_path / ".gitkeep").write_text("")
    (tmp_path / "moura_ribeiro_2009_table.csv").write_text("year\n1978\n")
    (tmp_path / "table_01_gompertz_annual.csv").write_text("year\n1978\n")

    paper_tables._clean_paper_csvs()

    assert sorted(path.name for path in tmp_path.iterdir()) == [".gitkeep"]
