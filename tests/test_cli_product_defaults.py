from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURE = ROOT / "examples" / "sources" / "github_tiny_cli_readme.md"


def test_ticket_assign_auto_profile_uses_llm_for_codex(tmp_path: Path) -> None:
    runner = CliRunner()
    ingest = runner.invoke(app, ["--root", str(tmp_path), "ingest", str(SOURCE_FIXTURE)])
    assert ingest.exit_code == 0, ingest.output

    result = runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-001", "--to", "codex"])

    assert result.exit_code == 0, result.output
    assert "backend: codex" in result.output
    assert "planner: llm" in result.output
    assert "agent runtime: llm" in result.output
    assert "backlog planner: llm" in result.output


def test_ticket_assign_auto_profile_keeps_fake_codex_deterministic(tmp_path: Path) -> None:
    runner = CliRunner()
    ingest = runner.invoke(app, ["--root", str(tmp_path), "ingest", str(SOURCE_FIXTURE)])
    assert ingest.exit_code == 0, ingest.output

    result = runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-001", "--to", "fake-codex"])

    assert result.exit_code == 0, result.output
    assert "backend: fake-codex" in result.output
    assert "planner: deterministic" in result.output
    assert "agent runtime: deterministic" in result.output
    assert "backlog planner: deterministic" in result.output
