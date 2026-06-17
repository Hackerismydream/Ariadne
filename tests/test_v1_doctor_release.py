from __future__ import annotations

import json
from pathlib import Path
import subprocess

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
    assert "secret scan:" in result.output
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
    assert "secret scan:" in result.output


def test_doctor_integrations_reports_readiness_without_secret_values(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-leak-deepseek")
    monkeypatch.setenv(
        "ARIADNE_LLM_BASE_URL",
        "https://user:do-not-leak-url-password@proxy.example.com:8443/v1?token=do-not-leak-url-token",
    )
    monkeypatch.setenv("FEISHU_APP_SECRET", "do-not-leak-feishu")
    monkeypatch.setenv("GITHUB_TOKEN", "do-not-leak-github")
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    monkeypatch.setenv("FEISHU_ENABLE_WRITE", "1")

    def fake_which(command: str) -> str | None:
        return {
            "codex": "/usr/local/bin/codex",
            "claude": "/usr/local/bin/claude",
            "lark-cli": "/usr/local/bin/lark-cli",
            "gh": "/usr/local/bin/gh",
        }.get(command)

    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.doctor.shutil.which", fake_which)
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", fake_which)
    monkeypatch.setattr(
        "ariadne_ltb.doctor.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )
    monkeypatch.setattr(
        "ariadne_ltb.github_integration.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "ok\n", ""),
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "integrations"])

    assert result.exit_code == 0, result.output
    assert "Integration doctor: ok" in result.output
    assert "DeepSeek API key: set" in result.output
    assert "CodexBackend command: found /usr/local/bin/codex" in result.output
    assert "ClaudeCodeBackend command: found /usr/local/bin/claude" in result.output
    assert "Feishu lark-cli command: found /usr/local/bin/lark-cli" in result.output
    assert "GitHub gh command: found /usr/local/bin/gh" in result.output
    assert "GitHub auth status: ok" in result.output
    assert "GitHub git transport: ok" in result.output
    assert "DeepSeek base URL: https://proxy.example.com:8443" in result.output
    assert "do-not-leak" not in result.output
    assert "user:" not in result.output

    snapshot_path = tmp_path / ".ariadne" / "doctor" / "integrations.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["llm"]["deepseek_api_key"] == "set"
    assert snapshot["llm"]["base_url"] == "https://proxy.example.com:8443"
    assert snapshot["feishu"]["FEISHU_APP_SECRET"] == "set"
    assert snapshot["github"]["GITHUB_TOKEN"] == "set"
    assert snapshot["github"]["git_transport"]["status"] == "ok"
    assert "do-not-leak" not in snapshot_path.read_text(encoding="utf-8")
    assert "user:" not in snapshot_path.read_text(encoding="utf-8")


def test_doctor_integrations_json_output_is_machine_readable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("FEISHU_ENABLE_WRITE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("ariadne_ltb.runtime.shutil.which", lambda command: None)
    monkeypatch.setattr("ariadne_ltb.doctor.shutil.which", lambda command: None)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "integrations", "--json"])

    assert result.exit_code == 0, result.output
    snapshot = json.loads(result.output)
    assert snapshot["llm"]["provider"] == "deepseek"
    assert snapshot["llm"]["deepseek_api_key"] == "unset"
    assert snapshot["coding_backends"]["codex"]["available"] is False
    assert snapshot["github"]["auth_status"] == "unavailable"
    assert snapshot["github"]["git_transport"]["status"] in {"no_remote", "failed"}
    assert (tmp_path / ".ariadne" / "doctor" / "integrations.json").exists()


def test_gitignore_contains_v1_secret_patterns() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for pattern in [".env", ".env.*", "*.secret", ".secrets", "secrets/", ".ariadne/"]:
        assert pattern in gitignore


def test_verify_v1_script_exists_and_is_executable() -> None:
    script = ROOT / "scripts" / "verify_v1.sh"
    assert script.exists()
    assert script.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
