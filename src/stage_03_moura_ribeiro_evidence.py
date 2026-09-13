"""Augment the canonical Stage-03 tables with Moura Jr.--Ribeiro diagnostics.

The baseline (refined) and benchmark (trusted) analytical layers deliberately
share the same table names and schemas.  This module computes the bootstrap,
likelihood-width and reproduction diagnostics required by the 2009 method, but
stores them directly in ``gompertz_annual.csv`` and ``pareto_annual.csv``.
No separate bootstrap or reproduction CSV is persisted.

Each analytical layer therefore contains the same six scientific tables plus a
``metadata.csv`` data dictionary.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data" / "metadata" / "df_metadata.xlsx"

START_YEAR, END_YEAR = 1978, 2025
BOOTSTRAP_REPS = int(os.environ.get("PNAD_BOOTSTRAP_REPS", "1000"))
BOOTSTRAP_SEED = 20090101
LIKELIHOOD_GRID_SIZE = 12001

LAYER_CONFIG = {
    "refined": {
        "role": "baseline",
        "data": ROOT / "data" / "refined",
        "tables": ROOT / "assets" / "tables_analysis_refined",
        "pattern": "pnad_refined_{year}.parquet",
    },
    "trusted": {
        "role": "benchmark",
        "data": ROOT / "data" / "trusted",
        "tables": ROOT / "assets" / "tables_analysis_trusted",
        "pattern": "pnad_trusted_{year}.parquet",
    },
}

ANALYSIS_TABLES = (
    "statistics_annual.csv",
    "geometric_bins.csv",
    "gompertz_annual.csv",
    "pareto_annual.csv",
    "gompertz_pareto_curves.csv",
    "lorenz.csv",
)
METADATA_FILE = "metadata.csv"
CANONICAL_FILES = set(ANALYSIS_TABLES) | {METADATA_FILE}

TABLE_DESCRIPTIONS = {
    "statistics_annual.csv": (
        "Annual descriptive statistics, inequality indices, concentration measures, "
        "and external Gini validation for the analytical income sample."
    ),
    "geometric_bins.csv": (
        "Geometric-bin summaries of annual adjusted income distributions using the "
        "canonical bin ratio 1.10."
    ),
    "gompertz_annual.csv": (
        "Annual Gompertz-regime estimates, boundary diagnostics, bootstrap "
        "uncertainties, exponential comparison diagnostics, and regime income share."
    ),
    "pareto_annual.csv": (
        "Annual Pareto-tail estimates from log-log least squares and direct maximum "
        "likelihood, including bootstrap and likelihood-width uncertainties."
    ),
    "gompertz_pareto_curves.csv": (
        "Binned empirical CCDF and fitted Gompertz/Pareto curves used for regime "
        "selection, estimation, diagnostics, and figures."
    ),
    "lorenz.csv": (
        "Annual Lorenz-curve coordinates on the common population-share grid."
    ),
    METADATA_FILE: (
        "Data dictionary describing every canonical Stage-03 analytical table and "
        "column."
    ),
}

GOMPERTZ_DIAGNOSTIC_COLUMNS = [
    "bootstrap_reps",
    "gompertz_B_bootstrap_se",
    "gompertz_A_free_bootstrap_se",
    "gompertz_B_free_bootstrap_se",
    "exponential_intercept",
    "exponential_alpha",
    "exponential_r2",
    "gompertz_income_share_pct",
]

PARETO_DIAGNOSTIC_COLUMNS = [
    "bootstrap_reps",
    "pareto_alpha_ls_bootstrap_se",
    "pareto_beta_ls_bootstrap_se",
    "pareto_alpha_mle_likelihood_se",
    "pareto_alpha_mle_bootstrap_se",
    "pareto_beta_mle_likelihood_se",
    "pareto_beta_mle_bootstrap_se",
    "pareto_mle_r2",
    "pareto_supported",
    "pareto_income_share_pct",
]


def years_of(values) -> list[int]:
    return sorted(
        int(year)
        for year in values
        if pd.notna(year) and START_YEAR <= int(year) <= END_YEAR
    )


def r2_log(observed, fitted) -> float:
    observed = np.asarray(observed, float)
    fitted = np.asarray(fitted, float)
    mask = (
        np.isfinite(observed)
        & np.isfinite(fitted)
        & (observed > 0)
        & (fitted > 0)
    )
    if mask.sum() < 2:
        return np.nan
    y = np.log(observed[mask])
    yh = np.log(fitted[mask])
    tss = float(np.sum((y - y.mean()) ** 2))
    if tss <= 0:
        return np.nan
    return float(1.0 - np.sum((y - yh) ** 2) / tss)


def bootstrap_line(x, y, rng, reps=BOOTSTRAP_REPS):
    """Bootstrap an unconstrained line ``y = intercept + slope*x``."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3:
        nan = np.full(reps, np.nan)
        return nan.copy(), nan.copy()

    idx = rng.integers(0, len(x), size=(reps, len(x)))
    xb, yb = x[idx], y[idx]
    xm, ym = xb.mean(axis=1), yb.mean(axis=1)
    den = ((xb - xm[:, None]) ** 2).sum(axis=1)
    slope = np.divide(
        ((xb - xm[:, None]) * (yb - ym[:, None])).sum(axis=1),
        den,
        out=np.full(reps, np.nan),
        where=den > 0,
    )
    return ym - slope * xm, slope


def bootstrap_fixed_gompertz_B(x, y, A, rng, reps=BOOTSTRAP_REPS):
    """Bootstrap ``B`` in ``y=A-Bx`` while preserving the theoretical fixed A."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3:
        return np.full(reps, np.nan)

    idx = rng.integers(0, len(x), size=(reps, len(x)))
    xb, yb = x[idx], y[idx]
    den = (xb**2).sum(axis=1)
    num = (xb * (float(A) - yb)).sum(axis=1)
    return np.divide(
        num,
        den,
        out=np.full(reps, np.nan),
        where=den > 0,
    )


def likelihood_alpha_se(tail, x_t, grid_size=LIKELIHOOD_GRID_SIZE) -> float:
    """Numerically reproduce the likelihood-width error used in the 2009 paper."""
    tail = np.asarray(tail, float)
    tail = tail[np.isfinite(tail) & (tail >= x_t)]
    n = int(tail.size)
    if n < 2 or not np.isfinite(x_t) or x_t <= 0:
        return np.nan

    c = float(np.log(tail / x_t).sum())
    if c <= 0:
        return np.nan

    alpha_hat = float(n / c)
    fisher = alpha_hat / np.sqrt(n)
    upper = max(8.0, alpha_hat + 14.0 * max(fisher, 0.05))
    alpha = np.linspace(1.0, upper, int(grid_size))
    logw = n * np.log(alpha) - c * alpha
    logw -= np.max(logw)
    weight = np.exp(logw)
    norm = float(np.trapezoid(weight, alpha))
    if not np.isfinite(norm) or norm <= 0:
        return np.nan

    mean = float(np.trapezoid(alpha * weight, alpha) / norm)
    mean2 = float(np.trapezoid(alpha * alpha * weight, alpha) / norm)
    return float(np.sqrt(max(0.0, mean2 - mean * mean)))


def _load_layer(layer: str):
    if layer not in LAYER_CONFIG:
        raise ValueError(f"Unknown layer: {layer}")
    cfg = LAYER_CONFIG[layer]
    tables = cfg["tables"]

    gompertz = pd.read_csv(tables / "gompertz_annual.csv")
    pareto = pd.read_csv(tables / "pareto_annual.csv")
    curves = pd.read_csv(tables / "gompertz_pareto_curves.csv")
    annual = gompertz.merge(
        pareto,
        on="year",
        how="inner",
        validate="one_to_one",
        suffixes=("", "_pareto"),
    )
    metadata = pd.read_excel(METADATA).rename(columns={"ano": "year"})

    for frame in (gompertz, pareto, annual, curves, metadata):
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")

    years = years_of(annual["year"].dropna())
    return cfg, gompertz, pareto, annual, curves, metadata, years


def _income(year: int, cfg, positive=True) -> np.ndarray:
    path = cfg["data"] / cfg["pattern"].format(year=year)
    frame = pd.read_parquet(path, columns=["renda"])
    income = pd.to_numeric(frame["renda"], errors="coerce").to_numpy(float)
    income = income[np.isfinite(income)]
    return income[income > 0] if positive else income


def _normalized_income(year: int, cfg) -> np.ndarray:
    x = _income(year, cfg, positive=True)
    mean = float(np.mean(x))
    if x.size == 0 or not np.isfinite(mean) or mean <= 0:
        raise ValueError(f"{year}: invalid positive-income sample")
    return x / mean


def build_bootstrap_uncertainties(layer: str) -> pd.DataFrame:
    """Compute annual bootstrap uncertainties without persisting a separate CSV."""
    cfg, _, _, annual, curves, _, years = _load_layer(layer)
    annual_i = annual.set_index("year")
    rows = []

    for year in years:
        fit = annual_i.loc[year]
        rng = np.random.default_rng(BOOTSTRAP_SEED + year)

        x_gmax = float(fit["gompertz_x_gmax"])
        g = curves[
            (curves["year"] == year)
            & (curves["income_normalized"] <= x_gmax)
            & curves["gompertz_transform"].notna()
        ]
        xg = g["income_normalized"].to_numpy(float)
        yg = g["gompertz_transform"].to_numpy(float)
        fixed_B = bootstrap_fixed_gompertz_B(
            xg, yg, float(fit["gompertz_A"]), rng
        )
        free_A, free_slope = bootstrap_line(xg, yg, rng)
        free_B = -free_slope

        x_pmin = float(fit["pareto_x_pmin"])
        p = curves[
            (curves["year"] == year)
            & (curves["income_normalized"] >= x_pmin)
            & (curves["empirical_ccdf_percent"] > 0)
        ]
        ls_intercept, ls_slope = bootstrap_line(
            np.log(p["income_normalized"].to_numpy(float)),
            np.log(p["empirical_ccdf_percent"].to_numpy(float)),
            rng,
        )

        x_t = float(fit["transition_x_t"])
        x = _normalized_income(year, cfg)
        z = np.log(x[x >= x_t] / x_t)
        n = int(len(z))
        if n < 2:
            alpha_mle = np.full(BOOTSTRAP_REPS, np.nan)
        else:
            idx = rng.integers(0, n, size=(BOOTSTRAP_REPS, n))
            sums = z[idx].sum(axis=1)
            alpha_mle = np.divide(
                n,
                sums,
                out=np.full(BOOTSTRAP_REPS, np.nan),
                where=sums > 0,
            )

        f_t = float(
            np.exp(
                np.exp(
                    float(fit["gompertz_A"])
                    - float(fit["gompertz_B"]) * x_t
                )
            )
        )
        beta_mle = f_t * x_t**alpha_mle

        def sd(values):
            return float(np.nanstd(values, ddof=1))

        rows.append(
            {
                "year": year,
                "bootstrap_reps": BOOTSTRAP_REPS,
                "gompertz_B_bootstrap_se": sd(fixed_B),
                "gompertz_A_free_bootstrap_se": sd(free_A),
                "gompertz_B_free_bootstrap_se": sd(free_B),
                "pareto_alpha_ls_bootstrap_se": sd(-ls_slope),
                "pareto_beta_ls_bootstrap_se": sd(np.exp(ls_intercept)),
                "pareto_alpha_mle_bootstrap_se": sd(alpha_mle),
                "pareto_beta_mle_bootstrap_se": sd(beta_mle),
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def _exponential_diagnostics(curves, fit, year):
    x_gmax = float(fit["gompertz_x_gmax"])
    d = curves[
        (curves["year"] == year)
        & (curves["income_normalized"] <= x_gmax)
        & (curves["empirical_ccdf_percent"] > 0)
    ]
    x = d["income_normalized"].to_numpy(float)
    y = np.log(d["empirical_ccdf_percent"].to_numpy(float))
    if len(x) < 2 or np.unique(x).size < 2:
        return np.nan, np.nan, np.nan
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    tss = float(np.sum((y - y.mean()) ** 2))
    r2 = np.nan if tss <= 0 else float(1.0 - np.sum((y - fitted) ** 2) / tss)
    return float(intercept), float(-slope), r2


def _mle_r2(curves, fit, year):
    x_t = float(fit["transition_x_t"])
    d = curves[
        (curves["year"] == year)
        & (curves["income_normalized"] >= x_t)
        & (curves["empirical_ccdf_percent"] > 0)
    ]
    return r2_log(
        d["empirical_ccdf_percent"],
        d["pareto_fitted_ccdf_percent_mle"],
    )


def build_diagnostics_annual(layer: str) -> pd.DataFrame:
    """Compute non-bootstrap annual diagnostics required downstream."""
    cfg, _, _, annual, curves, _, years = _load_layer(layer)
    annual_i = annual.set_index("year")
    rows = []

    for year in years:
        fit = annual_i.loc[year]
        x = _normalized_income(year, cfg)
        x_t = float(fit["transition_x_t"])
        tail = x[x >= x_t]
        total_income = float(np.sum(x))
        gompertz_income_share = 100.0 * float(np.sum(x[x < x_t])) / total_income
        pareto_income_share = 100.0 - gompertz_income_share

        likelihood_se = likelihood_alpha_se(tail, x_t)
        beta_mle = float(fit["pareto_beta_mle_continuity"])
        beta_likelihood_se = (
            abs(beta_mle * np.log(x_t) * likelihood_se)
            if np.isfinite(likelihood_se) and x_t > 0
            else np.nan
        )
        exp_intercept, exp_alpha, exp_r2 = _exponential_diagnostics(
            curves, fit, year
        )
        pareto_supported = (
            str(fit["pareto_selection_status"])
            == "earliest_tail_start_with_r2_ge_0.98"
        )

        rows.append(
            {
                "year": year,
                "exponential_intercept": exp_intercept,
                "exponential_alpha": exp_alpha,
                "exponential_r2": exp_r2,
                "gompertz_income_share_pct": gompertz_income_share,
                "pareto_alpha_mle_likelihood_se": likelihood_se,
                "pareto_beta_mle_likelihood_se": beta_likelihood_se,
                "pareto_mle_r2": _mle_r2(curves, fit, year),
                "pareto_supported": bool(pareto_supported),
                "pareto_income_share_pct": pareto_income_share,
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def _description(column: str) -> str:
    explicit = {
        "year": "Survey/reference year.",
        "bootstrap_reps": "Number of bootstrap replications.",
        "gompertz_A": "Canonical Gompertz A fixed at ln[ln(100)].",
        "gompertz_B": "Canonical Gompertz B estimated by least squares with A fixed.",
        "gompertz_B_bootstrap_se": "Bootstrap standard error of canonical fixed-A Gompertz B.",
        "gompertz_boundary_A_free": "Free-intercept Gompertz A used for boundary and reproduction diagnostics.",
        "gompertz_boundary_B_free": "Free-intercept Gompertz B used for boundary and reproduction diagnostics.",
        "gompertz_A_free_bootstrap_se": "Bootstrap standard error of free-intercept Gompertz A.",
        "gompertz_B_free_bootstrap_se": "Bootstrap standard error of free-intercept Gompertz B.",
        "gompertz_x_gmax": "Upper normalized-income boundary of the selected Gompertz regime.",
        "gompertz_income_share_pct": "Percentage of total income below the Gompertz-Pareto transition threshold.",
        "pareto_x_pmin": "Lower normalized-income boundary of the selected Pareto tail.",
        "transition_x_t": "Normalized-income transition threshold between Gompertz and Pareto regimes.",
        "transition_delta_x_t": "Half-width of the transition interval when regime boundaries differ.",
        "pareto_alpha_ls": "Pareto exponent estimated by log-log least squares.",
        "pareto_beta_ls": "Pareto amplitude estimated by log-log least squares.",
        "pareto_alpha_mle": "Pareto exponent estimated by direct maximum likelihood above x_t.",
        "pareto_alpha_mle_fisher_se": "Fisher-information standard error of the direct-MLE Pareto exponent.",
        "pareto_alpha_mle_likelihood_se": "Likelihood-width standard error of the direct-MLE Pareto exponent.",
        "pareto_alpha_mle_bootstrap_se": "Bootstrap standard error of the direct-MLE Pareto exponent.",
        "pareto_beta_mle_continuity": "Pareto amplitude obtained by Gompertz-Pareto continuity at x_t.",
        "pareto_beta_mle_likelihood_se": "Uncertainty propagated to continuity-based Pareto beta from the likelihood-width alpha error.",
        "pareto_beta_mle_bootstrap_se": "Bootstrap standard error of continuity-based Pareto beta.",
        "pareto_income_share_pct": "Percentage of total income at or above the transition threshold.",
        "pareto_supported": "Whether the selected Pareto tail satisfies the configured support criterion.",
        "exponential_intercept": "Intercept of the exponential-body diagnostic fitted on the selected Gompertz interval.",
        "exponential_alpha": "Positive decay coefficient of the exponential-body diagnostic.",
        "exponential_r2": "Coefficient of determination of the exponential-body diagnostic.",
        "population_share": "Cumulative population share on the Lorenz grid.",
        "income_share": "Cumulative income share on the Lorenz grid.",
        "bin_left": "Left boundary of the geometric income bin.",
        "bin_right": "Right boundary of the geometric income bin.",
        "bin_center_geo": "Geometric center of the income bin.",
        "N_bin": "Number of observations in the geometric income bin.",
        "income_normalized": "Income normalized by the annual positive-income mean.",
        "empirical_ccdf_percent": "Empirical complementary cumulative distribution in percent.",
        "empirical_ccdf_probability": "Empirical complementary cumulative distribution as a probability.",
        "gompertz_transform": "Transformed empirical CCDF ln[ln(F)] on the percent scale.",
        "regime": "Regime label assigned relative to the Gompertz-Pareto transition.",
    }
    if column in explicit:
        return explicit[column]
    if column.endswith("_r2") or column.endswith("_r2_free"):
        return "Coefficient of determination for the indicated fit."
    if column.endswith("_sse"):
        return "Sum of squared errors for the indicated fit."
    if column.endswith("_pct"):
        return column.replace("_", " ").capitalize() + "."
    return column.replace("_", " ").capitalize() + "."


def _unit(column: str) -> str:
    if column == "year":
        return "year"
    if column in {"regime", "gompertz_selection_status", "pareto_selection_status", "transition_rule"}:
        return "text"
    if column == "pareto_supported":
        return "boolean"
    if column.endswith("_pct") or column == "empirical_ccdf_percent":
        return "%"
    if column.endswith("_n") or column in {"N", "N_valid", "N_bin", "bootstrap_reps", "observations_in_bin", "positive_income_observation_n", "gompertz_point_n", "pareto_population_n", "gompertz_population_n"}:
        return "count"
    if "2025_usd" in column or column.endswith("_income_adj") or column == "income_adj_2025_usd":
        return "2025 US$"
    if column in {"income_normalized", "bin_right_normalized", "gompertz_x_gmax", "pareto_x_pmin", "transition_x_t", "transition_delta_x_t", "cutoff_normalized"}:
        return "normalized income"
    if column in {"population_share", "income_share", "ccdf", "empirical_ccdf_probability", "top_10", "top_1", "top_01"}:
        return "fraction"
    if "beta" in column and "gompertz" not in column:
        return "CCDF-percent scale"
    return "dimensionless"


def build_metadata_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for table_name in ANALYSIS_TABLES:
        frame = frames[table_name]
        for column in frame.columns:
            rows.append(
                {
                    "table_name": table_name,
                    "table_description": TABLE_DESCRIPTIONS[table_name],
                    "column_name": column,
                    "description": _description(column),
                    "unit": _unit(column),
                    "source": "Stage 03 analytical pipeline",
                }
            )

    metadata_columns = {
        "table_name": "Canonical Stage-03 table containing the documented field.",
        "table_description": "Human-readable description of the table as a whole.",
        "column_name": "Column documented by this metadata row.",
        "description": "Human-readable definition of the column.",
        "unit": "Measurement unit or scale.",
        "source": "Primary source or derivation.",
    }
    for column, description in metadata_columns.items():
        rows.append(
            {
                "table_name": METADATA_FILE,
                "table_description": TABLE_DESCRIPTIONS[METADATA_FILE],
                "column_name": column,
                "description": description,
                "unit": "text",
                "source": "Stage 03 metadata schema",
            }
        )
    return pd.DataFrame(rows)


def run_layer(layer: str):
    cfg, gompertz, pareto, _, _, _, _ = _load_layer(layer)
    bootstrap = build_bootstrap_uncertainties(layer)
    diagnostics = build_diagnostics_annual(layer)

    g_extra = bootstrap[
        [
            "year",
            "bootstrap_reps",
            "gompertz_B_bootstrap_se",
            "gompertz_A_free_bootstrap_se",
            "gompertz_B_free_bootstrap_se",
        ]
    ].merge(
        diagnostics[
            [
                "year",
                "exponential_intercept",
                "exponential_alpha",
                "exponential_r2",
                "gompertz_income_share_pct",
            ]
        ],
        on="year",
        validate="one_to_one",
    )
    p_extra = bootstrap[
        [
            "year",
            "bootstrap_reps",
            "pareto_alpha_ls_bootstrap_se",
            "pareto_beta_ls_bootstrap_se",
            "pareto_alpha_mle_bootstrap_se",
            "pareto_beta_mle_bootstrap_se",
        ]
    ].merge(
        diagnostics[
            [
                "year",
                "pareto_alpha_mle_likelihood_se",
                "pareto_beta_mle_likelihood_se",
                "pareto_mle_r2",
                "pareto_supported",
                "pareto_income_share_pct",
            ]
        ],
        on="year",
        validate="one_to_one",
    )

    gompertz = (
        gompertz.drop(columns=GOMPERTZ_DIAGNOSTIC_COLUMNS, errors="ignore")
        .merge(g_extra, on="year", how="left", validate="one_to_one")
        .sort_values("year")
        .reset_index(drop=True)
    )
    pareto = (
        pareto.drop(columns=PARETO_DIAGNOSTIC_COLUMNS, errors="ignore")
        .merge(p_extra, on="year", how="left", validate="one_to_one")
        .sort_values("year")
        .reset_index(drop=True)
    )

    tables = cfg["tables"]
    tables.mkdir(parents=True, exist_ok=True)
    gompertz.to_csv(tables / "gompertz_annual.csv", index=False)
    pareto.to_csv(tables / "pareto_annual.csv", index=False)

    for path in tables.glob("*.csv"):
        if path.name not in CANONICAL_FILES:
            path.unlink()

    frames = {
        name: (
            gompertz
            if name == "gompertz_annual.csv"
            else pareto
            if name == "pareto_annual.csv"
            else pd.read_csv(tables / name)
        )
        for name in ANALYSIS_TABLES
    }
    metadata = build_metadata_table(frames)
    metadata.to_csv(tables / METADATA_FILE, index=False)

    return {"gompertz": gompertz, "pareto": pareto, "metadata": metadata}


def validate_parallel_schemas():
    """Require baseline and benchmark analytical directories to be structurally identical."""
    refined = LAYER_CONFIG["refined"]["tables"]
    trusted = LAYER_CONFIG["trusted"]["tables"]
    refined_names = {p.name for p in refined.glob("*.csv")}
    trusted_names = {p.name for p in trusted.glob("*.csv")}
    if refined_names != CANONICAL_FILES or trusted_names != CANONICAL_FILES:
        raise AssertionError(
            "Refined/trusted analytical file sets must equal the canonical set: "
            f"refined={sorted(refined_names)}, trusted={sorted(trusted_names)}"
        )
    for name in sorted(CANONICAL_FILES):
        r_cols = list(pd.read_csv(refined / name, nrows=0).columns)
        t_cols = list(pd.read_csv(trusted / name, nrows=0).columns)
        if r_cols != t_cols:
            raise AssertionError(f"Schema mismatch for {name}: {r_cols} != {t_cols}")


def main():
    results = {layer: run_layer(layer) for layer in ("trusted", "refined")}
    validate_parallel_schemas()
    for layer, result in results.items():
        print(
            f"Stage 03 diagnostics ({layer}, {LAYER_CONFIG[layer]['role']}): "
            f"{len(result['gompertz'])} survey years; canonical schemas validated."
        )
    return results


if __name__ == "__main__":
    main()
