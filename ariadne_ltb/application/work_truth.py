from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ariadne_ltb.application.dtos import DaemonStatusDTO
from ariadne_ltb.models import (
    AgentRunStatus,
    AssignmentStatus,
    ExecutionResult,
    FailureReason,
    ReviewReport,
    ReviewVerdict,
    TicketAssignment,
)
from ariadne_ltb.storage import AriadneStore

TerminalVerdict = Literal[
    "blocked_before_execution",
    "executed_failed",
    "review_blocked",
    "succeeded",
    "unknown",
]

ACTIVE_ASSIGNMENT_STATUSES = {AssignmentStatus.CLAIMED, AssignmentStatus.RUNNING}
CLAIMABLE_ASSIGNMENT_STATUSES = {
    AssignmentStatus.QUEUED,
    AssignmentStatus.ROUTED,
    AssignmentStatus.HANDOFF_READY,
    AssignmentStatus.AWAITING_USER_APPROVAL,
    AssignmentStatus.READY_TO_CLAIM,
}


@dataclass(frozen=True)
class WorkTruth:
    terminal_verdict: TerminalVerdict
    blocked_reason: str | None = None
    agent_changed_files: tuple[str, ...] = ()
    preflight_dirty_files: tuple[str, ...] = ()


def reduce_work_truth(
    *,
    assignment: TicketAssignment | None = None,
    execution: ExecutionResult | None = None,
    review: ReviewReport | None = None,
    run_status: str | AgentRunStatus | None = None,
) -> WorkTruth:
    preflight_dirty_files = tuple(_preflight_dirty_files(execution))
    agent_changed_files = tuple(_agent_changed_files(execution))

    if assignment and assignment.status in {AssignmentStatus.BLOCKED, AssignmentStatus.FAILED}:
        return WorkTruth(
            terminal_verdict="blocked_before_execution",
            blocked_reason=assignment.blocker or _failure_reason_value(assignment.failure_reason),
            agent_changed_files=agent_changed_files,
            preflight_dirty_files=preflight_dirty_files,
        )

    if execution and execution.blocked:
        return WorkTruth(
            terminal_verdict="blocked_before_execution",
            blocked_reason=execution.block_reason or _failure_reason_value(execution.failure_reason),
            agent_changed_files=agent_changed_files,
            preflight_dirty_files=preflight_dirty_files,
        )

    if execution and (execution.exit_code != 0 or execution.test_exit_code not in {None, 0}):
        return WorkTruth(
            terminal_verdict="executed_failed",
            blocked_reason=execution.block_reason or _failure_reason_value(execution.failure_reason),
            agent_changed_files=agent_changed_files,
            preflight_dirty_files=preflight_dirty_files,
        )

    if review and review.verdict is not ReviewVerdict.PASS:
        reason = "; ".join(review.failed_checks or review.required_fixes or review.warnings)
        return WorkTruth(
            terminal_verdict="review_blocked",
            blocked_reason=reason or review.verdict.value,
            agent_changed_files=agent_changed_files,
            preflight_dirty_files=preflight_dirty_files,
        )

    normalized_run_status = run_status.value if isinstance(run_status, AgentRunStatus) else run_status
    if execution and review and review.verdict is ReviewVerdict.PASS:
        return WorkTruth(
            terminal_verdict="succeeded",
            agent_changed_files=agent_changed_files,
            preflight_dirty_files=preflight_dirty_files,
        )
    if normalized_run_status == AgentRunStatus.SUCCEEDED.value and not execution:
        return WorkTruth(terminal_verdict="unknown")

    return WorkTruth(
        terminal_verdict="unknown",
        agent_changed_files=agent_changed_files,
        preflight_dirty_files=preflight_dirty_files,
    )


def current_active_assignment(store: AriadneStore, daemon: DaemonStatusDTO | None = None) -> TicketAssignment | None:
    active = [
        assignment
        for assignment in store.list_assignments()
        if assignment.status in ACTIVE_ASSIGNMENT_STATUSES
    ]
    if active:
        return sorted(active, key=lambda item: item.started_at or item.claimed_at or item.created_at)[-1]

    if daemon is None or daemon.stale is True or not daemon.current_assignment_id:
        return None
    try:
        heartbeat_assignment = store.load_assignment(daemon.current_assignment_id)
    except FileNotFoundError:
        return None
    if heartbeat_assignment.status in ACTIVE_ASSIGNMENT_STATUSES:
        return heartbeat_assignment
    return None


def is_claimable_assignment(assignment: TicketAssignment) -> bool:
    return assignment.status in CLAIMABLE_ASSIGNMENT_STATUSES


def _agent_changed_files(execution: ExecutionResult | None) -> list[str]:
    if execution is None:
        return []
    if execution.blocked or execution.failure_reason is FailureReason.DIRTY_BASE_CHECKOUT:
        return []
    return execution.changed_files


def _preflight_dirty_files(execution: ExecutionResult | None) -> list[str]:
    if execution is None:
        return []
    if execution.failure_reason is not FailureReason.DIRTY_BASE_CHECKOUT:
        return []
    return _files_from_short_status(execution.git_status_before or execution.git_status_after)


def _files_from_short_status(status: str) -> list[str]:
    files: list[str] = []
    for raw_line in status.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path.strip())
    return sorted(set(files))


def _failure_reason_value(reason: FailureReason | None) -> str | None:
    return reason.value if reason else None
