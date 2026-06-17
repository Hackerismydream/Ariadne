from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    AssignmentStatus,
    BacklogOperation,
    BacklogOperationType,
    BacklogPreview,
    BacklogUpdate,
    BacklogUpdateTrigger,
    BuildTicket,
    ExecutionResult,
    FailureReason,
    FeishuWriteResult,
    GitHubIntegrationResult,
    InboxItem,
    InboxSeverity,
    InboxStatus,
    SourceDocument,
    SourceType,
    TicketStatus,
    TicketAssignment,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class InboxRepairTicketResult:
    inbox_item: InboxItem
    preview: BacklogPreview | None
    update: BacklogUpdate | None
    ticket: BuildTicket | None
    already_exists: bool = False
    preview_only: bool = False


def refresh_inbox(store: AriadneStore) -> list[InboxItem]:
    """Materialize local action items from failures and blocked integration results."""

    items: list[InboxItem] = []
    ticket_by_id = {ticket.id: ticket for ticket in store.list_tickets()}

    for assignment in store.list_assignments():
        if assignment.status in {AssignmentStatus.BLOCKED, AssignmentStatus.FAILED}:
            ticket = ticket_by_id.get(assignment.ticket_id)
            items.append(_from_assignment(store, assignment, ticket.key if ticket else assignment.ticket_key))

    for run in store.list_runs():
        if run.status in {AgentRunStatus.BLOCKED, AgentRunStatus.FAILED}:
            ticket = ticket_by_id.get(run.ticket_id)
            items.append(_from_agent_run(store, run, ticket.key if ticket else None))

    for execution in store.list_execution_results():
        if _execution_needs_inbox(execution):
            ticket = ticket_by_id.get(execution.ticket_id)
            items.append(_from_execution(store, execution, ticket.key if ticket else None))

    for result in store.list_feishu_write_results():
        if not result.ok or result.blocked:
            items.append(_from_feishu(store, result))

    for result in store.list_github_integration_results():
        if not result.ok or result.blocked:
            items.append(_from_github(store, result))

    deduped = _preserve_existing_status(store, _dedupe(items))
    store.save_inbox_items(deduped)
    return deduped


def create_repair_ticket_from_inbox(
    store: AriadneStore,
    item_id: str,
    priority: str = "high",
    preview_only: bool = False,
) -> InboxRepairTicketResult:
    """Create or preview a repair Build Ticket from one inbox item."""

    item = store.load_inbox_item(item_id)
    existing = _find_repair_ticket_for_inbox_item(store, item.id)
    if existing:
        acknowledged = store.update_inbox_item_status(
            item.id,
            InboxStatus.ACKNOWLEDGED,
            f"repair ticket already exists: {existing.key}",
        )
        return InboxRepairTicketResult(
            inbox_item=acknowledged,
            preview=None,
            update=None,
            ticket=existing,
            already_exists=True,
        )

    preview = _repair_ticket_preview(store, item, priority)
    store.save_backlog_preview(preview)
    if preview_only:
        return InboxRepairTicketResult(
            inbox_item=item,
            preview=preview,
            update=None,
            ticket=None,
            preview_only=True,
        )

    from ariadne_ltb.backlog import apply_backlog_preview

    applied = apply_backlog_preview(store, preview.id)
    ticket = (
        store.load_ticket(applied.update.created_ticket_ids[0])
        if applied.update and applied.update.created_ticket_ids
        else None
    )
    note = f"repair ticket created: {ticket.key}" if ticket else f"repair preview applied: {preview.id}"
    acknowledged = store.update_inbox_item_status(item.id, InboxStatus.ACKNOWLEDGED, note)
    return InboxRepairTicketResult(
        inbox_item=acknowledged,
        preview=applied.preview,
        update=applied.update,
        ticket=ticket,
        already_exists=applied.already_applied,
    )


def _repair_ticket_preview(store: AriadneStore, item: InboxItem, priority: str) -> BacklogPreview:
    from ariadne_ltb.backlog import ticket_backlog_fingerprint
    from ariadne_ltb.ingest import next_ticket_key

    fingerprint = ticket_backlog_fingerprint(store)
    source_document = _source_document_for_inbox_item(item)
    idempotency_key = stable_id(
        "backlog_preview_key",
        BacklogUpdateTrigger.INBOX_RECOVERY.value,
        fingerprint,
        item.id,
        item.status.value,
    )
    preview_id = stable_id("backlog_preview", idempotency_key)
    ticket_key = next_ticket_key(store)
    title = _repair_ticket_title(item)
    description = _repair_ticket_description(item)
    return BacklogPreview(
        id=preview_id,
        trigger_type=BacklogUpdateTrigger.INBOX_RECOVERY,
        trigger_ref=item.id,
        idempotency_key=idempotency_key,
        base_ticket_fingerprint=fingerprint,
        operations=[
            BacklogOperation(
                id=stable_id("backlog_op", preview_id, item.id, "repair_ticket"),
                operation_type=BacklogOperationType.ADD_TICKET,
                ticket_id=stable_id("ticket", "inbox_repair", item.id),
                ticket_key=ticket_key,
                title=title,
                description=description,
                source_type=SourceType.REVIEW.value,
                source_ref=item.evidence_ref or f"ariadne://inbox/{item.id}",
                priority=priority,
                status=TicketStatus.PLANNING,
                reason=f"Create {ticket_key} to repair inbox item {item.id}.",
                metadata={
                    "source_document": source_document.model_dump(mode="json"),
                    "owner_agent": "Build Lead",
                    "generated_from_inbox_item_id": item.id,
                    "generated_from_inbox_source_type": item.source_type,
                    "generated_from_inbox_source_id": item.source_id,
                },
            )
        ],
        conflicts=[],
        rationale=f"Create a repair Build Ticket from inbox item {item.id}.",
        evidence_refs=[item.id, item.evidence_ref or str(store.inbox_items_path)],
    )


def _source_document_for_inbox_item(item: InboxItem) -> SourceDocument:
    content = "\n".join(
        [
            _repair_ticket_title(item),
            item.summary,
            item.failure_reason.value if item.failure_reason else "unknown",
            item.recommended_action,
            item.evidence_ref or "",
        ]
    )
    return SourceDocument(
        id=stable_id("source", "inbox_repair", item.id),
        source_type=SourceType.REVIEW,
        title=_repair_ticket_title(item),
        path_or_url=item.evidence_ref or f"ariadne://inbox/{item.id}",
        content_hash=sha256(content.encode("utf-8")).hexdigest(),
        summary=_repair_ticket_description(item),
        metadata={
            "inbox_item_id": item.id,
            "inbox_source_type": item.source_type,
            "inbox_source_id": item.source_id,
            "inbox_ticket_key": item.ticket_key,
            "inbox_failure_reason": item.failure_reason.value if item.failure_reason else None,
            "inbox_recommended_action": item.recommended_action,
        },
    )


def _find_repair_ticket_for_inbox_item(store: AriadneStore, item_id: str) -> BuildTicket | None:
    for ticket in store.list_tickets():
        if ticket.metadata.get("generated_from_inbox_item_id") == item_id:
            return ticket
    return None


def _repair_ticket_title(item: InboxItem) -> str:
    ticket_part = f"{item.ticket_key} " if item.ticket_key else ""
    reason = item.failure_reason.value.replace("_", " ") if item.failure_reason else "failure"
    return f"Repair {ticket_part}{item.source_type} {reason}".strip()


def _repair_ticket_description(item: InboxItem) -> str:
    lines = [
        f"Repair inbox item `{item.id}` from `{item.source_type}`.",
        "",
        f"Summary: {item.summary}",
        f"Failure reason: {item.failure_reason.value if item.failure_reason else 'unknown'}",
        f"Recommended action: {item.recommended_action}",
    ]
    if item.evidence_ref:
        lines.append(f"Evidence: {item.evidence_ref}")
    return "\n".join(lines)


def _from_assignment(store: AriadneStore, assignment: TicketAssignment, ticket_key: str | None) -> InboxItem:
    reason = assignment.failure_reason or FailureReason.UNKNOWN
    summary = assignment.blocker or f"Assignment {assignment.id} is {assignment.status.value}."
    return InboxItem(
        id=stable_id("inbox", "assignment", assignment.id, reason.value, summary),
        source_type="assignment",
        source_id=assignment.id,
        ticket_id=assignment.ticket_id,
        ticket_key=ticket_key,
        title=f"{ticket_key or assignment.ticket_id}: assignment {assignment.status.value}",
        summary=summary,
        severity=_severity(reason),
        failure_reason=reason,
        evidence_ref=str(store.assignments_dir / f"{assignment.id}.json"),
        recommended_action=_recommended_action(reason),
    )


def _from_agent_run(store: AriadneStore, run: AgentRun, ticket_key: str | None) -> InboxItem:
    reason = run.failure_reason or FailureReason.UNKNOWN
    summary = run.error or run.output_summary or f"Agent run {run.id} is {run.status.value}."
    summary = f"{run.agent_role}: {summary}"
    return InboxItem(
        id=stable_id("inbox", "agent_run", run.id, reason.value, summary),
        source_type="agent_run",
        source_id=run.id,
        ticket_id=run.ticket_id,
        ticket_key=ticket_key,
        title=f"{ticket_key or run.ticket_id}: {run.agent_name} {run.status.value}",
        summary=summary[:1000],
        severity=_severity(reason),
        failure_reason=reason,
        evidence_ref=_agent_run_evidence_ref(store, run),
        recommended_action=_recommended_action(reason),
    )


def _from_execution(store: AriadneStore, execution: ExecutionResult, ticket_key: str | None) -> InboxItem:
    reason = execution.failure_reason or FailureReason.UNKNOWN
    summary = (
        execution.block_reason
        or execution.provider_failure_evidence
        or execution.stderr
        or execution.test_stderr
        or f"Execution exited {execution.exit_code}."
    )
    return InboxItem(
        id=stable_id("inbox", "execution", execution.id, reason.value, summary),
        source_type="execution",
        source_id=execution.id,
        ticket_id=execution.ticket_id,
        ticket_key=ticket_key,
        title=f"{ticket_key or execution.ticket_id}: execution issue",
        summary=summary[:1000],
        severity=_severity(reason),
        failure_reason=reason,
        evidence_ref=str(store.execution_results_dir / f"{execution.id}.json"),
        recommended_action=_recommended_action(reason),
    )


def _from_feishu(store: AriadneStore, result: FeishuWriteResult) -> InboxItem:
    reason = result.failure_reason or FailureReason.UNKNOWN
    summary = result.reason or result.stderr or result.operation_summary or "Feishu write failed."
    return InboxItem(
        id=stable_id("inbox", "feishu", result.id, reason.value, summary),
        source_type="feishu",
        source_id=result.id,
        ticket_id=result.ticket_id,
        ticket_key=result.ticket_key,
        title=f"{result.ticket_key}: Feishu write issue",
        summary=summary[:1000],
        severity=_severity(reason),
        failure_reason=reason,
        evidence_ref=str(_integration_path(store.feishu_integrations_dir, result.ticket_key, result.id)),
        recommended_action=_recommended_action(reason),
    )


def _from_github(store: AriadneStore, result: GitHubIntegrationResult) -> InboxItem:
    reason = result.failure_reason or FailureReason.UNKNOWN
    summary = result.reason or result.stderr or "GitHub integration failed."
    return InboxItem(
        id=stable_id("inbox", "github", result.id, reason.value, summary),
        source_type="github",
        source_id=result.id,
        ticket_id=result.ticket_id,
        ticket_key=result.ticket_key,
        title=f"{result.ticket_key}: GitHub {result.operation} issue",
        summary=summary[:1000],
        severity=_severity(reason),
        failure_reason=reason,
        evidence_ref=str(_integration_path(store.github_integrations_dir, result.ticket_key, result.id)),
        recommended_action=_recommended_action(reason),
    )


def _execution_needs_inbox(execution: ExecutionResult) -> bool:
    if execution.blocked:
        return True
    if execution.exit_code != 0:
        return True
    if execution.test_exit_code not in {None, 0}:
        return True
    return False


def _integration_path(base: Path, ticket_key: str, result_id: str) -> Path:
    return base / ticket_key / f"{result_id}.json"


def _agent_run_evidence_ref(store: AriadneStore, run: AgentRun) -> str:
    if run.artifact_ids:
        try:
            return store.load_artifact(run.artifact_ids[-1]).path
        except (OSError, ValueError, FileNotFoundError):
            pass
    return str(store.runs_dir / f"{run.id}.json")


def _severity(reason: FailureReason) -> InboxSeverity:
    if reason in {FailureReason.AUTHENTICATION_FAILED, FailureReason.QUOTA_EXCEEDED}:
        return InboxSeverity.HIGH
    if reason in {
        FailureReason.SCOPE_VIOLATION,
        FailureReason.INVALID_RESOURCE,
        FailureReason.PROVIDER_CONFIG_INVALID,
    }:
        return InboxSeverity.HIGH
    if reason in {FailureReason.TEST_FAILED, FailureReason.REVIEW_FAILED}:
        return InboxSeverity.MEDIUM
    return InboxSeverity.MEDIUM


def _recommended_action(reason: FailureReason) -> str:
    if reason is FailureReason.AUTHENTICATION_FAILED:
        return "login_or_refresh_credentials"
    if reason is FailureReason.QUOTA_EXCEEDED:
        return "wait_for_quota_or_change_provider"
    if reason is FailureReason.COMMAND_UNAVAILABLE:
        return "install_required_cli"
    if reason is FailureReason.EXTERNAL_EXECUTION_BLOCKED:
        return "rerun_with_explicit_confirmation_if_safe"
    if reason is FailureReason.PROVIDER_CONFIG_INVALID:
        return "fix_provider_configuration"
    if reason is FailureReason.SCOPE_VIOLATION:
        return "review_resource_boundary"
    return "human_review_required"


def _dedupe(items: list[InboxItem]) -> list[InboxItem]:
    by_id: dict[str, InboxItem] = {}
    for item in items:
        by_id[item.id] = item
    return sorted(by_id.values(), key=lambda item: (item.severity.value, item.created_at, item.id))


def _preserve_existing_status(store: AriadneStore, items: list[InboxItem]) -> list[InboxItem]:
    existing_by_id = {item.id: item for item in store.list_inbox_items()}
    merged: list[InboxItem] = []
    for item in items:
        existing = existing_by_id.get(item.id)
        if existing and existing.status is not InboxStatus.OPEN:
            merged.append(
                item.model_copy(
                    update={
                        "status": existing.status,
                        "resolution_note": existing.resolution_note,
                        "created_at": existing.created_at,
                        "updated_at": existing.updated_at,
                    }
                )
            )
        else:
            merged.append(item)
    return merged
