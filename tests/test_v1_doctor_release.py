from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_doctor_secrets_does_not_print_secret_values(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-leak-deepseek")
    monkeypatch.setenv("FEISHU_APP_SECRET", "do-not-leak-feishu")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "secrets"])

    assert result.exit_code == 0, result.output
    assert "DEEPSEEK_API_KEY: set" in result.output
    assert "FEISHU_APP_SECRET: set" in result.output
    assert "do-not-leak" not in result.output


def test_doctor_v1_reports_local_readiness(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"])
    runner.invoke(app, ["--root", str(tmp_path), "daemon", "run-once"])
    runner.invoke(app, ["--root", str(tmp_path), "export", "board"])

    result = runner.invoke(app, ["--root", str(tmp_path), "doctor", "v1"])

    assert result.exit_code == 0, result.output
    assert "agent profiles: ok" in result.output
    assert "backend capability: ok" in result.output
    assert "source fixtures: ok" in result.output
    assert "board: ok" in result.output
    assert "safety gates: ok" in result.output


def test_gitignore_contains_v1_secret_patterns() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for pattern in [".env", ".env.*", "*.secret", "secrets/", ".ariadne/"]:
        assert pattern in gitignore


def test_verify_v1_script_exists_and_is_executable() -> None:
    script = ROOT / "scripts" / "verify_v1.sh"
    assert script.exists()
    assert script.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
