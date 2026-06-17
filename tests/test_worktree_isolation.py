from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.daemon import LocalDaemonWorker
from ariadne_ltb.git_utils import git_status, run_git
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import FailureReason, TicketStatus
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_cli_ticket_run_isolate_worktree_creates_and_records_worktree(tmp_path: Path) -> None:
    runner = CliRunner()
    ingest_result = runner.invoke(
        app,
        ["--root", str(tmp_path), "ingest", *[str(path) for path in SOURCE_FIXTURES]],
    )
    assert ingest_result.exit_code == 0, ingest_result.output
    target = ensure_demo_target_project(tmp_path)
    base_sha = run_git(target, "rev-parse", "HEAD").stdout.strip()

    run_result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "ticket",
            "run",
            "ARI-003",
            "--backend",
            "dry-run",
            "--isolate-worktree",
        ],
    )

    assert run_result.exit_code == 0, run_result.output
    assert "worktree:" in run_result.output
    store = AriadneStore(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    record = ticket.metadata["worktree_isolation"]
    worktree_path = Path(record["worktree_path"])
    assert worktree_path.exists()
    assert run_git(worktree_path, "branch", "--show-current").stdout.strip() == record["branch_name"]
    assert record["ticket_id"] == ticket.id
    assert record["ticket_key"] == "ARI-003"
    assert record["base_branch"]
    assert record["base_sha"] == base_sha
    assert record["active"] is True
    assert git_status(target) == ""


def test_isolated_fake_codex_changes_worktree_without_dirtying_base(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)

    result = TicketRunOrchestrator(store).run_ticket(
        "ARI-003",
        backend_name="fake-codex",
        isolate_worktree=True,
    )

    ticket = store.load_ticket(result.ticket_id)
    worktree_path = Path(ticket.metadata["worktree_isolation"]["worktree_path"])
    assert ticket.status is TicketStatus.DONE
    assert result.changed_files == ["demo_todo/cli.py", "tests/test_cli.py"]
    assert "demo_todo/cli.py" in git_status(worktree_path)
    assert git_status(target) == ""


def test_daemon_assignment_runs_ticket_in_isolated_worktree(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    base_sha = run_git(target, "rev-parse", "HEAD").stdout.strip()
    ticket = store.resolve_ticket("ARI-003")
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))

    result = LocalDaemonWorker(store).run_once()

    ticket = store.load_ticket(ticket.id)
    record = ticket.metadata["worktree_isolation"]
    worktree_path = Path(record["worktree_path"])
    assert result.assignment_id == assignment.id
    assert result.ticket_run_result is not None
    assert result.ticket_run_result.worktree_path == str(worktree_path)
    assert worktree_path.exists()
    assert run_git(worktree_path, "branch", "--show-current").stdout.strip() == record["branch_name"]
    assert record["ticket_id"] == ticket.id
    assert record["base_sha"] == base_sha
    assert git_status(target) == ""


def test_isolate_worktree_blocks_when_ticket_already_has_active_worktree(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="dry-run", isolate_worktree=True)

    result = TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="dry-run", isolate_worktree=True)

    execution = store.load_execution_result(result.execution_result_id)
    assert execution.blocked is True
    assert execution.failure_reason is FailureReason.RESOURCE_LOCKED
    assert "active isolated worktree already exists" in (execution.block_reason or "")


def test_isolate_worktree_blocks_dirty_base_with_typed_execution_artifact(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    (target / "README.md").write_text("dirty base\n", encoding="utf-8")

    result = TicketRunOrchestrator(store).run_ticket(
        "ARI-003",
        backend_name="dry-run",
        target_repo_path=str(target),
        isolate_worktree=True,
    )

    execution = store.load_execution_result(result.execution_result_id)
    assert execution.blocked is True
    assert execution.failure_reason is FailureReason.DIRTY_BASE_CHECKOUT
    assert "base checkout is dirty" in (execution.block_reason or "")
    assert "README.md" in execution.git_status_before
    log = store.load_artifact(execution.execution_log_artifact_id or "")
    payload = json.loads(Path(log.path).read_text(encoding="utf-8"))
    assert payload["failure_reason"] == "dirty_base_checkout"
    assert not (tmp_path / ".ariadne" / "worktrees" / result.ticket_key.lower()).exists()


def test_worktree_isolation_metadata_persists_to_file_and_artifact(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)

    result = TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="dry-run", isolate_worktree=True)

    ticket = store.load_ticket(result.ticket_id)
    metadata = ticket.metadata["worktree_isolation"]
    record_path = Path(metadata["record_path"])
    assert record_path.exists()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record == metadata

    artifacts = store.list_artifacts_for_ticket(ticket.id)
    worktree_artifacts = [
        artifact for artifact in artifacts if artifact.artifact_type.value == "worktree_isolation"
    ]
    assert len(worktree_artifacts) == 1
    artifact_record = json.loads(Path(worktree_artifacts[0].path).read_text(encoding="utf-8"))
    assert artifact_record == metadata
