from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
WF = ROOT / ".github" / "workflows"

# Tests
p = TESTS / "test_stage_03_moura_ribeiro_evidence.py"
s = p.read_text(encoding="utf-8").replace(
    "from src import stage_03_moura_ribeiro_evidence as evidence",
    "from src import stage_03_pnad_analysis as evidence",
)
p.write_text(s, encoding="utf-8")

p = TESTS / "test_paper_figures.py"
s = p.read_text(encoding="utf-8").replace(
    "from src import stage_05_moura_ribeiro as stage_05",
    "from src import stage_05_publication as stage_05",
)
p.write_text(s, encoding="utf-8")

p = TESTS / "test_stage_05_tables.py"
s = p.read_text(encoding="utf-8")
s = s.replace(
    "from src import stage_05_tables as tables",
    "from src import stage_05_publication as tables\nfrom src import stage_03_pnad_analysis as analysis",
)
start = s.index("def test_band_record_is_nonoverlapping_summary():")
end = s.index("\ndef test_gompertz_paper_schema", start)
replacement = '''def test_exclusive_income_statistics_are_computed_in_stage03():\n    values = np.arange(1.0, 1001.0)\n    record = analysis.compute_exclusive_income_statistics(values)\n    assert record["income_observation_n"] == 1000\n    assert record["p90_p99_population_n"] == 90\n    assert record["p99_p999_population_n"] == 9\n    assert record["p999_p100_population_n"] == 1\n\n'''
s = s[:start] + replacement + s[end + 1:]
p.write_text(s, encoding="utf-8")

# Workflows
p = WF / "run_analysis.yml"
s = p.read_text(encoding="utf-8")
s = s.replace('      - "src/stage_03_moura_ribeiro_evidence.py"\n', "")
s = s.replace(
    "          python src/stage_03_pnad_analysis.py\n          python src/stage_03_moura_ribeiro_evidence.py\n",
    "          python src/stage_03_pnad_analysis.py\n",
)
p.write_text(s, encoding="utf-8")

p = WF / "build_paper_assets.yml"
s = p.read_text(encoding="utf-8")
for old in (
    '      - "src/stage_03_moura_ribeiro_evidence.py"\n',
    '      - "src/stage_05_moura_ribeiro.py"\n',
    '      - "src/stage_05_tables.py"\n',
):
    s = s.replace(old, "")
s = s.replace(
    '      - "src/stage_05_publication.py"\n',
    '      - "src/stage_03_pnad_analysis.py"\n      - "src/stage_05_publication.py"\n',
)
s = s.replace(
    "      - name: Build Stage 03 Moura-Ribeiro reproduction diagnostics\n        run: python src/stage_03_moura_ribeiro_evidence.py\n",
    "      - name: Refresh Stage 03 diagnostics\n        run: python src/stage_03_pnad_analysis.py --diagnostics-only\n",
)
p.write_text(s, encoding="utf-8")

# Root README
p = ROOT / "README.md"
s = p.read_text(encoding="utf-8")
s = s.replace(
    '| 03 | `src/stage_03_pnad_analysis.py` | Runs descriptive, inequality, CCDF, and Gompertz–Pareto analyses on refined and trusted data | analytical CSV and PNG assets |\n| 03 | `src/stage_03_moura_ribeiro_evidence.py` | Computes Moura Jr.–Ribeiro (2009) uncertainty and reproduction diagnostics for both analytical layers | diagnostics consolidated into canonical annual tables |',
    '| 03 | `src/stage_03_pnad_analysis.py` | Runs descriptive, inequality, CCDF, Gompertz–Pareto, bootstrap and Moura Jr.–Ribeiro reproduction analyses on refined and trusted data | analytical CSV and PNG assets |',
)
s = s.replace(
    '`stage_03_moura_ribeiro_evidence.py` adds the uncertainty calculations required to reproduce',
    '`stage_03_pnad_analysis.py` also contains the uncertainty calculations required to reproduce',
)
s = s.replace(
    'Stage 05 is presentation-only. `stage_05_publication.py` consumes persisted Stage-03 scientific results and orchestrates publication figures plus the canonical tables. `stage_05_moura_ribeiro.py` contains the figure routines, while `stage_05_tables.py` consolidates the paper-facing tables. Statistical bootstrap and likelihood calculations do not belong to Stage 05.',
    'Stage 05 is presentation-only. `stage_05_publication.py` contains the figure and table-formatting features and consumes persisted Stage-03 scientific results. Statistical estimation, bootstrap, likelihood calculations and top-income-band aggregation belong to Stage 03.',
)
s = s.replace("python src/stage_03_moura_ribeiro_evidence.py\n", "")
p.write_text(s, encoding="utf-8")

# Source README
p = SRC / "README.md"
s = p.read_text(encoding="utf-8")
s = s.replace(
    '| 03 | `stage_03_pnad_analysis.py` | descriptive, inequality, CCDF and Gompertz–Pareto analysis for refined/trusted |\n| 03 | `stage_03_moura_ribeiro_evidence.py` | 2009-method uncertainty and reproduction diagnostics consolidated into canonical tables |',
    '| 03 | `stage_03_pnad_analysis.py` | descriptive, inequality, CCDF, Gompertz–Pareto, uncertainty and 2009-method reproduction analysis for refined/trusted |',
)
s = s.replace(
    '| 05 | `stage_05_publication.py` | canonical paper-asset entry point |\n| 05 | `stage_05_moura_ribeiro.py` | publication figure routines only |\n| 05 | `stage_05_tables.py` | publication-table consolidation only |',
    '| 05 | `stage_05_publication.py` | publication figures and table formatting from persisted Stage-03 results |',
)
s = s.replace(
    '`stage_03_moura_ribeiro_evidence.py` computes the simulation/inference quantities needed to reproduce',
    '`stage_03_pnad_analysis.py` also computes the simulation/inference quantities needed to reproduce',
)
s = s.replace(
    'Stage 05 is strictly publication-only. `stage_05_publication.py` is the canonical executable. It reads the consolidated trusted Stage-03 outputs, calls the figure routines in `stage_05_moura_ribeiro.py`, and calls `stage_05_tables.py` to write four canonical tables.',
    'Stage 05 is strictly publication-only. `stage_05_publication.py` is the single Stage-05 executable and contains the figure and table-formatting features that consume consolidated trusted Stage-03 outputs.',
)
p.write_text(s, encoding="utf-8")

for rel in ("assets/README.md", "data/README.md"):
    p = ROOT / rel
    if p.exists():
        s = p.read_text(encoding="utf-8")
        s = s.replace("stage_03_moura_ribeiro_evidence.py", "stage_03_pnad_analysis.py")
        s = s.replace("stage_05_moura_ribeiro.py", "stage_05_publication.py")
        s = s.replace("stage_05_tables.py", "stage_05_publication.py")
        p.write_text(s, encoding="utf-8")
