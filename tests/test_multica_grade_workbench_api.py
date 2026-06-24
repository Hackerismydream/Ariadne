from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.application.dtos import CreateProjectGoalInput
from ariadne_ltb.application.project_goals import ProjectGoalService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.models import (
    BacklogOperation,
    BacklogOperationType,
    BacklogPreview,
    BacklogUpdateTrigger,
    BuildTicket,
    DaemonStatus,
    ExecutionResult,
    FailureReason,
    ReviewReport,
    ReviewVerdict,
    TicketStatus,
    WorkerHeartbeat,
    utc_now,
)
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def _prepared_store(tmp_path: Path) -> tuple[AriadneStore, str]:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    project = TargetProjectRegistry(store).register(ensure_demo_target_project(tmp_path), "Demo Target")
    ProjectGoalService(store).create(
        CreateProjectGoalInput(
            title="Demo current version",
            north_star="Deliver one scoped current version issue.",
            target_project_id=project.id,
        )
    )
    current = store.resolve_ticket("ARI-003")
    store.save_ticket(
        current.model_copy(
            deep=True,
            update={"metadata": current.metadata | {"target_project_id": project.id}},
        )
    )
    outside = store.resolve_ticket("ARI-001")
    store.save_ticket(
        outside.model_copy(
            deep=True,
            update={"metadata": outside.metadata | {"target_project_id": "outside-project"}},
        )
    )
    return store, project.id


def test_issues_endpoint_returns_current_version_mainline_tickets(tmp_path: Path) -> None:
    _prepared_store(tmp_path)
    client = TestClient(create_app(tmp_path))

    response = client.get("/api/issues")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["schema_version"] == "ariadne.issues.v1"
    keys = [item["key"] for item in payload["issues"]]
    assert keys == ["ARI-003"]
    assert payload["source"] == "build_ticket_projection"
    issue = payload["issues"][0]
    assert issue["id"]
    assert issue["target_version"] == "Demo current version"
    assert issue["source_count"] >= 1


def test_issues_endpoint_uses_latest_applied_issue_delta_as_current_version_boundary(tmp_path: Path) -> None:
    store, project_id = _prepared_store(tmp_path)
    old_ticket = BuildTicket(
        id="old-ticket",
        key="MCA-OLD",
        title="Old persisted issue",
        description="Historical issue from an earlier preview.",
        source_type="manual_goal",
        source_ref="old",
        status=TicketStatus.PLANNING,
        metadata={"target_project_id": project_id, "issue_class": "mainline", "root_ticket_key": "MCA-OLD"},
    )
    current_ticket = BuildTicket(
        id="current-ticket",
        key="MCA-NEW",
        title="Current version issue",
        description="Issue from the latest applied preview.",
        source_type="manual_goal",
        source_ref="new",
        status=TicketStatus.PLANNING,
        metadata={"target_project_id": project_id, "issue_class": "mainline", "root_ticket_key": "MCA-NEW"},
    )
    store.save_ticket(old_ticket)
    store.save_ticket(current_ticket)
    store.save_backlog_preview(
        BacklogPreview(
            id="preview-old",
            trigger_type=BacklogUpdateTrigger.MANUAL_GOAL,
            trigger_ref="goal",
            idempotency_key="preview-old",
            base_ticket_fingerprint="old",
            rationale="old preview",
            applied_at="2026-06-20T00:00:00Z",
            operations=[
                BacklogOperation(
                    id="op-old",
                    operation_type=BacklogOperationType.ADD_TICKET,
                    reason="old preview",
                    ticket_id=old_ticket.id,
                    ticket_key=old_ticket.key,
                    title=old_ticket.title,
                    metadata={"target_project_id": project_id, "included": True},
                )
            ],
        )
    )
    store.save_backlog_preview(
        BacklogPreview(
            id="preview-current",
            trigger_type=BacklogUpdateTrigger.MANUAL_GOAL,
            trigger_ref="goal",
            idempotency_key="preview-current",
            base_ticket_fingerprint="current",
            rationale="current preview",
            applied_at="2026-06-21T00:00:00Z",
            operations=[
                BacklogOperation(
                    id="op-current",
                    operation_type=BacklogOperationType.ADD_TICKET,
                    reason="current preview",
                    ticket_id=current_ticket.id,
                    ticket_key=current_ticket.key,
                    title=current_ticket.title,
                    metadata={"target_project_id": project_id, "included": True},
                )
            ],
        )
    )
    client = TestClient(create_app(tmp_path))

    response = client.get("/api/issues")

    assert response.status_code == 200, response.text
    keys = [item["key"] for item in response.json()["issues"]]
    assert keys == ["MCA-NEW"]


def test_workbench_endpoint_is_scoped_to_current_version_issue_set(tmp_path: Path) -> None:
    store, project_id = _prepared_store(tmp_path)
    current = store.resolve_ticket("ARI-003")
    historical = BuildTicket(
        id="historical-ticket",
        key="MCA-HIST",
        title="Historical issue",
        description="Old work that should stay stored but not pollute the Workbench.",
        source_type="manual_goal",
        source_ref="history",
        status=TicketStatus.PLANNING,
        metadata={"target_project_id": project_id, "issue_class": "mainline", "root_ticket_key": "MCA-HIST"},
    )
    store.save_ticket(historical)
    store.save_backlog_preview(
        BacklogPreview(
            id="preview-current-only",
            trigger_type=BacklogUpdateTrigger.MANUAL_GOAL,
            trigger_ref="goal",
            idempotency_key="preview-current-only",
            base_ticket_fingerprint="current-only",
            rationale="current preview",
            applied_at="2026-06-21T00:00:00Z",
            operations=[
                BacklogOperation(
                    id="op-current-only",
                    operation_type=BacklogOperationType.ADD_TICKET,
                    reason="current preview",
                    ticket_id=current.id,
                    ticket_key=current.key,
                    title=current.title,
                    metadata={"target_project_id": project_id, "included": True},
                )
            ],
        )
    )
    client = TestClient(create_app(tmp_path))

    response = client.get("/api/workbench")

    assert response.status_code == 200, response.text
    keys = [item["key"] for item in response.json()["tickets"]]
    assert keys == ["ARI-003"]


def test_issue_detail_timeline_and_comment_facade(tmp_path: Path) -> None:
    store, _project_id = _prepared_store(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    store.save_ticket(ticket.with_status(TicketStatus.PLANNING, "test", "planning started"))
    client = TestClient(create_app(tmp_path))

    comment = client.post(
        "/api/issues/ARI-003/comments",
        json={"body": "Human review note", "idempotency_key": "phase2-comment"},
    )
    detail = client.get("/api/issues/ARI-003")
    timeline = client.get("/api/issues/ARI-003/timeline")

    assert comment.status_code == 200, comment.text
    assert comment.json()["comment"]["body"] == "Human review note"
    assert detail.status_code == 200, detail.text
    issue = detail.json()["issue"]
    assert issue["key"] == "ARI-003"
    assert issue["body"]
    assert issue["comments"]
    assert any(event["event_type"] == "status_changed" for event in issue["timeline"])
    assert timeline.status_code == 200, timeline.text
    assert timeline.json()["ticket"]["key"] == "ARI-003"


def test_issue_patch_and_assignment_action_facades_reuse_existing_services(tmp_path: Path) -> None:
    store, project_id = _prepared_store(tmp_path)
    client = TestClient(create_app(tmp_path))

    patched = client.patch(
        "/api/issues/ARI-003",
        json={"priority": "high", "status": "planning", "title": "Scoped current issue"},
    )
    assigned = client.post(
        "/api/issues/ARI-003/assign",
        json={
            "assignee_id": "codex",
            "assignee_kind": "agent",
            "backend_name": "codex",
            "runtime_profile": "production",
            "target_project_id": project_id,
            "idempotency_key": "phase2-assign",
        },
    )

    assert patched.status_code == 200, patched.text
    assert patched.json()["issue"]["priority"] == "high"
    assert patched.json()["issue"]["title"] == "Scoped current issue"
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assignment"]["ticket_key"] == "ARI-003"
    assert store.resolve_ticket("ARI-003").metadata["latest_assignment_id"] == assigned.json()["assignment"]["id"]


def test_inbox_runtime_team_projects_and_snapshot_endpoints(tmp_path: Path) -> None:
    store, _project_id = _prepared_store(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("codex"))
    store.save_assignment(assignment.mark_blocked("external execution gate closed", FailureReason.EXTERNAL_EXECUTION_BLOCKED))
    client = TestClient(create_app(tmp_path))

    endpoints = {
        "/api/inbox": "ariadne.inbox.v1",
        "/api/runs/runtimes": "ariadne.runs-runtimes.v1",
        "/api/team/agents": "ariadne.team-agents.v1",
        "/api/team/build-teams": "ariadne.build-teams.v1",
        "/api/team/skills": "ariadne.team-skills.v1",
        "/api/projects": "ariadne.projects.v1",
        "/api/runs/assignments": "ariadne.runs-assignments.v1",
        "/api/agent-task-snapshot": "ariadne.agent-task-snapshot.v1",
    }

    payloads = {}
    for endpoint, schema_version in endpoints.items():
        response = client.get(endpoint)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["schema_version"] == schema_version
        payloads[endpoint] = payload

    assert payloads["/api/inbox"]["inbox"][0]["issue_key"] == "ARI-003"
    assert payloads["/api/inbox"]["inbox"][0]["failure_reason"] == "external_execution_blocked"
    assert payloads["/api/runs/runtimes"]["runtimes"]
    assert all(runtime["backend_name"] != "fake-codex" for runtime in payloads["/api/runs/runtimes"]["runtimes"])
    assert all(agent["id"] != "fake-codex" for agent in payloads["/api/team/agents"]["agents"])
    assert payloads["/api/projects"]["projects"][0]["id"]
    assert payloads["/api/runs/assignments"]["assignments"][0]["ticket_key"] == "ARI-003"
    assert payloads["/api/agent-task-snapshot"]["snapshot"]["blocked_count"] == 1


def test_stale_heartbeat_does_not_define_active_work(tmp_path: Path) -> None:
    store, _project_id = _prepared_store(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("codex"))
    blocked = assignment.mark_blocked("external execution gate closed", FailureReason.EXTERNAL_EXECUTION_BLOCKED)
    store.save_assignment(blocked)
    store.save_worker_heartbeat(
        WorkerHeartbeat(
            runtime_id="workbench-local",
            pid=999999,
            status=DaemonStatus.STOPPED,
            current_assignment_id=blocked.id,
            current_ticket_id=ticket.id,
            current_ticket_key=ticket.key,
            current_stage="stopped",
            started_at=utc_now(),
            heartbeat_at=utc_now(),
            last_error=blocked.blocker,
        )
    )
    client = TestClient(create_app(tmp_path))

    snapshot = client.get("/api/agent-task-snapshot")
    runtimes = client.get("/api/runs/runtimes")

    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json()["snapshot"]["active_assignment"] is None
    assert snapshot.json()["snapshot"]["current_issue_key"] is None
    assert snapshot.json()["snapshot"]["blocked_count"] == 1
    assert runtimes.status_code == 200, runtimes.text
    assert all(runtime["active_assignment"] is None for runtime in runtimes.json()["runtimes"])


def test_blocked_assignment_dominates_prior_success_in_issue_projection(tmp_path: Path) -> None:
    store, _project_id = _prepared_store(tmp_path)
    ticket = store.resolve_ticket("ARI-003")
    success_assignment = store.create_assignment(ticket, store.resolve_agent_profile("codex"), backend_name="codex")
    store.save_assignment(success_assignment.mark_done())
    execution = ExecutionResult(
        id="exec-prior-success",
        ticket_id=ticket.id,
        assignment_id=success_assignment.id,
        backend_name="codex",
        dry_run=False,
        blocked=False,
        command="codex exec",
        exit_code=0,
        test_command="python3.11 -m pytest",
        test_exit_code=0,
        changed_files=["src/cli.py"],
    )
    store.save_execution_result(execution)
    store.save_review_report(ReviewReport(id="review-prior-success", ticket_id=ticket.id, verdict=ReviewVerdict.PASS))
    blocked_assignment = store.create_assignment(ticket, store.resolve_agent_profile("codex"), backend_name="codex")
    store.save_assignment(
        blocked_assignment.mark_blocked("external execution gate closed", FailureReason.EXTERNAL_EXECUTION_BLOCKED)
    )
    client = TestClient(create_app(tmp_path))

    listing = client.get("/api/issues")
    detail = client.get("/api/issues/ARI-003")

    assert listing.status_code == 200, listing.text
    issue = listing.json()["issues"][0]
    assert issue["last_run_status"] == "blocked_before_execution"
    assert issue["terminal_verdict"] == "blocked_before_execution"
    assert issue["blocked_reason"] == "external execution gate closed"
    assert detail.status_code == 200, detail.text
    assert detail.json()["issue"]["terminal_verdict"] == "blocked_before_execution"


def test_project_detail_endpoint(tmp_path: Path) -> None:
    _store, project_id = _prepared_store(tmp_path)
    client = TestClient(create_app(tmp_path))

    response = client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["schema_version"] == "ariadne.project-detail.v1"
    assert payload["project"]["id"] == project_id


def test_issue_run_facades_report_missing_assignment(tmp_path: Path) -> None:
    _prepared_store(tmp_path)
    client = TestClient(create_app(tmp_path))

    rerun = client.post("/api/issues/ARI-003/rerun", json={"confirmation_token": "unused"})
    run_now = client.post("/api/issues/ARI-003/run-now", json={"confirmation_token": "unused"})

    assert rerun.status_code == 404
    assert run_now.status_code == 404
