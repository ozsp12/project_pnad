from pathlib import Path
import sys

import pandas as pd
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_04_build_analytic_pnad as stage_04


def write_layer(folder, layer, year, incomes):
    pd.DataFrame(
        {
            "renda": pd.Series(incomes, dtype="float64"),
            "ano": pd.Series([year] * len(incomes), dtype="int64"),
        }
    ).to_parquet(folder / f"pnad_{layer}_{year}.parquet", index=False)


def test_build_layer_product_preserves_values_order_and_schema(tmp_path):
    refined = tmp_path / "refined"
    refined.mkdir()
    write_layer(refined, "refined", 2002, [30.0, 40.0])
    write_layer(refined, "refined", 2000, [10.0, 20.0])

    output = tmp_path / "analytics" / "pnad_refined_all.parquet"
    metadata = tmp_path / "analytics" / "pnad_refined_all_metadata.csv"
    summary = stage_04.build_layer_product(
        layer="refined",
        input_path=refined,
        output_path=output,
        metadata_path=metadata,
    )
    result = pd.read_parquet(output)

    assert result.columns.tolist() == ["renda", "ano"]
    assert result["ano"].tolist() == [2000, 2000, 2002, 2002]
    assert result["renda"].tolist() == [10.0, 20.0, 30.0, 40.0]
    assert str(result["renda"].dtype) == "float64"
    assert str(result["ano"].dtype) == "int64"
    assert summary["n_years"] == 2
    assert summary["n_rows"] == 4

    parquet = pq.ParquetFile(output)
    assert parquet.metadata.num_row_groups == 2


def test_metadata_csv_documents_dataset_and_schema(tmp_path):
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    write_layer(trusted, "trusted", 2017, [650.0, 1064.0])
    write_layer(trusted, "trusted", 2018, [692.0])

    output = tmp_path / "analytics" / "pnad_trusted_all.parquet"
    metadata_path = tmp_path / "analytics" / "pnad_trusted_all_metadata.csv"
    stage_04.build_layer_product(
        layer="trusted",
        input_path=trusted,
        output_path=output,
        metadata_path=metadata_path,
    )

    metadata = pd.read_csv(metadata_path)
    assert set(metadata["column_name"]) == {"renda", "ano"}
    assert set(metadata["layer"]) == {"trusted"}
    assert set(metadata["processing_level"]) == {"validated benchmark"}
    assert set(metadata["parquet_file"]) == {"pnad_trusted_all.parquet"}
    assert set(metadata["schema_version"].astype(str)) == {"1.0"}
    assert set(metadata["n_rows"]) == {3}
    assert set(metadata["n_years"]) == {2}
    assert set(metadata["first_year"]) == {2017}
    assert set(metadata["last_year"]) == {2018}
    assert set(metadata["n_row_groups"]) == {2}
    assert set(metadata["observed_null_count"]) == {0}
    assert metadata["description"].notna().all()
    assert metadata["unit"].notna().all()
    assert metadata["arrow_type"].notna().all()


def test_build_analytics_products_writes_refined_and_trusted_and_removes_legacy(
    tmp_path, monkeypatch
):
    refined = tmp_path / "refined"
    trusted = tmp_path / "trusted"
    analytics = tmp_path / "analytics"
    refined.mkdir()
    trusted.mkdir()
    analytics.mkdir()

    write_layer(refined, "refined", 2017, [650.0, 1064.0, 150000.0])
    write_layer(trusted, "trusted", 2017, [650.0, 1064.0])

    refined_output = analytics / "pnad_refined_all.parquet"
    trusted_output = analytics / "pnad_trusted_all.parquet"
    refined_metadata = analytics / "pnad_refined_all_metadata.csv"
    trusted_metadata = analytics / "pnad_trusted_all_metadata.csv"
    legacy = analytics / "pnad_analytics_all.parquet"
    legacy.write_bytes(b"legacy")

    monkeypatch.setitem(stage_04.LAYER_CONFIG["refined"], "input_path", refined)
    monkeypatch.setitem(stage_04.LAYER_CONFIG["refined"], "output_path", refined_output)
    monkeypatch.setitem(stage_04.LAYER_CONFIG["refined"], "metadata_path", refined_metadata)
    monkeypatch.setitem(stage_04.LAYER_CONFIG["trusted"], "input_path", trusted)
    monkeypatch.setitem(stage_04.LAYER_CONFIG["trusted"], "output_path", trusted_output)
    monkeypatch.setitem(stage_04.LAYER_CONFIG["trusted"], "metadata_path", trusted_metadata)
    monkeypatch.setattr(stage_04, "LEGACY_OUTPUT_PATH", legacy)

    summaries = stage_04.build_analytics_products()

    assert set(summaries) == {"refined", "trusted"}
    assert refined_output.is_file()
    assert trusted_output.is_file()
    assert refined_metadata.is_file()
    assert trusted_metadata.is_file()
    assert not legacy.exists()

    assert pd.read_parquet(refined_output)["renda"].tolist() == [650.0, 1064.0, 150000.0]
    assert pd.read_parquet(trusted_output)["renda"].tolist() == [650.0, 1064.0]


def test_validate_layer_frame_rejects_inconsistent_year():
    frame = pd.DataFrame({"renda": [10.0, 20.0], "ano": [2000, 2001]})

    with pytest.raises(ValueError, match="inconsistent values"):
        stage_04.validate_layer_frame(frame, 2000, "refined")


def test_validate_layer_frame_rejects_negative_income():
    frame = pd.DataFrame({"renda": [10.0, -1.0], "ano": [2000, 2000]})

    with pytest.raises(ValueError, match="negative"):
        stage_04.validate_layer_frame(frame, 2000, "trusted")


def test_build_layer_product_rejects_schema_mismatch(tmp_path):
    refined = tmp_path / "refined"
    refined.mkdir()
    write_layer(refined, "refined", 2000, [10.0])
    pd.DataFrame(
        {"renda": [20.0], "ano": [2001], "extra": [1]}
    ).to_parquet(refined / "pnad_refined_2001.parquet", index=False)

    with pytest.raises(ValueError, match="schema columns differ"):
        stage_04.build_layer_product(
            layer="refined",
            input_path=refined,
            output_path=tmp_path / "out.parquet",
            metadata_path=tmp_path / "out_metadata.csv",
        )
