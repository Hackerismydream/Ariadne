from __future__ import annotations

from ariadne_ltb.models import AssignmentStatus, FailureReason, TicketAssignment
from ariadne_ltb.storage import AriadneStore, is_assignment_lease_expired

RUNNABLE_ASSIGNMENT_STATUSES = {
    AssignmentStatus.QUEUED,
    AssignmentStatus.ROUTED,
    AssignmentStatus.HANDOFF_READY,
    AssignmentStatus.AWAITING_USER_APPROVAL,
    AssignmentStatus.READY_TO_CLAIM,
    AssignmentStatus.CLAIMED,
    AssignmentStatus.RUNNING,
}


def is_claimable_assignment(
    assignment: TicketAssignment,
    *,
    target_project_id: str | None = None,
    allowed_backends: list[str] | None = None,
) -> bool:
    if assignment.status is AssignmentStatus.READY_TO_CLAIM:
        pass
    elif assignment.status is AssignmentStatus.QUEUED and assignment.metadata.get("requeue_reason"):
        pass
    elif assignment.status in {AssignmentStatus.CLAIMED, AssignmentStatus.RUNNING}:
        if not is_assignment_lease_expired(assignment):
            return False
    else:
        return False
    if target_project_id is not None and assignment.metadata.get("target_project_id") != target_project_id:
        return False
    if allowed_backends and assignment.backend_name not in allowed_backends:
        return False
    return True


def current_runnable_assignment(
    store: AriadneStore,
    *,
    ticket_id: str,
    backend_name: str | None,
    exclude_assignment_id: str | None = None,
) -> TicketAssignment | None:
    candidates = [
        assignment
        for assignment in store.list_assignments_for_ticket(ticket_id)
        if assignment.id != exclude_assignment_id
        and assignment.backend_name == backend_name
        and assignment.status in RUNNABLE_ASSIGNMENT_STATUSES
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item.attempt, item.created_at, item.id))[-1]


def has_persisted_runtime_authorization(assignment: TicketAssignment) -> bool:
    return bool(
        assignment.metadata.get("runtime_authorization_id")
        or assignment.metadata.get("confirmation_id")
        or assignment.metadata.get("authorization_id")
    )


def canonicalize_duplicate_runnable_assignments(
    store: AriadneStore,
    *,
    ticket_id: str | None = None,
) -> list[TicketAssignment]:
    assignments = [
        assignment
        for assignment in store.list_assignments()
        if (ticket_id is None or assignment.ticket_id == ticket_id)
        and assignment.status in RUNNABLE_ASSIGNMENT_STATUSES
    ]
    grouped: dict[tuple[str, str | None], list[TicketAssignment]] = {}
    for assignment in assignments:
        grouped.setdefault((assignment.ticket_id, assignment.backend_name), []).append(assignment)

    cancelled: list[TicketAssignment] = []
    for duplicates in grouped.values():
        if len(duplicates) < 2:
            continue
        keep = sorted(duplicates, key=lambda item: (item.attempt, item.created_at, item.id))[-1]
        for assignment in duplicates:
            if assignment.id == keep.id:
                continue
            updated = assignment.mark_cancelled(
                blocker=f"Duplicate runnable assignment superseded by {keep.id}.",
                failure_reason=FailureReason.USER_CANCELLED,
            )
            updated = updated.model_copy(
                deep=True,
                update={
                    "metadata": updated.metadata
                    | {
                        "superseded_by_assignment_id": keep.id,
                        "duplicate_runnable_cancelled": True,
                    }
                },
            )
            store.save_assignment(updated)
            cancelled.append(updated)
    return cancelled


def existing_child_retry(store: AriadneStore, parent_assignment_id: str) -> TicketAssignment | None:
    candidates = [
        assignment
        for assignment in store.list_assignments()
        if assignment.parent_assignment_id == parent_assignment_id
        and assignment.status in RUNNABLE_ASSIGNMENT_STATUSES
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item.attempt, item.created_at, item.id))[-1]
