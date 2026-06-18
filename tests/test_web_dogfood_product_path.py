from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.interfaces.http.app import create_app


def test_web_workbench_creates_goal_sources_preview_and_tickets(tmp_path: Path) -> None:
    target = tmp_path / "mini-code-agent"
    target.mkdir()
    client = TestClient(create_app(tmp_path))

    project_response = client.post(
        "/api/target-projects",
        json={"path": str(target), "label": "Mini Code Agent"},
    )
    assert project_response.status_code == 200, project_response.text
    project_id = project_response.json()["target_project"]["id"]

    goal_response = client.post(
        "/api/goals",
        json={
            "title": "Build Mini Code Agent",
            "north_star": (
                "A folder is a builder project: external knowledge updates issues, "
                "then Codex or Claude executes approved tickets."
            ),
            "current_state": "Ariadne has a web workbench shell.",
            "target_state": "The web workbench can drive the full builder loop.",
            "target_project_id": project_id,
        },
    )
    assert goal_response.status_code == 200, goal_response.text
    goal_id = goal_response.json()["goal"]["id"]

    sources = [
        {
            "title": "minimal-agent blog",
            "source_type": "blog",
            "path_or_url": "https://minimal-agent.com/",
            "content": "Minimal agents expose trajectory, actions, observations, and tests.",
        },
        {
            "title": "mini-SWE-agent repository",
            "source_type": "github_repo",
            "path_or_url": "https://github.com/SWE-agent/mini-SWE-agent",
            "content": "mini-SWE-agent is a compact reference for code-agent loops.",
        },
        {
            "title": "MiniCode repository",
            "source_type": "github_repo",
            "path_or_url": "https://github.com/LiuMengxuan04/MiniCode",
            "content": "MiniCode is a local mini code-agent implementation reference.",
        },
    ]
    source_ids: list[str] = []
    for source in sources:
        response = client.post("/api/sources", json=source)
        assert response.status_code == 200, response.text
        source_ids.append(response.json()["source"]["id"])

    preview_response = client.post(
        "/api/issue-factory/preview",
        json={"goal_id": goal_id, "source_ids": source_ids, "target_project_id": project_id},
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()["preview"]
    assert len(preview["operations"]) >= 6
    assert any("Mini Code Agent" in operation["title"] for operation in preview["operations"])

    apply_response = client.post(f"/api/issue-factory/{preview['id']}/apply", json={})
    assert apply_response.status_code == 200, apply_response.text
    assert len(apply_response.json()["created_ticket_ids"]) >= 6

    workbench = client.get("/api/workbench")
    assert workbench.status_code == 200, workbench.text
    payload = workbench.json()
    assert payload["goals"][0]["id"] == goal_id
    assert len(payload["sources"]) >= 3
    assert {"minimal-agent blog", "mini-SWE-agent repository", "MiniCode repository"}.issubset(
        {source["title"] for source in payload["sources"]}
    )
    assert any(ticket["title"] == "Implement Issue Factory for Mini Code Agent" for ticket in payload["tickets"])
    assert payload["backlog_previews"][0]["applied_update_id"]
    generated = next(ticket for ticket in payload["tickets"] if ticket["title"] == "Implement Mini Code Agent workspace model")
    assert generated["target_project_id"] == project_id
    assert generated["acceptance_criteria"]
    assert generated["affected_modules"]


def test_frontend_api_adapter_does_not_spread_fixture_data() -> None:
    data_ts = Path("frontend/ariadne-workbench/src/data.ts").read_text(encoding="utf-8")
    adapt_start = data_ts.index("function adaptApiWorkbench")
    adapt_end = data_ts.index("function adaptTicket")
    adapt_body = data_ts[adapt_start:adapt_end]

    assert "...workbenchData" not in adapt_body
    assert "workbenchData.tickets[0]" not in data_ts[data_ts.index("function adaptTicket"): data_ts.index("function adaptTicketStatus")]
