from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_00_build_metadata as stage_00


def test_specs_cover_full_period_and_validate_available_years():
    specs = stage_00.build_specs_pnad_df()

    assert specs["ano"].tolist() == list(range(1976, 2026))
    assert specs["ano"].is_unique

    available = specs[specs["pos_renda"].notna()]
    assert (available["raw_pattern"].astype(str).str.len() > 0).all()
    assert (available["n_files"] > 0).all()
    assert available["missing_renda"].notna().all()

    multi_file = available.set_index("ano").loc[[1983, 1988]]
    assert (multi_file["n_files"] == 8).all()
    assert multi_file.loc[1983, "raw_subdir"] == "1983"
    assert multi_file.loc[1988, "raw_subdir"] == "1988"


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
    assert {"Currency", "Exchange", "Index", "Inflation"}.issubset(metadata.columns)


def test_save_metadata_roundtrip(tmp_path):
    metadata = stage_00.build_metadata_df()
    output = tmp_path / "df_metadata.xlsx"

    saved = stage_00.save_metadata(metadata, output)
    restored = pd.read_excel(saved)

    assert saved == output
    assert restored["ano"].tolist() == metadata["ano"].tolist()
    assert list(restored.columns) == list(metadata.columns)
