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


def make_grid(n, cols=4, figsize=None, width_per_col=4.2, height_per_row=3.4,
              sharex=False, sharey=False):
    rows = int(np.ceil(n / cols))
    if figsize is None:
        figsize = (width_per_col * cols, height_per_row * rows)
    return plt.subplots(rows, cols, figsize=figsize, squeeze=False, sharex=sharex, sharey=sharey)


def finish_grid(fig, axes, n_used, suptitle, path, dpi=250):
    rows, cols = axes.shape
    for j in range(n_used, rows * cols):
        row, col = divmod(j, cols)
        fig.delaxes(axes[row, col])
    fig.suptitle(suptitle, fontsize=18, y=0.998)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
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


def plot_income_mean_median(df, output_path, figsize=(14, 5)):
    fig, axes = plt.subplots(1, 2, figsize=figsize, squeeze=False, sharex=True)
    full_years = np.arange(int(df["year"].min()), int(df["year"].max()) + 1)
    indexed = df.set_index("year").reindex(full_years)
    for ax, column, title in zip(axes.ravel(), ["mean", "median"], ["Mean income", "Median income"]):
        y = indexed[column].interpolate(method="linear", limit_direction="both")
        ax.plot(full_years, y, marker="o", markersize=3, linewidth=1.5)
        ax.set_title(title)
        ax.set_xlabel("Year")
        ax.set_ylabel("Adjusted income (2025 US$)")
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
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


def plot_ccdf_lnln(df, years, output_path, ncols=4, figsize=None):
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize, sharey=True)
    for i, year in enumerate(years):
        d = df[(df["year"] == year) & df["ln_ln_ccdf_pct"].notna()]
        ax = axes.ravel()[i]
        ax.plot(d["x"], d["ln_ln_ccdf_pct"], linewidth=1.5)
        ax.set_title(str(year))
        ax.grid(True, alpha=0.3)
    finish_grid(fig, axes, len(years), "ln[ln F(x)] with F in percent - PNAD", output_path)


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
    ax.set_title("Income concentration")
    ax.set_xlabel("Year")
    ax.set_ylabel("% of total income")
    ax.legend()
    ax.grid(True, alpha=0.3)
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
        y = indexed[col].interpolate(method="linear", limit_direction="both")
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
    return (np.nan if np.isclose(tss, 0) else float(1.0 - sse / tss)), sse


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
    curve = build_regime_ccdf(income_normalized)
    gompertz = select_gompertz_region(curve)
    pareto = select_pareto_region(curve, gompertz["gompertz_x_gmax"])
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
    if not np.allclose(
        fit_table["gompertz_population_pct"] + fit_table["pareto_population_pct"],
        100.0,
        rtol=0.0,
        atol=1e-10,
    ):
        raise AssertionError("Gompertz and Pareto population percentages must sum to 100%.")
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
        ax.scatter(d["income_normalized"], d["gompertz_transform"], s=12, alpha=0.7)
        ax.plot(d["income_normalized"], d["gompertz_fitted_transform"], linewidth=1.8)
        ax.axvline(xg, linestyle="--", linewidth=1.0)
        ax.set_title(
            fr"{year} - $A={f['gompertz_A']:.3f}$, $B={f['gompertz_B']:.3f}$, $R^2={f['gompertz_r2']:.3f}$"
        )
        ax.set_xlabel("Normalized individual income")
        ax.set_ylabel(r"$\ln[\ln(F)]$")
        ax.grid(True, alpha=0.3)
    finish_grid(fig, axes, len(years), "Gompertz region - fixed-A Moura-Ribeiro LSF", output_path)


def plot_pareto_regime_fits(curves, fits, years, output_path, ncols=4, figsize=None):
    fit_i = fits.set_index("year")
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize)
    for i, year in enumerate(years):
        f = fit_i.loc[year]
        xp = float(f["pareto_x_pmin"])
        xt = float(f["transition_x_t"])
        d = curves[
            (curves["year"] == year)
            & (curves["income_normalized"] >= min(xt, xp))
        ]
        ax = axes.ravel()[i]
        ax.scatter(d["income_normalized"], d["empirical_ccdf_percent"], s=12, alpha=0.7)
        ax.plot(d["income_normalized"], d["pareto_fitted_ccdf_percent_mle"], linewidth=1.8, label="MLE")
        ax.plot(d["income_normalized"], d["pareto_fitted_ccdf_percent_ls"], linewidth=1.2, linestyle="--", label="LSF")
        ax.axvline(xt, linestyle=":", linewidth=1.0)
        ax.axvline(xp, linestyle="--", linewidth=1.0)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(
            fr"{year} - $\alpha_{{MLE}}={f['pareto_alpha_mle']:.3f}$, $R^2_{{LS}}={f['pareto_ls_r2']:.3f}$"
        )
        ax.set_xlabel("Normalized individual income")
        ax.set_ylabel("CCDF (%)")
        ax.grid(True, alpha=0.3)
    finish_grid(fig, axes, len(years), "Pareto region - direct MLE and log-binned CCDF LSF", output_path)


def save_table(df, filename, tables_path):
    path = tables_path / filename
    df.to_csv(path, index=False)
    return path


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
    regime_fits, regime_curves = build_regime_datasets(files, results["df_metadata"])

    prefix = f"{layer}_analysis"
    tables = {
        f"{prefix}_statistics_annual.csv": stats,
        f"{prefix}_ccdf_empirical.csv": ccdf,
        f"{prefix}_geometric_bins.csv": bins,
        f"{prefix}_lorenz.csv": lorenz,
        f"{prefix}_histograms.csv": hist,
        f"{prefix}_gini_validation_vs_ipea_wb_annual.csv": gini_validation,
        f"{prefix}_gompertz_pareto_annual.csv": regime_fits,
        f"{prefix}_regime_curves.csv": regime_curves,
    }
    for filename, frame in tables.items():
        save_table(frame, filename, tables_path)

    plot_histograms(hist, years, figures_path / f"{prefix}_histograms.svg", ncols=4)
    plot_income_mean_median(stats, figures_path / f"{prefix}_income_mean_median.svg")
    plot_ccdf_loglog(ccdf, years, figures_path / f"{prefix}_ccdf_loglog.svg", ncols=4)
    plot_ccdf_lnln(ccdf, years, figures_path / f"{prefix}_ccdf_lnln.svg", ncols=4)
    plot_lorenz_indices_pretty(
        lorenz, stats, years,
        figures_path / f"{prefix}_lorenz_geometry.svg",
        ncols=3,
    )
    plot_top_shares(stats, figures_path / f"{prefix}_top_income_shares.svg")
    plot_top_shares_mean_median(stats, figures_path / f"{prefix}_top_income_shares_mean_median.svg")
    plot_inequality_indices(stats, figures_path / f"{prefix}_inequality_indices.svg")
    plot_inequality_indices_grid(stats, figures_path / f"{prefix}_inequality_indices_2x2.svg")
    plot_gini_validation(gini_validation, figures_path / f"{prefix}_gini_validation.svg")
    plot_gompertz_regime_fits(
        regime_curves, regime_fits, years,
        figures_path / f"{prefix}_regime_fits_gompertz_ccdf_empirical.svg",
        ncols=4,
        figsize=(20, 60),
    )
    plot_pareto_regime_fits(
        regime_curves, regime_fits, years,
        figures_path / f"{prefix}_regime_fits_pareto_ccdf_empirical.svg",
        ncols=4,
        figsize=(20, 60),
    )
    return {
        **results,
        "df_histograms": hist,
        "df_gini_validation": gini_validation,
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


def main():
    results = run_analysis()
    for layer in ("trusted", "refined"):
        result = results[layer]
        print(f"{layer.capitalize()} processed years: {len(result['years'])}")
        print(result["df_regime_fits"].to_string(index=False))
        print()


if __name__ == "__main__":
    main()
