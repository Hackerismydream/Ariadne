from __future__ import annotations

from pathlib import Path
import subprocess

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.execution import ClaudeCodeBackend, CodexBackend, ExecutionContext
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import AssignmentStatus, FailureReason
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_codex_template_supports_assignment_and_run_ids(monkeypatch, tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    monkeypatch.setenv(
        "ARIADNE_CODEX_COMMAND_TEMPLATE",
        "codex exec --cd {target_repo} --prompt-file {handoff_file} "
        "--ticket {ticket_key} --assignment {assignment_id} --run {run_id}",
    )
    context = ExecutionContext(
        ticket_id="ticket_123",
        ticket_key="ARI-123",
        build_packet_id="packet_123",
        target_repo_path=str(target),
        handoff_prompt="Add demo-todo export-json support.",
        backend_name="codex",
        allowed_paths=["demo_todo/cli.py", "tests/test_cli.py"],
        command="",
        test_command="pytest",
        assignment_id="assignment_123",
        run_id="run_123",
    )

    command = CodexBackend().render_command(context)

    assert "assignment_123" in command
    assert "run_123" in command


def test_assign_to_codex_blocks_without_gate_and_no_fake_fallback(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "ticket",
            "assign",
            "ARI-003",
            "--to",
            "codex",
            "--runtime-profile",
            "deterministic",
        ],
    )
    run = runner.invoke(app, ["--root", str(tmp_path), "daemon", "run-once"])

    ticket = store.resolve_ticket("ARI-003")
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    execution_id = store.load_ticket(ticket.id).metadata["execution_result_id"]
    execution = store.load_execution_result(execution_id)
    comments = store.list_comments(ticket.id)

    assert assign.exit_code == 0, assign.output
    assert run.exit_code == 0, run.output
    assert assignment.status is AssignmentStatus.BLOCKED
    assert execution.backend_name == "codex"
    assert execution.failure_reason is FailureReason.EXTERNAL_EXECUTION_BLOCKED
    assert "fake-codex" not in (execution.command or "")
    assert any("blocked" in comment.body.lower() for comment in comments)


def test_claude_backend_is_gated(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    target = ensure_demo_target_project(tmp_path)
    result = ClaudeCodeBackend().execute(
        ExecutionContext(
            ticket_id="ticket_123",
            ticket_key="ARI-123",
            build_packet_id="packet_123",
            target_repo_path=str(target),
            handoff_prompt="Add demo-todo export-json support.",
            backend_name="claude-code",
            allowed_paths=["demo_todo/cli.py", "tests/test_cli.py"],
            command="",
            test_command="pytest",
        )
    )

    assert result.blocked is True
    assert result.failure_reason is FailureReason.EXTERNAL_EXECUTION_BLOCKED


def test_backend_doctor_reports_codex_gate_without_secret(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-value-not-visible")
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    result = CliRunner().invoke(app, ["--root", str(tmp_path), "backend", "doctor"])

    assert result.exit_code == 0, result.output
    assert "external execution enabled? yes" in result.output.lower()
    assert "confirm required? yes" in result.output.lower()
    assert "secret-value-not-visible" not in result.output


def test_demo_codex_without_gate_records_blocked_result(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    runner = CliRunner()

    result = runner.invoke(app, ["--root", str(tmp_path), "demo", "codex"])

    store = AriadneStore(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    execution = store.load_execution_result(store.load_ticket(ticket.id).metadata["execution_result_id"])

    assert result.exit_code == 0, result.output
    assert "backend used: codex" in result.output
    assert "reviewer verdict: blocked" in result.output
    assert execution.backend_name == "codex"
    assert execution.blocked is True
    assert execution.failure_reason is FailureReason.EXTERNAL_EXECUTION_BLOCKED
    assert (tmp_path / ".ariadne" / "board" / "index.md").exists()


def test_backend_diagnose_codex_missing_does_not_print_template_value(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ARIADNE_CODEX_COMMAND_TEMPLATE", "codex exec --secret hidden")
    monkeypatch.setenv("ARIADNE_CODEX_CONFIG", str(tmp_path / "missing.toml"))
    monkeypatch.setattr("ariadne_ltb.cli.shutil.which", lambda command: None)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "backend", "diagnose", "codex"])

    assert result.exit_code == 0, result.output
    assert "CodexBackend command: missing" in result.output
    assert "Prompt-file support: unknown" in result.output
    assert "ARIADNE_CODEX_COMMAND_TEMPLATE: set" in result.output
    assert "codex exec --secret hidden" not in result.output


def test_backend_diagnose_codex_recommends_stdin_template_for_local_cli(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = tmp_path / "config.toml"
    config.write_text('service_tier = "priority"\n', encoding="utf-8")
    monkeypatch.setenv("ARIADNE_CODEX_CONFIG", str(config))
    monkeypatch.setattr("ariadne_ltb.cli.shutil.which", lambda command: "/usr/local/bin/codex")

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="Usage: codex exec [OPTIONS] [PROMPT]\n",
            stderr="",
        )

    monkeypatch.setattr("ariadne_ltb.cli.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "backend", "diagnose", "codex"])

    assert result.exit_code == 0, result.output
    assert "CodexBackend command: found /usr/local/bin/codex" in result.output
    assert "Prompt-file support: no" in result.output
    assert "codex exec --cd {target_repo} - < {handoff_file}" in result.output
    assert "service_tier=priority unsupported; expected fast or flex" in result.output
