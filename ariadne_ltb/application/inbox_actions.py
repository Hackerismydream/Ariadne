from __future__ import annotations

from dataclasses import dataclass

from ariadne_ltb.application.errors import ConflictError, NotFoundError, ValidationAppError
from ariadne_ltb.application.inbox_recovery import classify_inbox_item
from ariadne_ltb.inbox import (
    create_repair_ticket_from_inbox,
    find_repair_ticket_for_inbox_item,
    refresh_inbox,
)
from ariadne_ltb.models import (
    BuildTicket,
    CommentAuthorType,
    CommentKind,
    FailureReason,
    InboxItem,
    InboxStatus,
    TicketAssignment,
)
from ariadne_ltb.retry import create_retry_assignment
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class InboxActionResult:
    inbox_item: InboxItem
    action: str
    ticket: BuildTicket | None = None
    assignment: TicketAssignment | None = None
    already_exists: bool = False
    message: str = ""


class InboxActionService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def create_repair_ticket(self, item_id: str, priority: str = "high") -> InboxActionResult:
        item = self._load_typed_item(item_id)
        self._require_allowed_action(item, "create_repair_ticket")
        existing = find_repair_ticket_for_inbox_item(self.store, item.id)
        result = create_repair_ticket_from_inbox(self.store, item.id, priority=priority)
        repair_ticket = result.ticket or existing
        action = "inbox_repair_ticket_reused" if result.already_exists else "inbox_repair_ticket_created"
        message = (
            f"Repair ticket already exists: {repair_ticket.key}."
            if result.already_exists and repair_ticket
            else f"Repair ticket created: {repair_ticket.key}."
            if repair_ticket
            else "Repair ticket preview applied."
        )
        self._record_source_ticket_action(
            item,
            action,
            message,
            payload_ref=repair_ticket.id if repair_ticket else result.preview.id if result.preview else item.id,
        )
        return InboxActionResult(
            inbox_item=result.inbox_item,
            action=action,
            ticket=repair_ticket,
            already_exists=result.already_exists,
            message=message,
        )

    def acknowledge(self, item_id: str, note: str = "") -> InboxActionResult:
        item = self._load_typed_item(item_id)
        self._require_allowed_action(item, "acknowledge")
        updated = self.store.update_inbox_item_status(
            item.id,
            InboxStatus.ACKNOWLEDGED,
            note or "acknowledged from Workbench",
        )
        self._record_source_ticket_action(
            item,
            "inbox_acknowledged",
            f"Inbox item acknowledged: {updated.resolution_note}.",
            payload_ref=item.id,
        )
        return InboxActionResult(
            inbox_item=updated,
            action="inbox_acknowledged",
            message=updated.resolution_note or "acknowledged",
        )

    def resolve(self, item_id: str, note: str = "") -> InboxActionResult:
        item = self._load_typed_item(item_id)
        self._require_allowed_action(item, "resolve")
        updated = self.store.update_inbox_item_status(
            item.id,
            InboxStatus.RESOLVED,
            note or "resolved from Workbench",
        )
        self._record_source_ticket_action(
            item,
            "inbox_resolved",
            f"Inbox item resolved: {updated.resolution_note}.",
            payload_ref=item.id,
        )
        return InboxActionResult(
            inbox_item=updated,
            action="inbox_resolved",
            message=updated.resolution_note or "resolved",
        )

    def rerun_linked_assignment(self, item_id: str, reason: str = "", force: bool = False) -> InboxActionResult:
        item = self._load_typed_item(item_id)
        self._require_allowed_action(item, "rerun")
        assignment = self._resolve_linked_assignment(item)
        try:
            retry = create_retry_assignment(
                self.store,
                assignment,
                reason or f"rerun requested from inbox item {item.id}",
                force=force,
            )
        except ValueError as exc:
            raise ConflictError(
                "Linked assignment is not safe to rerun automatically.",
                {
                    "inbox_item_id": item.id,
                    "assignment_id": assignment.id,
                    "failure_reason": assignment.failure_reason.value if assignment.failure_reason else None,
                    "reason": str(exc),
                },
            ) from exc
        updated = self.store.update_inbox_item_status(
            item.id,
            InboxStatus.ACKNOWLEDGED,
            f"retry assignment created: {retry.id}",
        )
        self._record_source_ticket_action(
            item,
            "inbox_assignment_rerun_created",
            f"Retry assignment created from inbox item {item.id}: {retry.id}.",
            payload_ref=retry.id,
        )
        return InboxActionResult(
            inbox_item=updated,
            action="inbox_assignment_rerun_created",
            assignment=retry,
            message=f"Retry assignment created: {retry.id}.",
        )

    def _require_allowed_action(self, item: InboxItem, action: str) -> None:
        recovery = classify_inbox_item(item)
        if action in recovery.allowed_actions:
            return
        message = (
            "Inbox action is not safe to rerun for this blocker state."
            if action == "rerun"
            else "Inbox action is not allowed for this blocker state."
        )
        raise ConflictError(
            message,
            {
                "inbox_item_id": item.id,
                "requested_action": action,
                "allowed_actions": recovery.allowed_actions,
                "recovery_class": recovery.recovery_class,
            },
        )

    def _load_typed_item(self, item_id: str) -> InboxItem:
        # Refresh first so Workbench actions can operate on visible failure state even
        # when the inbox file was not materialized yet.
        refresh_inbox(self.store)
        try:
            item = self.store.load_inbox_item(item_id)
        except FileNotFoundError as exc:
            raise NotFoundError(f"inbox item not found: {item_id}", {"inbox_item_id": item_id}) from exc
        if item.failure_reason is not None:
            try:
                FailureReason(item.failure_reason.value)
            except ValueError as exc:
                raise ValidationAppError(
                    "Inbox item has an unsupported failure reason.",
                    {
                        "inbox_item_id": item.id,
                        "failure_reason": str(item.failure_reason),
                    },
                ) from exc
        return item

    def _resolve_linked_assignment(self, item: InboxItem) -> TicketAssignment:
        if item.source_type == "assignment":
            try:
                return self.store.load_assignment(item.source_id)
            except FileNotFoundError as exc:
                raise NotFoundError(
                    f"linked assignment not found: {item.source_id}",
                    {"inbox_item_id": item.id, "source_id": item.source_id},
                ) from exc
        if item.ticket_id:
            assignment = self.store.find_latest_assignment_for_ticket(item.ticket_id)
            if assignment is not None:
                return assignment
        raise ConflictError(
            "Inbox item has no linked assignment to rerun.",
            {
                "inbox_item_id": item.id,
                "source_type": item.source_type,
                "source_id": item.source_id,
            },
        )

    def _record_source_ticket_action(
        self,
        item: InboxItem,
        event_type: str,
        body: str,
        payload_ref: str | None = None,
    ) -> None:
        if not item.ticket_id:
            return
        try:
            ticket = self.store.load_ticket(item.ticket_id)
        except FileNotFoundError:
            return
        self.store.add_comment(
            ticket,
            CommentAuthorType.SYSTEM,
            "Inbox",
            CommentKind.RECOVERY,
            body,
            payload_ref=payload_ref,
            thread_id=item.id,
        )
        self.store.save_ticket(
            self.store.load_ticket(ticket.id).append_event(
                event_type,
                "Inbox",
                body,
                payload_ref=payload_ref,
            )
        )
