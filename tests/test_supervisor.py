from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import AssignmentStatus, FailureReason, TicketStatus
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_supervisor_run_once_recovers_and_dispatches_without_daemon(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_failed("provider config invalid", FailureReason.PROVIDER_CONFIG_INVALID))

    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "supervisor",
            "run-once",
            "--to",
            "fake-codex",
            "--runtime-profile",
            "deterministic",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["inbox_count"] == 1
    assert payload["recovery"]["created_ticket_count"] == 1
    assert payload["dispatch"]["assigned_count"] == 1
    assert payload["daemon"] is None

    dispatched = payload["dispatch"]["assignments"][0]
    repair_ticket = store.resolve_ticket(dispatched["ticket_key"])
    repair_assignment = store.load_assignment(dispatched["assignment_id"])
    assert repair_ticket.metadata["generated_from_inbox_item_id"]
    assert repair_ticket.status is TicketStatus.READY_FOR_EXECUTION
    assert repair_assignment.status is AssignmentStatus.QUEUED
    assert repair_assignment.assigned_by == "inbox_recovery"


def test_supervisor_run_once_can_skip_recovery_and_dispatch(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "supervisor",
            "run-once",
            "--no-recover",
            "--no-dispatch",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["inbox_count"] == 0
    assert payload["recovery"] is None
    assert payload["dispatch"] is None
    assert payload["daemon"] is None


def test_supervisor_run_once_can_poll_daemon_without_work(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "supervisor",
            "run-once",
            "--no-recover",
            "--no-dispatch",
            "--run-daemon",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["daemon"]["did_work"] is False
    assert payload["daemon"]["status"] == "no_work"


def test_supervisor_loop_recovers_dispatches_then_stops_idle(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_failed("provider quota exhausted", FailureReason.QUOTA_EXCEEDED))

    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "supervisor",
            "loop",
            "--to",
            "fake-codex",
            "--runtime-profile",
            "deterministic",
            "--max-cycles",
            "3",
            "--interval-seconds",
            "0",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["stop_reason"] == "idle"
    assert payload["cycle_count"] == 2
    assert payload["cycles"][0]["action_count"] == 2
    assert payload["cycles"][0]["result"]["recovery"]["created_ticket_count"] == 1
    assert payload["cycles"][0]["result"]["dispatch"]["assigned_count"] == 1
    assert payload["cycles"][1]["action_count"] == 0

    report_path = Path(payload["report_path"])
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["stop_reason"] == "idle"
    assert report["cycle_count"] == 2


def test_supervisor_loop_can_run_fixed_idle_cycles(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "supervisor",
            "loop",
            "--no-recover",
            "--no-dispatch",
            "--max-cycles",
            "2",
            "--stop-after-idle-cycles",
            "0",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["stop_reason"] == "max_cycles"
    assert payload["cycle_count"] == 2
    assert [cycle["status"] for cycle in payload["cycles"]] == ["idle", "idle"]
