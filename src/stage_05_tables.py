"""Build the canonical paper-facing tables for Stage 05.

Statistical estimation and reproduction diagnostics are produced by Stage 03
and persisted directly in the canonical Gompertz and Pareto annual tables.
This module only consolidates those results with trusted microdata into
publication tables.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES_TRUSTED = ROOT / "assets" / "tables_analysis_trusted"
TABLES_PAPER = ROOT / "assets" / "tables_paper"
TRUSTED_DATA = ROOT / "data" / "trusted"
METADATA_PATH = ROOT / "data" / "metadata" / "df_metadata.xlsx"
GINI_REFERENCE_PATH = ROOT / "data" / "auxiliary" / "series_gini_ipea_banco_mundial.csv"
GDP_PATH = ROOT / "data" / "auxiliary" / "gdp_growth_brazil_1978_2025.csv"

START_YEAR, END_YEAR = 1978, 2025

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

TABLE_DESCRIPTIONS = {
    GOMPERTZ_OUT.name: (
        "Annual Gompertz-regime estimates, including the canonical fixed-A fit "
        "and the unconstrained least-squares A/B diagnostic."
    ),
    PARETO_OUT.name: (
        "Annual Pareto-tail estimates from log-log least squares and direct "
        "maximum likelihood, including transition and uncertainty diagnostics."
    ),
    ECONOMIC_OUT.name: (
        "Annual income, inequality, external-validation, and top-income-band "
        "statistics used in the paper."
    ),
    METADATA_OUT.name: (
        "Data dictionary describing the canonical paper tables, their columns, "
        "units, and primary derivations."
    ),
}

COLUMN_DESCRIPTIONS = {
    "year": "Survey/reference year.",
    "gompertz_A": "Canonical Gompertz A fixed at ln[ln(100)].",
    "gompertz_B": "Canonical Gompertz B estimated by least squares with A fixed.",
    "gompertz_B_bootstrap_se": "Bootstrap standard error of canonical fixed-A Gompertz B.",
    "gompertz_boundary_A_free": "Gompertz A from the unconstrained least-squares fit used as a boundary/replication diagnostic.",
    "gompertz_A_free_bootstrap_se": "Bootstrap standard error of unconstrained Gompertz A.",
    "gompertz_boundary_B_free": "Gompertz B from the unconstrained least-squares fit used as a boundary/replication diagnostic.",
    "gompertz_B_free_bootstrap_se": "Bootstrap standard error of unconstrained Gompertz B.",
    "gompertz_x_gmax": "Upper normalized-income boundary of the selected Gompertz regime.",
    "transition_x_t": "Normalized-income transition threshold between Gompertz and Pareto regimes.",
    "transition_delta_x_t": "Half-width of the Gompertz-Pareto transition interval when the regime boundaries differ.",
    "gompertz_r2": "Coefficient of determination for the canonical Gompertz fit.",
    "gompertz_correlation_coefficient": "Correlation coefficient associated with the canonical Gompertz fit.",
    "gompertz_population_pct": "Percentage of observations assigned to the Gompertz regime.",
    "gompertz_income_share_pct": "Percentage of total income below the Gompertz-Pareto transition threshold.",
    "pareto_x_pmin": "Selected lower normalized-income boundary of the Pareto fit.",
    "pareto_selection_status": "Operational status returned by the Pareto-tail selection rule.",
    "pareto_supported": "Whether the selected Pareto tail satisfies the configured support criterion.",
    "pareto_alpha_ls": "Pareto exponent alpha estimated by log-log least squares.",
    "pareto_alpha_ls_bootstrap_se": "Bootstrap standard error of the least-squares Pareto alpha.",
    "pareto_beta_ls": "Pareto amplitude beta estimated by log-log least squares.",
    "pareto_beta_ls_bootstrap_se": "Bootstrap standard error of the least-squares Pareto beta.",
    "pareto_ls_r2": "Coefficient of determination for the log-log least-squares Pareto fit.",
    "pareto_ls_correlation_coefficient": "Correlation coefficient associated with the log-log Pareto fit.",
    "pareto_alpha_mle": "Pareto exponent alpha estimated by direct maximum likelihood above x_t.",
    "pareto_alpha_mle_fisher_se": "Fisher-information standard error of direct-MLE Pareto alpha.",
    "pareto_alpha_mle_likelihood_se": "Likelihood-width standard error of direct-MLE Pareto alpha following the 2009 prescription.",
    "pareto_alpha_mle_bootstrap_se": "Bootstrap standard error of direct-MLE Pareto alpha.",
    "pareto_beta_mle_continuity": "Pareto amplitude beta obtained by imposing Gompertz-Pareto continuity at x_t.",
    "pareto_beta_mle_likelihood_se": "Uncertainty propagated to continuity-based Pareto beta from the likelihood-width alpha error.",
    "pareto_beta_mle_bootstrap_se": "Bootstrap standard error of continuity-based Pareto beta.",
    "pareto_mle_r2": "Coefficient of determination for the direct-MLE Pareto curve against the empirical CCDF.",
    "pareto_mle_correlation_coefficient": "Correlation coefficient associated with the direct-MLE Pareto fit.",
    "pareto_population_pct": "Percentage of observations assigned to the Pareto regime.",
    "pareto_income_share_pct": "Percentage of total income at or above the Gompertz-Pareto transition threshold.",
    "bootstrap_reps": "Number of bootstrap replications.",
    "gdp_growth_pct": "Annual Brazilian real GDP growth rate.",
    "income_observation_n": "Number of positive trusted income observations used in the annual summary.",
    "income_mean_2025_usd": "Mean annual income converted to 2025 US dollars.",
    "income_median_2025_usd": "Median annual income converted to 2025 US dollars.",
    "income_std_2025_usd": "Standard deviation of annual income converted to 2025 US dollars.",
    "gini_pnad": "Gini coefficient estimated from the PNAD income sample.",
    "pietra_pnad": "Pietra inequality index estimated from the PNAD income sample.",
    "kolkata_pnad": "Kolkata inequality index estimated from the PNAD income sample.",
    "zanardi_pnad": "Zanardi inequality index estimated from the PNAD income sample.",
    "gini_ipea": "External annual Gini reference from IPEA when available.",
    "gini_world_bank": "External annual Gini reference from the World Bank when available.",
}


def _year_filter(frame):
    out = frame.copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    return out[(out["year"] >= START_YEAR) & (out["year"] <= END_YEAR)].copy()


def _load_metadata():
    metadata = pd.read_excel(METADATA_PATH).rename(columns={"ano": "year"})
    metadata = _year_filter(metadata)
    gini = pd.read_csv(GINI_REFERENCE_PATH).rename(
        columns={"ano": "year", "ipea": "gini_ipea", "banco_mundial": "gini_world_bank"}
    )
    gini = _year_filter(gini)
    for column in ("gini_ipea", "gini_world_bank"):
        gini[column] = pd.to_numeric(gini[column], errors="coerce")
        finite = gini[column].dropna()
        if not finite.empty and finite.max() > 1.5:
            gini[column] /= 100.0
    return metadata.merge(
        gini[["year", "gini_ipea", "gini_world_bank"]], on="year", how="left"
    )


def _adjusted_income(year, metadata_index):
    frame = pd.read_parquet(
        TRUSTED_DATA / f"pnad_trusted_{year}.parquet", columns=["renda"]
    )
    income = pd.to_numeric(frame["renda"], errors="coerce").to_numpy(float)
    income = income[np.isfinite(income) & (income > 0)]
    if income.size == 0:
        raise ValueError(f"{year}: no positive trusted income")
    row = metadata_index.loc[year]
    exchange, inflation = float(row["Exchange"]), float(row["Inflation"])
    if exchange <= 0 or inflation <= 0 or not np.isfinite(exchange * inflation):
        raise ValueError(f"{year}: invalid monetary metadata")
    return income / exchange * inflation


def _band_record(values, total, prefix):
    values = np.asarray(values, float)
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
        f"{prefix}_income_share_pct": 100.0 * float(values.sum()) / total,
        f"{prefix}_mean_income_2025_usd": float(values.mean()),
        f"{prefix}_median_income_2025_usd": float(np.median(values)),
        f"{prefix}_std_income_2025_usd": (
            float(np.std(values, ddof=1)) if values.size > 1 else np.nan
        ),
    }


def build_income_summaries(years, annual, stats, metadata):
    annual_i = annual.set_index("year")
    stats_i = stats.set_index("year")
    metadata_i = metadata.set_index("year")
    gdp = _year_filter(pd.read_csv(GDP_PATH)).set_index("year")
    economic_rows, regime_rows = [], []

    for year in years:
        adjusted = np.sort(_adjusted_income(year, metadata_i))
        total, n = float(adjusted.sum()), int(adjusted.size)
        if total <= 0:
            raise ValueError(f"{year}: non-positive trusted income total")

        i90, i99, i999 = int(0.90 * n), int(0.99 * n), int(0.999 * n)
        xt = float(annual_i.loc[year, "transition_x_t"])
        normalized = adjusted / adjusted.mean()
        gshare = 100.0 * float(adjusted[normalized < xt].sum()) / total
        regime_rows.append(
            {
                "year": year,
                "gompertz_income_share_pct": gshare,
                "pareto_income_share_pct": 100.0 - gshare,
            }
        )

        s, m = stats_i.loc[year], metadata_i.loc[year]
        row = {
            "year": year,
            "gdp_growth_pct": (
                float(gdp.loc[year, "gdp_growth_pct"]) if year in gdp.index else np.nan
            ),
            "income_observation_n": n,
            "income_mean_2025_usd": float(adjusted.mean()),
            "income_median_2025_usd": float(np.median(adjusted)),
            "income_std_2025_usd": (
                float(np.std(adjusted, ddof=1)) if n > 1 else np.nan
            ),
            "gini_pnad": float(s["Gini"]),
            "pietra_pnad": float(s["Pietra"]),
            "kolkata_pnad": float(s["Kolkata"]),
            "zanardi_pnad": float(s["Zanardi"]),
            "gini_ipea": float(m["gini_ipea"]) if pd.notna(m["gini_ipea"]) else np.nan,
            "gini_world_bank": (
                float(m["gini_world_bank"]) if pd.notna(m["gini_world_bank"]) else np.nan
            ),
        }
        row.update(_band_record(adjusted[i90:i99], total, "p90_p99"))
        row.update(_band_record(adjusted[i99:i999], total, "p99_p999"))
        row.update(_band_record(adjusted[i999:], total, "p999_p100"))
        economic_rows.append(row)

    return pd.DataFrame(economic_rows), pd.DataFrame(regime_rows)


def load_annual_fits():
    gompertz = _year_filter(pd.read_csv(TABLES_TRUSTED / "gompertz_annual.csv"))
    pareto = _year_filter(pd.read_csv(TABLES_TRUSTED / "pareto_annual.csv"))
    annual = gompertz.merge(
        pareto,
        on="year",
        how="inner",
        validate="one_to_one",
        suffixes=("", "_pareto"),
    )
    if "bootstrap_reps_pareto" in annual:
        if not np.array_equal(
            annual["bootstrap_reps"].to_numpy(),
            annual["bootstrap_reps_pareto"].to_numpy(),
        ):
            raise AssertionError("Gompertz and Pareto bootstrap replication counts differ")
        annual = annual.drop(columns=["bootstrap_reps_pareto"])
    return annual


def build_gompertz_table(annual):
    t = annual.copy()
    t["gompertz_correlation_coefficient"] = np.sqrt(
        np.clip(pd.to_numeric(t["gompertz_r2"], errors="coerce"), 0, 1)
    )
    columns = [
        "year",
        "gompertz_A",
        "gompertz_B",
        "gompertz_B_bootstrap_se",
        "gompertz_boundary_A_free",
        "gompertz_A_free_bootstrap_se",
        "gompertz_boundary_B_free",
        "gompertz_B_free_bootstrap_se",
        "gompertz_x_gmax",
        "transition_x_t",
        "gompertz_r2",
        "gompertz_correlation_coefficient",
        "gompertz_population_pct",
        "gompertz_income_share_pct",
        "bootstrap_reps",
    ]
    return t[columns].sort_values("year").reset_index(drop=True)


def build_pareto_table(annual):
    t = annual.copy()
    t["pareto_ls_correlation_coefficient"] = np.sqrt(
        np.clip(pd.to_numeric(t["pareto_ls_r2"], errors="coerce"), 0, 1)
    )
    t["pareto_mle_correlation_coefficient"] = np.sqrt(
        np.clip(pd.to_numeric(t["pareto_mle_r2"], errors="coerce"), 0, 1)
    )
    columns = [
        "year",
        "pareto_x_pmin",
        "transition_x_t",
        "transition_delta_x_t",
        "pareto_selection_status",
        "pareto_supported",
        "pareto_alpha_ls",
        "pareto_alpha_ls_bootstrap_se",
        "pareto_beta_ls",
        "pareto_beta_ls_bootstrap_se",
        "pareto_ls_r2",
        "pareto_ls_correlation_coefficient",
        "pareto_alpha_mle",
        "pareto_alpha_mle_fisher_se",
        "pareto_alpha_mle_likelihood_se",
        "pareto_alpha_mle_bootstrap_se",
        "pareto_beta_mle_continuity",
        "pareto_beta_mle_likelihood_se",
        "pareto_beta_mle_bootstrap_se",
        "pareto_mle_r2",
        "pareto_mle_correlation_coefficient",
        "pareto_population_pct",
        "pareto_income_share_pct",
        "bootstrap_reps",
    ]
    return t[columns].sort_values("year").reset_index(drop=True)


def _column_metadata(table_name, column):
    source = "Stage-05 consolidation"
    unit = "dimensionless"
    description = COLUMN_DESCRIPTIONS.get(
        column, column.replace("_", " ").capitalize() + "."
    )

    if column == "year":
        unit, source = "year", "PNAD / annual series"
    elif column == "pareto_selection_status":
        unit, source = "text", "Stage-03 analytical diagnostics"
    elif column == "pareto_supported":
        unit, source = "boolean", "Stage-03 analytical diagnostics"
    elif column.endswith("_pct"):
        unit = "%"
    elif column.endswith("_n") or column == "bootstrap_reps":
        unit = "count"
    elif "2025_usd" in column:
        unit = "2025 US$"
    elif column in {
        "gompertz_x_gmax",
        "pareto_x_pmin",
        "transition_x_t",
        "transition_delta_x_t",
    }:
        unit = "normalized income"
    elif "beta" in column:
        unit = "CCDF-percent scale"

    return description, unit, source


def build_metadata_table(tables):
    rows = []
    for table_name, frame in tables.items():
        table_description = TABLE_DESCRIPTIONS[table_name]
        for column in frame.columns:
            description, unit, source = _column_metadata(table_name, column)
            rows.append(
                {
                    "table_name": table_name,
                    "table_description": table_description,
                    "column_name": column,
                    "description": description,
                    "unit": unit,
                    "source": source,
                }
            )

    metadata_columns = {
        "table_name": "Canonical paper table containing the documented field.",
        "table_description": "Human-readable description of the table as a whole.",
        "column_name": "Column documented by this metadata row.",
        "description": "Human-readable definition of the column.",
        "unit": "Measurement unit or scale.",
        "source": "Primary source or derivation.",
    }
    for column, description in metadata_columns.items():
        rows.append(
            {
                "table_name": METADATA_OUT.name,
                "table_description": TABLE_DESCRIPTIONS[METADATA_OUT.name],
                "column_name": column,
                "description": description,
                "unit": "text",
                "source": "paper table schema",
            }
        )
    return pd.DataFrame(rows)


def validate_tables(gompertz, pareto, economic):
    merged = gompertz[["year", "gompertz_income_share_pct"]].merge(
        pareto[["year", "pareto_income_share_pct"]],
        on="year",
        validate="one_to_one",
    )
    if not np.allclose(
        merged["gompertz_income_share_pct"] + merged["pareto_income_share_pct"],
        100.0,
        atol=1e-8,
    ):
        raise AssertionError("Gompertz and Pareto income shares must sum to 100%")
    for frame in (gompertz, pareto, economic):
        if frame["year"].duplicated().any():
            raise AssertionError("Annual paper tables must have unique years")


def validate_persisted_regime_shares(annual, recomputed):
    check = annual[["year", "gompertz_income_share_pct", "pareto_income_share_pct"]].merge(
        recomputed,
        on="year",
        validate="one_to_one",
        suffixes=("_persisted", "_recomputed"),
    )
    for prefix in ("gompertz", "pareto"):
        if not np.allclose(
            check[f"{prefix}_income_share_pct_persisted"],
            check[f"{prefix}_income_share_pct_recomputed"],
            atol=1e-8,
        ):
            raise AssertionError(f"Persisted and recomputed {prefix} income shares differ")


def _clean_paper_csvs():
    TABLES_PAPER.mkdir(parents=True, exist_ok=True)
    for path in TABLES_PAPER.glob("*.csv"):
        path.unlink()


def main():
    stats = _year_filter(pd.read_csv(TABLES_TRUSTED / "statistics_annual.csv"))
    annual = load_annual_fits()
    metadata = _load_metadata()
    years = sorted(
        set(annual["year"].dropna().astype(int))
        & set(stats["year"].dropna().astype(int))
    )

    economic, recomputed_regime = build_income_summaries(years, annual, stats, metadata)
    validate_persisted_regime_shares(annual, recomputed_regime)
    gompertz = build_gompertz_table(annual)
    pareto = build_pareto_table(annual)
    validate_tables(gompertz, pareto, economic)

    metadata_table = build_metadata_table(
        {
            GOMPERTZ_OUT.name: gompertz,
            PARETO_OUT.name: pareto,
            ECONOMIC_OUT.name: economic,
        }
    )

    _clean_paper_csvs()
    outputs = (
        (GOMPERTZ_OUT, gompertz),
        (PARETO_OUT, pareto),
        (ECONOMIC_OUT, economic),
        (METADATA_OUT, metadata_table),
    )
    for path, frame in outputs:
        frame.to_csv(path, index=False)

    generated = {path.name for path in TABLES_PAPER.glob("*.csv")}
    if generated != CANONICAL_TABLES:
        raise AssertionError(f"Unexpected paper tables: {sorted(generated)}")
    print("Canonical Stage-05 tables generated: " + ", ".join(sorted(generated)))
    return {path.name: frame for path, frame in outputs}


if __name__ == "__main__":
    main()
