from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import _runtime_profile_values, app


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


def test_ticket_run_help_presents_production_aware_auto_defaults() -> None:
    result = CliRunner().invoke(app, ["ticket", "run", "--help"])
    compact_output = " ".join(result.output.split())

    assert result.exit_code == 0, result.output
    assert "Ariadne production-first local Agent Workbench" not in result.output
    assert "auto|deterministic|llm" in compact_output
    assert "auto production" in compact_output
    assert "defaults to llm" in compact_output
    assert "[default: auto]" in result.output
    assert "Defaults to the local fixture target" not in result.output
    assert "offline fixture target" in compact_output
    assert "smoke/regression only" in compact_output


def test_root_help_presents_production_first_workbench() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0, result.output
    assert "Ariadne production-first local Agent Workbench for AI builders." in result.output
    assert "local deterministic Learning-to-Build workbench" not in result.output


def test_runtime_profile_auto_resolves_to_llm_for_production() -> None:
    assert _runtime_profile_values("production", "auto", "auto", "auto") == ("llm", "llm", "llm")
    assert _runtime_profile_values("production", None, None, None) == ("llm", "llm", "llm")


def test_runtime_profile_auto_resolves_to_deterministic_for_offline_profile() -> None:
    assert _runtime_profile_values("deterministic", "auto", "auto", "auto") == (
        "deterministic",
        "deterministic",
        "deterministic",
    )
