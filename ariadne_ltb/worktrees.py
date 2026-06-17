from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

from ariadne_ltb.git_utils import git_available, git_status, is_git_repo, run_git
from ariadne_ltb.models import BuildTicket, FailureReason, WorktreeIsolation, stable_id
from ariadne_ltb.storage import AriadneStore

BRANCH_POLICY = "codex-ticket-slug-v1"
BRANCH_PREFIX = "codex"
MAX_BRANCH_NAME_LENGTH = 160
MAX_BRANCH_SLUG_LENGTH = 56
TICKET_KEY_RE = re.compile(r"^[a-z][a-z0-9]+-\d+$", re.IGNORECASE)
BRANCH_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class WorktreeBlock:
    reason: str
    failure_reason: FailureReason


@dataclass(frozen=True)
class WorktreeIsolationResult:
    record: WorktreeIsolation | None = None
    block: WorktreeBlock | None = None


@dataclass(frozen=True)
class BranchBinding:
    policy: str
    ticket_key: str
    slug: str
    branch_name: str
    worktree_dir_name: str


def branch_binding_for_ticket(ticket: BuildTicket) -> BranchBinding:
    ticket_key = _ticket_key_component(ticket.key)
    slug = _branch_slug(ticket)
    collision_token = sha256(f"{ticket.id}:{ticket.key}:{slug}".encode("utf-8")).hexdigest()[:8]
    full_slug = f"{slug}-{collision_token}"
    branch_name = f"{BRANCH_PREFIX}/{ticket_key}-{full_slug}"
    _validate_branch_name(branch_name)
    return BranchBinding(
        policy=BRANCH_POLICY,
        ticket_key=ticket_key,
        slug=full_slug,
        branch_name=branch_name,
        worktree_dir_name=f"{ticket_key}-{full_slug}",
    )


def prepare_isolated_worktree(
    store: AriadneStore,
    ticket: BuildTicket,
    base_repo: Path,
    assignment_id: str | None = None,
) -> WorktreeIsolationResult:
    base_repo = base_repo.resolve()
    try:
        branch_binding = branch_binding_for_ticket(ticket)
    except ValueError as exc:
        return WorktreeIsolationResult(
            block=WorktreeBlock(str(exc), FailureReason.INVALID_RESOURCE)
        )

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

    worktree_path = store.worktree_path(branch_binding.worktree_dir_name)
    if worktree_path.exists():
        return WorktreeIsolationResult(
            block=WorktreeBlock(
                f"isolated worktree path already exists for {ticket.key}: {worktree_path}",
                FailureReason.RESOURCE_LOCKED,
            )
        )

    base_sha = _git_stdout(base_repo, "rev-parse", "HEAD")
    base_branch = _current_branch(base_repo)
    branch_name = branch_binding.branch_name
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
        branch_policy=branch_binding.policy,
        branch_slug=branch_binding.slug,
        target_repo_path=str(base_repo),
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
            "branch_policy": branch_binding.policy,
            "branch_name": branch_name,
            "target_repo_path": str(base_repo),
            "worktree_path": str(worktree_path),
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


def _ticket_key_component(ticket_key: str) -> str:
    if ticket_key != ticket_key.strip():
        msg = f"invalid ticket key for branch binding: {ticket_key!r}"
        raise ValueError(msg)
    if not TICKET_KEY_RE.fullmatch(ticket_key):
        msg = (
            "invalid ticket key for branch binding: "
            f"{ticket_key!r}; expected PREFIX-NUMBER with only letters, digits, and '-'"
        )
        raise ValueError(msg)
    return ticket_key.lower()


def _branch_slug(ticket: BuildTicket) -> str:
    explicit_slug = ticket.metadata.get("branch_slug")
    if explicit_slug is not None:
        if not isinstance(explicit_slug, str):
            msg = "invalid branch slug: metadata['branch_slug'] must be a string"
            raise ValueError(msg)
        slug = explicit_slug.strip()
        if slug != explicit_slug or not BRANCH_SLUG_RE.fullmatch(slug):
            msg = (
                "invalid branch slug: "
                f"{explicit_slug!r}; expected lowercase letters, digits, and single '-' separators"
            )
            raise ValueError(msg)
        return _truncate_slug(slug)

    slug = re.sub(r"[^a-z0-9]+", "-", ticket.title.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if not slug:
        msg = f"ticket title cannot produce a branch slug for {ticket.key}"
        raise ValueError(msg)
    return _truncate_slug(slug)


def _truncate_slug(slug: str) -> str:
    truncated = slug[:MAX_BRANCH_SLUG_LENGTH].strip("-")
    if not truncated:
        msg = f"invalid branch slug after truncation: {slug!r}"
        raise ValueError(msg)
    return truncated


def _validate_branch_name(branch_name: str) -> None:
    if len(branch_name) > MAX_BRANCH_NAME_LENGTH:
        msg = f"branch name is too long: {branch_name!r}"
        raise ValueError(msg)
    if not branch_name.startswith(f"{BRANCH_PREFIX}/"):
        msg = f"branch name must start with {BRANCH_PREFIX}/: {branch_name!r}"
        raise ValueError(msg)
    if branch_name.endswith(("/", ".", ".lock")):
        msg = f"branch name has an unsafe suffix: {branch_name!r}"
        raise ValueError(msg)
    if any(pattern in branch_name for pattern in ("..", "@{", "\\")):
        msg = f"branch name contains unsafe characters: {branch_name!r}"
        raise ValueError(msg)
    if not re.fullmatch(r"[a-z0-9][a-z0-9/-]*", branch_name):
        msg = f"branch name contains unsupported characters: {branch_name!r}"
        raise ValueError(msg)
    parts = branch_name.split("/")
    if any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
        msg = f"branch name contains an unsafe path component: {branch_name!r}"
        raise ValueError(msg)


def _git_stdout(repo: Path, *args: str) -> str:
    result = run_git(repo, *args)
    return result.stdout.strip() if result.returncode == 0 else ""
