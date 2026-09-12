"""Build the canonical paper-facing tables for Stage 05.

Statistical estimation and reproduction diagnostics are produced by Stage 03.
This module only consolidates those persisted results with trusted microdata
into publication tables.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES_TRUSTED = ROOT / "assets" / "tables_analysis_trusted"
TABLES_REFINED = ROOT / "assets" / "tables_analysis_refined"
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
EVIDENCE_OUT = TABLES_PAPER / "table_05_moura_ribeiro_evidence.csv"
CANONICAL_TABLES = {
    GOMPERTZ_OUT.name,
    PARETO_OUT.name,
    ECONOMIC_OUT.name,
    METADATA_OUT.name,
    EVIDENCE_OUT.name,
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
    return metadata.merge(gini[["year", "gini_ipea", "gini_world_bank"]], on="year", how="left")


def _adjusted_income(year, metadata_index):
    frame = pd.read_parquet(TRUSTED_DATA / f"pnad_trusted_{year}.parquet", columns=["renda"])
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
        f"{prefix}_std_income_2025_usd": float(np.std(values, ddof=1)) if values.size > 1 else np.nan,
    }


def build_income_summaries(years, annual, stats, metadata):
    annual_i, stats_i, metadata_i = annual.set_index("year"), stats.set_index("year"), metadata.set_index("year")
    gdp = _year_filter(pd.read_csv(GDP_PATH)).set_index("year")
    economic_rows, regime_rows = [], []
    for year in years:
        adjusted = np.sort(_adjusted_income(year, metadata_i))
        total, n = float(adjusted.sum()), int(adjusted.size)
        if total <= 0:
            raise ValueError(f"{year}: non-positive trusted income total")
        i90, i99, i999 = int(.90*n), int(.99*n), int(.999*n)
        xt = float(annual_i.loc[year, "transition_x_t"])
        normalized = adjusted / adjusted.mean()
        gshare = 100.0 * float(adjusted[normalized < xt].sum()) / total
        regime_rows.append({"year": year, "gompertz_income_share_pct": gshare, "pareto_income_share_pct": 100.0-gshare})
        s, m = stats_i.loc[year], metadata_i.loc[year]
        row = {
            "year": year,
            "gdp_growth_pct": float(gdp.loc[year, "gdp_growth_pct"]) if year in gdp.index else np.nan,
            "income_observation_n": n,
            "income_mean_2025_usd": float(adjusted.mean()),
            "income_median_2025_usd": float(np.median(adjusted)),
            "income_std_2025_usd": float(np.std(adjusted, ddof=1)) if n > 1 else np.nan,
            "gini_pnad": float(s["Gini"]), "pietra_pnad": float(s["Pietra"]),
            "kolkata_pnad": float(s["Kolkata"]), "zanardi_pnad": float(s["Zanardi"]),
            "gini_ipea": float(m["gini_ipea"]) if pd.notna(m["gini_ipea"]) else np.nan,
            "gini_world_bank": float(m["gini_world_bank"]) if pd.notna(m["gini_world_bank"]) else np.nan,
        }
        row.update(_band_record(adjusted[i90:i99], total, "p90_p99"))
        row.update(_band_record(adjusted[i99:i999], total, "p99_p999"))
        row.update(_band_record(adjusted[i999:], total, "p999_p100"))
        economic_rows.append(row)
    return pd.DataFrame(economic_rows), pd.DataFrame(regime_rows)


def load_annual_fits():
    gompertz = _year_filter(pd.read_csv(TABLES_TRUSTED / "gompertz_annual.csv"))
    pareto = _year_filter(pd.read_csv(TABLES_TRUSTED / "pareto_annual.csv"))
    return gompertz.merge(pareto, on="year", how="inner", validate="one_to_one", suffixes=("", "_pareto"))


def build_gompertz_table(annual, bootstrap, regime):
    t = annual.merge(bootstrap, on="year", how="left").merge(regime, on="year", how="left")
    t["gompertz_correlation_coefficient"] = np.sqrt(np.clip(pd.to_numeric(t["gompertz_r2"], errors="coerce"), 0, 1))
    columns = [
        "year", "gompertz_A", "gompertz_B", "gompertz_B_bootstrap_se",
        "gompertz_boundary_A_free", "gompertz_A_free_bootstrap_se",
        "gompertz_boundary_B_free", "gompertz_B_free_bootstrap_se",
        "gompertz_x_gmax", "transition_x_t", "gompertz_r2",
        "gompertz_correlation_coefficient", "gompertz_population_pct",
        "gompertz_income_share_pct", "bootstrap_reps",
    ]
    return t[columns].sort_values("year").reset_index(drop=True)


def build_pareto_table(annual, bootstrap, regime, reproduction):
    diag = reproduction[["year", "pareto_mle_r2", "pareto_alpha_mle_likelihood_se", "pareto_beta_mle_likelihood_se", "pareto_supported"]]
    t = annual.merge(bootstrap, on="year", how="left").merge(regime, on="year", how="left").merge(diag, on="year", how="left")
    t["pareto_ls_correlation_coefficient"] = np.sqrt(np.clip(pd.to_numeric(t["pareto_ls_r2"], errors="coerce"), 0, 1))
    t["pareto_mle_correlation_coefficient"] = np.sqrt(np.clip(pd.to_numeric(t["pareto_mle_r2"], errors="coerce"), 0, 1))
    columns = [
        "year", "pareto_x_pmin", "transition_x_t", "transition_delta_x_t",
        "pareto_selection_status", "pareto_supported", "pareto_alpha_ls",
        "pareto_alpha_ls_bootstrap_se", "pareto_beta_ls", "pareto_beta_ls_bootstrap_se",
        "pareto_ls_r2", "pareto_ls_correlation_coefficient", "pareto_alpha_mle",
        "pareto_alpha_mle_fisher_se", "pareto_alpha_mle_likelihood_se",
        "pareto_alpha_mle_bootstrap_se", "pareto_beta_mle_continuity",
        "pareto_beta_mle_likelihood_se", "pareto_beta_mle_bootstrap_se",
        "pareto_mle_r2", "pareto_mle_correlation_coefficient", "pareto_population_pct",
        "pareto_income_share_pct", "bootstrap_reps",
    ]
    return t[columns].sort_values("year").reset_index(drop=True)


def build_evidence_table():
    refined = _year_filter(pd.read_csv(TABLES_REFINED / "moura_ribeiro_evidence_annual.csv"))
    trusted = _year_filter(pd.read_csv(TABLES_TRUSTED / "moura_ribeiro_evidence_annual.csv"))
    return pd.concat([refined, trusted], ignore_index=True).sort_values(["year", "layer", "paper_table", "test", "estimator", "parameter"]).reset_index(drop=True)


def _column_metadata(table_name, column):
    source = "Stage-05 consolidation"
    unit = "dimensionless"
    description = column.replace("_", " ").capitalize() + "."
    if column == "year": unit, source, description = "year", "PNAD / annual series", "Survey/reference year."
    elif column == "layer": unit, source, description = "text", "Stage-03 evidence", "Analysis layer: refined or trusted."
    elif column in {"paper_table", "test", "estimator", "parameter", "fit_metric", "criterion", "evidence_status", "pareto_selection_status"}:
        unit, source = "text", "Stage-03 reproduction diagnostics"
    elif column in {"passed", "within_paper_1se", "pareto_supported"}:
        unit, source = "boolean", "Stage-03 reproduction diagnostics"
    elif column.endswith("_pct") or column.endswith("_difference_pct"):
        unit = "%"
    elif column.endswith("_n") or column == "bootstrap_reps":
        unit = "count"
    elif "2025_usd" in column:
        unit = "2025 US$"
    elif column in {"gompertz_x_gmax", "pareto_x_pmin", "transition_x_t", "transition_delta_x_t"}:
        unit = "normalized income"
    elif "beta" in column:
        unit = "CCDF-percent scale"
    elif column in {"estimate", "standard_error", "paper_2009_value", "paper_2009_standard_error", "difference_from_2009"}:
        unit = "varies"
    if table_name == EVIDENCE_OUT.name:
        source = "Stage-03 refined/trusted evidence and Moura-Ribeiro 2009 reference"
    return description, unit, source


def build_metadata_table(tables):
    rows = []
    for table_name, frame in tables.items():
        for column in frame.columns:
            description, unit, source = _column_metadata(table_name, column)
            rows.append({"table_name": table_name, "column_name": column, "description": description, "unit": unit, "source": source})
    for column, description in {
        "table_name": "Canonical paper table containing the documented field.",
        "column_name": "Column documented by this metadata row.",
        "description": "Human-readable definition of the column.",
        "unit": "Measurement unit or scale.",
        "source": "Primary source or derivation.",
    }.items():
        rows.append({"table_name": METADATA_OUT.name, "column_name": column, "description": description, "unit": "text", "source": "paper table schema"})
    return pd.DataFrame(rows)


def validate_tables(gompertz, pareto, economic, evidence):
    merged = gompertz[["year", "gompertz_income_share_pct"]].merge(pareto[["year", "pareto_income_share_pct"]], on="year", validate="one_to_one")
    if not np.allclose(merged["gompertz_income_share_pct"] + merged["pareto_income_share_pct"], 100.0, atol=1e-8):
        raise AssertionError("Gompertz and Pareto income shares must sum to 100%")
    for frame in (gompertz, pareto, economic):
        if frame["year"].duplicated().any():
            raise AssertionError("Annual paper tables must have unique years")
    if set(evidence["layer"].dropna().unique()) != {"refined", "trusted"}:
        raise AssertionError("Evidence table must contain refined and trusted layers")
    required = {"year", "layer", "test", "estimator", "parameter", "estimate", "criterion", "evidence_status", "paper_2009_value", "difference_from_2009"}
    if missing := required - set(evidence.columns):
        raise AssertionError(f"Evidence table missing columns: {sorted(missing)}")


def _clean_paper_csvs():
    TABLES_PAPER.mkdir(parents=True, exist_ok=True)
    for path in TABLES_PAPER.glob("*.csv"):
        path.unlink()


def main():
    stats = _year_filter(pd.read_csv(TABLES_TRUSTED / "statistics_annual.csv"))
    annual = load_annual_fits()
    bootstrap = _year_filter(pd.read_csv(TABLES_TRUSTED / "moura_ribeiro_bootstrap_annual.csv"))
    reproduction = _year_filter(pd.read_csv(TABLES_TRUSTED / "moura_ribeiro_reproduction_annual.csv"))
    metadata = _load_metadata()
    years = sorted(set(annual["year"].dropna().astype(int)) & set(stats["year"].dropna().astype(int)))
    economic, regime = build_income_summaries(years, annual, stats, metadata)
    gompertz = build_gompertz_table(annual, bootstrap, regime)
    pareto = build_pareto_table(annual, bootstrap, regime, reproduction)
    evidence = build_evidence_table()
    validate_tables(gompertz, pareto, economic, evidence)
    metadata_table = build_metadata_table({GOMPERTZ_OUT.name: gompertz, PARETO_OUT.name: pareto, ECONOMIC_OUT.name: economic, EVIDENCE_OUT.name: evidence})
    _clean_paper_csvs()
    for path, frame in ((GOMPERTZ_OUT, gompertz), (PARETO_OUT, pareto), (ECONOMIC_OUT, economic), (METADATA_OUT, metadata_table), (EVIDENCE_OUT, evidence)):
        frame.to_csv(path, index=False)
    generated = {path.name for path in TABLES_PAPER.glob("*.csv")}
    if generated != CANONICAL_TABLES:
        raise AssertionError(f"Unexpected paper tables: {sorted(generated)}")
    print("Canonical Stage-05 tables generated: " + ", ".join(sorted(generated)))
    return {path.name: frame for path, frame in ((GOMPERTZ_OUT, gompertz), (PARETO_OUT, pareto), (ECONOMIC_OUT, economic), (METADATA_OUT, metadata_table), (EVIDENCE_OUT, evidence))}


if __name__ == "__main__":
    main()
