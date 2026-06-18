from __future__ import annotations

from dataclasses import dataclass

from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import (
    AssignmentStatus,
    BuildTicket,
    CommentAuthorType,
    CommentKind,
    FailureReason,
    TicketAssignment,
    TicketStatus,
)
from ariadne_ltb.storage import AriadneStore


SAFE_RETRY_FAILURE_REASONS = {
    FailureReason.RUNTIME_OFFLINE,
    FailureReason.TIMEOUT,
    FailureReason.COMMAND_UNAVAILABLE,
    FailureReason.REVIEW_FAILED,
}


@dataclass(frozen=True)
class AssignmentFailureResult:
    assignment: TicketAssignment
    ticket: BuildTicket
    comment_id: str
    event_id: str
    retry_recommendation: str


def record_assignment_failure(
    store: AriadneStore,
    ticket: BuildTicket,
    assignment: TicketAssignment,
    status: AssignmentStatus,
    blocker: str,
    failure_reason: FailureReason,
    runtime_id: str,
    actor: str | None = None,
    stage: str = "assignment",
    ticket_status: TicketStatus | None = None,
    metadata: dict | None = None,
) -> AssignmentFailureResult:
    if status is AssignmentStatus.BLOCKED:
        updated_assignment = assignment.mark_blocked(blocker, failure_reason)
        default_ticket_status = TicketStatus.BLOCKED
    elif status is AssignmentStatus.FAILED:
        updated_assignment = assignment.mark_failed(blocker, failure_reason)
        default_ticket_status = TicketStatus.FAILED
    elif status is AssignmentStatus.CANCELLED:
        updated_assignment = assignment.mark_cancelled(blocker, failure_reason)
        default_ticket_status = TicketStatus.CANCELLED
    else:
        msg = f"unsupported assignment failure status: {status.value}"
        raise ValueError(msg)

    store.save_assignment(updated_assignment)
    retry_recommendation = _retry_recommendation(ticket, failure_reason)
    actor_name = actor or updated_assignment.agent_name
    comment = store.add_comment(
        ticket,
        CommentAuthorType.AGENT,
        actor_name,
        CommentKind.BLOCKER,
        (
            f"{actor_name}: {status.value} - {blocker} "
            f"(failure_reason={failure_reason.value}; retry={retry_recommendation})."
        ),
        payload_ref=updated_assignment.id,
        thread_id=updated_assignment.id,
    )
    event = runtime_event(
        ticket,
        runtime_id,
        stage,
        status.value,
        actor_name,
        assignment_id=updated_assignment.id,
        payload_ref=updated_assignment.id,
        failure_reason=failure_reason,
        metadata={
            "blocker": blocker,
            "assignment_status": status.value,
            "retry_recommendation": retry_recommendation,
            **(metadata or {}),
        },
    )
    store.append_runtime_event(event)

    desired_status = ticket_status or default_ticket_status
    latest_ticket = store.load_ticket(ticket.id)
    if latest_ticket.status is not desired_status:
        latest_ticket = latest_ticket.with_status(
            desired_status,
            actor_name,
            f"Assignment {updated_assignment.id} {status.value}: {blocker}",
        )
    latest_ticket = latest_ticket.append_event(
        f"assignment_{status.value}",
        actor_name,
        f"{updated_assignment.id}: {failure_reason.value} - {blocker}",
        payload_ref=updated_assignment.id,
    )
    store.save_ticket(latest_ticket)
    return AssignmentFailureResult(
        assignment=updated_assignment,
        ticket=latest_ticket,
        comment_id=comment.id,
        event_id=event.id,
        retry_recommendation=retry_recommendation,
    )


def _retry_recommendation(ticket: BuildTicket, failure_reason: FailureReason) -> str:
    if failure_reason in SAFE_RETRY_FAILURE_REASONS:
        return f"ari ticket retry {ticket.key}"
    return "human_review_required"
