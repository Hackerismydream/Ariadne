from __future__ import annotations

import shutil
from pathlib import Path

from ariadne_ltb.git_utils import git_status, is_git_repo, run_git
from ariadne_ltb.models import WorkdirCleanupResult, WorkdirStatus, WorktreeIsolation
from ariadne_ltb.storage import AriadneStore


def list_workdirs(store: AriadneStore) -> list[WorkdirStatus]:
    return [_status_for_record(record) for record in store.list_worktree_isolations()]


def cleanup_workdirs(
    store: AriadneStore,
    *,
    confirm_cleanup: bool,
    force_dirty: bool = False,
    ticket_key: str | None = None,
) -> list[WorkdirCleanupResult]:
    if not confirm_cleanup:
        msg = "workdir cleanup requires --confirm-cleanup"
        raise PermissionError(msg)

    results: list[WorkdirCleanupResult] = []
    wanted = ticket_key.upper() if ticket_key else None
    for record in store.list_worktree_isolations():
        if wanted and record.ticket_key.upper() != wanted:
            continue
        result, updated = _cleanup_one(store, record, force_dirty=force_dirty)
        results.append(result)
        if updated is not None:
            store.save_worktree_isolation(updated)
    return results


def _status_for_record(record: WorktreeIsolation) -> WorkdirStatus:
    path = Path(record.worktree_path)
    status = git_status(path) if path.exists() and is_git_repo(path) else ""
    return WorkdirStatus(
        ticket_id=record.ticket_id,
        ticket_key=record.ticket_key,
        worktree_path=str(path),
        branch_name=record.branch_name,
        base_repo_path=record.base_repo_path,
        active=record.active,
        exists=path.exists(),
        dirty=bool(status.strip()),
        git_status=status,
        record_path=record.record_path,
    )


def _cleanup_one(
    store: AriadneStore,
    record: WorktreeIsolation,
    *,
    force_dirty: bool,
) -> tuple[WorkdirCleanupResult, WorktreeIsolation | None]:
    status = _status_for_record(record)
    if not _is_managed_worktree(store, Path(record.worktree_path)):
        return (
            WorkdirCleanupResult(
                ticket_key=record.ticket_key,
                worktree_path=record.worktree_path,
                skipped=True,
                reason="worktree path is outside .ariadne/worktrees",
                dirty=status.dirty,
                record_path=record.record_path,
            ),
            None,
        )
    if status.exists and status.dirty and not force_dirty:
        return (
            WorkdirCleanupResult(
                ticket_key=record.ticket_key,
                worktree_path=record.worktree_path,
                skipped=True,
                reason="worktree is dirty; rerun with --force-dirty to remove generated workdir",
                dirty=True,
                record_path=record.record_path,
            ),
            None,
        )

    removed = False
    reason = ""
    path = Path(record.worktree_path)
    if status.exists:
        removed, reason = _remove_git_worktree(record, force_dirty=force_dirty)
        if not removed and path.exists() and force_dirty:
            shutil.rmtree(path)
            removed = True
            reason = "removed by filesystem fallback after git worktree remove failed"
    else:
        reason = "worktree path already absent"

    branch_removed, branch_reason = _delete_managed_branch(record)
    if branch_reason:
        reason = f"{reason}; {branch_reason}" if reason else branch_reason
    removed = removed or branch_removed

    updated = record.model_copy(update={"active": False})
    return (
        WorkdirCleanupResult(
            ticket_key=record.ticket_key,
            worktree_path=record.worktree_path,
            removed=removed,
            skipped=False,
            reason=reason,
            dirty=status.dirty,
            record_path=record.record_path,
        ),
        updated,
    )


def _remove_git_worktree(record: WorktreeIsolation, *, force_dirty: bool) -> tuple[bool, str]:
    base = Path(record.base_repo_path)
    path = Path(record.worktree_path)
    if not base.exists() or not is_git_repo(base):
        return False, "base repo is unavailable"
    args = ["worktree", "remove"]
    if force_dirty:
        args.append("--force")
    args.append(str(path))
    result = run_git(base, *args)
    if result.returncode == 0:
        return True, "removed with git worktree remove"
    return False, (result.stderr or result.stdout or "git worktree remove failed").strip()


def _delete_managed_branch(record: WorktreeIsolation) -> tuple[bool, str]:
    if not record.branch_name.startswith(("ariadne/", "codex/")):
        return False, "branch cleanup skipped for non-Ariadne branch"
    base = Path(record.base_repo_path)
    if not base.exists() or not is_git_repo(base):
        return False, "branch cleanup skipped because base repo is unavailable"
    listed = run_git(base, "branch", "--list", record.branch_name)
    if not listed.stdout.strip():
        return False, "branch already absent"
    result = run_git(base, "branch", "-D", record.branch_name)
    if result.returncode == 0:
        return True, f"deleted branch {record.branch_name}"
    return False, (result.stderr or result.stdout or "git branch delete failed").strip()


def _is_managed_worktree(store: AriadneStore, path: Path) -> bool:
    try:
        path.resolve().relative_to(store.worktrees_dir.resolve())
    except ValueError:
        return False
    return True
