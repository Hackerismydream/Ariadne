from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board import export_board
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.local_safety import DirectoryLock
from ariadne_ltb.models import AgentRun, AgentRunStatus, StoreInvariantReason, stable_id
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_store_doctor_reports_clean_full_loop_and_board_summary(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "store"])

    assert result.exit_code == 0, result.output
    assert "store invariants: ok" in result.output
    assert "errors: 0" in result.output
    assert (tmp_path / ".ariadne" / "doctor" / "store_invariants.json").exists()

    board = export_board(store).read_text(encoding="utf-8")
    assert "## Store Invariants" in board
    assert "- Status: `ok`" in board


def test_store_doctor_json_output_is_machine_readable(tmp_path: Path) -> None:
    AriadneStore(tmp_path)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "store", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["issues"] == []


def test_store_doctor_detects_duplicate_ticket_keys(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    tickets = ingest_sources(store, SOURCE_FIXTURES)
    duplicate = tickets[1].model_copy(update={"id": "ticket_duplicate_key", "key": tickets[0].key})
    store.save_ticket(duplicate)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "store"])

    assert result.exit_code == 2
    assert StoreInvariantReason.DUPLICATE_TICKET_KEY.value in result.output


def test_store_doctor_detects_malformed_json_and_jsonl(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    (store.tickets_dir / "broken.json").write_text("{not json", encoding="utf-8")
    (store.journal_path).write_text('{"ok": true}\n{not jsonl\n', encoding="utf-8")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "store", "--json"])

    assert result.exit_code == 2
    payload = json.loads(result.output)
    reasons = {issue["reason"] for issue in payload["issues"]}
    assert StoreInvariantReason.MALFORMED_JSON.value in reasons
    assert StoreInvariantReason.MALFORMED_JSONL.value in reasons


def test_store_doctor_detects_missing_packet_artifact_run_and_bad_lifecycle(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, SOURCE_FIXTURES)[0]
    broken_run = AgentRun(
        id=stable_id("run", ticket.id, "broken"),
        ticket_id=ticket.id,
        agent_name="Execution",
        agent_role="execution",
        input_summary="Broken terminal run.",
        status=AgentRunStatus.SUCCEEDED,
    )
    store.save_run(broken_run)
    ticket = ticket.model_copy(
        update={
            "build_packet_id": "missing_packet",
            "agent_run_ids": ["missing_run", broken_run.id],
            "artifact_ids": ["missing_artifact"],
        }
    )
    store.save_ticket(ticket)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "store"])

    assert result.exit_code == 2
    for reason in [
        StoreInvariantReason.MISSING_BUILD_PACKET.value,
        StoreInvariantReason.MISSING_AGENT_RUN.value,
        StoreInvariantReason.MISSING_ARTIFACT_INDEX.value,
        StoreInvariantReason.INVALID_RUN_LIFECYCLE.value,
    ]:
        assert reason in result.output


def test_store_doctor_reports_stale_locks_as_warning(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    lock = DirectoryLock(store, target, runtime_id="test-worker")
    lock.acquire()
    try:
        metadata = json.loads(lock.lock_path.read_text(encoding="utf-8"))
        metadata["heartbeat_at"] = "2000-01-01T00:00:00Z"
        lock.lock_path.write_text(json.dumps(metadata), encoding="utf-8")

        result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "store"])
    finally:
        lock.release()

    assert result.exit_code == 0, result.output
    assert "warnings: 1" in result.output
    assert StoreInvariantReason.STALE_LOCK.value in result.output

