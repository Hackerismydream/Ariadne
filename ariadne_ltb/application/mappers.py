from __future__ import annotations

from ariadne_ltb.application.dtos import (
    AssignmentDTO,
    CommentDTO,
    RuntimeCapabilityDTO,
    TargetProjectDTO,
    TicketSummaryDTO,
)
from ariadne_ltb.domain.runtime_policy import browser_safe_runtime_capability
from ariadne_ltb.models import ProjectResource, RuntimeCapability, TicketAssignment, TicketComment
from ariadne_ltb.storage import AriadneStore


def ticket_summary(store: AriadneStore, ticket_id_or_obj) -> TicketSummaryDTO:  # noqa: ANN001
    ticket = ticket_id_or_obj if hasattr(ticket_id_or_obj, "key") else store.load_ticket(ticket_id_or_obj)
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
