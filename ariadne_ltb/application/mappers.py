from __future__ import annotations

from ariadne_ltb.application.dtos import (
    AgentProfileDTO,
    AssignmentDTO,
    BacklogOperationDTO,
    BacklogPreviewDTO,
    BuildSkillDTO,
    CommentDTO,
    InboxItemDTO,
    RuntimeCapabilityDTO,
    SourceDocumentDTO,
    SourceArtifactDTO,
    SourceEvidenceDTO,
    TargetProjectDTO,
    TicketEvidenceBundleDTO,
    TicketSummaryDTO,
)
from ariadne_ltb.application.inbox_recovery import classify_inbox_item
from ariadne_ltb.application.ticket_current_state import build_ticket_current_state
from ariadne_ltb.domain.runtime_policy import browser_safe_runtime_capability
from ariadne_ltb.inbox import find_repair_ticket_for_inbox_item
from ariadne_ltb.models import (
    AgentProfile,
    BacklogOperation,
    BacklogPreview,
    BuildSkill,
    InboxItem,
    ProjectResource,
    RuntimeCapability,
    SourceArtifact,
    SourceDocument,
    SourceEvidence,
    TicketAssignment,
    TicketComment,
)
from ariadne_ltb.storage import AriadneStore


def ticket_summary(store: AriadneStore, ticket_id_or_obj) -> TicketSummaryDTO:  # noqa: ANN001
    ticket = ticket_id_or_obj if hasattr(ticket_id_or_obj, "key") else store.load_ticket(ticket_id_or_obj)
    packet = None
    if ticket.build_packet_id:
        try:
            packet = store.load_build_packet(ticket.build_packet_id)
        except FileNotFoundError:
            packet = None
    review_id = ticket.metadata.get("review_report_id")
    review_verdict = None
    if review_id:
        try:
            review_verdict = store.load_review_report(review_id).verdict.value
        except FileNotFoundError:
            review_verdict = None
    return TicketSummaryDTO(
        id=ticket.id,
        key=ticket.key,
        title=ticket.title,
        status=ticket.status.value,
        source_type=str(ticket.source_type),
        priority=ticket.priority,
        assigned_agent_id=ticket.metadata.get("assigned_agent_id"),
        latest_assignment_id=ticket.metadata.get("latest_assignment_id"),
        latest_execution_result_id=ticket.metadata.get("execution_result_id"),
        latest_review_verdict=review_verdict,
        build_packet_id=ticket.build_packet_id,
        summary=packet.source_summary if packet else ticket.description,
        acceptance_criteria=packet.acceptance_criteria if packet else [],
        affected_modules=packet.affected_modules if packet else [],
        source_ref=ticket.source_ref,
        target_project_id=ticket.metadata.get("target_project_id"),
        evidence=ticket_evidence_bundle(store, ticket.id),
    )


def ticket_evidence_bundle(store: AriadneStore, ticket_id: str) -> TicketEvidenceBundleDTO | None:
    ticket = store.load_ticket(ticket_id)
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    execution = _latest_execution_result(store, ticket)
    current_state = build_ticket_current_state(store, ticket)
    review_id = ticket.metadata.get("review_report_id")
    review_verdict = None
    if review_id:
        try:
            review_verdict = store.load_review_report(review_id).verdict.value
        except FileNotFoundError:
            review_verdict = None
    if assignment is None and execution is None and review_id is None:
        return None
    diff_path = _artifact_path(store, execution.diff_artifact_id if execution else None)
    log_path = _artifact_path(store, execution.execution_log_artifact_id if execution else None)
    return TicketEvidenceBundleDTO(
        assignment_id=assignment.id if assignment else None,
        assignment_status=assignment.status.value if assignment else None,
        assignment_blocker=assignment.blocker if assignment else None,
        assignment_failure_reason=assignment.failure_reason.value if assignment and assignment.failure_reason else None,
        execution_result_id=execution.id if execution else ticket.metadata.get("execution_result_id"),
        backend_name=execution.backend_name if execution else None,
        dry_run=execution.dry_run if execution else None,
        blocked=execution.blocked if execution else None,
        block_reason=execution.block_reason if execution else None,
        failure_reason=execution.failure_reason.value if execution and execution.failure_reason else None,
        command=execution.command if execution else None,
        exit_code=execution.exit_code if execution else None,
        stdout_excerpt=_excerpt(execution.stdout) if execution else "",
        stderr_excerpt=_excerpt(execution.stderr) if execution else "",
        changed_files=execution.changed_files if execution else [],
        diff_artifact_id=execution.diff_artifact_id if execution else None,
        diff_artifact_path=diff_path,
        execution_log_artifact_id=execution.execution_log_artifact_id if execution else None,
        execution_log_artifact_path=log_path,
        handoff_file=execution.handoff_file if execution else None,
        test_command=execution.test_command if execution else "",
        test_exit_code=execution.test_exit_code if execution else None,
        test_stdout_excerpt=_excerpt(execution.test_stdout) if execution else "",
        test_stderr_excerpt=_excerpt(execution.test_stderr) if execution else "",
        review_report_id=review_id,
        review_verdict=review_verdict,
        memory_path=str(store.memory_dir / "tickets" / f"{ticket.id}.json")
        if (store.memory_dir / "tickets" / f"{ticket.id}.json").exists()
        else ticket.metadata.get("memory_path"),
        feishu_plan_path=ticket.metadata.get("feishu_plan_path"),
        next_tickets_path=ticket.metadata.get("next_tickets_path"),
        warnings=execution.warnings if execution else [],
        current_state=current_state.current_state,
        current_assignment_id=current_state.current_assignment_id,
        current_run_id=current_state.current_run_id,
        current_execution_result_id=current_state.current_execution_result_id,
        current_review_report_id=current_state.current_review_report_id,
        historical_blocker_count=current_state.historical_blocker_count,
        active_blocker_count=current_state.active_blocker_count,
        superseded_inbox_item_ids=current_state.superseded_inbox_item_ids or [],
    )


def _latest_execution_result(store: AriadneStore, ticket) -> object | None:  # noqa: ANN001
    result_id = ticket.metadata.get("execution_result_id")
    if result_id:
        try:
            return store.load_execution_result(result_id)
        except FileNotFoundError:
            pass
    results = [result for result in store.list_execution_results() if result.ticket_id == ticket.id]
    if not results:
        return None
    return sorted(results, key=lambda result: result.ended_at)[-1]


def _artifact_path(store: AriadneStore, artifact_id: str | None) -> str | None:
    if not artifact_id:
        return None
    try:
        return store.load_artifact(artifact_id).path
    except FileNotFoundError:
        return None


def _excerpt(value: str, limit: int = 1200) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "\n..."


def assignment_dto(assignment: TicketAssignment) -> AssignmentDTO:
    return AssignmentDTO(
        id=assignment.id,
        ticket_id=assignment.ticket_id,
        ticket_key=assignment.ticket_key,
        agent_id=assignment.agent_id,
        agent_name=assignment.agent_name,
        backend_name=assignment.backend_name,
        status=assignment.status.value,
        readiness_status=assignment.status.value,
        claimable=assignment.status.value == "ready_to_claim",
        route_decision_id=assignment.metadata.get("route_decision_id"),
        handoff_packet_id=assignment.metadata.get("handoff_packet_id"),
        handoff_hash=assignment.metadata.get("handoff_hash"),
        build_context_id=assignment.metadata.get("build_context_id"),
        blocked_reason=assignment.blocker,
        runtime_scope=assignment.metadata.get("target_project_id"),
        target_project_id=assignment.metadata.get("target_project_id"),
        parent_assignment_id=assignment.parent_assignment_id,
        retry_reason=assignment.retry_reason,
        retry_policy=assignment.retry_policy,
        created_at=assignment.created_at,
        started_at=assignment.started_at,
        ended_at=assignment.ended_at,
        blocker=assignment.blocker,
        failure_reason=assignment.failure_reason.value if assignment.failure_reason else None,
    )


def comment_dto(comment: TicketComment) -> CommentDTO:
    return CommentDTO(
        id=comment.id,
        ticket_id=comment.ticket_id,
        ticket_key=comment.ticket_key,
        author_type=comment.author_type.value,
        author=comment.author,
        kind=comment.kind.value,
        body=comment.body,
        thread_id=comment.thread_id,
        parent_comment_id=comment.parent_comment_id,
        created_at=comment.created_at,
    )


def runtime_capability_dto(capability: RuntimeCapability) -> RuntimeCapabilityDTO:
    return RuntimeCapabilityDTO.model_validate(browser_safe_runtime_capability(capability))


def target_project_dto(resource: ProjectResource, available: bool = True, reason: str = "") -> TargetProjectDTO:
    metadata = {
        key: value
        for key, value in resource.resource_ref.items()
        if key in {"daemon_id", "label", "test_command", "issue_prefix"}
    }
    local_path = resource.resource_ref.get("local_path")
    from pathlib import Path
    import subprocess

    path = Path(str(local_path)).expanduser() if local_path else None
    path_exists = bool(path and path.exists())
    is_git_repo = False
    git_branch = None
    git_dirty = None
    if path_exists and path:
        try:
            inside = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=path,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            is_git_repo = inside.stdout.strip() == "true"
            if is_git_repo:
                branch = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=path,
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                )
                status = subprocess.run(
                    ["git", "status", "--short"],
                    cwd=path,
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                )
                git_branch = branch.stdout.strip() or None
                git_dirty = bool(status.stdout.strip())
        except (OSError, subprocess.TimeoutExpired):
            pass
    return TargetProjectDTO(
        id=resource.id,
        label=resource.label or resource.resource_ref.get("label") or resource.id,
        available=available,
        disabled_reason=reason,
        metadata=metadata,
        local_path=str(path) if path else None,
        path_exists=path_exists,
        is_git_repo=is_git_repo,
        git_branch=git_branch,
        git_dirty=git_dirty,
        test_command=str(resource.resource_ref.get("test_command") or ""),
        issue_prefix=str(resource.resource_ref.get("issue_prefix") or ""),
    )


def source_document_dto(store: AriadneStore, source: SourceDocument) -> SourceDocumentDTO:
    linked_count = sum(
        1 for ticket in store.list_tickets()
        if ticket.metadata.get("source_document_id") == source.id or ticket.source_ref == source.path_or_url
    )
    evidence = source.metadata.get("evidence_snippets")
    artifact_ids = source.metadata.get("artifact_ids")
    return SourceDocumentDTO(
        id=source.id,
        source_type=source.source_type.value,
        source_role=str(source.metadata.get("source_role") or _default_source_role(source.source_type.value)),
        title=source.title,
        path_or_url=source.path_or_url,
        summary=source.summary,
        status="linked" if linked_count else str(source.metadata.get("analysis_status") or "new"),
        analysis_status=str(source.metadata.get("analysis_status") or "pending"),
        linked_ticket_count=linked_count,
        created_at=source.created_at,
        evidence_snippets=[str(item) for item in evidence] if isinstance(evidence, list) else [],
        artifact_ids=[str(item) for item in artifact_ids] if isinstance(artifact_ids, list) else [],
        license_risk=str(source.metadata.get("license_risk") or "unknown"),
    )


def source_artifact_dto(artifact: SourceArtifact) -> SourceArtifactDTO:
    return SourceArtifactDTO(
        id=artifact.id,
        source_document_id=artifact.source_document_id,
        artifact_type=artifact.artifact_type,
        payload_hash=artifact.payload_hash,
        payload_path=artifact.payload_path,
        evidence_ids=artifact.evidence_ids,
        created_at=str(artifact.created_at),
    )


def source_evidence_dto(evidence: SourceEvidence) -> SourceEvidenceDTO:
    return SourceEvidenceDTO(
        id=evidence.id,
        source_document_id=evidence.source_document_id,
        artifact_id=evidence.artifact_id,
        locator=evidence.locator,
        quote_or_summary=evidence.quote_or_summary,
        claim=evidence.claim,
        confidence=evidence.confidence,
        content_hash=evidence.content_hash,
        created_at=str(evidence.created_at),
    )


def _default_source_role(source_type: str) -> str:
    if source_type == "github_repo":
        return "reference_project"
    if source_type == "target_codebase":
        return "target_codebase"
    return "background_knowledge"


def agent_profile_dto(store: AriadneStore, profile: AgentProfile) -> AgentProfileDTO:
    return AgentProfileDTO(
        id=profile.id,
        name=profile.name,
        role=profile.role,
        backend_name=profile.backend_name,
        planner_name=profile.planner_name,
        agent_runtime=profile.agent_runtime,
        backlog_planner_name=profile.backlog_planner_name,
        description=profile.description,
        capabilities=profile.capabilities,
        enabled=profile.enabled,
        run_count=sum(1 for assignment in store.list_assignments() if assignment.agent_id == profile.id),
    )


def build_skill_dto(skill: BuildSkill) -> BuildSkillDTO:
    return BuildSkillDTO(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        applies_to_agent_roles=skill.applies_to_agent_roles,
        updated_at=skill.updated_at,
    )


def inbox_item_dto(store: AriadneStore, item: InboxItem) -> InboxItemDTO:
    repair_ticket = find_repair_ticket_for_inbox_item(store, item.id)
    recovery = classify_inbox_item(item)
    return InboxItemDTO(
        id=item.id,
        source_type=item.source_type,
        source_id=item.source_id,
        ticket_id=item.ticket_id,
        ticket_key=item.ticket_key,
        title=item.title,
        summary=item.summary,
        severity=item.severity.value,
        status=item.status.value,
        failure_reason=item.failure_reason.value if item.failure_reason else None,
        evidence_ref=item.evidence_ref,
        recommended_action=item.recommended_action,
        resolution_note=item.resolution_note,
        repair_ticket_id=repair_ticket.id if repair_ticket else None,
        repair_ticket_key=repair_ticket.key if repair_ticket else None,
        active=getattr(item, "active", True),
        current_state=getattr(item, "current_state", None),
        archive_reason=getattr(item, "archive_reason", None),
        superseded_by_ref=getattr(item, "superseded_by_ref", None),
        recovery_class=recovery.recovery_class,
        primary_action=recovery.primary_action,
        allowed_actions=recovery.allowed_actions,
        linked_assignment_id=item.source_id if item.source_type == "assignment" else None,
        retry_assignment_id=None,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def backlog_operation_dto(operation: BacklogOperation) -> BacklogOperationDTO:
    return BacklogOperationDTO(
        id=operation.id,
        operation_type=operation.operation_type.value,
        reason=operation.reason,
        ticket_id=operation.ticket_id,
        ticket_key=operation.ticket_key,
        title=operation.title,
        description=operation.description,
        source_type=operation.source_type,
        source_ref=operation.source_ref,
        priority=operation.priority,
        status=operation.status.value if operation.status else None,
        owner_agent=operation.metadata.get("owner_agent"),
        build_decision=operation.metadata.get("build_decision"),
        evidence_refs=[str(item) for item in operation.metadata.get("evidence_refs", [])],
        affected_modules=[str(item) for item in operation.metadata.get("affected_modules", [])],
        acceptance_criteria=[str(item) for item in operation.metadata.get("acceptance_criteria", [])],
        source_artifact_ids=[str(item) for item in operation.metadata.get("source_artifact_ids", [])],
        build_context_id=operation.metadata.get("build_context_id"),
        target_project_id=operation.metadata.get("target_project_id"),
        goal_reason=operation.metadata.get("goal_reason"),
        change_intent=str(operation.metadata.get("change_intent") or "add"),
        target_version_label=operation.metadata.get("target_version_label"),
        existing_ticket_key=operation.metadata.get("existing_ticket_key"),
        before_snapshot=operation.metadata.get("before_snapshot", {}),
        after_summary=str(operation.metadata.get("after_summary") or operation.description or ""),
        confidence=float(operation.metadata.get("confidence", 0.75)),
        decision_reason=str(operation.metadata.get("decision_reason") or operation.reason),
        included=bool(operation.metadata.get("included", True)),
        metadata={
            key: value
            for key, value in operation.metadata.items()
            if key
            in {
                "build_context_id",
                "context_fingerprint",
                "source_document_ids",
                "source_artifact_ids",
                "evidence_refs",
                "affected_modules",
                "acceptance_criteria",
                "goal_reason",
                "target_project_id",
                "risks",
                "assumptions",
                "test_command",
                "change_intent",
                "target_version_label",
                "existing_ticket_key",
                "before_snapshot",
                "after_summary",
                "confidence",
                "decision_reason",
                "included",
            }
        },
    )


def backlog_preview_dto(preview: BacklogPreview) -> BacklogPreviewDTO:
    first_metadata = preview.operations[0].metadata if preview.operations else {}
    return BacklogPreviewDTO(
        id=preview.id,
        trigger_type=preview.trigger_type.value,
        trigger_ref=preview.trigger_ref,
        rationale=preview.rationale,
        operations=[backlog_operation_dto(operation) for operation in preview.operations],
        conflict_count=len(preview.conflicts),
        evidence_refs=preview.evidence_refs,
        created_at=preview.created_at,
        applied_at=preview.applied_at,
        applied_update_id=preview.applied_update_id,
        base_ticket_fingerprint=preview.base_ticket_fingerprint,
        context_fingerprint=first_metadata.get("context_fingerprint"),
        source_document_ids=[str(item) for item in first_metadata.get("source_document_ids", [])],
        source_artifact_ids=[str(item) for item in first_metadata.get("source_artifact_ids", [])],
        target_project_id=first_metadata.get("target_project_id"),
        target_version_label=first_metadata.get("target_version_label"),
    )
