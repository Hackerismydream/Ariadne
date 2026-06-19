from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.models import BuildTicket, TicketStatus
from ariadne_ltb.storage import AriadneStore


def test_apply_stale_preview_returns_409(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    target = tmp_path / "mini-code-agent"
    target.mkdir()
    project_response = client.post("/api/target-projects", json={"path": str(target), "label": "Mini Code Agent"})
    project_id = project_response.json()["target_project"]["id"]
    goal_response = client.post(
        "/api/goals",
        json={
            "title": "Build Mini Code Agent",
            "north_star": "Build a Python mini code agent MVP for local AI Builders.",
            "target_project_id": project_id,
        },
    )
    goal_id = goal_response.json()["goal"]["id"]
    source_response = client.post(
        "/api/sources",
        json={
            "title": "minimal-agent blog",
            "source_type": "blog",
            "source_role": "requirement_source",
            "path_or_url": "https://minimal-agent.com/",
            "content": "Minimal agents loop through model, action, observation.",
        },
    )
    source_id = source_response.json()["source"]["id"]
    client.post(f"/api/sources/{source_id}/analyze", json={})
    preview = client.post(
        "/api/issue-factory/preview",
        json={"goal_id": goal_id, "source_ids": [source_id], "target_project_id": project_id},
    ).json()["preview"]

    # Change the backlog after preview creation.
    AriadneStore(tmp_path).save_ticket(
        BuildTicket(
            id="ticket_external_change",
            key="MCA-999",
            title="External change",
            description="Simulate another tab applying a backlog change.",
            source_type="note",
            source_ref="test",
            status=TicketStatus.PLANNING,
        )
    )

    response = client.post(f"/api/issue-factory/{preview['id']}/apply", json={})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stale_preview"
    assert "Regenerate" in response.json()["error"]["message"]
