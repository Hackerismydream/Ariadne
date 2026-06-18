from __future__ import annotations

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.llm import DeepSeekClient
from ariadne_ltb.llm_agents import JSONLLMAgent, LLMAgentRole, run_ticket_llm_agent
from ariadne_ltb.models import AgentRunStatus, ArtifactType, MemoryRecord
from ariadne_ltb.storage import AriadneStore


class FakeTransport:
    def __init__(self, response: dict[str, Any] | None = None, error: OSError | None = None) -> None:
        self.response = response or {
            "model": "deepseek-v4-pro",
            "choices": [{"message": {"content": '{"decision": "route"}'}}],
            "usage": {"total_tokens": 9},
        }
        self.error = error

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        if self.error:
            raise self.error
        return self.response


def test_json_llm_agent_returns_structured_result(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = DeepSeekClient(api_key="test-secret-key", transport=FakeTransport())

    result = JSONLLMAgent(LLMAgentRole.PLANNER, client=client, root=tmp_path).run(
        "Return json.",
        "ariadne_route_decision",
    )

    assert result.succeeded is True
    assert result.role is LLMAgentRole.PLANNER
    assert result.output_json == {"decision": "route"}
    assert result.model == "deepseek-v4-pro"
    assert result.usage.total_tokens == 9


def test_json_llm_agent_redacts_errors(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = DeepSeekClient(
        api_key="test-secret-key",
        transport=FakeTransport(error=OSError("bad test-secret-key")),
    )

    result = JSONLLMAgent(LLMAgentRole.REVIEWER, client=client, root=tmp_path).run(
        "Return json.",
        "ariadne_review_report",
    )

    assert result.succeeded is False
    assert result.error
    assert "test-secret-key" not in result.error


def test_ticket_llm_agent_persists_run_artifact_and_ticket_event(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    source_path = tmp_path / "source.md"
    source_path.write_text("# Source\n\nUse visible progress for agent work.\n", encoding="utf-8")
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source_path])[0]
    store.save_memory_record(
        MemoryRecord(
            id="memory_existing",
            ticket_id="ticket_previous",
            title="Previous memory title",
            decision_log_entry="Prior decision.",
            build_summary="Prior build summary.",
            review_summary="Prior review summary.",
        )
    )
    client = DeepSeekClient(
        api_key="test-secret-key",
        transport=FakeTransport(
            {
                "model": "deepseek-v4-pro",
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"summary":"route ticket","decision":"assign to codex",'
                                '"evidence":["ticket is code task"],"risks":["needs gate"],'
                                '"recommended_actions":["confirm execution gate"]}'
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            }
        ),
    )

    result = run_ticket_llm_agent(store, ticket, LLMAgentRole.BUILD_LEAD, client=client)

    assert result.succeeded is True
    assert result.run_id
    assert result.artifact_path
    run = store.load_run(result.run_id)
    assert run.status is AgentRunStatus.SUCCEEDED
    assert run.agent_role == "llm:build_lead"
    assert run.backend_name == "deepseek"
    assert run.metadata["usage"]["total_tokens"] == 18
    artifact = store.load_artifact(result.artifact_id or "")
    assert artifact.artifact_type is ArtifactType.LLM_AGENT_RESULT
    assert artifact.metadata["llm_role"] == "build_lead"
    updated_ticket = store.load_ticket(ticket.id)
    assert result.run_id in updated_ticket.agent_run_ids
    assert artifact.id in updated_ticket.artifact_ids
    assert updated_ticket.event_log[-1].event_type == "llm_agent_finished"


def test_ticket_llm_agent_blocks_on_invalid_schema(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    source_path = tmp_path / "source.md"
    source_path.write_text("# Source\n\nUse visible progress for agent work.\n", encoding="utf-8")
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source_path])[0]
    client = DeepSeekClient(api_key="test-secret-key", transport=FakeTransport())

    result = run_ticket_llm_agent(store, ticket, LLMAgentRole.MEMORY, client=client)

    assert result.succeeded is False
    assert result.error
    assert "schema validation" in result.error
    run = store.load_run(result.run_id or "")
    assert run.status is AgentRunStatus.BLOCKED
    artifact = store.load_artifact(result.artifact_id or "")
    assert artifact.metadata["succeeded"] is False
    assert "test-secret-key" not in Path(artifact.path).read_text(encoding="utf-8")


def test_ticket_llm_agent_blocks_prompt_failures_without_stranding_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    source_path = tmp_path / "source.md"
    source_path.write_text("# Source\n\nUse visible progress for agent work.\n", encoding="utf-8")
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source_path])[0]
    monkeypatch.setattr(
        "ariadne_ltb.llm_agents._role_prompt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad prompt secret test-secret-key")),
    )

    result = run_ticket_llm_agent(
        store,
        ticket,
        LLMAgentRole.KNOWLEDGE,
        client=DeepSeekClient(api_key="test-secret-key", transport=FakeTransport()),
    )

    assert result.succeeded is False
    assert result.error
    assert "test-secret-key" not in result.error
    run = store.load_run(result.run_id or "")
    assert run.status is AgentRunStatus.BLOCKED
    updated_ticket = store.load_ticket(ticket.id)
    assert run.id in updated_ticket.agent_run_ids
    assert result.artifact_id in updated_ticket.artifact_ids


def test_cli_llm_run_agent_requires_external_confirmation(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "llm",
            "run-agent",
            "build_lead",
            "--ticket",
            "ARI-001",
        ],
    )

    assert result.exit_code == 2
    assert "--confirm-external is required" in result.output
