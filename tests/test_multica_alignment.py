from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.local_safety import DirectoryLock, validate_target_repo_path
from ariadne_ltb.models import (
    AgentRun,
    AgentRunLifecycleState,
    AgentRunStatus,
    ArtifactType,
    FailureReason,
    ProjectResource,
    RuntimeCapability,
)
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.skills import discover_build_skills
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project
from ariadne_ltb.ingest import ingest_sources


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_required_multica_alignment_docs_exist() -> None:
    required = [
        ROOT / "docs" / "architecture" / "multica_architecture_digest.md",
        ROOT / "docs" / "architecture" / "ariadne_multica_gap_report.md",
        ROOT / "docs" / "adr" / "ADR-0002-multica-architecture-alignment.md",
        ROOT / "docs" / "smoke_test_results" / "ARI-004-real-codex-summary.md",
    ]

    for path in required:
        assert path.exists(), path
        text = path.read_text(encoding="utf-8")
        assert "multica-ai/multica" in text or "Multica" in text


def test_failure_reason_wire_values_and_terminal_run_invariants() -> None:
    assert FailureReason.RUNTIME_OFFLINE.value == "runtime_offline"
    assert FailureReason.RUNTIME_RECOVERY.value == "runtime_recovery"
    assert FailureReason.TIMEOUT.value == "timeout"
    assert FailureReason.AGENT_ERROR.value == "agent_error"
    assert FailureReason.INVALID_RESOURCE.value == "invalid_resource"
    assert FailureReason.RESOURCE_LOCKED.value == "resource_locked"

    run = AgentRun(
        id="run_demo",
        ticket_id="ticket_demo",
        agent_name="Execution",
        agent_role="execution",
        input_summary="Run ticket.",
    )
    running = run.mark_running()
    assert running.lifecycle_state is AgentRunLifecycleState.RUNNING

    with pytest.raises(ValueError, match="terminal"):
        running.mark_finished(AgentRunStatus.RUNNING)

    blocked = running.mark_finished(
        AgentRunStatus.BLOCKED,
        "Invalid path.",
        failure_reason=FailureReason.INVALID_RESOURCE,
    )
    assert blocked.lifecycle_state is AgentRunLifecycleState.TERMINAL
    assert blocked.failure_reason is FailureReason.INVALID_RESOURCE


def test_runtime_capability_snapshot_and_backend_doctor_secret_safety(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "never-print-this")
    runner = CliRunner()

    result = runner.invoke(app, ["--root", str(tmp_path), "backend", "doctor"])

    assert result.exit_code == 0, result.output
    assert "never-print-this" not in result.output
    snapshot_path = tmp_path / ".ariadne" / "runtimes" / "capability_snapshot.json"
    assert snapshot_path.exists()
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert any(item["backend_name"] == "fake-codex" for item in data["capabilities"])
    RuntimeCapability.model_validate(data["capabilities"][0])


def test_project_resources_serialize_and_target_path_validation(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    target = ensure_demo_target_project(tmp_path)
    resource = ProjectResource.local_directory(
        project_id="ariadne-local",
        local_path=target,
        label="demo target",
    )
    store.save_project_resources([resource])

    loaded = store.load_project_resources()
    assert loaded[0].resource_type == "local_directory"
    assert loaded[0].resource_ref["local_path"] == str(target)
    assert validate_target_repo_path(target).valid is True
    assert validate_target_repo_path("/").valid is False
    assert validate_target_repo_path(Path.home()).valid is False
    assert validate_target_repo_path("/tmp").valid is False


def test_directory_lock_serializes_same_resolved_path(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    target = tmp_path / "repo"
    target.mkdir()
    first = DirectoryLock(store, target)
    second = DirectoryLock(store, target)

    first.acquire()
    try:
        with pytest.raises(RuntimeError, match="locked"):
            second.acquire()
    finally:
        first.release()

    second.acquire()
    second.release()


def test_build_skill_discovery_and_handoff_references(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    tickets = ingest_sources(store, SOURCE_FIXTURES)
    result = TicketRunOrchestrator(store).run_ticket(tickets[2].key, backend_name="fake-codex")

    skills = discover_build_skills(ROOT)
    names = {skill.name for skill in skills}
    handoff = store.read_artifact_text(store.load_artifact(result.handoff_artifact_id))

    assert {"codex-handoff", "review-diff", "feishu-write-plan"}.issubset(names)
    assert "## Skills" in handoff
    assert "codex-handoff" in handoff
    assert "review-diff" in handoff


def test_route_decision_artifact_progress_events_and_board(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    result = TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")
    ticket = store.load_ticket(result.ticket_id)
    artifacts = [store.load_artifact(artifact_id) for artifact_id in ticket.artifact_ids]
    route = [artifact for artifact in artifacts if artifact.artifact_type is ArtifactType.ROUTE_DECISION]
    board = Path(result.board_path).read_text(encoding="utf-8")
    event_types = [event.event_type for event in ticket.event_log]

    assert route
    route_json = json.loads(Path(route[-1].path).read_text(encoding="utf-8"))
    assert route_json["backend_name"] == "fake-codex"
    assert "route_decision" in event_types
    assert "execution_started" in event_types
    assert "review_finished" in event_types
    assert "board_exported" in event_types
    assert "### Runtime Capability" in board
    assert "### Route Decision" in board
    assert "### Project Resources" in board
    assert "### Build Skills" in board
    assert "### Progress Events" in board
