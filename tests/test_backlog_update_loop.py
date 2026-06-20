from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.backlog import downgrade_ticket, record_noop_backlog_update
from ariadne_ltb.board import export_board
from ariadne_ltb.cli import app
from ariadne_ltb.daemon import LocalDaemonWorker
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import AssignmentStatus, BacklogUpdateTrigger, TicketChangeType, TicketStatus
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project
from tests.helpers import ready_assignment_with_handoff


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def _ready_assignment(store: AriadneStore, ticket, assignment):  # noqa: ANN001
    target_repo = ensure_demo_target_project(store.root)
    return ready_assignment_with_handoff(store, ticket, assignment, target_repo)


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
    assert "changes=created:" in history.output


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


def test_duplicate_source_inputs_are_deduped_in_one_backlog_update(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)

    tickets = ingest_sources(store, [SOURCE_FIXTURES[0], SOURCE_FIXTURES[0]])
    update = store.list_backlog_updates()[-1]

    assert len(tickets) == 1
    assert len(store.list_tickets()) == 1
    assert len(update.created_ticket_ids) == 1
    assert len(update.ticket_changes) == 1


def test_modified_source_path_updates_existing_ticket_instead_of_creating_duplicate(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Source\n\nBuild a small feature.\n", encoding="utf-8")
    store = AriadneStore(tmp_path)
    first = ingest_sources(store, [source])[0]

    source.write_text("# Source\n\nBuild a small feature with more evidence.\n", encoding="utf-8")
    second = ingest_sources(store, [source])[0]
    latest = store.list_backlog_updates()[-1]

    assert first.id == second.id
    assert len(store.list_tickets()) == 1
    assert latest.updated_ticket_ids == [first.id]
    assert latest.ticket_changes[0].change_type is TicketChangeType.UPDATED


def test_reingest_preserves_superseded_ticket_status(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    runner = CliRunner()
    supersede = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "ticket",
            "supersede",
            ticket.key,
            "--reason",
            "Replaced by a narrower ticket.",
        ],
    )
    assert supersede.exit_code == 0, supersede.output

    ingest_sources(store, [SOURCE_FIXTURES[0]])
    updated = store.resolve_ticket(ticket.key)

    assert updated.status is TicketStatus.SUPERSEDED


def test_supersede_cancels_open_assignments_and_daemon_skips_ticket(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    runner = CliRunner()

    supersede = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "ticket",
            "supersede",
            ticket.key,
            "--reason",
            "No longer needed.",
        ],
    )
    daemon = LocalDaemonWorker(store).run_once()

    assert supersede.exit_code == 0, supersede.output
    assert store.load_assignment(assignment.id).status is AssignmentStatus.CANCELLED
    assert daemon.did_work is False
    assert store.resolve_ticket(ticket.key).status is TicketStatus.SUPERSEDED


def test_orchestrator_refuses_superseded_ticket(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "ticket",
            "supersede",
            ticket.key,
            "--reason",
            "Replaced by a narrower ticket.",
        ],
    )
    assert result.exit_code == 0, result.output

    try:
        TicketRunOrchestrator(store).run_ticket(ticket.key)
    except RuntimeError as exc:
        assert "superseded" in str(exc)
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("orchestrator should refuse superseded ticket")
    assert store.resolve_ticket(ticket.key).status is TicketStatus.SUPERSEDED


def test_ticket_run_generates_feedback_backlog_updates_and_followups(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)

    result = TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")
    updates = store.list_backlog_updates_for_ticket(result.ticket_id)
    previews = store.list_backlog_previews()
    preview_ids = {preview.id for preview in previews}
    applied_preview_update_ids = {preview.applied_update_id for preview in previews}
    applied_preview_refs = {preview.applied_update_id: preview.id for preview in previews}
    triggers = {update.trigger_type for update in updates}
    changes = [change for update in updates for change in update.ticket_changes]
    followups = [
        ticket
        for ticket in store.list_tickets()
        if ticket.metadata.get("generated_from_ticket_id") == result.ticket_id
    ]
    board = export_board(store).read_text(encoding="utf-8")

    assert BacklogUpdateTrigger.EXECUTION_RESULT in triggers
    assert BacklogUpdateTrigger.REVIEW_FEEDBACK in triggers
    assert BacklogUpdateTrigger.MEMORY_GAP in triggers
    assert BacklogUpdateTrigger.CODEBASE_OBSERVATION in triggers
    assert TicketChangeType.CLOSED in {change.change_type for change in changes}
    feedback_triggers = {
        BacklogUpdateTrigger.EXECUTION_RESULT,
        BacklogUpdateTrigger.REVIEW_FEEDBACK,
        BacklogUpdateTrigger.MEMORY_GAP,
        BacklogUpdateTrigger.CODEBASE_OBSERVATION,
    }
    assert feedback_triggers <= {
        preview.trigger_type for preview in previews
    }
    assert all(preview.applied_update_id for preview in previews)
    assert result.backlog_preview_ids
    assert set(result.backlog_preview_ids) <= preview_ids
    preview_applied_updates = [
        update
        for update in updates
        if update.trigger_type in feedback_triggers
    ]
    assert {update.id for update in preview_applied_updates} <= applied_preview_update_ids
    assert all(update.trigger_ref == applied_preview_refs[update.id] for update in preview_applied_updates)
    assert followups
    assert any(ticket.build_packet_id for ticket in followups)
    assert result.backlog_update_ids
    assert "memory_gap" in board
    assert "codebase_observation" in board
    assert "Changes `" in board


def test_daemon_run_once_generates_feedback_backlog_updates(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, SOURCE_FIXTURES)[2]
    _ready_assignment(store, ticket, store.create_assignment(ticket, store.resolve_agent_profile("fake-codex")))

    result = LocalDaemonWorker(store).run_once()
    updates = store.list_backlog_updates_for_ticket(ticket.id)

    assert result.did_work is True
    assert result.ticket_run_result is not None
    assert result.ticket_run_result.backlog_preview_ids
    assert result.ticket_run_result.backlog_update_ids
    assert any(update.trigger_type is BacklogUpdateTrigger.MEMORY_GAP for update in updates)
    assert any(update.created_ticket_ids for update in updates)


def test_backlog_engine_records_downgrade_and_noop_decisions(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]

    downgrade = downgrade_ticket(store, ticket, "Not urgent after review feedback.", new_priority="low")
    noop = record_noop_backlog_update(
        store,
        store.load_ticket(ticket.id),
        BacklogUpdateTrigger.CODEBASE_OBSERVATION,
        "Codebase observation was already covered by existing tickets.",
        ["repo_status"],
    )
    board = export_board(store).read_text(encoding="utf-8")

    assert downgrade.ticket_changes[0].change_type is TicketChangeType.DOWNGRADED
    assert store.load_ticket(ticket.id).priority == "low"
    assert noop.ticket_changes[0].change_type is TicketChangeType.NO_OP
    assert "downgraded:1" in board
    assert "no_op:1" in board


def test_backlog_history_and_board_ignore_invalid_jsonl_lines(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, [SOURCE_FIXTURES[0]])
    with store.backlog_updates_path.open("a", encoding="utf-8") as handle:
        handle.write("{bad json\n")

    history = CliRunner().invoke(app, ["--root", str(tmp_path), "backlog", "history"])
    board = export_board(store).read_text(encoding="utf-8")

    assert history.exit_code == 0, history.output
    assert "source_ingest" in history.output
    assert "Ticket Backlog Updates" in board


def test_backlog_update_and_supersede_show_stable_cli_errors(tmp_path: Path) -> None:
    runner = CliRunner()

    missing = runner.invoke(
        app,
        ["--root", str(tmp_path), "backlog", "update", "--from-source", str(tmp_path / "missing.md")],
    )
    unknown = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "supersede", "ARI-999", "--reason", "No longer needed."],
    )

    assert missing.exit_code == 2
    assert "No such file" in missing.output or "not found" in missing.output.lower()
    assert "Traceback" not in missing.output
    assert unknown.exit_code == 2
    assert "unknown ticket: ARI-999" in unknown.output
    assert "Traceback" not in unknown.output
