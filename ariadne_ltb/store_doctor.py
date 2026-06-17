from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ariadne_ltb.local_safety import list_locks
from ariadne_ltb.models import (
    AgentHandoff,
    AgentRun,
    AgentRunLifecycleState,
    AgentRunStatus,
    Artifact,
    BuildPacket,
    BuildTicket,
    ExecutionResult,
    MemoryRecord,
    ReviewReport,
    StoreInvariantIssue,
    StoreInvariantReason,
    StoreInvariantReport,
    StoreInvariantSeverity,
    TicketAssignment,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore

T = TypeVar("T", bound=BaseModel)


def check_store_invariants(store: AriadneStore, stale_lock_seconds: int = 3600) -> StoreInvariantReport:
    issues: list[StoreInvariantIssue] = []
    checked_files = _scan_json_syntax(store, issues)

    tickets = _load_models(store.tickets_dir, BuildTicket, "ticket", issues)
    assignments = _load_models(store.assignments_dir, TicketAssignment, "assignment", issues)
    runs = _load_models(store.runs_dir, AgentRun, "agent_run", issues)
    packets = _load_models(store.build_packets_dir, BuildPacket, "build_packet", issues)
    artifacts = _load_models(store.artifact_index_dir, Artifact, "artifact", issues)
    handoffs = _load_models(store.handoffs_dir, AgentHandoff, "handoff", issues)
    memories = _load_models(store.memory_dir / "tickets", MemoryRecord, "memory_record", issues)
    reviews = _load_models(store.reviews_dir, ReviewReport, "review_report", issues)
    executions = _load_models(
        store.execution_results_dir,
        ExecutionResult,
        "execution_result",
        issues,
    )

    _check_duplicate_ticket_keys(tickets, issues)
    _check_ticket_links(store, tickets, packets, runs, artifacts, issues)
    _check_assignment_links(tickets, assignments, issues)
    _check_run_links(tickets, runs, artifacts, issues)
    _check_artifact_links(tickets, runs, artifacts, issues)
    _check_handoff_links(tickets, assignments, handoffs, issues)
    _check_review_memory_execution_links(tickets, memories, reviews, executions, issues)
    _check_stale_locks(store, stale_lock_seconds, issues)

    errors = sum(1 for issue in issues if issue.severity is StoreInvariantSeverity.ERROR)
    warnings = sum(1 for issue in issues if issue.severity is StoreInvariantSeverity.WARNING)
    report = StoreInvariantReport(
        id=stable_id("store_invariant_report", store.root, len(issues), checked_files),
        root_path=str(store.root),
        ok=errors == 0,
        error_count=errors,
        warning_count=warnings,
        checked_files=checked_files,
        issues=issues,
    )
    write_store_invariant_report(store, report)
    return report


def write_store_invariant_report(store: AriadneStore, report: StoreInvariantReport) -> Path:
    path = store.doctor_dir / "store_invariants.json"
    path.write_text(report.model_dump_json(indent=2, exclude_none=False) + "\n", encoding="utf-8")
    return path


def load_latest_store_invariant_report(store: AriadneStore) -> StoreInvariantReport | None:
    path = store.doctor_dir / "store_invariants.json"
    if not path.exists():
        return None
    try:
        return StoreInvariantReport.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, OSError):
        return None


def store_invariant_human_lines(report: StoreInvariantReport, report_path: Path | None = None) -> list[str]:
    lines = [
        f"store invariants: {'ok' if report.ok else 'blocked'}",
        f"errors: {report.error_count}",
        f"warnings: {report.warning_count}",
        f"checked files: {report.checked_files}",
    ]
    if report_path:
        lines.append(f"report: {report_path}")
    for issue in report.issues:
        lines.append(
            f"- {issue.severity.value} {issue.reason.value} "
            f"{issue.entity_type or 'file'}:{issue.entity_id or issue.path} - {issue.message}"
        )
    return lines


def _scan_json_syntax(store: AriadneStore, issues: list[StoreInvariantIssue]) -> int:
    if not store.base.exists():
        return 0
    checked = 0
    for path in sorted(store.base.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix == ".json":
            checked += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
                issues.append(
                    _issue(
                        StoreInvariantReason.MALFORMED_JSON,
                        path,
                        f"JSON file cannot be parsed: {exc}",
                    )
                )
        elif path.suffix == ".jsonl":
            checked += 1
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError) as exc:
                issues.append(
                    _issue(
                        StoreInvariantReason.MALFORMED_JSONL,
                        path,
                        f"JSONL file cannot be read: {exc}",
                    )
                )
                continue
            for line_number, line in enumerate(lines, start=1):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError as exc:
                    issues.append(
                        _issue(
                            StoreInvariantReason.MALFORMED_JSONL,
                            path,
                            f"JSONL line {line_number} cannot be parsed: {exc}",
                        )
                    )
    return checked


def _load_models(
    directory: Path,
    model_type: type[T],
    entity_type: str,
    issues: list[StoreInvariantIssue],
) -> dict[str, T]:
    loaded: dict[str, T] = {}
    if not directory.exists():
        return loaded
    for path in sorted(directory.glob("*.json")):
        try:
            model = model_type.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValidationError, json.JSONDecodeError, OSError, ValueError) as exc:
            issues.append(
                _issue(
                    StoreInvariantReason.MODEL_VALIDATION_FAILED,
                    path,
                    f"{entity_type} model validation failed: {exc}",
                    entity_type=entity_type,
                    entity_id=path.stem,
                )
            )
            continue
        loaded[getattr(model, "id")] = model
    return loaded


def _check_duplicate_ticket_keys(
    tickets: dict[str, BuildTicket],
    issues: list[StoreInvariantIssue],
) -> None:
    by_key: defaultdict[str, list[BuildTicket]] = defaultdict(list)
    for ticket in tickets.values():
        by_key[ticket.key.upper()].append(ticket)
    for key, matches in by_key.items():
        if len(matches) <= 1:
            continue
        ids = ", ".join(ticket.id for ticket in matches)
        for ticket in matches:
            issues.append(
                _issue(
                    StoreInvariantReason.DUPLICATE_TICKET_KEY,
                    Path(f".ariadne/tickets/{ticket.id}.json"),
                    f"ticket key {key} is used by multiple tickets: {ids}",
                    entity_type="ticket",
                    entity_id=ticket.id,
                )
            )


def _check_ticket_links(
    store: AriadneStore,
    tickets: dict[str, BuildTicket],
    packets: dict[str, BuildPacket],
    runs: dict[str, AgentRun],
    artifacts: dict[str, Artifact],
    issues: list[StoreInvariantIssue],
) -> None:
    for ticket in tickets.values():
        path = store.tickets_dir / f"{ticket.id}.json"
        if ticket.build_packet_id and ticket.build_packet_id not in packets:
            issues.append(
                _issue(
                    StoreInvariantReason.MISSING_BUILD_PACKET,
                    path,
                    f"ticket references missing BuildPacket {ticket.build_packet_id}",
                    entity_type="ticket",
                    entity_id=ticket.id,
                    related_entity_id=ticket.build_packet_id,
                )
            )
        for run_id in ticket.agent_run_ids:
            if run_id not in runs:
                issues.append(
                    _issue(
                        StoreInvariantReason.MISSING_AGENT_RUN,
                        path,
                        f"ticket references missing AgentRun {run_id}",
                        entity_type="ticket",
                        entity_id=ticket.id,
                        related_entity_id=run_id,
                    )
                )
        for artifact_id in ticket.artifact_ids:
            if artifact_id not in artifacts:
                issues.append(
                    _issue(
                        StoreInvariantReason.MISSING_ARTIFACT_INDEX,
                        path,
                        f"ticket references missing Artifact index {artifact_id}",
                        entity_type="ticket",
                        entity_id=ticket.id,
                        related_entity_id=artifact_id,
                    )
                )


def _check_assignment_links(
    tickets: dict[str, BuildTicket],
    assignments: dict[str, TicketAssignment],
    issues: list[StoreInvariantIssue],
) -> None:
    for assignment in assignments.values():
        path = Path(f".ariadne/assignments/{assignment.id}.json")
        ticket = tickets.get(assignment.ticket_id)
        if ticket is None:
            issues.append(
                _issue(
                    StoreInvariantReason.MISSING_TICKET,
                    path,
                    f"assignment references missing ticket {assignment.ticket_id}",
                    entity_type="assignment",
                    entity_id=assignment.id,
                    related_entity_id=assignment.ticket_id,
                )
            )
        elif ticket.key != assignment.ticket_key:
            issues.append(
                _issue(
                    StoreInvariantReason.BROKEN_ASSIGNMENT_LINK,
                    path,
                    f"assignment ticket_key {assignment.ticket_key} does not match ticket key {ticket.key}",
                    entity_type="assignment",
                    entity_id=assignment.id,
                    related_entity_id=assignment.ticket_id,
                )
            )
        if assignment.parent_assignment_id and assignment.parent_assignment_id not in assignments:
            issues.append(
                _issue(
                    StoreInvariantReason.BROKEN_ASSIGNMENT_LINK,
                    path,
                    f"assignment references missing parent {assignment.parent_assignment_id}",
                    entity_type="assignment",
                    entity_id=assignment.id,
                    related_entity_id=assignment.parent_assignment_id,
                )
            )
        if assignment.status.is_terminal and not assignment.ended_at:
            issues.append(
                _issue(
                    StoreInvariantReason.INVALID_ASSIGNMENT_LIFECYCLE,
                    path,
                    "terminal assignment is missing ended_at",
                    entity_type="assignment",
                    entity_id=assignment.id,
                )
            )
        if assignment.status.value in {"running", "claimed"} and assignment.ended_at:
            issues.append(
                _issue(
                    StoreInvariantReason.INVALID_ASSIGNMENT_LIFECYCLE,
                    path,
                    "non-terminal assignment has ended_at",
                    entity_type="assignment",
                    entity_id=assignment.id,
                )
            )


def _check_run_links(
    tickets: dict[str, BuildTicket],
    runs: dict[str, AgentRun],
    artifacts: dict[str, Artifact],
    issues: list[StoreInvariantIssue],
) -> None:
    ticket_run_refs = Counter(run_id for ticket in tickets.values() for run_id in ticket.agent_run_ids)
    for run in runs.values():
        path = Path(f".ariadne/runs/{run.id}.json")
        if run.ticket_id not in tickets:
            issues.append(
                _issue(
                    StoreInvariantReason.MISSING_TICKET,
                    path,
                    f"AgentRun references missing ticket {run.ticket_id}",
                    entity_type="agent_run",
                    entity_id=run.id,
                    related_entity_id=run.ticket_id,
                )
            )
        elif ticket_run_refs[run.id] == 0:
            issues.append(
                _issue(
                    StoreInvariantReason.BROKEN_RUN_LINK,
                    path,
                    "AgentRun exists but is not referenced by its ticket",
                    entity_type="agent_run",
                    entity_id=run.id,
                    related_entity_id=run.ticket_id,
                )
            )
        for artifact_id in run.artifact_ids:
            if artifact_id not in artifacts:
                issues.append(
                    _issue(
                        StoreInvariantReason.MISSING_ARTIFACT_INDEX,
                        path,
                        f"AgentRun references missing Artifact index {artifact_id}",
                        entity_type="agent_run",
                        entity_id=run.id,
                        related_entity_id=artifact_id,
                    )
                )
        _check_run_lifecycle(run, path, issues)


def _check_run_lifecycle(run: AgentRun, path: Path, issues: list[StoreInvariantIssue]) -> None:
    if run.status.is_terminal and run.lifecycle_state is not AgentRunLifecycleState.TERMINAL:
        issues.append(
            _issue(
                StoreInvariantReason.INVALID_RUN_LIFECYCLE,
                path,
                "terminal AgentRun status must use lifecycle_state=terminal",
                entity_type="agent_run",
                entity_id=run.id,
            )
        )
    if run.lifecycle_state is AgentRunLifecycleState.TERMINAL and not run.status.is_terminal:
        issues.append(
            _issue(
                StoreInvariantReason.INVALID_RUN_LIFECYCLE,
                path,
                "lifecycle_state=terminal requires a terminal status",
                entity_type="agent_run",
                entity_id=run.id,
            )
        )
    if run.status.is_terminal and not run.ended_at:
        issues.append(
            _issue(
                StoreInvariantReason.INVALID_RUN_LIFECYCLE,
                path,
                "terminal AgentRun is missing ended_at",
                entity_type="agent_run",
                entity_id=run.id,
            )
        )
    if run.status is AgentRunStatus.RUNNING and run.lifecycle_state is not AgentRunLifecycleState.RUNNING:
        issues.append(
            _issue(
                StoreInvariantReason.INVALID_RUN_LIFECYCLE,
                path,
                "running AgentRun must use lifecycle_state=running",
                entity_type="agent_run",
                entity_id=run.id,
            )
        )
    if run.status is AgentRunStatus.RUNNING and not run.started_at:
        issues.append(
            _issue(
                StoreInvariantReason.INVALID_RUN_LIFECYCLE,
                path,
                "running AgentRun is missing started_at",
                entity_type="agent_run",
                entity_id=run.id,
            )
        )
    if run.status is AgentRunStatus.PENDING and run.lifecycle_state is not AgentRunLifecycleState.CREATED:
        issues.append(
            _issue(
                StoreInvariantReason.INVALID_RUN_LIFECYCLE,
                path,
                "pending AgentRun must use lifecycle_state=created",
                entity_type="agent_run",
                entity_id=run.id,
            )
        )


def _check_artifact_links(
    tickets: dict[str, BuildTicket],
    runs: dict[str, AgentRun],
    artifacts: dict[str, Artifact],
    issues: list[StoreInvariantIssue],
) -> None:
    ticket_artifact_refs = {
        artifact_id for ticket in tickets.values() for artifact_id in ticket.artifact_ids
    }
    run_artifact_refs = {artifact_id for run in runs.values() for artifact_id in run.artifact_ids}
    for artifact in artifacts.values():
        path = Path(f".ariadne/artifact_index/{artifact.id}.json")
        artifact_file = Path(artifact.path)
        if artifact.ticket_id not in tickets:
            issues.append(
                _issue(
                    StoreInvariantReason.MISSING_TICKET,
                    path,
                    f"artifact references missing ticket {artifact.ticket_id}",
                    entity_type="artifact",
                    entity_id=artifact.id,
                    related_entity_id=artifact.ticket_id,
                )
            )
        if artifact.agent_run_id not in runs and artifact.agent_run_id != "build_lead":
            issues.append(
                _issue(
                    StoreInvariantReason.MISSING_AGENT_RUN,
                    path,
                    f"artifact references missing AgentRun {artifact.agent_run_id}",
                    entity_type="artifact",
                    entity_id=artifact.id,
                    related_entity_id=artifact.agent_run_id,
                )
            )
        if artifact.id not in ticket_artifact_refs and artifact.id not in run_artifact_refs:
            issues.append(
                _issue(
                    StoreInvariantReason.ORPHAN_ARTIFACT,
                    path,
                    "artifact is not referenced by any ticket or AgentRun",
                    entity_type="artifact",
                    entity_id=artifact.id,
                )
            )
        if not artifact_file.exists():
            issues.append(
                _issue(
                    StoreInvariantReason.MISSING_ARTIFACT_FILE,
                    path,
                    f"artifact payload file is missing: {artifact.path}",
                    entity_type="artifact",
                    entity_id=artifact.id,
                )
            )


def _check_handoff_links(
    tickets: dict[str, BuildTicket],
    assignments: dict[str, TicketAssignment],
    handoffs: dict[str, AgentHandoff],
    issues: list[StoreInvariantIssue],
) -> None:
    for handoff in handoffs.values():
        path = Path(f".ariadne/handoffs/{handoff.id}.json")
        ticket = tickets.get(handoff.ticket_id)
        if ticket is None:
            issues.append(
                _issue(
                    StoreInvariantReason.MISSING_TICKET,
                    path,
                    f"handoff references missing ticket {handoff.ticket_id}",
                    entity_type="handoff",
                    entity_id=handoff.id,
                    related_entity_id=handoff.ticket_id,
                )
            )
        elif ticket.key != handoff.ticket_key:
            issues.append(
                _issue(
                    StoreInvariantReason.BROKEN_HANDOFF_LINK,
                    path,
                    f"handoff ticket_key {handoff.ticket_key} does not match ticket key {ticket.key}",
                    entity_type="handoff",
                    entity_id=handoff.id,
                    related_entity_id=handoff.ticket_id,
                )
            )
        for field_name, assignment_id in [
            ("from_assignment_id", handoff.from_assignment_id),
            ("to_assignment_id", handoff.to_assignment_id),
        ]:
            if assignment_id and assignment_id not in assignments:
                issues.append(
                    _issue(
                        StoreInvariantReason.BROKEN_HANDOFF_LINK,
                        path,
                        f"{field_name} references missing assignment {assignment_id}",
                        entity_type="handoff",
                        entity_id=handoff.id,
                        related_entity_id=assignment_id,
                    )
                )


def _check_review_memory_execution_links(
    tickets: dict[str, BuildTicket],
    memories: dict[str, MemoryRecord],
    reviews: dict[str, ReviewReport],
    executions: dict[str, ExecutionResult],
    issues: list[StoreInvariantIssue],
) -> None:
    for memory in memories.values():
        if memory.ticket_id not in tickets:
            issues.append(
                _issue(
                    StoreInvariantReason.BROKEN_MEMORY_LINK,
                    Path(f".ariadne/memory/tickets/{memory.ticket_id}.json"),
                    f"memory references missing ticket {memory.ticket_id}",
                    entity_type="memory_record",
                    entity_id=memory.id,
                    related_entity_id=memory.ticket_id,
                )
            )
    for review in reviews.values():
        if review.ticket_id not in tickets:
            issues.append(
                _issue(
                    StoreInvariantReason.BROKEN_REVIEW_LINK,
                    Path(f".ariadne/reviews/{review.id}.json"),
                    f"review references missing ticket {review.ticket_id}",
                    entity_type="review_report",
                    entity_id=review.id,
                    related_entity_id=review.ticket_id,
                )
            )
    for execution in executions.values():
        if execution.ticket_id not in tickets:
            issues.append(
                _issue(
                    StoreInvariantReason.MISSING_TICKET,
                    Path(f".ariadne/execution_results/{execution.id}.json"),
                    f"execution result references missing ticket {execution.ticket_id}",
                    entity_type="execution_result",
                    entity_id=execution.id,
                    related_entity_id=execution.ticket_id,
                )
            )


def _check_stale_locks(
    store: AriadneStore,
    stale_lock_seconds: int,
    issues: list[StoreInvariantIssue],
) -> None:
    for lock in list_locks(store, stale_after_seconds=stale_lock_seconds):
        if not lock.stale:
            continue
        issues.append(
            _issue(
                StoreInvariantReason.STALE_LOCK,
                Path(lock.path),
                f"directory lock is stale for target {lock.target_path}",
                entity_type="directory_lock",
                entity_id=Path(lock.path).stem,
                related_entity_id=lock.assignment_id,
                severity=StoreInvariantSeverity.WARNING,
            )
        )


def _issue(
    reason: StoreInvariantReason,
    path: Path,
    message: str,
    *,
    severity: StoreInvariantSeverity = StoreInvariantSeverity.ERROR,
    entity_type: str | None = None,
    entity_id: str | None = None,
    related_entity_id: str | None = None,
) -> StoreInvariantIssue:
    return StoreInvariantIssue(
        reason=reason,
        severity=severity,
        path=str(path),
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        related_entity_id=related_entity_id,
    )
