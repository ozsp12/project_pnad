from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_between(text, start_marker, end_marker, replacement):
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one occurrence, found {text.count(old)}: {old[:80]!r}")
    return text.replace(old, new, 1)


# 1, 3, 5: Stage 03 owns Pareto support policy and does not interpolate missing years.
path = ROOT / "src/stage_03_pnad_analysis.py"
text = path.read_text(encoding="utf-8")

text = replace_between(
    text,
    "def plot_inequality_indices_grid",
    "def plot_gini_validation",
    '''def plot_inequality_indices_grid(df, output_path, ncols=2, figsize=(16, 10)):
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
    plt.close(fig)''',
)

text = replace_between(
    text,
    "def fit_year_regime",
    "def build_regime_datasets",
    '''def fit_year_regime(year, income_normalized, normalization_mean):
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
    return fit, curve''',
)

text = replace_between(
    text,
    "def build_regime_datasets",
    "def plot_gompertz_regime_fits",
    '''def build_regime_datasets(files_by_year, df_metadata):
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
    )''',
)

text = replace_between(
    text,
    "def plot_pareto_regime_fits",
    "def save_table",
    '''def plot_pareto_regime_fits(curves, fits, years, output_path, ncols=4, figsize=None):
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
            fr"{year} - $\alpha_{{MLE}}={f['pareto_alpha_mle']:.3f}$, $R^2_{{LS}}={f['pareto_ls_r2']:.3f}$"
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
    )''',
)

text = replace_between(
    text,
    "def build_diagnostics_annual",
    "def _description",
    '''def build_diagnostics_annual(layer: str) -> pd.DataFrame:
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

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)''',
)

path.write_text(text, encoding="utf-8")


# 4: Stage 05 breaks every annual line at missing years and handles unsupported Pareto years.
path = ROOT / "src/stage_05_publication.py"
text = path.read_text(encoding="utf-8")

text = replace_between(
    text,
    "def line_figure",
    "def plot_histograms",
    '''def annual_plot_frame(df):
    """Return a plotting-only annual grid with NaN at unobserved years."""
    data = df.copy()
    data["year"] = pd.to_numeric(data["year"], errors="coerce")
    data = data.dropna(subset=["year"])
    data["year"] = data["year"].astype(int)
    if data["year"].duplicated().any():
        raise ValueError("Annual plotting data must contain unique years.")
    full_years = pd.Index(range(START_YEAR, END_YEAR + 1), name="year")
    return data.set_index("year").reindex(full_years).reset_index()


def line_figure(df, stem, series, ylabel, scale=1.0):
    data = annual_plot_frame(df)
    fig, ax = plt.subplots(figsize=SINGLE_SIZE)
    for index, (column, label) in enumerate(series):
        ax.plot(
            data.year,
            scale * data[column],
            label=label,
            **series_style(index),
        )
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    style(ax)
    if len(series) > 1:
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, 1.13),
            ncol=min(4, len(series)),
            handlelength=2.5,
        )
        save(fig, stem, top=0.90)
    else:
        save(fig, stem)''',
)

text = replace_between(
    text,
    "def plot_model_families",
    "def plot_income_stats",
    '''def plot_model_families(curves, annual, years):
    fit = annual.set_index("year")

    def exp(ax, year):
        row = fit.loc[year]
        data = curves[
            (curves.year == year)
            & (curves.income_normalized <= row.gompertz_x_gmax)
            & (curves.empirical_ccdf_percent > 0)
        ]
        x = data.income_normalized.to_numpy(float)
        ax.scatter(x, np.log(data.empirical_ccdf_percent), label="Empirical", **scatter_style())
        ax.plot(
            x,
            row.exponential_intercept - row.exponential_alpha * x,
            color="0.05",
            lw=1.15,
            label="Exponential fit",
        )
        style(ax)

    def gom(ax, year):
        row = fit.loc[year]
        data = curves[
            (curves.year == year)
            & (curves.income_normalized <= row.gompertz_x_gmax)
            & curves.gompertz_transform.notna()
        ]
        x = data.income_normalized.to_numpy(float)
        ax.scatter(
            x,
            data.gompertz_transform,
            label="Empirical transform",
            **scatter_style(),
        )
        ax.plot(
            x,
            row.gompertz_A - row.gompertz_B * x,
            color="0.05",
            lw=1.20,
            label="Fixed-A Gompertz",
        )
        ax.plot(
            x,
            row.gompertz_boundary_A_free - row.gompertz_boundary_B_free * x,
            color="0.48",
            ls="--",
            lw=1.05,
            label="Free-intercept LSF",
        )
        style(ax)

    family(
        years,
        "exponential_fit",
        exp,
        "Normalized income",
        r"$\ln F(x)$",
        legend=True,
        ncol=2,
    )
    family(
        years,
        "gompertz_ls_fit",
        gom,
        "Normalized income",
        r"$\ln[\ln F(x)]$",
        legend=True,
        ncol=3,
    )

    for method in ("ls", "mle"):
        def draw(ax, year, method=method):
            row = fit.loc[year]
            supported = bool(row.get("pareto_supported", True))
            if not supported:
                annotation(ax, "Pareto tail not supported", x=0.20, y=0.48)
                style(ax)
                return

            column = f"pareto_fitted_ccdf_percent_{method}"
            xmin = (
                min(row.transition_x_t, row.pareto_x_pmin)
                if method == "ls"
                else row.transition_x_t
            )
            data = curves[
                (curves.year == year)
                & (curves.income_normalized >= xmin)
                & (curves.empirical_ccdf_percent > 0)
            ]
            ax.scatter(
                data.income_normalized,
                data.empirical_ccdf_percent,
                label="Empirical CCDF",
                **scatter_style(),
            )
            ax.plot(
                data.income_normalized,
                data[column],
                color="0.05",
                ls="--" if method == "ls" else "-",
                lw=1.20,
                label="Pareto LSF" if method == "ls" else "Pareto MLE",
            )
            ax.axvline(
                float(row.transition_x_t),
                color="0.52",
                ls=":",
                lw=0.9,
                label=r"$x_t$",
            )
            ax.set_xscale("log")
            ax.set_yscale("log")
            style(ax, True)

        family(
            years,
            f"pareto_{method}_fit",
            draw,
            "Normalized income",
            "CCDF (%)",
            legend=True,
            ncol=3,
        )''',
)

old = '''    fig, axes = plt.subplots(2, 2, figsize=(7, 6.2), sharex=True)
    for ax, (column, scale) in zip(
        axes.ravel(),
        [("Gini", 1), ("Zanardi", 1), ("Kolkata", 100), ("Pietra", 100)],
    ):
        ax.plot(stats.year, scale * stats[column], **series_style(0))
        ax.set_title(column, fontweight="semibold")
        style(ax)
    for ax in axes[-1]:
        ax.set_xlabel("Year")
    save(fig, "inequality_indices_grid")

    # Reindex only the plotting copy. Missing survey/reference years remain NaN,
    # which makes Matplotlib break the lines instead of visually interpolating
    # across years with no observation. The underlying Stage-03 tables are unchanged.
    full_years = pd.Index(range(START_YEAR, END_YEAR + 1), name="year")
    gini_validation = (
        stats.set_index("year")
        .reindex(full_years)
        .reset_index()
    )
'''
new = '''    temporal_stats = annual_plot_frame(stats)
    fig, axes = plt.subplots(2, 2, figsize=(7, 6.2), sharex=True)
    for ax, (column, scale) in zip(
        axes.ravel(),
        [("Gini", 1), ("Zanardi", 1), ("Kolkata", 100), ("Pietra", 100)],
    ):
        ax.plot(temporal_stats.year, scale * temporal_stats[column], **series_style(0))
        ax.set_title(column, fontweight="semibold")
        style(ax)
    for ax in axes[-1]:
        ax.set_xlabel("Year")
    save(fig, "inequality_indices_grid")

    gini_validation = temporal_stats
'''
text = replace_once(text, old, new)

text = replace_between(
    text,
    "def validate_tables",
    "def build_paper_tables",
    '''def validate_tables(g, p, e):
    merged = g[["year", "gompertz_income_share_pct"]].merge(
        p[["year", "pareto_income_share_pct"]], on="year", validate="one_to_one"
    )
    complete = merged.dropna(
        subset=["gompertz_income_share_pct", "pareto_income_share_pct"]
    )
    if not complete.empty and not np.allclose(
        complete.gompertz_income_share_pct + complete.pareto_income_share_pct,
        100.0,
        atol=1e-8,
    ):
        raise AssertionError("Supported Gompertz and Pareto income shares must sum to 100%")
    if any(frame.year.duplicated().any() for frame in (g, p, e)):
        raise AssertionError("Annual paper tables must have unique years")''',
)

path.write_text(text, encoding="utf-8")


# 1: CI invokes exactly the canonical Stage-03 entry point.
path = ROOT / ".github/workflows/run_analysis.yml"
text = path.read_text(encoding="utf-8")
text = replace_between(
    text,
    "      - name: Run complete PNAD Stage 03",
    "      - name: Commit analytical assets",
    '''      - name: Run complete PNAD Stage 03
        env:
          MPLBACKEND: Agg
        run: python src/stage_03_pnad_analysis.py''',
)
path.write_text(text, encoding="utf-8")


# 2: Document the exceptional p99 rule without using external validation series as calibration.
path = ROOT / "src/stage_02_build_trusted_pnad.py"
text = path.read_text(encoding="utf-8")
old = '''For the 1985 and 1990 surveys, the trusted layer applies an additional
conservative upper-tail rule: observations strictly above the empirical 99th
percentile of the structurally valid annual income distribution are removed.
The effective cutoff is therefore the minimum between the annual log-MAD
cutoff and the empirical p99 cutoff. The refined datasets remain unchanged,
and the exceptional cutoff is recorded explicitly in the audit table.
'''
new = '''For the 1985 and 1990 surveys, the trusted layer applies an additional
upper-tail rule: observations strictly above the empirical 99th percentile of
the structurally valid annual income distribution are removed. The effective
cutoff is therefore the minimum between the annual log-MAD cutoff and the
empirical p99 cutoff. This exceptional rule is defined from within-year tail
behavior and leverage only; external Gini reference series are not used to
select, tune, or validate the cutoff during construction. The refined datasets
remain unchanged, and the exceptional cutoff is recorded explicitly in the
audit table.
'''
text = replace_once(text, old, new)
path.write_text(text, encoding="utf-8")


path = ROOT / "README.md"
text = path.read_text(encoding="utf-8")
marker = "## Stage 03 methodology and analytical layers\n"
insert = '''## Trusted upper-tail treatment\n\nStage 02 uses the annual log-MAD upper-tail rule after structural cleaning. For 1985 and 1990 only, the trusted layer additionally applies the empirical 99th-percentile cutoff, with the effective threshold defined as `min(log-MAD, p99)`. The exception is based exclusively on within-year tail behavior and leverage; IPEA and World Bank Gini series are not used to choose or tune the cutoff. The untrimmed observations remain available in the refined layer. If the resulting trusted tail does not retain the canonical minimum number of Pareto bins, Stage 03 records the Pareto regime as unsupported rather than relaxing the fitting criterion.\n\n'''
if insert not in text:
    text = text.replace(marker, insert + marker, 1)
path.write_text(text, encoding="utf-8")

path = ROOT / "src/README.md"
text = path.read_text(encoding="utf-8")
marker = "## Stage 03\n"
insert = '''## Stage 02 upper-tail policy\n\nThe trusted layer applies the canonical log-MAD rule after structural cleaning. In 1985 and 1990 the effective upper cutoff is `min(log-MAD, p99)`. This exception is defined solely from the within-year income distribution and is not calibrated to IPEA or World Bank inequality series. Refined data remain unchanged.\n\n'''
if insert not in text:
    text = text.replace(marker, insert + marker, 1)
path.write_text(text, encoding="utf-8")


# 6: Regression tests for p99 behavior, unsupported Pareto tails, and missing years.
test_path = ROOT / "tests/test_methodology_integrity.py"
test_path.write_text('''from pathlib import Path\nimport inspect\n\nimport numpy as np\nimport pandas as pd\nimport pytest\n\nfrom src import stage_02_build_trusted_pnad as stage_02\nfrom src import stage_03_pnad_analysis as stage_03\nfrom src import stage_05_publication as stage_05\n\n\ndef _frame(year, values):\n    return pd.DataFrame({"ano": [year] * len(values), "renda": np.asarray(values, float)})\n\n\ndef test_p99_exception_applies_only_to_configured_years():\n    values = np.arange(1.0, 101.0)\n    trusted, audit, _ = stage_02.trim_refined_year(_frame(1985, values), 1985, threshold=50.0)\n    assert audit["cutoff_rule"] == "min_log_mad_p99_exception"\n    assert audit["p99_exception_cutoff"] == pytest.approx(np.quantile(values, 0.99))\n    assert audit["n_statistical_outlier"] == 1\n    assert trusted["renda"].max() < 100.0\n\n    trusted_regular, regular, _ = stage_02.trim_refined_year(\n        _frame(1986, values), 1986, threshold=50.0\n    )\n    assert regular["cutoff_rule"] == "log_mad"\n    assert np.isnan(regular["p99_exception_cutoff"])\n    assert regular["n_statistical_outlier"] == 0\n    assert trusted_regular["renda"].max() == pytest.approx(100.0)\n\n\ndef test_p99_ties_at_cutoff_are_retained():\n    values = np.array(list(range(1, 99)) + [100, 100], dtype=float)\n    trusted, audit, _ = stage_02.trim_refined_year(_frame(1990, values), 1990, threshold=50.0)\n    assert audit["p99_exception_cutoff"] == pytest.approx(100.0)\n    assert audit["n_statistical_outlier"] == 0\n    assert int((trusted["renda"] == 100.0).sum()) == 2\n\n\ndef test_stage03_marks_insufficient_pareto_tail_as_unsupported(monkeypatch):\n    gompertz = {\n        "gompertz_A": stage_03.GOMPERTZ_A_THEORY,\n        "gompertz_B": 0.5,\n        "gompertz_r2": 0.99,\n        "gompertz_sse": 0.01,\n        "gompertz_x_gmax": 2.0,\n        "gompertz_point_n": 10,\n        "gompertz_selection_status": "test",\n        "gompertz_boundary_A_free": 1.52,\n        "gompertz_boundary_B_free": 0.5,\n        "gompertz_boundary_r2_free": 0.99,\n    }\n    monkeypatch.setattr(stage_03, "select_gompertz_region", lambda curve: gompertz)\n\n    def _raise(*args, **kwargs):\n        raise ValueError("Insufficient Pareto-tail points.")\n\n    monkeypatch.setattr(stage_03, "select_pareto_region", _raise)\n    fit, curve = stage_03.fit_year_regime(1990, np.geomspace(0.1, 3.0, 100), 1.0)\n\n    assert fit["pareto_selection_status"] == "unsupported_insufficient_tail_points"\n    assert np.isnan(fit["transition_x_t"])\n    assert np.isnan(fit["pareto_alpha_mle"])\n    assert curve["pareto_fitted_ccdf_percent_mle"].isna().all()\n    assert set(curve["regime"]) == {"gompertz_body"}\n\n\ndef test_stage03_inequality_grid_does_not_interpolate_missing_years():\n    source = inspect.getsource(stage_03.plot_inequality_indices_grid)\n    assert ".interpolate(" not in source\n    assert ".reindex(" in source\n\n\ndef test_stage05_annual_plot_frame_preserves_missing_years_as_nan():\n    source = pd.DataFrame({"year": [1985, 1987], "Gini": [0.55, 0.57]})\n    plotted = stage_05.annual_plot_frame(source).set_index("year")\n    assert plotted.loc[1985, "Gini"] == pytest.approx(0.55)\n    assert np.isnan(plotted.loc[1986, "Gini"])\n    assert plotted.loc[1987, "Gini"] == pytest.approx(0.57)\n\n\ndef test_analysis_workflow_contains_no_runtime_pareto_monkeypatch():\n    workflow = Path(".github/workflows/run_analysis.yml").read_text(encoding="utf-8")\n    assert "MIN_PARETO_POINTS = 4" not in workflow\n    assert "fit_year_regime_with_p99_fallback" not in workflow\n    assert "python src/stage_03_pnad_analysis.py" in workflow\n''', encoding="utf-8")

print("Methodology refactor applied.")
