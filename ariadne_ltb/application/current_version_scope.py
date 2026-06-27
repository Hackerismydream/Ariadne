from __future__ import annotations

from ariadne_ltb.application.issue_projection import classify_ticket
from ariadne_ltb.application.project_versions import ProjectVersionService
from ariadne_ltb.models import BacklogOperation, BacklogPreview, BuildTicket, TicketStatus
from ariadne_ltb.storage import AriadneStore


def current_version_target_project_id(store: AriadneStore) -> str | None:
    return ProjectVersionService(store).current_target_project_id()


def current_version_mainline_tickets(store: AriadneStore, target_project_id: str | None) -> list[BuildTicket]:
    """Project the currently applied version issue set from persisted BuildTickets."""
    if target_project_id is None:
        return []
    current = ProjectVersionService(store).current()
    project_version_id = current.id if current and current.target_project_id == target_project_id else None
    target_version_label = current.version_label if current and current.target_project_id == target_project_id else None
    current_created_at = current.created_at if current and current.target_project_id == target_project_id else None
    all_tickets = store.list_tickets()
    scoped_tickets = [
        ticket
        for ticket in all_tickets
        if _belongs_to_target_version(
            ticket,
            target_project_id,
            project_version_id,
            target_version_label,
            current_created_at,
        )
    ]
    tickets = scoped_tickets
    latest_keys = _latest_applied_issue_delta_keys(store, target_project_id, project_version_id, target_version_label)
    if latest_keys:
        by_key = {ticket.key: ticket for ticket in tickets if _is_visible(ticket)}
        return [by_key[key] for key in latest_keys if key in by_key]
    return sorted(
        [ticket for ticket in tickets if _is_visible(ticket) and classify_ticket(ticket)[0] == "mainline"],
        key=lambda item: item.key,
    )


def _latest_applied_issue_delta_keys(
    store: AriadneStore,
    target_project_id: str | None,
    project_version_id: str | None,
    target_version_label: str | None,
) -> list[str]:
    previews = [
        preview
        for preview in store.list_backlog_previews()
        if preview.applied_at
        and preview.trigger_type.value == "manual_goal"
        and _preview_targets(preview, target_project_id, project_version_id, target_version_label)
    ]
    if not previews:
        return []
    latest = sorted(previews, key=lambda item: item.applied_at or item.created_at)[-1]
    keys: list[str] = []
    seen: set[str] = set()
    for operation in latest.operations:
        if not _operation_included(operation):
            continue
        if operation.ticket_key in seen:
            continue
        keys.append(operation.ticket_key)
        seen.add(operation.ticket_key)
    return keys


def _preview_targets(
    preview: BacklogPreview,
    target_project_id: str | None,
    project_version_id: str | None,
    target_version_label: str | None,
) -> bool:
    if target_project_id is None:
        return False
    return any(
        _metadata_targets_current_version(
            operation.metadata,
            target_project_id,
            project_version_id,
            target_version_label,
        )
        for operation in preview.operations
    )


def _operation_included(operation: BacklogOperation) -> bool:
    if operation.metadata.get("included") is False:
        return False
    return operation.operation_type.value in {"add_ticket", "update_ticket", "promote_ticket"}


def _belongs_to_target_version(
    ticket: BuildTicket,
    target_project_id: str | None,
    project_version_id: str | None,
    target_version_label: str | None,
    current_created_at: str | None,
) -> bool:
    if _metadata_targets_current_version(
        ticket.metadata,
        target_project_id,
        project_version_id,
        target_version_label,
    ):
        return True
    if (
        project_version_id
        and current_created_at
        and ticket.metadata.get("target_project_id") == target_project_id
        and not ticket.metadata.get("project_version_id")
        and not ticket.metadata.get("target_version_label")
    ):
        return ticket.created_at >= current_created_at
    return False


def _metadata_targets_current_version(
    metadata: dict[str, object],
    target_project_id: str | None,
    project_version_id: str | None,
    target_version_label: str | None,
) -> bool:
    if target_project_id is None or metadata.get("target_project_id") != target_project_id:
        return False
    metadata_version_id = metadata.get("project_version_id")
    if project_version_id:
        if metadata_version_id:
            return metadata_version_id == project_version_id
        metadata_version_label = metadata.get("target_version_label")
        if target_version_label and metadata_version_label:
            return metadata_version_label == target_version_label
        return False
    metadata_version_label = metadata.get("target_version_label")
    if target_version_label and metadata_version_label:
        return metadata_version_label == target_version_label
    return not metadata_version_id and not metadata_version_label


def _is_visible(ticket: BuildTicket) -> bool:
    return ticket.status is not TicketStatus.SUPERSEDED
