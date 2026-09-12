from pathlib import Path
from types import SimpleNamespace
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_01_build_refined_pnad as stage_01


def complete_metadata_row(year=2025):
    return {
        "ano": year,
        "pos_renda": 0,
        "tam_renda": 4,
        "pos_morador": 4,
        "tam_morador": 2,
        "missing_renda": 9999,
        "raw_subdir": "",
        "raw_pattern": "sample.dat",
        "n_files": 1,
    }


def test_load_metadata_rejects_duplicate_years(tmp_path):
    frame = pd.DataFrame([complete_metadata_row(), complete_metadata_row()])
    path = tmp_path / "metadata.xlsx"
    frame.to_excel(path, index=False)

    with pytest.raises(ValueError, match="duplicated years"):
        stage_01.load_metadata(path)


def test_get_available_specs_filters_incomplete_rows():
    complete = complete_metadata_row(2025)
    incomplete = complete_metadata_row(2024)
    incomplete["raw_pattern"] = ""
    unavailable = complete_metadata_row(2023)
    unavailable["pos_renda"] = None

    available = stage_01.get_available_specs(
        pd.DataFrame([incomplete, complete, unavailable])
    )

    assert available["ano"].tolist() == [2025]


def test_get_source_files_requires_declared_file_count(tmp_path):
    (tmp_path / "sample_a.dat").write_bytes(b"0001\n")
    (tmp_path / "sample_b.dat").write_bytes(b"0002\n")
    spec = SimpleNamespace(
        ano=2025,
        raw_subdir="",
        raw_pattern="sample_*.dat",
        n_files=1,
    )

    with pytest.raises(RuntimeError, match="Expected 1 file"):
        stage_01.get_source_files(spec, raw_path=tmp_path)


def test_read_year_fast_parses_per_capita_income_and_audit_counts(tmp_path):
    raw = tmp_path / "sample.dat"
    raw.write_bytes(
        b"001002\n"  # income 10, 2 residents -> 5
        b"002004\n"  # income 20, 4 residents -> 5
        b"999902\n"  # declared missing-income sentinel
        b"abcd02\n"  # invalid income field
        b"003000\n"  # invalid resident count
    )
    spec = SimpleNamespace(
        ano=2025,
        raw_subdir="",
        raw_pattern="sample.dat",
        n_files=1,
        pos_renda=0,
        tam_renda=4,
        missing_renda=9999,
        pos_morador=4,
        tam_morador=2,
    )

    refined, stats = stage_01.read_year_fast(
        spec,
        raw_path=tmp_path,
        show_file_progress=False,
    )

    assert refined["renda"].tolist() == [5.0, 5.0]
    assert refined["ano"].tolist() == [2025, 2025]
    assert stats["arquivos"] == 1
    assert stats["n_raw"] == 5
    assert stats["n_refined"] == 2
    assert stats["n_missing_renda"] == 1
    assert stats["n_invalid_renda"] == 1
    assert stats["n_invalid_morador"] == 1
    assert stats["per_capita"] is True
