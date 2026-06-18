from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.git_utils import git_status, run_git
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.workdir_policy import cleanup_workdirs, list_workdirs


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_workdir_list_reports_isolated_worktree(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="dry-run", isolate_worktree=True)

    items = list_workdirs(store)

    assert len(items) == 1
    assert items[0].ticket_key == "ARI-003"
    assert items[0].active is True
    assert items[0].exists is True
    assert items[0].dirty is False


def test_workdir_cleanup_requires_confirmation(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)

    try:
        cleanup_workdirs(store, confirm_cleanup=False)
    except PermissionError as exc:
        assert "--confirm-cleanup" in str(exc)
    else:
        raise AssertionError("expected PermissionError")


def test_workdir_cleanup_removes_dirty_generated_worktree_with_force(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex", isolate_worktree=True)
    before = list_workdirs(store)[0]
    assert before.dirty is True
    assert "demo_todo/cli.py" in git_status(Path(before.worktree_path))

    skipped = cleanup_workdirs(store, confirm_cleanup=True)
    assert skipped[0].skipped is True
    assert Path(before.worktree_path).exists()

    removed = cleanup_workdirs(store, confirm_cleanup=True, force_dirty=True)

    assert removed[0].removed is True
    assert not Path(before.worktree_path).exists()
    assert run_git(Path(before.base_repo_path), "branch", "--list", before.branch_name).stdout.strip() == ""
    record = store.load_worktree_isolation("ARI-003")
    assert record.active is False

    rerun = TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="dry-run", isolate_worktree=True)
    assert rerun.worktree_path
    assert Path(rerun.worktree_path).exists()


def test_workdir_cli_lists_and_cleans_json(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="dry-run", isolate_worktree=True)
    runner = CliRunner()

    listed = runner.invoke(app, ["--root", str(tmp_path), "workdir", "list", "--output", "json"])
    cleaned = runner.invoke(
        app,
        ["--root", str(tmp_path), "workdir", "cleanup", "--confirm-cleanup", "--output", "json"],
    )

    assert listed.exit_code == 0, listed.output
    assert json.loads(listed.output)[0]["ticket_key"] == "ARI-003"
    assert cleaned.exit_code == 0, cleaned.output
    assert json.loads(cleaned.output)[0]["removed"] is True
