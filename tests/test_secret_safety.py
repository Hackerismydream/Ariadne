from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.execution import ExecutionContext, ShellBackend
from ariadne_ltb.models import FailureReason
from ariadne_ltb.secret_safety import scan_for_secrets
from ariadne_ltb.target_project import ensure_demo_target_project


def _fake_openai_key() -> str:
    return "sk-" + "fake" * 6


def _fake_github_token() -> str:
    return "ghp_" + "1234567890" * 4


def test_secret_scanner_reports_paths_without_values(tmp_path: Path) -> None:
    secret_value = _fake_openai_key()
    (tmp_path / "config.secret").write_text(f"OPENAI_API_KEY={secret_value}\n", encoding="utf-8")

    scan = scan_for_secrets(tmp_path)
    summary = scan.safe_summary()

    assert scan.ok is False
    assert summary["finding_count"] >= 1
    assert "config.secret" in str(summary)
    assert secret_value not in str(summary)
    assert "[REDACTED]" in str(summary)


def test_doctor_secrets_reports_secret_scan_without_leaking_value(tmp_path: Path) -> None:
    secret_value = _fake_openai_key()
    (tmp_path / ".env").write_text(f"DEEPSEEK_API_KEY={secret_value}\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "secrets"])

    assert result.exit_code == 0, result.output
    assert "secret scan: blocked" in result.output
    assert ".env" in result.output
    assert secret_value not in result.output
    assert "[REDACTED]" in result.output


def test_shell_backend_blocks_target_repo_with_sensitive_file(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    secret_value = _fake_github_token()
    (target / ".env").write_text(f"GITHUB_TOKEN={secret_value}\n", encoding="utf-8")

    result = ShellBackend().execute(
        ExecutionContext(
            ticket_id="ticket_secret",
            ticket_key="ARI-SECRET",
            build_packet_id="packet_secret",
            target_repo_path=str(target),
            handoff_prompt="Run safe command.",
            backend_name="shell",
            allowed_paths=["."],
            command="python3.11 -c 'print(1)'",
            test_command="",
            confirm_execution=True,
        )
    )

    assert result.blocked is True
    assert result.failure_reason is FailureReason.SCOPE_VIOLATION
    assert "sensitive material detected" in (result.block_reason or "")
    assert secret_value not in (result.block_reason or "")


def test_shell_backend_blocks_command_referencing_sensitive_path(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)

    result = ShellBackend().execute(
        ExecutionContext(
            ticket_id="ticket_secret",
            ticket_key="ARI-SECRET",
            build_packet_id="packet_secret",
            target_repo_path=str(target),
            handoff_prompt="Do not read secrets.",
            backend_name="shell",
            allowed_paths=["."],
            command="cat .env",
            test_command="",
            confirm_execution=True,
        )
    )

    assert result.blocked is True
    assert result.failure_reason is FailureReason.SCOPE_VIOLATION
    assert "command references sensitive path" in (result.block_reason or "")
    assert "[REDACTED]" in result.stderr or "redacted" in result.stderr
