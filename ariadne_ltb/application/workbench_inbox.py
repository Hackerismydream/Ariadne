from __future__ import annotations

from ariadne_ltb.application.dtos import InboxListItemDTO, InboxListResponse
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.storage import AriadneStore


class WorkbenchInboxService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def list(self) -> InboxListResponse:
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
            if item.active
        ]
        return InboxListResponse(inbox=items)
