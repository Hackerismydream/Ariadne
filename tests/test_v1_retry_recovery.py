from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import AssignmentStatus, FailureReason
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_ticket_retry_creates_new_assignment_chain(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    first = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(first.mark_blocked("review failed", FailureReason.REVIEW_FAILED))

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "ticket", "retry", ticket.key, "--reason", "fix after review"],
    )

    assignments = store.list_assignments_for_ticket(ticket.id)
    latest = store.find_latest_assignment_for_ticket(ticket.id)
    assert result.exit_code == 0, result.output
    assert len(assignments) == 2
    assert latest is not None
    assert latest.id != first.id
    assert latest.parent_assignment_id == first.id
    assert latest.attempt == 2
    assert latest.retry_reason == "fix after review"
    assert latest.status is AssignmentStatus.QUEUED


def test_unsafe_retry_requires_force(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    first = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(first.mark_blocked("scope violation", FailureReason.SCOPE_VIOLATION))

    blocked = CliRunner().invoke(app, ["--root", str(tmp_path), "ticket", "retry", ticket.key])
    forced = CliRunner().invoke(app, ["--root", str(tmp_path), "ticket", "retry", ticket.key, "--force"])

    assert blocked.exit_code == 2
    assert "unsafe" in blocked.output.lower()
    assert forced.exit_code == 0, forced.output
    assert store.find_latest_assignment_for_ticket(ticket.id).attempt == 2


def test_runtime_recover_recommends_retry_for_safe_blocker(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_blocked("review failed", FailureReason.REVIEW_FAILED))

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "runtime", "recover"])

    assert result.exit_code == 0, result.output
    assert f"recommended: ari ticket retry {ticket.key}" in result.output


def test_board_shows_retry_chain(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    first = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(first.mark_blocked("review failed", FailureReason.REVIEW_FAILED))
    retry = CliRunner().invoke(app, ["--root", str(tmp_path), "ticket", "retry", ticket.key])
    board = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])

    assert retry.exit_code == 0, retry.output
    assert board.exit_code == 0, board.output
    text = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")
    assert "Assignment Retry Chain" in text
    assert first.id in text
