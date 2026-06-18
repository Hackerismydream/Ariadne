from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.feishu import create_lark_doc_from_plan
from ariadne_ltb.github_integration import sync_ticket_with_github
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import ExecutionResult, FailureReason, FeishuWritePlan, InboxStatus
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.llm import DeepSeekClient
from ariadne_ltb.llm_agents import LLMAgentRole, run_ticket_llm_agent


class _InvalidLLMTransport:
    def post_json(
        self,
        url: str,
        payload: dict,
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> dict:
        return {
            "model": "deepseek-v4-pro",
            "choices": [{"message": {"content": '{"decision":"missing required fields"}'}}],
            "usage": {"total_tokens": 3},
        }


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_inbox_refresh_materializes_real_failure_sources(tmp_path: Path, monkeypatch) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(
        assignment.mark_blocked("quota exceeded while coding", FailureReason.QUOTA_EXCEEDED)
    )
    store.save_execution_result(
        ExecutionResult(
            id="execution_blocked",
            ticket_id=ticket.id,
            backend_name="codex",
            dry_run=False,
            blocked=True,
            block_reason="not logged in",
            failure_reason=FailureReason.AUTHENTICATION_FAILED,
            command="codex exec",
            exit_code=1,
            provider_failure_kind="authentication_failed",
            provider_failure_evidence="not logged in",
        )
    )
    plan = FeishuWritePlan(
        id="feishu_plan",
        ticket_id=ticket.id,
        decision_log_entry="write result",
        run_summary="summary",
    )
    monkeypatch.setenv("FEISHU_ENABLE_WRITE", "1")
    monkeypatch.setattr("ariadne_ltb.feishu.shutil.which", lambda command: None)
    feishu = create_lark_doc_from_plan(plan, store.feishu_integrations_dir / ticket.key, True, ticket_key=ticket.key)
    store.save_feishu_write_result(feishu)
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", lambda command: None)
    github = sync_ticket_with_github(store, ticket, confirm_write=True)
    store.save_github_integration_result(github)

    items = refresh_inbox(store)

    source_types = {item.source_type for item in items}
    assert {"assignment", "execution", "feishu", "github"}.issubset(source_types)
    assert any(item.failure_reason is FailureReason.AUTHENTICATION_FAILED for item in items)
    assert any("lark-cli is not installed" in item.summary for item in items)
    assert any("gh command is not installed" in item.summary for item in items)
    assert (tmp_path / ".ariadne" / "inbox" / "items.json").exists()


def test_inbox_cli_lists_json_without_network(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(
        assignment.mark_failed("provider config invalid", FailureReason.PROVIDER_CONFIG_INVALID)
    )

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "inbox", "list", "--refresh", "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload
    assert payload[0]["ticket_key"] == ticket.key
    assert payload[0]["failure_reason"] == "provider_config_invalid"
    assert "provider config invalid" in payload[0]["summary"]


def test_inbox_refresh_materializes_blocked_llm_agent_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]

    result = run_ticket_llm_agent(
        store,
        ticket,
        LLMAgentRole.KNOWLEDGE,
        client=DeepSeekClient(api_key="test-secret-key", transport=_InvalidLLMTransport()),
    )
    assert result.succeeded is False

    items = refresh_inbox(store)

    llm_items = [item for item in items if item.source_type == "agent_run"]
    assert llm_items
    assert llm_items[0].ticket_key == ticket.key
    assert llm_items[0].failure_reason is FailureReason.AGENT_ERROR
    assert "llm:knowledge" in llm_items[0].summary
    assert result.artifact_path
    assert llm_items[0].evidence_ref == result.artifact_path


def test_inbox_show_and_resolve_preserves_status_across_refresh(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_failed("provider config invalid", FailureReason.PROVIDER_CONFIG_INVALID))
    items = refresh_inbox(store)
    item_id = items[0].id

    show = CliRunner().invoke(app, ["--root", str(tmp_path), "inbox", "show", item_id])
    assert show.exit_code == 0, show.output
    assert "recommended action:" in show.output
    assert "evidence:" in show.output

    resolve = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "inbox",
            "resolve",
            item_id,
            "--note",
            "fixed local provider config",
        ],
    )
    assert resolve.exit_code == 0, resolve.output
    assert "resolved:" in resolve.output

    listed = CliRunner().invoke(app, ["--root", str(tmp_path), "inbox", "list"])
    assert listed.exit_code == 0, listed.output
    assert "No inbox items." in listed.output

    listed_with_resolved = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "inbox", "list", "--include-resolved", "--output", "json"],
    )
    assert listed_with_resolved.exit_code == 0, listed_with_resolved.output
    payload = json.loads(listed_with_resolved.output)
    assert payload[0]["status"] == "resolved"
    assert payload[0]["resolution_note"] == "fixed local provider config"

    refreshed = refresh_inbox(store)
    refreshed_item = next(item for item in refreshed if item.id == item_id)
    assert refreshed_item.status is InboxStatus.RESOLVED
    assert refreshed_item.resolution_note == "fixed local provider config"


def test_inbox_create_ticket_applies_repair_backlog_update_idempotently(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_failed("provider config invalid", FailureReason.PROVIDER_CONFIG_INVALID))
    item = refresh_inbox(store)[0]

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "inbox", "create-ticket", item.id, "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ticket_key"]
    assert payload["update_id"]
    assert payload["inbox_status"] == "acknowledged"

    repair_ticket = store.load_ticket(payload["ticket_id"])
    assert repair_ticket.metadata["generated_from_inbox_item_id"] == item.id
    assert repair_ticket.status.value == "planning"
    assert repair_ticket.build_packet_id
    assert len(store.list_backlog_updates()) == 2  # source ingest plus inbox recovery

    second = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "inbox", "create-ticket", item.id, "--output", "json"],
    )
    assert second.exit_code == 0, second.output
    second_payload = json.loads(second.output)
    assert second_payload["already_exists"] is True
    assert second_payload["ticket_id"] == repair_ticket.id
    assert len(store.list_tickets()) == 2


def test_inbox_recover_creates_repair_tickets_for_open_items_idempotently(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    tickets = ingest_sources(store, SOURCE_FIXTURES[:2])
    for ticket in tickets:
        assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
        store.save_assignment(assignment.mark_failed("provider config invalid", FailureReason.PROVIDER_CONFIG_INVALID))

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "inbox", "recover", "--output", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["recovered_count"] == 2
    assert payload["created_ticket_count"] == 2
    assert payload["existing_ticket_count"] == 0
    assert payload["preview_count"] == 0
    assert payload["skipped_count"] == 0
    assert all(item["inbox_status"] == "acknowledged" for item in payload["recovered"])

    repair_tickets = [
        ticket for ticket in store.list_tickets() if ticket.metadata.get("generated_from_inbox_item_id")
    ]
    assert len(repair_tickets) == 2
    assert all(store.load_inbox_item(ticket.metadata["generated_from_inbox_item_id"]).status is InboxStatus.ACKNOWLEDGED for ticket in repair_tickets)

    second = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "inbox",
            "recover",
            "--include-acknowledged",
            "--no-refresh",
            "--output",
            "json",
        ],
    )

    assert second.exit_code == 0, second.output
    second_payload = json.loads(second.output)
    assert second_payload["recovered_count"] == 2
    assert second_payload["created_ticket_count"] == 0
    assert second_payload["existing_ticket_count"] == 2
    assert all(item["already_exists"] is True for item in second_payload["recovered"])
    assert len(store.list_tickets()) == 4


def test_inbox_recover_preview_only_respects_limit(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    tickets = ingest_sources(store, SOURCE_FIXTURES[:2])
    for ticket in tickets:
        assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
        store.save_assignment(assignment.mark_blocked("quota exceeded", FailureReason.QUOTA_EXCEEDED))

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "inbox", "recover", "--preview-only", "--limit", "1", "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["recovered_count"] == 1
    assert payload["preview_count"] == 1
    assert payload["created_ticket_count"] == 0
    assert payload["skipped_count"] == 1
    assert payload["recovered"][0]["preview_only"] is True
    assert payload["recovered"][0]["ticket_id"] is None
    assert len(store.list_tickets()) == 2
    assert len(store.list_backlog_previews()) == 1
    assert store.list_backlog_previews()[0].trigger_type.value == "inbox_recovery"


def test_inbox_create_ticket_preview_only_does_not_mutate_tickets(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[2]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_blocked("quota exceeded", FailureReason.QUOTA_EXCEEDED))
    item = refresh_inbox(store)[0]

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "inbox", "create-ticket", item.id, "--preview-only", "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["preview_only"] is True
    assert payload["preview_id"]
    assert payload["ticket_id"] is None
    assert len(store.list_tickets()) == 1
    assert store.load_inbox_item(item.id).status is InboxStatus.OPEN
