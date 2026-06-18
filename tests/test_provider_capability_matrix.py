from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.models import RuntimeCapability


def test_backend_matrix_persists_required_backend_capabilities(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    monkeypatch.setenv("ARIADNE_CODEX_COMMAND_TEMPLATE", "codex exec --secret hidden")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "never-print-this")
    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", lambda command: None)
    runner = CliRunner()

    result = runner.invoke(app, ["--root", str(tmp_path), "backend", "matrix"])

    assert result.exit_code == 0, result.output
    assert "Provider capability matrix:" in result.output
    for backend in ["fake-codex", "dry-run", "shell", "codex", "claude-code"]:
        assert backend in result.output
    assert "prompt-file" in result.output
    assert "mcp" in result.output
    assert "reasoning" in result.output
    assert "tests" in result.output
    assert "ARIADNE_CODEX_COMMAND_TEMPLATE:set" in result.output
    assert "codex exec --secret hidden" not in result.output
    assert "never-print-this" not in result.output

    snapshot = tmp_path / ".ariadne" / "runtimes" / "capability_snapshot.json"
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    capabilities = {
        item["backend_name"]: RuntimeCapability.model_validate(item)
        for item in data["capabilities"]
    }
    assert set(capabilities) == {"fake-codex", "dry-run", "shell", "codex", "claude-code"}
    assert capabilities["codex"].available is False
    assert capabilities["codex"].supports_prompt_file is False
    assert capabilities["codex"].supports_stdin_prompt is True
    assert capabilities["codex"].supports_diff_capture is True
    assert capabilities["codex"].supports_test_capture is True
    assert capabilities["codex"].command_template_set is True
    assert "codex command is missing" in capabilities["codex"].disabled_reasons
    assert "ARIADNE_ENABLE_EXTERNAL_EXECUTION is unset" in capabilities["shell"].disabled_reasons
    assert capabilities["claude-code"].supports_stdin_prompt is True


def test_backend_matrix_json_and_command_template_rendering_status(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_which(command: str) -> str | None:
        paths = {"codex": "/usr/local/bin/codex", "claude": "/usr/local/bin/claude"}
        return paths.get(command)

    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setenv("ARIADNE_CLAUDE_COMMAND_TEMPLATE", "claude --print < {handoff_file}")
    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", fake_which)
    runner = CliRunner()

    result = runner.invoke(app, ["--root", str(tmp_path), "backend", "matrix", "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    capabilities = {item["backend_name"]: item for item in data["capabilities"]}
    assert capabilities["codex"]["available"] is True
    assert capabilities["codex"]["command_path"] == "/usr/local/bin/codex"
    assert capabilities["codex"]["external_execution_enabled"] is True
    assert capabilities["codex"]["command_template_set"] is False
    assert capabilities["claude-code"]["command_path"] == "/usr/local/bin/claude"
    assert capabilities["claude-code"]["command_template_set"] is True
    assert capabilities["claude-code"]["disabled_reasons"] == []


def test_export_board_includes_provider_capability_matrix(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", lambda command: None)
    runner = CliRunner()

    matrix = runner.invoke(app, ["--root", str(tmp_path), "backend", "matrix"])
    export = runner.invoke(app, ["--root", str(tmp_path), "export", "board"])

    assert matrix.exit_code == 0, matrix.output
    assert export.exit_code == 0, export.output
    board = tmp_path / ".ariadne" / "board" / "index.md"
    text = board.read_text(encoding="utf-8")
    assert "## Provider Capability Matrix" in text
    assert "prompt_file=`false`" in text
    assert "stdin=`true`" in text
    assert "blocked=`codex command is missing; ARIADNE_ENABLE_EXTERNAL_EXECUTION is unset`" in text
