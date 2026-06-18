from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.storage import AriadneStore


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
