from __future__ import annotations

from pathlib import Path
import subprocess

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.execution import ClaudeCodeBackend, CodexBackend, ExecutionContext, ShellBackend
from ariadne_ltb.models import FailureReason
from ariadne_ltb.target_project import ensure_demo_target_project


def test_backend_doctor_reports_gates_without_secrets(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-print")
    monkeypatch.setenv("ARIADNE_CODEX_COMMAND_TEMPLATE", "codex exec {ticket_key}")
    runner = CliRunner()

    result = runner.invoke(app, ["--root", str(tmp_path), "backend", "doctor"])

    assert result.exit_code == 0, result.output
    assert "FakeCodexBackend: available" in result.output
    assert "ShellBackend: available" in result.output
    assert "CodexBackend command:" in result.output
    assert "ClaudeCodeBackend command:" in result.output
    assert "ARIADNE_ENABLE_EXTERNAL_EXECUTION: unset" in result.output
    assert "ARIADNE_CODEX_COMMAND_TEMPLATE: set" in result.output
    assert "DEEPSEEK_API_KEY: set" in result.output
    assert "secret scan:" in result.output
    assert "do-not-print" not in result.output


def test_codex_smoke_test_blocks_without_external_execution_flag(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "backend", "smoke-test", "codex", "--confirm-execution"],
    )

    assert result.exit_code == 2
    assert "ARIADNE_ENABLE_EXTERNAL_EXECUTION" in result.output
    assert not (tmp_path / ".ariadne" / "demo_target_project").exists()


def test_codex_smoke_test_blocks_without_confirmation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    runner = CliRunner()

    result = runner.invoke(app, ["--root", str(tmp_path), "backend", "smoke-test", "codex"])

    assert result.exit_code == 2
    assert "--confirm-execution" in result.output
    assert not (tmp_path / ".ariadne" / "demo_target_project").exists()


def test_codex_smoke_test_blocks_when_codex_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setattr(CodexBackend, "is_available", lambda self: False)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "backend", "smoke-test", "codex", "--confirm-execution"],
    )

    assert result.exit_code == 2
    assert "codex command is not available" in result.output


def test_claude_code_smoke_test_blocks_when_claude_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setattr(ClaudeCodeBackend, "is_available", lambda self: False)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "backend", "smoke-test", "claude-code", "--confirm-execution"],
    )

    assert result.exit_code == 2
    assert "claude command is not available" in result.output


def test_backend_smoke_test_runs_codex_through_assignment_daemon_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    patcher = tmp_path / "patch_demo.py"
    patcher.write_text(
        '''
from pathlib import Path

cli = Path("demo_todo/cli.py")
text = cli.read_text(encoding="utf-8")
if "export-json" not in text:
    text = text.replace(
        '    subcommands.add_parser("list")\\n',
        '    subcommands.add_parser("list")\\n'
        '    subcommands.add_parser("export-json")\\n',
    )
    text = text.replace(
        '    if args.command == "list":\\n'
        '        for task in load_tasks():\\n'
        '            print(task)\\n'
        '        return 0\\n',
        '    if args.command == "list":\\n'
        '        for task in load_tasks():\\n'
        '            print(task)\\n'
        '        return 0\\n'
        '    if args.command == "export-json":\\n'
        '        import json\\n'
        '        print(json.dumps(load_tasks()))\\n'
        '        return 0\\n',
    )
cli.write_text(text, encoding="utf-8")

test = Path("tests/test_cli.py")
test_text = test.read_text(encoding="utf-8")
if "test_export_json_command" not in test_text:
    test.write_text(
        test_text
        + '\\n\\ndef test_export_json_command(tmp_path, monkeypatch) -> None:\\n'
        + '    monkeypatch.chdir(tmp_path)\\n'
        + '    add = run_cli("add", "ship")\\n'
        + '    exported = run_cli("export-json")\\n'
        + '    assert add.returncode == 0\\n'
        + '    assert exported.returncode == 0\\n'
        + '    assert "ship" in exported.stdout\\n',
        encoding="utf-8",
    )
''',
        encoding="utf-8",
    )
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setenv("ARIADNE_CODEX_COMMAND_TEMPLATE", f"python3.11 {patcher}")
    monkeypatch.setattr(CodexBackend, "is_available", lambda self: True)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "backend",
            "smoke-test",
            "codex",
            "--confirm-execution",
            "--timeout-seconds",
            "30",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "backend: codex" in result.output
    assert "assignment status: done" in result.output
    assert "review verdict: pass" in result.output
    assert "agent runtime: deterministic" in result.output
    assert "changed files: demo_todo/cli.py, tests/test_cli.py" in result.output


def test_existing_fake_codex_ticket_run_still_passes(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    sources = sorted((root / "examples" / "sources").glob("*.md"))
    runner = CliRunner()

    ingest = runner.invoke(app, ["--root", str(tmp_path), "ingest", *[str(path) for path in sources]])
    run = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "run", "ARI-003", "--backend", "fake-codex"],
    )

    assert ingest.exit_code == 0, ingest.output
    assert run.exit_code == 0, run.output
    assert "reviewer verdict: pass" in run.output


def test_codex_backend_timeout_returns_execution_result(
    monkeypatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setenv("ARIADNE_CODEX_COMMAND_TEMPLATE", "python3.11 -c 'print(1)'")

    original_run = subprocess.run

    def timeout_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("shell") is True:
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout"))
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", timeout_run)

    result = CodexBackend().execute(
        ExecutionContext(
            ticket_id="ticket_timeout",
            ticket_key="ARI-TIMEOUT",
            build_packet_id="packet_timeout",
            target_repo_path=str(target),
            handoff_prompt="Add demo-todo export-json support.",
            backend_name="codex",
            allowed_paths=["demo_todo/cli.py", "tests/test_cli.py"],
            command="",
            test_command="",
            confirm_execution=True,
            timeout_seconds=1,
        )
    )

    assert result.exit_code == 124
    assert result.blocked is False
    assert "timed out after 1 seconds" in result.stderr


def test_shell_backend_requires_confirmation_as_blocked_result(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()

    result = ShellBackend().execute(
        ExecutionContext(
            ticket_id="ticket_shell",
            ticket_key="ARI-SHELL",
            build_packet_id="packet_shell",
            target_repo_path=str(target),
            handoff_prompt="Run shell command.",
            backend_name="shell",
            allowed_paths=[],
            command="echo unsafe",
            test_command="",
            confirm_execution=False,
        )
    )

    assert result.blocked is True
    assert result.failure_reason is FailureReason.EXTERNAL_EXECUTION_BLOCKED
    assert "--confirm-execution" in (result.block_reason or "")


def test_shell_backend_blocks_dangerous_git_operation_when_confirmed(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)

    result = ShellBackend().execute(
        ExecutionContext(
            ticket_id="ticket_shell",
            ticket_key="ARI-SHELL",
            build_packet_id="packet_shell",
            target_repo_path=str(target),
            handoff_prompt="Do not run dangerous git operations.",
            backend_name="shell",
            allowed_paths=["."],
            command="git push origin main",
            test_command="",
            confirm_execution=True,
        )
    )

    assert result.blocked is True
    assert result.failure_reason is FailureReason.SCOPE_VIOLATION
    assert "dangerous git operation" in (result.block_reason or "")


def test_shell_backend_blocks_changed_files_outside_allowed_paths(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)

    result = ShellBackend().execute(
        ExecutionContext(
            ticket_id="ticket_shell",
            ticket_key="ARI-SHELL",
            build_packet_id="packet_shell",
            target_repo_path=str(target),
            handoff_prompt="Write outside the allowed module.",
            backend_name="shell",
            allowed_paths=["demo_todo/cli.py"],
            command="python3.11 -c 'from pathlib import Path; Path(\"outside.txt\").write_text(\"x\")'",
            test_command="",
            confirm_execution=True,
        )
    )

    assert result.blocked is True
    assert result.failure_reason is FailureReason.SCOPE_VIOLATION
    assert "outside allowed paths" in (result.block_reason or "")
    assert "outside.txt" in result.changed_files
