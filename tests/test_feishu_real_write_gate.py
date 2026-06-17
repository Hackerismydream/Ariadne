from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.full_demo import default_source_fixtures, run_full_demo


def _seed_ticket_with_feishu_plan(root: Path) -> None:
    run_full_demo(root=root, source_paths=default_source_fixtures(), backend_name="fake-codex")


def _latest_result(root: Path) -> dict:
    result_paths = sorted((root / ".ariadne" / "integrations" / "feishu" / "ARI-003").glob("*.json"))
    assert result_paths
    return json.loads(result_paths[-1].read_text(encoding="utf-8"))


def test_feishu_plan_command_shows_existing_dry_run_plan(tmp_path: Path) -> None:
    _seed_ticket_with_feishu_plan(tmp_path)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "feishu", "plan", "ARI-003"])

    assert result.exit_code == 0, result.output
    assert "Feishu dry-run plan for ARI-003" in result.output
    assert "dry_run: true" in result.output


def test_feishu_write_blocks_without_env_and_persists_result(tmp_path: Path) -> None:
    _seed_ticket_with_feishu_plan(tmp_path)

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "feishu", "write", "ARI-003", "--confirm-write"],
    )

    assert result.exit_code == 2, result.output
    assert "FEISHU_ENABLE_WRITE=1" in result.output
    persisted = _latest_result(tmp_path)
    assert persisted["ok"] is False
    assert persisted["blocked"] is True
    assert persisted["failure_reason"] == "external_execution_blocked"


def test_feishu_write_blocks_without_confirm(tmp_path: Path, monkeypatch) -> None:
    _seed_ticket_with_feishu_plan(tmp_path)
    monkeypatch.setenv("FEISHU_ENABLE_WRITE", "1")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "feishu", "write", "ARI-003"])

    assert result.exit_code == 2, result.output
    assert "--confirm-write" in result.output
    assert _latest_result(tmp_path)["failure_reason"] == "external_execution_blocked"


def test_feishu_write_blocks_when_lark_cli_missing(tmp_path: Path, monkeypatch) -> None:
    _seed_ticket_with_feishu_plan(tmp_path)
    monkeypatch.setenv("FEISHU_ENABLE_WRITE", "1")
    monkeypatch.setattr("ariadne_ltb.feishu.shutil.which", lambda command: None)

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "feishu", "write", "ARI-003", "--confirm-write"],
    )

    assert result.exit_code == 2, result.output
    assert "lark-cli is not installed" in result.output
    assert _latest_result(tmp_path)["failure_reason"] == "command_unavailable"


def test_feishu_write_uses_lark_cli_records_doc_and_redacts_secrets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_ticket_with_feishu_plan(tmp_path)
    monkeypatch.setenv("FEISHU_ENABLE_WRITE", "1")
    monkeypatch.setenv("FEISHU_FOLDER_TOKEN", "folder-token-value")
    monkeypatch.setenv("FEISHU_APP_SECRET", "do-not-leak-feishu")
    monkeypatch.setattr("ariadne_ltb.feishu.shutil.which", lambda command: "/usr/local/bin/lark-cli")

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        assert command[0] == "/usr/local/bin/lark-cli"
        assert "--parent-token" in command
        assert "folder-token-value" in command
        return CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "data": {
                        "document_id": "doc_123",
                        "url": "https://example.feishu.cn/docx/doc_123",
                    }
                }
            ),
            stderr="created with token=do-not-leak-feishu",
        )

    monkeypatch.setattr("ariadne_ltb.feishu.subprocess.run", fake_run)

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "feishu", "write", "ARI-003", "--confirm-write"],
    )

    assert result.exit_code == 0, result.output
    assert "Feishu write result" in result.output
    persisted = _latest_result(tmp_path)
    assert persisted["ok"] is True
    assert persisted["blocked"] is False
    assert persisted["document_id"] == "doc_123"
    assert persisted["document_url"] == "https://example.feishu.cn/docx/doc_123"
    assert "folder-token-value" not in json.dumps(persisted)
    assert "do-not-leak-feishu" not in json.dumps(persisted)
    assert "[REDACTED]" in json.dumps(persisted)
