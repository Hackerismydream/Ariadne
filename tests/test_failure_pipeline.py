from __future__ import annotations

from pathlib import Path

from ariadne_ltb.backlog import supersede_ticket
from ariadne_ltb.daemon import LocalDaemonWorker
from ariadne_ltb.failure import record_assignment_failure
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import AssignmentStatus, CommentKind, FailureReason, TicketStatus
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_record_assignment_failure_blocks_with_comment_journal_and_retry_hint(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))

    result = record_assignment_failure(
        store,
        ticket,
        assignment,
        AssignmentStatus.BLOCKED,
        "review failed",
        FailureReason.REVIEW_FAILED,
        "runtime-test",
        actor="Reviewer",
        stage="review",
    )

    updated = store.load_assignment(assignment.id)
    updated_ticket = store.load_ticket(ticket.id)
    comments = store.list_comments(ticket.id)
    events = store.list_runtime_events_for_ticket(ticket.id)

    assert result.assignment.status is AssignmentStatus.BLOCKED
    assert updated.status is AssignmentStatus.BLOCKED
    assert updated.failure_reason is FailureReason.REVIEW_FAILED
    assert updated_ticket.status is TicketStatus.BLOCKED
    assert comments[-1].kind is CommentKind.BLOCKER
    assert "retry=ari ticket retry" in comments[-1].body
    assert events[-1].stage == "review"
    assert events[-1].event_type == "blocked"
    assert events[-1].failure_reason is FailureReason.REVIEW_FAILED
    assert events[-1].metadata["retry_recommendation"] == f"ari ticket retry {ticket.key}"


def test_record_assignment_failure_fails_with_human_review_retry_hint(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))

    result = record_assignment_failure(
        store,
        ticket,
        assignment,
        AssignmentStatus.FAILED,
        "agent exception",
        FailureReason.AGENT_ERROR,
        "runtime-test",
    )

    assert result.assignment.status is AssignmentStatus.FAILED
    assert result.assignment.failure_reason is FailureReason.AGENT_ERROR
    assert store.load_ticket(ticket.id).status is TicketStatus.FAILED
    assert result.retry_recommendation == "human_review_required"
    assert store.list_runtime_events_for_ticket(ticket.id)[-1].event_type == "failed"


def test_supersede_cancels_open_assignments_through_failure_pipeline(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))

    supersede_ticket(store, ticket, "no longer needed")

    updated = store.load_assignment(assignment.id)
    events = store.list_runtime_events_for_ticket(ticket.id)

    assert updated.status is AssignmentStatus.CANCELLED
    assert updated.failure_reason is FailureReason.USER_CANCELLED
    assert store.load_ticket(ticket.id).status is TicketStatus.SUPERSEDED
    assert any(event.event_type == "cancelled" for event in events)
    assert any(event.failure_reason is FailureReason.USER_CANCELLED for event in events)


def test_daemon_exception_uses_unified_failure_pipeline(monkeypatch, tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))

    def boom(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("orchestrator exploded")

    monkeypatch.setattr(TicketRunOrchestrator, "run_ticket", boom)

    result = LocalDaemonWorker(store, runtime_id="failure-worker").run_once()

    updated = store.load_assignment(assignment.id)
    updated_ticket = store.load_ticket(ticket.id)
    comments = store.list_comments(ticket.id)
    events = store.list_runtime_events_for_ticket(ticket.id)

    assert result.status == "failed"
    assert updated.status is AssignmentStatus.FAILED
    assert updated.failure_reason is FailureReason.AGENT_ERROR
    assert updated_ticket.status is TicketStatus.FAILED
    assert comments[-1].kind is CommentKind.BLOCKER
    assert "failure_reason=agent_error" in comments[-1].body
    assert events[-1].event_type == "failed"
    assert events[-1].failure_reason is FailureReason.AGENT_ERROR
    assert events[-1].metadata["retry_recommendation"] == "human_review_required"

