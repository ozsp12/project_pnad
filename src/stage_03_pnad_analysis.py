"""Run the complete PNAD analysis contained in notebook 04.

Stage 03 consumes only the trusted annual PNAD/PNAD Continua datasets and
persists every analytical object produced by the original notebook:
descriptive statistics, histogram data, geometric bins, empirical CCDF,
Gompertz transform, Lorenz curves, Gini/Pietra/Kolkata/Zanardi indices,
top-income shares, temporal diagnostics, external Gini validation, and the
notebook's Gompertz-Pareto least-squares regime analysis.

General analytical outputs are written to assets/tables_analysis and
assets/figures_analysis. Paper-specific assets are intentionally reserved
for stages 04 and 05.
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
TRUSTED_DATA_PATH = REPO_ROOT / "data" / "data_trusted"
GINI_REFERENCE_PATH = REPO_ROOT / "data" / "trusted" / "series_gini_ipea_banco_mundial.csv"

TABLES_ANALYSIS_PATH = REPO_ROOT / "assets" / "tables_analysis"
FIGURES_ANALYSIS_PATH = REPO_ROOT / "assets" / "figures_analysis"

BIN_RATIO = 1.05
LORENZ_GRID_SIZE = 1001
PLOT_COLS = 4


def geometric_edges(xmin, xmax, ratio=1.05):
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
    fig, axes = plt.subplots(
        rows,
        cols,
        figsize=figsize,
        squeeze=False,
        sharex=sharex,
        sharey=sharey,
    )
    return fig, axes


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
    wb = pick(cols, [
        "banco_mundial", "gini_banco_mundial", "serie_banco_mundial",
        "world_bank", "worldbank", "wb",
    ])

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
            q[source_col].str.contains("ipea", na=False),
            "IPEA",
            np.where(
                q[source_col].str.contains("banco|world|bank", regex=True, na=False),
                "Banco_Mundial",
                np.nan,
            ),
        )
        q = q.dropna(subset=[year_col, "source_norm"])
        out = q.pivot_table(
            index=year_col,
            columns="source_norm",
            values=value_col,
            aggfunc="first",
        ).reset_index().rename(columns={year_col: "year"})
        out["year"] = out["year"].astype(int)
        out.columns.name = None
        return out

    raise ValueError(f"External Gini CSV format not recognized. Columns: {sorted(cols)}")


def year_from_filename(path):
    match = re.search(r"(\d{4})$", path.stem)
    if not match:
        raise ValueError(f"Year not identified in {path.name}")
    return int(match.group(1))


def load_inputs(metadata_path=METADATA_PATH, trusted_data_path=TRUSTED_DATA_PATH):
    df_metadata = pd.read_excel(metadata_path)
    required = {"ano", "Exchange", "Inflation"}
    missing = required - set(df_metadata.columns)
    if missing:
        raise ValueError("Missing metadata columns: " + ", ".join(sorted(missing)))

    df_metadata = df_metadata.copy()
    df_metadata["ano"] = df_metadata["ano"].astype(int)

    files_by_year = {
        year_from_filename(path): path
        for path in trusted_data_path.glob("pnad_trusted_*.parquet")
    }
    years = sorted(files_by_year)

    if not years:
        raise RuntimeError(f"No trusted Parquet files found in {trusted_data_path}")

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

    ccdf_records = [
        {
            "year": year,
            "x": float(x),
            "ccdf": float(c),
            "ccdf_pct": float(cp),
            "ln_ln_ccdf_pct": float(ll) if np.isfinite(ll) else np.nan,
        }
        for x, c, cp, ll in zip(thresholds, ccdf, ccdf_pct, lnln)
    ]

    bins_records = []
    for i in range(len(edges) - 1):
        left, right = edges[i], edges[i + 1]
        mask_bin = (
            (positive_adjusted >= left)
            & (
                (positive_adjusted <= right)
                if i == len(edges) - 2
                else (positive_adjusted < right)
            )
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
    lorenz_records = [
        {
            "year": year,
            "population_share": float(p),
            "income_share": float(L),
        }
        for p, L in zip(lorenz_grid, sampled_income)
    ]

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


def pipeline(metadata_path=METADATA_PATH, trusted_data_path=TRUSTED_DATA_PATH,
             bin_ratio=BIN_RATIO, lorenz_grid_size=LORENZ_GRID_SIZE):
    df_metadata, files_by_year, years = load_inputs(metadata_path, trusted_data_path)
    metadata_index = df_metadata.set_index("ano")

    stats_records = []
    ccdf_records = []
    bins_records = []
    lorenz_records = []

    for year in tqdm(years, desc="Analyzing PNAD", unit="year"):
        stats, ccdf, bins, lorenz = analyze_year(
            year,
            files_by_year[year],
            metadata_index.loc[year],
            bin_ratio,
            lorenz_grid_size,
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
    if years is None:
        years = sorted(files_by_year)

    records = []
    for year in tqdm(years, desc="Histogram bins", unit="year"):
        df = pd.read_parquet(files_by_year[year])
        income = pd.to_numeric(df["renda"], errors="coerce").to_numpy(dtype=float)
        income = income[np.isfinite(income)]
        income = income[income >= 0]

        counts, edges = np.histogram(income, bins=bins)
        centers = 0.5 * (edges[:-1] + edges[1:])
        records.extend(
            {
                "year": int(year),
                "bin_left": float(left),
                "bin_right": float(right),
                "bin_center": float(center),
                "count": int(count),
            }
            for left, right, center, count
            in zip(edges[:-1], edges[1:], centers, counts)
        )

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


def plot_histograms(df_histograms, years, output_path, ncols=4, figsize=None):
    fig, axes = make_grid(
        len(years), cols=ncols, figsize=figsize,
        width_per_col=4.4, height_per_row=3.5, sharey=True,
    )
    for i, year in enumerate(years):
        temp = df_histograms[df_histograms["year"] == year]
        ax = axes.ravel()[i]
        ax.bar(
            temp["bin_left"], temp["count"],
            width=temp["bin_right"] - temp["bin_left"],
            align="edge", edgecolor="black", linewidth=0.35,
        )
        ax.set_yscale("log")
        ax.set_title(f"PNAD histogram - {year}", fontsize=10)
        ax.set_xlabel("Income")
        ax.set_ylabel("Frequency (log)")
        ax.grid(axis="y", alpha=0.25, linestyle="--")
    finish_grid(fig, axes, len(years), "Annual histograms - PNAD 1976-2025", output_path)


def plot_income_mean_median(df_stats_year, output_path, figsize=(14, 5)):
    metrics = [("mean", "Mean income"), ("median", "Median income")]
    fig, axes = plt.subplots(1, 2, figsize=figsize, squeeze=False, sharex=True)
    full_years = np.arange(int(df_stats_year["year"].min()), int(df_stats_year["year"].max()) + 1)
    indexed = df_stats_year.set_index("year").reindex(full_years)

    for ax, (column, title) in zip(axes.ravel(), metrics):
        interpolated = indexed[column].interpolate(
            method="linear",
            limit_direction="both",
        )
        ax.plot(
            full_years,
            interpolated,
            marker="o",
            markersize=3,
            linewidth=1.5,
        )
        ax.set_title(title)
        ax.set_xlabel("Year")
        ax.set_ylabel("Adjusted income (2025 US$)")
        ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)


def plot_ccdf_loglog(df_ccdf, years, output_path, ncols=4, figsize=None):
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize, sharey=True)
    for i, year in enumerate(years):
        temp = df_ccdf[
            (df_ccdf["year"] == year)
            & (df_ccdf["x"] > 0)
            & (df_ccdf["ccdf"] > 0)
        ]
        ax = axes.ravel()[i]
        ax.plot(temp["x"], temp["ccdf"], linewidth=1.5)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(str(year))
        ax.grid(True, which="both", alpha=0.25)
    finish_grid(fig, axes, len(years), "Empirical CCDF by year - PNAD 1976-2025", output_path)


def plot_ccdf_lnln(df_ccdf, years, output_path, ncols=4, figsize=None):
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize, sharey=True)
    for i, year in enumerate(years):
        temp = df_ccdf[
            (df_ccdf["year"] == year)
            & df_ccdf["ln_ln_ccdf_pct"].notna()
        ]
        ax = axes.ravel()[i]
        ax.plot(temp["x"], temp["ln_ln_ccdf_pct"], linewidth=1.5)
        ax.set_title(str(year))
        ax.grid(True, alpha=0.25)
    finish_grid(
        fig, axes, len(years),
        "ln[ln(100 x CCDF)] transform - PNAD 1976-2025",
        output_path,
    )


def plot_lorenz_indices_pretty(df_lorenz, df_stats_year, years, output_path,
                               ncols=3, figsize=None):
    stats_index = df_stats_year.set_index("year")
    fig, axes = make_grid(
        len(years), cols=ncols, figsize=figsize,
        width_per_col=4.3, height_per_row=4.1, sharex=True, sharey=True,
    )

    for i, year in enumerate(years):
        temp = df_lorenz[df_lorenz["year"] == year]
        row = stats_index.loc[year]
        ax = axes.ravel()[i]

        p = 100.0 * temp["population_share"].to_numpy()
        L = 100.0 * temp["income_share"].to_numpy()

        ax.fill_between(p, 0, L, alpha=0.15, label="area B")
        ax.plot(p, L, linewidth=1.8)
        ax.plot([0, 100], [0, 100], linewidth=1.2, label="equality line")

        k_pct = 100.0 * float(row["Kolkata"])
        q_pct = 100.0 - k_pct
        ax.scatter([k_pct], [q_pct], s=34, zorder=6)
        ax.plot([k_pct, k_pct], [0, q_pct], linestyle=":", linewidth=1.2)
        ax.plot([0, k_pct], [q_pct, q_pct], linestyle=":", linewidth=1.2)
        ax.text(k_pct, -5.5, "k", ha="center", va="top")
        ax.text(-5.5, q_pct, "100-k", ha="right", va="center")

        diff = p - L
        pietra_idx = int(np.argmax(diff))
        pietra_x = p[pietra_idx]
        pietra_y = L[pietra_idx]
        ax.plot([pietra_x, pietra_x], [pietra_y, pietra_x], linestyle="--", linewidth=1.5)
        ax.scatter([pietra_x], [pietra_y], s=22, zorder=6)
        ax.text(pietra_x + 1.5, 0.5 * (pietra_y + pietra_x), "p", va="center")

        ax.plot([], [], color="none", label=f"k: {k_pct:.3f}")
        ax.plot([], [], color="none", label=f"G: {row['Gini']:.3f}")
        ax.plot([], [], color="none", label=f"Z: {row['Zanardi']:.3f}")
        ax.plot([], [], color="none", label=f"p: {100.0 * row['Pietra']:.3f}")

        ax.set_title(str(year))
        ax.set_xlim(-5, 105)
        ax.set_ylim(-5, 105)
        ax.set_xlabel("households (%)")
        ax.set_ylabel("income (%)")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper left", fontsize=8, framealpha=0.85)

    finish_grid(
        fig, axes, len(years),
        "Lorenz curves and inequality geometry - PNAD 1976-2025",
        output_path,
    )


def plot_top_shares(df_stats_year, output_path, figsize=(14, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(df_stats_year["year"], 100 * df_stats_year["top_10"], marker="o", label="Top 10%")
    ax.plot(df_stats_year["year"], 100 * df_stats_year["top_1"], marker="s", label="Top 1%")
    ax.plot(df_stats_year["year"], 100 * df_stats_year["top_01"], marker="^", label="Top 0.1%")
    ax.set_title("Income concentration")
    ax.set_xlabel("Year")
    ax.set_ylabel("% of total income")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)


def plot_inequality_indices(df_stats_year, output_path, figsize=(14, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(df_stats_year["year"], df_stats_year["Gini"], marker="o", label="Gini")
    ax.plot(df_stats_year["year"], df_stats_year["Pietra"], marker="s", label="Pietra")
    ax.plot(df_stats_year["year"], df_stats_year["Kolkata"], marker="^", label="Kolkata")
    ax.plot(df_stats_year["year"], df_stats_year["Zanardi"], marker="d", label="Zanardi")
    ax.set_title("Evolution of inequality indices")
    ax.set_xlabel("Year")
    ax.set_ylabel("Index")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)


def plot_inequality_indices_grid(df_stats_year, output_path, ncols=2, figsize=(16, 10)):
    series = [
        ("Gini", "Gini Index", 1.0, "Index value"),
        ("Zanardi", "Zanardi Index", 1.0, "Index value"),
        ("Kolkata", "Kolkata Index", 100.0, "Index value (%)"),
        ("Pietra", "Pietra Index", 100.0, "Index value (%)"),
    ]
    nrows = int(np.ceil(len(series) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False, sharex=True)

    first_year = int(df_stats_year["year"].min())
    last_year = int(df_stats_year["year"].max())
    full_years = np.arange(first_year, last_year + 1)
    indexed = df_stats_year.set_index("year").reindex(full_years)

    for ax, (column, title, scale, ylabel) in zip(axes.ravel(), series):
        interpolated = indexed[column].interpolate(
            method="linear",
            limit_direction="both",
        )
        ax.plot(
            full_years,
            scale * interpolated,
            marker="o",
            markersize=4,
            linewidth=1.7,
        )
        ax.set_title(f"Evolution of the {title} - Brazil ({first_year}-{last_year})")
        ax.set_xlabel("Year")
        ax.set_ylabel(ylabel)
        ax.set_xticks(np.arange(first_year, last_year + 1, 4))
        ax.set_xticks(full_years, minor=True)
        ax.grid(True, which="major", linestyle="--", alpha=0.6)
        ax.grid(True, which="minor", axis="x", linestyle="--", alpha=0.25)

    fig.tight_layout()
    fig.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)


def plot_gini_validation(df_gini_validation, output_path, figsize=(14, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(df_gini_validation["year"], df_gini_validation["Gini"], marker="o", label="PNAD - calculated")

    if "IPEA" in df_gini_validation:
        temp = df_gini_validation.dropna(subset=["IPEA"])
        ax.plot(temp["year"], temp["IPEA"], marker="s", label="IPEA")

    if "Banco_Mundial" in df_gini_validation:
        temp = df_gini_validation.dropna(subset=["Banco_Mundial"])
        ax.plot(temp["year"], temp["Banco_Mundial"], marker="^", label="World Bank")

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
    r2 = np.nan if np.isclose(tss, 0) else float(1 - sse / tss)
    return r2, sse


def fit_gompertz_ls(income_normalized, gompertz_transform):
    x = np.asarray(income_normalized, dtype=float)
    y = np.asarray(gompertz_transform, dtype=float)
    A = float(np.log(np.log(100.0)))
    denominator = float(np.sum(x ** 2))
    if x.size < 2 or denominator <= 0:
        return np.nan
    B = float(np.sum(x * (A - y)) / denominator)
    return B if np.isfinite(B) and B > 0 else np.nan


def fit_pareto_ls(income_normalized, empirical_ccdf_percent, cutoff, F_cutoff):
    x = np.asarray(income_normalized, dtype=float)
    F = np.asarray(empirical_ccdf_percent, dtype=float)
    z = np.log(x / cutoff)
    w = np.log(F_cutoff) - np.log(F)
    denominator = float(np.sum(z ** 2))
    if x.size < 2 or denominator <= 0:
        return np.nan
    alpha = float(np.sum(z * w) / denominator)
    return alpha if np.isfinite(alpha) and alpha > 0 else np.nan


def fit_year_regime(
    df_ccdf_year,
    stats_row,
    min_body_observations=100,
    min_tail_observations=100,
    min_tail_fraction=0.005,
    cutoff_quantile_min=0.20,
    cutoff_quantile_max=0.995,
    min_curve_points=5,
):
    year = int(stats_row["year"] if "year" in stats_row.index else stats_row.name)
    n_total = int(stats_row["N_valid"] - stats_row["n_zero"])
    if n_total <= 0:
        raise ValueError(f"{year}: no positive finite income")

    normalization_mean = float(stats_row["income_sum"] / n_total)

    curve = df_ccdf_year[["x", "ccdf_pct"]].copy()
    curve = curve[
        np.isfinite(curve["x"])
        & np.isfinite(curve["ccdf_pct"])
        & (curve["x"] > 0)
        & (curve["ccdf_pct"] > 0)
    ].sort_values("x").reset_index(drop=True)

    curve["empirical_ccdf_percent"] = np.minimum(
        100.0,
        curve["ccdf_pct"] * float(stats_row["N_valid"]) / n_total,
    )
    curve["income_adj_2025_usd"] = curve["x"]
    curve["income_normalized"] = curve["x"] / normalization_mean

    F = curve["empirical_ccdf_percent"].to_numpy(float)
    transform = np.full(F.shape, np.nan, dtype=float)
    valid_transform = F > 1.0
    transform[valid_transform] = np.log(np.log(F[valid_transform]))
    curve["gompertz_transform"] = transform

    A = float(np.log(np.log(100.0)))
    candidates = []

    for row in curve.itertuples(index=False):
        cutoff = float(row.income_normalized)
        tail_fraction = float(row.empirical_ccdf_percent / 100.0)
        n_tail = int(np.rint(tail_fraction * n_total))
        n_body = n_total - n_tail
        cutoff_quantile = n_body / n_total

        if n_body < min_body_observations or n_tail < min_tail_observations:
            continue
        if tail_fraction < min_tail_fraction:
            continue
        if not (cutoff_quantile_min <= cutoff_quantile <= cutoff_quantile_max):
            continue

        body = curve[
            (curve["income_normalized"] < cutoff)
            & curve["gompertz_transform"].notna()
        ]
        tail = curve[curve["income_normalized"] >= cutoff]

        if len(body) < min_curve_points or len(tail) < min_curve_points:
            continue

        body_x = body["income_normalized"].to_numpy(float)
        body_y = body["gompertz_transform"].to_numpy(float)
        B = fit_gompertz_ls(body_x, body_y)
        if not np.isfinite(B):
            continue

        F_cutoff = float(np.exp(np.exp(A - B * cutoff)))

        tail_x = tail["income_normalized"].to_numpy(float)
        tail_F = tail["empirical_ccdf_percent"].to_numpy(float)
        alpha = fit_pareto_ls(tail_x, tail_F, cutoff, F_cutoff)
        if not np.isfinite(alpha):
            continue

        body_fitted_transform = A - B * body_x
        gompertz_r2, _ = _fit_r2(body_y, body_fitted_transform)

        tail_logF = np.log(tail_F)
        tail_fitted_logF = np.log(F_cutoff) - alpha * np.log(tail_x / cutoff)
        pareto_r2, tail_sse_logF = _fit_r2(tail_logF, tail_fitted_logF)

        body_common = curve[curve["income_normalized"] < cutoff]
        body_common_x = body_common["income_normalized"].to_numpy(float)
        body_common_logF = np.log(body_common["empirical_ccdf_percent"].to_numpy(float))
        body_fitted_logF = np.exp(A - B * body_common_x)
        body_sse_logF = float(np.sum((body_common_logF - body_fitted_logF) ** 2))

        joint_sse = body_sse_logF + tail_sse_logF
        beta = float(F_cutoff * cutoff ** alpha)

        candidates.append({
            "year": year,
            "normalization_mean": normalization_mean,
            "cutoff_normalized": cutoff,
            "cutoff_income_adj": cutoff * normalization_mean,
            "cutoff_quantile": cutoff_quantile,
            "n_total": n_total,
            "n_body": n_body,
            "n_tail": n_tail,
            "body_fraction": n_body / n_total,
            "tail_fraction": n_tail / n_total,
            "gompertz_A": A,
            "gompertz_B": B,
            "gompertz_r2": gompertz_r2,
            "pareto_alpha": alpha,
            "pareto_beta": beta,
            "pareto_r2": pareto_r2,
            "body_sse_logF": body_sse_logF,
            "tail_sse_logF": tail_sse_logF,
            "joint_sse": joint_sse,
        })

    if not candidates:
        raise ValueError(f"{year}: no admissible cutoff")

    best = min(candidates, key=lambda item: item["joint_sse"])
    cutoff = best["cutoff_normalized"]

    curve["year"] = year
    curve["regime"] = np.where(
        curve["income_normalized"] < cutoff,
        "gompertz_body",
        "pareto_tail",
    )
    curve["cutoff_normalized"] = cutoff
    curve["cutoff_income_adj"] = best["cutoff_income_adj"]

    body_mask = curve["regime"] == "gompertz_body"
    tail_mask = curve["regime"] == "pareto_tail"

    curve["gompertz_fitted_transform"] = np.where(
        body_mask,
        A - best["gompertz_B"] * curve["income_normalized"],
        np.nan,
    )
    curve["pareto_fitted_ccdf_percent"] = np.where(
        tail_mask,
        best["pareto_beta"] * curve["income_normalized"] ** (-best["pareto_alpha"]),
        np.nan,
    )

    curve = curve[[
        "year",
        "income_normalized",
        "income_adj_2025_usd",
        "empirical_ccdf_percent",
        "gompertz_transform",
        "regime",
        "cutoff_normalized",
        "cutoff_income_adj",
        "gompertz_fitted_transform",
        "pareto_fitted_ccdf_percent",
    ]]
    return best, curve


def build_regime_datasets(df_ccdf, df_stats_year):
    fits = []
    curves = []
    stats_index = df_stats_year.set_index("year")

    for year in sorted(df_ccdf["year"].unique()):
        fit, curve = fit_year_regime(
            df_ccdf[df_ccdf["year"] == year],
            stats_index.loc[year],
        )
        fits.append(fit)
        curves.append(curve)

    return (
        pd.DataFrame(fits).sort_values("year").reset_index(drop=True),
        pd.concat(curves, ignore_index=True)
        .sort_values(["year", "income_normalized"])
        .reset_index(drop=True),
    )


def plot_gompertz_regime_fits(df_regime_curves, df_regime_fits, years,
                              output_path, ncols=4, figsize=None):
    fits_index = df_regime_fits.set_index("year")
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize)

    for i, year in enumerate(years):
        temp = df_regime_curves[
            (df_regime_curves["year"] == year)
            & (df_regime_curves["regime"] == "gompertz_body")
        ]
        ax = axes.ravel()[i]
        r2 = float(fits_index.loc[year, "gompertz_r2"])
        ax.scatter(temp["income_normalized"], temp["gompertz_transform"], s=12, alpha=0.7)
        ax.plot(temp["income_normalized"], temp["gompertz_fitted_transform"], linewidth=1.8)
        cutoff = float(temp["cutoff_normalized"].iloc[0])
        ax.axvline(cutoff, linestyle="--", linewidth=1.0)
        ax.set_title(fr"{year} - $R^2={r2:.3f}$")
        ax.set_xlabel("Normalized income")
        ax.set_ylabel(r"$\ln[\ln(F)]$")
        ax.grid(True, alpha=0.3)

    finish_grid(
        fig, axes, len(years),
        "Gompertz body - annual least-squares fits",
        output_path,
    )


def plot_pareto_regime_fits(df_regime_curves, df_regime_fits, years,
                            output_path, ncols=4, figsize=None):
    fits_index = df_regime_fits.set_index("year")
    fig, axes = make_grid(len(years), cols=ncols, figsize=figsize)

    for i, year in enumerate(years):
        temp = df_regime_curves[
            (df_regime_curves["year"] == year)
            & (df_regime_curves["regime"] == "pareto_tail")
        ]
        ax = axes.ravel()[i]
        alpha = float(fits_index.loc[year, "pareto_alpha"])
        r2 = float(fits_index.loc[year, "pareto_r2"])

        ax.scatter(temp["income_normalized"], temp["empirical_ccdf_percent"], s=12, alpha=0.7)
        ax.plot(temp["income_normalized"], temp["pareto_fitted_ccdf_percent"], linewidth=1.8)
        cutoff = float(temp["cutoff_normalized"].iloc[0])
        ax.axvline(cutoff, linestyle="--", linewidth=1.0)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(fr"{year} - $\alpha={alpha:.3f}$, $R^2={r2:.3f}$")
        ax.set_xlabel("Normalized income")
        ax.set_ylabel("CCDF (%)")
        ax.grid(True, alpha=0.3)

    finish_grid(
        fig, axes, len(years),
        "Pareto tail - annual least-squares fits",
        output_path,
    )


def save_table(df, filename):
    path = TABLES_ANALYSIS_PATH / filename
    df.to_csv(path, index=False)
    return path


def run_analysis():
    TABLES_ANALYSIS_PATH.mkdir(parents=True, exist_ok=True)
    FIGURES_ANALYSIS_PATH.mkdir(parents=True, exist_ok=True)

    results = pipeline()
    years = results["years"]
    files_by_year = results["files_by_year"]
    df_stats_year = results["df_stats_year"]
    df_ccdf = results["df_ccdf"]
    df_bins = results["df_bins"]
    df_lorenz = results["df_lorenz"]

    df_histograms = build_histogram_dataset(files_by_year, years, bins=100)
    df_bins_preview = bins_table(df_bins, n=20)
    df_gini_validation = build_gini_validation(df_stats_year)
    df_regime_fits, df_regime_curves = build_regime_datasets(df_ccdf, df_stats_year)

    tables = {
        "trusted_analysis_statistics_annual.csv": df_stats_year,
        "trusted_analysis_ccdf.csv": df_ccdf,
        "trusted_analysis_geometric_bins.csv": df_bins,
        "trusted_analysis_geometric_bins_preview.csv": df_bins_preview,
        "trusted_analysis_lorenz.csv": df_lorenz,
        "trusted_analysis_histograms.csv": df_histograms,
        "trusted_analysis_gini_validation_annual.csv": df_gini_validation,
        "trusted_analysis_regime_fits_annual.csv": df_regime_fits,
        "trusted_analysis_regime_curves.csv": df_regime_curves,
    }
    for filename, frame in tables.items():
        save_table(frame, filename)

    plot_histograms(
        df_histograms, years,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_histograms.svg",
        ncols=4,
    )
    plot_income_mean_median(
        df_stats_year,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_income_mean_median.svg",
    )
    plot_ccdf_loglog(
        df_ccdf, years,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_ccdf_loglog.svg",
        ncols=4,
    )
    plot_ccdf_lnln(
        df_ccdf, years,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_ccdf_lnln.svg",
        ncols=4,
    )
    plot_lorenz_indices_pretty(
        df_lorenz, df_stats_year, years,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_lorenz_geometry.svg",
        ncols=3,
    )
    plot_top_shares(
        df_stats_year,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_top_income_shares.svg",
    )
    plot_inequality_indices(
        df_stats_year,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_inequality_indices.svg",
    )
    plot_inequality_indices_grid(
        df_stats_year,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_inequality_indices_2x2.svg",
    )
    plot_gini_validation(
        df_gini_validation,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_gini_validation.svg",
    )
    plot_gompertz_regime_fits(
        df_regime_curves, df_regime_fits, years,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_regime_fits_gompertz.svg",
        ncols=4,
        figsize=(20, 60),
    )
    plot_pareto_regime_fits(
        df_regime_curves, df_regime_fits, years,
        FIGURES_ANALYSIS_PATH / "trusted_analysis_regime_fits_pareto.svg",
        ncols=4,
        figsize=(20, 60),
    )

    return {
        **results,
        "df_histograms": df_histograms,
        "df_gini_validation": df_gini_validation,
        "df_regime_fits": df_regime_fits,
        "df_regime_curves": df_regime_curves,
    }


def main():
    results = run_analysis()
    print(f"Processed years: {len(results['years'])}")
    print(results["df_stats_year"].to_string(index=False))


if __name__ == "__main__":
    main()
