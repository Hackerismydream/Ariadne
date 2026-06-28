from __future__ import annotations

from pathlib import Path

from ariadne_ltb.daemon import LocalDaemonWorker
from ariadne_ltb.models import (
    AssignmentStatus,
    BuildTicket,
    ExecutionResult,
    ReviewReport,
    ReviewVerdict,
    TicketAssignment,
)
from ariadne_ltb.orchestrator import _finalize_assignment_from_run_result
from ariadne_ltb.storage import AriadneStore


def test_orchestrator_finalizes_active_assignment_after_successful_run(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = BuildTicket(
        id="ticket_1",
        key="MCA-321",
        title="Integrate safety approval",
        description="",
        source_type="blog",
        source_ref="https://minimal-agent.com/",
    )
    store.save_ticket(ticket)
    assignment = TicketAssignment(
        id="assignment_1",
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        agent_id="agent_codex",
        agent_name="Codex",
        backend_name="codex",
        status=AssignmentStatus.RUNNING,
    )
    store.save_assignment(assignment)
    execution = ExecutionResult(
        id="execution_1",
        ticket_id=ticket.id,
        backend_name="codex",
        dry_run=False,
        blocked=False,
        command="codex exec --cd /tmp/target - < handoff.md",
        exit_code=0,
        stdout="done",
        stderr="",
        changed_files=["mini_code_agent/core/loop.py"],
        git_diff="diff --git a/mini_code_agent/core/loop.py b/mini_code_agent/core/loop.py",
        test_command="python3.11 -m pytest",
        test_exit_code=0,
    )
    review = ReviewReport(id="review_1", ticket_id=ticket.id, verdict=ReviewVerdict.PASS)

    _finalize_assignment_from_run_result(
        store,
        assignment.id,
        execution=execution,
        review=review,
        board_path="/tmp/board/index.html",
    )

    finalized = store.load_assignment(assignment.id)
    assert finalized.status is AssignmentStatus.DONE
    assert finalized.ended_at is not None
    assert finalized.metadata["execution_result_id"] == execution.id
    assert finalized.metadata["review_report_id"] == review.id
    assert finalized.metadata["review_verdict"] == "pass"
    assert finalized.metadata["board_path"] == "/tmp/board/index.html"


def test_orphan_recovery_finalizes_stale_successful_assignment(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = BuildTicket(
        id="ticket_1",
        key="MCA-359",
        title="Add integration test for full agent loop",
        description="",
        source_type="github_repo",
        source_ref="https://github.com/SWE-agent/mini-swe-agent",
    )
    store.save_ticket(ticket)
    assignment = TicketAssignment(
        id="assignment_1",
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        agent_id="agent_codex",
        agent_name="Codex",
        backend_name="codex",
        status=AssignmentStatus.RUNNING,
        claimed_by_runtime_id="local",
        started_at="2026-06-28T10:00:00Z",
        lease_expires_at="2026-06-28T10:01:00Z",
    )
    store.save_assignment(assignment)
    store.save_execution_result(
        ExecutionResult(
            id="execution_1",
            ticket_id=ticket.id,
            backend_name="codex",
            dry_run=False,
            blocked=False,
            command="codex exec --cd /tmp/target - < handoff.md",
            exit_code=0,
            stdout="done",
            stderr="",
            started_at="2026-06-28T10:02:00Z",
            ended_at="2026-06-28T10:05:00Z",
            changed_files=["mini_code_agent/core/loop.py", "tests/test_integration.py"],
            git_diff="diff --git a/mini_code_agent/core/loop.py b/mini_code_agent/core/loop.py",
            test_command="python3.11 -m pytest",
            test_exit_code=0,
        )
    )
    store.save_review_report(
        ReviewReport(
            id="review_1",
            ticket_id=ticket.id,
            verdict=ReviewVerdict.PASS,
            created_at="2026-06-28T10:06:00Z",
        )
    )

    recovered = LocalDaemonWorker(store, runtime_id="local")._recover_stale_assignments()

    finalized = store.load_assignment(assignment.id)
    assert recovered == 1
    assert finalized.status is AssignmentStatus.DONE
    assert finalized.metadata["execution_result_id"] == "execution_1"
    assert finalized.metadata["review_report_id"] == "review_1"
    assert finalized.metadata["recovered_from_stale_success"] is True
    assert "requeue_reason" not in finalized.metadata
