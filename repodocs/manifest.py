from pathlib import Path

import yaml

from repodocs.constants import DEFAULT_MODEL, MANIFEST_FILENAME
from repodocs.scanner import scan


def write_manifest(root: Path, model: str = DEFAULT_MODEL) -> dict:
    """
    Scan `root` and write repodocs.yaml describing what `run` will process.
    The project name always reflects root's own directory name.
    """
    manifest = {
        "project": root.name,
        "model": model,
        "files": scan(root),
    }
    manifest_path = root / MANIFEST_FILENAME
    manifest_path.write_text(
        yaml.dump(manifest, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return manifest


def read_manifest(root: Path) -> dict:
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"{MANIFEST_FILENAME} not found in {root} — run `repodocs init` first."
        )
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
