from __future__ import annotations

from ariadne_ltb.models import (
    AssignmentStatus,
    BuildTicket,
    ResumePlan,
    ResumeSafety,
    RuntimeEvent,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


TERMINAL_SUCCESS_STAGES = {"planning", "route", "execution", "review", "memory", "next_tickets", "board"}


def runtime_event(
    ticket: BuildTicket | None,
    runtime_id: str,
    stage: str,
    event_type: str,
    actor: str,
    assignment_id: str | None = None,
    run_id: str | None = None,
    payload_ref: str | None = None,
    metadata: dict | None = None,
) -> RuntimeEvent:
    ticket_id = ticket.id if ticket else None
    ticket_key = ticket.key if ticket else None
    idempotency_key = ":".join(
        item
        for item in [
            ticket_id or "no-ticket",
            assignment_id or "no-assignment",
            stage,
            event_type,
            payload_ref or run_id or "event",
        ]
        if item
    )
    return RuntimeEvent(
        id=stable_id("event", idempotency_key),
        ticket_id=ticket_id,
        ticket_key=ticket_key,
        assignment_id=assignment_id,
        run_id=run_id,
        runtime_id=runtime_id,
        stage=stage,
        event_type=event_type,
        actor=actor,
        payload_ref=payload_ref,
        idempotency_key=idempotency_key,
        metadata=metadata or {},
    )


def build_resume_plan(store: AriadneStore, ticket: BuildTicket) -> ResumePlan:
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    events = store.list_runtime_events_for_ticket(ticket.id)
    successful = [event.stage for event in events if event.event_type == "succeeded"]
    last_completed = successful[-1] if successful else None
    current_stage = events[-1].stage if events else None
    next_stage = _next_stage(last_completed)
    reasons: list[str] = []

    if assignment is None:
        safety = ResumeSafety.UNSAFE
        reasons.append("No assignment exists for this ticket.")
        recommended = None
    elif assignment.status is AssignmentStatus.DONE:
        safety = ResumeSafety.NEEDS_HUMAN_REVIEW
        reasons.append("Latest assignment is already done; Ariadne will not duplicate completed work.")
        recommended = None
    elif assignment.status in {AssignmentStatus.QUEUED, AssignmentStatus.BLOCKED}:
        safety = ResumeSafety.SAFE_TO_RESUME
        reasons.append("Assignment is not running and can be picked up by daemon run-once.")
        recommended = "ari daemon run-once"
    else:
        safety = ResumeSafety.NEEDS_HUMAN_REVIEW
        reasons.append(f"Assignment is {assignment.status.value}; conservative recovery requires review.")
        recommended = f"ari ticket resume {ticket.key}"

    return ResumePlan(
        id=stable_id("resume", ticket.id, assignment.id if assignment else "missing", current_stage),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        assignment_id=assignment.id if assignment else None,
        last_completed_stage=last_completed,
        current_stage=current_stage,
        next_stage=next_stage,
        safety=safety,
        reasons=reasons,
        recommended_command=recommended,
    )


def _next_stage(last_completed: str | None) -> str | None:
    ordered = ["planning", "route", "execution", "review", "memory", "next_tickets", "board"]
    if last_completed is None:
        return ordered[0]
    if last_completed not in ordered:
        return None
    index = ordered.index(last_completed)
    if index + 1 >= len(ordered):
        return None
    return ordered[index + 1]
