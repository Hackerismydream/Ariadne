from __future__ import annotations

from fastapi.testclient import TestClient

from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.storage import AriadneStore


def test_create_source_can_auto_analyze_github_repo(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/sources",
        json={
            "title": "SWE-agent/mini-swe-agent",
            "source_type": "github_repo",
            "source_role": "reference_project",
            "path_or_url": "https://github.com/SWE-agent/mini-swe-agent/",
            "summary": "Reference repo",
            "content": "Reference for minimal SWE agent loop, tools, trajectory, and tests.",
            "auto_analyze": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["duplicate"] is False
    assert payload["source"]["analysis_status"] == "analyzed"
    assert payload["source"]["artifact_ids"]
    store = AriadneStore(tmp_path)
    assert store.list_source_artifacts(payload["source"]["id"])
    assert store.list_source_evidence(payload["source"]["id"])


def test_create_source_normalizes_duplicate_github_urls(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    first = {
        "title": "mini-SWE-agent",
        "source_type": "github_repo",
        "source_role": "reference_project",
        "path_or_url": "https://github.com/SWE-agent/mini-SWE-agent",
        "summary": "reference",
        "auto_analyze": False,
    }
    second = {
        **first,
        "title": "SWE-agent/mini-swe-agent",
        "path_or_url": "https://github.com/SWE-agent/mini-swe-agent/",
    }

    first_response = client.post("/api/sources", json=first)
    second_response = client.post("/api/sources", json=second)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["source"]["id"] == first_response.json()["source"]["id"]
    assert second_response.json()["duplicate"] is True
