DEFAULT_MODEL = "openai/gpt-oss-120b"

MANIFEST_FILENAME = "repodocs.yaml"

# File suffixes repodocs will consider documentation-worthy source material.
INCLUDED_SUFFIXES = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".md", ".txt", ".yaml", ".yml", ".json",
}

# Directories never worth scanning, regardless of .gitignore contents.
ALWAYS_EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".tox", "dist", "build", "egg-info",
}

# Per-file character budget sent to the summarization call. Large files are
# truncated rather than chunked — good enough for a dense summary, and much
# simpler than token-aware chunking.
MAX_FILE_CHARS = 20_000
