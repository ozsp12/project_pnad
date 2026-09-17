from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src import stage_00_build_metadata as stage_00


STRING_COLUMNS = [
    "var_renda",
    "var_morador",
    "link",
    "raw_subdir",
    "raw_pattern",
    "Currency",
]


def normalize_metadata(frame):
    frame = frame.copy()
    for column in STRING_COLUMNS:
        frame[column] = frame[column].fillna("").astype(str)
    return frame


def test_specs_cover_full_period_and_validate_available_years():
    specs = stage_00.build_specs_pnad_df()

    assert specs["ano"].tolist() == list(range(1976, 2026))
    assert specs["ano"].is_unique

    available = specs[specs["pos_renda"].notna()]
    assert (available["raw_pattern"].astype(str).str.len() > 0).all()
    assert (available["n_files"] > 0).all()
    assert available["missing_renda"].notna().all()
    assert available["income_scale_divisor"].notna().all()
    assert (available["income_scale_divisor"] > 0).all()

    multi_file = available.set_index("ano").loc[[1983, 1988]]
    assert (multi_file["n_files"] == 8).all()
    assert multi_file.loc[1983, "raw_subdir"] == "1983"
    assert multi_file.loc[1988, "raw_subdir"] == "1988"


def test_specs_preserve_validated_income_fields():
    specs = stage_00.build_specs_pnad_df().set_index("ano")

    assert specs.loc[1989, "var_renda"] == "V5010"
    assert specs.loc[1989, "pos_renda"] == 249
    assert specs.loc[1989, "tam_renda"] == 9

    expected_continua_positions = {
        2016: 671,
        2017: 674,
        2018: 676,
        2019: 679,
        2020: 605,
        2021: 605,
        2022: 673,
        2023: 673,
        2024: 673,
        2025: 666,
    }
    for year, position in expected_continua_positions.items():
        assert specs.loc[year, "var_renda"] == "VD5008"
        assert specs.loc[year, "pos_renda"] == position
        assert specs.loc[year, "tam_renda"] == 8
        assert specs.loc[year, "missing_renda"] == 999_999
        assert specs.loc[year, "income_scale_divisor"] == pytest.approx(1.0)


def test_currency_metadata_is_normalized_to_2025():
    currency = stage_00.build_currency_df()

    assert currency["Year"].tolist() == list(range(1976, 2026))
    assert currency["Year"].is_unique

    row_2025 = currency.set_index("Year").loc[2025]
    assert row_2025["Inflation"] == pytest.approx(1.0)
    assert row_2025["Adjust2025"] == pytest.approx(0.0)

    finite = currency["Index"].notna()
    assert np.isfinite(currency.loc[finite, "Inflation"]).all()
    assert (currency.loc[finite, "Inflation"] > 0).all()


def test_metadata_merge_preserves_one_row_per_year():
    metadata = stage_00.build_metadata_df()

    assert metadata["ano"].tolist() == list(range(1976, 2026))
    assert metadata["ano"].is_unique
    assert {"Currency", "Exchange", "Index", "Inflation", "income_scale_divisor"}.issubset(metadata.columns)


def test_save_metadata_roundtrip(tmp_path):
    metadata = stage_00.build_metadata_df()
    output = tmp_path / "df_metadata.xlsx"
    csv_output = tmp_path / "df_metadata.csv"

    saved = stage_00.save_metadata(metadata, output)
    restored_xlsx = pd.read_excel(saved, dtype={"raw_subdir": "string"})
    restored_csv = pd.read_csv(csv_output, dtype={"raw_subdir": "string"})

    assert saved == output
    assert output.is_file()
    assert csv_output.is_file()
    assert restored_xlsx["ano"].tolist() == metadata["ano"].tolist()
    assert restored_csv["ano"].tolist() == metadata["ano"].tolist()
    assert list(restored_xlsx.columns) == list(metadata.columns)
    assert list(restored_csv.columns) == list(metadata.columns)


def test_persisted_metadata_artifacts_match_stage_00_builder():
    expected = normalize_metadata(stage_00.build_metadata_df())
    metadata_dir = REPO_ROOT / "data" / "metadata"

    persisted_csv = normalize_metadata(
        pd.read_csv(metadata_dir / "df_metadata.csv", dtype={"raw_subdir": "string"})
    )
    persisted_xlsx = normalize_metadata(
        pd.read_excel(metadata_dir / "df_metadata.xlsx", dtype={"raw_subdir": "string"})
    )

    assert_frame_equal(
        expected,
        persisted_csv,
        check_dtype=False,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    assert_frame_equal(
        expected,
        persisted_xlsx,
        check_dtype=False,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
