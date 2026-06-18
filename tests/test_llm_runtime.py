from __future__ import annotations

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.llm import DeepSeekClient, LLMClientError, load_local_env
from ariadne_ltb.models import ReviewVerdict
from ariadne_ltb.planner import LLMPlanner
from ariadne_ltb.storage import AriadneStore


class FakeTransport:
    def __init__(self, response: dict[str, Any] | None = None, error: OSError | None = None) -> None:
        self.response = response or {
            "id": "chatcmpl_test",
            "model": "deepseek-v4-pro",
            "choices": [
                {
                    "index": 0,
                    "message": {"content": '{"ok": true, "summary": "valid json"}'},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 3,
                "prompt_cache_hit_tokens": 1,
                "prompt_cache_miss_tokens": 2,
                "completion_tokens": 4,
                "total_tokens": 7,
            },
        }
        self.error = error
        self.url = ""
        self.payload: dict[str, Any] = {}
        self.headers: dict[str, str] = {}
        self.timeout_seconds = 0

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        self.url = url
        self.payload = payload
        self.headers = headers
        self.timeout_seconds = timeout_seconds
        if self.error:
            raise self.error
        return self.response


def test_deepseek_client_uses_official_chat_json_payload(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    transport = FakeTransport()

    response = DeepSeekClient(
        api_key="test-secret-key",
        transport=transport,
        timeout_seconds=12,
    ).complete_json_response("Return json.", "ariadne_test")

    assert transport.url == "https://api.deepseek.com/chat/completions"
    assert transport.payload["model"] == "deepseek-v4-pro"
    assert transport.payload["response_format"] == {"type": "json_object"}
    assert transport.payload["stream"] is False
    assert transport.payload["messages"][0]["content"] == "You are an Ariadne production agent. Return only valid JSON."
    assert "Requested schema: ariadne_test" in transport.payload["messages"][1]["content"]
    assert transport.headers["Authorization"] == "Bearer test-secret-key"
    assert transport.timeout_seconds == 12
    assert response.content_json == {"ok": True, "summary": "valid json"}
    assert response.usage.total_tokens == 7
    assert response.usage.prompt_cache_hit_tokens == 1
    assert response.usage.prompt_cache_miss_tokens == 2


def test_deepseek_request_keeps_cacheable_system_prefix_stable(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = DeepSeekClient(api_key="test-secret-key", transport=FakeTransport())

    first = client.build_request("First prompt.", "ariadne_first")
    second = client.build_request("Second prompt.", "ariadne_second")

    assert first.messages[0].content == second.messages[0].content
    assert "ariadne_first" not in first.messages[0].content
    assert "ariadne_second" not in second.messages[0].content
    assert "Requested schema: ariadne_first" in first.messages[1].content
    assert "Requested schema: ariadne_second" in second.messages[1].content


def test_deepseek_client_redacts_transport_errors(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    transport = FakeTransport(error=OSError("bad token test-secret-key"))

    try:
        DeepSeekClient(api_key="test-secret-key", transport=transport).complete_json(
            "Return json.",
            "ariadne_test",
        )
    except LLMClientError as exc:
        assert "test-secret-key" not in exc.error.message
        assert "[REDACTED]" in exc.error.message or "[REDACTED]" in exc.error.message
    else:
        raise AssertionError("expected LLMClientError")


def test_load_local_env_reads_only_llm_allowlist(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("ARIADNE_LLM_MODEL", raising=False)
    (tmp_path / ".env").write_text(
        "DEEPSEEK_API_KEY=local-test-key\n"
        "ARIADNE_LLM_MODEL=deepseek-v4-flash\n"
        "UNRELATED_SECRET=do-not-load\n",
        encoding="utf-8",
    )

    loaded = load_local_env(tmp_path)

    assert loaded == ["DEEPSEEK_API_KEY", "ARIADNE_LLM_MODEL"]
    assert "UNRELATED_SECRET" not in loaded


def test_llm_doctor_reports_configuration_without_secret(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=local-test-key\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "llm", "doctor"])

    assert result.exit_code == 0, result.output
    assert "LLM provider: deepseek" in result.output
    assert "DeepSeek API key: set" in result.output
    assert "https://api.deepseek.com" in result.output
    assert "local-test-key" not in result.output


def test_llm_smoke_requires_external_confirmation(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["--root", str(tmp_path), "llm", "smoke", "--provider", "deepseek"])

    assert result.exit_code == 2
    assert "--confirm-external" in result.output


def test_llm_planner_reads_local_env_with_fake_transport(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    source_path = tmp_path / "feature.md"
    source_path.write_text("# Feature\n\nImplement export-json for the CLI.\n", encoding="utf-8")
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=local-test-key\n", encoding="utf-8")
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source_path])[0]
    response = {
        "id": "chatcmpl_test",
        "model": "deepseek-v4-pro",
        "choices": [
            {
                "message": {
                    "content": (
                        '{"source_summary":"summary","insight":"insight",'
                        '"evidence":[{"quote_or_summary":"Implement export-json",'
                        '"location":"feature.md","confidence":0.8}],'
                        '"project_relevance":"relevant","build_decision":"code_task",'
                        '"tasks":["add export-json"],'
                        '"acceptance_criteria":["export-json works"],'
                        '"affected_modules":["demo_todo/cli.py","tests/test_cli.py"],'
                        '"risks":[],"assumptions":[]}'
                    )
                },
                "finish_reason": "stop",
            }
        ],
    }
    client = DeepSeekClient(api_key="local-test-key", transport=FakeTransport(response=response))

    result = LLMPlanner(client=client).plan_ticket(store, ticket)

    assert result.succeeded is True
    packet = store.load_build_packet(result.build_packet_id)
    assert packet.metadata["planner_mode"] == "llm"


def test_review_run_llm_missing_key_blocks_gracefully(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    source_path = tmp_path / "feature.md"
    source_path.write_text("# Feature\n\nImplement export-json for the CLI.\n", encoding="utf-8")
    runner = CliRunner()
    ingest = runner.invoke(app, ["--root", str(tmp_path), "ingest", str(source_path)])
    plan = runner.invoke(app, ["--root", str(tmp_path), "ticket", "plan", "ARI-001"])

    result = runner.invoke(app, ["--root", str(tmp_path), "review", "run", "ARI-001", "--reviewer", "llm"])

    assert ingest.exit_code == 0, ingest.output
    assert plan.exit_code == 0, plan.output
    assert result.exit_code == 0, result.output
    assert "reviewer: llm" in result.output
    assert "reviewer verdict: blocked" in result.output
    reports = AriadneStore(tmp_path).list_review_reports()
    assert reports[-1].verdict is ReviewVerdict.BLOCKED
