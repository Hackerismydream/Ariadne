from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ariadne_ltb.models import SourceFetchRecord, stable_id

GITHUB_RE = re.compile(r"^https://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?(?:[#?].*)?$")


@dataclass(frozen=True)
class GitHubRepoRef:
    owner: str
    repo: str
    url: str


@dataclass(frozen=True)
class SourceFetchResult:
    status: str
    source_url: str
    cache_path: str | None
    commit_sha: str | None
    default_branch: str | None
    fetched_ref: str | None
    file_count: int
    warnings: list[str]
    error: str | None = None
    byte_count: int = 0


class RepositoryFetcher(Protocol):
    def fetch(self, url: str, cache_root: Path, timeout_seconds: int = 45) -> SourceFetchResult: ...


def parse_github_url(value: str) -> GitHubRepoRef | None:
    match = GITHUB_RE.match(value.strip())
    if not match:
        return None
    owner, repo = match.groups()
    repo = repo.removesuffix(".git")
    return GitHubRepoRef(owner=owner, repo=repo, url=f"https://github.com/{owner}/{repo}")


class GitRepositoryFetcher:
    def fetch(self, url: str, cache_root: Path, timeout_seconds: int = 45) -> SourceFetchResult:
        ref = parse_github_url(url)
        if ref is None:
            return SourceFetchResult("blocked", url, None, None, None, None, 0, [], "unsupported_git_url")
        checkout = cache_root / "github.com" / ref.owner / ref.repo / "checkout"
        try:
            if checkout.exists() and (checkout / ".git").exists():
                subprocess.run(
                    ["git", "fetch", "--depth=1", "origin"],
                    cwd=checkout,
                    timeout=timeout_seconds,
                    check=True,
                    capture_output=True,
                )
            else:
                checkout.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ["git", "clone", "--depth=1", "--filter=blob:none", ref.url, str(checkout)],
                    timeout=timeout_seconds,
                    check=True,
                    capture_output=True,
                )
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=checkout,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=checkout,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip() or None
            files = [path for path in checkout.rglob("*") if path.is_file() and ".git" not in path.parts]
            byte_count = sum(path.stat().st_size for path in files)
            return SourceFetchResult(
                "cached",
                ref.url,
                str(checkout),
                commit,
                branch,
                branch,
                len(files),
                [],
                byte_count=byte_count,
            )
        except subprocess.TimeoutExpired:
            return SourceFetchResult("blocked", ref.url, None, None, None, None, 0, [], "repository_fetch_timeout")
        except (OSError, subprocess.CalledProcessError) as exc:
            return SourceFetchResult(
                "blocked",
                ref.url,
                None,
                None,
                None,
                None,
                0,
                [],
                f"repository_fetch_failed:{type(exc).__name__}",
            )


def fetch_record_from_result(source_id: str, result: SourceFetchResult) -> SourceFetchRecord:
    return SourceFetchRecord(
        id=stable_id("source_fetch", source_id, result.source_url, result.commit_sha or result.error or result.status),
        source_document_id=source_id,
        source_url=result.source_url,
        status=result.status,  # type: ignore[arg-type]
        cache_path=result.cache_path,
        commit_sha=result.commit_sha,
        default_branch=result.default_branch,
        fetched_ref=result.fetched_ref,
        file_count=result.file_count,
        byte_count=result.byte_count,
        warnings=result.warnings,
        error=result.error,
    )
