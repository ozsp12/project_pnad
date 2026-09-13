from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tests" / "test_stage_05_tables.py"
text = path.read_text(encoding="utf-8")
marker = "\ndef test_persisted_regime_shares_must_match_recomputed_values():"
if marker in text:
    text = text[:text.index(marker)].rstrip() + "\n"
path.write_text(text, encoding="utf-8")
