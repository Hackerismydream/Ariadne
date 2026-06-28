from __future__ import annotations

import difflib
import shutil
import subprocess
from pathlib import Path


def git_available() -> bool:
    return shutil.which("git") is not None


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    command = ["git", *args]
    try:
        return subprocess.run(
            command,
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        return subprocess.CompletedProcess(command, 128, "", str(exc))


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
    tracked_diff = run_git(repo, "diff", "--", ".").stdout
    untracked_diff = _untracked_diff(repo)
    return "\n".join(part for part in [tracked_diff.rstrip(), untracked_diff.rstrip()] if part).strip()


def changed_files(repo: Path) -> list[str]:
    status = git_status(repo)
    files: list[str] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        for changed_path in _expand_status_path(repo, path):
            if _is_ignored_generated_path(changed_path):
                continue
            files.append(changed_path)
    return sorted(files)


def _untracked_diff(repo: Path) -> str:
    patches: list[str] = []
    for path in _untracked_files(repo):
        file_path = repo / path
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            patches.append(
                "\n".join(
                    [
                        f"diff --git a/{path} b/{path}",
                        "new file mode 100644",
                        "index 0000000..0000000",
                        "--- /dev/null",
                        f"+++ b/{path}",
                        "@@ -0,0 +1 @@",
                        "+<binary file omitted>",
                    ]
                )
            )
            continue
        lines = content.splitlines(keepends=True)
        patch = "".join(
            difflib.unified_diff(
                [],
                lines,
                fromfile="/dev/null",
                tofile=f"b/{path}",
            )
        )
        patches.append(
            "\n".join(
                [
                    f"diff --git a/{path} b/{path}",
                    "new file mode 100644",
                    "index 0000000..0000000",
                    patch.rstrip(),
                ]
            )
        )
    return "\n".join(patch for patch in patches if patch)


def _untracked_files(repo: Path) -> list[str]:
    files: list[str] = []
    for line in git_status(repo).splitlines():
        if not line.startswith("?? "):
            continue
        path = line[3:].strip()
        for changed_path in _expand_status_path(repo, path):
            if _is_ignored_generated_path(changed_path):
                continue
            files.append(changed_path)
    return sorted(files)


def _expand_status_path(repo: Path, path: str) -> list[str]:
    normalized = path.strip()
    if not normalized.endswith("/"):
        return [normalized]
    directory = repo / normalized
    if not directory.is_dir():
        return [normalized]
    expanded: list[str] = []
    for child in sorted(item for item in directory.rglob("*") if item.is_file()):
        relative = child.relative_to(repo).as_posix()
        if not _is_ignored_generated_path(relative):
            expanded.append(relative)
    return expanded or [normalized]


def _is_ignored_generated_path(path: str) -> bool:
    return "__pycache__" in path or path.endswith(".pyc") or ".pytest_cache" in path
