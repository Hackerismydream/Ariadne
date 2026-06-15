from __future__ import annotations

import pytest
from pydantic import ValidationError

from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    BuildDecision,
    BuildPacket,
    BuildTicket,
    Evidence,
    TicketStatus,
    stable_id,
)


def test_stable_id_is_deterministic_and_prefixed() -> None:
    assert stable_id("ticket", "examples/multica_research_note.md") == stable_id(
        "ticket", "examples/multica_research_note.md"
    )
    assert stable_id("ticket", "examples/multica_research_note.md").startswith("ticket_")


def test_build_ticket_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        BuildTicket(
            id="ticket_demo",
            key="ARI-001",
            title="Implement Ariadne MVP Ticket Kernel",
            description="Demo ticket",
            source_type="research_note",
            source_ref="examples/multica_research_note.md",
            status="not-a-status",
        )


def test_code_task_build_packet_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        BuildPacket(
            id="packet_demo",
            ticket_id="ticket_demo",
            source_summary="A source summary",
            insight="A ticket-like carrier makes agent work visible.",
            project_relevance="Relevant to Ariadne.",
            build_decision=BuildDecision.CODE_TASK,
            tasks=["Implement the kernel"],
            acceptance_criteria=["Pipeline creates terminal runs"],
            affected_modules=["ariadne_ltb.models"],
        )


def test_code_task_build_packet_accepts_evidence() -> None:
    packet = BuildPacket(
        id="packet_demo",
        ticket_id="ticket_demo",
        source_summary="A source summary",
        insight="A ticket-like carrier makes agent work visible.",
        evidence=[
            Evidence(
                id="evidence_demo",
                source_ref="examples/multica_research_note.md",
                quote_or_summary="Build Ticket as visible work carrier.",
                location="Product decision",
                confidence=0.95,
            )
        ],
        project_relevance="Relevant to Ariadne.",
        build_decision=BuildDecision.CODE_TASK,
        tasks=["Implement the kernel"],
        acceptance_criteria=["Pipeline creates terminal runs"],
        affected_modules=["ariadne_ltb.models"],
    )

    assert packet.build_decision is BuildDecision.CODE_TASK
    assert packet.evidence[0].confidence == 0.95


def test_agent_run_terminal_status_logic() -> None:
    run = AgentRun(
        id="run_demo",
        ticket_id="ticket_demo",
        agent_name="Reviewer",
        agent_role="reviewer",
        status=AgentRunStatus.RUNNING,
        input_summary="Review the ticket.",
    )
    assert not run.is_terminal

    finished = run.mark_finished(AgentRunStatus.SUCCEEDED, "Review passed.")
    assert finished.is_terminal
    assert finished.output_summary == "Review passed."


def test_ticket_status_transition_updates_status() -> None:
    ticket = BuildTicket(
        id="ticket_demo",
        key="ARI-001",
        title="Implement Ariadne MVP Ticket Kernel",
        description="Demo ticket",
        source_type="research_note",
        source_ref="examples/multica_research_note.md",
        status=TicketStatus.INBOX,
    )

    updated = ticket.with_status(TicketStatus.PLANNING, actor="Build Lead")
    assert updated.status is TicketStatus.PLANNING
    assert updated.event_log[-1].event_type == "status_changed"
