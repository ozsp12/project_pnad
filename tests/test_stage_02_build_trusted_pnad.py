from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_02_build_trusted_pnad as stage_02


def test_compute_log_mad_threshold_matches_definition():
    income = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 8.0, 16.0])
    threshold = 2.5

    result = stage_02.compute_log_mad_threshold(income, threshold=threshold)

    z = np.log1p(income)
    center = np.median(z)
    mad = np.median(np.abs(z - center))
    dispersion = stage_02.MAD_CONSISTENCY * mad
    expected_cutoff = np.expm1(center + threshold * dispersion)

    assert result["dispersion_method"] == "scaled_mad"
    assert result["median_log1p"] == pytest.approx(center)
    assert result["mad_log1p"] == pytest.approx(mad)
    assert result["scaled_dispersion_log1p"] == pytest.approx(dispersion)
    assert result["statistical_cutoff"] == pytest.approx(expected_cutoff)


def test_compute_log_mad_threshold_uses_zero_dispersion_cutoff():
    income = np.array([5.0])

    result = stage_02.compute_log_mad_threshold(income)

    assert result["dispersion_method"] == "zero_dispersion"
    assert result["scaled_dispersion_log1p"] == pytest.approx(0.0)
    assert result["statistical_cutoff"] == pytest.approx(5.0)


def test_compute_log_mad_threshold_rejects_sentinel_values():
    income = np.array([1.0, 2.0, 999_999.0])

    with pytest.raises(ValueError, match="sentinel income values"):
        stage_02.compute_log_mad_threshold(income)


def test_trim_refined_year_accounts_for_invalids_and_tail_removal():
    year = 2025
    frame = pd.DataFrame(
        {
            "ano": [year] * 8,
            "renda": [0.0, 1.0, 2.0, 3.0, 1000.0, np.nan, np.inf, -1.0],
            "id": np.arange(8),
        }
    )

    trusted, audit, tests = stage_02.trim_refined_year(
        frame,
        year,
        threshold=1.0,
    )

    assert trusted["renda"].tolist() == [0.0, 1.0, 2.0, 3.0]
    assert audit["n_refined"] == 8
    assert audit["n_invalid_nan"] == 1
    assert audit["n_invalid_inf"] == 1
    assert audit["n_invalid_negative"] == 1
    assert audit["n_invalid_sentinel"] == 0
    assert audit["n_invalid_structural"] == 3
    assert audit["n_statistical_outlier"] == 1
    assert audit["n_removed_total"] == 4
    assert audit["n_trusted"] == 4
    assert audit["n_refined"] == audit["n_trusted"] + audit["n_removed_total"]
    assert trusted["renda"].max() <= audit["statistical_cutoff"]
    assert tests["test_count_identity"]
    assert tests["test_valid_input_no_sentinel"]
    assert tests["test_trusted_no_sentinel"]
    assert tests["test_trusted_finite"]
    assert tests["test_trusted_nonnegative"]
    assert tests["test_max_after_le_cutoff"]
    assert tests["all_tests_pass"]


def test_trim_refined_year_removes_all_global_sentinels_before_trimming():
    year = 2009
    frame = pd.DataFrame(
        {
            "ano": [year] * 7,
            "renda": [
                100.0,
                200.0,
                300.0,
                400.0,
                999_999.0,
                9_999_999.0,
                99_999_999.0,
            ],
        }
    )

    trusted, audit, tests = stage_02.trim_refined_year(
        frame,
        year,
        threshold=20.0,
    )

    assert trusted["renda"].tolist() == [100.0, 200.0, 300.0, 400.0]
    assert audit["n_invalid_sentinel"] == 3
    assert audit["n_invalid_sentinel_999999"] == 1
    assert audit["n_invalid_sentinel_9999999"] == 1
    assert audit["n_invalid_sentinel_99999999"] == 1
    assert audit["n_invalid_structural"] == 3
    assert audit["n_statistical_outlier"] == 0
    assert tests["input_n_sentinel"] == 3
    assert tests["n_invalid_sentinel"] == 3
    assert tests["test_valid_input_no_sentinel"]
    assert tests["test_trusted_no_sentinel"]
    assert tests["all_tests_pass"]


def test_trim_refined_year_rejects_inconsistent_year_column():
    frame = pd.DataFrame({"ano": [2024, 2025], "renda": [1.0, 2.0]})

    with pytest.raises(ValueError, match="inconsistent values in column 'ano'"):
        stage_02.trim_refined_year(frame, 2025)
