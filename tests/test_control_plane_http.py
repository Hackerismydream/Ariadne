from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.dtos import AssignTicketInput
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_control_plane_health_and_workbench(tmp_path: Path) -> None:
    ingest_sources(AriadneStore(tmp_path), SOURCE_FIXTURES)
    client = TestClient(create_app(tmp_path))

    assert client.get("/health").json() == {"status": "ok"}
    workbench = client.get("/api/workbench")
    assert workbench.status_code == 200
    assert workbench.json()["schema_version"] == "ariadne.workbench.v1"


def test_control_plane_mutation_requires_json(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))

    response = client.post("/api/target-projects", content="not-json")

    assert response.status_code == 415


def test_assignment_websocket_streams_initial_events(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = TargetProjectRegistry(store).register(ensure_demo_target_project(tmp_path), "Demo Target")
    assigned = AssignTicketService(store).assign(
        "ARI-003",
        AssignTicketInput(
            assignee_id="codex",
            assignee_kind="agent",
            backend_name="codex",
            runtime_profile="production",
            target_project_id=target.id,
            idempotency_key="ws-assign",
        ),
        source="http",
    )
    client = TestClient(create_app(tmp_path))

    with client.websocket_connect(f"/ws/assignments/{assigned.assignment.id}") as websocket:
        payload = websocket.receive_json()

    assert payload["schema_version"] == "ariadne.assignment-events.v1"
    assert payload["assignment"]["id"] == assigned.assignment.id
    assert payload["events"]
    assert "confirmation_token" not in str(payload)


def test_workbench_static_dist_can_be_served(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<main>Ariadne Workbench</main>", encoding="utf-8")
    client = TestClient(create_app(tmp_path, serve_workbench=True, frontend_dist=dist))

    response = client.get("/")

    assert response.status_code == 200
    assert "Ariadne Workbench" in response.text
