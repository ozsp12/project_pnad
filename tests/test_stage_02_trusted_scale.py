from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import trusted_input as stage_02_scale


def test_load_trusted_scale_divisors_reads_2017_metadata(tmp_path):
    metadata = pd.DataFrame(
        {
            "ano": [2016, 2017, 2018],
            "income_scale_divisor": [1.0, 100.0, 1.0],
        }
    )
    path = tmp_path / "metadata.csv"
    metadata.to_csv(path, index=False)

    divisors = stage_02_scale.load_trusted_scale_divisors(path)

    assert divisors == {2017: 100.0}


def test_correct_frame_for_trusted_scales_2017_only_and_keeps_sentinel():
    frame = pd.DataFrame(
        {
            "ano": [2017, 2017, 2017],
            "renda": [65_030.0, 106_447.0, 999_999.0],
        }
    )

    corrected = stage_02_scale.correct_frame_for_trusted(frame, 2017, 100.0)

    assert frame["renda"].tolist() == [65_030.0, 106_447.0, 999_999.0]
    assert corrected["renda"].tolist() == pytest.approx([650.30, 1064.47, 999_999.0])


def test_correct_frame_for_trusted_refuses_double_correction():
    frame = pd.DataFrame(
        {
            "ano": [2017, 2017],
            "renda": [650.30, 1064.47],
        }
    )

    with pytest.raises(RuntimeError, match="refusing to divide twice"):
        stage_02_scale.correct_frame_for_trusted(frame, 2017, 100.0)


def test_correct_frame_for_trusted_identity_divisor_returns_copy():
    frame = pd.DataFrame({"ano": [2018], "renda": [1000.0]})

    corrected = stage_02_scale.correct_frame_for_trusted(frame, 2018, 1.0)

    assert corrected.equals(frame)
    assert corrected is not frame
