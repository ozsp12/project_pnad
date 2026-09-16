"""Prepare trusted-layer inputs without modifying persisted refined data.

The persisted refined layer is intentionally preserved as-is. For 2017 only,
Stage 02 applies the canonical ``income_scale_divisor`` from Stage-00 metadata
to a temporary copy before the trusted upper-tail treatment is executed.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from src import stage_02_build_trusted_pnad as stage_02


REPO_ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = REPO_ROOT / "data" / "metadata" / "df_metadata.csv"
TRUSTED_SCALE_YEARS = frozenset({2017})
ALREADY_CORRECTED_MEDIAN_GUARD = 10_000.0


def load_trusted_scale_divisors(metadata_path: Path = METADATA_PATH) -> dict[int, float]:
    """Load positive scale divisors for years normalized in the trusted layer."""
    metadata = pd.read_csv(metadata_path)
    required = {"ano", "income_scale_divisor"}
    missing = required.difference(metadata.columns)
    if missing:
        raise ValueError(
            "Metadata missing trusted-scale columns: " + ", ".join(sorted(missing))
        )
    if not metadata["ano"].is_unique:
        raise ValueError("Metadata contains duplicated years.")

    indexed = metadata.set_index("ano")
    divisors: dict[int, float] = {}
    for year in TRUSTED_SCALE_YEARS:
        if year not in indexed.index:
            raise ValueError(f"Metadata does not contain year {year}.")
        divisor = float(indexed.loc[year, "income_scale_divisor"])
        if not np.isfinite(divisor) or divisor <= 0:
            raise ValueError(f"Invalid income_scale_divisor for {year}: {divisor}")
        divisors[year] = divisor
    return divisors


def correct_frame_for_trusted(
    frame: pd.DataFrame,
    year: int,
    divisor: float,
) -> pd.DataFrame:
    """Return a trusted-input copy with the year-specific scale correction."""
    if "renda" not in frame.columns:
        raise ValueError(f"{year}: refined dataset is missing column 'renda'.")
    if not np.isfinite(divisor) or divisor <= 0:
        raise ValueError(f"{year}: invalid trusted scale divisor {divisor}.")
    if divisor == 1.0:
        return frame.copy()

    income = pd.to_numeric(frame["renda"], errors="coerce").to_numpy(float)
    finite = np.isfinite(income)
    sentinel = finite & np.isin(income, stage_02.INCOME_SENTINELS)
    eligible = finite & (income >= 0) & ~sentinel

    if not eligible.any():
        raise ValueError(f"{year}: no valid income values available for scale correction.")

    median_before = float(np.median(income[eligible]))
    if year == 2017 and median_before < ALREADY_CORRECTED_MEDIAN_GUARD:
        raise RuntimeError(
            "2017 refined income already appears scale-corrected; refusing to divide twice."
        )

    corrected = frame.copy()
    corrected_values = income.copy()
    corrected_values[eligible] = corrected_values[eligible] / divisor
    corrected["renda"] = corrected_values
    return corrected


def build_trusted_from_persisted_refined(
    refined_path: Path = stage_02.REFINED_PATH,
    trusted_path: Path = stage_02.TRUSTED_PATH,
    tables_path: Path = stage_02.VALIDATION_TABLES_PATH,
    metadata_path: Path = METADATA_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build trusted data using temporary trusted-only scale normalization."""
    refined_path = Path(refined_path)
    trusted_path = Path(trusted_path)
    tables_path = Path(tables_path)
    divisors = load_trusted_scale_divisors(Path(metadata_path))
    files = stage_02.discover_refined_files(refined_path)

    with TemporaryDirectory(prefix="pnad_trusted_input_") as tmp:
        temporary_refined = Path(tmp)

        for year, source in files.items():
            target = temporary_refined / source.name
            if year not in divisors or divisors[year] == 1.0:
                target.symlink_to(source.resolve())
                continue

            frame = pd.read_parquet(source, engine=stage_02.PARQUET_ENGINE)
            corrected = correct_frame_for_trusted(frame, year, divisors[year])
            corrected.to_parquet(
                target,
                index=False,
                engine=stage_02.PARQUET_ENGINE,
                compression=stage_02.PARQUET_COMPRESSION,
            )

        audit, tests = stage_02.build_trusted_datasets(
            refined_path=temporary_refined,
            trusted_path=trusted_path,
            tables_path=tables_path,
        )

    audit["trusted_input_scale_divisor"] = audit["year"].map(
        lambda year: divisors.get(int(year), 1.0)
    )
    audit["trusted_input_scale_applied"] = audit["year"].map(
        lambda year: int(year) in divisors and divisors[int(year)] != 1.0
    )
    audit.to_csv(tables_path / stage_02.AUDIT_FILE.name, index=False)
    return audit, tests


def main() -> tuple[pd.DataFrame, pd.DataFrame]:
    return build_trusted_from_persisted_refined()


if __name__ == "__main__":
    audit, tests = main()
    row_2017 = audit.loc[audit["year"] == 2017]
    if not row_2017.empty:
        print(
            row_2017[
                [
                    "year",
                    "trusted_input_scale_divisor",
                    "trusted_input_scale_applied",
                    "trusted_median",
                    "trusted_mean",
                ]
            ].to_string(index=False)
        )
    print(f"Validated annual distributions: {int(tests['all_tests_pass'].sum())}/{len(tests)}")
