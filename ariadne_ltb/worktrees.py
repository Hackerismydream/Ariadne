from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from ariadne_ltb.git_utils import git_available, git_status, is_git_repo, run_git
from ariadne_ltb.models import BuildTicket, FailureReason, WorktreeIsolation, stable_id
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class WorktreeBlock:
    reason: str
    failure_reason: FailureReason


@dataclass(frozen=True)
class WorktreeIsolationResult:
    record: WorktreeIsolation | None = None
    block: WorktreeBlock | None = None


def prepare_isolated_worktree(
    store: AriadneStore,
    ticket: BuildTicket,
    base_repo: Path,
    assignment_id: str | None = None,
) -> WorktreeIsolationResult:
    base_repo = base_repo.resolve()
    if not git_available():
        return WorktreeIsolationResult(
            block=WorktreeBlock("git command is not available.", FailureReason.COMMAND_UNAVAILABLE)
        )
    if not is_git_repo(base_repo):
        return WorktreeIsolationResult(
            block=WorktreeBlock(f"target repo is not a git work tree: {base_repo}", FailureReason.INVALID_RESOURCE)
        )

    status = git_status(base_repo)
    if status.strip():
        return WorktreeIsolationResult(
            block=WorktreeBlock(
                "base checkout is dirty; commit, stash, or clean it before isolated execution.\n"
                f"git status --short:\n{status}",
                FailureReason.DIRTY_BASE_CHECKOUT,
            )
        )

    record_path = store.worktree_record_path(ticket.key)
    if record_path.exists():
        existing = store.load_worktree_isolation(ticket.key)
        if existing.active:
            return WorktreeIsolationResult(
                block=WorktreeBlock(
                    "active isolated worktree already exists for "
                    f"{ticket.key}: {existing.worktree_path}",
                    FailureReason.RESOURCE_LOCKED,
                )
            )

    worktree_path = store.worktree_path(ticket.key)
    if worktree_path.exists():
        return WorktreeIsolationResult(
            block=WorktreeBlock(
                f"isolated worktree path already exists for {ticket.key}: {worktree_path}",
                FailureReason.RESOURCE_LOCKED,
            )
        )

    base_sha = _git_stdout(base_repo, "rev-parse", "HEAD")
    base_branch = _current_branch(base_repo)
    branch_name = _branch_name(ticket)
    if _branch_exists(base_repo, branch_name):
        return WorktreeIsolationResult(
            block=WorktreeBlock(
                f"isolated branch already exists for {ticket.key}: {branch_name}",
                FailureReason.RESOURCE_LOCKED,
            )
        )

    result = run_git(base_repo, "worktree", "add", "-b", branch_name, str(worktree_path), base_sha)
    if result.returncode != 0:
        reason = (result.stderr or result.stdout or "git worktree add failed").strip()
        return WorktreeIsolationResult(
            block=WorktreeBlock(
                f"failed to create isolated worktree for {ticket.key}: {reason}",
                FailureReason.RESOURCE_LOCKED,
            )
        )

    record = WorktreeIsolation(
        id=stable_id("worktree", ticket.id, branch_name),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        base_repo_path=str(base_repo),
        base_branch=base_branch,
        base_sha=base_sha,
        branch_name=branch_name,
        worktree_path=str(worktree_path),
        record_path=str(record_path),
        active=True,
        owner_metadata={
            "ticket_id": ticket.id,
            "ticket_key": ticket.key,
            "assignment_id": assignment_id,
        },
    )
    store.save_worktree_isolation(record)
    return WorktreeIsolationResult(record=record)


def _current_branch(repo: Path) -> str:
    branch = _git_stdout(repo, "branch", "--show-current")
    if branch:
        return branch
    ref = _git_stdout(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return ref if ref and ref != "HEAD" else "detached"


def _branch_exists(repo: Path, branch_name: str) -> bool:
    result = run_git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}")
    return result.returncode == 0


def _branch_name(ticket: BuildTicket) -> str:
    key = re.sub(r"[^a-z0-9._-]+", "-", ticket.key.lower()).strip("-")
    ticket_id = re.sub(r"[^a-z0-9]+", "", ticket.id.lower())[:8]
    return f"ariadne/{key}-{ticket_id}"


def _git_stdout(repo: Path, *args: str) -> str:
    result = run_git(repo, *args)
    return result.stdout.strip() if result.returncode == 0 else ""
