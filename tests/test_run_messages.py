from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board import export_board
from ariadne_ltb.cli import app
from ariadne_ltb.demo import run_demo
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import AgentRun, AgentRunStatus, RunMessageType, stable_id
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))
SOURCE_NOTE = ROOT / "examples" / "multica_research_note.md"


def test_store_appends_and_filters_run_messages(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    run = AgentRun(
        id="run_demo",
        ticket_id="ticket_demo",
        agent_name="Execution",
        agent_role="execution",
        input_summary="Run demo.",
    ).mark_running()
    store.save_run(run)
    store.reset_run_messages(run.id)

    first = store.append_run_message(run.id, "start", RunMessageType.STATUS, "started")
    second = store.append_run_message(run.id, "artifact", RunMessageType.ARTIFACT, "wrote artifact")
    third = store.append_run_message(run.id, "finish", RunMessageType.RESULT, "finished")

    assert [message.seq for message in [first, second, third]] == [1, 2, 3]
    assert store.run_messages_path(run.id).exists()
    assert [message.seq for message in store.list_run_messages(run.id)] == [1, 2, 3]
    assert [message.seq for message in store.list_run_messages(run.id, since=1)] == [2, 3]
    assert [message.seq for message in store.list_run_messages(run.id, since=3)] == []


def test_ticket_run_writes_message_stream_for_each_run(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)

    result = TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")
    ticket = store.load_ticket(result.ticket_id)

    assert ticket.agent_run_ids
    for run_id in ticket.agent_run_ids:
        run = store.load_run(run_id)
        messages = store.list_run_messages(run_id)
        assert store.run_messages_path(run_id).exists()
        assert [message.seq for message in messages] == list(range(1, len(messages) + 1))
        assert messages[0].stage == "start"
        assert messages[-1].stage == "finish"
        assert messages[-1].metadata["status"] == run.status.value
        assert run.status in {
            AgentRunStatus.SUCCEEDED,
            AgentRunStatus.FAILED,
            AgentRunStatus.BLOCKED,
            AgentRunStatus.SKIPPED,
            AgentRunStatus.CANCELLED,
        }


def test_run_messages_cli_outputs_canonical_jsonl_and_since_cursor(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    run = AgentRun(
        id=stable_id("run", "ticket_demo", "messages"),
        ticket_id="ticket_demo",
        agent_name="Execution",
        agent_role="execution",
        input_summary="Run demo.",
    ).mark_running()
    store.save_run(run)
    store.reset_run_messages(run.id)
    store.append_run_message(run.id, "start", RunMessageType.STATUS, "started")
    store.append_run_message(run.id, "artifact", RunMessageType.ARTIFACT, "wrote artifact")
    store.append_run_message(run.id, "finish", RunMessageType.RESULT, "finished")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "run", "messages", run.id, "--since", "1"])

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert len(lines) == 2
    payloads = [json.loads(line) for line in lines]
    assert [payload["seq"] for payload in payloads] == [2, 3]
    assert payloads[0]["message_type"] == "artifact"
    assert lines[0].startswith('{"artifact_ref":')
    assert result.output.endswith("\n")


def test_run_messages_cli_rejects_unknown_run(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["--root", str(tmp_path), "run", "messages", "missing_run"])

    assert result.exit_code == 2
    assert "unknown run: missing_run" in result.output


def test_board_links_run_messages_without_inlining_body(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    board_path = export_board(store)
    board = board_path.read_text(encoding="utf-8")

    assert "| Started | Agent | Role | Attempt | Backend | Status | Messages | Summary |" in board
    assert "messages.jsonl" in board
    assert "wrote artifact" not in board


def test_kernel_demo_message_stream_resets_on_rerun(tmp_path: Path) -> None:
    first = run_demo(root=tmp_path, source_path=SOURCE_NOTE)
    store = AriadneStore(tmp_path)
    ticket = store.load_ticket(first.ticket_id)
    first_run_id = ticket.agent_run_ids[0]
    first_messages = store.list_run_messages(first_run_id)

    second = run_demo(root=tmp_path, source_path=SOURCE_NOTE)
    ticket = store.load_ticket(second.ticket_id)
    second_messages = store.list_run_messages(first_run_id)

    assert first.ticket_id == second.ticket_id
    assert len(first_messages) == len(second_messages)
    assert [message.seq for message in second_messages] == list(range(1, len(second_messages) + 1))
