"""Run the complete PNAD analysis for refined and trusted annual datasets.

Stage 03 is the canonical analytical layer of the project. It contains the
shared descriptive, histogram, CCDF, Lorenz, inequality, concentration,
validation and plotting routines together with a single Gompertz--Pareto
regime implementation following Moura Jr. and Ribeiro (EPJ B 67, 101--120,
2009).

For the regime analysis, individual income is normalized by the annual mean,
the empirical CCDF is expressed in percent, logarithmic thresholds use ratio
1.10, and the Gompertz transform is ln[ln F(x)]. The Gompertz normalization is
fixed by A = ln[ln(100)]. The empirical boundaries x_G,max and x_P,min are
identified separately, x_t is determined only after both boundaries are known,
and the Pareto tail is then estimated by least squares and direct maximum
likelihood on individual observations.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import os
import re
import unicodedata

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tqdm.auto import tqdm


REPO_ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = REPO_ROOT / "data" / "metadata" / "df_metadata.xlsx"
REFINED_DATA_PATH = REPO_ROOT / "data" / "refined"
TRUSTED_DATA_PATH = REPO_ROOT / "data" / "trusted"
GINI_REFERENCE_PATH = REPO_ROOT / "data" / "auxiliary" / "series_gini_ipea_banco_mundial.csv"

TABLES_ANALYSIS_REFINED_PATH = REPO_ROOT / "assets" / "tables_analysis_refined"
TABLES_ANALYSIS_TRUSTED_PATH = REPO_ROOT / "assets" / "tables_analysis_trusted"
FIGURES_ANALYSIS_REFINED_PATH = REPO_ROOT / "assets" / "figures_analysis_refined"
FIGURES_ANALYSIS_TRUSTED_PATH = REPO_ROOT / "assets" / "figures_analysis_trusted"

BIN_RATIO = 1.10
LORENZ_GRID_SIZE = 1001
PLOT_COLS = 4
GOMPERTZ_A_THEORY = float(np.log(np.log(100.0)))
GOMPERTZ_A_MIN = 1.4
GOMPERTZ_A_MAX = 1.6
MIN_GOMPERTZ_POINTS = 8
MIN_PARETO_POINTS = 5
PARETO_MIN_R2 = 0.98


def geometric_edges(xmin, xmax, ratio=BIN_RATIO):
    if xmin <= 0 or xmax <= 0 or xmax < xmin:
        raise ValueError(f"Invalid interval: xmin={xmin}, xmax={xmax}")
    if np.isclose(xmin, xmax):
        return np.array([xmin, xmin * ratio], dtype=float)
    n = int(np.ceil(np.log(xmax / xmin) / np.log(ratio)))
    edges = xmin * ratio ** np.arange(n + 1, dtype=float)
    if edges[-1] <= xmax:
        edges = np.append(edges, edges[-1] * ratio)
    return edges


def empirical_ccdf(values, thresholds):
    x = np.sort(np.asarray(values, dtype=float))
    t = np.asarray(thresholds, dtype=float)
    idx = np.searchsorted(x, t, side="left")
    return (x.size - idx) / x.size


def lorenz_curve(values):
    x = np.sort(np.asarray(values, dtype=float))
    if x.size == 0 or np.any(x < 0) or x.sum() <= 0:
        raise ValueError("Lorenz curve requires non-negative income and positive total income.")
    p = np.arange(1, x.size + 1, dtype=float) / x.size
    L = np.cumsum(x) / x.sum()
    return np.insert(p, 0, 0.0), np.insert(L, 0, 0.0)


def inequality_geometry(p, L):
    p = np.asarray(p, float)
    L = np.asarray(L, float)
    G = 1.0 - 2.0 * np.trapezoid(L, p)

    d = p - L
    ip = int(np.argmax(d))
    P = float(d[ip])

    f = L + p - 1.0
    crossing = np.where(np.signbit(f[:-1]) != np.signbit(f[1:]))[0]
    if crossing.size:
        i = int(crossing[0])
        x0, x1 = p[i], p[i + 1]
        y0, y1 = f[i], f[i + 1]
        k = float(x0 if np.isclose(y0, y1) else x0 - y0 * (x1 - x0) / (y1 - y0))
    else:
        k = float(p[np.argmin(np.abs(f))])

    pp = 100.0 * p
    LL = 100.0 * L
    kp = 100.0 * k
    corner = ((100.0 - kp) ** 2) / 2.0
    left = pp <= kp
    right = pp >= kp
    B1 = np.trapezoid(LL[left], pp[left]) + corner
    B2 = np.trapezoid(LL[right], pp[right]) - corner
    G1 = (2500.0 - B1) / 2500.0
    G2 = (2500.0 - B2) / 2500.0
    Z = np.nan if np.isclose(G, 0) else kp * (100.0 - kp) * (G2 - G1) / (10000.0 * G)

    return {
        "Gini": float(G),
        "Pietra": P,
        "Pietra_x": float(p[ip]),
        "Pietra_y": float(L[ip]),
        "Kolkata": k,
        "Kolkata_pct": kp,
        "Zanardi": float(Z),
    }


def top_share(p, L, cutoff):
    return float(1.0 - np.interp(cutoff, p, L))


def geometric_mean_positive(values):
    x = np.asarray(values, float)
    x = x[x > 0]
    return np.nan if x.size == 0 else float(np.exp(np.mean(np.log(x))))



def _band_statistics(values, total, prefix):
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


def compute_exclusive_income_statistics(values):
    """Compute positive-income and exclusive top-band summaries in Stage 03."""
    values = np.sort(np.asarray(values, float))
    values = values[np.isfinite(values) & (values > 0)]
    if values.size == 0:
        raise ValueError("Positive-income summary requires at least one observation.")
    total = float(values.sum())
    n = int(values.size)
    i90, i99, i999 = int(0.90 * n), int(0.99 * n), int(0.999 * n)
    out = {
        "income_observation_n": n,
        "income_mean_2025_usd": float(values.mean()),
        "income_median_2025_usd": float(np.median(values)),
        "income_std_2025_usd": float(np.std(values, ddof=1)) if n > 1 else np.nan,
    }
    out.update(_band_statistics(values[i90:i99], total, "p90_p99"))
    out.update(_band_statistics(values[i99:i999], total, "p99_p999"))
    out.update(_band_statistics(values[i999:], total, "p999_p100"))
    return out


def make_grid(n, cols=4, figsize=None, width_per_col=4.2, height_per_row=3.4,
              sharex=False, sharey=False):
    rows = int(np.ceil(n / cols))
    if figsize is None:
        figsize = (width_per_col * cols, height_per_row * rows)
    return plt.subplots(rows, cols, figsize=figsize, squeeze=False, sharex=sharex, sharey=sharey)


def finish_grid(fig, axes, n_used, suptitle, path, dpi=250, top=0.985):
    rows, cols = axes.shape
    for j in range(n_used, rows * cols):
        row, col = divmod(j, cols)
        fig.delaxes(axes[row, col])
    fig.suptitle(suptitle, fontsize=18, y=0.998)
    fig.tight_layout(rect=[0, 0, 1, top])
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

def norm_col(name):
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower().strip()).strip("_")


def pick(cols, candidates):
    return next((c for c in candidates if c in cols), None)


def gini_scale(s):
    x = pd.to_numeric(s, errors="coerce")
    finite = x[np.isfinite(x)]
    return x / 100.0 if (not finite.empty and finite.max() > 1.5) else x


def load_gini_reference(path):
    t = pd.read_csv(path, sep=None, engine="python").copy()
    t.columns = [norm_col(c) for c in t.columns]
    cols = set(t.columns)
    year_col = pick(cols, ["year", "ano"])
    if year_col is None:
        raise ValueError(f"Year column not identified. Columns: {sorted(cols)}")

    ipea = pick(cols, ["ipea", "gini_ipea", "serie_ipea", "ipeadata"])
    wb = pick(cols, ["banco_mundial", "gini_banco_mundial", "serie_banco_mundial",
                     "world_bank", "worldbank", "wb"])
    if ipea is not None or wb is not None:
        out = pd.DataFrame({"year": pd.to_numeric(t[year_col], errors="coerce")})
        if ipea is not None:
            out["IPEA"] = gini_scale(t[ipea])
        if wb is not None:
            out["Banco_Mundial"] = gini_scale(t[wb])
        out = out.dropna(subset=["year"])
        out["year"] = out["year"].astype(int)
        return out

    source_col = pick(cols, ["source", "fonte", "serie"])
    value_col = pick(cols, ["value", "valor", "gini"])
    if source_col is not None and value_col is not None:
        q = t[[year_col, source_col, value_col]].copy()
        q[year_col] = pd.to_numeric(q[year_col], errors="coerce")
        q[value_col] = gini_scale(q[value_col])
        q[source_col] = q[source_col].astype(str).str.lower()
        q["source_norm"] = np.where(
            q[source_col].str.contains("ipea", na=False), "IPEA",
            np.where(q[source_col].str.contains("banco|world|bank", regex=True, na=False),
                     "Banco_Mundial", np.nan),
        )
        q = q.dropna(subset=[year_col, "source_norm"])
        out = q.pivot_table(index=year_col, columns="source_norm", values=value_col,
                            aggfunc="first").reset_index().rename(columns={year_col: "year"})
        out["year"] = out["year"].astype(int)
        out.columns.name = None
        return out
    raise ValueError(f"External Gini CSV format not recognized. Columns: {sorted(cols)}")


def year_from_filename(path):
    match = re.search(r"(\d{4})$", path.stem)
    if not match:
        raise ValueError(f"Year not identified in {path.name}")
    return int(match.group(1))


def load_inputs(metadata_path=METADATA_PATH, data_path=TRUSTED_DATA_PATH,
                file_pattern="pnad_trusted_*.parquet", layer="trusted"):
    df_metadata = pd.read_excel(metadata_path)
    required = {"ano", "Exchange", "Inflation"}
    missing = required - set(df_metadata.columns)
    if missing:
        raise ValueError("Missing metadata columns: " + ", ".join(sorted(missing)))
    df_metadata = df_metadata.copy()
    df_metadata["ano"] = df_metadata["ano"].astype(int)

    files_by_year = {year_from_filename(path): path for path in data_path.glob(file_pattern)}
    years = sorted(files_by_year)
    if not years:
        raise RuntimeError(f"No {layer} Parquet files matching '{file_pattern}' found in {data_path}")
    metadata_years = set(df_metadata["ano"])
    missing_years = [year for year in years if year not in metadata_years]
    if missing_years:
        raise ValueError(f"Years without metadata: {missing_years}")
    return df_metadata, files_by_year, years


def analyze_year(year, parquet_path, metadata_row, bin_ratio=BIN_RATIO,
                 lorenz_grid_size=LORENZ_GRID_SIZE):
    df = pd.read_parquet(parquet_path)
    if "renda" not in df.columns:
        raise ValueError(f"{year}: missing renda column")
    nominal = pd.to_numeric(df["renda"], errors="coerce").to_numpy(float)
    n_total = nominal.size
    n_nan = int(np.isnan(nominal).sum())
    valid = nominal[np.isfinite(nominal)]
    n_zero = int(np.sum(valid == 0))
    n_negative = int(np.sum(valid < 0))
    if valid.size == 0:
        raise ValueError(f"{year}: no valid income")
    if n_negative > 0:
        raise ValueError(f"{year}: {n_negative} negative incomes")
    positive = valid[valid > 0]
    if positive.size == 0:
        raise ValueError(f"{year}: no positive income")

    exchange = float(metadata_row["Exchange"])
    inflation = float(metadata_row["Inflation"])
    if not np.isfinite(exchange) or exchange <= 0:
        raise ValueError(f"{year}: invalid Exchange")
    if not np.isfinite(inflation) or inflation <= 0:
        raise ValueError(f"{year}: invalid Inflation")

    adjusted = valid / exchange * inflation
    positive_adjusted = adjusted[adjusted > 0]
    xmin = float(positive_adjusted.min())
    xmax = float(positive_adjusted.max())
    edges = geometric_edges(xmin, xmax, bin_ratio)
    thresholds = edges[:-1]
    ccdf = empirical_ccdf(adjusted, thresholds)
    ccdf_pct = 100.0 * ccdf
    lnln = np.full_like(ccdf_pct, np.nan, float)
    mask = ccdf_pct > 1.0
    lnln[mask] = np.log(np.log(ccdf_pct[mask]))

    ccdf_records = [{"year": year, "x": float(x), "ccdf": float(c),
                     "ccdf_pct": float(cp),
                     "ln_ln_ccdf_pct": float(ll) if np.isfinite(ll) else np.nan}
                    for x, c, cp, ll in zip(thresholds, ccdf, ccdf_pct, lnln)]

    bins_records = []
    for i in range(len(edges) - 1):
        left, right = edges[i], edges[i + 1]
        mask_bin = (positive_adjusted >= left) & (
            (positive_adjusted <= right) if i == len(edges) - 2 else (positive_adjusted < right)
        )
        values_bin = positive_adjusted[mask_bin]
        if values_bin.size == 0:
            continue
        bins_records.append({
            "year": year,
            "bin_left": float(left),
            "bin_right": float(right),
            "bin_center_geo": float(np.sqrt(left * right)),
            "N_bin": int(values_bin.size),
            "mean": float(np.mean(values_bin)),
            "geometric_mean": geometric_mean_positive(values_bin),
            "median": float(np.median(values_bin)),
            "std": float(np.std(values_bin, ddof=1)) if values_bin.size > 1 else np.nan,
            "ccdf": float(empirical_ccdf(adjusted, np.array([left]))[0]),
        })

    population, income_share = lorenz_curve(adjusted)
    indices = inequality_geometry(population, income_share)
    lorenz_grid = np.linspace(0.0, 1.0, lorenz_grid_size)
    sampled_income = np.interp(lorenz_grid, population, income_share)
    lorenz_records = [{"year": year, "population_share": float(p), "income_share": float(L)}
                      for p, L in zip(lorenz_grid, sampled_income)]

    stats_record = {
        "year": year,
        "N": int(n_total),
        "N_valid": int(valid.size),
        "n_nan": n_nan,
        "n_zero": n_zero,
        "n_negative": n_negative,
        "xmin_positive_nominal": float(positive.min()),
        "xmax_nominal": float(valid.max()),
        "mean_nominal": float(np.mean(valid)),
        "median_nominal": float(np.median(valid)),
        "std_nominal": float(np.std(valid, ddof=1)) if valid.size > 1 else np.nan,
        "income_sum_nominal": float(np.sum(valid)),
        "xmin_positive": xmin,
        "xmax": xmax,
        "mean": float(np.mean(adjusted)),
        "median": float(np.median(adjusted)),
        "std": float(np.std(adjusted, ddof=1)) if adjusted.size > 1 else np.nan,
        "income_sum": float(np.sum(adjusted)),
        "Gini": indices["Gini"],
        "Pietra": indices["Pietra"],
        "Kolkata": indices["Kolkata"],
        "Kolkata_pct": indices["Kolkata_pct"],
        "Zanardi": indices["Zanardi"],
        "top_10": top_share(population, income_share, 0.90),
        "top_1": top_share(population, income_share, 0.99),
        "top_01": top_share(population, income_share, 0.999),
    }
    stats_record.update(compute_exclusive_income_statistics(positive_adjusted))
    return stats_record, ccdf_records, bins_records, lorenz_records


def pipeline(metadata_path=METADATA_PATH, data_path=TRUSTED_DATA_PATH,
             file_pattern="pnad_trusted_*.parquet", layer="trusted",
             bin_ratio=BIN_RATIO, lorenz_grid_size=LORENZ_GRID_SIZE):
    df_metadata, files_by_year, years = load_inputs(metadata_path, data_path, file_pattern, layer)
    metadata_index = df_metadata.set_index("ano")
    stats_records, ccdf_records, bins_records, lorenz_records = [], [], [], []
    for year in tqdm(years, desc=f"Analyzing PNAD {layer}", unit="year"):
        stats, ccdf, bins, lorenz = analyze_year(
            year, files_by_year[year], metadata_index.loc[year], bin_ratio, lorenz_grid_size
        )
        stats_records.append(stats)
        ccdf_records.extend(ccdf)
        bins_records.extend(bins)
        lorenz_records.extend(lorenz)
    return {
        "df_metadata": df_metadata,
        "files_by_year": files_by_year,
        "years": years,
        "df_stats_year": pd.DataFrame(stats_records).sort_values("year").reset_index(drop=True),
        "df_ccdf": pd.DataFrame(ccdf_records).sort_values(["year", "x"]).reset_index(drop=True),
        "df_bins": pd.DataFrame(bins_records).sort_values(["year", "bin_left"]).reset_index(drop=True),
        "df_lorenz": pd.DataFrame(lorenz_records).sort_values(["year", "population_share"]).reset_index(drop=True),
    }


def build_histogram_dataset(files_by_year, years=None, bins=100):
    years = sorted(files_by_year) if years is None else years
    records = []
    for year in tqdm(years, desc="Histogram bins", unit="year"):
        df = pd.read_parquet(files_by_year[year])
        income = pd.to_numeric(df["renda"], errors="coerce").to_numpy(float)
        income = income[np.isfinite(income) & (income >= 0)]
        counts, edges = np.histogram(income, bins=bins)
        centers = 0.5 * (edges[:-1] + edges[1:])
        records.extend({"year": int(year), "bin_left": float(left), "bin_right": float(right),
                        "bin_center": float(center), "count": int(count)}
                       for left, right, center, count in zip(edges[:-1], edges[1:], centers, counts))
    return pd.DataFrame(records).sort_values(["year", "bin_left"]).reset_index(drop=True)


def bins_table(df_bins, n=20):
    return df_bins.head(n).copy()


def build_gini_validation(df_stats_year, reference_path=GINI_REFERENCE_PATH):
    df_reference = load_gini_reference(reference_path)
    result = df_stats_year[["year", "Gini"]].merge(df_reference, on="year", how="left")
    if "IPEA" in result:
        result["diff_IPEA"] = result["Gini"] - result["IPEA"]
    if "Banco_Mundial" in result:
        result["diff_Banco_Mundial"] = result["Gini"] - result["Banco_Mundial"]
    return result


def plot_histograms(df, years, output_path, ncols=4, figsize=None):
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize, width_per_col=4.4,
                          height_per_row=3.5, sharey=True)
    for i, year in enumerate(years):
        d = df[df["year"] == year]
        ax = axes.ravel()[i]
        ax.bar(d["bin_left"], d["count"], width=d["bin_right"] - d["bin_left"],
               align="edge", edgecolor="black", linewidth=0.35)
        ax.set_yscale("log")
        ax.set_title(f"PNAD histogram - {year}", fontsize=10)
        ax.set_xlabel("Income")
        ax.set_ylabel("Frequency (log)")
        ax.grid(axis="y", alpha=0.25, linestyle="--")
    finish_grid(fig, axes, len(years), "Annual histograms - PNAD", output_path)


def plot_income_mean_median(df, output_path, figsize=(14, 13)):
    fig, axes = plt.subplots(3, 2, figsize=figsize, squeeze=False, sharex=True)
    full_years = np.arange(int(df["year"].min()), int(df["year"].max()) + 1)
    indexed = df.set_index("year").reindex(full_years)
    indexed["dispersion"] = indexed["std"] / indexed["mean"]
    series = [
        ("mean", "Mean income", "Adjusted income (2025 US$)"),
        ("median", "Median income", "Adjusted income (2025 US$)"),
        ("std", "Standard deviation", "Adjusted income (2025 US$)"),
        ("dispersion", r"Relative dispersion $\sigma/\mu$", r"$\sigma/\mu$"),
        ("xmax", "Maximum income", "Adjusted income (2025 US$)"),
        ("xmin", "Minimum income", "Adjusted income (2025 US$)"),
    ]
    for ax, (column, title, ylabel) in zip(axes.ravel(), series):
        y = indexed[column].interpolate(method="linear", limit_direction="both")
        ax.plot(full_years, y, marker="o", markersize=3, linewidth=1.4)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
    axes[2, 0].set_xlabel("Year")
    axes[2, 1].set_xlabel("Year")
    axes[2, 1].axhline(0.0, linestyle="--", linewidth=0.9)
    fig.suptitle("Annual income statistics - PNAD", fontsize=18, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)

def plot_ccdf_loglog(df, years, output_path, ncols=4, figsize=None):
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize, sharey=True)
    for i, year in enumerate(years):
        d = df[(df["year"] == year) & (df["x"] > 0) & (df["ccdf"] > 0)]
        ax = axes.ravel()[i]
        ax.plot(d["x"], d["ccdf"], linewidth=1.5)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(str(year))
        ax.grid(True, which="both", alpha=0.25)
    finish_grid(fig, axes, len(years), "Empirical CCDF by year - PNAD", output_path)




def plot_lorenz_indices_pretty(df_lorenz, df_stats, years, output_path, ncols=3, figsize=None):
    stats = df_stats.set_index("year")
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize, width_per_col=4.3,
                          height_per_row=4.1, sharex=True, sharey=True)
    for i, year in enumerate(years):
        d = df_lorenz[df_lorenz["year"] == year]
        row = stats.loc[year]
        p = 100.0 * d["population_share"].to_numpy()
        L = 100.0 * d["income_share"].to_numpy()
        ax = axes.ravel()[i]
        ax.fill_between(p, 0, L, alpha=0.15, label="area B")
        ax.plot(p, L, linewidth=1.8)
        ax.plot([0, 100], [0, 100], linewidth=1.2, label="equality line")
        k = 100.0 * float(row["Kolkata"])
        q = 100.0 - k
        ax.scatter([k], [q], s=34, zorder=6)
        ax.plot([k, k], [0, q], linestyle=":", linewidth=1.2)
        ax.plot([0, k], [q, q], linestyle=":", linewidth=1.2)
        diff = p - L
        ip = int(np.argmax(diff))
        px, py = p[ip], L[ip]
        ax.plot([px, px], [py, px], linestyle="--", linewidth=1.5)
        ax.scatter([px], [py], s=22, zorder=6)
        ax.plot([], [], color="none", label=f"k: {k:.3f}")
        ax.plot([], [], color="none", label=f"G: {row['Gini']:.3f}")
        ax.plot([], [], color="none", label=f"Z: {row['Zanardi']:.3f}")
        ax.plot([], [], color="none", label=f"p: {100.0 * row['Pietra']:.3f}")
        ax.set_title(str(year))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("households (%)")
        ax.set_ylabel("income (%)")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper left", fontsize=8, framealpha=0.85)
    finish_grid(fig, axes, len(years), "Lorenz curves and inequality geometry - 100 x 100 (%)", output_path)


def plot_top_shares(df, output_path, figsize=(14, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    for col, label, marker in [("top_10", "Top 10%", "o"), ("top_1", "Top 1%", "s"), ("top_01", "Top 0.1%", "^")]:
        ax.plot(df["year"], 100 * df[col], marker=marker, label=label)
    ax.set_title("Income concentration - cumulative top shares")
    ax.set_xlabel("Year")
    ax.set_ylabel("Share of total income (%)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)


def plot_top_shares_exclusive(df, output_path, figsize=(14, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    brackets = [
        (100 * (df["top_10"] - df["top_1"]), "90-99%", "o"),
        (100 * (df["top_1"] - df["top_01"]), "99-99.9%", "s"),
        (100 * df["top_01"], "99.9-100%", "^"),
    ]
    for values, label, marker in brackets:
        ax.plot(df["year"], values, marker=marker, label=label)
    ax.set_title("Income concentration - exclusive top-income brackets")
    ax.set_xlabel("Year")
    ax.set_ylabel("Share of total income (%)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)

def plot_top_shares_mean_median(df, output_path, figsize=(14, 10)):
    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)
    axes[0].plot(df["year"], df["mean"], marker="o", label="Mean")
    axes[0].plot(df["year"], df["median"], marker="s", label="Median")
    axes[0].set_title("Mean and median adjusted income")
    axes[0].set_ylabel("Adjusted income (2025 US$)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    for col, label, marker in [("top_10", "Top 10%", "o"), ("top_1", "Top 1%", "s"), ("top_01", "Top 0.1%", "^")]:
        axes[1].plot(df["year"], 100 * df[col], marker=marker, label=label)
    axes[1].set_title("Income concentration")
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("% of total income")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)


def plot_inequality_indices(df, output_path, figsize=(14, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    for col, marker in [("Gini", "o"), ("Pietra", "s"), ("Kolkata", "^"), ("Zanardi", "d")]:
        ax.plot(df["year"], df[col], marker=marker, label=col)
    ax.set_title("Evolution of inequality indices")
    ax.set_xlabel("Year")
    ax.set_ylabel("Index")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)


def plot_inequality_indices_grid(df, output_path, ncols=2, figsize=(16, 10)):
    series = [
        ("Gini", "Gini Index", 1.0, "Index value"),
        ("Zanardi", "Zanardi Index", 1.0, "Index value"),
        ("Kolkata", "Kolkata Index", 100.0, "Index value (%)"),
        ("Pietra", "Pietra Index", 100.0, "Index value (%)"),
    ]
    fig, axes = plt.subplots(2, ncols, figsize=figsize, squeeze=False, sharex=True)
    first = int(df["year"].min())
    last = int(df["year"].max())
    years = np.arange(first, last + 1)
    indexed = df.set_index("year").reindex(years)
    for ax, (col, title, scale, ylabel) in zip(axes.ravel(), series):
        # Missing survey years remain NaN so the plotted line is interrupted.
        y = indexed[col]
        ax.plot(years, scale * y, marker="o", markersize=4, linewidth=1.7)
        ax.set_title(f"Evolution of the {title} - Brazil ({first}-{last})")
        ax.set_xlabel("Year")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.4)
    fig.tight_layout()
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)

def plot_gini_validation(df, output_path, figsize=(14, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(df["year"], df["Gini"], marker="o", label="PNAD - calculated")
    if "IPEA" in df:
        d = df.dropna(subset=["IPEA"])
        ax.plot(d["year"], d["IPEA"], marker="s", label="IPEA")
    if "Banco_Mundial" in df:
        d = df.dropna(subset=["Banco_Mundial"])
        ax.plot(d["year"], d["Banco_Mundial"], marker="^", label="World Bank")
    ax.set_title("External validation of the Gini coefficient")
    ax.set_xlabel("Year")
    ax.set_ylabel("Gini coefficient")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)


def _fit_r2(observed, fitted):
    observed = np.asarray(observed, dtype=float)
    fitted = np.asarray(fitted, dtype=float)
    residual = observed - fitted
    sse = float(np.sum(residual ** 2))
    tss = float(np.sum((observed - observed.mean()) ** 2))
    return (np.nan if tss <= 0.0 else float(1.0 - sse / tss)), sse


def linear_fit(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size < 2 or np.unique(x).size < 2:
        raise ValueError("Linear fit requires at least two distinct finite abscissae.")
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    r2, sse = _fit_r2(y, fitted)
    return {"intercept": float(intercept), "slope": float(slope), "fit_r2": float(r2), "fit_sse": float(sse)}


def fit_gompertz_ls(income_normalized, gompertz_transform, A=GOMPERTZ_A_THEORY):
    x = np.asarray(income_normalized, dtype=float)
    y = np.asarray(gompertz_transform, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    denominator = float(np.sum(x ** 2))
    if x.size < 2 or denominator <= 0:
        return np.nan
    B = float(np.sum(x * (A - y)) / denominator)
    return B if np.isfinite(B) and B > 0 else np.nan


def load_normalized_individual_income(parquet_path: Path, metadata_row: pd.Series):
    frame = pd.read_parquet(parquet_path)
    if "renda" not in frame.columns:
        raise ValueError(f"{parquet_path.name}: missing renda column")
    nominal = pd.to_numeric(frame["renda"], errors="coerce").to_numpy(float)
    nominal = nominal[np.isfinite(nominal) & (nominal > 0)]
    if nominal.size == 0:
        raise ValueError(f"{parquet_path.name}: no positive finite income")
    exchange = float(metadata_row["Exchange"])
    inflation = float(metadata_row["Inflation"])
    if not np.isfinite(exchange) or exchange <= 0 or not np.isfinite(inflation) or inflation <= 0:
        raise ValueError(f"{parquet_path.name}: invalid monetary metadata")
    adjusted = nominal / exchange * inflation
    mean = float(np.mean(adjusted))
    if not np.isfinite(mean) or mean <= 0:
        raise ValueError(f"{parquet_path.name}: invalid annual mean income")
    return adjusted / mean, mean


def build_regime_ccdf(income_normalized):
    X = np.sort(np.asarray(income_normalized, dtype=float))
    X = X[np.isfinite(X) & (X > 0)]
    if X.size < 2:
        raise ValueError("Regime fitting requires at least two positive observations.")
    edges = geometric_edges(float(X[0]), float(X[-1]), ratio=BIN_RATIO)
    thresholds, right_edges = edges[:-1], edges[1:]
    left = np.searchsorted(X, thresholds, side="left")
    right = np.searchsorted(X, right_edges, side="left")
    counts = right - left
    probability = (X.size - left) / X.size
    percent = 100.0 * probability
    transform = np.full(percent.shape, np.nan, dtype=float)
    valid = percent > 1.0
    transform[valid] = np.log(np.log(percent[valid]))
    return pd.DataFrame({
        "income_normalized": thresholds,
        "bin_right_normalized": right_edges,
        "observations_in_bin": counts,
        "empirical_ccdf_probability": probability,
        "empirical_ccdf_percent": percent,
        "gompertz_transform": transform,
    })


def select_gompertz_region(regime_ccdf):
    valid = regime_ccdf.loc[
        np.isfinite(regime_ccdf["gompertz_transform"])
        & (regime_ccdf["empirical_ccdf_percent"] > 1.0)
        & (regime_ccdf["observations_in_bin"] > 0)
    ].reset_index(drop=True)
    if len(valid) < MIN_GOMPERTZ_POINTS:
        raise ValueError("Insufficient Gompertz-region points.")

    candidates = []
    for end in range(MIN_GOMPERTZ_POINTS, len(valid) + 1):
        block = valid.iloc[:end]
        free = linear_fit(block["income_normalized"], block["gompertz_transform"])
        A_free = float(free["intercept"])
        B_free = float(-free["slope"])
        candidates.append({
            "end": end,
            "x": float(block["income_normalized"].iloc[-1]),
            "A_free": A_free,
            "B_free": B_free,
            "r2_free": float(free["fit_r2"]),
            "ok": GOMPERTZ_A_MIN <= A_free <= GOMPERTZ_A_MAX and B_free > 0,
        })

    frame = pd.DataFrame(candidates)
    admissible = frame[frame["ok"]]
    if not admissible.empty:
        chosen = admissible.iloc[-1]
        status = "largest_range_with_free_A_in_1.4_to_1.6"
    else:
        frame["distance"] = (frame["A_free"] - GOMPERTZ_A_THEORY).abs()
        chosen = frame.sort_values(["distance", "x"]).iloc[0]
        status = "fallback_closest_free_A_to_ln_ln_100"

    block = valid.iloc[:int(chosen["end"])]
    x = block["income_normalized"].to_numpy(float)
    y = block["gompertz_transform"].to_numpy(float)
    B = fit_gompertz_ls(x, y)
    if not np.isfinite(B):
        raise ValueError("Fixed-A Gompertz least-squares fit returned invalid B.")
    r2, sse = _fit_r2(y, GOMPERTZ_A_THEORY - B * x)
    return {
        "gompertz_A": GOMPERTZ_A_THEORY,
        "gompertz_B": float(B),
        "gompertz_r2": float(r2),
        "gompertz_sse": float(sse),
        "gompertz_x_gmax": float(chosen["x"]),
        "gompertz_point_n": int(chosen["end"]),
        "gompertz_selection_status": status,
        "gompertz_boundary_A_free": float(chosen["A_free"]),
        "gompertz_boundary_B_free": float(chosen["B_free"]),
        "gompertz_boundary_r2_free": float(chosen["r2_free"]),
    }


def select_pareto_region(regime_ccdf, gompertz_x_gmax):
    valid = regime_ccdf.loc[
        (regime_ccdf["income_normalized"] >= gompertz_x_gmax)
        & (regime_ccdf["empirical_ccdf_percent"] > 0)
        & (regime_ccdf["observations_in_bin"] > 0)
    ].reset_index(drop=True)
    if len(valid) < MIN_PARETO_POINTS:
        raise ValueError("Insufficient Pareto-tail points.")

    candidates = []
    for start in range(0, len(valid) - MIN_PARETO_POINTS + 1):
        tail = valid.iloc[start:]
        fit = linear_fit(np.log(tail["income_normalized"]), np.log(tail["empirical_ccdf_percent"]))
        alpha = float(-fit["slope"])
        candidates.append({
            "x": float(tail["income_normalized"].iloc[0]),
            "alpha": alpha,
            "r2": float(fit["fit_r2"]),
            "ok": np.isfinite(alpha) and alpha > 0 and fit["fit_r2"] >= PARETO_MIN_R2,
        })

    frame = pd.DataFrame(candidates)
    admissible = frame[frame["ok"]]
    if not admissible.empty:
        chosen = admissible.iloc[0]
        status = "earliest_tail_start_with_r2_ge_0.98"
    else:
        chosen = frame.sort_values(["r2", "x"], ascending=[False, True]).iloc[0]
        status = "fallback_highest_tail_r2"
    return {
        "pareto_x_pmin": float(chosen["x"]),
        "pareto_selection_alpha": float(chosen["alpha"]),
        "pareto_selection_r2": float(chosen["r2"]),
        "pareto_selection_status": status,
    }

def determine_threshold(gompertz_x_gmax, pareto_x_pmin):
    if pareto_x_pmin < gompertz_x_gmax:
        raise ValueError("Pareto lower boundary cannot precede Gompertz upper boundary.")
    if np.isclose(gompertz_x_gmax, pareto_x_pmin, rtol=1e-12, atol=0.0):
        return float(gompertz_x_gmax), 0.0, "coincident_regime_bounds"
    return (
        0.5 * (gompertz_x_gmax + pareto_x_pmin),
        0.5 * (pareto_x_pmin - gompertz_x_gmax),
        "midpoint_between_regime_bounds",
    )


def fit_pareto_ls(regime_ccdf, pareto_x_pmin):
    tail = regime_ccdf.loc[
        (regime_ccdf["income_normalized"] >= pareto_x_pmin)
        & (regime_ccdf["empirical_ccdf_percent"] > 0)
        & (regime_ccdf["observations_in_bin"] > 0)
    ]
    if len(tail) < MIN_PARETO_POINTS:
        raise ValueError("Insufficient Pareto points for least squares.")
    fit = linear_fit(np.log(tail["income_normalized"]), np.log(tail["empirical_ccdf_percent"]))
    alpha = float(-fit["slope"])
    beta = float(np.exp(fit["intercept"]))
    if not np.isfinite(alpha) or alpha <= 0 or not np.isfinite(beta) or beta <= 0:
        raise ValueError("Pareto LS returned invalid parameters.")
    return alpha, beta, float(fit["fit_r2"]), float(fit["fit_sse"])


def direct_pareto_mle(income_normalized, x_t):
    X = np.asarray(income_normalized, dtype=float)
    tail = X[np.isfinite(X) & (X >= x_t)]
    n = int(tail.size)
    if n < 2:
        raise ValueError("Pareto MLE requires at least two tail observations.")
    log_sum = float(np.log(tail / x_t).sum())
    if log_sum <= 0:
        raise ValueError("Pareto MLE logarithmic sum must be positive.")
    alpha = float(n / log_sum)
    return alpha, float(alpha / np.sqrt(n)), n


def continuity_beta(alpha, x_t, gompertz_A, gompertz_B):
    F_t = float(np.exp(np.exp(gompertz_A - gompertz_B * x_t)))
    return float(F_t * x_t ** alpha), F_t


def fit_year_regime(year, income_normalized, normalization_mean):
    """Fit the annual Gompertz--Pareto regime without relaxing support criteria.

    If fewer than ``MIN_PARETO_POINTS`` valid binned tail points remain after the
    Gompertz boundary, the Pareto regime is recorded as unsupported. No reduced
    minimum-point fallback is used. This policy is part of Stage 03 itself so
    local execution and CI execute the same scientific algorithm.
    """
    curve = build_regime_ccdf(income_normalized)
    gompertz = select_gompertz_region(curve)

    try:
        pareto = select_pareto_region(curve, gompertz["gompertz_x_gmax"])
    except ValueError as exc:
        if "Insufficient Pareto-tail points" not in str(exc):
            raise

        n_total = int(len(income_normalized))
        fit = {
            "year": int(year),
            "log_bin_ratio": BIN_RATIO,
            "normalization_mean_income_adj_2025_usd": float(normalization_mean),
            "positive_income_observation_n": n_total,
            **gompertz,
            "pareto_x_pmin": np.nan,
            "pareto_selection_alpha": np.nan,
            "pareto_selection_r2": np.nan,
            "pareto_selection_status": "unsupported_insufficient_tail_points",
            "transition_x_t": np.nan,
            "transition_delta_x_t": np.nan,
            "transition_rule": "unsupported_no_pareto_transition",
            "gompertz_population_n": np.nan,
            "pareto_population_n": np.nan,
            "gompertz_population_pct": np.nan,
            "pareto_population_pct": np.nan,
            "pareto_alpha_ls": np.nan,
            "pareto_beta_ls": np.nan,
            "pareto_ls_r2": np.nan,
            "pareto_ls_sse": np.nan,
            "pareto_alpha_mle": np.nan,
            "pareto_alpha_mle_fisher_se": np.nan,
            "pareto_beta_mle_continuity": np.nan,
            "gompertz_ccdf_at_x_t_percent": np.nan,
            "cutoff_normalized": np.nan,
            "cutoff_income_adj": np.nan,
            "pareto_alpha": np.nan,
            "pareto_r2": np.nan,
        }

        curve.insert(0, "year", int(year))
        x = curve["income_normalized"].to_numpy(float)
        curve["regime"] = "gompertz_body"
        curve["gompertz_x_gmax"] = gompertz["gompertz_x_gmax"]
        curve["pareto_x_pmin"] = np.nan
        curve["cutoff_normalized"] = np.nan
        curve["cutoff_income_adj"] = np.nan
        curve["income_adj_2025_usd"] = x * normalization_mean
        curve["gompertz_fitted_transform"] = np.where(
            x <= gompertz["gompertz_x_gmax"],
            gompertz["gompertz_A"] - gompertz["gompertz_B"] * x,
            np.nan,
        )
        curve["pareto_fitted_ccdf_percent_ls"] = np.nan
        curve["pareto_fitted_ccdf_percent_mle"] = np.nan
        curve["pareto_fitted_ccdf_percent"] = np.nan
        return fit, curve

    x_t, dx_t, threshold_rule = determine_threshold(
        gompertz["gompertz_x_gmax"], pareto["pareto_x_pmin"]
    )

    alpha_ls, beta_ls, r2_ls, sse_ls = fit_pareto_ls(curve, pareto["pareto_x_pmin"])
    alpha_mle, alpha_mle_se, n_pareto = direct_pareto_mle(income_normalized, x_t)
    beta_mle, F_t = continuity_beta(
        alpha_mle, x_t, gompertz["gompertz_A"], gompertz["gompertz_B"]
    )

    n_total = int(len(income_normalized))
    n_gompertz = n_total - n_pareto
    pct_pareto = 100.0 * n_pareto / n_total
    pct_gompertz = 100.0 - pct_pareto
    fit = {
        "year": int(year),
        "log_bin_ratio": BIN_RATIO,
        "normalization_mean_income_adj_2025_usd": float(normalization_mean),
        "positive_income_observation_n": n_total,
        **gompertz,
        **pareto,
        "transition_x_t": float(x_t),
        "transition_delta_x_t": float(dx_t),
        "transition_rule": threshold_rule,
        "gompertz_population_n": n_gompertz,
        "pareto_population_n": n_pareto,
        "gompertz_population_pct": pct_gompertz,
        "pareto_population_pct": pct_pareto,
        "pareto_alpha_ls": alpha_ls,
        "pareto_beta_ls": beta_ls,
        "pareto_ls_r2": r2_ls,
        "pareto_ls_sse": sse_ls,
        "pareto_alpha_mle": alpha_mle,
        "pareto_alpha_mle_fisher_se": alpha_mle_se,
        "pareto_beta_mle_continuity": beta_mle,
        "gompertz_ccdf_at_x_t_percent": F_t,
        "cutoff_normalized": float(x_t),
        "cutoff_income_adj": float(x_t * normalization_mean),
        "pareto_alpha": alpha_mle,
        "pareto_r2": r2_ls,
    }

    curve.insert(0, "year", int(year))
    x = curve["income_normalized"].to_numpy(float)
    curve["regime"] = np.where(x < x_t, "gompertz_body", "pareto_tail")
    curve["gompertz_x_gmax"] = gompertz["gompertz_x_gmax"]
    curve["pareto_x_pmin"] = pareto["pareto_x_pmin"]
    curve["cutoff_normalized"] = x_t
    curve["cutoff_income_adj"] = x_t * normalization_mean
    curve["income_adj_2025_usd"] = x * normalization_mean
    curve["gompertz_fitted_transform"] = np.where(
        x <= gompertz["gompertz_x_gmax"],
        gompertz["gompertz_A"] - gompertz["gompertz_B"] * x,
        np.nan,
    )
    curve["pareto_fitted_ccdf_percent_ls"] = np.where(
        x >= pareto["pareto_x_pmin"], beta_ls * x ** (-alpha_ls), np.nan
    )
    curve["pareto_fitted_ccdf_percent_mle"] = np.where(
        x >= x_t, beta_mle * x ** (-alpha_mle), np.nan
    )
    curve["pareto_fitted_ccdf_percent"] = curve["pareto_fitted_ccdf_percent_mle"]
    return fit, curve

def build_regime_datasets(files_by_year, df_metadata):
    fits, curves = [], []
    metadata = df_metadata.set_index("ano")
    for year in sorted(files_by_year):
        x, mean = load_normalized_individual_income(files_by_year[year], metadata.loc[year])
        fit, curve = fit_year_regime(year, x, mean)
        fits.append(fit)
        curves.append(curve)
    fit_table = pd.DataFrame(fits).sort_values("year").reset_index(drop=True)
    supported = fit_table[["gompertz_population_pct", "pareto_population_pct"]].notna().all(axis=1)
    if supported.any() and not np.allclose(
        fit_table.loc[supported, "gompertz_population_pct"]
        + fit_table.loc[supported, "pareto_population_pct"],
        100.0,
        rtol=0.0,
        atol=1e-10,
    ):
        raise AssertionError("Supported Gompertz and Pareto population percentages must sum to 100%.")
    return (
        fit_table,
        pd.concat(curves, ignore_index=True)
        .sort_values(["year", "income_normalized"])
        .reset_index(drop=True),
    )

def plot_gompertz_regime_fits(curves, fits, years, output_path, ncols=4, figsize=None):
    fit_i = fits.set_index("year")
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize)
    for i, year in enumerate(years):
        f = fit_i.loc[year]
        xg = float(f["gompertz_x_gmax"])
        d = curves[
            (curves["year"] == year)
            & (curves["income_normalized"] <= xg)
            & curves["gompertz_transform"].notna()
        ]
        ax = axes.ravel()[i]
        ax.scatter(
            d["income_normalized"], d["gompertz_transform"],
            s=12, alpha=0.7, color="0.35", label="Empirical transform"
        )
        ax.plot(
            d["income_normalized"], d["gompertz_fitted_transform"],
            linewidth=1.8, color="tab:blue", label="Fixed-A Gompertz fit"
        )
        a_free = float(f["gompertz_boundary_A_free"])
        b_free = float(f["gompertz_boundary_B_free"])
        if np.isfinite(a_free) and np.isfinite(b_free):
            ax.plot(
                d["income_normalized"],
                a_free - b_free * d["income_normalized"],
                linewidth=1.4, linestyle="--", color="tab:orange",
                label="Free-intercept LSF diagnostic",
            )
        ax.axvline(
            xg, linestyle=":", linewidth=1.0, color="black",
            label=r"$x_{G,\max}$",
        )
        ax.set_title(
            fr"{year} - $A={f['gompertz_A']:.3f}$, $B={f['gompertz_B']:.3f}$, $R^2={f['gompertz_r2']:.3f}$"
        )
        ax.set_xlabel("Normalized individual income")
        ax.set_ylabel(r"$\ln[\ln(F)]$")
        ax.grid(True, alpha=0.3)
    handles, labels = axes.ravel()[0].get_legend_handles_labels()
    fig.legend(
        handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.985),
        ncol=4, frameon=True,
    )
    finish_grid(
        fig, axes, len(years),
        "Gompertz region - fixed-A Moura-Ribeiro fit",
        output_path, top=0.965,
    )

def plot_pareto_regime_fits(curves, fits, years, output_path, ncols=4, figsize=None):
    fit_i = fits.set_index("year")
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize)
    for i, year in enumerate(years):
        f = fit_i.loc[year]
        ax = axes.ravel()[i]
        status = str(f["pareto_selection_status"])
        if status.startswith("unsupported_"):
            ax.text(
                0.5,
                0.5,
                "Pareto tail not supported",
                transform=ax.transAxes,
                ha="center",
                va="center",
            )
            ax.set_title(f"{year} - Pareto tail not supported")
            ax.set_xlabel("Normalized individual income")
            ax.set_ylabel("CCDF (%)")
            ax.grid(True, alpha=0.3)
            continue

        xp = float(f["pareto_x_pmin"])
        xt = float(f["transition_x_t"])
        d = curves[
            (curves["year"] == year)
            & (curves["income_normalized"] >= min(xt, xp))
        ]
        ax.scatter(
            d["income_normalized"], d["empirical_ccdf_percent"],
            s=12, alpha=0.7, color="0.35", label="Empirical CCDF",
        )
        ax.plot(
            d["income_normalized"], d["pareto_fitted_ccdf_percent_mle"],
            linewidth=1.8, color="tab:blue", label="Pareto MLE",
        )
        ax.plot(
            d["income_normalized"], d["pareto_fitted_ccdf_percent_ls"],
            linewidth=1.4, linestyle="--", color="tab:orange", label="Pareto LSF",
        )
        ax.axvline(
            xt, linestyle=":", linewidth=1.0, color="black", label=r"$x_t$"
        )
        ax.axvline(
            xp, linestyle="-.", linewidth=1.0, color="0.5", label=r"$x_{P,\min}$"
        )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(
            fr"{year} - $lpha_{{MLE}}={f['pareto_alpha_mle']:.3f}$, $R^2_{{LS}}={f['pareto_ls_r2']:.3f}$"
        )
        ax.set_xlabel("Normalized individual income")
        ax.set_ylabel("CCDF (%)")
        ax.grid(True, alpha=0.3)
    handles, labels = axes.ravel()[0].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.985),
            ncol=5, frameon=True,
        )
    finish_grid(
        fig, axes, len(years),
        "Pareto region - direct MLE and log-binned CCDF LSF",
        output_path, top=0.965,
    )

def save_table(df, filename, tables_path):
    path = tables_path / filename
    df.to_csv(path, index=False)
    return path


GOMPERTZ_ANNUAL_COLUMNS = [
    "year",
    "log_bin_ratio",
    "normalization_mean_income_adj_2025_usd",
    "positive_income_observation_n",
    "gompertz_A",
    "gompertz_B",
    "gompertz_r2",
    "gompertz_sse",
    "gompertz_x_gmax",
    "gompertz_point_n",
    "gompertz_selection_status",
    "gompertz_boundary_A_free",
    "gompertz_boundary_B_free",
    "gompertz_boundary_r2_free",
    "gompertz_population_n",
    "gompertz_population_pct",
    "gompertz_ccdf_at_x_t_percent",
]

PARETO_ANNUAL_COLUMNS = [
    "year",
    "pareto_x_pmin",
    "pareto_selection_alpha",
    "pareto_selection_r2",
    "pareto_selection_status",
    "transition_x_t",
    "transition_delta_x_t",
    "transition_rule",
    "pareto_population_n",
    "pareto_population_pct",
    "pareto_alpha_ls",
    "pareto_beta_ls",
    "pareto_ls_r2",
    "pareto_ls_sse",
    "pareto_alpha_mle",
    "pareto_alpha_mle_fisher_se",
    "pareto_beta_mle_continuity",
    "cutoff_normalized",
    "cutoff_income_adj",
    "pareto_alpha",
    "pareto_r2",
]


def split_regime_annual(regime_fits):
    gompertz = regime_fits[GOMPERTZ_ANNUAL_COLUMNS].copy()
    pareto = regime_fits[PARETO_ANNUAL_COLUMNS].copy()
    return gompertz, pareto


def run_analysis_layer(layer, data_path, file_pattern, tables_path, figures_path):
    tables_path.mkdir(parents=True, exist_ok=True)
    figures_path.mkdir(parents=True, exist_ok=True)
    results = pipeline(
        data_path=data_path,
        file_pattern=file_pattern,
        layer=layer,
        bin_ratio=BIN_RATIO,
    )
    years = results["years"]
    files = results["files_by_year"]
    stats = results["df_stats_year"]
    ccdf = results["df_ccdf"]
    bins = results["df_bins"]
    lorenz = results["df_lorenz"]
    hist = build_histogram_dataset(files, years, bins=100)
    gini_validation = build_gini_validation(stats)
    stats = stats.merge(
        gini_validation.drop(columns=["Gini"]),
        on="year",
        how="left",
        validate="one_to_one",
    )
    regime_fits, regime_curves = build_regime_datasets(files, results["df_metadata"])
    gompertz_annual, pareto_annual = split_regime_annual(regime_fits)

    legacy_names = [
        f"{layer}_analysis_statistics_annual.csv",
        f"{layer}_analysis_ccdf_empirical.csv",
        f"{layer}_analysis_geometric_bins.csv",
        f"{layer}_analysis_lorenz.csv",
        f"{layer}_analysis_histograms.csv",
        f"{layer}_analysis_gini_validation_vs_ipea_wb_annual.csv",
        f"{layer}_analysis_gompertz_pareto_annual.csv",
        f"{layer}_analysis_regime_curves.csv",
    ]
    for filename in legacy_names:
        (tables_path / filename).unlink(missing_ok=True)

    tables = {
        "statistics_annual.csv": stats,
        "geometric_bins.csv": bins,
        "lorenz.csv": lorenz,
        "gompertz_annual.csv": gompertz_annual,
        "pareto_annual.csv": pareto_annual,
        "gompertz_pareto_curves.csv": regime_curves,
    }
    for filename, frame in tables.items():
        save_table(frame, filename, tables_path)

    for legacy_path in figures_path.glob("*.svg"):
        legacy_path.unlink(missing_ok=True)

    for legacy_path in figures_path.glob(f"{layer}_analysis_*.png"):
        legacy_path.unlink(missing_ok=True)
    (figures_path / "ccdf_lnln.png").unlink(missing_ok=True)

    income_plot_stats = stats.copy()
    income_plot_stats["xmin"] = np.where(
        income_plot_stats["n_zero"] > 0,
        0.0,
        income_plot_stats["xmin_positive"],
    )

    plot_histograms(hist, years, figures_path / "histograms.png", ncols=4)
    plot_income_mean_median(income_plot_stats, figures_path / "income_mean_median.png")
    plot_ccdf_loglog(ccdf, years, figures_path / "ccdf_loglog.png", ncols=4)
    plot_lorenz_indices_pretty(
        lorenz, stats, years,
        figures_path / "lorenz_geometry.png",
        ncols=3,
    )
    plot_top_shares(stats, figures_path / "top_income_shares.png")
    plot_top_shares_exclusive(stats, figures_path / "top_income_exclusive_shares.png")
    plot_top_shares_mean_median(stats, figures_path / "top_income_shares_mean_median.png")
    plot_inequality_indices(stats, figures_path / "inequality_indices.png")
    plot_inequality_indices_grid(stats, figures_path / "inequality_indices_2x2.png")
    plot_gini_validation(gini_validation, figures_path / "gini_validation.png")
    plot_gompertz_regime_fits(
        regime_curves, regime_fits, years,
        figures_path / "gompertz_fit.png",
        ncols=4,
        figsize=(20, 60),
    )
    plot_pareto_regime_fits(
        regime_curves, regime_fits, years,
        figures_path / "pareto_fit.png",
        ncols=4,
        figsize=(20, 60),
    )
    return {
        **results,
        "df_histograms": hist,
        "df_gini_validation": gini_validation,
        "df_gompertz_annual": gompertz_annual,
        "df_pareto_annual": pareto_annual,
        "df_gompertz_pareto_curves": regime_curves,
        "df_regime_fits": regime_fits,
        "df_regime_curves": regime_curves,
    }


def run_analysis():
    trusted = run_analysis_layer(
        "trusted",
        TRUSTED_DATA_PATH,
        "pnad_trusted_*.parquet",
        TABLES_ANALYSIS_TRUSTED_PATH,
        FIGURES_ANALYSIS_TRUSTED_PATH,
    )
    refined = run_analysis_layer(
        "refined",
        REFINED_DATA_PATH,
        "pnad_refined_*.parquet",
        TABLES_ANALYSIS_REFINED_PATH,
        FIGURES_ANALYSIS_REFINED_PATH,
    )
    return {"trusted": trusted, "refined": refined}

# --- Stage-03 uncertainty/reproduction features ---

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
        "Annual sample counts, nominal and 2025-US$ income statistics, inequality "
        "indices, top-income shares, and external Gini comparisons."
    ),
    "geometric_bins.csv": (
        "Geometric-bin summaries of annual income expressed in constant 2025 US$, "
        "using the canonical multiplicative bin ratio 1.10."
    ),
    "gompertz_annual.csv": (
        "Annual Gompertz-body estimates, free-intercept diagnostics, bootstrap "
        "uncertainties, exponential comparison diagnostics, and body population/income shares."
    ),
    "pareto_annual.csv": (
        "Annual Pareto-tail boundaries and estimates from log-log least squares and "
        "direct maximum likelihood, with Fisher, likelihood-width, and bootstrap uncertainties."
    ),
    "gompertz_pareto_curves.csv": (
        "Binned empirical CCDF coordinates and fitted Gompertz/Pareto curves used for "
        "regime selection, estimation, diagnostics, and publication figures."
    ),
    "lorenz.csv": (
        "Annual Lorenz-curve coordinates giving cumulative population and income shares."
    ),
    METADATA_FILE: (
        "Data dictionary describing every canonical Stage-03 analytical table and column."
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

COLUMN_DESCRIPTIONS = {
    "year": "PNAD or PNAD Contínua survey/reference year.",
    "N": "Total number of observations in the analytical annual sample.",
    "N_valid": "Number of observations with valid finite income values used in annual statistics.",
    "n_nan": "Number of observations with missing or non-numeric income.",
    "n_zero": "Number of observations with zero income.",
    "n_negative": "Number of observations with negative income.",
    "xmin_positive_nominal": "Smallest strictly positive income in the original nominal monetary scale.",
    "xmax_nominal": "Largest income in the original nominal monetary scale.",
    "mean_nominal": "Arithmetic mean income in the original nominal monetary scale.",
    "median_nominal": "Median income in the original nominal monetary scale.",
    "std_nominal": "Sample standard deviation of income in the original nominal monetary scale.",
    "income_sum_nominal": "Sum of income in the original nominal monetary scale.",
    "xmin_positive": "Smallest strictly positive income converted to constant 2025 US$.",
    "xmax": "Largest income converted to constant 2025 US$.",
    "mean": "Arithmetic mean income converted to constant 2025 US$.",
    "median": "Median income converted to constant 2025 US$.",
    "std": "Sample standard deviation of income converted to constant 2025 US$.",
    "income_sum": "Sum of income converted to constant 2025 US$.",
    "Gini": "Gini coefficient computed from the annual analytical income distribution.",
    "Pietra": "Pietra index computed from the annual Lorenz curve.",
    "Kolkata": "Kolkata index as a population fraction, defined by the Lorenz-curve crossing condition.",
    "Kolkata_pct": "Kolkata index expressed as a percentage of the population.",
    "Zanardi": "Zanardi inequality index computed from the annual income distribution.",
    "top_10": "Fraction of total income received by the top 10% of observations ranked by income.",
    "top_1": "Fraction of total income received by the top 1% of observations ranked by income.",
    "top_01": "Fraction of total income received by the top 0.1% of observations ranked by income.",
    "IPEA": "External IPEA Gini coefficient for the corresponding year, when available.",
    "Banco_Mundial": "External World Bank Gini coefficient for the corresponding year, when available.",
    "diff_IPEA": "Difference between the Stage-03 Gini estimate and the IPEA Gini value.",
    "diff_Banco_Mundial": "Difference between the Stage-03 Gini estimate and the World Bank Gini value.",
    "bin_left": "Lower boundary of the geometric income bin in constant 2025 US$.",
    "bin_right": "Upper boundary of the geometric income bin in constant 2025 US$.",
    "bin_center_geo": "Geometric center of the income bin in constant 2025 US$.",
    "N_bin": "Number of observations assigned to the geometric income bin.",
    "geometric_mean": "Geometric mean income within the bin in constant 2025 US$.",
    "ccdf": "Empirical complementary cumulative distribution evaluated at the bin threshold as a probability.",
    "log_bin_ratio": "Multiplicative ratio between consecutive geometric-bin boundaries; fixed at 1.10 in the canonical analysis.",
    "normalization_mean_income_adj_2025_usd": "Annual positive-income mean in constant 2025 US$, used to normalize income before regime fitting.",
    "positive_income_observation_n": "Number of strictly positive income observations entering the normalized distribution analysis.",
    "gompertz_A": "Canonical Gompertz parameter A fixed by G(0)=100, so A=ln[ln(100)].",
    "gompertz_B": "Canonical Gompertz slope parameter B estimated by least squares with A fixed.",
    "gompertz_r2": "Coefficient of determination of the selected fixed-A Gompertz fit in transformed coordinates.",
    "gompertz_sse": "Sum of squared residuals of the selected fixed-A Gompertz fit in transformed coordinates.",
    "gompertz_x_gmax": "Upper normalized-income boundary of the selected Gompertz regime.",
    "gompertz_point_n": "Number of binned CCDF points used in the selected Gompertz fit.",
    "gompertz_selection_status": "Rule/status describing how the upper Gompertz boundary was selected.",
    "gompertz_boundary_A_free": "Intercept A from the unconstrained Gompertz linearization used as a boundary and 2009-method diagnostic.",
    "gompertz_boundary_B_free": "Slope parameter B from the unconstrained Gompertz linearization used as a boundary and 2009-method diagnostic.",
    "gompertz_boundary_r2_free": "Coefficient of determination of the unconstrained free-intercept Gompertz diagnostic fit.",
    "gompertz_population_n": "Number of observations assigned below the Gompertz-Pareto transition threshold.",
    "gompertz_population_pct": "Percentage of observations assigned below the Gompertz-Pareto transition threshold.",
    "gompertz_ccdf_at_x_t_percent": "Gompertz CCDF evaluated at the transition threshold, expressed in percent.",
    "bootstrap_reps": "Number of bootstrap resamples used to estimate the reported bootstrap standard errors.",
    "gompertz_B_bootstrap_se": "Bootstrap standard error of the canonical fixed-A Gompertz B estimate.",
    "gompertz_A_free_bootstrap_se": "Bootstrap standard error of the free-intercept Gompertz A diagnostic.",
    "gompertz_B_free_bootstrap_se": "Bootstrap standard error of the free-intercept Gompertz B diagnostic.",
    "exponential_intercept": "Intercept of the comparison fit ln F(x)=c-alpha x over the selected Gompertz interval.",
    "exponential_alpha": "Positive decay coefficient alpha of the comparison exponential-body fit.",
    "exponential_r2": "Coefficient of determination of the comparison exponential-body fit.",
    "gompertz_income_share_pct": "Percentage of total income received by observations below the transition threshold.",
    "pareto_x_pmin": "Lower normalized-income boundary selected for the Pareto tail.",
    "pareto_selection_alpha": "Pareto exponent from the candidate tail fit used during threshold selection.",
    "pareto_selection_r2": "Coefficient of determination of the candidate log-log Pareto fit used during threshold selection.",
    "pareto_selection_status": "Rule/status describing how the lower Pareto boundary was selected.",
    "transition_x_t": "Normalized-income threshold joining the Gompertz body and Pareto tail.",
    "transition_delta_x_t": "Half-width of the gap between selected Gompertz and Pareto boundaries when they do not coincide.",
    "transition_rule": "Rule used to define x_t from the selected Gompertz and Pareto boundaries.",
    "pareto_population_n": "Number of observations assigned at or above the Pareto transition threshold.",
    "pareto_population_pct": "Percentage of observations assigned at or above the Pareto transition threshold.",
    "pareto_alpha_ls": "Pareto exponent alpha estimated by log-log least squares.",
    "pareto_beta_ls": "Pareto amplitude beta estimated by log-log least squares on the percent-scale CCDF.",
    "pareto_ls_r2": "Coefficient of determination of the selected log-log least-squares Pareto fit.",
    "pareto_ls_sse": "Sum of squared residuals of the selected log-log least-squares Pareto fit.",
    "pareto_alpha_mle": "Pareto exponent alpha estimated directly by maximum likelihood above x_t.",
    "pareto_alpha_mle_fisher_se": "Asymptotic Fisher-information standard error of the direct-MLE Pareto exponent.",
    "pareto_beta_mle_continuity": "Pareto amplitude beta determined by enforcing Gompertz-Pareto continuity at x_t.",
    "cutoff_normalized": "Normalized-income cutoff associated with the selected transition/tail analysis.",
    "cutoff_income_adj": "Monetary value of the cutoff converted to constant 2025 US$.",
    "pareto_alpha": "Compatibility field for the canonical Pareto exponent retained in the Stage-03 output.",
    "pareto_r2": "Compatibility field for the canonical Pareto goodness-of-fit statistic retained in the Stage-03 output.",
    "pareto_alpha_ls_bootstrap_se": "Bootstrap standard error of the log-log least-squares Pareto exponent.",
    "pareto_beta_ls_bootstrap_se": "Bootstrap standard error of the log-log least-squares Pareto amplitude.",
    "pareto_alpha_mle_bootstrap_se": "Bootstrap standard error of the direct-MLE Pareto exponent.",
    "pareto_beta_mle_bootstrap_se": "Bootstrap standard error of the continuity-based direct-MLE Pareto amplitude.",
    "pareto_alpha_mle_likelihood_se": "Likelihood-width standard error of the direct-MLE Pareto exponent following the 2009 prescription.",
    "pareto_beta_mle_likelihood_se": "Uncertainty in continuity-based Pareto beta propagated from the likelihood-width alpha uncertainty.",
    "pareto_mle_r2": "Log-scale coefficient of determination of the direct-MLE Pareto curve against the empirical CCDF.",
    "pareto_supported": "Whether the selected Pareto tail satisfies the configured support criterion.",
    "pareto_income_share_pct": "Percentage of total income received by observations at or above the transition threshold.",
    "income_normalized": "Income divided by the annual mean of strictly positive income observations.",
    "bin_right_normalized": "Upper boundary of the corresponding geometric bin expressed in normalized-income units.",
    "observations_in_bin": "Number of observations represented by the binned CCDF point.",
    "empirical_ccdf_probability": "Empirical complementary cumulative distribution as a probability in [0,1].",
    "empirical_ccdf_percent": "Empirical complementary cumulative distribution expressed in percent.",
    "gompertz_transform": "Double-log Gompertz transform ln[ln F(x)] using F on the percent scale.",
    "regime": "Regime label identifying whether the binned point belongs to the Gompertz body, transition, or Pareto tail.",
    "income_adj_2025_usd": "Income coordinate of the binned point converted to constant 2025 US$.",
    "gompertz_fitted_transform": "Fitted fixed-A Gompertz relation A-Bx in double-log transformed coordinates.",
    "pareto_fitted_ccdf_percent_ls": "Pareto CCDF fitted by log-log least squares, expressed in percent.",
    "pareto_fitted_ccdf_percent_mle": "Pareto CCDF fitted with the direct-MLE exponent and continuity amplitude, expressed in percent.",
    "pareto_fitted_ccdf_percent": "Canonical Pareto fitted CCDF retained for compatibility, expressed in percent.",
    "population_share": "Cumulative share of observations along the Lorenz curve.",
    "income_share": "Cumulative share of total income along the Lorenz curve.",
}

COLUMN_UNITS = {
    "year": "year",
    "N": "count",
    "N_valid": "count",
    "n_nan": "count",
    "n_zero": "count",
    "n_negative": "count",
    "xmin_positive_nominal": "nominal currency units",
    "xmax_nominal": "nominal currency units",
    "mean_nominal": "nominal currency units",
    "median_nominal": "nominal currency units",
    "std_nominal": "nominal currency units",
    "income_sum_nominal": "nominal currency units",
    "xmin_positive": "2025 US$",
    "xmax": "2025 US$",
    "mean": "2025 US$",
    "median": "2025 US$",
    "std": "2025 US$",
    "income_sum": "2025 US$",
    "Gini": "dimensionless",
    "Pietra": "dimensionless",
    "Kolkata": "fraction",
    "Kolkata_pct": "%",
    "Zanardi": "dimensionless",
    "top_10": "fraction",
    "top_1": "fraction",
    "top_01": "fraction",
    "IPEA": "dimensionless",
    "Banco_Mundial": "dimensionless",
    "diff_IPEA": "dimensionless",
    "diff_Banco_Mundial": "dimensionless",
    "bin_left": "2025 US$",
    "bin_right": "2025 US$",
    "bin_center_geo": "2025 US$",
    "N_bin": "count",
    "geometric_mean": "2025 US$",
    "ccdf": "fraction",
    "log_bin_ratio": "dimensionless",
    "normalization_mean_income_adj_2025_usd": "2025 US$",
    "positive_income_observation_n": "count",
    "gompertz_point_n": "count",
    "gompertz_selection_status": "text",
    "gompertz_population_n": "count",
    "gompertz_population_pct": "%",
    "gompertz_ccdf_at_x_t_percent": "%",
    "bootstrap_reps": "count",
    "gompertz_income_share_pct": "%",
    "pareto_selection_status": "text",
    "transition_rule": "text",
    "pareto_population_n": "count",
    "pareto_population_pct": "%",
    "pareto_beta_ls": "CCDF-percent scale",
    "pareto_beta_mle_continuity": "CCDF-percent scale",
    "cutoff_income_adj": "2025 US$",
    "pareto_beta_ls_bootstrap_se": "CCDF-percent scale",
    "pareto_beta_mle_bootstrap_se": "CCDF-percent scale",
    "pareto_beta_mle_likelihood_se": "CCDF-percent scale",
    "pareto_supported": "boolean",
    "pareto_income_share_pct": "%",
    "income_normalized": "normalized income",
    "bin_right_normalized": "normalized income",
    "observations_in_bin": "count",
    "empirical_ccdf_probability": "fraction",
    "empirical_ccdf_percent": "%",
    "regime": "text",
    "gompertz_x_gmax": "normalized income",
    "pareto_x_pmin": "normalized income",
    "transition_x_t": "normalized income",
    "transition_delta_x_t": "normalized income",
    "cutoff_normalized": "normalized income",
    "income_adj_2025_usd": "2025 US$",
    "pareto_fitted_ccdf_percent_ls": "%",
    "pareto_fitted_ccdf_percent_mle": "%",
    "pareto_fitted_ccdf_percent": "%",
    "population_share": "fraction",
    "income_share": "fraction",
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
    data = curves[
        (curves["year"] == year)
        & (curves["income_normalized"] <= x_gmax)
        & (curves["empirical_ccdf_percent"] > 0)
    ]
    x = data["income_normalized"].to_numpy(float)
    y = np.log(data["empirical_ccdf_percent"].to_numpy(float))
    if len(x) < 2 or np.unique(x).size < 2:
        return np.nan, np.nan, np.nan
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    tss = float(np.sum((y - y.mean()) ** 2))
    r2 = np.nan if tss <= 0 else float(1.0 - np.sum((y - fitted) ** 2) / tss)
    return float(intercept), float(-slope), r2

def _mle_r2(curves, fit, year):
    x_t = float(fit["transition_x_t"])
    data = curves[
        (curves["year"] == year)
        & (curves["income_normalized"] >= x_t)
        & (curves["empirical_ccdf_percent"] > 0)
    ]
    return r2_log(
        data["empirical_ccdf_percent"],
        data["pareto_fitted_ccdf_percent_mle"],
    )

def build_diagnostics_annual(layer: str) -> pd.DataFrame:
    """Compute non-bootstrap annual diagnostics required downstream."""
    cfg, _, _, annual, curves, _, years = _load_layer(layer)
    annual_i = annual.set_index("year")
    rows = []

    for year in years:
        fit = annual_i.loc[year]
        x = _normalized_income(year, cfg)
        selection_status = str(fit["pareto_selection_status"])
        pareto_estimable = not selection_status.startswith("unsupported_")

        exp_intercept, exp_alpha, exp_r2 = _exponential_diagnostics(
            curves, fit, year
        )

        if pareto_estimable:
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
            pareto_mle_r2 = _mle_r2(curves, fit, year)
        else:
            gompertz_income_share = np.nan
            pareto_income_share = np.nan
            likelihood_se = np.nan
            beta_likelihood_se = np.nan
            pareto_mle_r2 = np.nan

        pareto_supported = (
            selection_status == "earliest_tail_start_with_r2_ge_0.98"
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
                "pareto_mle_r2": pareto_mle_r2,
                "pareto_supported": bool(pareto_supported),
                "pareto_income_share_pct": pareto_income_share,
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)

def _description(column: str) -> str:
    if column in COLUMN_DESCRIPTIONS:
        return COLUMN_DESCRIPTIONS[column]
    if column.endswith("_r2") or column.endswith("_r2_free"):
        return "Coefficient of determination for the indicated fitted model."
    if column.endswith("_sse"):
        return "Sum of squared residuals for the indicated fitted model."
    if column.endswith("_pct"):
        return column.replace("_", " ").capitalize() + "."
    return column.replace("_", " ").capitalize() + "."

def _unit(column: str) -> str:
    if column in COLUMN_UNITS:
        return COLUMN_UNITS[column]
    if column.endswith("_n"):
        return "count"
    if column.endswith("_pct"):
        return "%"
    if "2025_usd" in column or column.endswith("_income_adj"):
        return "2025 US$"
    if column.endswith("_status") or column.endswith("_rule"):
        return "text"
    if "beta" in column and "gompertz" not in column:
        return "CCDF-percent scale"
    return "dimensionless"

def _source(column: str) -> str:
    if column in {"IPEA", "diff_IPEA"}:
        return "IPEA auxiliary Gini series + Stage 03 analytical pipeline"
    if column in {"Banco_Mundial", "diff_Banco_Mundial"}:
        return "World Bank auxiliary Gini series + Stage 03 analytical pipeline"
    if "bootstrap" in column:
        return "Stage 03 Moura–Ribeiro bootstrap diagnostics"
    if "likelihood" in column:
        return "Stage 03 Moura–Ribeiro likelihood-width diagnostics"
    if column.startswith("exponential_"):
        return "Stage 03 exponential-vs-Gompertz diagnostic"
    return "Stage 03 analytical pipeline"

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
                    "source": _source(column),
                }
            )

    metadata_columns = {
        "table_name": "Canonical Stage-03 table containing the documented field.",
        "table_description": "Scientific description of the table as a whole.",
        "column_name": "Column documented by this metadata row.",
        "description": "Scientific definition of the column.",
        "unit": "Measurement unit, scale, or data type.",
        "source": "Primary data source or computational derivation of the field.",
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
        refined_columns = list(pd.read_csv(refined / name, nrows=0).columns)
        trusted_columns = list(pd.read_csv(trusted / name, nrows=0).columns)
        if refined_columns != trusted_columns:
            raise AssertionError(
                f"Schema mismatch for {name}: {refined_columns} != {trusted_columns}"
            )

COLUMN_DESCRIPTIONS.update({
    "income_observation_n": "Number of strictly positive income observations used in annual publication summaries.",
    "income_mean_2025_usd": "Arithmetic mean of strictly positive annual income in constant 2025 US$.",
    "income_median_2025_usd": "Median of strictly positive annual income in constant 2025 US$.",
    "income_std_2025_usd": "Sample standard deviation of strictly positive annual income in constant 2025 US$.",
})
for _prefix, _label in (("p90_p99", "90th to 99th"), ("p99_p999", "99th to 99.9th"), ("p999_p100", "99.9th to 100th")):
    COLUMN_DESCRIPTIONS[f"{_prefix}_population_n"] = f"Number of positive-income observations in the {_label} percentile-rank band."
    COLUMN_DESCRIPTIONS[f"{_prefix}_income_share_pct"] = f"Percentage of total positive income received in the {_label} percentile-rank band."
    COLUMN_DESCRIPTIONS[f"{_prefix}_mean_income_2025_usd"] = f"Mean income in the {_label} percentile-rank band in constant 2025 US$."
    COLUMN_DESCRIPTIONS[f"{_prefix}_median_income_2025_usd"] = f"Median income in the {_label} percentile-rank band in constant 2025 US$."
    COLUMN_DESCRIPTIONS[f"{_prefix}_std_income_2025_usd"] = f"Income standard deviation in the {_label} percentile-rank band in constant 2025 US$."
    COLUMN_UNITS[f"{_prefix}_population_n"] = "count"
    COLUMN_UNITS[f"{_prefix}_income_share_pct"] = "%"
    for _suffix in ("mean_income_2025_usd", "median_income_2025_usd", "std_income_2025_usd"):
        COLUMN_UNITS[f"{_prefix}_{_suffix}"] = "2025 US$"
COLUMN_UNITS.update({
    "income_observation_n": "count",
    "income_mean_2025_usd": "2025 US$",
    "income_median_2025_usd": "2025 US$",
    "income_std_2025_usd": "2025 US$",
})


def run_diagnostics():
    results = {layer: run_layer(layer) for layer in ("trusted", "refined")}
    validate_parallel_schemas()
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run canonical PNAD Stage 03.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--analysis-only", action="store_true")
    mode.add_argument("--diagnostics-only", action="store_true")
    args = parser.parse_args(argv)
    if args.diagnostics_only:
        return run_diagnostics()
    analysis = run_analysis()
    if args.analysis_only:
        return analysis
    diagnostics = run_diagnostics()
    return {"analysis": analysis, "diagnostics": diagnostics}


if __name__ == "__main__":
    main()
