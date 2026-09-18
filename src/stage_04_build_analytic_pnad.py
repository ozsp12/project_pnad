"""Build consolidated PNAD data products and publication metadata.

Stage 04 is a structural publication stage. It validates and vertically
concatenates the annual refined and trusted datasets without changing stored
values or filtering observations. It also materializes dataset-level metadata,
annual metadata, and one schema/data-dictionary CSV per consolidated Parquet.

No scientific model is fitted in this stage.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from tqdm.auto import tqdm


REPO_ROOT = Path(__file__).resolve().parents[1]
REFINED_PATH = REPO_ROOT / "data" / "refined"
TRUSTED_PATH = REPO_ROOT / "data" / "trusted"
ANALYTICS_PATH = REPO_ROOT / "data" / "analytics"

METADATA_SOURCE_PATH = REPO_ROOT / "data" / "metadata" / "df_metadata.csv"
GINI_REFERENCE_PATH = (
    REPO_ROOT / "data" / "auxiliary" / "series_gini_ipea_banco_mundial.csv"
)
TRUSTED_AUDIT_PATH = (
    REPO_ROOT / "assets" / "tables_validation" / "trusted_trim_audit_annual.csv"
)

REFINED_OUTPUT_PATH = ANALYTICS_PATH / "pnad_refined_all.parquet"
TRUSTED_OUTPUT_PATH = ANALYTICS_PATH / "pnad_trusted_all.parquet"
REFINED_SCHEMA_PATH = ANALYTICS_PATH / "pnad_refined_all_schema.csv"
TRUSTED_SCHEMA_PATH = ANALYTICS_PATH / "pnad_trusted_all_schema.csv"
ANNUAL_METADATA_PATH = ANALYTICS_PATH / "pnad_annual_metadata.csv"
DATASETS_METADATA_PATH = ANALYTICS_PATH / "pnad_datasets_metadata.csv"

LEGACY_OUTPUT_PATH = ANALYTICS_PATH / "pnad_analytics_all.parquet"
LEGACY_METADATA_PATHS = (
    ANALYTICS_PATH / "pnad_refined_all_metadata.csv",
    ANALYTICS_PATH / "pnad_trusted_all_metadata.csv",
)

PARQUET_COMPRESSION = "snappy"
REQUIRED_COLUMNS = {"renda", "ano"}
DATA_SCHEMA_VERSION = "1.0"

EXCHANGE_SOURCE = (
    "Banco Central do Brasil, Sistema Gerenciador de Series Temporais (SGS), "
    "series 3692: annual end-of-period U.S. dollar selling exchange rate"
)
PRICE_INDEX_SOURCE = (
    "U.S. Bureau of Labor Statistics, Consumer Price Index for All Urban "
    "Consumers (CPIAUCSL), distributed by FRED, Federal Reserve Bank of St. Louis"
)
MONETARY_PROVENANCE = (
    f"{EXCHANGE_SOURCE}; {PRICE_INDEX_SOURCE}. Values are persisted in Stage 00 "
    "metadata and are not queried at Stage 04 runtime."
)

LAYER_CONFIG = {
    "refined": {
        "input_path": REFINED_PATH,
        "pattern": "pnad_refined_*.parquet",
        "output_path": REFINED_OUTPUT_PATH,
        "schema_path": REFINED_SCHEMA_PATH,
        "processing_level": "baseline",
        "source_stage": "Stage 01",
        "source": "Stage 01 annual refined PNAD Parquet files",
        "description": (
            "Consolidated minimally transformed baseline containing all annual "
            "refined PNAD/PNAD Continua income records."
        ),
    },
    "trusted": {
        "input_path": TRUSTED_PATH,
        "pattern": "pnad_trusted_*.parquet",
        "output_path": TRUSTED_OUTPUT_PATH,
        "schema_path": TRUSTED_SCHEMA_PATH,
        "processing_level": "validated benchmark",
        "source_stage": "Stage 02",
        "source": "Stage 02 annual trusted PNAD Parquet files",
        "description": (
            "Consolidated quality-controlled benchmark containing annual trusted "
            "PNAD/PNAD Continua income records after Stage 02 row selection."
        ),
    },
}

COLUMN_DEFINITIONS = {
    "renda": {
        "description": (
            "Harmonized annual income value. Stage 01 applies the annual "
            "income-scale divisor and, when a member field is configured, "
            "divides household income by the member count. Exact annual rules "
            "are recorded in pnad_annual_metadata.csv."
        ),
        "logical_type": "continuous numeric",
        "unit": "nominal survey-year currency units",
        "is_calculated": True,
        "calculation_stage": "Stage 01",
        "calculation": (
            "income_raw / income_scale_divisor; additionally / member_count "
            "when stage01_divides_by_members is true"
        ),
    },
    "ano": {
        "description": "Survey year assigned to each observation.",
        "logical_type": "integer temporal identifier",
        "unit": "year",
        "is_calculated": True,
        "calculation_stage": "Stage 01",
        "calculation": "survey year assigned from the annual extraction specification",
    },
}

ANNUAL_METADATA_REQUIRED = {
    "ano",
    "var_renda",
    "pos_renda",
    "tam_renda",
    "var_morador",
    "pos_morador",
    "tam_morador",
    "link",
    "raw_subdir",
    "raw_pattern",
    "n_files",
    "missing_renda",
    "income_scale_divisor",
    "Currency",
    "Exchange",
    "Index",
    "Adjust2025",
    "Inflation",
}

AUDIT_COLUMNS = {
    "year",
    "mad_consistency",
    "threshold_k",
    "log_mad_cutoff",
    "p99_exception_quantile",
    "p99_exception_cutoff",
    "cutoff_rule",
    "statistical_cutoff",
    "n_refined",
    "n_invalid_structural",
    "n_statistical_outlier",
    "n_removed_total",
    "n_trusted",
    "total_removal_rate",
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


def _count_unique_values(parquet_path: Path, column: str) -> int:
    values = pq.read_table(parquet_path, columns=[column])[column]
    return int(pc.count_distinct(values, mode="only_valid").as_py())


def _write_schema(
    *,
    layer: str,
    output_path: Path,
    schema_path: Path,
    schema: pa.Schema,
    null_counts: dict[str, int],
    n_rows: int,
) -> None:
    """Write a variable-level schema/data dictionary for one consolidated layer."""
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []

    for field in schema:
        definition = COLUMN_DEFINITIONS.get(
            field.name,
            {
                "description": f"Column preserved from annual {layer} data.",
                "logical_type": "unspecified",
                "unit": "as stored in annual source",
                "is_calculated": False,
                "calculation_stage": "",
                "calculation": "",
            },
        )
        source = LAYER_CONFIG[layer]["source"]
        if layer == "trusted":
            source += "; values retained unchanged after Stage 02 row selection"

        n_missing = int(null_counts[field.name])
        rows.append(
            {
                "layer": layer,
                "schema_version": DATA_SCHEMA_VERSION,
                "column_name": field.name,
                "description": definition["description"],
                "logical_type": definition["logical_type"],
                "storage_type": str(field.type),
                "unit": definition["unit"],
                "source": source,
                "is_calculated": bool(definition["is_calculated"]),
                "calculation_stage": definition["calculation_stage"],
                "calculation": definition["calculation"],
                "nullable": False,
                "storage_nullable": bool(field.nullable),
                "n": int(n_rows - n_missing),
                "n_missing": n_missing,
                "n_unique": _count_unique_values(output_path, field.name),
                "n_categories": pd.NA,
            }
        )

    pd.DataFrame(rows).to_csv(schema_path, index=False)


def build_layer_product(
    *,
    layer: str,
    input_path: Path | None = None,
    output_path: Path | None = None,
    schema_path: Path | None = None,
) -> dict[str, int | str]:
    """Build one consolidated layer Parquet and its schema/data dictionary."""
    if layer not in LAYER_CONFIG:
        raise ValueError(f"Unsupported analytical layer: {layer}")

    config = LAYER_CONFIG[layer]
    input_path = Path(input_path or config["input_path"])
    output_path = Path(output_path or config["output_path"])
    schema_path = Path(schema_path or config["schema_path"])
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

    _write_schema(
        layer=layer,
        output_path=output_path,
        schema_path=schema_path,
        schema=canonical_schema,
        null_counts=null_counts,
        n_rows=total_rows,
    )

    years = list(files_by_year)
    return {
        "layer": layer,
        "output": str(output_path),
        "schema": str(schema_path),
        "n_columns": len(canonical_schema),
        "n_years": len(years),
        "first_year": years[0],
        "last_year": years[-1],
        "n_rows": total_rows,
        "n_row_groups": len(years),
    }


def build_annual_metadata(
    *,
    years: list[int],
    metadata_source_path: Path | None = None,
    gini_reference_path: Path | None = None,
    trusted_audit_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, int | str]:
    """Build annual metadata aligned exactly to the consolidated datasets."""
    metadata_source_path = Path(metadata_source_path or METADATA_SOURCE_PATH)
    gini_reference_path = Path(gini_reference_path or GINI_REFERENCE_PATH)
    trusted_audit_path = Path(trusted_audit_path or TRUSTED_AUDIT_PATH)
    output_path = Path(output_path or ANNUAL_METADATA_PATH)

    metadata = pd.read_csv(metadata_source_path)
    missing = ANNUAL_METADATA_REQUIRED.difference(metadata.columns)
    if missing:
        raise ValueError(
            "Annual Stage-00 metadata is missing columns: "
            + ", ".join(sorted(missing))
        )
    if not metadata["ano"].is_unique:
        raise ValueError("Annual Stage-00 metadata contains duplicated years.")

    metadata = metadata.loc[metadata["ano"].isin(years)].copy()
    if set(metadata["ano"].astype(int)) != set(years):
        missing_years = sorted(set(years) - set(metadata["ano"].astype(int)))
        raise ValueError(f"Annual metadata is missing survey years: {missing_years}")

    gini = pd.read_csv(gini_reference_path)
    required_gini = {"ano", "ipea", "banco_mundial"}
    if missing := required_gini.difference(gini.columns):
        raise ValueError(
            "External Gini reference is missing columns: "
            + ", ".join(sorted(missing))
        )
    if not gini["ano"].is_unique:
        raise ValueError("External Gini reference contains duplicated years.")
    gini = gini.rename(
        columns={"ipea": "gini_ipea", "banco_mundial": "gini_world_bank"}
    )

    audit = pd.read_csv(trusted_audit_path)
    if missing := AUDIT_COLUMNS.difference(audit.columns):
        raise ValueError(
            "Trusted-treatment audit is missing columns: "
            + ", ".join(sorted(missing))
        )
    if not audit["year"].is_unique:
        raise ValueError("Trusted-treatment audit contains duplicated years.")
    audit = audit[list(sorted(AUDIT_COLUMNS))].rename(
        columns={
            "year": "ano",
            "mad_consistency": "trusted_mad_consistency",
            "threshold_k": "trusted_mad_k",
            "log_mad_cutoff": "trusted_log_mad_cutoff",
            "p99_exception_quantile": "trusted_p99_exception_quantile",
            "p99_exception_cutoff": "trusted_p99_exception_cutoff",
            "cutoff_rule": "trusted_cutoff_rule",
            "statistical_cutoff": "trusted_effective_cutoff",
            "n_refined": "trusted_n_refined",
            "n_invalid_structural": "trusted_n_invalid_structural",
            "n_statistical_outlier": "trusted_n_statistical_outlier",
            "n_removed_total": "trusted_n_removed_total",
            "n_trusted": "trusted_n_trusted",
            "total_removal_rate": "trusted_total_removal_rate",
        }
    )

    renamed = metadata.rename(
        columns={
            "var_renda": "income_variable",
            "pos_renda": "income_position",
            "tam_renda": "income_width",
            "var_morador": "member_variable",
            "pos_morador": "member_position",
            "tam_morador": "member_width",
            "link": "raw_source",
            "n_files": "raw_file_count",
            "missing_renda": "missing_income_code",
            "Currency": "currency",
            "Exchange": "exchange",
            "Index": "price_index",
            "Adjust2025": "adjust_2025",
            "Inflation": "inflation_factor_2025",
        }
    )

    selected = [
        "ano",
        "income_variable",
        "income_position",
        "income_width",
        "member_variable",
        "member_position",
        "member_width",
        "raw_source",
        "raw_subdir",
        "raw_pattern",
        "raw_file_count",
        "missing_income_code",
        "income_scale_divisor",
        "currency",
        "exchange",
        "price_index",
        "adjust_2025",
        "inflation_factor_2025",
    ]
    annual = renamed[selected].copy()
    annual.insert(
        1,
        "survey",
        np.where(annual["ano"] >= 2016, "PNAD Continua", "PNAD"),
    )
    annual["stage01_divides_by_members"] = (
        annual["member_position"].notna() & annual["member_width"].notna()
    )
    annual["income_construction"] = np.where(
        annual["stage01_divides_by_members"],
        "income_raw / income_scale_divisor / member_count",
        "income_raw / income_scale_divisor",
    )
    annual["adjusted_income_formula"] = (
        "renda / exchange * inflation_factor_2025"
    )
    annual["exchange_source"] = EXCHANGE_SOURCE
    annual["price_index_source"] = PRICE_INDEX_SOURCE
    annual["monetary_provenance"] = MONETARY_PROVENANCE

    annual = annual.merge(
        gini[["ano", "gini_ipea", "gini_world_bank"]],
        on="ano",
        how="left",
        validate="one_to_one",
    )
    annual["gini_reference_role"] = "external validation only"
    annual = annual.merge(audit, on="ano", how="left", validate="one_to_one")

    if annual["trusted_cutoff_rule"].isna().any():
        missing_years = annual.loc[
            annual["trusted_cutoff_rule"].isna(), "ano"
        ].astype(int).tolist()
        raise ValueError(
            f"Trusted-treatment audit is missing survey years: {missing_years}"
        )

    annual = annual.sort_values("ano").reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    annual.to_csv(output_path, index=False)

    return {
        "output": str(output_path),
        "n_years": len(annual),
        "first_year": int(annual["ano"].iloc[0]),
        "last_year": int(annual["ano"].iloc[-1]),
    }


def build_datasets_metadata(
    summaries: dict[str, dict[str, int | str]],
    output_path: Path | None = None,
) -> dict[str, int | str]:
    """Write one metadata row for each consolidated Parquet dataset."""
    output_path = Path(output_path or DATASETS_METADATA_PATH)
    rows = []

    for layer in ("refined", "trusted"):
        summary = summaries[layer]
        config = LAYER_CONFIG[layer]
        parquet_path = Path(str(summary["output"]))
        schema_path = Path(str(summary["schema"]))
        parquet = pq.ParquetFile(parquet_path)

        compression = {
            parquet.metadata.row_group(row_group).column(column).compression.lower()
            for row_group in range(parquet.metadata.num_row_groups)
            for column in range(parquet.metadata.num_columns)
        }
        compression_value = ";".join(sorted(compression))

        rows.append(
            {
                "dataset_name": parquet_path.stem,
                "layer": layer,
                "parquet_file": parquet_path.name,
                "description": config["description"],
                "processing_level": config["processing_level"],
                "source_stage": config["source_stage"],
                "source_pattern": config["pattern"],
                "n_rows": int(parquet.metadata.num_rows),
                "n_columns": int(parquet.metadata.num_columns),
                "n_years": int(summary["n_years"]),
                "first_year": int(summary["first_year"]),
                "last_year": int(summary["last_year"]),
                "n_row_groups": int(parquet.metadata.num_row_groups),
                "compression": compression_value,
                "file_size_bytes": int(parquet_path.stat().st_size),
                "schema_version": DATA_SCHEMA_VERSION,
                "schema_file": schema_path.name,
                "annual_metadata_file": ANNUAL_METADATA_PATH.name,
                "observation_unit": "harmonized household per-resident income record",
                "record_weighting": (
                    "equal observation weights; survey expansion weights are not included"
                ),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return {"output": str(output_path), "n_datasets": len(rows)}


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
    schema_path = (
        Path(metadata_path)
        if metadata_path is not None
        else Path(output_path).with_name(f"{Path(output_path).stem}_schema.csv")
    )
    return build_layer_product(
        layer="trusted",
        input_path=trusted_path,
        output_path=output_path,
        schema_path=schema_path,
    )


def build_analytics_products() -> dict[str, dict[str, int | str]]:
    """Build canonical Stage-04 Parquets, schemas, and metadata tables."""
    refined_files = discover_layer_files(
        Path(LAYER_CONFIG["refined"]["input_path"]),
        "refined",
        str(LAYER_CONFIG["refined"]["pattern"]),
    )
    trusted_files = discover_layer_files(
        Path(LAYER_CONFIG["trusted"]["input_path"]),
        "trusted",
        str(LAYER_CONFIG["trusted"]["pattern"]),
    )
    years = list(refined_files)
    if years != list(trusted_files):
        raise ValueError(
            "Refined and trusted annual layers must cover the same survey years."
        )

    summaries = {
        "refined": build_layer_product(layer="refined"),
        "trusted": build_layer_product(layer="trusted"),
    }
    build_annual_metadata(years=years)
    build_datasets_metadata(summaries)

    for legacy_path in (LEGACY_OUTPUT_PATH, *LEGACY_METADATA_PATHS):
        if legacy_path.exists():
            legacy_path.unlink()

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
        print(summary["schema"])
    print(ANNUAL_METADATA_PATH)
    print(DATASETS_METADATA_PATH)
