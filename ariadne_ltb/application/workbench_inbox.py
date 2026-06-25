from __future__ import annotations

from ariadne_ltb.application.current_version_scope import current_version_mainline_tickets, current_version_target_project_id
from ariadne_ltb.application.dtos import InboxListItemDTO, InboxListResponse
from ariadne_ltb.application.inbox_recovery import classify_inbox_item
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.storage import AriadneStore


class WorkbenchInboxService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def list(self) -> InboxListResponse:
        target_project_id = current_version_target_project_id(self.store)
        current_ticket_ids = {
            ticket.id for ticket in current_version_mainline_tickets(self.store, target_project_id)
        }
        items = [
            self._list_item(item)
            for item in refresh_inbox(self.store)
            if item.active and (item.ticket_id is None or item.ticket_id in current_ticket_ids)
        ]
        return InboxListResponse(inbox=items)

    def _list_item(self, item) -> InboxListItemDTO:  # noqa: ANN001
        recovery = classify_inbox_item(item)
        return InboxListItemDTO(
            id=item.id,
            issue_key=item.ticket_key,
            source_type=item.source_type,
            source_id=item.source_id,
            linked_assignment_id=item.source_id if item.source_type == "assignment" else None,
            agent_id=item.agent_id,
            agent_name=item.agent_name,
            canonical_blocker_id=item.id,
            failure_reason=item.failure_reason.value if item.failure_reason else "none",
            severity=item.severity.value,
            action_type=str(item.recommended_action or "human_review_required"),
            allowed_actions=recovery.allowed_actions,
            primary_action=recovery.primary_action,
            recovery_class=recovery.recovery_class,
            created_at=item.created_at,
            status=item.status.value,
            resolution_note=item.resolution_note,
        )
