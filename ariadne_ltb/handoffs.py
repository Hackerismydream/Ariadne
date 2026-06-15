from __future__ import annotations

from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import (
    AgentHandoff,
    CommentAuthorType,
    CommentKind,
    HandoffStatus,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


def record_handoff(
    store: AriadneStore,
    ticket,
    runtime_id: str,
    from_agent: str,
    to_agent: str,
    reason: str,
    assignment_id: str | None = None,
    payload_ref: str | None = None,
    status: HandoffStatus = HandoffStatus.COMPLETED,
) -> AgentHandoff:
    handoff = AgentHandoff(
        id=stable_id("handoff", ticket.id, from_agent, to_agent, reason, payload_ref or ""),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        from_agent=from_agent,
        to_agent=to_agent,
        from_assignment_id=assignment_id,
        reason=reason,
        payload_ref=payload_ref,
        status=status,
    )
    if status is HandoffStatus.COMPLETED:
        handoff = handoff.mark_completed()
    store.save_handoff(handoff)
    store.add_comment(
        ticket,
        CommentAuthorType.AGENT,
        from_agent,
        CommentKind.HANDOFF,
        f"{from_agent} -> {to_agent}: {reason}",
        payload_ref=handoff.id,
    )
    store.append_runtime_event(
        runtime_event(
            ticket,
            runtime_id,
            "handoff",
            status.value,
            from_agent,
            assignment_id=assignment_id,
            payload_ref=handoff.id,
            metadata={"from_agent": from_agent, "to_agent": to_agent, "reason": reason},
        )
    )
    return handoff
