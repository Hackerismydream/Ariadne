from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import HandoffStatus
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_ticket_run_generates_agent_handoff_chain(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)

    result = TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")
    handoffs = store.list_handoffs_for_ticket(result.ticket_id)

    assert [handoff.to_agent for handoff in handoffs] == [
        "Planner",
        "Execution",
        "Reviewer",
        "Memory",
        "Build Lead",
    ]
    assert all(handoff.status is HandoffStatus.COMPLETED for handoff in handoffs)


def test_daemon_run_once_generates_handoff_chain(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"],
    )
    run = runner.invoke(app, ["--root", str(tmp_path), "daemon", "run-once"])

    ticket = store.resolve_ticket("ARI-003")
    handoffs = store.list_handoffs_for_ticket(ticket.id)
    assert assign.exit_code == 0, assign.output
    assert run.exit_code == 0, run.output
    assert [handoff.to_agent for handoff in handoffs][-1] == "Build Lead"


def test_ticket_handoffs_cli_and_comments(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "ticket", "handoffs", "ARI-003"])
    comments = store.list_comments(store.resolve_ticket("ARI-003").id)

    assert result.exit_code == 0, result.output
    assert "Build Lead -> Planner" in result.output
    assert "Execution -> Reviewer" in result.output
    assert any("-> Reviewer" in comment.body for comment in comments)


def test_board_shows_agent_handoffs(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")
    CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])

    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")
    assert "Agent Handoffs" in board
    assert "Reviewer -> Memory" in board
