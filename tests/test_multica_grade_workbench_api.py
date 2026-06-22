from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.application.dtos import CreateProjectGoalInput
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.models import FailureReason, TicketStatus
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def _prepared_store(tmp_path: Path) -> tuple[AriadneStore, str]:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    project = TargetProjectRegistry(store).register(ensure_demo_target_project(tmp_path), "Demo Target")
    ProjectGoalService(store).create(
        CreateProjectGoalInput(
            title="Demo current version",
            north_star="Deliver one scoped current version issue.",
            target_project_id=project.id,
        )
    )
    current = store.resolve_ticket("ARI-003")
    store.save_ticket(
        current.model_copy(
            deep=True,
            update={"metadata": current.metadata | {"target_project_id": project.id}},
        )
    )
    outside = store.resolve_ticket("ARI-001")
    store.save_ticket(
        outside.model_copy(
            deep=True,
            update={"metadata": outside.metadata | {"target_project_id": "outside-project"}},
        )
    )
    return store, project.id


def test_issues_endpoint_returns_current_version_mainline_tickets(tmp_path: Path) -> None:
    _prepared_store(tmp_path)
    client = TestClient(create_app(tmp_path))

    response = client.get("/api/issues")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["schema_version"] == "ariadne.issues.v1"
    keys = [item["key"] for item in payload["issues"]]
    assert keys == ["ARI-003"]
    assert payload["source"] == "build_ticket_projection"
    issue = payload["issues"][0]
    assert issue["id"]
    assert issue["target_version"] == "Demo current version"
    assert issue["source_count"] >= 1


def test_issue_detail_timeline_and_comment_facade(tmp_path: Path) -> None:
    store, _project_id = _prepared_store(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    store.save_ticket(ticket.with_status(TicketStatus.PLANNING, "test", "planning started"))
    client = TestClient(create_app(tmp_path))

    comment = client.post(
        "/api/issues/ARI-003/comments",
        json={"body": "Human review note", "idempotency_key": "phase2-comment"},
    )
    detail = client.get("/api/issues/ARI-003")
    timeline = client.get("/api/issues/ARI-003/timeline")

    assert comment.status_code == 200, comment.text
    assert comment.json()["comment"]["body"] == "Human review note"
    assert detail.status_code == 200, detail.text
    issue = detail.json()["issue"]
    assert issue["key"] == "ARI-003"
    assert issue["body"]
    assert issue["comments"]
    assert any(event["event_type"] == "status_changed" for event in issue["timeline"])
    assert timeline.status_code == 200, timeline.text
    assert timeline.json()["ticket"]["key"] == "ARI-003"


def test_issue_patch_and_assignment_action_facades_reuse_existing_services(tmp_path: Path) -> None:
    store, project_id = _prepared_store(tmp_path)
    client = TestClient(create_app(tmp_path))

    patched = client.patch(
        "/api/issues/ARI-003",
        json={"priority": "high", "status": "planning", "title": "Scoped current issue"},
    )
    assigned = client.post(
        "/api/issues/ARI-003/assign",
        json={
            "assignee_id": "codex",
            "assignee_kind": "agent",
            "backend_name": "codex",
            "runtime_profile": "production",
            "target_project_id": project_id,
            "idempotency_key": "phase2-assign",
        },
    )

    assert patched.status_code == 200, patched.text
    assert patched.json()["issue"]["priority"] == "high"
    assert patched.json()["issue"]["title"] == "Scoped current issue"
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assignment"]["ticket_key"] == "ARI-003"
    assert store.resolve_ticket("ARI-003").metadata["latest_assignment_id"] == assigned.json()["assignment"]["id"]


def test_inbox_runtime_team_projects_and_snapshot_endpoints(tmp_path: Path) -> None:
    store, _project_id = _prepared_store(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("codex"))
    store.save_assignment(assignment.mark_blocked("external execution gate closed", FailureReason.EXTERNAL_EXECUTION_BLOCKED))
    client = TestClient(create_app(tmp_path))

    endpoints = {
        "/api/inbox": "ariadne.inbox.v1",
        "/api/runs/runtimes": "ariadne.runs-runtimes.v1",
        "/api/team/agents": "ariadne.team-agents.v1",
        "/api/team/build-teams": "ariadne.build-teams.v1",
        "/api/team/skills": "ariadne.team-skills.v1",
        "/api/projects": "ariadne.projects.v1",
        "/api/runs/assignments": "ariadne.runs-assignments.v1",
        "/api/agent-task-snapshot": "ariadne.agent-task-snapshot.v1",
    }

    payloads = {}
    for endpoint, schema_version in endpoints.items():
        response = client.get(endpoint)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["schema_version"] == schema_version
        payloads[endpoint] = payload

    assert payloads["/api/inbox"]["inbox"][0]["issue_key"] == "ARI-003"
    assert payloads["/api/inbox"]["inbox"][0]["failure_reason"] == "external_execution_blocked"
    assert payloads["/api/runs/runtimes"]["runtimes"]
    assert all(runtime["backend_name"] != "fake-codex" for runtime in payloads["/api/runs/runtimes"]["runtimes"])
    assert all(agent["id"] != "fake-codex" for agent in payloads["/api/team/agents"]["agents"])
    assert payloads["/api/projects"]["projects"][0]["id"]
    assert payloads["/api/runs/assignments"]["assignments"][0]["ticket_key"] == "ARI-003"
    assert payloads["/api/agent-task-snapshot"]["snapshot"]["blocked_count"] == 1


def test_project_detail_endpoint(tmp_path: Path) -> None:
    _store, project_id = _prepared_store(tmp_path)
    client = TestClient(create_app(tmp_path))

    response = client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["schema_version"] == "ariadne.project-detail.v1"
    assert payload["project"]["id"] == project_id


def test_issue_run_facades_report_missing_assignment(tmp_path: Path) -> None:
    _prepared_store(tmp_path)
    client = TestClient(create_app(tmp_path))

    rerun = client.post("/api/issues/ARI-003/rerun", json={"confirmation_token": "unused"})
    run_now = client.post("/api/issues/ARI-003/run-now", json={"confirmation_token": "unused"})

    assert rerun.status_code == 404
    assert run_now.status_code == 404
