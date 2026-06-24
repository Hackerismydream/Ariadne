from __future__ import annotations

from ariadne_ltb.application.current_version_scope import current_version_mainline_tickets, current_version_target_project_id
from ariadne_ltb.application.dtos import InboxListItemDTO, InboxListResponse
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
            InboxListItemDTO(
                id=item.id,
                issue_key=item.ticket_key,
                failure_reason=item.failure_reason.value if item.failure_reason else "none",
                severity=item.severity.value,
                action_type=str(item.recommended_action or "human_review_required"),
                created_at=item.created_at,
                status=item.status.value,
                resolution_note=item.resolution_note,
            )
            for item in refresh_inbox(self.store)
            if item.active and (item.ticket_id is None or item.ticket_id in current_ticket_ids)
        ]
        return InboxListResponse(inbox=items)
