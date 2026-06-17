from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import FailureReason
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def _fake_github_token() -> str:
    return "ghp_" + "1234567890" * 4


def _seed_ticket(root: Path):
    store = AriadneStore(root)
    ingest_sources(store, SOURCE_FIXTURES)
    return store.resolve_ticket("ARI-003")


def _latest_result(root: Path) -> dict:
    paths = sorted((root / ".ariadne" / "integrations" / "github" / "ARI-003").glob("*.json"))
    assert paths
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    return sorted(
        payloads,
        key=lambda payload: (
            payload["created_at"],
            {"link": 0, "create_issue": 1, "create_pr": 2, "sync": 3, "status": 4}.get(
                payload.get("operation", ""),
                5,
            ),
        ),
    )[-1]


def test_github_doctor_reports_without_printing_token(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", _fake_github_token())
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", lambda command: None)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "github", "doctor"])

    assert result.exit_code == 0, result.output
    assert "gh command: missing" in result.output
    assert "GITHUB_TOKEN: set" in result.output
    assert "ghp_" not in result.output


def test_github_link_records_ticket_metadata_and_result(tmp_path: Path) -> None:
    ticket = _seed_ticket(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "github",
            "link",
            ticket.key,
            "--repo",
            "Hackerismydream/Ariadne",
            "--issue",
            "123",
            "--pr",
            "45",
            "--branch",
            "codex/phase-4",
        ],
    )

    assert result.exit_code == 0, result.output
    store = AriadneStore(tmp_path)
    linked = store.resolve_ticket(ticket.key)
    assert linked.metadata["github"]["repo"] == "Hackerismydream/Ariadne"
    assert linked.metadata["github"]["issue"] == 123
    persisted = _latest_result(tmp_path)
    assert persisted["ok"] is True
    assert persisted["operation"] == "link"
    assert persisted["repo"] == "Hackerismydream/Ariadne"
    assert persisted["issue_number"] == 123


def test_github_create_issue_blocks_without_confirm_and_persists_result(tmp_path: Path) -> None:
    _seed_ticket(tmp_path)

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "github", "create-issue", "ARI-003", "--repo", "owner/repo"],
    )

    assert result.exit_code == 2, result.output
    assert "--confirm-write" in result.output
    persisted = _latest_result(tmp_path)
    assert persisted["operation"] == "create_issue"
    assert persisted["blocked"] is True
    assert persisted["failure_reason"] == FailureReason.EXTERNAL_EXECUTION_BLOCKED.value


def test_github_create_issue_uses_gh_links_ticket_and_redacts_token(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_ticket(tmp_path)
    fake_token = _fake_github_token()
    monkeypatch.setenv("GITHUB_TOKEN", fake_token)
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", lambda command: "/usr/local/bin/gh")

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        text = " ".join(command)
        if command[:3] == ["git", "config", "--get"]:
            return CompletedProcess(command, 0, stdout="https://github.com/owner/repo.git\n", stderr="")
        if command[:2] == ["git", "rev-parse"]:
            return CompletedProcess(command, 0, stdout="abc123def456\n", stderr="")
        if "issue create" in text:
            body_file = Path(command[command.index("--body-file") + 1])
            assert body_file.exists()
            assert "Ariadne ticket" in body_file.read_text(encoding="utf-8")
            return CompletedProcess(
                command,
                0,
                stdout="https://github.com/owner/repo/issues/42\n",
                stderr=f"created token={fake_token}",
            )
        return CompletedProcess(command, 1, stdout="", stderr=f"unexpected command: {command}")

    monkeypatch.setattr("ariadne_ltb.github_integration.subprocess.run", fake_run)

    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "github",
            "create-issue",
            "ARI-003",
            "--repo",
            "owner/repo",
            "--branch",
            "codex/phase-4",
            "--confirm-write",
        ],
    )

    assert result.exit_code == 0, result.output
    store = AriadneStore(tmp_path)
    linked = store.resolve_ticket("ARI-003")
    assert linked.metadata["github"]["issue"] == 42
    persisted = _latest_result(tmp_path)
    assert persisted["ok"] is True
    assert persisted["operation"] == "create_issue"
    assert persisted["issue_number"] == 42
    assert persisted["issue_url"] == "https://github.com/owner/repo/issues/42"
    assert persisted["branch"] == "codex/phase-4"
    assert "ghp_" not in json.dumps(persisted)
    assert "[REDACTED]" in json.dumps(persisted)


def test_github_sync_blocks_without_confirm_and_persists_result(tmp_path: Path) -> None:
    _seed_ticket(tmp_path)
    CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "github", "link", "ARI-003", "--repo", "owner/repo", "--issue", "7"],
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "github", "sync", "ARI-003"])

    assert result.exit_code == 2, result.output
    assert "--confirm-write" in result.output
    persisted = _latest_result(tmp_path)
    assert persisted["blocked"] is True
    assert persisted["failure_reason"] == FailureReason.EXTERNAL_EXECUTION_BLOCKED.value


def test_github_create_pr_blocks_without_confirm_and_persists_result(tmp_path: Path) -> None:
    _seed_ticket(tmp_path)
    CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "github",
            "link",
            "ARI-003",
            "--repo",
            "owner/repo",
            "--issue",
            "7",
            "--branch",
            "codex/phase-4",
        ],
    )

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "github", "create-pr", "ARI-003"])

    assert result.exit_code == 2, result.output
    assert "--confirm-write" in result.output
    persisted = _latest_result(tmp_path)
    assert persisted["operation"] == "create_pr"
    assert persisted["blocked"] is True
    assert persisted["failure_reason"] == FailureReason.EXTERNAL_EXECUTION_BLOCKED.value


def test_github_create_pr_uses_gh_links_ticket_and_redacts_token(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_ticket(tmp_path)
    CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "github",
            "link",
            "ARI-003",
            "--repo",
            "owner/repo",
            "--issue",
            "7",
            "--branch",
            "codex/phase-4",
        ],
    )
    fake_token = _fake_github_token()
    monkeypatch.setenv("GITHUB_TOKEN", fake_token)
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", lambda command: "/usr/local/bin/gh")

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        text = " ".join(command)
        if command[:3] == ["git", "config", "--get"]:
            return CompletedProcess(command, 0, stdout="https://github.com/owner/repo.git\n", stderr="")
        if command[:2] == ["git", "rev-parse"]:
            return CompletedProcess(command, 0, stdout="abc123def456\n", stderr="")
        if "pr create" in text:
            body_file = Path(command[command.index("--body-file") + 1])
            assert "Closes #7" in body_file.read_text(encoding="utf-8")
            assert "--base" in command
            assert "--head" in command
            return CompletedProcess(
                command,
                0,
                stdout="https://github.com/owner/repo/pull/11\n",
                stderr=f"created token={fake_token}",
            )
        return CompletedProcess(command, 1, stdout="", stderr=f"unexpected command: {command}")

    monkeypatch.setattr("ariadne_ltb.github_integration.subprocess.run", fake_run)

    result = CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "github",
            "create-pr",
            "ARI-003",
            "--base",
            "main",
            "--head",
            "codex/phase-4",
            "--confirm-write",
        ],
    )

    assert result.exit_code == 0, result.output
    store = AriadneStore(tmp_path)
    linked = store.resolve_ticket("ARI-003")
    assert linked.metadata["github"]["pr"] == 11
    persisted = _latest_result(tmp_path)
    assert persisted["ok"] is True
    assert persisted["operation"] == "create_pr"
    assert persisted["issue_number"] == 7
    assert persisted["pr_number"] == 11
    assert persisted["pr_url"] == "https://github.com/owner/repo/pull/11"
    assert persisted["branch"] == "codex/phase-4"
    assert "ghp_" not in json.dumps(persisted)
    assert "[REDACTED]" in json.dumps(persisted)


def test_github_sync_blocks_when_gh_missing(tmp_path: Path, monkeypatch) -> None:
    _seed_ticket(tmp_path)
    CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "github", "link", "ARI-003", "--repo", "owner/repo", "--issue", "7"],
    )
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", lambda command: None)

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "github", "sync", "ARI-003", "--confirm-write"],
    )

    assert result.exit_code == 2, result.output
    assert "gh command is not installed" in result.output
    persisted = _latest_result(tmp_path)
    assert persisted["failure_reason"] == FailureReason.COMMAND_UNAVAILABLE.value


def test_github_status_reads_issue_pr_checks_and_records_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_ticket(tmp_path)
    CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "github",
            "link",
            "ARI-003",
            "--repo",
            "owner/repo",
            "--issue",
            "7",
            "--pr",
            "11",
            "--branch",
            "codex/phase-4",
        ],
    )
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", lambda command: "/usr/local/bin/gh")

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        text = " ".join(command)
        if command[:3] == ["git", "config", "--get"]:
            return CompletedProcess(command, 0, stdout="https://github.com/owner/repo.git\n", stderr="")
        if command[:2] == ["git", "rev-parse"]:
            return CompletedProcess(command, 0, stdout="abc123def456\n", stderr="")
        if "issue view 7" in text:
            return CompletedProcess(
                command,
                0,
                stdout=json.dumps({"number": 7, "title": "Issue", "state": "OPEN", "url": "https://github.com/owner/repo/issues/7"}),
                stderr="",
            )
        if "pr view 11" in text:
            return CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "number": 11,
                        "title": "PR",
                        "state": "OPEN",
                        "url": "https://github.com/owner/repo/pull/11",
                        "headRefName": "codex/phase-4",
                        "headRefOid": "abc123def456",
                        "baseRefName": "main",
                        "mergeable": "MERGEABLE",
                        "reviewDecision": "REVIEW_REQUIRED",
                        "statusCheckRollup": [],
                    }
                ),
                stderr="",
            )
        if "pr checks 11" in text:
            return CompletedProcess(
                command,
                8,
                stdout=json.dumps([{"name": "pytest", "bucket": "pending", "state": "IN_PROGRESS"}]),
                stderr="checks pending",
            )
        return CompletedProcess(command, 1, stdout="", stderr=f"unexpected command: {command}")

    monkeypatch.setattr("ariadne_ltb.github_integration.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "github", "status", "ARI-003"])

    assert result.exit_code == 0, result.output
    persisted = _latest_result(tmp_path)
    assert persisted["ok"] is True
    assert persisted["operation"] == "status"
    assert persisted["issue_url"] == "https://github.com/owner/repo/issues/7"
    assert persisted["pr_url"] == "https://github.com/owner/repo/pull/11"
    assert persisted["evidence"]["checks"][0]["bucket"] == "pending"


def test_github_status_treats_no_checks_as_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_ticket(tmp_path)
    CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "github",
            "link",
            "ARI-003",
            "--repo",
            "owner/repo",
            "--issue",
            "7",
            "--pr",
            "11",
            "--branch",
            "codex/phase-4",
        ],
    )
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", lambda command: "/usr/local/bin/gh")

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        text = " ".join(command)
        if command[:3] == ["git", "config", "--get"]:
            return CompletedProcess(command, 0, stdout="https://github.com/owner/repo.git\n", stderr="")
        if command[:2] == ["git", "rev-parse"]:
            return CompletedProcess(command, 0, stdout="abc123def456\n", stderr="")
        if "issue view 7" in text:
            return CompletedProcess(
                command,
                0,
                stdout=json.dumps({"number": 7, "title": "Issue", "state": "OPEN", "url": "https://github.com/owner/repo/issues/7"}),
                stderr="",
            )
        if "pr view 11" in text:
            return CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "number": 11,
                        "title": "PR",
                        "state": "OPEN",
                        "url": "https://github.com/owner/repo/pull/11",
                        "headRefName": "codex/phase-4",
                        "headRefOid": "abc123def456",
                    }
                ),
                stderr="",
            )
        if "pr checks 11" in text:
            return CompletedProcess(command, 1, stdout="", stderr="no checks reported on the branch\n")
        return CompletedProcess(command, 1, stdout="", stderr=f"unexpected command: {command}")

    monkeypatch.setattr("ariadne_ltb.github_integration.subprocess.run", fake_run)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "github", "status", "ARI-003"])

    assert result.exit_code == 0, result.output
    persisted = _latest_result(tmp_path)
    assert persisted["ok"] is True
    assert persisted["evidence"]["checks"] == []
    assert persisted["evidence"]["checks_status"] == "no_checks_reported"


def test_github_sync_uses_gh_records_remote_evidence_and_redacts_token(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_ticket(tmp_path)
    CliRunner().invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "github",
            "link",
            "ARI-003",
            "--repo",
            "owner/repo",
            "--issue",
            "7",
            "--pr",
            "9",
            "--branch",
            "codex/phase-4",
        ],
    )
    fake_token = _fake_github_token()
    monkeypatch.setenv("GITHUB_TOKEN", fake_token)
    monkeypatch.setattr("ariadne_ltb.github_integration.shutil.which", lambda command: "/usr/local/bin/gh")

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        text = " ".join(command)
        if command[:3] == ["git", "config", "--get"]:
            return CompletedProcess(command, 0, stdout="https://github.com/owner/repo.git\n", stderr="")
        if command[:2] == ["git", "rev-parse"]:
            return CompletedProcess(command, 0, stdout="abc123def456\n", stderr="")
        if "issue view 7" in text:
            return CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "number": 7,
                        "title": "Issue title",
                        "state": "OPEN",
                        "url": "https://github.com/owner/repo/issues/7",
                    }
                ),
                stderr="",
            )
        if "pr view 9" in text:
            return CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "number": 9,
                        "title": "PR title",
                        "state": "OPEN",
                        "url": "https://github.com/owner/repo/pull/9",
                        "headRefName": "codex/phase-4",
                        "headRefOid": "abc123def456",
                    }
                ),
                stderr="",
            )
        if "issue comment 7" in text:
            return CompletedProcess(
                command,
                0,
                stdout="https://github.com/owner/repo/issues/7#issuecomment-1\n",
                stderr=f"posted token={fake_token}",
            )
        return CompletedProcess(command, 1, stdout="", stderr=f"unexpected command: {command}")

    monkeypatch.setattr("ariadne_ltb.github_integration.subprocess.run", fake_run)

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "github", "sync", "ARI-003", "--confirm-write"],
    )

    assert result.exit_code == 0, result.output
    persisted = _latest_result(tmp_path)
    assert persisted["ok"] is True
    assert persisted["blocked"] is False
    assert persisted["repo"] == "owner/repo"
    assert persisted["issue_number"] == 7
    assert persisted["pr_number"] == 9
    assert persisted["branch"] == "codex/phase-4"
    assert persisted["commit_sha"] == "abc123def456"
    assert persisted["remote_url"] == "https://github.com/owner/repo.git"
    assert persisted["issue_url"] == "https://github.com/owner/repo/issues/7"
    assert persisted["pr_url"] == "https://github.com/owner/repo/pull/9"
    assert persisted["comment_url"] == "https://github.com/owner/repo/issues/7#issuecomment-1"
    assert "ghp_" not in json.dumps(persisted)
    assert "[REDACTED]" in json.dumps(persisted)
