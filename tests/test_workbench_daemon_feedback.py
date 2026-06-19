from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.models import AssignmentStatus, FailureReason
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_daemon_status_endpoint_reports_queue_without_running_daemon(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    store.create_assignment(store.resolve_ticket("ARI-003"), store.resolve_agent_profile("fake-codex"))
    client = TestClient(create_app(tmp_path))

    response = client.get("/api/daemon/status")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["runtime_id"] == "workbench-local"
    assert payload["status"] == "unknown"
    assert payload["background_running"] is False
    assert payload["open_assignment_count"] == 1
    assert payload["claimable_assignment_count"] == 0
    assert "sk-" not in response.text


def test_run_now_claims_assignment_and_projects_blocked_codex_evidence(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")
    client = TestClient(create_app(tmp_path))
    assigned = client.post(
        "/api/tickets/ARI-003/assign",
        json={
            "assignee_id": "codex",
            "assignee_kind": "agent",
            "backend_name": "codex",
            "runtime_profile": "deterministic",
            "target_project_id": project.id,
            "idempotency_key": "assign-run-now-codex",
        },
    )
    assert assigned.status_code == 200, assigned.text
    assignment_id = assigned.json()["assignment"]["id"]
    token = assigned.json()["confirmation_token"]

    result = client.post(
        f"/api/assignments/{assignment_id}/run-now",
        json={
            "confirmation_token": token,
            "timeout_seconds": 5,
            "idempotency_key": "run-now-codex",
        },
    )

    assert result.status_code == 200, result.text
    payload = result.json()
    assert payload["did_work"] is True
    assert payload["assignment"]["status"] == "blocked"
    assert payload["daemon"]["current_assignment_id"] == assignment_id
    assert payload["daemon"]["current_ticket_key"] == "ARI-003"
    assignment = store.load_assignment(assignment_id)
    assert assignment.status is AssignmentStatus.BLOCKED
    assert assignment.failure_reason is FailureReason.EXTERNAL_EXECUTION_BLOCKED

    events = client.get(f"/api/assignments/{assignment_id}/events")
    assert events.status_code == 200, events.text
    event_summaries = "\n".join(event["summary"] for event in events.json()["events"])
    assert "claim" in event_summaries
    assert "blocked" in event_summaries.lower()

    workbench = client.get("/api/workbench")
    assert workbench.status_code == 200, workbench.text
    ticket = next(item for item in workbench.json()["tickets"] if item["key"] == "ARI-003")
    evidence = ticket["evidence"]
    assert evidence["assignment_id"] == assignment_id
    assert evidence["assignment_status"] == "blocked"
    assert evidence["backend_name"] == "codex"
    assert evidence["blocked"] is True
    assert evidence["failure_reason"] == "external_execution_blocked"
    assert "ARIADNE_ENABLE_EXTERNAL_EXECUTION" in evidence["block_reason"]
    assert evidence["execution_result_id"]
    assert evidence["execution_log_artifact_path"].endswith("execution_log.json")
    assert evidence["diff_artifact_path"].endswith("git_diff.patch")
    assert evidence["review_report_id"]
    assert evidence["memory_path"].endswith(f"{ticket['id']}.json")
    assert evidence["feishu_plan_path"].endswith(".json")
    assert evidence["next_tickets_path"].endswith("next_tickets.json")
    assert "confirmation_token" not in workbench.text


def test_runtime_start_authorization_replaces_per_run_external_confirmation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setattr("ariadne_ltb.execution.shutil.which", lambda _command: None)
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")
    client = TestClient(create_app(tmp_path))

    started = client.post(
        "/api/daemon/start",
        json={
            "runtime_id": "workbench-local",
            "external_execution_authorized": True,
            "interval_seconds": 60,
        },
    )

    assert started.status_code == 200, started.text
    assert started.json()["daemon"]["external_execution_authorized"] is True

    assigned = client.post(
        "/api/tickets/ARI-003/assign",
        json={
            "assignee_id": "codex",
            "assignee_kind": "agent",
            "backend_name": "codex",
            "runtime_profile": "deterministic",
            "target_project_id": project.id,
            "idempotency_key": "assign-runtime-authorized-codex",
        },
    )
    assert assigned.status_code == 200, assigned.text
    assignment_id = assigned.json()["assignment"]["id"]
    token = assigned.json()["confirmation_token"]

    result = client.post(
        f"/api/assignments/{assignment_id}/run-now",
        json={
            "confirmation_token": token,
            "timeout_seconds": 5,
            "idempotency_key": "run-runtime-authorized-codex",
        },
    )

    assert result.status_code == 200, result.text
    execution = store.load_execution_result(result.json()["ticket_run_result"]["execution_result_id"])
    assert execution.failure_reason is FailureReason.COMMAND_UNAVAILABLE
    assert "--confirm-execution is required" not in execution.block_reason
    client.post("/api/daemon/stop", json={})


def test_stopping_daemon_clears_runtime_external_authorization(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))

    started = client.post(
        "/api/daemon/start",
        json={
            "runtime_id": "workbench-local",
            "external_execution_authorized": True,
        },
    )
    assert started.status_code == 200, started.text
    assert started.json()["daemon"]["external_execution_authorized"] is True

    stopped = client.post("/api/daemon/stop", json={})

    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["daemon"]["background_running"] is False
    assert stopped.json()["daemon"]["external_execution_authorized"] is False
