"""Final paper-figure filename normalization.

Stage 05 now owns the complete trusted publication figure set. This helper is
kept only because the paper-assets workflow still invokes it; it no longer
creates an additional inequality figure.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIGURES_PAPER = REPO_ROOT / "assets" / "figures_paper"
LEGACY_PREFIX = "moura_ribeiro_2009_"


def normalize_paper_figure_names() -> None:
    """Remove the legacy Moura-Ribeiro prefix from any remaining PNG names."""
    FIGURES_PAPER.mkdir(parents=True, exist_ok=True)
    for source in sorted(FIGURES_PAPER.glob(f"{LEGACY_PREFIX}*.png")):
        target = source.with_name(source.name.removeprefix(LEGACY_PREFIX))
        if target.exists():
            target.unlink()
        source.replace(target)


def main() -> None:
    normalize_paper_figure_names()
    print("Paper figure names normalized.")


if __name__ == "__main__":
    main()
