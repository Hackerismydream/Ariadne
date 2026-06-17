from __future__ import annotations

from pathlib import Path

from ariadne_ltb.failure import record_assignment_failure
from ariadne_ltb.models import (
    AssignmentStatus,
    BacklogUpdate,
    BacklogUpdateTrigger,
    BuildTicket,
    CommentAuthorType,
    CommentKind,
    FailureReason,
    TicketChange,
    TicketChangeType,
    TicketStatus,
    stable_id,
    utc_now,
)
from ariadne_ltb.storage import AriadneStore


def record_source_ingest_backlog_update(
    store: AriadneStore,
    tickets: list[BuildTicket],
    changes: list[TicketChange],
    evidence_refs: list[str],
    source_paths: list[Path],
) -> BacklogUpdate:
    created_ticket_ids = [
        change.ticket_id for change in changes if change.change_type is TicketChangeType.CREATED
    ]
    updated_ticket_ids = [
        change.ticket_id for change in changes if change.change_type is TicketChangeType.UPDATED
    ]
    now = utc_now()
    update = BacklogUpdate(
        id=stable_id(
            "backlog",
            BacklogUpdateTrigger.SOURCE_INGEST.value,
            ",".join(sorted(str(path.resolve()) for path in source_paths)),
            now,
        ),
        trigger_type=BacklogUpdateTrigger.SOURCE_INGEST,
        trigger_ref=", ".join(str(path.resolve()) for path in source_paths),
        created_ticket_ids=created_ticket_ids,
        updated_ticket_ids=updated_ticket_ids,
        rationale=(
            f"Ingested {len(source_paths)} source(s); created "
            f"{len(created_ticket_ids)} ticket(s) and updated {len(updated_ticket_ids)} ticket(s)."
        ),
        evidence_refs=evidence_refs,
        ticket_changes=changes,
        created_at=now,
    )
    store.save_backlog_update(update)
    for ticket in tickets:
        updated_ticket = store.load_ticket(ticket.id).append_event(
            "backlog_updated",
            "Backlog",
            f"Backlog update recorded: {update.rationale}",
            payload_ref=update.id,
        )
        store.save_ticket(updated_ticket)
    return update


def supersede_ticket(store: AriadneStore, ticket: BuildTicket, reason: str) -> BacklogUpdate:
    previous_status = ticket.status.value
    updated = ticket.with_status(
        TicketStatus.SUPERSEDED,
        "Backlog",
        f"Ticket superseded: {reason}",
    ).append_event(
        "backlog_updated",
        "Backlog",
        f"Superseded by backlog update: {reason}",
    )
    updated = updated.model_copy(
        deep=True,
        update={"metadata": updated.metadata | {"superseded_reason": reason}},
    )
    store.save_ticket(updated)
    for assignment in store.list_assignments_for_ticket(updated.id):
        if not assignment.is_terminal:
            record_assignment_failure(
                store,
                updated,
                assignment,
                AssignmentStatus.CANCELLED,
                f"Ticket superseded: {reason}",
                FailureReason.USER_CANCELLED,
                "local",
                actor="Backlog",
                stage="assignment",
                ticket_status=TicketStatus.SUPERSEDED,
            )
    store.add_comment(
        updated,
        CommentAuthorType.SYSTEM,
        "Backlog",
        CommentKind.PROGRESS,
        f"Ticket superseded: {reason}",
    )
    now = utc_now()
    update = BacklogUpdate(
        id=stable_id("backlog", BacklogUpdateTrigger.REVIEW_FEEDBACK.value, ticket.id, reason, now),
        trigger_type=BacklogUpdateTrigger.REVIEW_FEEDBACK,
        trigger_ref=ticket.id,
        superseded_ticket_ids=[ticket.id],
        rationale=f"Superseded {ticket.key}: {reason}",
        evidence_refs=[ticket.id],
        ticket_changes=[
            TicketChange(
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                change_type=TicketChangeType.SUPERSEDED,
                reason=reason,
                before_status=previous_status,
                after_status=TicketStatus.SUPERSEDED.value,
                before_priority=ticket.priority,
                after_priority=updated.priority,
            )
        ],
        created_at=now,
    )
    store.save_backlog_update(update)
    updated = store.load_ticket(ticket.id).append_event(
        "backlog_updated",
        "Backlog",
        f"Backlog update recorded: {update.rationale}",
        payload_ref=update.id,
    )
    store.save_ticket(updated)
    return update
