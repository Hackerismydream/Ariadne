from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.interfaces.http.app import create_app


def test_web_workbench_creates_goal_sources_preview_and_tickets(tmp_path: Path) -> None:
    target = tmp_path / "mini-code-agent"
    target.mkdir()
    mini_swe_repo = _reference_repo(tmp_path / "mini-swe-agent", "mini-SWE-agent")
    minicode_repo = _reference_repo(tmp_path / "minicode", "MiniCode")
    client = TestClient(create_app(tmp_path))

    version_response = client.post(
        "/api/project-versions",
        json={
            "target_repo_path": str(target),
            "target_repo_label": "Mini Code Agent",
            "version_label": "v0.1",
            "goal_title": "Build Mini Code Agent",
            "goal_north_star": (
                "A folder is a builder project: external knowledge updates issues, "
                "then Codex or Claude executes approved tickets."
            ),
            "target_state": "The web workbench can drive the full builder loop.",
            "issue_prefix": "MCA",
        },
    )
    assert version_response.status_code == 200, version_response.text
    project_version = version_response.json()["project_version"]
    project_id = project_version["target_project_id"]
    goal_id = project_version["goal_id"]

    sources = [
        {
            "title": "minimal-agent blog",
            "source_type": "blog",
            "source_role": "requirement_source",
            "path_or_url": "https://minimal-agent.com/",
            "content": "Minimal agents expose trajectory, actions, observations, and tests.",
        },
        {
            "title": "mini-SWE-agent repository",
            "source_type": "github_repo",
            "source_role": "reference_project",
            "path_or_url": str(mini_swe_repo),
            "content": "mini-SWE-agent is a compact reference for code-agent loops.",
        },
        {
            "title": "MiniCode repository",
            "source_type": "github_repo",
            "source_role": "reference_project",
            "path_or_url": str(minicode_repo),
            "content": "MiniCode is a local mini code-agent implementation reference.",
        },
    ]
    source_ids: list[str] = []
    for source in sources:
        response = client.post("/api/sources", json=source)
        assert response.status_code == 200, response.text
        source_id = response.json()["source"]["id"]
        source_ids.append(source_id)
        analyze = client.post(f"/api/sources/{source_id}/analyze", json={})
        assert analyze.status_code == 200, analyze.text
        assert analyze.json()["result"]["status"] == "analyzed"

    preview_response = client.post(
        "/api/issue-factory/preview",
        json={"goal_id": goal_id, "source_ids": source_ids, "target_project_id": project_id},
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()["preview"]
    assert [operation["ticket_key"] for operation in preview["operations"][:10]] == [
        "MCA-001",
        "MCA-002",
        "MCA-003",
        "MCA-004",
        "MCA-005",
        "MCA-006",
        "MCA-007",
        "MCA-008",
        "MCA-009",
        "MCA-010",
    ]
    assert {operation["title"] for operation in preview["operations"]}.issuperset(
        {
            "Bootstrap Python package and CLI",
            "Add DeepSeek-backed LLM client configuration",
            "Define tool protocol and model action schema",
            "Implement shell command tool with allowlist",
            "Implement file read and patch tools with review-before-write safety",
            "Implement agent loop: prompt -> action -> observation -> repeat",
            "Persist session trace and run summary",
            "Capture git diff and test result",
            "Add minimal reviewer checks for task completion",
            "Write README quickstart and usage examples",
        }
    )
    for operation in preview["operations"]:
        assert operation["target_project_id"] == project_id
        assert operation["build_context_id"]
        assert operation["evidence_refs"]
        assert operation["acceptance_criteria"]
        assert operation["affected_modules"]

    apply_response = client.post(f"/api/issue-factory/{preview['id']}/apply", json={})
    assert apply_response.status_code == 200, apply_response.text
    assert len(apply_response.json()["created_ticket_ids"]) >= 10

    workbench = client.get("/api/workbench")
    assert workbench.status_code == 200, workbench.text
    payload = workbench.json()
    assert payload["current_project_version"]["goal_id"] == goal_id
    assert payload["current_project_version"]["version_label"] == "v0.1"
    assert len(payload["sources"]) >= 3
    assert payload["source_artifacts"]
    assert payload["source_evidence"]
    assert {"minimal-agent blog", "mini-SWE-agent repository", "MiniCode repository"}.issubset(
        {source["title"] for source in payload["sources"]}
    )
    assert any(ticket["key"] == "MCA-001" and ticket["title"] == "Bootstrap Python package and CLI" for ticket in payload["tickets"])
    assert payload["backlog_previews"][0]["applied_update_id"]
    generated = next(ticket for ticket in payload["tickets"] if ticket["key"] == "MCA-001")
    assert generated["target_project_id"] == project_id
    assert generated["acceptance_criteria"]
    assert generated["affected_modules"]


def _reference_repo(path: Path, title: str) -> Path:
    path.mkdir()
    (path / "README.md").write_text(
        f"# {title}\n\nCLI coding assistant with action/observation loop, diff review, and test result capture.",
        encoding="utf-8",
    )
    (path / "pyproject.toml").write_text(
        "[project]\nname='reference'\n[project.scripts]\nreference='reference.cli:main'\n",
        encoding="utf-8",
    )
    (path / "reference").mkdir()
    (path / "reference" / "cli.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    (path / "tests").mkdir()
    (path / "tests" / "test_cli.py").write_text("def test_cli():\n    assert True\n", encoding="utf-8")
    return path


def test_frontend_api_adapter_does_not_spread_fixture_data() -> None:
    data_ts = Path("frontend/ariadne-workbench/src/data.ts").read_text(encoding="utf-8")
    adapt_start = data_ts.index("function adaptApiWorkbench")
    adapt_end = data_ts.index("function adaptTicket")
    adapt_body = data_ts[adapt_start:adapt_end]

    assert "...workbenchData" not in adapt_body
    assert "workbenchData.tickets[0]" not in data_ts[data_ts.index("function adaptTicket"): data_ts.index("function adaptTicketStatus")]
