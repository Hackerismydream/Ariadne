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
    TargetProjectDTO,
    TicketSummaryDTO,
)
from ariadne_ltb.domain.runtime_policy import browser_safe_runtime_capability
from ariadne_ltb.models import (
    AgentProfile,
    BacklogOperation,
    BacklogPreview,
    BuildSkill,
    InboxItem,
    ProjectResource,
    RuntimeCapability,
    SourceDocument,
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
    )


def assignment_dto(assignment: TicketAssignment) -> AssignmentDTO:
    return AssignmentDTO(
        id=assignment.id,
        ticket_id=assignment.ticket_id,
        ticket_key=assignment.ticket_key,
        agent_id=assignment.agent_id,
        agent_name=assignment.agent_name,
        backend_name=assignment.backend_name,
        status=assignment.status.value,
        target_project_id=assignment.metadata.get("target_project_id"),
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
    return TargetProjectDTO(
        id=resource.id,
        label=resource.label or resource.resource_ref.get("label") or resource.id,
        available=available,
        disabled_reason=reason,
    )


def source_document_dto(store: AriadneStore, source: SourceDocument) -> SourceDocumentDTO:
    linked_count = sum(
        1 for ticket in store.list_tickets()
        if ticket.metadata.get("source_document_id") == source.id or ticket.source_ref == source.path_or_url
    )
    evidence = source.metadata.get("evidence_snippets")
    return SourceDocumentDTO(
        id=source.id,
        source_type=source.source_type.value,
        title=source.title,
        path_or_url=source.path_or_url,
        summary=source.summary,
        status="linked" if linked_count else "new",
        linked_ticket_count=linked_count,
        created_at=source.created_at,
        evidence_snippets=[str(item) for item in evidence] if isinstance(evidence, list) else [],
    )


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


def inbox_item_dto(item: InboxItem) -> InboxItemDTO:
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
        repair_ticket_id=None,
        repair_ticket_key=None,
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
    )


def backlog_preview_dto(preview: BacklogPreview) -> BacklogPreviewDTO:
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
    )
