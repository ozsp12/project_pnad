"""Canonical Stage-05 publication entry point.

Stage 05 consumes scientific results already produced by Stage 03. It creates
paper figures and consolidates the paper-facing tables; it does not estimate
bootstrap or likelihood uncertainties itself.
"""

from __future__ import annotations

try:  # package import used by tests
    from . import stage_05_moura_ribeiro as figures
    from . import stage_05_tables as tables
except ImportError:  # direct execution: python src/stage_05_publication.py
    import stage_05_moura_ribeiro as figures
    import stage_05_tables as tables


def main():
    figures.PAPER_TABLES.mkdir(parents=True, exist_ok=True)
    figures.clean_figures()
    stats, lorenz, annual, curves, meta = figures.load_inputs()
    years = figures.years_of(annual["year"].dropna())

    exponential = annual[
        ["year", "exponential_intercept", "exponential_alpha", "exponential_r2", "gompertz_x_gmax"]
    ].rename(
        columns={
            "exponential_intercept": "intercept",
            "exponential_alpha": "alpha",
            "exponential_r2": "r2",
            "gompertz_x_gmax": "xg",
        }
    )
    shares = annual[
        ["year", "gompertz_income_share_pct", "pareto_income_share_pct"]
    ].copy()

    figures.plot_histograms(years, meta)
    figures.plot_income_statistics(stats, years, meta)
    figures.plot_ccdf(curves, annual, years)
    figures.plot_lorenz(lorenz, stats, years)
    figures.line_figure(stats, "gini", [("Gini", "Gini")], "Gini coefficient")
    figures.plot_exponential(curves, exponential, years)
    figures.plot_gompertz(curves, annual, annual, years)
    figures.plot_pareto(curves, annual, annual, years, "ls")
    figures.plot_pareto(curves, annual, annual, years, "mle")
    figures.line_figure(
        stats,
        "top_income_shares",
        [("top_10", "Top 10%"), ("top_1", "Top 1%"), ("top_01", "Top 0.1%")],
        "Share of total income (%)",
        100,
    )
    exclusive = stats.copy()
    exclusive["p90_p99"] = exclusive.top_10 - exclusive.top_1
    exclusive["p99_p999"] = exclusive.top_1 - exclusive.top_01
    exclusive["p999_p100"] = exclusive.top_01
    figures.line_figure(
        exclusive,
        "top_income_exclusive_shares",
        [("p90_p99", "90-99%"), ("p99_p999", "99-99.9%"), ("p999_p100", "99.9-100%")],
        "Share of total income (%)",
        100,
    )
    figures.plot_top_combined(stats)
    figures.line_figure(
        stats,
        "inequality_indices",
        [("Gini", "Gini"), ("Pietra", "Pietra"), ("Kolkata", "Kolkata"), ("Zanardi", "Zanardi")],
        "Inequality index",
    )
    figures.plot_inequality_grid(stats)
    figures.plot_gini_validation(stats)
    figures.plot_pareto_share(shares)
    figures.plot_gdp()

    generated = tables.main()
    print(
        f"Stage 05 publication assets generated for {len(years)} survey years "
        "from persisted Stage-03 scientific results."
    )
    return generated


if __name__ == "__main__":
    main()
