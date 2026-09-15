from pathlib import Path

import pathspec

from repodocs.constants import ALWAYS_EXCLUDED_DIRS, INCLUDED_SUFFIXES


def _load_gitignore_spec(root: Path) -> pathspec.PathSpec:
    gitignore = root / ".gitignore"
    patterns = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    return pathspec.PathSpec.from_lines("gitignore", patterns)


def scan(root: Path) -> list[str]:
    """
    Walk `root`, respecting its .gitignore, and return a sorted list of
    relative file paths worth summarizing (non-empty, allowed suffix, not
    inside an always-excluded directory).
    """
    spec = _load_gitignore_spec(root)
    matched: list[str] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        rel = path.relative_to(root)

        if any(part in ALWAYS_EXCLUDED_DIRS for part in rel.parts):
            continue

        if path.suffix not in INCLUDED_SUFFIXES:
            continue

        if spec.match_file(str(rel)):
            continue

        if path.stat().st_size == 0:
            continue

        matched.append(str(rel).replace("\\", "/"))

    return sorted(matched)
