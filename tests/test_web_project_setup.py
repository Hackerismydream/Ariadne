from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.interfaces.http.app import create_app


def test_target_project_can_create_missing_folder_and_init_git(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "store"))
    target = tmp_path / "mini-code-agent"

    response = client.post(
        "/api/target-projects",
        json={
            "path": str(target),
            "label": "Mini Code Agent",
            "create_if_missing": True,
            "init_git": True,
            "test_command": "python3.11 -m pytest",
            "issue_prefix": "MCA",
        },
    )

    assert response.status_code == 200, response.text
    assert target.exists()
    assert (target / ".git").exists()
    payload = response.json()["target_project"]
    assert payload["metadata"]["test_command"] == "python3.11 -m pytest"
    assert payload["metadata"]["issue_prefix"] == "MCA"


def test_target_project_missing_path_returns_product_error(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "store"))
    target = tmp_path / "missing"

    response = client.post(
        "/api/target-projects",
        json={"path": str(target), "label": "Missing"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "target_path_missing"
    assert response.json()["error"]["details"]["action"] == "create_folder"
