from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def git_available() -> bool:
    return shutil.which("git") is not None


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


def is_git_repo(repo: Path) -> bool:
    if not git_available():
        return False
    result = run_git(repo, "rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and result.stdout.strip() == "true"


def git_head(repo: Path) -> str | None:
    if not is_git_repo(repo):
        return None
    result = run_git(repo, "rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else None


def git_status(repo: Path) -> str:
    if not is_git_repo(repo):
        return ""
    return run_git(repo, "status", "--short").stdout


def git_branch(repo: Path) -> str | None:
    if not is_git_repo(repo):
        return None
    result = run_git(repo, "branch", "--show-current")
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    result = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    branch = result.stdout.strip() if result.returncode == 0 else ""
    return branch if branch and branch != "HEAD" else None


def git_diff(repo: Path) -> str:
    if not is_git_repo(repo):
        return ""
    return run_git(repo, "diff", "--", ".").stdout


def changed_files(repo: Path) -> list[str]:
    status = git_status(repo)
    files: list[str] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        if "__pycache__" in path or path.endswith(".pyc") or ".pytest_cache" in path:
            continue
        files.append(path)
    return sorted(files)
