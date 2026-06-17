from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from ariadne_ltb.failure import record_assignment_failure
from ariadne_ltb.models import (
    AssignmentStatus,
    BacklogUpdate,
    BacklogUpdateTrigger,
    BuildDecision,
    BuildPacket,
    BuildTicket,
    CommentAuthorType,
    CommentKind,
    Evidence,
    ExecutionResult,
    FailureReason,
    ReviewReport,
    ReviewVerdict,
    SourceDocument,
    SourceType,
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


def record_feedback_backlog_updates(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
    memory_record_id: str,
    next_tickets_artifact_path: str,
) -> list[BacklogUpdate]:
    """Record ticket-set deltas caused by one completed ticket run.

    This keeps Ariadne's product loop ticket-centered: execution, review, local
    memory, and codebase observations can update the backlog before the next
    agent is assigned.
    """

    suggestions = _read_next_ticket_suggestions(next_tickets_artifact_path)
    updates = [
        _record_execution_result_update(store, ticket, execution, review),
        _record_review_feedback_update(
            store,
            ticket,
            packet,
            execution,
            review,
            suggestions,
            next_tickets_artifact_path,
        ),
        _record_memory_gap_update(
            store,
            ticket,
            packet,
            execution,
            review,
            suggestions,
            memory_record_id,
            next_tickets_artifact_path,
        ),
        _record_codebase_observation_update(
            store,
            ticket,
            packet,
            execution,
            review,
            suggestions,
            next_tickets_artifact_path,
        ),
    ]
    for update in updates:
        _attach_backlog_update_to_source_ticket(store, ticket.id, update)
    return updates


def downgrade_ticket(
    store: AriadneStore,
    ticket: BuildTicket,
    reason: str,
    new_priority: str = "low",
) -> BacklogUpdate:
    before_priority = ticket.priority
    updated = ticket.append_event("backlog_downgraded", "Backlog", reason)
    updated = updated.model_copy(
        deep=True,
        update={"priority": new_priority, "metadata": updated.metadata | {"downgraded_reason": reason}},
    )
    store.save_ticket(updated)
    now = utc_now()
    update = BacklogUpdate(
        id=stable_id("backlog", BacklogUpdateTrigger.REVIEW_FEEDBACK.value, ticket.id, "downgrade", now),
        trigger_type=BacklogUpdateTrigger.REVIEW_FEEDBACK,
        trigger_ref=ticket.id,
        updated_ticket_ids=[ticket.id],
        rationale=f"Downgraded {ticket.key}: {reason}",
        evidence_refs=[ticket.id],
        ticket_changes=[
            TicketChange(
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                change_type=TicketChangeType.DOWNGRADED,
                reason=reason,
                before_status=ticket.status.value,
                after_status=updated.status.value,
                before_priority=before_priority,
                after_priority=new_priority,
            )
        ],
        created_at=now,
    )
    store.save_backlog_update(update)
    _attach_backlog_update_to_source_ticket(store, ticket.id, update)
    return update


def record_noop_backlog_update(
    store: AriadneStore,
    ticket: BuildTicket,
    trigger_type: BacklogUpdateTrigger,
    reason: str,
    evidence_refs: list[str] | None = None,
    attach_to_ticket: bool = True,
) -> BacklogUpdate:
    now = utc_now()
    update = BacklogUpdate(
        id=stable_id("backlog", trigger_type.value, ticket.id, "noop", reason, now),
        trigger_type=trigger_type,
        trigger_ref=ticket.id,
        rationale=reason,
        evidence_refs=evidence_refs or [ticket.id],
        ticket_changes=[
            TicketChange(
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                change_type=TicketChangeType.NO_OP,
                reason=reason,
                before_status=ticket.status.value,
                after_status=ticket.status.value,
                before_priority=ticket.priority,
                after_priority=ticket.priority,
            )
        ],
        created_at=now,
    )
    store.save_backlog_update(update)
    if attach_to_ticket:
        _attach_backlog_update_to_source_ticket(store, ticket.id, update)
    return update


def _record_execution_result_update(
    store: AriadneStore,
    ticket: BuildTicket,
    execution: ExecutionResult,
    review: ReviewReport,
) -> BacklogUpdate:
    now = utc_now()
    if review.verdict is ReviewVerdict.PASS and execution.exit_code == 0:
        change_type = TicketChangeType.CLOSED
        rationale = f"Execution for {ticket.key} passed review; ticket is closed as done."
        after_status = TicketStatus.DONE.value
    elif execution.blocked or review.verdict is ReviewVerdict.BLOCKED:
        change_type = TicketChangeType.DOWNGRADED
        rationale = f"Execution for {ticket.key} is blocked; ticket remains blocked pending repair."
        after_status = TicketStatus.BLOCKED.value
    else:
        change_type = TicketChangeType.UPDATED
        rationale = f"Execution for {ticket.key} needs follow-up based on reviewer feedback."
        after_status = TicketStatus.NEEDS_FIX.value
    update = BacklogUpdate(
        id=stable_id("backlog", BacklogUpdateTrigger.EXECUTION_RESULT.value, ticket.id, execution.id, now),
        trigger_type=BacklogUpdateTrigger.EXECUTION_RESULT,
        trigger_ref=execution.id,
        updated_ticket_ids=[ticket.id],
        rationale=rationale,
        evidence_refs=[execution.id, review.id],
        ticket_changes=[
            TicketChange(
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                change_type=change_type,
                reason=rationale,
                before_status=ticket.status.value,
                after_status=after_status,
                before_priority=ticket.priority,
                after_priority=ticket.priority,
            )
        ],
        created_at=now,
    )
    store.save_backlog_update(update)
    return update


def _record_review_feedback_update(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
    suggestions: list[dict[str, Any]],
    next_tickets_artifact_path: str,
) -> BacklogUpdate:
    review_suggestions = [
        item for item in suggestions if item.get("source") in {"failed_check", "review"}
    ]
    if not review_suggestions:
        return record_noop_backlog_update(
            store,
            ticket,
            BacklogUpdateTrigger.REVIEW_FEEDBACK,
            f"Reviewer verdict {review.verdict.value} did not require a review-specific backlog change.",
            [review.id, next_tickets_artifact_path],
            attach_to_ticket=False,
        )
    return _record_suggestion_update(
        store,
        ticket,
        packet,
        execution,
        review,
        BacklogUpdateTrigger.REVIEW_FEEDBACK,
        review_suggestions,
        next_tickets_artifact_path,
        "Review feedback generated follow-up backlog decisions.",
    )


def _record_memory_gap_update(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
    suggestions: list[dict[str, Any]],
    memory_record_id: str,
    next_tickets_artifact_path: str,
) -> BacklogUpdate:
    memory_suggestions = [item for item in suggestions if item.get("source") == "memory"]
    if not memory_suggestions:
        return record_noop_backlog_update(
            store,
            ticket,
            BacklogUpdateTrigger.MEMORY_GAP,
            "Memory write-back did not expose a new planner memory gap.",
            [memory_record_id, next_tickets_artifact_path],
            attach_to_ticket=False,
        )
    return _record_suggestion_update(
        store,
        ticket,
        packet,
        execution,
        review,
        BacklogUpdateTrigger.MEMORY_GAP,
        memory_suggestions,
        next_tickets_artifact_path,
        "Memory gap generated follow-up backlog decisions.",
        extra_evidence=[memory_record_id],
    )


def _record_codebase_observation_update(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
    suggestions: list[dict[str, Any]],
    next_tickets_artifact_path: str,
) -> BacklogUpdate:
    codebase_suggestions = [item for item in suggestions if item.get("source") == "changed_file"]
    if not codebase_suggestions:
        return record_noop_backlog_update(
            store,
            ticket,
            BacklogUpdateTrigger.CODEBASE_OBSERVATION,
            "Execution produced no changed-file observation requiring a new ticket.",
            [execution.id, next_tickets_artifact_path],
            attach_to_ticket=False,
        )
    return _record_suggestion_update(
        store,
        ticket,
        packet,
        execution,
        review,
        BacklogUpdateTrigger.CODEBASE_OBSERVATION,
        codebase_suggestions,
        next_tickets_artifact_path,
        "Changed files generated follow-up backlog decisions.",
    )


def _record_suggestion_update(
    store: AriadneStore,
    source_ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
    trigger_type: BacklogUpdateTrigger,
    suggestions: list[dict[str, Any]],
    next_tickets_artifact_path: str,
    rationale: str,
    extra_evidence: list[str] | None = None,
) -> BacklogUpdate:
    changes: list[TicketChange] = []
    created_ticket_ids: list[str] = []
    updated_ticket_ids: list[str] = []
    evidence_refs = [
        source_ticket.id,
        execution.id,
        review.id,
        next_tickets_artifact_path,
        *(extra_evidence or []),
    ]
    for suggestion in suggestions:
        priority = str(suggestion.get("priority") or "medium")
        if priority == "low":
            changes.append(
                TicketChange(
                    ticket_id=source_ticket.id,
                    ticket_key=source_ticket.key,
                    change_type=TicketChangeType.NO_OP,
                    reason=(
                        f"Suggestion retained in next_tickets artifact but not ticketed now: "
                        f"{suggestion.get('title', 'Untitled')}"
                    ),
                    before_status=source_ticket.status.value,
                    after_status=source_ticket.status.value,
                    before_priority=source_ticket.priority,
                    after_priority=source_ticket.priority,
                )
            )
            continue
        generated, change = _create_or_update_followup_ticket(
            store,
            source_ticket,
            packet,
            suggestion,
            trigger_type,
            next_tickets_artifact_path,
        )
        changes.append(change)
        if change.change_type is TicketChangeType.CREATED:
            created_ticket_ids.append(generated.id)
        else:
            updated_ticket_ids.append(generated.id)
        evidence_refs.append(generated.id)
    if created_ticket_ids or updated_ticket_ids:
        updated_ticket_ids.append(source_ticket.id)
        changes.append(
            TicketChange(
                ticket_id=source_ticket.id,
                ticket_key=source_ticket.key,
                change_type=TicketChangeType.UPDATED,
                reason=(
                    f"{trigger_type.value} changed the ticket set for "
                    f"{source_ticket.key}: created={len(created_ticket_ids)} "
                    f"updated={len(updated_ticket_ids) - 1}."
                ),
                before_status=source_ticket.status.value,
                after_status=source_ticket.status.value,
                before_priority=source_ticket.priority,
                after_priority=source_ticket.priority,
            )
        )
    if not changes:
        changes.append(
            TicketChange(
                ticket_id=source_ticket.id,
                ticket_key=source_ticket.key,
                change_type=TicketChangeType.NO_OP,
                reason="All suggestions were intentionally left as artifact-only context.",
                before_status=source_ticket.status.value,
                after_status=source_ticket.status.value,
                before_priority=source_ticket.priority,
                after_priority=source_ticket.priority,
            )
        )
    now = utc_now()
    update = BacklogUpdate(
        id=stable_id("backlog", trigger_type.value, source_ticket.id, next_tickets_artifact_path, now),
        trigger_type=trigger_type,
        trigger_ref=next_tickets_artifact_path,
        created_ticket_ids=created_ticket_ids,
        updated_ticket_ids=updated_ticket_ids,
        rationale=rationale,
        evidence_refs=_dedupe_strings(evidence_refs),
        ticket_changes=changes,
        created_at=now,
    )
    store.save_backlog_update(update)
    return update


def _create_or_update_followup_ticket(
    store: AriadneStore,
    source_ticket: BuildTicket,
    source_packet: BuildPacket,
    suggestion: dict[str, Any],
    trigger_type: BacklogUpdateTrigger,
    next_tickets_artifact_path: str,
) -> tuple[BuildTicket, TicketChange]:
    title = str(suggestion.get("title") or "Untitled follow-up ticket")
    reason = str(suggestion.get("reason") or "Generated from ticket run feedback.")
    generated_ref = stable_id("feedback", source_ticket.id, title)
    existing = _find_generated_ticket(store, source_ticket.id, generated_ref)
    source_doc = _source_document_for_suggestion(
        source_ticket,
        suggestion,
        next_tickets_artifact_path,
        generated_ref,
    )
    store.save_source_document(source_doc)
    before_status = existing.status.value if existing else None
    before_priority = existing.priority if existing else None
    if existing is None:
        ticket = BuildTicket(
            id=stable_id("ticket", generated_ref),
            key=_next_ticket_key(store),
            title=title,
            description=reason,
            source_type=SourceType.REVIEW.value,
            source_ref=next_tickets_artifact_path,
            status=TicketStatus.PLANNING,
            priority=str(suggestion.get("priority") or "medium"),
            owner_agent="Build Lead",
            metadata={
                "source_document_id": source_doc.id,
                "generated_from_ticket_id": source_ticket.id,
                "generated_from_ticket_key": source_ticket.key,
                "generated_suggestion_ref": generated_ref,
                "generated_by_backlog_trigger": trigger_type.value,
            },
        ).append_event(
            "ticket_created",
            "Backlog",
            f"Created from {trigger_type.value} on {source_ticket.key}.",
            payload_ref=next_tickets_artifact_path,
        )
        change_type = TicketChangeType.CREATED
    else:
        ticket = existing.model_copy(
            deep=True,
            update={
                "title": title,
                "description": reason,
                "priority": str(suggestion.get("priority") or existing.priority),
                "source_ref": next_tickets_artifact_path,
                "metadata": existing.metadata
                | {
                    "source_document_id": source_doc.id,
                    "generated_from_ticket_id": source_ticket.id,
                    "generated_from_ticket_key": source_ticket.key,
                    "generated_suggestion_ref": generated_ref,
                    "generated_by_backlog_trigger": trigger_type.value,
                },
            },
        ).append_event(
            "ticket_updated",
            "Backlog",
            f"Updated from {trigger_type.value} on {source_ticket.key}.",
            payload_ref=next_tickets_artifact_path,
        )
        change_type = TicketChangeType.UPDATED
    packet = _build_packet_for_suggestion(ticket, source_packet, source_doc, suggestion)
    store.save_build_packet(packet)
    ticket = ticket.model_copy(deep=True, update={"build_packet_id": packet.id})
    store.save_ticket(ticket)
    return ticket, TicketChange(
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        change_type=change_type,
        reason=reason,
        before_status=before_status,
        after_status=ticket.status.value,
        before_priority=before_priority,
        after_priority=ticket.priority,
    )


def _find_generated_ticket(
    store: AriadneStore,
    source_ticket_id: str,
    generated_ref: str,
) -> BuildTicket | None:
    for ticket in store.list_tickets():
        if (
            ticket.metadata.get("generated_from_ticket_id") == source_ticket_id
            and ticket.metadata.get("generated_suggestion_ref") == generated_ref
        ):
            return ticket
    return None


def _source_document_for_suggestion(
    source_ticket: BuildTicket,
    suggestion: dict[str, Any],
    next_tickets_artifact_path: str,
    generated_ref: str,
) -> SourceDocument:
    title = str(suggestion.get("title") or "Untitled follow-up ticket")
    reason = str(suggestion.get("reason") or "Generated from ticket run feedback.")
    content = json.dumps(suggestion, sort_keys=True)
    return SourceDocument(
        id=stable_id("source", generated_ref),
        source_type=SourceType.REVIEW,
        title=title,
        path_or_url=next_tickets_artifact_path,
        content_hash=sha256(content.encode("utf-8")).hexdigest(),
        summary=f"review source: {reason}",
        metadata={
            "source_ticket_id": source_ticket.id,
            "source_ticket_key": source_ticket.key,
            "suggestion": suggestion,
            "evidence_snippets": [reason],
        },
    )


def _build_packet_for_suggestion(
    ticket: BuildTicket,
    source_packet: BuildPacket,
    source: SourceDocument,
    suggestion: dict[str, Any],
) -> BuildPacket:
    title = str(suggestion.get("title") or ticket.title)
    reason = str(suggestion.get("reason") or ticket.description)
    decision_value = str(suggestion.get("suggested_build_decision") or BuildDecision.CODE_TASK.value)
    try:
        decision = BuildDecision(decision_value)
    except ValueError:
        decision = BuildDecision.CODE_TASK
    affected_modules = list(suggestion.get("affected_modules") or source_packet.affected_modules)
    acceptance_criteria = list(
        suggestion.get("acceptance_criteria") or ["Follow-up ticket has explicit acceptance criteria."]
    )
    return BuildPacket(
        id=stable_id("packet", ticket.id),
        ticket_id=ticket.id,
        source_summary=source.summary,
        insight=reason,
        evidence=[
            Evidence(
                id=stable_id("evidence", source.id, title),
                source_ref=source.path_or_url,
                quote_or_summary=reason[:500],
                location="next_tickets.json",
                confidence=0.78,
            )
        ],
        project_relevance=f"Follow-up generated from {source.metadata.get('source_ticket_key')}.",
        build_decision=decision,
        tasks=[title],
        acceptance_criteria=acceptance_criteria,
        affected_modules=affected_modules,
        risks=["Generated follow-up may need replanning before execution."],
        assumptions=["Backlog update suggestions are local deterministic feedback, not user-approved scope expansion."],
        confidence=0.74,
        metadata={
            "planner_mode": "feedback_backlog_update",
            "generated_from_ticket_id": source.metadata.get("source_ticket_id"),
            "generated_from_ticket_key": source.metadata.get("source_ticket_key"),
        },
    )


def _read_next_ticket_suggestions(path: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    suggestions = payload.get("next_tickets", [])
    return [item for item in suggestions if isinstance(item, dict)]


def _attach_backlog_update_to_source_ticket(
    store: AriadneStore,
    ticket_id: str,
    update: BacklogUpdate,
) -> None:
    current = store.load_ticket(ticket_id)
    updated = current.append_event(
        "backlog_updated",
        "Backlog",
        f"Backlog update recorded: {update.rationale}",
        payload_ref=update.id,
    )
    store.save_ticket(updated)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _next_ticket_key(store: AriadneStore) -> str:
    used = {ticket.key for ticket in store.list_tickets()}
    candidate = 1
    while True:
        key = f"ARI-{candidate:03d}"
        if key not in used:
            return key
        candidate += 1
