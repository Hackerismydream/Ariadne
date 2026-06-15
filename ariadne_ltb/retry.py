from __future__ import annotations

from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import (
    AssignmentStatus,
    CommentAuthorType,
    CommentKind,
    FailureReason,
    TicketAssignment,
    stable_id,
    utc_now,
)
from ariadne_ltb.storage import AriadneStore


SAFE_RETRY_REASONS = {
    FailureReason.RUNTIME_OFFLINE,
    FailureReason.TIMEOUT,
    FailureReason.COMMAND_UNAVAILABLE,
    FailureReason.REVIEW_FAILED,
}

UNSAFE_RETRY_REASONS = {
    FailureReason.SCOPE_VIOLATION,
    FailureReason.INVALID_RESOURCE,
    FailureReason.RESOURCE_LOCKED,
    FailureReason.UNKNOWN,
    FailureReason.EXTERNAL_EXECUTION_BLOCKED,
}


def is_safe_to_retry(assignment: TicketAssignment) -> bool:
    if assignment.status not in {AssignmentStatus.BLOCKED, AssignmentStatus.FAILED}:
        return False
    if assignment.failure_reason in SAFE_RETRY_REASONS:
        return True
    if assignment.failure_reason in UNSAFE_RETRY_REASONS:
        return False
    return False


def create_retry_assignment(
    store: AriadneStore,
    assignment: TicketAssignment,
    reason: str = "retry requested",
    force: bool = False,
) -> TicketAssignment:
    ticket = store.load_ticket(assignment.ticket_id)
    safe = is_safe_to_retry(assignment)
    if not safe and not force:
        store.append_runtime_event(
            runtime_event(
                ticket,
                assignment.claimed_by_runtime_id or "local",
                "retry",
                "retry_blocked",
                "Ariadne",
                assignment_id=assignment.id,
                failure_reason=assignment.failure_reason,
                metadata={"safe_to_retry": False, "reason": reason},
            )
        )
        msg = f"unsafe retry for {assignment.id}: {assignment.failure_reason}"
        raise ValueError(msg)

    retry = assignment.model_copy(
        deep=True,
        update={
            "id": stable_id(
                "assignment",
                assignment.ticket_id,
                assignment.agent_id,
                "retry",
                assignment.attempt + 1,
                utc_now(),
            ),
            "status": AssignmentStatus.QUEUED,
            "parent_assignment_id": assignment.id,
            "attempt": assignment.attempt + 1,
            "retry_reason": reason,
            "retry_policy": "force" if force else "safe",
            "claimed_by_runtime_id": None,
            "claimed_at": None,
            "started_at": None,
            "ended_at": None,
            "failure_reason": None,
            "blocker": None,
        },
    )
    store.save_assignment(retry)
    store.add_comment(
        ticket,
        CommentAuthorType.SYSTEM,
        "Retry",
        CommentKind.RECOVERY,
        f"Retry created: {retry.id} from {assignment.id} attempt {retry.attempt}.",
        payload_ref=retry.id,
    )
    store.append_runtime_event(
        runtime_event(
            ticket,
            assignment.claimed_by_runtime_id or "local",
            "retry",
            "retry_created",
            "Ariadne",
            assignment_id=retry.id,
            payload_ref=retry.id,
            metadata={
                "parent_assignment_id": assignment.id,
                "force": force,
                "reason": reason,
            },
        )
    )
    return retry
