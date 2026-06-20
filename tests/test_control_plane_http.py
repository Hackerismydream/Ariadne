from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.dtos import AssignTicketInput
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.models import FailureReason, InboxStatus
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


def test_control_plane_inbox_actions_create_repair_acknowledge_resolve(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_failed("provider config invalid", FailureReason.PROVIDER_CONFIG_INVALID))
    item = refresh_inbox(store)[0]
    client = TestClient(create_app(tmp_path))

    repair = client.post(f"/api/inbox/{item.id}/repair", json={"priority": "high"})
    duplicate = client.post(f"/api/inbox/{item.id}/repair", json={"priority": "high"})
    acknowledge = client.post(f"/api/inbox/{item.id}/acknowledge", json={"note": "seen"})
    resolve = client.post(f"/api/inbox/{item.id}/resolve", json={"note": "fixed"})

    assert repair.status_code == 200
    assert repair.json()["ticket"]["key"]
    assert duplicate.status_code == 200
    assert duplicate.json()["already_exists"] is True
    assert acknowledge.status_code == 200
    assert acknowledge.json()["inbox_item"]["status"] == "acknowledged"
    assert resolve.status_code == 200
    assert resolve.json()["inbox_item"]["status"] == "resolved"
    assert store.load_inbox_item(item.id).status is InboxStatus.RESOLVED


def test_control_plane_inbox_rerun_linked_assignment(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_blocked("runtime offline", FailureReason.RUNTIME_OFFLINE))
    item = refresh_inbox(store)[0]
    client = TestClient(create_app(tmp_path))

    response = client.post(f"/api/inbox/{item.id}/rerun", json={"reason": "retry from workbench"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["assignment"]["parent_assignment_id"] == assignment.id
    assert payload["assignment"]["status"] == "queued"
    assert payload["inbox_item"]["status"] == "acknowledged"
