from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import stage_02_build_trusted_pnad as stage_02


def test_validation_outputs_are_outside_analysis_tables():
    assert stage_02.AUDIT_FILE.parent == stage_02.VALIDATION_TABLES_PATH
    assert stage_02.TESTS_FILE.parent == stage_02.VALIDATION_TABLES_PATH
    assert stage_02.VALIDATION_TABLES_PATH.name == "tables_validation"
