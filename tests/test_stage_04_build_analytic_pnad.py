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


def write_annual_sources(tmp_path, years=(2017, 2018)):
    metadata = pd.DataFrame(
        {
            "ano": list(years),
            "var_renda": ["VD5008"] * len(years),
            "pos_renda": [674, 676][: len(years)],
            "tam_renda": [8] * len(years),
            "var_morador": [pd.NA] * len(years),
            "pos_morador": [pd.NA] * len(years),
            "tam_morador": [pd.NA] * len(years),
            "link": ["https://example.org/raw"] * len(years),
            "raw_subdir": [""] * len(years),
            "raw_pattern": [f"DOM{year}.*" for year in years],
            "n_files": [1] * len(years),
            "missing_renda": [999999] * len(years),
            "income_scale_divisor": [1.0] * len(years),
            "Currency": ["Real R$"] * len(years),
            "Exchange": [3.2, 3.6][: len(years)],
            "Index": [100.0, 103.0][: len(years)],
            "Adjust2025": [0.20, 0.15][: len(years)],
            "Inflation": [1.20, 1.15][: len(years)],
        }
    )
    metadata_path = tmp_path / "df_metadata.csv"
    metadata.to_csv(metadata_path, index=False)

    gini = pd.DataFrame(
        {
            "ano": list(years),
            "ipea": [0.539, 0.545][: len(years)],
            "banco_mundial": [0.533, 0.539][: len(years)],
        }
    )
    gini_path = tmp_path / "gini.csv"
    gini.to_csv(gini_path, index=False)

    audit = pd.DataFrame(
        {
            "year": list(years),
            "mad_consistency": [1.4826] * len(years),
            "threshold_k": [6.0] * len(years),
            "log_mad_cutoff": [200000.0, 210000.0][: len(years)],
            "p99_exception_quantile": [pd.NA] * len(years),
            "p99_exception_cutoff": [pd.NA] * len(years),
            "cutoff_rule": ["log_mad"] * len(years),
            "statistical_cutoff": [200000.0, 210000.0][: len(years)],
            "n_refined": [3, 2][: len(years)],
            "n_invalid_structural": [0] * len(years),
            "n_statistical_outlier": [0] * len(years),
            "n_removed_total": [0] * len(years),
            "n_trusted": [3, 2][: len(years)],
            "total_removal_rate": [0.0] * len(years),
        }
    )
    audit_path = tmp_path / "audit.csv"
    audit.to_csv(audit_path, index=False)
    return metadata_path, gini_path, audit_path


def test_build_layer_product_preserves_values_order_and_schema(tmp_path):
    refined = tmp_path / "refined"
    refined.mkdir()
    write_layer(refined, "refined", 2002, [30.0, 40.0])
    write_layer(refined, "refined", 2000, [10.0, 20.0])

    output = tmp_path / "analytics" / "pnad_refined_all.parquet"
    schema_path = tmp_path / "analytics" / "pnad_refined_all_schema.csv"
    summary = stage_04.build_layer_product(
        layer="refined",
        input_path=refined,
        output_path=output,
        schema_path=schema_path,
    )
    result = pd.read_parquet(output)

    assert result.columns.tolist() == ["renda", "ano"]
    assert result["ano"].tolist() == [2000, 2000, 2002, 2002]
    assert result["renda"].tolist() == [10.0, 20.0, 30.0, 40.0]
    assert str(result["renda"].dtype) == "float64"
    assert str(result["ano"].dtype) == "int64"
    assert summary["n_columns"] == 2
    assert summary["n_years"] == 2
    assert summary["n_rows"] == 4
    assert pq.ParquetFile(output).metadata.num_row_groups == 2


def test_schema_csv_is_variable_level_data_dictionary(tmp_path):
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    write_layer(trusted, "trusted", 2017, [650.0, 1064.0])
    write_layer(trusted, "trusted", 2018, [692.0])

    output = tmp_path / "analytics" / "pnad_trusted_all.parquet"
    schema_path = tmp_path / "analytics" / "pnad_trusted_all_schema.csv"
    stage_04.build_layer_product(
        layer="trusted",
        input_path=trusted,
        output_path=output,
        schema_path=schema_path,
    )

    schema = pd.read_csv(schema_path)
    required = {
        "layer",
        "schema_version",
        "column_name",
        "description",
        "logical_type",
        "storage_type",
        "unit",
        "source",
        "is_calculated",
        "calculation_stage",
        "calculation",
        "nullable",
        "storage_nullable",
        "n",
        "n_missing",
        "n_unique",
        "n_categories",
    }
    assert required.issubset(schema.columns)
    assert set(schema["column_name"]) == {"renda", "ano"}
    assert set(schema["layer"]) == {"trusted"}
    assert set(schema["n"]) == {3}
    assert set(schema["n_missing"]) == {0}
    assert schema.set_index("column_name").loc["ano", "n_unique"] == 2
    assert schema.set_index("column_name").loc["renda", "n_unique"] == 3
    assert not schema["nullable"].any()


def test_build_annual_metadata_combines_processing_and_reference_data(tmp_path):
    metadata_path, gini_path, audit_path = write_annual_sources(tmp_path)
    output = tmp_path / "pnad_annual_metadata.csv"

    summary = stage_04.build_annual_metadata(
        years=[2017, 2018],
        metadata_source_path=metadata_path,
        gini_reference_path=gini_path,
        trusted_audit_path=audit_path,
        output_path=output,
    )
    annual = pd.read_csv(output)

    assert summary["n_years"] == 2
    assert annual["ano"].tolist() == [2017, 2018]
    assert set(annual["survey"]) == {"PNAD Continua"}
    assert annual.loc[annual["ano"] == 2017, "income_position"].iloc[0] == 674
    assert set(annual["currency"]) == {"Real R$"}
    assert set(annual["gini_reference_role"]) == {"external validation only"}
    assert annual["gini_ipea"].notna().all()
    assert annual["gini_world_bank"].notna().all()
    assert set(annual["trusted_cutoff_rule"]) == {"log_mad"}
    assert set(annual["trusted_mad_k"]) == {6.0}
    assert "adjusted_income_formula" in annual.columns
    assert "income_construction" in annual.columns
    assert set(annual["exchange_source"]) == {stage_04.EXCHANGE_SOURCE}
    assert set(annual["price_index_source"]) == {stage_04.PRICE_INDEX_SOURCE}
    assert set(annual["monetary_provenance"]) == {stage_04.MONETARY_PROVENANCE}
    assert not annual["monetary_provenance"].str.contains("not yet recorded").any()


def test_build_datasets_metadata_describes_each_parquet(tmp_path, monkeypatch):
    analytics = tmp_path / "analytics"
    refined = tmp_path / "refined"
    trusted = tmp_path / "trusted"
    analytics.mkdir()
    refined.mkdir()
    trusted.mkdir()

    write_layer(refined, "refined", 2017, [650.0, 1064.0])
    write_layer(trusted, "trusted", 2017, [650.0])

    refined_output = analytics / "pnad_refined_all.parquet"
    trusted_output = analytics / "pnad_trusted_all.parquet"
    refined_schema = analytics / "pnad_refined_all_schema.csv"
    trusted_schema = analytics / "pnad_trusted_all_schema.csv"

    refined_summary = stage_04.build_layer_product(
        layer="refined",
        input_path=refined,
        output_path=refined_output,
        schema_path=refined_schema,
    )
    trusted_summary = stage_04.build_layer_product(
        layer="trusted",
        input_path=trusted,
        output_path=trusted_output,
        schema_path=trusted_schema,
    )

    output = analytics / "pnad_datasets_metadata.csv"
    monkeypatch.setattr(stage_04, "ANNUAL_METADATA_PATH", analytics / "pnad_annual_metadata.csv")
    summary = stage_04.build_datasets_metadata(
        {"refined": refined_summary, "trusted": trusted_summary}, output
    )
    metadata = pd.read_csv(output)

    assert summary["n_datasets"] == 2
    assert metadata["layer"].tolist() == ["refined", "trusted"]
    assert metadata["dataset_name"].tolist() == [
        "pnad_refined_all",
        "pnad_trusted_all",
    ]
    assert metadata["n_columns"].tolist() == [2, 2]
    assert metadata["n_years"].tolist() == [1, 1]
    assert metadata["n_row_groups"].tolist() == [1, 1]
    assert set(metadata["compression"]) == {"snappy"}
    assert (metadata["file_size_bytes"] > 0).all()
    assert set(metadata["schema_version"].astype(str)) == {"1.0"}
    assert set(metadata["record_weighting"]) == {
        "equal observation weights; survey expansion weights are not included"
    }


def test_build_analytics_products_writes_new_contract_and_removes_legacy(
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
    metadata_path, gini_path, audit_path = write_annual_sources(tmp_path, years=(2017,))

    refined_output = analytics / "pnad_refined_all.parquet"
    trusted_output = analytics / "pnad_trusted_all.parquet"
    refined_schema = analytics / "pnad_refined_all_schema.csv"
    trusted_schema = analytics / "pnad_trusted_all_schema.csv"
    annual_metadata = analytics / "pnad_annual_metadata.csv"
    datasets_metadata = analytics / "pnad_datasets_metadata.csv"
    legacy = analytics / "pnad_analytics_all.parquet"
    old_refined_metadata = analytics / "pnad_refined_all_metadata.csv"
    old_trusted_metadata = analytics / "pnad_trusted_all_metadata.csv"
    legacy.write_bytes(b"legacy")
    old_refined_metadata.write_text("legacy")
    old_trusted_metadata.write_text("legacy")

    monkeypatch.setitem(stage_04.LAYER_CONFIG["refined"], "input_path", refined)
    monkeypatch.setitem(stage_04.LAYER_CONFIG["refined"], "output_path", refined_output)
    monkeypatch.setitem(stage_04.LAYER_CONFIG["refined"], "schema_path", refined_schema)
    monkeypatch.setitem(stage_04.LAYER_CONFIG["trusted"], "input_path", trusted)
    monkeypatch.setitem(stage_04.LAYER_CONFIG["trusted"], "output_path", trusted_output)
    monkeypatch.setitem(stage_04.LAYER_CONFIG["trusted"], "schema_path", trusted_schema)
    monkeypatch.setattr(stage_04, "METADATA_SOURCE_PATH", metadata_path)
    monkeypatch.setattr(stage_04, "GINI_REFERENCE_PATH", gini_path)
    monkeypatch.setattr(stage_04, "TRUSTED_AUDIT_PATH", audit_path)
    monkeypatch.setattr(stage_04, "ANNUAL_METADATA_PATH", annual_metadata)
    monkeypatch.setattr(stage_04, "DATASETS_METADATA_PATH", datasets_metadata)
    monkeypatch.setattr(stage_04, "LEGACY_OUTPUT_PATH", legacy)
    monkeypatch.setattr(
        stage_04,
        "LEGACY_METADATA_PATHS",
        (old_refined_metadata, old_trusted_metadata),
    )

    summaries = stage_04.build_analytics_products()

    assert set(summaries) == {"refined", "trusted"}
    assert refined_output.is_file()
    assert trusted_output.is_file()
    assert refined_schema.is_file()
    assert trusted_schema.is_file()
    assert annual_metadata.is_file()
    assert datasets_metadata.is_file()
    assert not legacy.exists()
    assert not old_refined_metadata.exists()
    assert not old_trusted_metadata.exists()
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
            schema_path=tmp_path / "out_schema.csv",
        )
