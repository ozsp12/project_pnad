from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import build_release_manifest as release_manifest


def populate_release_files(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(release_manifest.RELEASE_FILES):
        (folder / name).write_bytes(f"file-{index}-{name}".encode("utf-8"))


def test_build_and_validate_release_manifest(tmp_path):
    analytics = tmp_path / "analytics"
    populate_release_files(analytics)

    manifest = analytics / "SHA256SUMS.txt"
    summary = release_manifest.build_release_manifest(analytics, manifest)

    assert summary["n_files"] == len(release_manifest.RELEASE_FILES)
    assert manifest.is_file()

    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(release_manifest.RELEASE_FILES)
    assert [line.split("  ", 1)[1] for line in lines] == list(
        release_manifest.RELEASE_FILES
    )
    assert all(len(line.split("  ", 1)[0]) == 64 for line in lines)

    release_manifest.validate_release_manifest(analytics, manifest)


def test_validate_release_manifest_detects_tampering(tmp_path):
    analytics = tmp_path / "analytics"
    populate_release_files(analytics)
    manifest = analytics / "SHA256SUMS.txt"
    release_manifest.build_release_manifest(analytics, manifest)

    target = analytics / release_manifest.RELEASE_FILES[1]
    target.write_bytes(target.read_bytes() + b"tampered")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        release_manifest.validate_release_manifest(analytics, manifest)


def test_build_release_manifest_requires_complete_package(tmp_path):
    analytics = tmp_path / "analytics"
    analytics.mkdir()
    (analytics / "README.md").write_text("partial", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Release manifest inputs are missing"):
        release_manifest.build_release_manifest(analytics)
