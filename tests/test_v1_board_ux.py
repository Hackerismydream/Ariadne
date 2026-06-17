from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board_server import board_serve_command
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_board_contains_v1_workbench_sections(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    for heading in [
        "Ariadne v1.0 Workbench",
        "System Summary",
        "Agent Queue",
        "Tickets by Status",
        "Active Assignments",
        "Daemon / Runtime",
        "Agent Comments",
        "Recent Journal Events",
        "Executed Tickets",
        "Next Tickets",
        "Backend Capability",
        "Safety Gates",
        "Assignment Retry Chain",
        "Agent Handoffs",
        "Codex Gate Status",
    ]:
        assert heading in board


def test_board_export_tolerates_legacy_unknown_artifact_types(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    ticket = store.resolve_ticket("ARI-003")
    artifact_id = "artifact_legacy_landing_gate"
    (store.artifact_index_dir / f"{artifact_id}.json").write_text(
        json.dumps(
            {
                "id": artifact_id,
                "ticket_id": ticket.id,
                "agent_run_id": "legacy",
                "artifact_type": "landing_gate",
                "path": str(tmp_path / ".ariadne" / "legacy.json"),
                "summary": "Legacy landing gate artifact.",
                "created_at": "2026-06-17T00:00:00Z",
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )
    store.save_ticket(ticket.model_copy(update={"artifact_ids": [artifact_id]}))

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".ariadne" / "board" / "index.md").exists()


def test_board_serve_command_builds_expected_handler(tmp_path: Path) -> None:
    board_dir = tmp_path / ".ariadne" / "board"
    board_dir.mkdir(parents=True)
    (board_dir / "index.html").write_text("<h1>Ariadne</h1>", encoding="utf-8")

    config = board_serve_command(board_dir, port=0, dry_run=True)

    assert config["directory"] == str(board_dir.resolve())
    assert config["port"] == 0


def test_cli_outputs_readable_ticket_state(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"])
    show = runner.invoke(app, ["--root", str(tmp_path), "ticket", "show", "ARI-003"])

    assert assign.exit_code == 0, assign.output
    assert show.exit_code == 0, show.output
    assert "Assignment:" in show.output
    assert "Status:" in show.output
