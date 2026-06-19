from __future__ import annotations

from pathlib import Path

import pytest

from ariadne_ltb.application.assignment_readiness import prepare_assignment_for_claim
from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.dtos import AssignTicketInput, IssueFactoryPreviewInput
from ariadne_ltb.application.issue_factory import IssueFactoryService
from ariadne_ltb.models import AgentProfile, AssignmentStatus, BuildTicket, SourceType
from ariadne_ltb.storage import AriadneStore
from tests.test_issue_factory_compiler import _seed_mini_code_agent_context


def test_assignment_cannot_be_ready_without_route_and_handoff(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = BuildTicket(
        id="ticket_1",
        key="MCA-001",
        title="Bootstrap package",
        description="Bootstrap package.",
        source_type=SourceType.NOTE,
        source_ref="memory://note",
        status="planning",
        priority="high",
    )
    store.save_ticket(ticket)
    agent = AgentProfile(id="codex-agent", name="Codex", role="implementer", backend_name="codex")
    store.save_agent_profiles([agent])
    assignment = store.create_assignment(ticket, agent, backend_name="codex")

    with pytest.raises(ValueError, match="missing_route_decision"):
        prepare_assignment_for_claim(store, assignment, ticket)


def test_build_team_assignment_persists_route_and_handoff_before_ready(tmp_path: Path) -> None:
    store, goal_id, project_id, source_ids = _seed_mini_code_agent_context(tmp_path)
    preview = IssueFactoryService(store).preview(
        IssueFactoryPreviewInput(goal_id=goal_id, source_ids=source_ids, target_project_id=project_id)
    )
    applied = IssueFactoryService(store).apply(preview.id)
    ticket_id = applied.created_ticket_ids[0]
    ticket = store.load_ticket(ticket_id)

    result = AssignTicketService(store).assign(
        ticket.key,
        AssignTicketInput(
            assignee_kind="build_team",
            assignee_id="build-team",
            backend_name="codex",
            target_project_id=project_id,
            runtime_profile="production",
            idempotency_key="assign-mca-001",
        ),
        source="http",
    )

    assignment = store.load_assignment(result.assignment.id)
    assert assignment.status is AssignmentStatus.READY_TO_CLAIM
    assert assignment.metadata["route_decision_id"]
    assert assignment.metadata["handoff_packet_id"]
    packet = store.load_handoff_packet(str(assignment.metadata["handoff_packet_id"]))
    markdown = Path(packet.markdown_path).read_text(encoding="utf-8")
    assert ticket.title in markdown
    assert packet.target_project_id == project_id
    assert packet.acceptance_criteria
    assert store.load_route_decision(str(assignment.metadata["route_decision_id"])).ticket_id == ticket.id
