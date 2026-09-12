from pathlib import Path
import sys

import pandas as pd
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_04_build_analytic_pnad as stage_04


def write_trusted(path, year, incomes):
    pd.DataFrame({"renda": incomes, "ano": year}).to_parquet(path, index=False)


def test_build_analytics_parquet_concatenates_years_in_order(tmp_path):
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    write_trusted(trusted / "pnad_trusted_2002.parquet", 2002, [30.0, 40.0])
    write_trusted(trusted / "pnad_trusted_2000.parquet", 2000, [10.0, 20.0])

    output = tmp_path / "analytics" / "pnad_analytics_all.parquet"
    summary = stage_04.build_analytics_parquet(trusted, output)
    result = pd.read_parquet(output)

    assert result.columns.tolist() == ["renda", "ano"]
    assert result["ano"].tolist() == [2000, 2000, 2002, 2002]
    assert result["renda"].tolist() == [10.0, 20.0, 30.0, 40.0]
    assert summary["n_years"] == 2
    assert summary["n_rows"] == 4

    parquet = pq.ParquetFile(output)
    assert parquet.metadata.num_row_groups == 2


def test_validate_trusted_frame_rejects_inconsistent_year():
    frame = pd.DataFrame({"renda": [10.0, 20.0], "ano": [2000, 2001]})

    with pytest.raises(ValueError, match="inconsistent values"):
        stage_04.validate_trusted_frame(frame, 2000)


def test_validate_trusted_frame_rejects_negative_income():
    frame = pd.DataFrame({"renda": [10.0, -1.0], "ano": [2000, 2000]})

    with pytest.raises(ValueError, match="negative"):
        stage_04.validate_trusted_frame(frame, 2000)
