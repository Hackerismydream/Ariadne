from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.llm import DeepSeekClient
from ariadne_ltb.models import ArtifactType
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


class FakeTransport:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.payload: dict[str, Any] = {}

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        self.payload = payload
        return self.response


def test_ticket_run_llm_backlog_missing_key_writes_blocked_artifact_and_falls_back(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    runner = CliRunner()
    ingest = runner.invoke(
        app,
        ["--root", str(tmp_path), "ingest", *[str(path) for path in SOURCE_FIXTURES]],
    )

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "ticket",
            "run",
            "ARI-003",
            "--backend",
            "fake-codex",
            "--backlog-planner",
            "llm",
        ],
    )

    assert ingest.exit_code == 0, ingest.output
    assert result.exit_code == 0, result.output
    assert "backlog planner: llm" in result.output
    assert "backlog planner artifact:" in result.output
    store = AriadneStore(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    artifact_paths = [
        Path(store.load_artifact(artifact_id).path)
        for artifact_id in ticket.artifact_ids
        if store.load_artifact(artifact_id).artifact_type is ArtifactType.NEXT_TICKETS
    ]
    blocked_artifacts = [
        path for path in artifact_paths if path.name == "llm_next_tickets_blocked.json"
    ]
    assert blocked_artifacts
    payload = json.loads(blocked_artifacts[-1].read_text(encoding="utf-8"))
    assert payload["blocked"] is True
    assert "DEEPSEEK_API_KEY" in payload["reason"]
    assert payload["fallback_next_tickets_path"].endswith("next_tickets.json")
    updates = store.list_backlog_updates_for_ticket(ticket.id)
    assert updates


def test_orchestrator_llm_backlog_success_drives_followup_ticket(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    response = {
        "id": "chatcmpl_test",
        "model": "deepseek-v4-pro",
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "rationale": "LLM memory agent found a concrete backlog gap.",
                            "next_tickets": [
                                {
                                    "title": "Index memory for future LLM planning",
                                    "reason": "Planner memory exists but should be indexed before LLM backlog decisions.",
                                    "source": "memory",
                                    "priority": "high",
                                    "suggested_build_decision": "code_task",
                                    "acceptance_criteria": [
                                        "Backlog planner can cite prior memory records.",
                                    ],
                                    "affected_modules": [
                                        "ariadne_ltb/memory.py",
                                        "ariadne_ltb/llm_backlog.py",
                                    ],
                                }
                            ],
                        }
                    )
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"total_tokens": 77},
    }
    transport = FakeTransport(response)
    client = DeepSeekClient(api_key="test-secret-key", transport=transport)

    result = TicketRunOrchestrator(store).run_ticket(
        "ARI-003",
        backend_name="fake-codex",
        backlog_planner="llm",
        backlog_planner_client=client,
    )

    assert result.backlog_planner_name == "llm"
    assert result.backlog_planner_artifact_path
    artifact_payload = json.loads(Path(result.backlog_planner_artifact_path).read_text(encoding="utf-8"))
    assert artifact_payload["blocked"] is False
    assert artifact_payload["next_tickets"][0]["title"] == "Index memory for future LLM planning"
    followups = [
        ticket
        for ticket in store.list_tickets()
        if ticket.metadata.get("generated_from_ticket_id") == result.ticket_id
    ]
    assert any(ticket.title == "Index memory for future LLM planning" for ticket in followups)
    manifest = json.loads(Path(result.orchestrator_result_path).read_text(encoding="utf-8"))
    assert manifest["backlog_planner_name"] == "llm"
    assert manifest["backlog_planner_artifact_id"]
    assert manifest["artifacts"]["backlog_planner_artifact_path"] == result.backlog_planner_artifact_path
    assert transport.payload["model"] == client.model
