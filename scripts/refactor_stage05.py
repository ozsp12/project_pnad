from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def cut_before_main(source):
    i = source.rfind("\ndef main():")
    if i < 0:
        raise RuntimeError("main() not found")
    return source[:i].rstrip() + "\n"


def node_names(node):
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    out = []
    for target in targets:
        if isinstance(target, ast.Name):
            out.append(target.id)
    return out


def extract(source, assignments, functions):
    tree = ast.parse(source)
    blocks = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and set(node_names(node)) & assignments:
            blocks.append(ast.get_source_segment(source, node))
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            blocks.append(ast.get_source_segment(source, node))
    return "\n\n".join(x for x in blocks if x)


publication = SRC / "stage_05_publication.py"
figures = SRC / "stage_05_moura_ribeiro.py"
tables = SRC / "stage_05_tables.py"
base = cut_before_main(figures.read_text(encoding="utf-8"))
tables_source = tables.read_text(encoding="utf-8")
base = base.replace(
    '"""Publication visual layer for trusted PNAD outputs.',
    '"""Canonical Stage-05 publication layer for trusted PNAD outputs.',
    1,
)

assignments = {
    "TABLES_TRUSTED", "TABLES_PAPER", "GDP_PATH",
    "GOMPERTZ_OUT", "PARETO_OUT", "ECONOMIC_OUT", "METADATA_OUT",
    "CANONICAL_TABLES", "TABLE_DESCRIPTIONS", "COLUMN_DESCRIPTIONS",
}
functions = {
    "_year_filter", "load_annual_fits", "build_gompertz_table",
    "build_pareto_table", "_column_metadata", "build_metadata_table",
    "validate_tables", "_clean_paper_csvs",
}
features = extract(tables_source, assignments, functions)

paper_features = '''\n\nPAPER_ECONOMIC_COLUMNS = [\n    "year", "gdp_growth_pct", "income_observation_n",\n    "income_mean_2025_usd", "income_median_2025_usd", "income_std_2025_usd",\n    "gini_pnad", "pietra_pnad", "kolkata_pnad", "zanardi_pnad",\n    "gini_ipea", "gini_world_bank",\n    "p90_p99_population_n", "p90_p99_income_share_pct",\n    "p90_p99_mean_income_2025_usd", "p90_p99_median_income_2025_usd", "p90_p99_std_income_2025_usd",\n    "p99_p999_population_n", "p99_p999_income_share_pct",\n    "p99_p999_mean_income_2025_usd", "p99_p999_median_income_2025_usd", "p99_p999_std_income_2025_usd",\n    "p999_p100_population_n", "p999_p100_income_share_pct",\n    "p999_p100_mean_income_2025_usd", "p999_p100_median_income_2025_usd", "p999_p100_std_income_2025_usd",\n]\n\n\ndef build_economic_table(stats):\n    """Format persisted Stage-03 statistics as the paper economic table."""\n    data = _year_filter(stats)\n    gdp = _year_filter(pd.read_csv(GDP_PATH))[["year", "gdp_growth_pct"]]\n    data = data.merge(gdp, on="year", how="left", validate="one_to_one")\n    data = data.rename(columns={\n        "Gini": "gini_pnad",\n        "Pietra": "pietra_pnad",\n        "Kolkata": "kolkata_pnad",\n        "Zanardi": "zanardi_pnad",\n        "IPEA": "gini_ipea",\n        "Banco_Mundial": "gini_world_bank",\n    })\n    for column in PAPER_ECONOMIC_COLUMNS:\n        if column not in data:\n            data[column] = np.nan\n    return data[PAPER_ECONOMIC_COLUMNS].sort_values("year").reset_index(drop=True)\n\n\ndef build_paper_tables():\n    stats = _year_filter(pd.read_csv(TABLES_TRUSTED / "statistics_annual.csv"))\n    annual = load_annual_fits()\n    economic = build_economic_table(stats)\n    gompertz = build_gompertz_table(annual)\n    pareto = build_pareto_table(annual)\n    validate_tables(gompertz, pareto, economic)\n    metadata_table = build_metadata_table({\n        GOMPERTZ_OUT.name: gompertz,\n        PARETO_OUT.name: pareto,\n        ECONOMIC_OUT.name: economic,\n    })\n    _clean_paper_csvs()\n    outputs = (\n        (GOMPERTZ_OUT, gompertz),\n        (PARETO_OUT, pareto),\n        (ECONOMIC_OUT, economic),\n        (METADATA_OUT, metadata_table),\n    )\n    for path, frame in outputs:\n        frame.to_csv(path, index=False)\n    generated = {path.name for path in TABLES_PAPER.glob("*.csv")}\n    if generated != CANONICAL_TABLES:\n        raise AssertionError(f"Unexpected paper tables: {sorted(generated)}")\n    return {path.name: frame for path, frame in outputs}\n'''

entry = '''\n\ndef main():\n    """Generate publication figures and tables from persisted Stage-03 results."""\n    PAPER_TABLES.mkdir(parents=True, exist_ok=True)\n    clean_figures()\n    stats, lorenz, annual, curves, meta = load_inputs()\n    years = years_of(annual["year"].dropna())\n    exponential = annual[[\n        "year", "exponential_intercept", "exponential_alpha",\n        "exponential_r2", "gompertz_x_gmax",\n    ]].rename(columns={\n        "exponential_intercept": "intercept",\n        "exponential_alpha": "alpha",\n        "exponential_r2": "r2",\n        "gompertz_x_gmax": "xg",\n    })\n    shares = annual[["year", "gompertz_income_share_pct", "pareto_income_share_pct"]].copy()\n\n    plot_histograms(years, meta)\n    plot_income_statistics(stats, years, meta)\n    plot_ccdf(curves, annual, years)\n    plot_lorenz(lorenz, stats, years)\n    line_figure(stats, "gini", [("Gini", "Gini")], "Gini coefficient")\n    plot_exponential(curves, exponential, years)\n    plot_gompertz(curves, annual, years)\n    plot_pareto(curves, annual, years, "ls")\n    plot_pareto(curves, annual, years, "mle")\n    line_figure(stats, "top_income_shares", [("top_10", "Top 10%"), ("top_1", "Top 1%"), ("top_01", "Top 0.1%")], "Share of total income (%)", 100)\n    exclusive = stats.copy()\n    exclusive["p90_p99"] = exclusive.top_10 - exclusive.top_1\n    exclusive["p99_p999"] = exclusive.top_1 - exclusive.top_01\n    exclusive["p999_p100"] = exclusive.top_01\n    line_figure(exclusive, "top_income_exclusive_shares", [("p90_p99", "90-99%"), ("p99_p999", "99-99.9%"), ("p999_p100", "99.9-100%")], "Share of total income (%)", 100)\n    plot_top_combined(stats)\n    line_figure(stats, "inequality_indices", [("Gini", "Gini"), ("Pietra", "Pietra"), ("Kolkata", "Kolkata"), ("Zanardi", "Zanardi")], "Inequality index")\n    plot_inequality_grid(stats)\n    plot_gini_validation(stats)\n    plot_pareto_share(shares)\n    plot_gdp()\n    generated = build_paper_tables()\n    print(f"Stage 05 publication assets generated for {len(years)} survey years.")\n    return generated\n\n\nif __name__ == "__main__":\n    main()\n'''

publication.write_text(base.rstrip() + "\n\n# --- Paper-table formatting features ---\n\n" + features + paper_features + entry, encoding="utf-8")
figures.unlink()
tables.unlink()
