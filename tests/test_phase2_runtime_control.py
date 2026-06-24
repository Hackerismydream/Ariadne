from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.dtos import AssignTicketInput, RunAssignmentInput
from ariadne_ltb.application.run_assignment import RunAssignmentService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.application.workbench_issues import WorkbenchIssuesService
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.models import ExecutionResult, FailureReason, stable_id
from ariadne_ltb.retry import create_retry_assignment
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def _register_demo_target(store: AriadneStore, tmp_path: Path) -> str:
    return TargetProjectRegistry(store).register(ensure_demo_target_project(tmp_path), "Demo Target").id


def _assign_http_codex(store: AriadneStore, target_project_id: str, key: str = "assign-1"):
    return AssignTicketService(store).assign(
        "ARI-003",
        AssignTicketInput(
            assignee_id="codex",
            assignee_kind="agent",
            backend_name="codex",
            runtime_profile="production",
            target_project_id=target_project_id,
            idempotency_key=key,
        ),
        source="http",
    )


def test_duplicate_http_assign_reuses_current_runnable_assignment(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target_project_id = _register_demo_target(store, tmp_path)

    first = _assign_http_codex(store, target_project_id, "duplicate-assign-1")
    second = _assign_http_codex(store, target_project_id, "duplicate-assign-2")

    assignments = [
        item
        for item in store.list_assignments_for_ticket(store.resolve_ticket("ARI-003").id)
        if item.backend_name == "codex"
    ]
    assert second.assignment.id == first.assignment.id
    assert second.confirmation_token is None
    assert len(assignments) == 1


def test_run_assignment_survives_browser_refresh_with_persisted_authorization(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target_project_id = _register_demo_target(store, tmp_path)
    assigned = _assign_http_codex(store, target_project_id, "refresh-run-assign")

    result = RunAssignmentService(store).run(
        assigned.assignment.id,
        RunAssignmentInput(
            confirmation_token="",
            idempotency_key="refresh-run-without-browser-token",
        ),
    )

    assert result.assignment.id == assigned.assignment.id
    assert result.status == "ready_to_claim"
    assert "run dispatched" in result.message


def test_terminal_assignment_run_request_is_noop_without_fake_progress(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    assignment = assignment.model_copy(
        deep=True,
        update={"metadata": assignment.metadata | {"runtime_authorization_id": "test-auth"}},
    )
    store.save_assignment(assignment.mark_failed("runtime offline", FailureReason.RUNTIME_OFFLINE))
    before_events = len(store.list_runtime_events())
    before_comments = len(store.list_comments(ticket.id))

    result = RunAssignmentService(store).run(
        assignment.id,
        RunAssignmentInput(confirmation_token="", idempotency_key="terminal-noop"),
    )

    assert result.status == "failed"
    assert "no run dispatch" in result.message
    assert len(store.list_runtime_events()) == before_events
    assert len(store.list_comments(ticket.id)) == before_comments


def test_inbox_list_projects_allowed_actions_and_blocks_invalid_action(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(
        assignment.mark_blocked(
            "external execution disabled",
            FailureReason.EXTERNAL_EXECUTION_BLOCKED,
        )
    )
    item = refresh_inbox(store)[0]
    client = TestClient(create_app(tmp_path))

    listed = client.get("/api/inbox")
    rerun = client.post(f"/api/inbox/{item.id}/rerun", json={"reason": "retry without authorization"})

    assert listed.status_code == 200, listed.text
    inbox_item = listed.json()["inbox"][0]
    assert inbox_item["canonical_blocker_id"] == item.id
    assert inbox_item["allowed_actions"] == ["acknowledge", "resolve"]
    assert rerun.status_code == 409
    assert "not safe to rerun" in rerun.text


def test_runtime_failure_pipeline_projects_one_active_canonical_inbox_item(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_blocked("external execution disabled", FailureReason.EXTERNAL_EXECUTION_BLOCKED))
    execution = ExecutionResult(
        id=stable_id("execution", ticket.id, "phase2", "blocked"),
        ticket_id=ticket.id,
        backend_name="codex",
        dry_run=False,
        blocked=True,
        block_reason="external execution disabled",
        failure_reason=FailureReason.EXTERNAL_EXECUTION_BLOCKED,
        command="codex",
        exit_code=1,
        assignment_id=assignment.id,
    )
    store.save_execution_result(execution)

    items = refresh_inbox(store)
    active = [item for item in items if item.active]
    archived = [item for item in items if not item.active]

    assert len(active) == 1
    assert active[0].source_type == "assignment"
    assert active[0].failure_reason is FailureReason.EXTERNAL_EXECUTION_BLOCKED
    assert archived
    assert all(item.superseded_by_ref == active[0].id for item in archived)


def test_assignment_retry_endpoint_creates_explicit_attempt_lineage(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_blocked("runtime offline", FailureReason.RUNTIME_OFFLINE))
    client = TestClient(create_app(tmp_path))

    response = client.post(f"/api/assignments/{assignment.id}/retry", json={"reason": "retry exact row"})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["parent_assignment_id"] == assignment.id
    assert payload["assignment"]["parent_assignment_id"] == assignment.id
    assert payload["assignment"]["attempt"] == 2
    assert payload["assignment"]["status"] == "queued"


def test_assignment_retry_endpoint_reuses_existing_child_retry(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_blocked("runtime offline", FailureReason.RUNTIME_OFFLINE))
    client = TestClient(create_app(tmp_path))

    first = client.post(f"/api/assignments/{assignment.id}/retry", json={"reason": "retry exact row"})
    second = client.post(f"/api/assignments/{assignment.id}/retry", json={"reason": "retry exact row"})

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["assignment"]["id"] == second.json()["assignment"]["id"]
    children = [item for item in store.list_assignments() if item.parent_assignment_id == assignment.id]
    assert len(children) == 1


def test_assignment_retry_endpoint_rejects_unsafe_and_force_retry(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(
        assignment.mark_blocked("external execution disabled", FailureReason.EXTERNAL_EXECUTION_BLOCKED)
    )
    client = TestClient(create_app(tmp_path))

    unsafe = client.post(f"/api/assignments/{assignment.id}/retry", json={"reason": "retry unsafe"})
    forced = client.post(f"/api/assignments/{assignment.id}/retry", json={"force": True})

    assert unsafe.status_code == 409
    assert "not safe to retry" in unsafe.text
    assert forced.status_code == 409
    assert "Force retry is not allowed" in forced.text
    assert not [item for item in store.list_assignments() if item.parent_assignment_id == assignment.id]


def test_assignment_retry_endpoint_rejects_unsafe_parent_with_existing_child(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    parent = assignment.mark_blocked(
        "external execution disabled",
        FailureReason.EXTERNAL_EXECUTION_BLOCKED,
    )
    store.save_assignment(parent)
    legacy_child = create_retry_assignment(store, parent, reason="legacy forced child", force=True)
    assert legacy_child.parent_assignment_id == parent.id
    client = TestClient(create_app(tmp_path))

    unsafe = client.post(f"/api/assignments/{parent.id}/retry", json={"reason": "retry unsafe"})

    assert unsafe.status_code == 409
    assert "not safe to retry" in unsafe.text


def test_daemon_start_blocks_broad_claim_when_multiple_assignments_are_claimable(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    tickets = ingest_sources(store, SOURCE_FIXTURES[:2])
    agent = store.resolve_agent_profile("fake-codex")
    for ticket in tickets:
        assignment = store.create_assignment(ticket, agent)
        store.save_assignment(assignment.mark_ready_to_claim({"target_project_id": "test"}))
    client = TestClient(create_app(tmp_path))

    response = client.post("/api/daemon/start", json={"external_execution_authorized": True})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "broad_claim_blocked"
    assert "needs an assignment" in payload["message"]


def test_daemon_start_blocks_broad_claim_for_requeued_assignments(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    tickets = ingest_sources(store, SOURCE_FIXTURES[:2])
    agent = store.resolve_agent_profile("fake-codex")
    for ticket in tickets:
        assignment = store.create_assignment(ticket, agent)
        store.save_assignment(assignment.requeue("Stale heartbeat - orphan recovery"))
    client = TestClient(create_app(tmp_path))

    response = client.post("/api/daemon/start", json={"external_execution_authorized": True})

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "broad_claim_blocked"


def test_issue_detail_canonicalizes_duplicate_runnable_assignments(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    agent = store.resolve_agent_profile("fake-codex")
    first = store.create_assignment(ticket, agent)
    second = store.create_assignment(ticket, agent)
    store.save_assignment(first.mark_ready_to_claim({"target_project_id": "test"}))
    store.save_assignment(second.mark_ready_to_claim({"target_project_id": "test"}))

    detail = WorkbenchIssuesService(store).detail(ticket.key)
    assignments = store.list_assignments_for_ticket(ticket.id)
    runnable = [item for item in assignments if item.status.value == "ready_to_claim"]
    cancelled = [item for item in assignments if item.status.value == "cancelled"]

    assert len(runnable) == 1
    assert len(cancelled) == 1
    assert cancelled[0].metadata["superseded_by_assignment_id"] == runnable[0].id
    assert len([item for item in detail.issue.assignments if item.status == "ready_to_claim"]) == 1
