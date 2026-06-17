from __future__ import annotations

from pathlib import Path
from typing import Any

from ariadne_ltb.llm import DeepSeekClient
from ariadne_ltb.llm_agents import JSONLLMAgent, LLMAgentRole


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
    client = DeepSeekClient(api_key="sk-test-secret", transport=FakeTransport())

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
        api_key="sk-test-secret",
        transport=FakeTransport(error=OSError("bad sk-test-secret")),
    )

    result = JSONLLMAgent(LLMAgentRole.REVIEWER, client=client, root=tmp_path).run(
        "Return json.",
        "ariadne_review_report",
    )

    assert result.succeeded is False
    assert result.error
    assert "sk-test-secret" not in result.error
