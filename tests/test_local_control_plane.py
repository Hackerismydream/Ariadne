from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.daemon_control import DaemonControlService
from ariadne_ltb.application.dtos import AssignTicketInput, CreateProjectVersionInput, DaemonStartInput, RunAssignmentInput
from ariadne_ltb.application.project_versions import ProjectVersionService
from ariadne_ltb.application.run_assignment import RunAssignmentService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.daemon import LocalDaemonWorker
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_target_project_registry_registers_and_returns_path_for_workbench(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    target = ensure_demo_target_project(tmp_path)

    registered = TargetProjectRegistry(store).register(target, "Demo Target")
    listed = TargetProjectRegistry(store).list()

    assert registered.label == "Demo Target"
    assert registered.available is True
    assert listed == [registered]
    assert registered.local_path == str(target)
    assert registered.path_exists is True
    resources = store.load_project_resources()
    assert resources[0].resource_ref["local_path"] == str(target)


def test_target_project_cli_register_and_list_redacts_path(tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    runner = CliRunner()

    register = runner.invoke(
        app,
        ["--root", str(tmp_path), "target-project", "register", str(target), "--label", "Demo Target"],
    )
    listed = runner.invoke(app, ["--root", str(tmp_path), "target-project", "list"])

    assert register.exit_code == 0, register.output
    assert listed.exit_code == 0, listed.output
    assert "Demo Target" in listed.output
    assert str(target) not in listed.output


def test_http_workbench_and_runtime_status_are_browser_safe(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")
    ProjectVersionService(store).create(
        CreateProjectVersionInput(
            target_project_id=project.id,
            version_label="v0.1",
            goal_title="Demo Target v0.1",
            goal_north_star="Deliver one scoped current version issue.",
        )
    )
    ticket = store.resolve_ticket("ARI-003")
    store.save_ticket(ticket.model_copy(update={"metadata": ticket.metadata | {"target_project_id": project.id}}))
    client = TestClient(create_app(tmp_path))

    workbench = client.get("/api/workbench")
    runtime = client.get("/api/runtime/status")

    assert workbench.status_code == 200, workbench.text
    payload = workbench.json()
    assert {ticket["key"] for ticket in payload["tickets"]} >= {"ARI-003"}
    assert payload["target_projects"][0]["label"] == "Demo Target"
    assert payload["target_projects"][0]["local_path"] == str(target)
    assert payload["environment"]["active_target_project"]["local_path"] == str(target)
    assert runtime.status_code == 200, runtime.text
    backends = {item["backend_name"] for item in runtime.json()["capabilities"]}
    assert {"codex", "claude-code", "fake-codex", "dry-run"} <= backends
    fallback = {item["backend_name"]: item["fallback_only"] for item in runtime.json()["capabilities"]}
    assert fallback["fake-codex"] is True
    assert fallback["dry-run"] is True
    assert fallback["codex"] is False
    assert "command_path" not in runtime.text


def test_service_test_source_can_run_fallback_backend_against_registered_target(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")

    assign = AssignTicketService(store).assign(
        "ARI-003",
        AssignTicketInput(
            assignee_id="build-team",
            assignee_kind="build_team",
            backend_name="fake-codex",
            runtime_profile="deterministic",
            target_project_id=project.id,
            idempotency_key="assign-ari-003",
        ),
        source="test",
    )
    assignment_id = assign.assignment.id
    assignment = store.load_assignment(assignment_id)
    assert assignment.metadata["target_repo_path"] == str(target)
    assert assign.confirmation_token

    run_payload = RunAssignmentService(store).run(
        assignment_id,
        RunAssignmentInput(
            confirmation_token=assign.confirmation_token,
            timeout_seconds=30,
            idempotency_key="run-ari-003",
        ),
    )

    assert run_payload.did_work is False
    assert run_payload.assignment.status == "ready_to_claim"
    assert run_payload.ticket_run_result is None
    daemon_result = LocalDaemonWorker(store, runtime_id="test-daemon").run_once(
        confirm_execution=True,
        assignment_id=assignment_id,
    )
    assert daemon_result.did_work is True
    assert daemon_result.status == "done"
    assert daemon_result.ticket_run_result is not None
    assert daemon_result.ticket_run_result.review_verdict == "pass"
    final_assignment = store.load_assignment(assignment_id)
    assert final_assignment.status.value == "done"
    worktree_path = Path(daemon_result.ticket_run_result.worktree_path or "")
    execution_id = daemon_result.ticket_run_result.execution_result_id
    execution = store.load_execution_result(execution_id)
    assert execution.test_exit_code == 0
    assert str(worktree_path).startswith(str(tmp_path / ".ariadne" / "worktrees"))
    assert (worktree_path / "demo_todo" / "cli.py").read_text(encoding="utf-8").count("export-json") >= 1

    client = TestClient(create_app(tmp_path))
    events = client.get(f"/api/assignments/{assignment_id}/events")
    assert events.status_code == 200, events.text
    assert events.json()["events"]
    assert "confirmation_token" not in events.text


def test_workbench_run_now_executes_against_registered_target_without_isolation(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")
    assign = AssignTicketService(store).assign(
        "ARI-003",
        AssignTicketInput(
            assignee_id="build-team",
            assignee_kind="build_team",
            backend_name="fake-codex",
            runtime_profile="deterministic",
            target_project_id=project.id,
            idempotency_key="assign-direct-target",
        ),
        source="test",
    )

    result = DaemonControlService(store).run_now(
        assign.assignment.id,
        RunAssignmentInput(
            confirmation_token=assign.confirmation_token or "",
            timeout_seconds=30,
            idempotency_key="run-direct-target",
        ),
    )

    assert result.status == "done"
    assert result.ticket_run_result is not None
    execution = store.load_execution_result(result.ticket_run_result["execution_result_id"])
    assert execution.target_repo_path == str(target)
    assert execution.target_worktree_path is None
    assert "demo_todo/cli.py" in execution.changed_files
    assert not store.list_worktree_isolations()


def test_daemon_start_replaces_loop_when_allowed_assignment_changes(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    service = DaemonControlService(store)

    first = service.start(
        DaemonStartInput(
            runtime_id="workbench-local",
            interval_seconds=10,
            max_iterations=100,
            allowed_assignment_id="assignment_old",
        )
    )
    second = service.start(
        DaemonStartInput(
            runtime_id="workbench-local",
            interval_seconds=10,
            max_iterations=100,
            allowed_assignment_id="assignment_new",
        )
    )
    stopped = service.stop()

    assert first.status == "started"
    assert second.status == "started"
    assert stopped.status == "stopped"


def test_daemon_start_replaces_unscoped_loop_with_assignment_scoped_loop(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    service = DaemonControlService(store)

    first = service.start(
        DaemonStartInput(
            runtime_id="workbench-local",
            interval_seconds=10,
            max_iterations=100,
            allowed_assignment_id=None,
        )
    )
    second = service.start(
        DaemonStartInput(
            runtime_id="workbench-local",
            interval_seconds=10,
            max_iterations=100,
            allowed_assignment_id="assignment_current",
        )
    )
    stopped = service.stop()

    assert first.status == "started"
    assert second.status == "started"
    assert stopped.status == "stopped"


def test_http_product_assign_rejects_fallback_backend(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/api/tickets/ARI-003/assign",
        json={
            "assignee_id": "build-team",
            "assignee_kind": "build_team",
            "backend_name": "fake-codex",
            "runtime_profile": "deterministic",
            "target_project_id": project.id,
        },
    )

    assert response.status_code == 422
    assert "not allowed for browser product actions" in response.text


def test_http_assign_contract_rejects_raw_command_and_target_path(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/api/tickets/ARI-003/assign",
        json={
            "assignee_id": "build-team",
            "assignee_kind": "build_team",
            "backend_name": "codex",
            "target_project_id": project.id,
            "command": "echo unsafe",
            "target_repo_path": str(target),
        },
    )

    assert response.status_code == 422
    assert "command" in response.text
    assert "target_repo_path" in response.text
