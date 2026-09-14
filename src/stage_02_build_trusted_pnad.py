"""Build trusted annual PNAD datasets and audit each distribution.

Stage 02 reads the annual refined Parquet files created by
``stage_01_build_refined_pnad.py``, removes structurally invalid income values
and the project-wide sentinel values 999999, 9999999, and 99999999, applies
the deterministic upper-tail log-MAD rule, validates the resulting annual
distributions, and writes trusted datasets plus validation/audit tables.

The statistical transformation is

    z_i = log(1 + x_i)
    m   = median(z_i)
    s   = 1.4826 * median(|z_i - m|)
    x_c = exp(m + k s) - 1

with k=6 by default. The log-MAD rule is applied only after non-finite,
negative, and sentinel values have been excluded. Sentinel removal is therefore
a structural cleaning rule and is never delegated to the statistical outlier
criterion.

For the 1985 and 1990 surveys, the trusted layer applies an additional
conservative upper-tail rule: observations strictly above the empirical 99th
percentile of the structurally valid annual income distribution are removed.
The effective cutoff is therefore the minimum between the annual log-MAD
cutoff and the empirical p99 cutoff. The refined datasets remain unchanged,
and the exceptional cutoff is recorded explicitly in the audit table.
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
TRUSTED_PATH = REPO_ROOT / "data" / "trusted"
VALIDATION_TABLES_PATH = REPO_ROOT / "assets" / "tables_validation"

REFINED_PATTERN = "pnad_refined_*.parquet"
MAD_CONSISTENCY = 1.4826
MAD_THRESHOLD = 6.0
PARQUET_ENGINE = "pyarrow"
PARQUET_COMPRESSION = "snappy"
INCOME_SENTINELS = (999_999.0, 9_999_999.0, 99_999_999.0)
EXCEPTIONAL_P99_TRIM_YEARS = frozenset({1985, 1990})
EXCEPTIONAL_P99_QUANTILE = 0.99

AUDIT_FILE = VALIDATION_TABLES_PATH / "trusted_trim_audit_annual.csv"
TESTS_FILE = VALIDATION_TABLES_PATH / "trusted_distribution_tests_annual.csv"


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
    """Validate structural assumptions and return income as float64."""
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

    return pd.to_numeric(df["renda"], errors="coerce").to_numpy(float)


def distribution_statistics(
    income: np.ndarray,
    prefix: str,
) -> dict[str, float | int]:
    """Compute annual quality-control statistics."""
    x = np.asarray(income, dtype=float)
    finite = x[np.isfinite(x)]
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
            f"{prefix}_std": (
                float(np.std(finite, ddof=1))
                if finite.size > 1
                else np.nan
            ),
            f"{prefix}_q01": float(np.quantile(finite, 0.01)),
            f"{prefix}_q25": float(np.quantile(finite, 0.25)),
            f"{prefix}_q50": float(np.quantile(finite, 0.50)),
            f"{prefix}_q75": float(np.quantile(finite, 0.75)),
            f"{prefix}_q99": float(np.quantile(finite, 0.99)),
            f"{prefix}_sum": float(np.sum(finite)),
        })
    else:
        for key in (
            "min", "max", "mean", "median", "std",
            "q01", "q25", "q50", "q75", "q99", "sum",
        ):
            out[f"{prefix}_{key}"] = np.nan

    return out


def compute_log_mad_threshold(
    income: np.ndarray,
    threshold: float = MAD_THRESHOLD,
    consistency: float = MAD_CONSISTENCY,
) -> dict[str, float | str]:
    """Compute the deterministic annual upper cutoff in log1p space."""
    x = np.asarray(income, dtype=float)

    if x.size == 0:
        raise ValueError("log-MAD requires at least one valid income value.")
    if not np.isfinite(x).all():
        raise ValueError("log-MAD requires finite income values.")
    if (x < 0).any():
        raise ValueError("log-MAD requires non-negative income values.")
    if np.isin(x, INCOME_SENTINELS).any():
        raise ValueError("log-MAD input must not contain sentinel income values.")

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
    raw_income: np.ndarray,
    valid_income: np.ndarray,
    trusted_income: np.ndarray,
    cutoff: float,
    n_invalid: int,
    n_sentinel: int,
    n_statistical_outlier: int,
) -> dict[str, float | int | bool]:
    """Run deterministic tests on one annual distribution."""
    raw_income = np.asarray(raw_income, dtype=float)
    valid_income = np.asarray(valid_income, dtype=float)
    trusted_income = np.asarray(trusted_income, dtype=float)

    tests: dict[str, float | int | bool] = {
        "year": int(year),
        "input_n_nan": int(np.isnan(raw_income).sum()),
        "input_n_inf": int(np.isinf(raw_income).sum()),
        "input_n_negative": int(
            np.sum(raw_income[np.isfinite(raw_income)] < 0)
        ),
        "input_n_sentinel": int(np.isin(raw_income, INCOME_SENTINELS).sum()),
        "n_invalid_structural": int(n_invalid),
        "n_invalid_sentinel": int(n_sentinel),
        "n_statistical_outlier": int(n_statistical_outlier),
        "test_raw_nonempty": bool(raw_income.size > 0),
        "test_valid_input_nonempty": bool(valid_income.size > 0),
        "test_trusted_nonempty": bool(trusted_income.size > 0),
        "test_valid_input_finite": bool(np.isfinite(valid_income).all()),
        "test_valid_input_nonnegative": bool((valid_income >= 0).all()),
        "test_valid_input_no_sentinel": bool(
            not np.isin(valid_income, INCOME_SENTINELS).any()
        ),
        "test_trusted_finite": bool(np.isfinite(trusted_income).all()),
        "test_trusted_nonnegative": bool((trusted_income >= 0).all()),
        "test_trusted_no_sentinel": bool(
            not np.isin(trusted_income, INCOME_SENTINELS).any()
        ),
        "test_count_monotonic": bool(
            trusted_income.size <= valid_income.size <= raw_income.size
        ),
        "test_count_identity": bool(
            raw_income.size
            == trusted_income.size + n_invalid + n_statistical_outlier
        ),
        "test_cutoff_finite_nonnegative": bool(
            np.isfinite(cutoff) and cutoff >= 0
        ),
        "test_max_after_le_cutoff": bool(
            trusted_income.size > 0
            and float(np.max(trusted_income))
            <= cutoff
            + np.finfo(float).eps * max(1.0, abs(cutoff))
        ),
    }

    if valid_income.size and trusted_income.size:
        before_median = float(np.median(valid_income))
        after_median = float(np.median(trusted_income))
        before_mean = float(np.mean(valid_income))
        after_mean = float(np.mean(trusted_income))

        tests["median_relative_change"] = (
            np.nan
            if np.isclose(before_median, 0)
            else float((after_median - before_median) / before_median)
        )
        tests["mean_relative_change"] = (
            np.nan
            if np.isclose(before_mean, 0)
            else float((after_mean - before_mean) / before_mean)
        )
        tests["structural_invalid_rate"] = float(n_invalid / raw_income.size)
        tests["statistical_removal_rate"] = float(
            n_statistical_outlier / raw_income.size
        )
        tests["total_removal_rate"] = float(
            (n_invalid + n_statistical_outlier) / raw_income.size
        )
    else:
        tests["median_relative_change"] = np.nan
        tests["mean_relative_change"] = np.nan
        tests["structural_invalid_rate"] = np.nan
        tests["statistical_removal_rate"] = np.nan
        tests["total_removal_rate"] = np.nan

    invariant_columns = [
        key for key in tests
        if key.startswith("test_")
    ]
    tests["all_tests_pass"] = bool(
        all(bool(tests[key]) for key in invariant_columns)
    )
    return tests


def trim_refined_year(
    df: pd.DataFrame,
    year: int,
    threshold: float = MAD_THRESHOLD,
    consistency: float = MAD_CONSISTENCY,
) -> tuple[pd.DataFrame, dict, dict]:
    """Return trusted data, trimming audit, and tests for one year."""
    raw_income = _income_array(df, year)

    finite_mask = np.isfinite(raw_income)
    sentinel_mask = finite_mask & np.isin(raw_income, INCOME_SENTINELS)
    nonnegative_mask = finite_mask & (raw_income >= 0) & ~sentinel_mask
    valid_income = raw_income[nonnegative_mask]

    n_nan = int(np.isnan(raw_income).sum())
    n_inf = int(np.isinf(raw_income).sum())
    n_negative = int(np.sum(raw_income[finite_mask] < 0))
    n_sentinel = int(np.count_nonzero(sentinel_mask))
    sentinel_counts = {
        int(value): int(np.count_nonzero(raw_income == value))
        for value in INCOME_SENTINELS
    }
    n_invalid = int(raw_income.size - valid_income.size)

    if valid_income.size == 0:
        raise ValueError(
            f"{year}: no finite non-negative non-sentinel income values."
        )

    threshold_info = compute_log_mad_threshold(
        valid_income,
        threshold=threshold,
        consistency=consistency,
    )
    log_mad_cutoff = float(threshold_info["statistical_cutoff"])
    p99_exception_cutoff = np.nan
    cutoff_rule = "log_mad"
    cutoff = log_mad_cutoff

    if year in EXCEPTIONAL_P99_TRIM_YEARS:
        p99_exception_cutoff = float(
            np.quantile(valid_income, EXCEPTIONAL_P99_QUANTILE)
        )
        cutoff = min(log_mad_cutoff, p99_exception_cutoff)
        cutoff_rule = "min_log_mad_p99_exception"

    threshold_info.update({
        "log_mad_cutoff": log_mad_cutoff,
        "p99_exception_quantile": (
            EXCEPTIONAL_P99_QUANTILE
            if year in EXCEPTIONAL_P99_TRIM_YEARS
            else np.nan
        ),
        "p99_exception_cutoff": p99_exception_cutoff,
        "cutoff_rule": cutoff_rule,
        "statistical_cutoff": float(cutoff),
    })

    statistical_keep_valid = valid_income <= cutoff
    n_statistical_outlier = int(np.count_nonzero(~statistical_keep_valid))

    keep_mask = nonnegative_mask & (raw_income <= cutoff)
    trusted = df.loc[keep_mask].copy()
    trusted_income = raw_income[keep_mask]

    raw_stats = distribution_statistics(raw_income, "raw")
    valid_stats = distribution_statistics(valid_income, "valid")
    trusted_stats = distribution_statistics(trusted_income, "trusted")

    audit = {
        "year": int(year),
        **threshold_info,
        "n_refined": int(raw_income.size),
        "n_invalid_nan": n_nan,
        "n_invalid_inf": n_inf,
        "n_invalid_negative": n_negative,
        "n_invalid_sentinel": n_sentinel,
        "n_invalid_sentinel_999999": sentinel_counts[999_999],
        "n_invalid_sentinel_9999999": sentinel_counts[9_999_999],
        "n_invalid_sentinel_99999999": sentinel_counts[99_999_999],
        "n_invalid_structural": n_invalid,
        "n_valid_before_trim": int(valid_income.size),
        "n_statistical_outlier": n_statistical_outlier,
        "n_removed_total": int(n_invalid + n_statistical_outlier),
        "n_trusted": int(trusted_income.size),
        "structural_invalid_rate": float(n_invalid / raw_income.size),
        "statistical_removal_rate": float(
            n_statistical_outlier / raw_income.size
        ),
        "total_removal_rate": float(
            (n_invalid + n_statistical_outlier) / raw_income.size
        ),
        "maximum_valid_before_trim": float(np.max(valid_income)),
        "maximum_after": float(np.max(trusted_income)),
        **raw_stats,
        **valid_stats,
        **trusted_stats,
    }

    tests = validate_distribution(
        year=year,
        raw_income=raw_income,
        valid_income=valid_income,
        trusted_income=trusted_income,
        cutoff=cutoff,
        n_invalid=n_invalid,
        n_sentinel=n_sentinel,
        n_statistical_outlier=n_statistical_outlier,
    )

    if not tests["all_tests_pass"]:
        failed = [
            key for key, value in tests.items()
            if key.startswith("test_") and not bool(value)
        ]
        raise RuntimeError(
            f"{year}: distribution tests failed: {', '.join(failed)}"
        )

    return trusted, audit, tests


def build_trusted_datasets(
    refined_path: Path = REFINED_PATH,
    trusted_path: Path = TRUSTED_PATH,
    tables_path: Path = VALIDATION_TABLES_PATH,
    threshold: float = MAD_THRESHOLD,
    consistency: float = MAD_CONSISTENCY,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build all trusted PNAD datasets and persist validation/audit tables."""
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

        df_refined = pd.read_parquet(
            input_path,
            engine=PARQUET_ENGINE,
        )
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

    df_audit = (
        pd.DataFrame(audit_rows)
        .sort_values("year")
        .reset_index(drop=True)
    )
    df_tests = (
        pd.DataFrame(test_rows)
        .sort_values("year")
        .reset_index(drop=True)
    )

    if not df_tests["all_tests_pass"].all():
        raise RuntimeError(
            "At least one annual trusted distribution failed validation."
        )

    df_audit.to_csv(
        tables_path / AUDIT_FILE.name,
        index=False,
    )
    df_tests.to_csv(
        tables_path / TESTS_FILE.name,
        index=False,
    )

    return df_audit, df_tests


def main() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run stage 02."""
    return build_trusted_datasets()


if __name__ == "__main__":
    audit, tests = main()
    print(
        audit[[
            "year",
            "n_refined",
            "n_invalid_sentinel",
            "n_invalid_structural",
            "n_statistical_outlier",
            "n_removed_total",
            "n_trusted",
            "statistical_cutoff",
            "maximum_after",
        ]].to_string(index=False)
    )
    print()
    print(
        "Validated annual distributions: "
        f"{int(tests['all_tests_pass'].sum())}/{len(tests)}"
    )
