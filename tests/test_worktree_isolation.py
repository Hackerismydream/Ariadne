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
from ariadne_ltb.worktrees import branch_binding_for_ticket, prepare_isolated_worktree
from tests.helpers import ready_assignment_with_handoff


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def _ready_assignment(store: AriadneStore, ticket, assignment, target: Path):  # noqa: ANN001
    return ready_assignment_with_handoff(store, ticket, assignment, target)


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
    assert record["branch_policy"] == "codex-ticket-slug-v1"
    assert record["branch_name"].startswith("codex/ari-003-")
    assert record["target_repo_path"] == str(target)
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


def test_isolated_fake_codex_records_worktree_target_and_handoff_resource(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)

    result = TicketRunOrchestrator(store).run_ticket(
        "ARI-003",
        backend_name="fake-codex",
        target_repo_path=str(target),
        isolate_worktree=True,
    )

    ticket = store.load_ticket(result.ticket_id)
    worktree_path = ticket.metadata["worktree_isolation"]["worktree_path"]
    execution = store.load_execution_result(result.execution_result_id)
    handoff = store.read_artifact_text(store.load_artifact(result.handoff_artifact_id))
    artifacts = [store.load_artifact(artifact_id) for artifact_id in ticket.artifact_ids]
    resource_artifacts = [
        artifact for artifact in artifacts if artifact.artifact_type.value == "project_resources"
    ]
    resources = json.loads(Path(resource_artifacts[-1].path).read_text(encoding="utf-8"))
    worktree_resource = resources["resources"][0]

    assert execution.target_repo_path == worktree_path
    assert execution.target_worktree_path == worktree_path
    assert "## Project Resources" in handoff
    assert worktree_resource["id"] in handoff
    assert worktree_resource["resource_ref"]["local_path"] == worktree_path
    assert worktree_path in handoff
    assert git_status(target) == ""


def test_daemon_assignment_runs_ticket_in_isolated_worktree(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    base_sha = run_git(target, "rev-parse", "HEAD").stdout.strip()
    ticket = store.resolve_ticket("ARI-003")
    assignment = _ready_assignment(
        store,
        ticket,
        store.create_assignment(ticket, store.resolve_agent_profile("fake-codex")),
        target,
    )

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


def test_daemon_assignments_get_distinct_isolated_worktrees(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    agent = store.resolve_agent_profile("fake-codex")
    first = _ready_assignment(store, ticket, store.create_assignment(ticket, agent), target)

    first_result = LocalDaemonWorker(store).run_once(assignment_id=first.id)

    second_ticket = store.load_ticket(ticket.id)
    second = _ready_assignment(store, second_ticket, store.create_assignment(second_ticket, agent), target)
    second_result = LocalDaemonWorker(store).run_once(assignment_id=second.id)
    records = store.list_worktree_isolations()
    paths = {record.worktree_path for record in records}

    assert first_result.status == "done"
    assert second_result.status == "done"
    assert len(records) == 2
    assert len(paths) == 2
    assert all(Path(path).exists() for path in paths)
    assert all(record.owner_metadata["assignment_id"] in {first.id, second.id} for record in records)
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


def test_isolate_worktree_blocks_missing_target_without_demo_fallback(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    missing_target = tmp_path / "missing-target"

    result = TicketRunOrchestrator(store).run_ticket(
        "ARI-003",
        backend_name="dry-run",
        target_repo_path=str(missing_target),
        isolate_worktree=True,
    )

    execution = store.load_execution_result(result.execution_result_id)
    assert execution.blocked is True
    assert execution.failure_reason is FailureReason.INVALID_RESOURCE
    assert execution.target_repo_path == str(missing_target)
    assert execution.target_worktree_path is None
    assert execution.block_reason == "target path does not exist"
    assert not (tmp_path / ".ariadne" / "demo_target_project").exists()


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
    resolved = store.resolve_active_worktree("ARI-003")
    assert resolved is not None
    assert resolved.branch_name == metadata["branch_name"]
    assert resolved.worktree_path == metadata["worktree_path"]

    artifacts = store.list_artifacts_for_ticket(ticket.id)
    worktree_artifacts = [
        artifact for artifact in artifacts if artifact.artifact_type.value == "worktree_isolation"
    ]
    assert len(worktree_artifacts) == 1
    artifact_record = json.loads(Path(worktree_artifacts[0].path).read_text(encoding="utf-8"))
    assert artifact_record == metadata


def test_branch_binding_is_canonical_deterministic_and_collision_resistant(
    tmp_path: Path,
) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    ticket = store.resolve_ticket("ARI-003")

    first = branch_binding_for_ticket(ticket)
    second = branch_binding_for_ticket(ticket)
    duplicate_title = ticket.model_copy(update={"id": "ticket_different"})

    assert first == second
    assert first.policy == "codex-ticket-slug-v1"
    assert first.branch_name.startswith("codex/ari-003-")
    assert first.branch_name == first.branch_name.lower()
    assert "/" not in first.worktree_dir_name
    assert branch_binding_for_ticket(duplicate_title).branch_name != first.branch_name


def test_isolate_worktree_blocks_when_canonical_branch_already_exists(
    tmp_path: Path,
) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    binding = branch_binding_for_ticket(ticket)
    create_branch = run_git(target, "branch", binding.branch_name)
    assert create_branch.returncode == 0, create_branch.stderr

    result = prepare_isolated_worktree(store, ticket, target)

    assert result.record is None
    assert result.block is not None
    assert result.block.failure_reason is FailureReason.RESOURCE_LOCKED
    assert "isolated branch already exists" in result.block.reason
    assert not store.worktree_record_path(ticket.key).exists()
    assert not store.worktree_path(binding.worktree_dir_name).exists()


def test_isolate_worktree_rejects_invalid_ticket_key_before_filesystem_mutation(
    tmp_path: Path,
) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    ticket = store.resolve_ticket("ARI-003").model_copy(update={"key": "ARI/003"})

    result = prepare_isolated_worktree(store, ticket, target)

    assert result.record is None
    assert result.block is not None
    assert result.block.failure_reason is FailureReason.INVALID_RESOURCE
    assert "invalid ticket key" in result.block.reason
    assert not any(store.worktree_records_dir.glob("*.json"))
    assert not any(path.name != "records" for path in store.worktrees_dir.iterdir())
    branches = run_git(target, "branch", "--list", "codex/*").stdout.strip()
    assert branches == ""


def test_isolate_worktree_rejects_invalid_explicit_branch_slug_before_mutation(
    tmp_path: Path,
) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    ticket = store.resolve_ticket("ARI-003").model_copy(
        update={"metadata": {"branch_slug": "../unsafe"}}
    )

    result = prepare_isolated_worktree(store, ticket, target)

    assert result.record is None
    assert result.block is not None
    assert result.block.failure_reason is FailureReason.INVALID_RESOURCE
    assert "invalid branch slug" in result.block.reason
    assert not any(store.worktree_records_dir.glob("*.json"))
    assert not any(path.name != "records" for path in store.worktrees_dir.iterdir())
    branches = run_git(target, "branch", "--list", "codex/*").stdout.strip()
    assert branches == ""
