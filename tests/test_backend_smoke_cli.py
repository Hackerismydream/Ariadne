from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.execution import CodexBackend


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
