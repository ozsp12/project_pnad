"""Build the canonical publication tables from trusted PNAD outputs.

The paper-facing table layer is intentionally small: one annual Gompertz table,
one annual Pareto table, one annual economic/inequality table, and one schema
metadata table. The module consumes the canonical trusted Stage-03 products
directly and removes intermediate paper CSVs before persisting the four final
tables.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES_ANALYSIS = REPO_ROOT / "assets" / "tables_analysis_trusted"
TABLES_PAPER = REPO_ROOT / "assets" / "tables_paper"
TRUSTED_DATA = REPO_ROOT / "data" / "trusted"
METADATA_PATH = REPO_ROOT / "data" / "metadata" / "df_metadata.xlsx"
GINI_REFERENCE_PATH = REPO_ROOT / "data" / "auxiliary" / "series_gini_ipea_banco_mundial.csv"
GDP_PATH = REPO_ROOT / "data" / "auxiliary" / "gdp_growth_brazil_1978_2025.csv"

STATS_PATH = TABLES_ANALYSIS / "statistics_annual.csv"
GOMPERTZ_PATH = TABLES_ANALYSIS / "gompertz_annual.csv"
PARETO_PATH = TABLES_ANALYSIS / "pareto_annual.csv"
CURVES_PATH = TABLES_ANALYSIS / "gompertz_pareto_curves.csv"
BOOTSTRAP_PATH = TABLES_PAPER / "moura_ribeiro_2009_bootstrap_uncertainties_trusted_1978_2025.csv"

START_YEAR = 1978
END_YEAR = 2025

GOMPERTZ_OUT = TABLES_PAPER / "table_01_gompertz_annual.csv"
PARETO_OUT = TABLES_PAPER / "table_02_pareto_annual.csv"
ECONOMIC_OUT = TABLES_PAPER / "table_03_economic_inequality_annual.csv"
METADATA_OUT = TABLES_PAPER / "table_04_metadata.csv"
CANONICAL_TABLES = {
    GOMPERTZ_OUT.name,
    PARETO_OUT.name,
    ECONOMIC_OUT.name,
    METADATA_OUT.name,
}


def _year_filter(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    return out[(out["year"] >= START_YEAR) & (out["year"] <= END_YEAR)].copy()


def _load_metadata() -> pd.DataFrame:
    """Return the annual metadata frame enriched with the external Gini series."""
    metadata = pd.read_excel(METADATA_PATH).rename(columns={"ano": "year"})
    if "year" not in metadata.columns:
        raise ValueError("df_metadata.xlsx must contain ano or year")
    metadata["year"] = pd.to_numeric(metadata["year"], errors="coerce").astype("Int64")

    gini = pd.read_csv(GINI_REFERENCE_PATH).rename(
        columns={"ano": "year", "ipea": "gini_ipea", "banco_mundial": "gini_world_bank"}
    )
    gini["year"] = pd.to_numeric(gini["year"], errors="coerce").astype("Int64")
    for column in ("gini_ipea", "gini_world_bank"):
        gini[column] = pd.to_numeric(gini[column], errors="coerce")
        finite = gini[column].dropna()
        if not finite.empty and finite.max() > 1.5:
            gini[column] = gini[column] / 100.0

    return metadata.merge(
        gini[["year", "gini_ipea", "gini_world_bank"]],
        on="year",
        how="left",
    )


def _load_adjusted_income(year: int, metadata_index: pd.DataFrame) -> np.ndarray:
    """Load positive trusted income and reproduce the stage-03 2025-US$ scale."""
    path = TRUSTED_DATA / f"pnad_trusted_{year}.parquet"
    frame = pd.read_parquet(path, columns=["renda"])
    income = pd.to_numeric(frame["renda"], errors="coerce").to_numpy(float)
    income = income[np.isfinite(income) & (income > 0)]
    if income.size == 0:
        raise ValueError(f"{year}: no positive trusted income observations")

    row = metadata_index.loc[year]
    exchange = float(row["Exchange"])
    inflation = float(row["Inflation"])
    if not np.isfinite(exchange) or exchange <= 0:
        raise ValueError(f"{year}: invalid Exchange in metadata")
    if not np.isfinite(inflation) or inflation <= 0:
        raise ValueError(f"{year}: invalid Inflation in metadata")
    return income / exchange * inflation


def _band_record(
    values: np.ndarray,
    total_income: float,
    prefix: str,
) -> dict[str, float | int]:
    if values.size == 0:
        return {
            f"{prefix}_population_n": 0,
            f"{prefix}_income_share_pct": 0.0,
            f"{prefix}_mean_income_2025_usd": np.nan,
            f"{prefix}_median_income_2025_usd": np.nan,
            f"{prefix}_std_income_2025_usd": np.nan,
        }
    return {
        f"{prefix}_population_n": int(values.size),
        f"{prefix}_income_share_pct": 100.0 * float(values.sum()) / total_income,
        f"{prefix}_mean_income_2025_usd": float(np.mean(values)),
        f"{prefix}_median_income_2025_usd": float(np.median(values)),
        f"{prefix}_std_income_2025_usd": (
            float(np.std(values, ddof=1)) if values.size > 1 else np.nan
        ),
    }


def build_income_summaries(
    years: list[int],
    annual: pd.DataFrame,
    stats: pd.DataFrame,
    metadata: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build economic rows and Gompertz/Pareto income shares from trusted microdata."""
    annual_index = annual.set_index("year")
    stats_index = stats.set_index("year")
    metadata_index = metadata.set_index("year")
    economic_rows: list[dict[str, float | int]] = []
    regime_rows: list[dict[str, float | int]] = []

    gdp = pd.read_csv(GDP_PATH)
    gdp["year"] = pd.to_numeric(gdp["year"], errors="coerce").astype("Int64")
    gdp["gdp_growth_pct"] = pd.to_numeric(gdp["gdp_growth_pct"], errors="coerce")
    gdp_index = gdp.set_index("year")

    for year in years:
        if (
            year not in annual_index.index
            or year not in stats_index.index
            or year not in metadata_index.index
        ):
            continue

        adjusted = np.sort(_load_adjusted_income(year, metadata_index))
        total = float(adjusted.sum())
        if total <= 0:
            raise ValueError(f"{year}: non-positive trusted income total")

        n = adjusted.size
        i90 = int(np.floor(0.90 * n))
        i99 = int(np.floor(0.99 * n))
        i999 = int(np.floor(0.999 * n))
        p90_p99 = adjusted[i90:i99]
        p99_p999 = adjusted[i99:i999]
        p999_p100 = adjusted[i999:]

        xt = float(annual_index.loc[year, "transition_x_t"])
        normalized = adjusted / float(np.mean(adjusted))
        gompertz_share = 100.0 * float(adjusted[normalized < xt].sum()) / total
        pareto_share = 100.0 - gompertz_share
        regime_rows.append(
            {
                "year": year,
                "gompertz_income_share_pct": gompertz_share,
                "pareto_income_share_pct": pareto_share,
            }
        )

        stats_row = stats_index.loc[year]
        metadata_row = metadata_index.loc[year]
        row: dict[str, float | int] = {
            "year": year,
            "gdp_growth_pct": (
                float(gdp_index.loc[year, "gdp_growth_pct"])
                if year in gdp_index.index
                else np.nan
            ),
            "income_observation_n": int(n),
            "income_mean_2025_usd": float(np.mean(adjusted)),
            "income_median_2025_usd": float(np.median(adjusted)),
            "income_std_2025_usd": (
                float(np.std(adjusted, ddof=1)) if n > 1 else np.nan
            ),
            "gini_pnad": float(stats_row["Gini"]),
            "pietra_pnad": float(stats_row["Pietra"]),
            "kolkata_pnad": float(stats_row["Kolkata"]),
            "zanardi_pnad": float(stats_row["Zanardi"]),
            "gini_ipea": (
                float(metadata_row["gini_ipea"])
                if pd.notna(metadata_row["gini_ipea"])
                else np.nan
            ),
            "gini_world_bank": (
                float(metadata_row["gini_world_bank"])
                if pd.notna(metadata_row["gini_world_bank"])
                else np.nan
            ),
        }
        row.update(_band_record(p90_p99, total, "p90_p99"))
        row.update(_band_record(p99_p999, total, "p99_p999"))
        row.update(_band_record(p999_p100, total, "p999_p100"))
        economic_rows.append(row)

    economic = pd.DataFrame(economic_rows).sort_values("year").reset_index(drop=True)
    regime = pd.DataFrame(regime_rows).sort_values("year").reset_index(drop=True)
    return economic, regime


def _mle_r2(curves: pd.DataFrame, annual: pd.DataFrame) -> pd.DataFrame:
    annual_index = annual.set_index("year")
    rows = []
    for year in sorted(int(y) for y in annual["year"].dropna().unique()):
        xt = float(annual_index.loc[year, "transition_x_t"])
        d = curves[
            (curves["year"] == year)
            & (curves["income_normalized"] >= xt)
            & (curves["empirical_ccdf_percent"] > 0)
        ]
        observed = pd.to_numeric(
            d["empirical_ccdf_percent"], errors="coerce"
        ).to_numpy(float)
        fitted = pd.to_numeric(
            d["pareto_fitted_ccdf_percent_mle"], errors="coerce"
        ).to_numpy(float)
        mask = (
            np.isfinite(observed)
            & np.isfinite(fitted)
            & (observed > 0)
            & (fitted > 0)
        )
        if mask.sum() < 2:
            r2 = np.nan
        else:
            y = np.log(observed[mask])
            yh = np.log(fitted[mask])
            tss = float(np.sum((y - y.mean()) ** 2))
            sse = float(np.sum((y - yh) ** 2))
            r2 = np.nan if tss <= 0 else 1.0 - sse / tss
        rows.append({"year": year, "pareto_mle_r2": r2})
    return pd.DataFrame(rows)


def build_gompertz_table(
    annual: pd.DataFrame,
    bootstrap: pd.DataFrame,
    regime: pd.DataFrame,
) -> pd.DataFrame:
    t = annual.merge(bootstrap, on="year", how="left").merge(
        regime, on="year", how="left"
    )
    t["gompertz_correlation_coefficient"] = np.sqrt(
        np.clip(pd.to_numeric(t["gompertz_r2"], errors="coerce"), 0.0, 1.0)
    )
    columns = [
        "year",
        "gompertz_A",
        "gompertz_A_bootstrap_se",
        "gompertz_B",
        "gompertz_B_bootstrap_se",
        "gompertz_x_gmax",
        "transition_x_t",
        "gompertz_r2",
        "gompertz_correlation_coefficient",
        "gompertz_population_pct",
        "gompertz_income_share_pct",
        "bootstrap_reps",
    ]
    return t[columns].sort_values("year").reset_index(drop=True)


def build_pareto_table(
    annual: pd.DataFrame,
    bootstrap: pd.DataFrame,
    regime: pd.DataFrame,
    curves: pd.DataFrame,
) -> pd.DataFrame:
    mle = _mle_r2(curves, annual)
    t = (
        annual.merge(bootstrap, on="year", how="left")
        .merge(regime, on="year", how="left")
        .merge(mle, on="year", how="left")
    )
    t["pareto_ls_correlation_coefficient"] = np.sqrt(
        np.clip(pd.to_numeric(t["pareto_ls_r2"], errors="coerce"), 0.0, 1.0)
    )
    t["pareto_mle_correlation_coefficient"] = np.sqrt(
        np.clip(pd.to_numeric(t["pareto_mle_r2"], errors="coerce"), 0.0, 1.0)
    )
    columns = [
        "year",
        "pareto_x_pmin",
        "transition_x_t",
        "transition_delta_x_t",
        "pareto_alpha_ls",
        "pareto_alpha_ls_bootstrap_se",
        "pareto_beta_ls",
        "pareto_beta_ls_bootstrap_se",
        "pareto_ls_r2",
        "pareto_ls_correlation_coefficient",
        "pareto_alpha_mle",
        "pareto_alpha_mle_fisher_se",
        "pareto_alpha_mle_bootstrap_se",
        "pareto_beta_mle_continuity",
        "pareto_beta_mle_bootstrap_se",
        "pareto_mle_r2",
        "pareto_mle_correlation_coefficient",
        "pareto_population_pct",
        "pareto_income_share_pct",
        "bootstrap_reps",
    ]
    return t[columns].sort_values("year").reset_index(drop=True)


def _metadata_for_column(table_name: str, column: str) -> tuple[str, str, str]:
    fixed: dict[str, tuple[str, str, str]] = {
        "year": ("Survey/reference year.", "year", "PNAD / auxiliary annual series"),
        "gompertz_A": (
            "Gompertz normalization parameter A.",
            "dimensionless",
            "trusted PNAD regime fit",
        ),
        "gompertz_A_bootstrap_se": (
            "Bootstrap standard error associated with the Gompertz intercept diagnostic.",
            "dimensionless",
            "trusted PNAD bootstrap",
        ),
        "gompertz_B": (
            "Gompertz slope parameter B in G(x)=exp[exp(A-Bx)].",
            "dimensionless",
            "trusted PNAD regime fit",
        ),
        "gompertz_B_bootstrap_se": (
            "Bootstrap standard error of Gompertz B.",
            "dimensionless",
            "trusted PNAD bootstrap",
        ),
        "gompertz_x_gmax": (
            "Largest normalized income assigned to the Gompertz fitting region.",
            "normalized income",
            "trusted PNAD regime fit",
        ),
        "transition_x_t": (
            "Gompertz-Pareto transition income.",
            "normalized income",
            "trusted PNAD regime fit",
        ),
        "gompertz_r2": (
            "Coefficient of determination for the Gompertz linearized fit.",
            "dimensionless",
            "trusted PNAD regime fit",
        ),
        "gompertz_correlation_coefficient": (
            "Positive square root of Gompertz R^2.",
            "dimensionless",
            "derived from trusted PNAD fit",
        ),
        "gompertz_population_pct": (
            "Share of positive-income observations in the Gompertz regime.",
            "%",
            "trusted PNAD regime fit",
        ),
        "gompertz_income_share_pct": (
            "Share of total trusted adjusted income below x_t.",
            "%",
            "trusted PNAD microdata",
        ),
        "bootstrap_reps": (
            "Number of bootstrap resamples used for parameter uncertainty.",
            "count",
            "paper pipeline configuration",
        ),
        "pareto_x_pmin": (
            "Minimum normalized income of the selected Pareto LS tail.",
            "normalized income",
            "trusted PNAD regime fit",
        ),
        "transition_delta_x_t": (
            "Half-width between x_G,max and x_P,min when the bounds differ.",
            "normalized income",
            "trusted PNAD regime fit",
        ),
        "pareto_alpha_ls": (
            "Pareto exponent estimated by log-log least squares.",
            "dimensionless",
            "trusted PNAD regime fit",
        ),
        "pareto_alpha_ls_bootstrap_se": (
            "Bootstrap standard error of the Pareto LS exponent.",
            "dimensionless",
            "trusted PNAD bootstrap",
        ),
        "pareto_beta_ls": (
            "Pareto amplitude estimated by log-log least squares.",
            "CCDF-percent scale",
            "trusted PNAD regime fit",
        ),
        "pareto_beta_ls_bootstrap_se": (
            "Bootstrap standard error of the Pareto LS amplitude.",
            "CCDF-percent scale",
            "trusted PNAD bootstrap",
        ),
        "pareto_ls_r2": (
            "Coefficient of determination for the Pareto LS log-log fit.",
            "dimensionless",
            "trusted PNAD regime fit",
        ),
        "pareto_ls_correlation_coefficient": (
            "Positive square root of Pareto LS R^2.",
            "dimensionless",
            "derived from trusted PNAD fit",
        ),
        "pareto_alpha_mle": (
            "Pareto exponent estimated directly from individual observations above x_t.",
            "dimensionless",
            "trusted PNAD direct MLE",
        ),
        "pareto_alpha_mle_fisher_se": (
            "Fisher-information standard error of the direct Pareto MLE exponent.",
            "dimensionless",
            "trusted PNAD direct MLE",
        ),
        "pareto_alpha_mle_bootstrap_se": (
            "Bootstrap standard error of the direct Pareto MLE exponent.",
            "dimensionless",
            "trusted PNAD bootstrap",
        ),
        "pareto_beta_mle_continuity": (
            "Pareto amplitude implied by continuity with the Gompertz curve at x_t.",
            "CCDF-percent scale",
            "trusted PNAD continuity condition",
        ),
        "pareto_beta_mle_bootstrap_se": (
            "Bootstrap standard error of the continuity Pareto amplitude.",
            "CCDF-percent scale",
            "trusted PNAD bootstrap",
        ),
        "pareto_mle_r2": (
            "Log-space R^2 diagnostic for the direct-MLE Pareto curve.",
            "dimensionless",
            "trusted PNAD regime curves",
        ),
        "pareto_mle_correlation_coefficient": (
            "Positive square root of the MLE-curve R^2 diagnostic.",
            "dimensionless",
            "derived from trusted PNAD regime curves",
        ),
        "pareto_population_pct": (
            "Share of positive-income observations in the Pareto regime.",
            "%",
            "trusted PNAD regime fit",
        ),
        "pareto_income_share_pct": (
            "Share of total trusted adjusted income at or above x_t.",
            "%",
            "trusted PNAD microdata",
        ),
        "gdp_growth_pct": (
            "Brazil real GDP annual growth rate.",
            "% per year",
            "World Bank/WDI NY.GDP.MKTP.KD.ZG snapshot",
        ),
        "income_observation_n": (
            "Number of positive finite trusted income observations used in the annual summary.",
            "count",
            "trusted PNAD microdata",
        ),
        "income_mean_2025_usd": (
            "Mean positive trusted income after the project 2025-US$ adjustment.",
            "2025 US$",
            "trusted PNAD microdata + df_metadata.xlsx",
        ),
        "income_median_2025_usd": (
            "Median positive trusted income after the project 2025-US$ adjustment.",
            "2025 US$",
            "trusted PNAD microdata + df_metadata.xlsx",
        ),
        "income_std_2025_usd": (
            "Sample standard deviation of positive trusted adjusted income.",
            "2025 US$",
            "trusted PNAD microdata + df_metadata.xlsx",
        ),
        "gini_pnad": (
            "Gini coefficient calculated from trusted PNAD income.",
            "dimensionless",
            "trusted PNAD analysis",
        ),
        "pietra_pnad": (
            "Pietra inequality index calculated from trusted PNAD income.",
            "dimensionless",
            "trusted PNAD analysis",
        ),
        "kolkata_pnad": (
            "Kolkata inequality index calculated from trusted PNAD income.",
            "dimensionless",
            "trusted PNAD analysis",
        ),
        "zanardi_pnad": (
            "Zanardi inequality index calculated from trusted PNAD income.",
            "dimensionless",
            "trusted PNAD analysis",
        ),
        "gini_ipea": (
            "External IPEA Gini reference merged into the annual metadata frame.",
            "dimensionless",
            "series_gini_ipea_banco_mundial.csv",
        ),
        "gini_world_bank": (
            "External World Bank Gini reference merged into the annual metadata frame.",
            "dimensionless",
            "series_gini_ipea_banco_mundial.csv",
        ),
    }
    if column in fixed:
        return fixed[column]

    bands = {
        "p90_p99": "mutually exclusive 90th-to-99th-percentile income rank band",
        "p99_p999": "mutually exclusive 99th-to-99.9th-percentile income rank band",
        "p999_p100": "mutually exclusive top-0.1% income rank band",
    }
    for prefix, label in bands.items():
        if column == f"{prefix}_population_n":
            return (
                f"Observation count in the {label}.",
                "count",
                "trusted PNAD microdata",
            )
        if column == f"{prefix}_income_share_pct":
            return (
                f"Share of total annual income received by the {label}.",
                "%",
                "trusted PNAD microdata",
            )
        if column == f"{prefix}_mean_income_2025_usd":
            return (
                f"Mean adjusted income in the {label}.",
                "2025 US$",
                "trusted PNAD microdata + df_metadata.xlsx",
            )
        if column == f"{prefix}_median_income_2025_usd":
            return (
                f"Median adjusted income in the {label}.",
                "2025 US$",
                "trusted PNAD microdata + df_metadata.xlsx",
            )
        if column == f"{prefix}_std_income_2025_usd":
            return (
                f"Sample standard deviation of adjusted income in the {label}.",
                "2025 US$",
                "trusted PNAD microdata + df_metadata.xlsx",
            )
    raise KeyError(f"No metadata description for {table_name}.{column}")


def build_metadata_table(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for table_name, frame in tables.items():
        for column in frame.columns:
            description, unit, source = _metadata_for_column(table_name, column)
            rows.append(
                {
                    "table_name": table_name,
                    "column_name": column,
                    "description": description,
                    "unit": unit,
                    "source": source,
                }
            )
    rows.extend(
        [
            {
                "table_name": METADATA_OUT.name,
                "column_name": "table_name",
                "description": "Name of the canonical paper table containing the documented field.",
                "unit": "text",
                "source": "paper table schema",
            },
            {
                "table_name": METADATA_OUT.name,
                "column_name": "column_name",
                "description": "Column name documented by this metadata row.",
                "unit": "text",
                "source": "paper table schema",
            },
            {
                "table_name": METADATA_OUT.name,
                "column_name": "description",
                "description": "Human-readable definition of the column.",
                "unit": "text",
                "source": "paper table schema",
            },
            {
                "table_name": METADATA_OUT.name,
                "column_name": "unit",
                "description": "Measurement unit or scale of the column.",
                "unit": "text",
                "source": "paper table schema",
            },
            {
                "table_name": METADATA_OUT.name,
                "column_name": "source",
                "description": "Primary repository data source or derivation for the column.",
                "unit": "text",
                "source": "paper table schema",
            },
        ]
    )
    return pd.DataFrame(rows)


def _clean_paper_csvs() -> None:
    TABLES_PAPER.mkdir(parents=True, exist_ok=True)
    for path in TABLES_PAPER.glob("*.csv"):
        path.unlink()


def validate_tables(
    gompertz: pd.DataFrame,
    pareto: pd.DataFrame,
    economic: pd.DataFrame,
) -> None:
    if not np.allclose(
        gompertz["gompertz_income_share_pct"].to_numpy(float)
        + pareto["pareto_income_share_pct"].to_numpy(float),
        100.0,
        atol=1e-8,
        equal_nan=False,
    ):
        raise AssertionError("Gompertz and Pareto income shares must sum to 100%")
    for prefix in ("p90_p99", "p99_p999", "p999_p100"):
        if (economic[f"{prefix}_population_n"] < 0).any():
            raise AssertionError(f"Negative population count in {prefix}")
        shares = economic[f"{prefix}_income_share_pct"]
        if ((shares < 0) | (shares > 100)).any():
            raise AssertionError(f"Invalid income share in {prefix}")
    if (
        economic["year"].duplicated().any()
        or gompertz["year"].duplicated().any()
        or pareto["year"].duplicated().any()
    ):
        raise AssertionError("Canonical paper tables must contain at most one row per year")


def load_canonical_annual_fits() -> pd.DataFrame:
    """Merge the canonical Stage-03 Gompertz and Pareto annual tables."""
    gompertz = _year_filter(pd.read_csv(GOMPERTZ_PATH))
    pareto = _year_filter(pd.read_csv(PARETO_PATH))
    return gompertz.merge(
        pareto,
        on="year",
        how="inner",
        validate="one_to_one",
        suffixes=("", "_pareto"),
    )


def main() -> None:
    stats = _year_filter(pd.read_csv(STATS_PATH))
    annual = load_canonical_annual_fits()
    curves = _year_filter(pd.read_csv(CURVES_PATH))
    bootstrap = _year_filter(pd.read_csv(BOOTSTRAP_PATH))
    metadata = _load_metadata()

    years = sorted(
        set(int(y) for y in annual["year"].dropna())
        & set(int(y) for y in stats["year"].dropna())
    )
    economic, regime = build_income_summaries(years, annual, stats, metadata)
    gompertz = build_gompertz_table(annual, bootstrap, regime)
    pareto = build_pareto_table(annual, bootstrap, regime, curves)
    validate_tables(gompertz, pareto, economic)

    metadata_table = build_metadata_table(
        {
            GOMPERTZ_OUT.name: gompertz,
            PARETO_OUT.name: pareto,
            ECONOMIC_OUT.name: economic,
        }
    )

    _clean_paper_csvs()
    gompertz.to_csv(GOMPERTZ_OUT, index=False)
    pareto.to_csv(PARETO_OUT, index=False)
    economic.to_csv(ECONOMIC_OUT, index=False)
    metadata_table.to_csv(METADATA_OUT, index=False)

    generated = {path.name for path in TABLES_PAPER.glob("*.csv")}
    if generated != CANONICAL_TABLES:
        raise AssertionError(
            f"Unexpected paper tables after cleanup: {sorted(generated)}"
        )
    print(f"Canonical paper tables generated: {', '.join(sorted(generated))}")


if __name__ == "__main__":
    main()
