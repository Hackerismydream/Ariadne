from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.daemon import is_stale_heartbeat
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import DaemonStatus, WorkerHeartbeat
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_run_once_writes_worker_heartbeat(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"],
    )
    assert assign.exit_code == 0, assign.output

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "daemon", "run-once", "--runtime-id", "test-worker"],
    )

    heartbeat = store.load_worker_heartbeat("test-worker")
    assert result.exit_code == 0, result.output
    assert heartbeat.runtime_id == "test-worker"
    assert heartbeat.status in {DaemonStatus.STOPPED, DaemonStatus.IDLE, DaemonStatus.RUNNING}
    assert heartbeat.current_assignment_id
    assert heartbeat.current_ticket_key == "ARI-003"
    assert heartbeat.current_stage in {"done", "board", "stopped"}


def test_run_once_can_claim_specific_assignment(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    first = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"],
    )
    second = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"],
    )
    first_id = _assignment_id_from_output(first.output)
    second_id = _assignment_id_from_output(second.output)

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "daemon",
            "run-once",
            "--assignment-id",
            second_id,
        ],
    )

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert result.exit_code == 0, result.output
    assert f"Assignment claimed: {second_id}" in result.output
    assert store.load_assignment(first_id).status.value == "ready_to_claim"
    assert store.load_assignment(second_id).status.value == "done"


def test_daemon_status_shows_heartbeat_and_counts(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    heartbeat = WorkerHeartbeat.new(runtime_id="visible-worker", status=DaemonStatus.IDLE)
    store.save_worker_heartbeat(heartbeat)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "daemon", "status"])

    assert result.exit_code == 0, result.output
    assert "runtime_id: visible-worker" in result.output
    assert "status: idle" in result.output
    assert "stale:" in result.output
    assert "open assignments:" in result.output


def test_list_worker_heartbeats_ignores_partial_or_invalid_files(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    store.save_worker_heartbeat(WorkerHeartbeat.new(runtime_id="valid-worker", status=DaemonStatus.IDLE))
    (tmp_path / ".ariadne" / "daemon" / "heartbeats" / "partial.json").write_text("", encoding="utf-8")

    heartbeats = store.list_worker_heartbeats()

    assert [heartbeat.runtime_id for heartbeat in heartbeats] == ["valid-worker"]


def test_stale_heartbeat_by_old_timestamp_and_dead_pid() -> None:
    heartbeat = WorkerHeartbeat(
        runtime_id="stale-worker",
        pid=999999,
        status=DaemonStatus.RUNNING,
        started_at="2000-01-01T00:00:00Z",
        heartbeat_at="2000-01-01T00:00:00Z",
    )

    assert is_stale_heartbeat(heartbeat, stale_after_seconds=1) is True


def test_daemon_start_max_iterations_does_not_block(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "daemon",
            "start",
            "--runtime-id",
            "loop-test",
            "--max-iterations",
            "1",
            "--interval",
            "0",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "daemon loop finished" in result.output
    data = json.loads(
        (tmp_path / ".ariadne" / "daemon" / "heartbeats" / "loop-test.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["runtime_id"] == "loop-test"


def _assignment_id_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("Assignment created:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError(output)
