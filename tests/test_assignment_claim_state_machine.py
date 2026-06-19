from __future__ import annotations

from ariadne_ltb.daemon import LocalDaemonWorker
from ariadne_ltb.models import AssignmentStatus, BuildTicket, TicketAssignment, TicketStatus
from ariadne_ltb.storage import AriadneStore


def test_daemon_claims_only_ready_assignment_for_current_project(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    old_ticket = _save_ticket(store, "ticket_old", "OLD-001", "old_project")
    current_ticket = _save_ticket(store, "ticket_current", "MCA-001", "current_project")
    old_assignment = _save_assignment(
        store,
        old_ticket,
        "assignment_old",
        AssignmentStatus.QUEUED,
        "old_project",
    )
    current_assignment = _save_assignment(
        store,
        current_ticket,
        "assignment_current",
        AssignmentStatus.READY_TO_CLAIM,
        "current_project",
    )

    claimed = store.claim_next_assignment(
        runtime_id="runtime_1",
        target_project_id="current_project",
        allowed_backends=["codex"],
    )

    assert claimed is not None
    assert claimed.id == current_assignment.id
    assert store.load_assignment(old_assignment.id).status is AssignmentStatus.QUEUED
    assert claimed.status is AssignmentStatus.CLAIMED


def test_daemon_run_once_does_not_claim_plain_queued_assignment(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    ticket = _save_ticket(store, "ticket_queued", "MCA-002", "current_project")
    assignment = _save_assignment(
        store,
        ticket,
        "assignment_queued",
        AssignmentStatus.QUEUED,
        "current_project",
    )

    result = LocalDaemonWorker(store, runtime_id="runtime_1").run_once(assignment_id=assignment.id)

    assert result.did_work is False
    assert "not claimable" in result.message
    assert store.load_assignment(assignment.id).status is AssignmentStatus.QUEUED


def _save_ticket(store: AriadneStore, ticket_id: str, key: str, target_project_id: str) -> BuildTicket:
    ticket = BuildTicket(
        id=ticket_id,
        key=key,
        title=key,
        description="test ticket",
        source_type="note",
        source_ref="test",
        status=TicketStatus.PLANNING,
        metadata={"target_project_id": target_project_id},
    )
    store.save_ticket(ticket)
    return ticket


def _save_assignment(
    store: AriadneStore,
    ticket: BuildTicket,
    assignment_id: str,
    status: AssignmentStatus,
    target_project_id: str,
) -> TicketAssignment:
    assignment = TicketAssignment(
        id=assignment_id,
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        agent_id="codex",
        agent_name="Ariadne Codex",
        backend_name="codex",
        status=status,
        metadata={
            "target_project_id": target_project_id,
            "route_decision_id": "route_1",
            "handoff_packet_id": "handoff_1",
            "permission_profile_id": "permission_1",
            "confirmation_id": "confirmation_1",
            "handoff_hash": "sha256:test",
            "target_repo_path": "/tmp/project",
            "expected_git_head": "abc123",
        },
    )
    store.save_assignment(assignment)
    return assignment
