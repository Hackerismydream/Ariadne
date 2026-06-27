from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from ariadne_ltb.failure import record_assignment_failure
from ariadne_ltb.models import (
    AssignmentStatus,
    BacklogConflict,
    BacklogConflictType,
    BacklogOperation,
    BacklogOperationType,
    BacklogPreview,
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


@dataclass(frozen=True)
class BacklogApplyResult:
    preview: BacklogPreview
    update: BacklogUpdate | None
    already_applied: bool = False


def generate_source_backlog_preview(store: AriadneStore, source_paths: list[Path]) -> BacklogPreview:
    from ariadne_ltb.ingest import (
        _dedupe_paths,
        _ticket_source_path_key,
        source_document_from_path,
        ticket_from_source,
    )

    paths = _dedupe_paths(source_paths)
    fingerprint = ticket_backlog_fingerprint(store)
    source_documents = [source_document_from_path(path) for path in sorted(paths)]
    idempotency_key = stable_id(
        "backlog_preview_key",
        BacklogUpdateTrigger.SOURCE_INGEST.value,
        fingerprint,
        ",".join(f"{document.path_or_url}:{document.content_hash}" for document in source_documents),
    )
    preview_id = stable_id("backlog_preview", idempotency_key)
    existing = _load_existing_preview(store, preview_id)
    if existing:
        return existing

    existing_by_source = {
        ticket.metadata.get("source_document_id"): ticket for ticket in store.list_tickets()
    }
    existing_by_path = {
        source_path: ticket
        for ticket in store.list_tickets()
        if (source_path := _ticket_source_path_key(ticket)) is not None
    }
    operations: list[BacklogOperation] = []
    next_index = 1
    for document in source_documents:
        existing_ticket = existing_by_source.get(document.id) or existing_by_path.get(document.path_or_url)
        if existing_ticket:
            operations.append(
                BacklogOperation(
                    id=stable_id("backlog_op", preview_id, document.id, "update"),
                    operation_type=BacklogOperationType.UPDATE_TICKET,
                    ticket_id=existing_ticket.id,
                    ticket_key=existing_ticket.key,
                    title=existing_ticket.title,
                    description=document.summary,
                    source_type=document.source_type.value,
                    source_ref=document.path_or_url,
                    priority=existing_ticket.priority,
                    status=existing_ticket.status,
                    reason=f"Update {existing_ticket.key} from source: {document.title}.",
                    metadata={"source_document": document.model_dump(mode="json")},
                )
            )
            continue
        ticket_key, next_index = _next_preview_ticket_key(store, operations, start_index=next_index)
        ticket = ticket_from_source(document, ticket_key)
        operations.append(
            BacklogOperation(
                id=stable_id("backlog_op", preview_id, document.id, "add"),
                operation_type=BacklogOperationType.ADD_TICKET,
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                title=ticket.title,
                description=ticket.description,
                source_type=ticket.source_type,
                source_ref=ticket.source_ref,
                priority=ticket.priority,
                status=TicketStatus.PLANNING,
                reason=f"Create {ticket.key} from source: {document.title}.",
                metadata={
                    "source_document": document.model_dump(mode="json"),
                    "owner_agent": ticket.owner_agent,
                },
            )
        )
    preview = BacklogPreview(
        id=preview_id,
        trigger_type=BacklogUpdateTrigger.SOURCE_INGEST,
        trigger_ref=", ".join(document.path_or_url for document in source_documents),
        idempotency_key=idempotency_key,
        base_ticket_fingerprint=fingerprint,
        operations=operations,
        conflicts=_detect_preview_conflicts(store, operations),
        rationale=(
            f"Previewed {len(operations)} backlog operation(s) from "
            f"{len(source_documents)} source(s)."
        ),
        evidence_refs=[document.id for document in source_documents],
    )
    store.save_backlog_preview(preview)
    return preview


def generate_review_feedback_preview(
    store: AriadneStore,
    ticket: BuildTicket,
    review_report: ReviewReport,
) -> BacklogPreview:
    fingerprint = ticket_backlog_fingerprint(store)
    idempotency_key = stable_id(
        "backlog_preview_key",
        BacklogUpdateTrigger.REVIEW_FEEDBACK.value,
        fingerprint,
        ticket.id,
        review_report.id,
        review_report.verdict.value,
        "|".join(review_report.failed_checks),
        "|".join(review_report.warnings),
        "|".join(review_report.required_fixes),
    )
    preview_id = stable_id("backlog_preview", idempotency_key)
    existing = _load_existing_preview(store, preview_id)
    if existing:
        return existing

    operations: list[BacklogOperation] = []
    if review_report.verdict is ReviewVerdict.PASS:
        operations.append(
            BacklogOperation(
                id=stable_id("backlog_op", preview_id, ticket.id, "review_promote"),
                operation_type=BacklogOperationType.PROMOTE_TICKET,
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                status=TicketStatus.DONE,
                reason=f"Promote {ticket.key} after passing review {review_report.id}.",
                metadata={"review_report_id": review_report.id},
            )
        )
    else:
        operations.append(
            BacklogOperation(
                id=stable_id("backlog_op", preview_id, ticket.id, "review_defer"),
                operation_type=BacklogOperationType.DEFER_TICKET,
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                reason=f"Defer {ticket.key} because review {review_report.id} did not pass.",
                metadata={
                    "review_report_id": review_report.id,
                    "failed_checks": review_report.failed_checks,
                    "warnings": review_report.warnings,
                },
            )
        )
        next_index = 1
        for index, fix in enumerate(review_report.required_fixes, start=1):
            ticket_key, next_index = _next_preview_ticket_key(store, operations, start_index=next_index)
            operations.append(
                BacklogOperation(
                    id=stable_id("backlog_op", preview_id, ticket.id, "review_fix", index, fix),
                    operation_type=BacklogOperationType.ADD_TICKET,
                    ticket_id=stable_id("ticket", ticket.id, review_report.id, "fix", index),
                    ticket_key=ticket_key,
                    title=f"Fix review issue for {ticket.key}: {fix[:72]}",
                    description=fix,
                    source_type=SourceType.REVIEW.value,
                    source_ref=review_report.id,
                    priority=ticket.priority,
                    status=TicketStatus.PLANNING,
                    reason=f"Create follow-up from review required fix: {fix}",
                    metadata={
                        "source_ticket_id": ticket.id,
                        "source_ticket_key": ticket.key,
                        "review_report_id": review_report.id,
                    },
                )
            )

    preview = BacklogPreview(
        id=preview_id,
        trigger_type=BacklogUpdateTrigger.REVIEW_FEEDBACK,
        trigger_ref=review_report.id,
        idempotency_key=idempotency_key,
        base_ticket_fingerprint=fingerprint,
        operations=operations,
        conflicts=_detect_preview_conflicts(store, operations),
        rationale=f"Previewed backlog changes from review {review_report.id} for {ticket.key}.",
        evidence_refs=[review_report.id, ticket.id],
    )
    store.save_backlog_preview(preview)
    return preview


def generate_execution_feedback_preview(
    store: AriadneStore,
    ticket: BuildTicket,
    execution_result: ExecutionResult,
) -> BacklogPreview:
    fingerprint = ticket_backlog_fingerprint(store)
    idempotency_key = stable_id(
        "backlog_preview_key",
        BacklogUpdateTrigger.EXECUTION_RESULT.value,
        fingerprint,
        ticket.id,
        execution_result.id,
        execution_result.exit_code,
        execution_result.test_exit_code,
        execution_result.blocked,
        execution_result.block_reason,
        execution_result.failure_reason.value if execution_result.failure_reason else "",
        "|".join(execution_result.changed_files),
        "|".join(execution_result.warnings),
    )
    preview_id = stable_id("backlog_preview", idempotency_key)
    existing = _load_existing_preview(store, preview_id)
    if existing:
        return existing

    execution_passed = (
        not execution_result.blocked
        and execution_result.exit_code == 0
        and (execution_result.test_exit_code is None or execution_result.test_exit_code == 0)
    )
    if execution_passed:
        operations = [
            BacklogOperation(
                id=stable_id("backlog_op", preview_id, ticket.id, "execution_promote"),
                operation_type=BacklogOperationType.PROMOTE_TICKET,
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                status=TicketStatus.REVIEWING,
                reason=f"Promote {ticket.key} after successful execution {execution_result.id}.",
                metadata={
                    "execution_result_id": execution_result.id,
                    "changed_files": execution_result.changed_files,
                },
            )
        ]
    else:
        reason = execution_result.block_reason or (
            f"execution exit={execution_result.exit_code} test_exit={execution_result.test_exit_code}"
        )
        ticket_key, _ = _next_preview_ticket_key(store, [], start_index=1)
        operations = [
            BacklogOperation(
                id=stable_id("backlog_op", preview_id, ticket.id, "execution_defer"),
                operation_type=BacklogOperationType.DEFER_TICKET,
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                reason=f"Defer {ticket.key} after failed execution {execution_result.id}: {reason}.",
                metadata={
                    "execution_result_id": execution_result.id,
                    "failure_reason": (
                        execution_result.failure_reason.value
                        if execution_result.failure_reason
                        else None
                    ),
                    "changed_files": execution_result.changed_files,
                    "warnings": execution_result.warnings,
                },
            ),
            BacklogOperation(
                id=stable_id("backlog_op", preview_id, ticket.id, "execution_repair"),
                operation_type=BacklogOperationType.ADD_TICKET,
                ticket_id=stable_id("ticket", ticket.id, execution_result.id, "repair"),
                ticket_key=ticket_key,
                title=f"Repair execution failure for {ticket.key}",
                description=reason,
                source_type=SourceType.REVIEW.value,
                source_ref=execution_result.id,
                priority=ticket.priority,
                status=TicketStatus.PLANNING,
                reason=f"Create repair ticket from failed execution: {reason}",
                metadata={
                    "source_ticket_id": ticket.id,
                    "source_ticket_key": ticket.key,
                    "execution_result_id": execution_result.id,
                    "failure_reason": (
                        execution_result.failure_reason.value
                        if execution_result.failure_reason
                        else None
                    ),
                },
            ),
        ]

    preview = BacklogPreview(
        id=preview_id,
        trigger_type=BacklogUpdateTrigger.EXECUTION_RESULT,
        trigger_ref=execution_result.id,
        idempotency_key=idempotency_key,
        base_ticket_fingerprint=fingerprint,
        operations=operations,
        conflicts=_detect_preview_conflicts(store, operations),
        rationale=f"Previewed backlog changes from execution {execution_result.id} for {ticket.key}.",
        evidence_refs=[execution_result.id, ticket.id],
    )
    store.save_backlog_preview(preview)
    return preview


def generate_memory_gap_preview(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
    memory_record_id: str,
    next_tickets_artifact_path: str,
) -> BacklogPreview:
    suggestions = [
        item for item in _read_next_ticket_suggestions(next_tickets_artifact_path)
        if item.get("source") == "memory"
    ]
    return _generate_suggestion_feedback_preview(
        store,
        ticket,
        packet,
        execution,
        review,
        BacklogUpdateTrigger.MEMORY_GAP,
        trigger_ref=memory_record_id,
        suggestions=suggestions,
        next_tickets_artifact_path=next_tickets_artifact_path,
        rationale=f"Previewed memory-gap backlog changes for {ticket.key}.",
        no_suggestions_reason="Memory write-back did not expose a new planner memory gap.",
        evidence_refs=[ticket.id, execution.id, review.id, memory_record_id, next_tickets_artifact_path],
    )


def generate_codebase_observation_preview(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
    next_tickets_artifact_path: str,
) -> BacklogPreview:
    suggestions = [
        item for item in _read_next_ticket_suggestions(next_tickets_artifact_path)
        if item.get("source") == "changed_file"
    ]
    return _generate_suggestion_feedback_preview(
        store,
        ticket,
        packet,
        execution,
        review,
        BacklogUpdateTrigger.CODEBASE_OBSERVATION,
        trigger_ref=execution.id,
        suggestions=suggestions,
        next_tickets_artifact_path=next_tickets_artifact_path,
        rationale=f"Previewed codebase-observation backlog changes for {ticket.key}.",
        no_suggestions_reason="Execution produced no changed-file observation requiring a new ticket.",
        evidence_refs=[ticket.id, execution.id, review.id, next_tickets_artifact_path],
    )


def apply_backlog_preview(store: AriadneStore, preview_id: str) -> BacklogApplyResult:
    from ariadne_ltb.ingest import build_packet_from_source

    preview = store.load_backlog_preview(preview_id)
    if preview.applied_update_id:
        return BacklogApplyResult(
            preview=preview,
            update=_find_backlog_update(store, preview.applied_update_id),
            already_applied=True,
        )
    if preview.conflicts:
        msg = f"unresolved_conflicts: {', '.join(conflict.conflict_type.value for conflict in preview.conflicts)}"
        raise ValueError(msg)
    current_fingerprint = ticket_backlog_fingerprint(store)
    if current_fingerprint != preview.base_ticket_fingerprint:
        msg = "stale_preview: ticket backlog changed after this preview was created"
        raise ValueError(msg)
    _validate_preview_operations_for_apply(store, preview)

    created_ticket_ids: list[str] = []
    updated_ticket_ids: list[str] = []
    superseded_ticket_ids: list[str] = []
    ticket_changes: list[TicketChange] = []
    touched_ticket_ids: list[str] = []
    for operation in preview.operations:
        before_status: str | None = None
        before_priority: str | None = None
        if operation.operation_type is BacklogOperationType.ADD_TICKET:
            document_payload = operation.metadata.get("source_document")
            document = SourceDocument.model_validate(document_payload) if document_payload else None
            if document:
                store.save_source_document(document)
            ticket = BuildTicket(
                id=operation.ticket_id or stable_id("ticket", document.id if document else operation.id),
                key=operation.ticket_key or "ARI-000",
                title=operation.title or (document.title if document else "Backlog follow-up"),
                description=operation.description or (document.summary if document else operation.reason),
                source_type=operation.source_type or (document.source_type.value if document else "review"),
                source_ref=operation.source_ref or (document.path_or_url if document else operation.id),
                status=operation.status or TicketStatus.PLANNING,
                priority=operation.priority or "medium",
                owner_agent=str(operation.metadata.get("owner_agent") or "Build Lead"),
                metadata=_ticket_metadata_for_operation(operation, document),
            ).append_event(
                "backlog_preview_applied",
                "Backlog",
                f"Applied preview operation: {operation.reason}",
                payload_ref=preview.id,
            )
            if document:
                packet = _build_packet_from_preview_operation(
                    ticket,
                    document,
                    operation,
                    build_packet_from_source,
                )
                store.save_build_packet(packet)
                ticket = ticket.model_copy(update={"build_packet_id": packet.id})
            store.save_ticket(ticket)
            created_ticket_ids.append(ticket.id)
            touched_ticket_ids.append(ticket.id)
            change_type = TicketChangeType.CREATED
        elif operation.operation_type is BacklogOperationType.UPDATE_TICKET:
            if operation.ticket_id is None:
                msg = f"operation {operation.id} missing ticket_id"
                raise ValueError(msg)
            ticket = store.load_ticket(operation.ticket_id)
            before_status = ticket.status.value
            before_priority = ticket.priority
            document = SourceDocument.model_validate(operation.metadata["source_document"])
            store.save_source_document(document)
            ticket = ticket.model_copy(
                deep=True,
                update={
                    "title": operation.title or ticket.title,
                    "description": operation.description or ticket.description,
                    "source_type": operation.source_type or ticket.source_type,
                    "source_ref": operation.source_ref or ticket.source_ref,
                    "priority": operation.priority or ticket.priority,
                    "metadata": ticket.metadata | _ticket_metadata_for_operation(operation, document),
                },
            ).append_event(
                "backlog_preview_applied",
                "Backlog",
                f"Applied preview operation: {operation.reason}",
                payload_ref=preview.id,
            )
            packet = _build_packet_from_preview_operation(
                ticket,
                document,
                operation,
                build_packet_from_source,
            )
            store.save_build_packet(packet)
            ticket = ticket.model_copy(update={"build_packet_id": packet.id})
            store.save_ticket(ticket)
            updated_ticket_ids.append(ticket.id)
            touched_ticket_ids.append(ticket.id)
            change_type = TicketChangeType.UPDATED
        elif operation.operation_type is BacklogOperationType.SUPERSEDE_TICKET:
            if operation.ticket_id is None:
                msg = f"operation {operation.id} missing ticket_id"
                raise ValueError(msg)
            ticket = store.load_ticket(operation.ticket_id)
            before_status = ticket.status.value
            before_priority = ticket.priority
            ticket = ticket.with_status(TicketStatus.SUPERSEDED, "Backlog", operation.reason)
            store.save_ticket(ticket)
            superseded_ticket_ids.append(ticket.id)
            touched_ticket_ids.append(ticket.id)
            change_type = TicketChangeType.SUPERSEDED
        elif operation.operation_type is BacklogOperationType.NO_OP:
            if operation.ticket_id is None:
                msg = f"operation {operation.id} missing ticket_id"
                raise ValueError(msg)
            current_ticket = store.load_ticket(operation.ticket_id)
            before_status = current_ticket.status.value
            before_priority = current_ticket.priority
            ticket = current_ticket.append_event(
                "backlog_preview_noop",
                "Backlog",
                operation.reason,
                payload_ref=preview.id,
            )
            store.save_ticket(ticket)
            touched_ticket_ids.append(ticket.id)
            change_type = TicketChangeType.NO_OP
        else:
            if operation.ticket_id is None:
                msg = f"operation {operation.id} missing ticket_id"
                raise ValueError(msg)
            ticket = store.load_ticket(operation.ticket_id)
            before_status = ticket.status.value
            before_priority = ticket.priority
            if operation.operation_type is BacklogOperationType.DEFER_TICKET:
                ticket = ticket.with_status(TicketStatus.BLOCKED, "Backlog", operation.reason)
                change_type = TicketChangeType.DOWNGRADED
            else:
                promoted_status = operation.status or TicketStatus.READY_FOR_EXECUTION
                ticket = ticket.with_status(
                    promoted_status,
                    "Backlog",
                    operation.reason,
                )
                change_type = (
                    TicketChangeType.CLOSED
                    if promoted_status is TicketStatus.DONE
                    else TicketChangeType.UPDATED
                )
            store.save_ticket(ticket)
            updated_ticket_ids.append(ticket.id)
            touched_ticket_ids.append(ticket.id)
        ticket_changes.append(
            TicketChange(
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                change_type=change_type,
                reason=operation.reason,
                before_status=before_status,
                after_status=ticket.status.value,
                before_priority=before_priority,
                after_priority=ticket.priority,
            )
        )

    now = utc_now()
    update = BacklogUpdate(
        id=stable_id("backlog", preview.id, "applied"),
        trigger_type=preview.trigger_type,
        trigger_ref=preview.id,
        created_ticket_ids=created_ticket_ids,
        updated_ticket_ids=updated_ticket_ids,
        superseded_ticket_ids=superseded_ticket_ids,
        rationale=f"Applied backlog preview {preview.id}.",
        evidence_refs=[preview.id, *preview.evidence_refs],
        ticket_changes=ticket_changes,
        created_at=now,
    )
    store.save_backlog_update(update)
    for ticket_id in touched_ticket_ids:
        store.save_ticket(
            store.load_ticket(ticket_id).append_event(
                "backlog_updated",
                "Backlog",
                f"Backlog update recorded: {update.rationale}",
                payload_ref=update.id,
            )
        )
    preview = preview.model_copy(update={"applied_at": now, "applied_update_id": update.id})
    store.save_backlog_preview(preview)
    return BacklogApplyResult(preview=preview, update=update)


def ticket_backlog_fingerprint(store: AriadneStore) -> str:
    payload = [
        {
            "id": ticket.id,
            "key": ticket.key,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status.value,
            "priority": ticket.priority,
            "source_ref": ticket.source_ref,
            "source_type": ticket.source_type,
            "build_packet_id": ticket.build_packet_id,
            "metadata": ticket.metadata,
            "updated_at": ticket.updated_at,
            "event_log_size": len(ticket.event_log),
        }
        for ticket in store.list_tickets()
    ]
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _load_existing_preview(store: AriadneStore, preview_id: str) -> BacklogPreview | None:
    path = store.backlog_previews_dir / f"{preview_id}.json"
    if not path.exists():
        return None
    return store.load_backlog_preview(preview_id)


def _find_backlog_update(store: AriadneStore, update_id: str) -> BacklogUpdate | None:
    for update in store.list_backlog_updates():
        if update.id == update_id:
            return update
    return None


def _ticket_metadata_for_operation(operation: BacklogOperation, document: SourceDocument | None) -> dict[str, Any]:
    metadata = dict(operation.metadata)
    metadata.pop("source_document", None)
    metadata.pop("source_packet", None)
    metadata.pop("suggestion", None)
    if document:
        metadata |= {
            "source_document_id": document.id,
            "source_content_hash": document.content_hash,
        }
    return metadata


def _build_packet_from_preview_operation(
    ticket: BuildTicket,
    document: SourceDocument,
    operation: BacklogOperation,
    fallback_builder: Any,
) -> BuildPacket:
    source_packet_payload = operation.metadata.get("source_packet")
    suggestion = operation.metadata.get("suggestion")
    if source_packet_payload and isinstance(suggestion, dict):
        return _build_packet_for_suggestion(
            ticket,
            BuildPacket.model_validate(source_packet_payload),
            document,
            suggestion,
        )
    if operation.metadata.get("acceptance_criteria") or operation.metadata.get("affected_modules"):
        decision_value = str(operation.metadata.get("build_decision") or BuildDecision.CODE_TASK.value)
        try:
            decision = BuildDecision(decision_value)
        except ValueError:
            decision = BuildDecision.CODE_TASK
        return BuildPacket(
            id=stable_id("packet", ticket.id),
            ticket_id=ticket.id,
            source_summary=document.summary,
            insight=operation.reason,
            evidence=[
                Evidence(
                    id=stable_id("evidence", ticket.id, document.id, str(index), str(item)),
                    source_ref=document.id,
                    quote_or_summary=str(item),
                    location=document.path_or_url,
                    confidence=0.8,
                )
                for index, item in enumerate((document.metadata.get("evidence_snippets") or [operation.reason])[:5])
            ],
            project_relevance="Generated from the active Web Workbench goal and selected external knowledge.",
            build_decision=decision,
            tasks=[operation.title or ticket.title],
            acceptance_criteria=[str(item) for item in operation.metadata.get("acceptance_criteria", [])],
            affected_modules=[str(item) for item in operation.metadata.get("affected_modules", [])],
            risks=["Generated issue needs normal review before real external execution."],
            assumptions=["The target project path registered in Workbench is the intended build workspace."],
            metadata={
                "source_document_id": document.id,
                "preview_operation_id": operation.id,
                "target_project_id": operation.metadata.get("target_project_id"),
                "project_version_id": operation.metadata.get("project_version_id"),
                "target_version_label": operation.metadata.get("target_version_label"),
                "target_project_label": operation.metadata.get("target_project_label"),
                "target_repo_path": operation.metadata.get("target_repo_path"),
                "source_document_ids": operation.metadata.get("source_document_ids", []),
                "source_artifact_ids": operation.metadata.get("source_artifact_ids", []),
                "evidence_refs": operation.metadata.get("evidence_refs", []),
                "build_context_id": operation.metadata.get("build_context_id"),
            },
        )
    return fallback_builder(ticket, document)


def _validate_preview_operations_for_apply(store: AriadneStore, preview: BacklogPreview) -> None:
    existing_tickets = store.list_tickets()
    existing_ids = {ticket.id for ticket in existing_tickets}
    existing_keys = {ticket.key for ticket in existing_tickets}
    add_ids: set[str] = set()
    add_keys: set[str] = set()
    for operation in preview.operations:
        if operation.operation_type is BacklogOperationType.ADD_TICKET:
            if operation.ticket_id and operation.ticket_id in existing_ids:
                msg = f"preview_operation_conflict: ticket id already exists: {operation.ticket_id}"
                raise ValueError(msg)
            if operation.ticket_key and operation.ticket_key in existing_keys:
                msg = f"preview_operation_conflict: ticket key already exists: {operation.ticket_key}"
                raise ValueError(msg)
            if operation.ticket_id and operation.ticket_id in add_ids:
                msg = f"preview_operation_conflict: duplicate added ticket id: {operation.ticket_id}"
                raise ValueError(msg)
            if operation.ticket_key and operation.ticket_key in add_keys:
                msg = f"preview_operation_conflict: duplicate added ticket key: {operation.ticket_key}"
                raise ValueError(msg)
            if operation.ticket_id:
                add_ids.add(operation.ticket_id)
            if operation.ticket_key:
                add_keys.add(operation.ticket_key)
            continue
        if operation.ticket_id is None:
            msg = f"operation {operation.id} missing ticket_id"
            raise ValueError(msg)
        if operation.ticket_id not in existing_ids:
            msg = f"preview_operation_conflict: ticket id not found: {operation.ticket_id}"
            raise ValueError(msg)


def _detect_preview_conflicts(
    store: AriadneStore,
    operations: list[BacklogOperation],
) -> list[BacklogConflict]:
    conflicts: list[BacklogConflict] = []
    by_target: dict[str, list[BacklogOperation]] = {}
    for operation in operations:
        target = operation.ticket_id or operation.source_ref or operation.id
        if operation.operation_type is not BacklogOperationType.NO_OP:
            by_target.setdefault(target, []).append(operation)
        if (
            operation.ticket_id
            and operation.operation_type is not BacklogOperationType.SUPERSEDE_TICKET
            and _target_is_superseded(store, operation.ticket_id)
        ):
            conflicts.append(
                BacklogConflict(
                    conflict_type=BacklogConflictType.SUPERSEDED_TARGET,
                    message=(
                        f"Operation {operation.id} targets superseded ticket "
                        f"{operation.ticket_key or operation.ticket_id}."
                    ),
                    operation_ids=[operation.id],
                    evidence_refs=[operation.ticket_id],
                    resolution_options=[
                        "Create a new follow-up ticket instead of mutating the superseded ticket.",
                        "Regenerate the preview from the ticket that superseded this work.",
                        "Keep the ticket superseded and archive this feedback.",
                    ],
                )
            )
    for target, target_operations in by_target.items():
        if len(target_operations) > 1:
            conflicts.append(
                BacklogConflict(
                    conflict_type=BacklogConflictType.DUPLICATE_OPERATION,
                    message=f"Multiple backlog operations target {target}.",
                    operation_ids=[operation.id for operation in target_operations],
                    evidence_refs=[target],
                    resolution_options=[
                        "Split the operations into separate previews and apply one at a time.",
                        "Keep the most specific operation and regenerate the preview.",
                        "Resolve manually before applying because apply refuses conflicted previews.",
                    ],
                )
            )
    return conflicts


def _next_preview_ticket_key(
    store: AriadneStore,
    operations: list[BacklogOperation],
    start_index: int,
) -> tuple[str, int]:
    used_keys = {ticket.key for ticket in store.list_tickets()}
    used_keys.update(
        operation.ticket_key
        for operation in operations
        if operation.operation_type is BacklogOperationType.ADD_TICKET and operation.ticket_key
    )
    index = start_index
    while True:
        key = f"ARI-{index:03d}"
        if key not in used_keys:
            return key, index + 1
        index += 1


def _generate_suggestion_feedback_preview(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
    trigger_type: BacklogUpdateTrigger,
    trigger_ref: str,
    suggestions: list[dict[str, Any]],
    next_tickets_artifact_path: str,
    rationale: str,
    no_suggestions_reason: str,
    evidence_refs: list[str],
) -> BacklogPreview:
    fingerprint = ticket_backlog_fingerprint(store)
    suggestions_hash = sha256(
        json.dumps(suggestions, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    idempotency_key = stable_id(
        "backlog_preview_key",
        trigger_type.value,
        fingerprint,
        ticket.id,
        execution.id,
        review.id,
        trigger_ref,
        next_tickets_artifact_path,
        suggestions_hash,
    )
    preview_id = stable_id("backlog_preview", idempotency_key)
    existing = _load_existing_preview(store, preview_id)
    if existing:
        return existing

    operations = _suggestion_preview_operations(
        store,
        ticket,
        packet,
        trigger_type,
        suggestions,
        next_tickets_artifact_path,
        preview_id,
        no_suggestions_reason,
    )
    preview = BacklogPreview(
        id=preview_id,
        trigger_type=trigger_type,
        trigger_ref=trigger_ref,
        idempotency_key=idempotency_key,
        base_ticket_fingerprint=fingerprint,
        operations=operations,
        conflicts=_detect_preview_conflicts(store, operations),
        rationale=rationale,
        evidence_refs=_dedupe_strings(evidence_refs),
    )
    store.save_backlog_preview(preview)
    return preview


def _suggestion_preview_operations(
    store: AriadneStore,
    source_ticket: BuildTicket,
    source_packet: BuildPacket,
    trigger_type: BacklogUpdateTrigger,
    suggestions: list[dict[str, Any]],
    next_tickets_artifact_path: str,
    preview_id: str,
    no_suggestions_reason: str,
) -> list[BacklogOperation]:
    operations: list[BacklogOperation] = []
    if not suggestions:
        return [
            BacklogOperation(
                id=stable_id("backlog_op", preview_id, source_ticket.id, trigger_type.value, "noop"),
                operation_type=BacklogOperationType.NO_OP,
                ticket_id=source_ticket.id,
                ticket_key=source_ticket.key,
                reason=no_suggestions_reason,
                metadata={
                    "source_ticket_id": source_ticket.id,
                    "source_ticket_key": source_ticket.key,
                },
            )
        ]

    next_index = 1
    materialized_count = 0
    for index, suggestion in enumerate(suggestions, start=1):
        title = str(suggestion.get("title") or "Untitled follow-up ticket")
        reason = str(suggestion.get("reason") or "Generated from ticket run feedback.")
        priority = str(suggestion.get("priority") or "medium")
        generated_ref = stable_id("feedback", source_ticket.id, title)
        if priority == "low":
            operations.append(
                BacklogOperation(
                    id=stable_id("backlog_op", preview_id, generated_ref, "low", index),
                    operation_type=BacklogOperationType.NO_OP,
                    ticket_id=source_ticket.id,
                    ticket_key=source_ticket.key,
                    reason=(
                        "Suggestion retained in next_tickets artifact but not "
                        f"ticketed now: {title}"
                    ),
                    metadata={
                        "source_ticket_id": source_ticket.id,
                        "source_ticket_key": source_ticket.key,
                        "generated_suggestion_ref": generated_ref,
                        "suggestion": suggestion,
                    },
                )
            )
            continue

        existing = _find_generated_ticket(store, source_ticket.id, generated_ref)
        source_doc = _source_document_for_suggestion(
            source_ticket,
            suggestion,
            next_tickets_artifact_path,
            generated_ref,
        )
        metadata = {
            "source_document": source_doc.model_dump(mode="json"),
            "source_packet": source_packet.model_dump(mode="json"),
            "suggestion": suggestion,
            "owner_agent": "Build Lead",
            "generated_from_ticket_id": source_ticket.id,
            "generated_from_ticket_key": source_ticket.key,
            "generated_suggestion_ref": generated_ref,
            "generated_by_backlog_trigger": trigger_type.value,
        }
        if existing:
            operations.append(
                BacklogOperation(
                    id=stable_id("backlog_op", preview_id, generated_ref, "update", index),
                    operation_type=BacklogOperationType.UPDATE_TICKET,
                    ticket_id=existing.id,
                    ticket_key=existing.key,
                    title=title,
                    description=reason,
                    source_type=SourceType.REVIEW.value,
                    source_ref=next_tickets_artifact_path,
                    priority=priority,
                    status=existing.status,
                    reason=f"Update {existing.key} from {trigger_type.value}: {title}.",
                    metadata=metadata,
                )
            )
        else:
            ticket_key, next_index = _next_preview_ticket_key(store, operations, start_index=next_index)
            operations.append(
                BacklogOperation(
                    id=stable_id("backlog_op", preview_id, generated_ref, "add", index),
                    operation_type=BacklogOperationType.ADD_TICKET,
                    ticket_id=stable_id("ticket", generated_ref),
                    ticket_key=ticket_key,
                    title=title,
                    description=reason,
                    source_type=SourceType.REVIEW.value,
                    source_ref=next_tickets_artifact_path,
                    priority=priority,
                    status=TicketStatus.PLANNING,
                    reason=f"Create {ticket_key} from {trigger_type.value}: {title}.",
                    metadata=metadata,
                )
            )
        materialized_count += 1

    if materialized_count:
        operations.append(
            BacklogOperation(
                id=stable_id("backlog_op", preview_id, source_ticket.id, trigger_type.value, "source_trace"),
                operation_type=BacklogOperationType.NO_OP,
                ticket_id=source_ticket.id,
                ticket_key=source_ticket.key,
                reason=(
                    f"{trigger_type.value} preview materialized "
                    f"{materialized_count} follow-up ticket operation(s)."
                ),
                metadata={
                    "source_ticket_id": source_ticket.id,
                    "source_ticket_key": source_ticket.key,
                    "materialized_operation_count": materialized_count,
                },
            )
        )
    return operations


def _target_is_superseded(store: AriadneStore, ticket_id: str) -> bool:
    try:
        return store.load_ticket(ticket_id).status is TicketStatus.SUPERSEDED
    except FileNotFoundError:
        return False


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
    include_execution_result: bool = True,
    include_review_feedback: bool = True,
    include_memory_gap: bool = True,
    include_codebase_observation: bool = True,
) -> list[BacklogUpdate]:
    """Record ticket-set deltas caused by one completed ticket run.

    This keeps Ariadne's product loop ticket-centered: execution, review, local
    memory, and codebase observations can update the backlog before the next
    agent is assigned.
    """

    suggestions = _read_next_ticket_suggestions(next_tickets_artifact_path)
    updates: list[BacklogUpdate] = []
    if include_execution_result:
        updates.append(_record_execution_result_update(store, ticket, execution, review))
    if include_review_feedback:
        updates.append(
            _record_review_feedback_update(
                store,
                ticket,
                packet,
                execution,
                review,
                suggestions,
                next_tickets_artifact_path,
            )
        )
    if include_memory_gap:
        updates.append(
            _record_memory_gap_update(
                store,
                ticket,
                packet,
                execution,
                review,
                suggestions,
                memory_record_id,
                next_tickets_artifact_path,
            )
        )
    if include_codebase_observation:
        updates.append(
            _record_codebase_observation_update(
                store,
                ticket,
                packet,
                execution,
                review,
                suggestions,
                next_tickets_artifact_path,
            )
        )
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
    generated_ticket_id = stable_id("ticket", generated_ref)
    for ticket in store.list_tickets():
        if ticket.id == generated_ticket_id:
            return ticket
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
