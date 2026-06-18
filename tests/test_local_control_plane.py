from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from ariadne_ltb.application.dtos import AssignTicketInput
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_target_project_registry_registers_without_exposing_paths(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    target = ensure_demo_target_project(tmp_path)

    registered = TargetProjectRegistry(store).register(target, "Demo Target")
    listed = TargetProjectRegistry(store).list()

    assert registered.label == "Demo Target"
    assert registered.available is True
    assert listed == [registered]
    assert str(target) not in registered.model_dump_json()
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
    TargetProjectRegistry(store).register(target, "Demo Target")
    client = TestClient(create_app(tmp_path))

    workbench = client.get("/api/workbench")
    runtime = client.get("/api/runtime/status")

    assert workbench.status_code == 200, workbench.text
    payload = workbench.json()
    assert {ticket["key"] for ticket in payload["tickets"]} >= {"ARI-003"}
    assert payload["target_projects"][0]["label"] == "Demo Target"
    assert str(target) not in workbench.text
    assert runtime.status_code == 200, runtime.text
    backends = {item["backend_name"] for item in runtime.json()["capabilities"]}
    assert backends == {"codex", "claude-code"}
    assert "command_path" not in runtime.text


def test_http_assign_and_run_assignment_uses_registered_target(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = ensure_demo_target_project(tmp_path)
    project = TargetProjectRegistry(store).register(target, "Demo Target")
    client = TestClient(create_app(tmp_path))

    assign = client.post(
        "/api/tickets/ARI-003/assign",
        json=AssignTicketInput(
            assignee_id="build-team",
            assignee_kind="build_team",
            backend_name="fake-codex",
            planner_name="deterministic",
            agent_runtime="deterministic",
            backlog_planner_name="deterministic",
            target_project_id=project.id,
        ).model_dump(mode="json"),
        headers={"Idempotency-Key": "assign-ari-003"},
    )
    assert assign.status_code == 200, assign.text
    assignment_id = assign.json()["assignment"]["id"]
    assignment = store.load_assignment(assignment_id)
    assert assignment.metadata["target_repo_path"] == str(target)

    run = client.post(
        f"/api/assignments/{assignment_id}/run",
        json={
            "confirm_execution": False,
            "runtime_id": "api-test",
            "agent_runtime": "deterministic",
            "backlog_planner": "deterministic",
            "timeout_seconds": 30,
        },
        headers={"Idempotency-Key": "run-ari-003"},
    )

    assert run.status_code == 200, run.text
    run_payload = run.json()
    assert run_payload["did_work"] is True
    assert run_payload["assignment"]["status"] == "done"
    assert run_payload["ticket_run_result"]["review_verdict"] == "pass"
    worktree_path = Path(run_payload["ticket_run_result"]["worktree_path"])
    execution_id = run_payload["ticket_run_result"]["execution_result_id"]
    execution = store.load_execution_result(execution_id)
    assert execution.test_exit_code == 0
    assert str(worktree_path).startswith(str(tmp_path / ".ariadne" / "worktrees"))
    assert (worktree_path / "demo_todo" / "cli.py").read_text(encoding="utf-8").count("export-json") >= 1


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
