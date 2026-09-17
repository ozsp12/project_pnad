"""Build consolidated refined and trusted PNAD analytical data products.

Stage 04 is a structural data-product stage. It performs validation and vertical
concatenation only: no observations are filtered, no income values are changed,
and no statistical quantity is estimated.

For each layer, the annual Parquet files are ordered by survey year and written
to one consolidated Parquet with one row group per year. A companion CSV
documents the dataset-level metadata and the Parquet schema.
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
REFINED_PATH = REPO_ROOT / "data" / "refined"
TRUSTED_PATH = REPO_ROOT / "data" / "trusted"
ANALYTICS_PATH = REPO_ROOT / "data" / "analytics"

REFINED_OUTPUT_PATH = ANALYTICS_PATH / "pnad_refined_all.parquet"
TRUSTED_OUTPUT_PATH = ANALYTICS_PATH / "pnad_trusted_all.parquet"
REFINED_METADATA_PATH = ANALYTICS_PATH / "pnad_refined_all_metadata.csv"
TRUSTED_METADATA_PATH = ANALYTICS_PATH / "pnad_trusted_all_metadata.csv"
LEGACY_OUTPUT_PATH = ANALYTICS_PATH / "pnad_analytics_all.parquet"

PARQUET_COMPRESSION = "snappy"
REQUIRED_COLUMNS = {"renda", "ano"}
SCHEMA_VERSION = "1.0"

LAYER_CONFIG = {
    "refined": {
        "input_path": REFINED_PATH,
        "pattern": "pnad_refined_*.parquet",
        "output_path": REFINED_OUTPUT_PATH,
        "metadata_path": REFINED_METADATA_PATH,
        "processing_level": "baseline",
        "dataset_description": (
            "Consolidated refined PNAD/PNAD Continua baseline before "
            "trusted-stage statistical treatment."
        ),
        "source": "Stage 01 annual refined PNAD Parquet files",
    },
    "trusted": {
        "input_path": TRUSTED_PATH,
        "pattern": "pnad_trusted_*.parquet",
        "output_path": TRUSTED_OUTPUT_PATH,
        "metadata_path": TRUSTED_METADATA_PATH,
        "processing_level": "validated benchmark",
        "dataset_description": (
            "Consolidated trusted PNAD/PNAD Continua benchmark after Stage 02 "
            "structural cleaning, deterministic upper-tail treatment, and validation."
        ),
        "source": "Stage 02 annual trusted PNAD Parquet files",
    },
}

COLUMN_DESCRIPTIONS = {
    "renda": (
        "Income value preserved exactly from the corresponding annual data layer. "
        "For years where Stage 01 applies a per-capita construction, this is the "
        "resulting per-capita income."
    ),
    "ano": "Survey year associated with the observation.",
}

COLUMN_UNITS = {
    "renda": "nominal survey-year currency units",
    "ano": "year",
}


def year_from_filename(path: Path, layer: str) -> int:
    """Extract the survey year from an annual layer filename."""
    match = re.fullmatch(rf"pnad_{re.escape(layer)}_(\d{{4}})", path.stem)
    if not match:
        raise ValueError(f"Invalid {layer} filename: {path.name}")
    return int(match.group(1))


def discover_layer_files(
    input_path: Path,
    layer: str,
    pattern: str | None = None,
) -> dict[int, Path]:
    """Return annual Parquet files ordered by survey year."""
    input_path = Path(input_path)
    pattern = pattern or f"pnad_{layer}_*.parquet"
    files = {
        year_from_filename(path, layer): path
        for path in input_path.glob(pattern)
        if path.is_file()
    }
    if not files:
        raise FileNotFoundError(
            f"No files matching '{pattern}' were found in {input_path}."
        )
    return dict(sorted(files.items()))


def validate_layer_frame(df: pd.DataFrame, year: int, layer: str) -> pd.DataFrame:
    """Validate one annual frame without changing its stored values or dtypes."""
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(
            f"{year}: missing required {layer} columns: {', '.join(sorted(missing))}"
        )
    if df.empty:
        raise ValueError(f"{year}: empty {layer} dataset.")

    years = pd.to_numeric(df["ano"], errors="coerce").to_numpy(float)
    if not np.isfinite(years).all():
        raise ValueError(f"{year}: non-finite values in column 'ano'.")
    if not np.all(years == year):
        raise ValueError(f"{year}: inconsistent values in column 'ano'.")

    income = pd.to_numeric(df["renda"], errors="coerce").to_numpy(float)
    if not np.isfinite(income).all():
        raise ValueError(f"{year}: {layer} income contains non-finite values.")
    if np.any(income < 0):
        raise ValueError(f"{year}: {layer} income contains negative values.")

    return df.copy()


def _write_metadata(
    *,
    layer: str,
    output_path: Path,
    metadata_path: Path,
    schema: pa.Schema,
    null_counts: dict[str, int],
    n_rows: int,
    years: list[int],
) -> None:
    config = LAYER_CONFIG[layer]
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for field in schema:
        rows.append(
            {
                "dataset_name": output_path.stem,
                "layer": layer,
                "processing_level": config["processing_level"],
                "dataset_description": config["dataset_description"],
                "parquet_file": output_path.name,
                "metadata_file": metadata_path.name,
                "schema_version": SCHEMA_VERSION,
                "stage04_operation": "validation and vertical concatenation only",
                "source": config["source"],
                "source_pattern": config["pattern"],
                "column_name": field.name,
                "arrow_type": str(field.type),
                "parquet_nullable": bool(field.nullable),
                "observed_null_count": int(null_counts[field.name]),
                "description": COLUMN_DESCRIPTIONS.get(
                    field.name, f"Column preserved from annual {layer} data."
                ),
                "unit": COLUMN_UNITS.get(field.name, "as stored in annual source"),
                "n_rows": int(n_rows),
                "n_columns": len(schema),
                "n_years": len(years),
                "first_year": years[0],
                "last_year": years[-1],
                "n_row_groups": len(years),
                "compression": PARQUET_COMPRESSION,
            }
        )

    pd.DataFrame(rows).to_csv(metadata_path, index=False)


def build_layer_product(
    *,
    layer: str,
    input_path: Path | None = None,
    output_path: Path | None = None,
    metadata_path: Path | None = None,
) -> dict[str, int | str]:
    """Build one consolidated layer Parquet and its metadata/schema CSV."""
    if layer not in LAYER_CONFIG:
        raise ValueError(f"Unsupported analytical layer: {layer}")

    config = LAYER_CONFIG[layer]
    input_path = Path(input_path or config["input_path"])
    output_path = Path(output_path or config["output_path"])
    metadata_path = Path(metadata_path or config["metadata_path"])
    files_by_year = discover_layer_files(input_path, layer, str(config["pattern"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".tmp.parquet")
    if temporary_path.exists():
        temporary_path.unlink()

    writer: pq.ParquetWriter | None = None
    canonical_schema: pa.Schema | None = None
    canonical_columns: list[str] | None = None
    total_rows = 0
    null_counts: dict[str, int] = {}

    try:
        progress = tqdm(
            files_by_year.items(),
            total=len(files_by_year),
            desc=f"Building {layer} analytical PNAD parquet",
            unit="year",
        )

        for year, path in progress:
            progress.set_postfix_str(str(year))
            df = validate_layer_frame(
                pd.read_parquet(path, engine="pyarrow"), year, layer
            )

            columns = list(df.columns)
            if canonical_columns is None:
                canonical_columns = columns
                null_counts = {column: 0 for column in columns}
            elif columns != canonical_columns:
                raise ValueError(
                    f"{year}: {layer} schema columns differ from the first annual file. "
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
                    f"{year}: {layer} Arrow schema differs from the first annual file."
                )

            for column in columns:
                null_counts[column] += int(df[column].isna().sum())

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

    if total_rows == 0 or canonical_schema is None:
        raise RuntimeError(f"The consolidated {layer} dataset would be empty.")

    parquet = pq.ParquetFile(temporary_path)
    if parquet.metadata.num_rows != total_rows:
        raise RuntimeError(
            f"Consolidated {layer} Parquet row count does not match annual inputs."
        )
    if parquet.metadata.num_row_groups != len(files_by_year):
        raise RuntimeError(
            f"Expected one Parquet row group per {layer} survey year."
        )

    temporary_path.replace(output_path)

    years = list(files_by_year)
    _write_metadata(
        layer=layer,
        output_path=output_path,
        metadata_path=metadata_path,
        schema=canonical_schema,
        null_counts=null_counts,
        n_rows=total_rows,
        years=years,
    )

    return {
        "layer": layer,
        "output": str(output_path),
        "metadata": str(metadata_path),
        "n_years": len(years),
        "first_year": years[0],
        "last_year": years[-1],
        "n_rows": total_rows,
        "n_row_groups": len(years),
    }


def discover_trusted_files(trusted_path: Path = TRUSTED_PATH) -> dict[int, Path]:
    """Compatibility wrapper for the former trusted-only Stage-04 API."""
    return discover_layer_files(trusted_path, "trusted")


def validate_trusted_frame(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Compatibility wrapper for the former trusted-only Stage-04 API."""
    return validate_layer_frame(df, year, "trusted")


def build_analytics_parquet(
    trusted_path: Path = TRUSTED_PATH,
    output_path: Path = TRUSTED_OUTPUT_PATH,
    metadata_path: Path | None = None,
) -> dict[str, int | str]:
    """Compatibility wrapper that builds the consolidated trusted product."""
    if metadata_path is None:
        metadata_path = Path(output_path).with_name(
            f"{Path(output_path).stem}_metadata.csv"
        )
    return build_layer_product(
        layer="trusted",
        input_path=trusted_path,
        output_path=output_path,
        metadata_path=metadata_path,
    )


def build_analytics_products() -> dict[str, dict[str, int | str]]:
    """Build both canonical Stage-04 analytical products."""
    summaries = {
        "refined": build_layer_product(layer="refined"),
        "trusted": build_layer_product(layer="trusted"),
    }
    if LEGACY_OUTPUT_PATH.exists():
        LEGACY_OUTPUT_PATH.unlink()
    return summaries


def main() -> dict[str, dict[str, int | str]]:
    """Run Stage 04."""
    return build_analytics_products()


if __name__ == "__main__":
    summaries = main()
    for layer in ("refined", "trusted"):
        summary = summaries[layer]
        print(
            f"Stage 04 {layer} dataset created: "
            f"{summary['n_rows']:,} rows, {summary['n_years']} survey years "
            f"({summary['first_year']}-{summary['last_year']}), "
            f"{summary['n_row_groups']} row groups."
        )
        print(summary["output"])
        print(summary["metadata"])
