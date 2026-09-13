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


def extract_features(source):
    tree = ast.parse(source)
    blocks = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            blocks.append(ast.get_source_segment(source, node))
        elif isinstance(node, ast.FunctionDef) and node.name != "main":
            blocks.append(ast.get_source_segment(source, node))
    return "\n\n".join(x for x in blocks if x)


analysis_path = SRC / "stage_03_pnad_analysis.py"
diagnostics_path = SRC / "stage_03_moura_ribeiro_evidence.py"
base = cut_before_main(analysis_path.read_text(encoding="utf-8"))
diagnostics = diagnostics_path.read_text(encoding="utf-8")
base = base.replace(
    "from pathlib import Path\nimport re\n",
    "from pathlib import Path\nimport argparse\nimport os\nimport re\n",
    1,
)

helper = '''\n\ndef _band_statistics(values, total, prefix):\n    values = np.asarray(values, float)\n    if values.size == 0:\n        return {\n            f"{prefix}_population_n": 0,\n            f"{prefix}_income_share_pct": 0.0,\n            f"{prefix}_mean_income_2025_usd": np.nan,\n            f"{prefix}_median_income_2025_usd": np.nan,\n            f"{prefix}_std_income_2025_usd": np.nan,\n        }\n    return {\n        f"{prefix}_population_n": int(values.size),\n        f"{prefix}_income_share_pct": 100.0 * float(values.sum()) / total,\n        f"{prefix}_mean_income_2025_usd": float(values.mean()),\n        f"{prefix}_median_income_2025_usd": float(np.median(values)),\n        f"{prefix}_std_income_2025_usd": float(np.std(values, ddof=1)) if values.size > 1 else np.nan,\n    }\n\n\ndef compute_exclusive_income_statistics(values):\n    """Compute positive-income and exclusive top-band summaries in Stage 03."""\n    values = np.sort(np.asarray(values, float))\n    values = values[np.isfinite(values) & (values > 0)]\n    if values.size == 0:\n        raise ValueError("Positive-income summary requires at least one observation.")\n    total = float(values.sum())\n    n = int(values.size)\n    i90, i99, i999 = int(0.90 * n), int(0.99 * n), int(0.999 * n)\n    out = {\n        "income_observation_n": n,\n        "income_mean_2025_usd": float(values.mean()),\n        "income_median_2025_usd": float(np.median(values)),\n        "income_std_2025_usd": float(np.std(values, ddof=1)) if n > 1 else np.nan,\n    }\n    out.update(_band_statistics(values[i90:i99], total, "p90_p99"))\n    out.update(_band_statistics(values[i99:i999], total, "p99_p999"))\n    out.update(_band_statistics(values[i999:], total, "p999_p100"))\n    return out\n'''
marker = "\ndef make_grid("
if marker not in base:
    raise RuntimeError("make_grid marker not found")
base = base.replace(marker, helper + "\n" + marker, 1)
old = "    }\n    return stats_record, ccdf_records, bins_records, lorenz_records"
new = "    }\n    stats_record.update(compute_exclusive_income_statistics(positive_adjusted))\n    return stats_record, ccdf_records, bins_records, lorenz_records"
if old not in base:
    raise RuntimeError("stats return marker not found")
base = base.replace(old, new, 1)

metadata_updates = '''\n\nCOLUMN_DESCRIPTIONS.update({\n    "income_observation_n": "Number of strictly positive income observations used in annual publication summaries.",\n    "income_mean_2025_usd": "Arithmetic mean of strictly positive annual income in constant 2025 US$.",\n    "income_median_2025_usd": "Median of strictly positive annual income in constant 2025 US$.",\n    "income_std_2025_usd": "Sample standard deviation of strictly positive annual income in constant 2025 US$.",\n})\nfor _prefix, _label in (("p90_p99", "90th to 99th"), ("p99_p999", "99th to 99.9th"), ("p999_p100", "99.9th to 100th")):\n    COLUMN_DESCRIPTIONS[f"{_prefix}_population_n"] = f"Number of positive-income observations in the {_label} percentile-rank band."\n    COLUMN_DESCRIPTIONS[f"{_prefix}_income_share_pct"] = f"Percentage of total positive income received in the {_label} percentile-rank band."\n    COLUMN_DESCRIPTIONS[f"{_prefix}_mean_income_2025_usd"] = f"Mean income in the {_label} percentile-rank band in constant 2025 US$."\n    COLUMN_DESCRIPTIONS[f"{_prefix}_median_income_2025_usd"] = f"Median income in the {_label} percentile-rank band in constant 2025 US$."\n    COLUMN_DESCRIPTIONS[f"{_prefix}_std_income_2025_usd"] = f"Income standard deviation in the {_label} percentile-rank band in constant 2025 US$."\n    COLUMN_UNITS[f"{_prefix}_population_n"] = "count"\n    COLUMN_UNITS[f"{_prefix}_income_share_pct"] = "%"\n    for _suffix in ("mean_income_2025_usd", "median_income_2025_usd", "std_income_2025_usd"):\n        COLUMN_UNITS[f"{_prefix}_{_suffix}"] = "2025 US$"\nCOLUMN_UNITS.update({\n    "income_observation_n": "count",\n    "income_mean_2025_usd": "2025 US$",\n    "income_median_2025_usd": "2025 US$",\n    "income_std_2025_usd": "2025 US$",\n})\n'''

entry = '''\n\ndef run_diagnostics():\n    results = {layer: run_layer(layer) for layer in ("trusted", "refined")}\n    validate_parallel_schemas()\n    return results\n\n\ndef main(argv=None):\n    parser = argparse.ArgumentParser(description="Run canonical PNAD Stage 03.")\n    mode = parser.add_mutually_exclusive_group()\n    mode.add_argument("--analysis-only", action="store_true")\n    mode.add_argument("--diagnostics-only", action="store_true")\n    args = parser.parse_args(argv)\n    if args.diagnostics_only:\n        return run_diagnostics()\n    analysis = run_analysis()\n    if args.analysis_only:\n        return analysis\n    diagnostics = run_diagnostics()\n    return {"analysis": analysis, "diagnostics": diagnostics}\n\n\nif __name__ == "__main__":\n    main()\n'''

new_source = base.rstrip() + "\n\n# --- Stage-03 uncertainty/reproduction features ---\n\n" + extract_features(diagnostics) + metadata_updates + entry
analysis_path.write_text(new_source, encoding="utf-8")
diagnostics_path.unlink()
