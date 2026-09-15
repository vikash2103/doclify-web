import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from threading import Lock
from typing import Optional

from git import GitCommandError, Repo

GITHUB_URL_RE = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+(?:\.git)?/?$"
)

ERROR_MARKERS = ("Error:", "Traceback (most recent call last)")

_JOBS: dict[str, dict] = {}
_LOCK = Lock()


def is_valid_github_url(url: str) -> bool:
    return bool(GITHUB_URL_RE.match(url.strip()))


def _repo_name_from_url(repo_url: str) -> str:
    name = repo_url.rstrip("/")
    name = name.removesuffix(".git")
    return name.rsplit("/", 1)[-1]


def _repodocs_executable() -> str:
    """Path to the `repodocs` console script installed in this venv."""
    bin_dir = Path(sys.executable).parent
    name = "repodocs.exe" if os.name == "nt" else "repodocs"
    return str(bin_dir / name)


def _set_status(job_id: str, status: str, stage_detail: str = "") -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        job["status"] = status
        job["stage_detail"] = stage_detail


def _set_error(job_id: str, message: str) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        job["status"] = "error"
        job["error"] = message


def create_job(repo_url: str) -> str:
    job_id = str(uuid.uuid4())
    with _LOCK:
        _JOBS[job_id] = {
            "status": "queued",
            "stage_detail": "",
            "repo_url": repo_url,
            "readme_content": None,
            "error": None,
        }
    return job_id


def get_job(job_id: str) -> Optional[dict]:
    with _LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job is not None else None


def _run_repodocs_command(args: list[str], cwd: Path, env: dict) -> subprocess.CompletedProcess:
    # CREATE_NO_WINDOW keeps a console window from flashing/attaching when this
    # subprocess is spawned from a background server process on Windows.
    # repodocs itself never depends on console-mode detection (plain print(),
    # no rich/colorama), so this is general hygiene rather than a bug workaround.
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(
        [_repodocs_executable(), *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
        creationflags=creationflags,
    )


def _looks_like_failure(result: subprocess.CompletedProcess) -> bool:
    if result.returncode != 0:
        return True
    combined = f"{result.stdout}\n{result.stderr}"
    return any(marker in combined for marker in ERROR_MARKERS)


def run_pipeline(job_id: str, repo_url: str, groq_api_key: str) -> None:
    """
    Background task: clone -> repodocs init -> repodocs run -> read README -> cleanup.
    Never logs or persists groq_api_key; it only ever lives in this process's
    subprocess environment for the lifetime of the `repodocs run` call.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="repodocs_job_"))
    # repodocs derives the project name from its target directory's own basename,
    # so clone into a subdirectory named after the real repo rather than using
    # the random temp dir itself as the working directory.
    repo_dir = temp_dir / _repo_name_from_url(repo_url)

    try:
        _set_status(job_id, "cloning", f"Cloning {repo_url}")
        try:
            Repo.clone_from(repo_url, repo_dir, depth=1)
        except GitCommandError as e:
            _set_error(job_id, f"Failed to clone repository: {e.stderr or e}")
            return

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        _set_status(job_id, "initializing", "Running repodocs init")
        init_result = _run_repodocs_command(["init"], cwd=repo_dir, env=env)
        if _looks_like_failure(init_result):
            detail = (init_result.stdout + "\n" + init_result.stderr).strip()
            _set_error(job_id, f"repodocs init failed: {detail[-2000:]}")
            return

        _set_status(job_id, "summarizing", "Generating file summaries and README (this can take a while)")
        env["GROQ_API_KEY"] = groq_api_key
        try:
            run_result = _run_repodocs_command(["run"], cwd=repo_dir, env=env)
        finally:
            env.pop("GROQ_API_KEY", None)

        _set_status(job_id, "generating", "Finalizing README")
        readme_path = repo_dir / "README.md"

        if _looks_like_failure(run_result) or not readme_path.exists():
            detail = (run_result.stdout + "\n" + run_result.stderr).strip()
            _set_error(job_id, f"repodocs run failed: {detail[-2000:]}")
            return

        readme_content = readme_path.read_text(encoding="utf-8")

        with _LOCK:
            job = _JOBS.get(job_id)
            if job is not None:
                job["readme_content"] = readme_content
                job["status"] = "done"
                job["stage_detail"] = "README.md generated"

    except subprocess.TimeoutExpired:
        _set_error(job_id, "Timed out while running repodocs.")
    except Exception as e:
        _set_error(job_id, f"Unexpected error: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
