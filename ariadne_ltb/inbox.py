from __future__ import annotations

from pathlib import Path

from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    AssignmentStatus,
    ExecutionResult,
    FailureReason,
    FeishuWriteResult,
    GitHubIntegrationResult,
    InboxItem,
    InboxSeverity,
    TicketAssignment,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


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

    deduped = _dedupe(items)
    store.save_inbox_items(deduped)
    return deduped


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
