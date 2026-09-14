from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "src/stage_03_pnad_analysis.py"
text = source.read_text(encoding="utf-8")
old = '\x07lpha'
if old not in text:
    raise RuntimeError("Expected malformed alpha escape was not found")
text = text.replace(old, r'\alpha')
source.write_text(text, encoding="utf-8")

test = root / "tests/test_methodology_integrity.py"
t = test.read_text(encoding="utf-8")
addition = '''\n\ndef test_stage03_source_contains_no_disallowed_control_characters():\n    source_text = Path("src/stage_03_pnad_analysis.py").read_text(encoding="utf-8")\n    controls = [\n        ch for ch in source_text\n        if ord(ch) < 32 and ch not in {"\\n", "\\r", "\\t"}\n    ]\n    assert controls == []\n'''
if "test_stage03_source_contains_no_disallowed_control_characters" not in t:
    t += addition
test.write_text(t, encoding="utf-8")

print("Pareto mathtext hotfix applied")
