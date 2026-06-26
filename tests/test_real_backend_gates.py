from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.execution import ClaudeCodeBackend, CodexBackend, ExecutionContext
from ariadne_ltb.models import (
    BuildPacket,
    BuildDecision,
    BuildTicket,
    Evidence,
    FailureReason,
    ReviewReport,
    ReviewVerdict,
)
from ariadne_ltb.memory import generate_feishu_plan, write_memory_record
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


def _context(target: Path, backend_name: str = "codex") -> ExecutionContext:
    return ExecutionContext(
        ticket_id="ticket_real",
        ticket_key="ARI-REAL",
        build_packet_id="packet_real",
        target_repo_path=str(target),
        handoff_prompt="Add demo-todo export-json support.",
        backend_name=backend_name,
        allowed_paths=["demo_todo/cli.py", "tests/test_cli.py"],
        command="",
        test_command="python3.11 -m pytest",
        confirm_execution=True,
        timeout_seconds=10,
    )


def test_codex_backend_records_handoff_template_session_and_quota_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    target = ensure_demo_target_project(tmp_path)
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setenv(
        "ARIADNE_CODEX_COMMAND_TEMPLATE",
        (
            "python3.11 -c 'import sys; "
            'print(\"session id: codex-session-123\"); '
            'sys.stderr.write(\"rate limit exceeded token=redacted-secret-value\"); '
            "sys.exit(7)'"
        ),
    )

    result = CodexBackend().execute(_context(target))

    assert result.exit_code == 7
    assert result.failure_reason is FailureReason.QUOTA_EXCEEDED
    assert result.provider_failure_kind == "quota_exceeded"
    assert result.provider_session_id == "codex-session-123"
    assert result.handoff_file and Path(result.handoff_file).exists()
    assert result.command_template_env_var == "ARIADNE_CODEX_COMMAND_TEMPLATE"
    assert "redacted-secret-value" not in (result.provider_failure_evidence or "")
    assert "redacted-secret-value" not in result.command_template


def test_codex_backend_default_template_uses_stdin_without_forcing_service_tier(
    tmp_path: Path,
) -> None:
    target = ensure_demo_target_project(tmp_path)
    context = _context(target)
    command = CodexBackend().render_command(context)

    assert " --cd " in command
    assert " - < " in command
    assert "--prompt-file" not in command
    assert "service_tier" not in command


def test_codex_backend_reuses_existing_handoff_file_without_overwrite(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    handoff_file = tmp_path / ".ariadne" / "handoffs" / "packets" / "ARI-REAL-packet.md"
    handoff_file.parent.mkdir(parents=True)
    handoff_file.write_text("frozen packet markdown\n", encoding="utf-8")
    context = _context(target).model_copy(
        update={"handoff_file": str(handoff_file), "handoff_prompt": "replacement prompt"}
    )

    written = CodexBackend().write_handoff_file(context)

    assert written == handoff_file
    assert handoff_file.read_text(encoding="utf-8") == "frozen packet markdown\n"


def test_codex_backend_blocks_when_persisted_handoff_file_is_missing(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    missing_handoff = tmp_path / ".ariadne" / "handoffs" / "packets" / "missing.md"
    context = _context(target).model_copy(update={"handoff_file": str(missing_handoff)})

    result = CodexBackend().execute(context)

    assert result.blocked
    assert result.failure_reason is FailureReason.INVALID_RESOURCE
    assert "Persisted handoff file is missing" in (result.block_reason or "")


def test_codex_gate_block_does_not_attribute_dirty_repo_files(monkeypatch, tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    (target / "demo_todo" / "cli.py").write_text("# pre-existing dirty file\n", encoding="utf-8")
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)

    result = CodexBackend().execute(_context(target))

    assert result.blocked
    assert result.failure_reason is FailureReason.EXTERNAL_EXECUTION_BLOCKED
    assert result.changed_files == []
    assert result.git_diff == ""
    assert result.git_status_before == result.git_status_after


def test_blocked_memory_and_feishu_plan_do_not_claim_changed_files(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = BuildTicket(
        id="ticket_blocked",
        key="ARI-BLOCKED",
        title="Blocked execution",
        description="Blocked execution",
        source_type="test",
        source_ref="source.md",
    )
    packet = BuildPacket(
        id="packet_blocked",
        ticket_id=ticket.id,
        source_summary="source",
        insight="insight",
        evidence=[
            Evidence(
                id="evidence_blocked",
                source_ref="source.md",
                quote_or_summary="External execution gate should block without file attribution.",
                location="source.md",
            )
        ],
        project_relevance="relevant",
        build_decision=BuildDecision.CODE_TASK,
        tasks=["Resolve blocker"],
        acceptance_criteria=["Execution blocker is recorded.", "No fake changed files are attributed."],
        affected_modules=["ariadne_ltb/execution.py"],
    )
    execution = CodexBackend().execute(_context(ensure_demo_target_project(tmp_path / "target")))
    review = ReviewReport(
        id="review_blocked",
        ticket_id=ticket.id,
        verdict=ReviewVerdict.BLOCKED,
        failed_checks=["Execution backend was not blocked"],
        required_fixes=["Authorize external execution."],
    )

    memory, memory_path = write_memory_record(store, ticket, packet, execution, review)
    plan, _ = generate_feishu_plan(store, ticket, packet, execution, review)

    assert "blocked before coding" in memory.build_summary
    assert "changed demo_todo" not in memory.build_summary
    assert "No target files were attributed to this run" in memory_path.read_text(encoding="utf-8")
    body = plan.proposed_docs[0]["body_markdown"]
    assert "No files changed; execution blocked before coding." in body


def test_claude_backend_template_supports_model_effort_and_json(monkeypatch, tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    monkeypatch.setenv(
        "ARIADNE_CLAUDE_COMMAND_TEMPLATE",
        "claude --print --output-format json --model {model} --effort {effort} < {handoff_file}",
    )
    monkeypatch.setenv("ARIADNE_CLAUDE_MODEL", "sonnet")
    monkeypatch.setenv("ARIADNE_CLAUDE_EFFORT", "high")

    command = ClaudeCodeBackend().render_command(_context(target, backend_name="claude-code"))

    assert "claude --print --output-format json" in command
    assert "--model sonnet" in command
    assert "--effort high" in command


def test_backend_diagnose_claude_code_reports_capabilities_without_template_value(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ARIADNE_CLAUDE_COMMAND_TEMPLATE", "claude --secret hidden")
    monkeypatch.setattr("ariadne_ltb.cli.shutil.which", lambda command: "/usr/local/bin/claude")

    def fake_help(*args, **kwargs):  # type: ignore[no-untyped-def]
        from subprocess import CompletedProcess

        return CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="--print\n--output-format\n--model\n--effort\n--session-id\n",
            stderr="",
        )

    monkeypatch.setattr("ariadne_ltb.cli.subprocess.run", fake_help)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "backend", "diagnose", "claude-code"])

    assert result.exit_code == 0, result.output
    assert "Backend: claude-code" in result.output
    assert "ClaudeCodeBackend command: found /usr/local/bin/claude" in result.output
    assert "JSON output support: yes" in result.output
    assert "Model selection support: yes" in result.output
    assert "Reasoning effort support: yes" in result.output
    assert "Session id support: yes" in result.output
    assert "ARIADNE_CLAUDE_COMMAND_TEMPLATE: set" in result.output
    assert "claude --secret hidden" not in result.output


def test_backend_diagnose_rejects_unknown_backend(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["--root", str(tmp_path), "backend", "diagnose", "unknown"])

    assert result.exit_code == 2
    assert "backend must be `codex` or `claude-code`" in result.output


def test_codex_backend_classifies_unsupported_service_tier_as_provider_config(
    monkeypatch,
    tmp_path: Path,
) -> None:
    target = ensure_demo_target_project(tmp_path)
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setenv(
        "ARIADNE_CODEX_COMMAND_TEMPLATE",
        "python3.11 -c 'import sys; sys.stderr.write(\"Unsupported service_tier: flex\"); sys.exit(1)'",
    )

    result = CodexBackend().execute(_context(target))

    assert result.failure_reason is FailureReason.PROVIDER_CONFIG_INVALID
    assert result.provider_failure_kind == "provider_config_invalid"
