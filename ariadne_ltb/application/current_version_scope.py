from __future__ import annotations

from collections import Counter

from ariadne_ltb.application.issue_projection import classify_ticket
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.models import BacklogOperation, BacklogPreview, BuildTicket, TicketStatus
from ariadne_ltb.storage import AriadneStore


def current_version_target_project_id(store: AriadneStore) -> str | None:
    goals = ProjectGoalService(store).list()
    resources = store.load_project_resources()
    goal = max(enumerate(goals), key=lambda item: (item[1].created_at, -item[0]))[1] if goals else None
    if goal and goal.target_project_id:
        return goal.target_project_id
    target_ids = [
        str(ticket.metadata["target_project_id"])
        for ticket in store.list_tickets()
        if ticket.metadata.get("target_project_id")
    ]
    if target_ids:
        return Counter(target_ids).most_common(1)[0][0]
    target = resources[-1] if resources else None
    return target.id if target else None


def current_version_mainline_tickets(store: AriadneStore, target_project_id: str | None) -> list[BuildTicket]:
    """Project the currently applied version issue set from persisted BuildTickets."""
    all_tickets = store.list_tickets()
    scoped_tickets = [ticket for ticket in all_tickets if _belongs_to_target(ticket, target_project_id)]
    tickets = scoped_tickets or all_tickets
    latest_keys = _latest_applied_issue_delta_keys(store, target_project_id)
    if latest_keys:
        by_key = {ticket.key: ticket for ticket in tickets if _is_visible(ticket)}
        return [by_key[key] for key in latest_keys if key in by_key]
    return sorted(
        [ticket for ticket in tickets if _is_visible(ticket) and classify_ticket(ticket)[0] == "mainline"],
        key=lambda item: item.key,
    )


def _latest_applied_issue_delta_keys(store: AriadneStore, target_project_id: str | None) -> list[str]:
    previews = [
        preview
        for preview in store.list_backlog_previews()
        if preview.applied_at and preview.trigger_type.value == "manual_goal" and _preview_targets(preview, target_project_id)
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


def _preview_targets(preview: BacklogPreview, target_project_id: str | None) -> bool:
    if target_project_id is None:
        return True
    return any(operation.metadata.get("target_project_id") == target_project_id for operation in preview.operations)


def _operation_included(operation: BacklogOperation) -> bool:
    if operation.metadata.get("included") is False:
        return False
    return operation.operation_type.value in {"add_ticket", "update_ticket", "promote_ticket"}


def _belongs_to_target(ticket: BuildTicket, target_project_id: str | None) -> bool:
    if target_project_id is None:
        return True
    return ticket.metadata.get("target_project_id") == target_project_id


def _is_visible(ticket: BuildTicket) -> bool:
    return ticket.status is not TicketStatus.SUPERSEDED
