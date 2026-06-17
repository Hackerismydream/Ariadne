from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board import export_board
from ariadne_ltb.cli import app
from ariadne_ltb.execution import (
    ClaudeCodeBackend,
    CodexBackend,
    ExecutionContext,
    FakeCodexBackend,
)
from ariadne_ltb.full_demo import run_full_demo
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.llm import DeepSeekClient
from ariadne_ltb.models import (
    AgentRun,
    ArtifactType,
    BacklogUpdateTrigger,
    BuildDecision,
    ReviewVerdict,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.planner import DeterministicPlanner, LLMPlanner
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


class FakeLLMTransport:
    def post_json(self, url, payload, headers, timeout_seconds):  # type: ignore[no-untyped-def]
        return {
            "model": "deepseek-v4-pro",
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"summary":"role completed","decision":"continue",'
                            '"evidence":["ticket evidence"],"risks":[],'
                            '"recommended_actions":["continue product loop"]}'
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        }


def test_orchestrator_runs_reusable_full_loop(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)

    result = TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    ticket = store.load_ticket(result.ticket_id)
    artifacts = [store.load_artifact(artifact_id) for artifact_id in ticket.artifact_ids]
    artifact_types = {artifact.artifact_type for artifact in artifacts}

    assert ticket.status is TicketStatus.DONE
    assert result.ticket_key == "ARI-003"
    assert result.review_verdict == ReviewVerdict.PASS.value
    assert result.test_exit_code == 0
    assert result.memory_path and Path(result.memory_path).exists()
    assert result.feishu_plan_path and Path(result.feishu_plan_path).exists()
    assert result.next_tickets_path and Path(result.next_tickets_path).exists()
    assert result.board_path and Path(result.board_path).exists()
    assert ArtifactType.CODEX_HANDOFF in artifact_types
    assert ArtifactType.NEXT_TICKETS in artifact_types
    assert ArtifactType.ORCHESTRATOR_RESULT in artifact_types
    assert ArtifactType.PERMISSION_PROFILE in artifact_types
    assert result.orchestrator_result_path
    manifest = json.loads(Path(result.orchestrator_result_path).read_text(encoding="utf-8"))
    assert manifest["ticket_key"] == "ARI-003"
    assert manifest["backend_name"] == "fake-codex"
    assert manifest["execution_result_id"] == result.execution_result_id
    assert manifest["review_verdict"] == "pass"
    assert manifest["board_path"] == result.board_path
    assert manifest["permission_profile_id"]
    assert manifest["artifacts"]["next_tickets_path"] == result.next_tickets_path
    assert manifest["artifacts"]["permission_profile_path"].endswith("execution_permission_profile.json")

    handoff_path = store.load_artifact(result.handoff_artifact_id).path
    handoff = Path(handoff_path).read_text(encoding="utf-8")
    assert "## Execution Permission Profile" in handoff
    assert "Git operations policy" in handoff


def test_orchestrator_runs_llm_role_agents_inside_ticket_loop(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    client = DeepSeekClient(api_key="test-secret-key", transport=FakeLLMTransport())

    result = TicketRunOrchestrator(store).run_ticket(
        "ARI-003",
        backend_name="fake-codex",
        agent_runtime="llm",
        llm_agent_client=client,
    )

    assert result.review_verdict == "pass"
    assert result.agent_runtime == "llm"
    assert len(result.llm_agent_artifact_paths) == 3
    assert all(Path(path).exists() for path in result.llm_agent_artifact_paths)
    ticket = store.load_ticket(result.ticket_id)
    llm_runs = [store.load_run(run_id) for run_id in ticket.agent_run_ids if store.load_run(run_id).agent_role.startswith("llm:")]
    assert {run.agent_role for run in llm_runs} >= {"llm:build_lead", "llm:knowledge", "llm:memory"}
    assert all(run.is_terminal for run in llm_runs)
    manifest = json.loads(Path(result.orchestrator_result_path).read_text(encoding="utf-8"))
    assert manifest["agent_runtime"] == "llm"
    assert manifest["artifacts"]["llm_agent_artifact_paths"] == result.llm_agent_artifact_paths


def test_demo_full_uses_ticket_run_orchestrator(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []
    original = TicketRunOrchestrator.run_ticket

    def spy(self, ticket_id_or_key: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(ticket_id_or_key)
        return original(self, ticket_id_or_key, *args, **kwargs)

    monkeypatch.setattr(TicketRunOrchestrator, "run_ticket", spy)
    result = run_full_demo(root=tmp_path, source_paths=SOURCE_FIXTURES)

    assert calls == [result.selected_ticket_key]
    assert result.next_tickets_path.exists()


def test_cli_ticket_run_completes_review_memory_next_tickets_and_board(tmp_path: Path) -> None:
    runner = CliRunner()
    ingest_result = runner.invoke(
        app,
        ["--root", str(tmp_path), "ingest", *[str(path) for path in SOURCE_FIXTURES]],
    )
    assert ingest_result.exit_code == 0, ingest_result.output

    run_result = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "run", "ARI-003", "--backend", "fake-codex"],
    )
    assert run_result.exit_code == 0, run_result.output
    assert "reviewer verdict: pass" in run_result.output
    assert "backlog previews:" in run_result.output
    assert (tmp_path / ".ariadne" / "board" / "index.md").exists()
    assert (tmp_path / ".ariadne" / "memory" / "decision_log.md").exists()

    next_tickets = list((tmp_path / ".ariadne" / "artifacts").glob("*/next_tickets.json"))
    assert next_tickets


def test_cli_ticket_run_defaults_to_real_codex_and_records_blocked_evidence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    runner = CliRunner()
    ingest_result = runner.invoke(
        app,
        ["--root", str(tmp_path), "ingest", *[str(path) for path in SOURCE_FIXTURES]],
    )
    assert ingest_result.exit_code == 0, ingest_result.output

    run_result = runner.invoke(app, ["--root", str(tmp_path), "ticket", "run", "ARI-003"])

    assert run_result.exit_code == 0, run_result.output
    assert "backend used: codex" in run_result.output
    assert (tmp_path / ".ariadne" / "board" / "index.md").exists()
    store = AriadneStore(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    execution = store.load_execution_result(ticket.metadata["execution_result_id"])
    previews = store.list_backlog_previews()
    execution_previews = [
        preview for preview in previews if preview.trigger_type is BacklogUpdateTrigger.EXECUTION_RESULT
    ]
    repair_tickets = [
        item
        for item in store.list_tickets()
        if item.metadata.get("execution_result_id") == execution.id
    ]
    assert execution.backend_name == "codex"
    assert execution.blocked is True
    assert "ARIADNE_ENABLE_EXTERNAL_EXECUTION" in (execution.block_reason or "")
    assert execution_previews
    assert execution_previews[0].applied_update_id
    assert repair_tickets
    assert any(
        update.trigger_ref == execution_previews[0].id
        for update in store.list_backlog_updates_for_ticket(ticket.id)
        if update.trigger_type is BacklogUpdateTrigger.EXECUTION_RESULT
    )


def test_orchestrator_supersedes_stale_non_terminal_execution_run(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, SOURCE_FIXTURES)[2]
    stale = AgentRun(
        id=stable_id("run", ticket.id, "execution", "stale"),
        ticket_id=ticket.id,
        agent_name="Execution",
        agent_role="execution",
        input_summary="Stale execution run from interrupted process.",
        backend_name="codex",
    ).mark_running()
    store.save_run(stale)
    store.save_ticket(ticket.with_run(stale.id))

    result = TicketRunOrchestrator(store).run_ticket(ticket.key, backend_name="fake-codex")
    review = store.load_review_report(result.review_report_id)
    stale_after = store.load_run(stale.id)

    assert result.review_verdict == "pass"
    assert "All Agent Runs have terminal status" in review.passed_checks
    assert stale_after.is_terminal


def test_fake_codex_blocks_when_task_does_not_mention_export_json(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    result = FakeCodexBackend().execute(
        ExecutionContext(
            ticket_id="ticket_demo",
            ticket_key="ARI-999",
            build_packet_id="packet_demo",
            target_repo_path=str(target),
            handoff_prompt="Add a pretty list command.",
            backend_name="fake-codex",
            allowed_paths=["demo_todo/cli.py", "tests/test_cli.py"],
            command="add list output",
            test_command="pytest",
        )
    )

    assert result.blocked is True
    assert "export-json" in (result.block_reason or "")
    assert result.changed_files == []


def test_fake_codex_blocks_when_required_paths_are_not_allowed(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    result = FakeCodexBackend().execute(
        ExecutionContext(
            ticket_id="ticket_demo",
            ticket_key="ARI-999",
            build_packet_id="packet_demo",
            target_repo_path=str(target),
            handoff_prompt="Add demo-todo export-json support.",
            backend_name="fake-codex",
            allowed_paths=["demo_todo/cli.py"],
            command="add export-json",
            test_command="pytest",
        )
    )

    assert result.blocked is True
    assert "allowed paths" in (result.block_reason or "")
    assert result.changed_files == []


def test_codex_backend_disabled_path_and_command_template(monkeypatch, tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    monkeypatch.setenv(
        "ARIADNE_CODEX_COMMAND_TEMPLATE",
        "codex exec --cd {target_repo} --prompt-file {handoff_file} --ticket {ticket_key}",
    )
    context = _external_context(target)
    backend = CodexBackend()

    command = backend.render_command(context)
    result = backend.execute(context)

    assert str(target) in command
    assert "ARI-123" in command
    assert result.blocked is True
    assert "ARIADNE_ENABLE_EXTERNAL_EXECUTION" in (result.block_reason or "")


def test_claude_backend_disabled_path(monkeypatch, tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    result = ClaudeCodeBackend().execute(_external_context(target, backend_name="claude-code"))

    assert result.blocked is True
    assert "ARIADNE_ENABLE_EXTERNAL_EXECUTION" in (result.block_reason or "")


def test_deterministic_planner_creates_valid_build_packet_from_arbitrary_markdown(
    tmp_path: Path,
) -> None:
    source = tmp_path / "note.md"
    source.write_text(
        "# Retrieval Note\n\nLocal memory should be searchable before planning future tasks.\n",
        encoding="utf-8",
    )
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source])[0]

    result = DeterministicPlanner().plan_ticket(store, ticket)
    packet = store.load_build_packet(result.build_packet_id)

    assert result.succeeded is True
    assert packet.ticket_id == ticket.id
    assert 1 <= len(packet.evidence) <= 5
    assert packet.build_decision is not BuildDecision.CODE_TASK
    assert Path(result.handoff_artifact_path).exists()


def test_llm_planner_missing_key_fails_gracefully(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]

    result = LLMPlanner().plan_ticket(store, ticket)

    assert result.succeeded is False
    assert result.error
    assert result.error_artifact_path and Path(result.error_artifact_path).exists()


def test_source_ingestion_extracts_multiple_evidence_snippets(tmp_path: Path) -> None:
    source = tmp_path / "paper_note.md"
    source.write_text(
        "# Workflow Evidence\n\n"
        "Agent runs need visible logs.\n\n"
        "Reviewers need changed file evidence.\n\n"
        "Memory should cite completed decisions.\n",
        encoding="utf-8",
    )
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source])[0]
    packet = store.load_build_packet(ticket.build_packet_id)

    assert len(packet.evidence) >= 2


def test_board_includes_loop_trace_after_export(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    board_path = export_board(store)
    board = board_path.read_text(encoding="utf-8")

    assert "Source -> Ticket -> Packet -> Handoff -> Backend -> Diff -> Tests -> Review -> Memory -> Feishu Plan -> Next Tickets" in board
    assert "next_tickets.json" in board
    assert "feishu_write_plan.json" in board


def test_board_links_provider_audit_artifacts(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    board_path = export_board(store)
    board = board_path.read_text(encoding="utf-8")

    assert "### Provider Audit Artifacts" in board
    assert "orchestrator_result.json" in board
    assert "execution_log.json" in board
    assert "git_diff.patch" in board
    assert "test_output.json" in board
    assert "execution_permission_profile.json" in board
    assert "### Execution Permission Profile" in board
    assert "block_commit_push_merge_pr" in board
    assert "- Backend: `fake-codex`" in board
    assert "- Review verdict: `pass`" in board
    assert "- External execution enabled: `false`" in board


def test_env_and_workspace_outputs_are_gitignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    for pattern in [".env", ".env.*", "*.secret", ".secrets", "secrets/", ".ariadne/"]:
        assert pattern in gitignore


def _external_context(target: Path, backend_name: str = "codex") -> ExecutionContext:
    return ExecutionContext(
        ticket_id="ticket_123",
        ticket_key="ARI-123",
        build_packet_id="packet_123",
        target_repo_path=str(target),
        handoff_prompt="Add demo-todo export-json support.",
        backend_name=backend_name,
        allowed_paths=["demo_todo/cli.py", "tests/test_cli.py"],
        command="",
        test_command="pytest",
        handoff_file=str(target.parent / "handoffs" / "ARI-123.md"),
    )
