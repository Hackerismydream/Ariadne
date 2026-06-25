from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    AgentProfile,
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


@dataclass(frozen=True)
class InboxRecoveryBatchResult:
    recovered: list[InboxRepairTicketResult]
    skipped: list[InboxItem]

    @property
    def created_ticket_count(self) -> int:
        return sum(1 for item in self.recovered if item.ticket and not item.already_exists)

    @property
    def existing_ticket_count(self) -> int:
        return sum(1 for item in self.recovered if item.ticket and item.already_exists)

    @property
    def preview_count(self) -> int:
        return sum(1 for item in self.recovered if item.preview_only)


@dataclass(frozen=True)
class InboxRepairDispatchSkip:
    ticket: BuildTicket
    reason: str


@dataclass(frozen=True)
class InboxRepairDispatchResult:
    assignments: list[TicketAssignment]
    skipped: list[InboxRepairDispatchSkip]


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

    deduped = _archive_superseded_items(
        store,
        _canonicalize_runtime_failures(_preserve_existing_status(store, _dedupe(items))),
    )
    store.save_inbox_items(deduped)
    return deduped


def recover_inbox_items(
    store: AriadneStore,
    priority: str = "high",
    preview_only: bool = False,
    refresh: bool = True,
    include_acknowledged: bool = False,
    limit: int | None = None,
) -> InboxRecoveryBatchResult:
    """Create repair Build Tickets for actionable inbox items."""

    items = refresh_inbox(store) if refresh else store.list_inbox_items()
    actionable: list[InboxItem] = []
    skipped: list[InboxItem] = []
    for item in items:
        if item.status is InboxStatus.RESOLVED:
            skipped.append(item)
            continue
        if item.status is InboxStatus.ACKNOWLEDGED and not include_acknowledged:
            skipped.append(item)
            continue
        actionable.append(item)

    if limit is not None:
        skipped.extend(actionable[limit:])
        actionable = actionable[:limit]

    recovered = [
        create_repair_ticket_from_inbox(store, item.id, priority=priority, preview_only=preview_only)
        for item in actionable
    ]
    return InboxRecoveryBatchResult(recovered=recovered, skipped=skipped)


def dispatch_repair_tickets(
    store: AriadneStore,
    agent: AgentProfile,
    backend_name: str | None = None,
    planner_name: str | None = None,
    agent_runtime: str | None = None,
    backlog_planner_name: str | None = None,
    limit: int | None = None,
) -> InboxRepairDispatchResult:
    """Assign inbox-generated repair tickets that do not already have open work."""

    repair_tickets = [
        ticket
        for ticket in store.list_tickets()
        if ticket.metadata.get("generated_from_inbox_item_id")
    ]
    assignments: list[TicketAssignment] = []
    skipped: list[InboxRepairDispatchSkip] = []
    actionable: list[BuildTicket] = []
    for ticket in repair_tickets:
        if ticket.status in {
            TicketStatus.DONE,
            TicketStatus.CANCELLED,
            TicketStatus.SUPERSEDED,
        }:
            skipped.append(InboxRepairDispatchSkip(ticket, f"ticket_status_{ticket.status.value}"))
            continue
        open_assignment = next(
            (
                assignment
                for assignment in store.list_assignments_for_ticket(ticket.id)
                if assignment.status
                in {
                    AssignmentStatus.QUEUED,
                    AssignmentStatus.CLAIMED,
                    AssignmentStatus.RUNNING,
                }
            ),
            None,
        )
        if open_assignment:
            skipped.append(InboxRepairDispatchSkip(ticket, f"open_assignment_exists:{open_assignment.id}"))
            continue
        actionable.append(ticket)

    if limit is not None:
        skipped.extend(InboxRepairDispatchSkip(ticket, "limit_exceeded") for ticket in actionable[limit:])
        actionable = actionable[:limit]

    for ticket in actionable:
        assignment = store.create_assignment(
            ticket,
            agent,
            backend_name=backend_name,
            planner_name=planner_name,
            agent_runtime=agent_runtime,
            backlog_planner_name=backlog_planner_name,
            assigned_by="inbox_recovery",
        )
        status = (
            TicketStatus.READY_FOR_EXECUTION
            if (assignment.backend_name or agent.backend_name) == "fake-codex"
            else TicketStatus.WAITING_APPROVAL
        )
        store.save_ticket(
            store.load_ticket(ticket.id).with_status(
                status,
                "Ariadne",
                f"Inbox repair ticket assigned to {agent.name}.",
            )
        )
        assignments.append(assignment)

    return InboxRepairDispatchResult(assignments=assignments, skipped=skipped)


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


def find_repair_ticket_for_inbox_item(store: AriadneStore, item_id: str) -> BuildTicket | None:
    return _find_repair_ticket_for_inbox_item(store, item_id)


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
        agent_id=assignment.agent_id,
        agent_name=assignment.agent_name,
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
        agent_id=str(run.metadata.get("agent_id") or "") or None,
        agent_name=run.agent_name,
        title=f"{ticket_key or run.ticket_id}: {run.agent_name} {run.status.value}",
        summary=summary[:1000],
        severity=_severity(reason),
        failure_reason=reason,
        evidence_ref=_agent_run_evidence_ref(store, run),
        recommended_action=_recommended_action(reason),
    )


def _from_execution(store: AriadneStore, execution: ExecutionResult, ticket_key: str | None) -> InboxItem:
    reason = execution.failure_reason or FailureReason.UNKNOWN
    assignment = store.find_latest_assignment_for_ticket(execution.ticket_id)
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
        agent_id=assignment.agent_id if assignment else None,
        agent_name=assignment.agent_name if assignment else None,
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


def _canonicalize_runtime_failures(items: list[InboxItem]) -> list[InboxItem]:
    canonical_by_key: dict[tuple[str, str], InboxItem] = {}
    result_by_id: dict[str, InboxItem] = {}
    for item in items:
        key = _runtime_failure_key(item)
        if key is None:
            result_by_id[item.id] = item
            continue
        current = canonical_by_key.get(key)
        if current is None or _runtime_failure_priority(item) < _runtime_failure_priority(current):
            canonical_by_key[key] = item

    canonical_ids = {item.id for item in canonical_by_key.values()}
    for item in items:
        key = _runtime_failure_key(item)
        if key is None or item.id in canonical_ids:
            result_by_id[item.id] = item
            continue
        canonical = canonical_by_key[key]
        result_by_id[item.id] = item.model_copy(
            update={
                "status": InboxStatus.RESOLVED,
                "active": False,
                "current_state": "canonicalized_blocker",
                "archive_reason": "superseded_by_canonical_runtime_blocker",
                "superseded_by_ref": canonical.id,
                "resolution_note": f"superseded by canonical blocker {canonical.id}",
            }
        )
    return sorted(
        result_by_id.values(),
        key=lambda item: (not item.active, item.ticket_key or "", item.failure_reason.value if item.failure_reason else "", item.id),
    )


def _runtime_failure_key(item: InboxItem) -> tuple[str, str] | None:
    if item.source_type not in {"assignment", "agent_run", "execution"}:
        return None
    if not item.ticket_id or item.failure_reason is None:
        return None
    return (item.ticket_id, item.failure_reason.value)


def _runtime_failure_priority(item: InboxItem) -> int:
    return {"assignment": 0, "execution": 1, "agent_run": 2}.get(item.source_type, 99)


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
                        "agent_id": item.agent_id or existing.agent_id,
                        "agent_name": item.agent_name or existing.agent_name,
                        "created_at": existing.created_at,
                        "updated_at": existing.updated_at,
                    }
                )
            )
        else:
            merged.append(item)
    return merged


def _archive_superseded_items(store: AriadneStore, items: list[InboxItem]) -> list[InboxItem]:
    success_by_ticket: dict[str, str] = {}
    for ticket in store.list_tickets():
        success_ref = _current_success_ref(store, ticket)
        if success_ref:
            success_by_ticket[ticket.id] = success_ref
    result: list[InboxItem] = []
    for item in items:
        success_ref = success_by_ticket.get(item.ticket_id or "")
        if success_ref and item.status is InboxStatus.OPEN:
            result.append(
                item.model_copy(
                    update={
                        "status": InboxStatus.RESOLVED,
                        "active": False,
                        "current_state": "historical_blocker",
                        "archive_reason": "superseded_by_current_success",
                        "superseded_by_ref": success_ref,
                        "resolution_note": f"superseded by {success_ref}",
                    }
                )
            )
        else:
            result.append(item)
    return result


def _current_success_ref(store: AriadneStore, ticket: BuildTicket) -> str | None:
    execution_id = ticket.metadata.get("execution_result_id")
    review_id = ticket.metadata.get("review_report_id")
    if not execution_id or not review_id or ticket.status is not TicketStatus.DONE:
        return None
    try:
        execution = store.load_execution_result(execution_id)
        review = store.load_review_report(review_id)
    except FileNotFoundError:
        return None
    if (
        not execution.blocked
        and execution.exit_code == 0
        and execution.test_exit_code in {None, 0}
        and review.verdict.value == "pass"
    ):
        return execution.id
    return None
