from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board import export_board
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import BacklogUpdateTrigger, TicketChangeType, TicketStatus
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_ingest_records_source_backlog_update_and_board_trace(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)

    tickets = ingest_sources(store, SOURCE_FIXTURES)
    updates = store.list_backlog_updates()
    board = export_board(store).read_text(encoding="utf-8")

    assert len(tickets) == len(SOURCE_FIXTURES)
    assert updates
    latest = updates[-1]
    assert latest.trigger_type is BacklogUpdateTrigger.SOURCE_INGEST
    assert len(latest.created_ticket_ids) == len(SOURCE_FIXTURES)
    assert not latest.superseded_ticket_ids
    assert latest.evidence_refs
    assert all(change.change_type is TicketChangeType.CREATED for change in latest.ticket_changes)
    assert "## Ticket Backlog Updates" in board
    assert latest.id in board
    assert "source_ingest" in board
    assert "Created" in board


def test_cli_backlog_update_and_history_show_rationale(tmp_path: Path) -> None:
    runner = CliRunner()

    update = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "backlog",
            "update",
            "--from-source",
            str(SOURCE_FIXTURES[0]),
            "--from-source",
            str(SOURCE_FIXTURES[1]),
        ],
    )
    history = runner.invoke(app, ["--root", str(tmp_path), "backlog", "history"])

    assert update.exit_code == 0, update.output
    assert "backlog update:" in update.output
    assert "created tickets:" in update.output
    assert history.exit_code == 0, history.output
    assert "source_ingest" in history.output
    assert "rationale:" in history.output


def test_cli_backlog_update_accepts_glob_expanded_paths_after_from_source(
    tmp_path: Path,
) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "backlog",
            "update",
            "--from-source",
            str(SOURCE_FIXTURES[0]),
            str(SOURCE_FIXTURES[1]),
            str(SOURCE_FIXTURES[2]),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "created tickets: 3" in result.output


def test_ticket_supersede_records_backlog_update_comment_and_status(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "ticket",
            "supersede",
            ticket.key,
            "--reason",
            "Replaced by a narrower ticket after review feedback.",
        ],
    )

    assert result.exit_code == 0, result.output
    updated = store.resolve_ticket(ticket.key)
    comments = store.list_comments(updated.id)
    backlog_update = store.list_backlog_updates()[-1]
    raw_update = json.loads((tmp_path / ".ariadne" / "backlog" / "updates.jsonl").read_text().splitlines()[-1])

    assert updated.status is TicketStatus.SUPERSEDED
    assert updated.metadata["superseded_reason"] == "Replaced by a narrower ticket after review feedback."
    assert updated.id in backlog_update.superseded_ticket_ids
    assert backlog_update.ticket_changes[0].change_type is TicketChangeType.SUPERSEDED
    assert comments[-1].kind.value == "progress"
    assert "superseded" in comments[-1].body.lower()
    assert raw_update["superseded_ticket_ids"] == [updated.id]
