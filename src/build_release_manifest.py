"""Build and validate SHA-256 checksums for the archival analytics package."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYTICS_PATH = REPO_ROOT / "data" / "analytics"
DEFAULT_OUTPUT_PATH = ANALYTICS_PATH / "SHA256SUMS.txt"

RELEASE_FILES = (
    "README.md",
    "pnad_refined_all.parquet",
    "pnad_trusted_all.parquet",
    "pnad_refined_all_schema.csv",
    "pnad_trusted_all_schema.csv",
    "pnad_annual_metadata.csv",
    "pnad_datasets_metadata.csv",
)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of one file without loading it fully in memory."""
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release_manifest(
    analytics_path: Path = ANALYTICS_PATH,
    output_path: Path | None = None,
) -> dict[str, int | str]:
    """Write a deterministic GNU-style SHA256SUMS file for archival products."""
    analytics_path = Path(analytics_path)
    output_path = Path(output_path or analytics_path / DEFAULT_OUTPUT_PATH.name)

    missing = [name for name in RELEASE_FILES if not (analytics_path / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "Release manifest inputs are missing: " + ", ".join(missing)
        )

    lines = [
        f"{sha256_file(analytics_path / name)}  {name}"
        for name in RELEASE_FILES
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"output": str(output_path), "n_files": len(lines)}


def validate_release_manifest(
    analytics_path: Path = ANALYTICS_PATH,
    manifest_path: Path | None = None,
) -> None:
    """Raise if the release manifest is incomplete, duplicated, or stale."""
    analytics_path = Path(analytics_path)
    manifest_path = Path(manifest_path or analytics_path / DEFAULT_OUTPUT_PATH.name)

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Release manifest not found: {manifest_path}")

    entries: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, separator, filename = line.partition("  ")
        if not separator or len(digest) != 64 or not filename:
            raise ValueError(f"Malformed checksum line: {line}")
        if filename in entries:
            raise ValueError(f"Duplicate checksum entry: {filename}")
        entries[filename] = digest.lower()

    if tuple(entries) != RELEASE_FILES:
        raise ValueError(
            "Release manifest file set/order differs from the canonical package."
        )

    for filename, expected in entries.items():
        path = analytics_path / filename
        if not path.is_file():
            raise FileNotFoundError(f"Release file not found: {path}")
        observed = sha256_file(path)
        if observed != expected:
            raise ValueError(f"SHA-256 mismatch for {filename}")


def main() -> dict[str, int | str]:
    """Build and immediately validate the archival checksum manifest."""
    summary = build_release_manifest()
    validate_release_manifest()
    return summary


if __name__ == "__main__":
    summary = main()
    print(
        f"Release checksum manifest created for {summary['n_files']} files: "
        f"{summary['output']}"
    )
