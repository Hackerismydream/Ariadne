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


def test_http_assign_rejects_command_and_local_path_fields(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/api/tickets/ARI-003/assign",
        json={
            "assignee_id": "build-team",
            "backend_name": "codex",
            "runtime_profile": "production",
            "target_project_id": project.id,
            "command": "echo unsafe",
            "target_repo_path": str(target),
        },
    )

    assert response.status_code == 422
    assert "command" in response.text
    assert "target_repo_path" in response.text


def test_http_comment_rejects_client_author_field(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/api/tickets/ARI-003/comments",
        json={
            "body": "browser feedback",
            "author": "not-human",
            "idempotency_key": "comment-author-rejected",
        },
    )

    assert response.status_code == 422
    assert "author" in response.text
