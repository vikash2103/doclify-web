import argparse
import sys
from pathlib import Path

from repodocs import __version__
from repodocs.constants import DEFAULT_MODEL, MAX_FILE_CHARS
from repodocs.llm import generate_readme, get_client, summarize_file
from repodocs.manifest import read_manifest, write_manifest


def _force_utf8_stdio() -> None:
    # Plain print() only, no rich/colorama — nothing here does Windows
    # console-mode detection, so there's no legacy-console write path to
    # crash on. This reconfigure is defense in depth for the rare case
    # stdout wasn't already UTF-8 (e.g. PYTHONIOENCODING unset upstream).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    manifest = write_manifest(root, model=args.model)
    print(f"Initialized {root / 'repodocs.yaml'}")
    print(f"Project: {manifest['project']}")
    print(f"Files found: {len(manifest['files'])}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    try:
        manifest = read_manifest(root)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    files = manifest.get("files", [])
    if not files:
        print("No files found in manifest — nothing to summarize.", file=sys.stderr)
        return 1

    model = args.model or manifest.get("model", DEFAULT_MODEL)

    try:
        client = get_client()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    file_summaries: dict[str, str] = {}
    for i, rel_path in enumerate(files, start=1):
        file_path = root / rel_path
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"Skipping {rel_path}: {e}", file=sys.stderr)
            continue

        content = content[:MAX_FILE_CHARS]
        print(f"[{i}/{len(files)}] Summarizing {rel_path}")
        try:
            file_summaries[rel_path] = summarize_file(client, model, rel_path, content)
        except Exception as e:
            print(f"Failed to summarize {rel_path}: {e}", file=sys.stderr)

    if not file_summaries:
        print("Error: no file summaries were generated.", file=sys.stderr)
        return 1

    print("Generating README.md")
    try:
        readme = generate_readme(client, model, manifest["project"], file_summaries)
    except Exception as e:
        print(f"Error: failed to generate README.md: {e}", file=sys.stderr)
        return 1

    readme_path = root / "README.md"
    if readme_path.exists():
        readme_path.replace(root / "README.md.bak")

    readme_path.write_text(readme, encoding="utf-8")
    print(f"Wrote {readme_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repodocs", description="Generate an AI-written README for a codebase.")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Scan a directory and build a manifest.")
    init_parser.add_argument("path", nargs="?", default=".", help="Target directory (default: current directory)")
    init_parser.add_argument("--model", default=DEFAULT_MODEL, help="Groq model to record in the manifest")
    init_parser.set_defaults(func=cmd_init)

    run_parser = subparsers.add_parser("run", help="Summarize files and generate README.md.")
    run_parser.add_argument("path", nargs="?", default=".", help="Target directory (default: current directory)")
    run_parser.add_argument("--model", default=None, help="Override the model recorded in the manifest")
    run_parser.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
