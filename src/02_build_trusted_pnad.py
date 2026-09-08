"""Build trusted annual PNAD datasets and audit each distribution.

Stage 02 reads the annual refined Parquet files created by
`01_build_refined_pnad.py`, applies the deterministic upper-tail log-MAD
rule used in the project notebook, validates the resulting annual
distributions, and writes both trusted datasets and analytical audit tables.

The statistical transformation is

    z_i = log(1 + x_i)
    m   = median(z_i)
    s   = 1.4826 * median(|z_i - m|)
    x_c = exp(m + k s) - 1

with k=6 by default. Only observations x_i > x_c are removed.
"""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
import re

import numpy as np
import pandas as pd
from tqdm.auto import tqdm


REPO_ROOT = Path(__file__).resolve().parents[1]
REFINED_PATH = REPO_ROOT / "data" / "refined"
TRUSTED_PATH = REPO_ROOT / "data" / "data_trusted"
TABLES_ANALYSIS_PATH = REPO_ROOT / "assets" / "tables_analysis"

REFINED_PATTERN = "pnad_refined_*.parquet"
MAD_CONSISTENCY = 1.4826
MAD_THRESHOLD = 6.0
PARQUET_ENGINE = "pyarrow"
PARQUET_COMPRESSION = "snappy"

AUDIT_FILE = TABLES_ANALYSIS_PATH / "02_build_trusted_pnad__trim_audit.csv"
TESTS_FILE = TABLES_ANALYSIS_PATH / "02_build_trusted_pnad__distribution_tests.csv"


def year_from_filename(path: Path) -> int:
    """Extract the four-digit year from a refined PNAD filename."""
    match = re.fullmatch(r"pnad_refined_(\d{4})", path.stem)
    if not match:
        raise ValueError(f"Invalid refined filename: {path.name}")
    return int(match.group(1))


def discover_refined_files(refined_path: Path = REFINED_PATH) -> dict[int, Path]:
    """Return annual refined Parquet files ordered by year."""
    files = {
        year_from_filename(path): path
        for path in refined_path.glob(REFINED_PATTERN)
        if path.is_file()
    }
    if not files:
        raise FileNotFoundError(
            f"No files matching '{REFINED_PATTERN}' were found in {refined_path}."
        )
    return dict(sorted(files.items()))


def _income_array(df: pd.DataFrame, year: int) -> np.ndarray:
    """Validate the structural assumptions and return income as float64."""
    required = {"renda", "ano"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(
            f"{year}: missing required columns: {', '.join(sorted(missing))}"
        )

    if len(df) == 0:
        raise ValueError(f"{year}: empty refined dataset.")

    year_values = pd.to_numeric(df["ano"], errors="coerce").to_numpy(float)
    if not np.isfinite(year_values).all():
        raise ValueError(f"{year}: non-finite values in column 'ano'.")
    if not np.all(year_values == year):
        raise ValueError(f"{year}: inconsistent values in column 'ano'.")

    income = pd.to_numeric(df["renda"], errors="coerce").to_numpy(float)
    return income


def distribution_statistics(income: np.ndarray, prefix: str) -> dict[str, float | int]:
    """Compute the quality-control statistics used for every annual distribution."""
    x = np.asarray(income, dtype=float)
    finite = x[np.isfinite(x)]
    nonnegative = finite[finite >= 0]
    positive = finite[finite > 0]

    out: dict[str, float | int] = {
        f"{prefix}_n": int(x.size),
        f"{prefix}_n_nan": int(np.isnan(x).sum()),
        f"{prefix}_n_inf": int(np.isinf(x).sum()),
        f"{prefix}_n_negative": int(np.sum(finite < 0)),
        f"{prefix}_n_zero": int(np.sum(finite == 0)),
        f"{prefix}_n_positive": int(positive.size),
    }

    if finite.size:
        out.update({
            f"{prefix}_min": float(np.min(finite)),
            f"{prefix}_max": float(np.max(finite)),
            f"{prefix}_mean": float(np.mean(finite)),
            f"{prefix}_median": float(np.median(finite)),
            f"{prefix}_std": float(np.std(finite, ddof=1)) if finite.size > 1 else np.nan,
            f"{prefix}_q01": float(np.quantile(finite, 0.01)),
            f"{prefix}_q25": float(np.quantile(finite, 0.25)),
            f"{prefix}_q50": float(np.quantile(finite, 0.50)),
            f"{prefix}_q75": float(np.quantile(finite, 0.75)),
            f"{prefix}_q99": float(np.quantile(finite, 0.99)),
            f"{prefix}_sum": float(np.sum(finite)),
        })
    else:
        for key in ("min", "max", "mean", "median", "std", "q01", "q25", "q50", "q75", "q99", "sum"):
            out[f"{prefix}_{key}"] = np.nan

    out[f"{prefix}_all_nonnegative"] = int(nonnegative.size == finite.size)
    return out


def compute_log_mad_threshold(
    income: np.ndarray,
    threshold: float = MAD_THRESHOLD,
    consistency: float = MAD_CONSISTENCY,
) -> dict[str, float | str]:
    """Compute the deterministic annual upper cutoff in log1p space."""
    x = np.asarray(income, dtype=float)

    if not np.isfinite(x).all():
        raise ValueError("log-MAD requires finite income values.")
    if (x < 0).any():
        raise ValueError("log-MAD requires non-negative income values.")

    transformed = np.log1p(x)
    center = float(np.median(transformed))

    deviations = np.abs(transformed - center)
    mad = float(np.median(deviations))
    dispersion = float(consistency * mad)
    method = "scaled_mad"

    if dispersion <= 0 and x.size > 1:
        dispersion = float(np.std(transformed, ddof=1))
        method = "std_fallback"

    if dispersion > 0:
        cutoff = float(np.expm1(center + float(threshold) * dispersion))
    else:
        cutoff = float(np.max(x))
        method = "zero_dispersion"

    return {
        "median_log1p": center,
        "mad_log1p": mad,
        "scaled_dispersion_log1p": dispersion,
        "dispersion_method": method,
        "mad_consistency": float(consistency),
        "threshold_k": float(threshold),
        "statistical_cutoff": cutoff,
    }


def validate_distribution(
    year: int,
    before: np.ndarray,
    after: np.ndarray,
    cutoff: float,
) -> dict[str, float | int | bool]:
    """Run deterministic tests on one annual distribution."""
    before = np.asarray(before, dtype=float)
    after = np.asarray(after, dtype=float)

    tests = {
        "year": int(year),
        "test_before_nonempty": bool(before.size > 0),
        "test_after_nonempty": bool(after.size > 0),
        "test_before_finite": bool(np.isfinite(before).all()),
        "test_after_finite": bool(np.isfinite(after).all()),
        "test_before_nonnegative": bool((before >= 0).all()),
        "test_after_nonnegative": bool((after >= 0).all()),
        "test_count_monotonic": bool(after.size <= before.size),
        "test_cutoff_finite_positive": bool(np.isfinite(cutoff) and cutoff >= 0),
        "test_max_after_le_cutoff": bool(
            after.size > 0 and float(np.max(after)) <= cutoff + np.finfo(float).eps * max(1.0, abs(cutoff))
        ),
    }

    n_removed = int(before.size - after.size)
    tests["n_removed"] = n_removed
    tests["test_count_identity"] = bool(before.size == after.size + n_removed)

    if before.size and after.size:
        before_median = float(np.median(before))
        after_median = float(np.median(after))
        before_mean = float(np.mean(before))
        after_mean = float(np.mean(after))

        tests["median_relative_change"] = (
            np.nan if np.isclose(before_median, 0)
            else float((after_median - before_median) / before_median)
        )
        tests["mean_relative_change"] = (
            np.nan if np.isclose(before_mean, 0)
            else float((after_mean - before_mean) / before_mean)
        )
        tests["removal_rate"] = float(n_removed / before.size)
    else:
        tests["median_relative_change"] = np.nan
        tests["mean_relative_change"] = np.nan
        tests["removal_rate"] = np.nan

    invariant_columns = [key for key in tests if key.startswith("test_")]
    tests["all_tests_pass"] = bool(all(bool(tests[key]) for key in invariant_columns))
    return tests


def trim_refined_year(
    df: pd.DataFrame,
    year: int,
    threshold: float = MAD_THRESHOLD,
    consistency: float = MAD_CONSISTENCY,
) -> tuple[pd.DataFrame, dict, dict]:
    """Return trusted data, trimming audit, and distribution tests for one year."""
    raw_income = _income_array(df, year)

    if np.isnan(raw_income).any() or np.isinf(raw_income).any():
        raise ValueError(f"{year}: refined dataset contains NaN or infinite income values.")
    if (raw_income < 0).any():
        raise ValueError(f"{year}: refined dataset contains negative income values.")

    threshold_info = compute_log_mad_threshold(
        raw_income,
        threshold=threshold,
        consistency=consistency,
    )
    cutoff = float(threshold_info["statistical_cutoff"])
    keep = raw_income <= cutoff

    trusted = df.loc[keep].copy()
    trusted_income = raw_income[keep]

    before_stats = distribution_statistics(raw_income, "before")
    after_stats = distribution_statistics(trusted_income, "after")

    audit = {
        "year": int(year),
        **threshold_info,
        "n_refined": int(raw_income.size),
        "n_statistical_outlier": int(np.count_nonzero(~keep)),
        "n_trusted": int(trusted_income.size),
        "removal_rate": float(np.count_nonzero(~keep) / raw_income.size),
        "maximum_before": float(np.max(raw_income)),
        "maximum_after": float(np.max(trusted_income)),
        **before_stats,
        **after_stats,
    }

    tests = validate_distribution(
        year=year,
        before=raw_income,
        after=trusted_income,
        cutoff=cutoff,
    )

    if not tests["all_tests_pass"]:
        failed = [k for k, v in tests.items() if k.startswith("test_") and not bool(v)]
        raise RuntimeError(f"{year}: distribution tests failed: {', '.join(failed)}")

    return trusted, audit, tests


def build_trusted_datasets(
    refined_path: Path = REFINED_PATH,
    trusted_path: Path = TRUSTED_PATH,
    tables_path: Path = TABLES_ANALYSIS_PATH,
    threshold: float = MAD_THRESHOLD,
    consistency: float = MAD_CONSISTENCY,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build all trusted PNAD datasets and persist quality-control tables."""
    files_by_year = discover_refined_files(refined_path)

    trusted_path.mkdir(parents=True, exist_ok=True)
    tables_path.mkdir(parents=True, exist_ok=True)

    audit_rows = []
    test_rows = []

    progress = tqdm(
        files_by_year.items(),
        total=len(files_by_year),
        desc="Building trusted PNAD datasets",
        unit="year",
    )

    for year, input_path in progress:
        progress.set_postfix_str(str(year))
        t0 = perf_counter()

        df_refined = pd.read_parquet(input_path, engine=PARQUET_ENGINE)
        t_read = perf_counter()

        df_trusted, audit, tests = trim_refined_year(
            df_refined,
            year,
            threshold=threshold,
            consistency=consistency,
        )
        t_trim = perf_counter()

        output_path = trusted_path / f"pnad_trusted_{year}.parquet"
        df_trusted.to_parquet(
            output_path,
            index=False,
            engine=PARQUET_ENGINE,
            compression=PARQUET_COMPRESSION,
        )
        t_write = perf_counter()

        audit.update({
            "input_file": input_path.name,
            "output_file": output_path.name,
            "read_seconds": t_read - t0,
            "trim_seconds": t_trim - t_read,
            "write_seconds": t_write - t_trim,
            "total_seconds": t_write - t0,
        })

        audit_rows.append(audit)
        test_rows.append(tests)

    df_audit = pd.DataFrame(audit_rows).sort_values("year").reset_index(drop=True)
    df_tests = pd.DataFrame(test_rows).sort_values("year").reset_index(drop=True)

    if not df_tests["all_tests_pass"].all():
        raise RuntimeError("At least one annual trusted distribution failed validation.")

    df_audit.to_csv(tables_path / AUDIT_FILE.name, index=False)
    df_tests.to_csv(tables_path / TESTS_FILE.name, index=False)

    return df_audit, df_tests


def main() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run stage 02."""
    return build_trusted_datasets()


if __name__ == "__main__":
    audit, tests = main()
    print(audit[[
        "year",
        "n_refined",
        "n_statistical_outlier",
        "removal_rate",
        "n_trusted",
        "maximum_before",
        "statistical_cutoff",
        "maximum_after",
    ]].to_string(index=False))
    print()
    print(f"Validated annual distributions: {int(tests['all_tests_pass'].sum())}/{len(tests)}")
