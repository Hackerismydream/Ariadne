from __future__ import annotations

from dataclasses import dataclass

from ariadne_ltb.models import FailureReason, InboxItem


@dataclass(frozen=True)
class InboxRecovery:
    recovery_class: str
    primary_action: str
    allowed_actions: list[str]


AUTO_RERUNNABLE = {
    "timeout",
    "runtime_offline",
    "command_unavailable",
    "review_failed",
}

REPAIR_REQUIRED = {
    "test_failed",
    "agent_error",
    "planner_failed",
    "dirty_base_checkout",
    "model_unsupported",
}

CONFIRMATION_REQUIRED = {
    "external_execution_blocked",
}


def classify_inbox_item(item: InboxItem) -> InboxRecovery:
    if getattr(item, "active", True) is False:
        return InboxRecovery("historical", "view_history", ["view_history"])
    reason = _reason_value(item.failure_reason)
    if reason in AUTO_RERUNNABLE:
        return InboxRecovery("auto_rerunnable", "rerun", ["rerun", "acknowledge", "resolve"])
    if reason in REPAIR_REQUIRED:
        return InboxRecovery(
            "repair_ticket_required",
            "create_repair_ticket",
            ["create_repair_ticket", "acknowledge", "resolve"],
        )
    if reason in CONFIRMATION_REQUIRED:
        return InboxRecovery("confirmation_required", "authorize_in_runtime", ["acknowledge", "resolve"])
    return InboxRecovery(
        "human_required",
        "manual_review",
        ["create_repair_ticket", "acknowledge", "resolve"],
    )


def _reason_value(reason: FailureReason | None) -> str:
    return reason.value if reason else "unknown"
