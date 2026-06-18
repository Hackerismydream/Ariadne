from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_control_plane_api_supports_frontend_assign_run_watch_comment_flow(
    tmp_path: Path,
) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")
    client = TestClient(create_app(tmp_path))

    assigned = client.post(
        "/api/tickets/ARI-003/assign",
        json={
            "assignee_id": "build-team",
            "assignee_kind": "build_team",
            "backend_name": "fake-codex",
            "runtime_profile": "deterministic",
            "target_project_id": project.id,
            "idempotency_key": "assign-e2e",
        },
        headers={"X-Ignored": "not-test-mode"},
    )
    assert assigned.status_code == 422

    assigned = client.post(
        "/api/tickets/ARI-003/assign",
        json={
            "assignee_id": "build-team",
            "assignee_kind": "build_team",
            "backend_name": "codex",
            "runtime_profile": "production",
            "target_project_id": project.id,
            "idempotency_key": "assign-e2e-product",
        },
    )
    assert assigned.status_code == 200, assigned.text
    assignment_id = assigned.json()["assignment"]["id"]
    token = assigned.json()["confirmation_token"]

    watched = client.get(f"/api/assignments/{assignment_id}/events")
    assert watched.status_code == 200, watched.text
    assert watched.json()["events"]

    comment = client.post(
        "/api/tickets/ARI-003/comments",
        json={
            "body": "frontend feedback",
            "assignment_id": assignment_id,
            "idempotency_key": "comment-e2e-product",
        },
    )
    assert comment.status_code == 200, comment.text

    run = client.post(
        f"/api/assignments/{assignment_id}/run",
        json={
            "confirmation_token": token,
            "timeout_seconds": 1,
            "idempotency_key": "run-e2e-product",
        },
    )
    assert run.status_code == 200, run.text
    assert "confirmation_token" not in client.get("/api/workbench").text
