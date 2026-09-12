"""Build one concatenated analytical PNAD Parquet from trusted annual data.

Stage 04 is a structural data-product stage. It does not re-estimate any
statistics. It reads every annual ``data/trusted/pnad_trusted_YYYY.parquet``
file, validates the trusted invariants, and writes a single vertically
concatenated Parquet file ordered by survey year.

The resulting file keeps the trusted columns unchanged and stores each survey
year as one Parquet row group, which makes the combined dataset convenient for
cross-year analysis while preserving efficient year-level filtering.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm.auto import tqdm


REPO_ROOT = Path(__file__).resolve().parents[1]
TRUSTED_PATH = REPO_ROOT / "data" / "trusted"
ANALYTICS_PATH = REPO_ROOT / "data" / "analytics"
OUTPUT_PATH = ANALYTICS_PATH / "pnad_analytics_all.parquet"

TRUSTED_PATTERN = "pnad_trusted_*.parquet"
PARQUET_COMPRESSION = "snappy"
REQUIRED_COLUMNS = {"renda", "ano"}


def year_from_filename(path: Path) -> int:
    """Extract the survey year from a trusted annual filename."""
    match = re.fullmatch(r"pnad_trusted_(\d{4})", path.stem)
    if not match:
        raise ValueError(f"Invalid trusted filename: {path.name}")
    return int(match.group(1))


def discover_trusted_files(trusted_path: Path = TRUSTED_PATH) -> dict[int, Path]:
    """Return all trusted annual Parquet files ordered by survey year."""
    files = {
        year_from_filename(path): path
        for path in trusted_path.glob(TRUSTED_PATTERN)
        if path.is_file()
    }
    if not files:
        raise FileNotFoundError(
            f"No files matching '{TRUSTED_PATTERN}' were found in {trusted_path}."
        )
    return dict(sorted(files.items()))


def validate_trusted_frame(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Validate one trusted annual frame without changing its analytical content."""
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(
            f"{year}: missing required trusted columns: {', '.join(sorted(missing))}"
        )
    if df.empty:
        raise ValueError(f"{year}: empty trusted dataset.")

    years = pd.to_numeric(df["ano"], errors="coerce").to_numpy(float)
    if not np.isfinite(years).all():
        raise ValueError(f"{year}: non-finite values in column 'ano'.")
    if not np.all(years == year):
        raise ValueError(f"{year}: inconsistent values in column 'ano'.")

    income = pd.to_numeric(df["renda"], errors="coerce").to_numpy(float)
    if not np.isfinite(income).all():
        raise ValueError(f"{year}: trusted income contains non-finite values.")
    if np.any(income < 0):
        raise ValueError(f"{year}: trusted income contains negative values.")

    out = df.copy()
    out["ano"] = years.astype("int64")
    out["renda"] = income.astype("float64")
    return out


def build_analytics_parquet(
    trusted_path: Path = TRUSTED_PATH,
    output_path: Path = OUTPUT_PATH,
) -> dict[str, int | str]:
    """Concatenate trusted annual files into one validated Parquet dataset."""
    files_by_year = discover_trusted_files(trusted_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = output_path.with_suffix(".tmp.parquet")
    if temporary_path.exists():
        temporary_path.unlink()

    writer: pq.ParquetWriter | None = None
    canonical_schema: pa.Schema | None = None
    canonical_columns: list[str] | None = None
    total_rows = 0

    try:
        progress = tqdm(
            files_by_year.items(),
            total=len(files_by_year),
            desc="Building analytical PNAD parquet",
            unit="year",
        )

        for year, path in progress:
            progress.set_postfix_str(str(year))
            df = validate_trusted_frame(pd.read_parquet(path, engine="pyarrow"), year)

            columns = list(df.columns)
            if canonical_columns is None:
                canonical_columns = columns
            elif columns != canonical_columns:
                raise ValueError(
                    f"{year}: trusted schema columns differ from the first annual file. "
                    f"Expected {canonical_columns}, found {columns}."
                )

            table = pa.Table.from_pandas(df, preserve_index=False).replace_schema_metadata()
            if canonical_schema is None:
                canonical_schema = table.schema
                writer = pq.ParquetWriter(
                    temporary_path,
                    canonical_schema,
                    compression=PARQUET_COMPRESSION,
                )
            elif not table.schema.equals(canonical_schema, check_metadata=False):
                raise ValueError(
                    f"{year}: trusted Arrow schema differs from the first annual file."
                )

            assert writer is not None
            writer.write_table(table, row_group_size=len(df))
            total_rows += len(df)
    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()
        raise
    finally:
        if writer is not None:
            writer.close()

    if total_rows == 0:
        raise RuntimeError("The concatenated analytical dataset would be empty.")

    parquet = pq.ParquetFile(temporary_path)
    if parquet.metadata.num_rows != total_rows:
        raise RuntimeError(
            "Concatenated Parquet row count does not match the annual trusted inputs."
        )
    if parquet.metadata.num_row_groups != len(files_by_year):
        raise RuntimeError(
            "Expected one Parquet row group per trusted survey year."
        )

    temporary_path.replace(output_path)

    years = list(files_by_year)
    return {
        "output": str(output_path),
        "n_years": len(years),
        "first_year": years[0],
        "last_year": years[-1],
        "n_rows": total_rows,
        "n_row_groups": len(years),
    }


def main() -> dict[str, int | str]:
    """Run Stage 04."""
    return build_analytics_parquet()


if __name__ == "__main__":
    summary = main()
    print(
        "Stage 04 analytical dataset created: "
        f"{summary['n_rows']:,} rows, {summary['n_years']} survey years "
        f"({summary['first_year']}-{summary['last_year']}), "
        f"{summary['n_row_groups']} row groups."
    )
    print(summary["output"])
