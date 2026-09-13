"""Moura Jr.--Ribeiro (2009) reproduction diagnostics for Stage 03.

This analytical module reads the canonical Stage-03 outputs for the refined
and trusted layers, reproduces the main statistical quantities used by Moura
Jr. and Ribeiro (EPJ B 67, 101--120, 2009), and quantifies uncertainty.

Two files are produced in each Stage-03 table directory:

- ``moura_ribeiro_bootstrap_annual.csv``: current-model bootstrap uncertainties
  plus free-intercept Gompertz bootstrap diagnostics;
- ``moura_ribeiro_reproduction_annual.csv``: one annual row collecting the
  quantities needed to reproduce the published tables and main fit tests.

The current project model keeps A = ln[ln(100)] fixed. The free-intercept
Gompertz estimates are retained separately because the 2009 paper reports A and
B from an unconstrained least-squares fit after using A approximately 1.53 as a
boundary diagnostic.
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
        "data": ROOT / "data" / "refined",
        "tables": ROOT / "assets" / "tables_analysis_refined",
        "pattern": "pnad_refined_{year}.parquet",
    },
    "trusted": {
        "data": ROOT / "data" / "trusted",
        "tables": ROOT / "assets" / "tables_analysis_trusted",
        "pattern": "pnad_trusted_{year}.parquet",
    },
}


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
    """Bootstrap an unconstrained line y = intercept + slope*x."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3:
        nan = np.full(reps, np.nan)
        return nan.copy(), nan.copy()

    idx = rng.integers(0, len(x), size=(reps, len(x)))
    xb = x[idx]
    yb = y[idx]
    xm = xb.mean(axis=1)
    ym = yb.mean(axis=1)
    den = ((xb - xm[:, None]) ** 2).sum(axis=1)
    slope = np.divide(
        ((xb - xm[:, None]) * (yb - ym[:, None])).sum(axis=1),
        den,
        out=np.full(reps, np.nan),
        where=den > 0,
    )
    intercept = ym - slope * xm
    return intercept, slope


def bootstrap_fixed_gompertz_B(x, y, A, rng, reps=BOOTSTRAP_REPS):
    """Bootstrap B in y=A-Bx while preserving the theoretical fixed A."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3:
        return np.full(reps, np.nan)

    idx = rng.integers(0, len(x), size=(reps, len(x)))
    xb = x[idx]
    yb = y[idx]
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

    stats = pd.read_csv(tables / "statistics_annual.csv")
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

    for frame in (stats, annual, curves, metadata):
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")

    years = years_of(annual["year"].dropna())
    return cfg, stats, annual, curves, metadata, years


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
    """Build annual uncertainty diagnostics for one Stage-03 data layer."""
    cfg, _, annual, curves, _, years = _load_layer(layer)
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
                "layer": layer,
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


def build_reproduction_annual(layer: str, bootstrap=None) -> pd.DataFrame:
    """Collect the annual quantities required for a 2009-paper reproduction."""
    cfg, stats, annual, curves, metadata, years = _load_layer(layer)
    if bootstrap is None:
        bootstrap = build_bootstrap_uncertainties(layer)

    annual_i = annual.set_index("year")
    stats_i = stats.set_index("year")
    metadata_i = metadata.set_index("year")
    boot_i = bootstrap.set_index("year")
    rows = []

    for year in years:
        fit = annual_i.loc[year]
        stat = stats_i.loc[year]
        meta = metadata_i.loc[year]
        boot = boot_i.loc[year]

        nominal = _income(year, cfg, positive=True)
        exchange = float(meta["Exchange"])
        if not np.isfinite(exchange) or exchange <= 0:
            raise ValueError(f"{year}: invalid Exchange")
        mean_income_usd_current_date = float(np.mean(nominal) / exchange)

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
        mle_r2 = _mle_r2(curves, fit, year)

        free_A = float(fit["gompertz_boundary_A_free"])
        free_B = float(fit["gompertz_boundary_B_free"])
        free_r2 = float(fit["gompertz_boundary_r2_free"])
        free_corr = np.sqrt(np.clip(free_r2, 0.0, 1.0))
        ls_r2 = float(fit["pareto_ls_r2"])
        ls_corr = np.sqrt(np.clip(ls_r2, 0.0, 1.0))
        pareto_supported = (
            str(fit["pareto_selection_status"])
            == "earliest_tail_start_with_r2_ge_0.98"
        )

        rows.append(
            {
                "year": year,
                "layer": layer,
                "mean_income_usd_current_date": mean_income_usd_current_date,
                "exponential_intercept": exp_intercept,
                "exponential_alpha": exp_alpha,
                "exponential_r2": exp_r2,
                "gompertz_A_fixed": float(fit["gompertz_A"]),
                "gompertz_B_fixed": float(fit["gompertz_B"]),
                "gompertz_B_fixed_bootstrap_se": float(
                    boot["gompertz_B_bootstrap_se"]
                ),
                "gompertz_A_free": free_A,
                "gompertz_A_free_bootstrap_se": float(
                    boot["gompertz_A_free_bootstrap_se"]
                ),
                "gompertz_B_free": free_B,
                "gompertz_B_free_bootstrap_se": float(
                    boot["gompertz_B_free_bootstrap_se"]
                ),
                "gompertz_x_gmax": float(fit["gompertz_x_gmax"]),
                "gompertz_free_r2": free_r2,
                "gompertz_free_correlation_coefficient": float(free_corr),
                "gompertz_population_pct": float(fit["gompertz_population_pct"]),
                "pareto_x_pmin": float(fit["pareto_x_pmin"]),
                "transition_x_t": x_t,
                "transition_delta_x_t": float(fit["transition_delta_x_t"]),
                "pareto_alpha_ls": float(fit["pareto_alpha_ls"]),
                "pareto_alpha_ls_bootstrap_se": float(
                    boot["pareto_alpha_ls_bootstrap_se"]
                ),
                "pareto_beta_ls": float(fit["pareto_beta_ls"]),
                "pareto_beta_ls_bootstrap_se": float(
                    boot["pareto_beta_ls_bootstrap_se"]
                ),
                "pareto_ls_r2": ls_r2,
                "pareto_ls_correlation_coefficient": float(ls_corr),
                "pareto_alpha_mle": float(fit["pareto_alpha_mle"]),
                "pareto_alpha_mle_fisher_se": float(
                    fit["pareto_alpha_mle_fisher_se"]
                ),
                "pareto_alpha_mle_likelihood_se": likelihood_se,
                "pareto_alpha_mle_bootstrap_se": float(
                    boot["pareto_alpha_mle_bootstrap_se"]
                ),
                "pareto_beta_mle_continuity": beta_mle,
                "pareto_beta_mle_likelihood_se": beta_likelihood_se,
                "pareto_beta_mle_bootstrap_se": float(
                    boot["pareto_beta_mle_bootstrap_se"]
                ),
                "pareto_mle_r2": mle_r2,
                "pareto_population_pct": float(fit["pareto_population_pct"]),
                "pareto_supported": bool(pareto_supported),
                "gompertz_income_share_pct": gompertz_income_share,
                "pareto_income_share_pct": pareto_income_share,
                "gini": float(stat["Gini"]),
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def run_layer(layer: str):
    cfg, _, _, _, _, _ = _load_layer(layer)
    bootstrap = build_bootstrap_uncertainties(layer)
    reproduction = build_reproduction_annual(layer, bootstrap)

    tables = cfg["tables"]
    tables.mkdir(parents=True, exist_ok=True)
    bootstrap.to_csv(tables / "moura_ribeiro_bootstrap_annual.csv", index=False)
    reproduction.to_csv(
        tables / "moura_ribeiro_reproduction_annual.csv", index=False
    )
    return {
        "bootstrap": bootstrap,
        "reproduction": reproduction,
    }


def main():
    results = {layer: run_layer(layer) for layer in ("trusted", "refined")}
    for layer, result in results.items():
        years = result["reproduction"]["year"]
        print(
            f"Stage 03 Moura-Ribeiro reproduction ({layer}): "
            f"{len(years)} survey years."
        )
    return results


if __name__ == "__main__":
    main()
