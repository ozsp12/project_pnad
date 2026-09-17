from pathlib import Path

path = Path("src/stage_03_pnad_analysis.py")
text = path.read_text(encoding="utf-8")

old_block = '''# --- Stage-03 uncertainty/reproduction features ---

ROOT = Path(__file__).resolve().parents[1]

METADATA = ROOT / "data" / "metadata" / "df_metadata.xlsx"

START_YEAR, END_YEAR = 1978, 2025

BOOTSTRAP_REPS = int(os.environ.get("PNAD_BOOTSTRAP_REPS", "1000"))

BOOTSTRAP_SEED = 20090101

LIKELIHOOD_GRID_SIZE = 12001

LAYER_CONFIG = {
    "refined": {
        "role": "baseline",
        "data": ROOT / "data" / "refined",
        "tables": ROOT / "assets" / "tables_analysis_refined",
        "pattern": "pnad_refined_{year}.parquet",
    },
    "trusted": {
        "role": "benchmark",
        "data": ROOT / "data" / "trusted",
        "tables": ROOT / "assets" / "tables_analysis_trusted",
        "pattern": "pnad_trusted_{year}.parquet",
    },
}
'''

new_block = '''# --- Stage-03 uncertainty/reproduction features ---

START_YEAR, END_YEAR = 1978, 2025

BOOTSTRAP_REPS = int(os.environ.get("PNAD_BOOTSTRAP_REPS", "1000"))

BOOTSTRAP_SEED = 20090101

LIKELIHOOD_GRID_SIZE = 12001

LAYER_CONFIG = {
    "refined": {
        "role": "baseline",
        "data": REFINED_DATA_PATH,
        "tables": TABLES_ANALYSIS_REFINED_PATH,
        "pattern": "pnad_refined_{year}.parquet",
    },
    "trusted": {
        "role": "benchmark",
        "data": TRUSTED_DATA_PATH,
        "tables": TABLES_ANALYSIS_TRUSTED_PATH,
        "pattern": "pnad_trusted_{year}.parquet",
    },
}
'''

if text.count(old_block) != 1:
    raise SystemExit("Expected duplicate Stage-03 path block exactly once")
text = text.replace(old_block, new_block)

old_read = 'metadata = pd.read_excel(METADATA).rename(columns={"ano": "year"})'
new_read = 'metadata = pd.read_excel(METADATA_PATH).rename(columns={"ano": "year"})'
if text.count(old_read) != 1:
    raise SystemExit("Expected duplicate METADATA alias use exactly once")
text = text.replace(old_read, new_read)

path.write_text(text, encoding="utf-8")
