from __future__ import annotations

from pathlib import Path

import pytest

from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.dtos import AssignTicketInput, CreateProjectVersionInput
from ariadne_ltb.application.project_versions import ProjectVersionService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_assign_ticket_service_creates_assignment_with_registered_target(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = TargetProjectRegistry(store).register(
        ensure_demo_target_project(tmp_path),
        "Demo Target",
        target_project_id="local-default",
    )

    result = AssignTicketService(store).assign(
        "ARI-003",
        AssignTicketInput(
            assignee_id="build-team",
            assignee_kind="build_team",
            backend_name="codex",
            runtime_profile="production",
            target_project_id=target.id,
            idempotency_key="assign-service-1",
        ),
        source="http",
    )

    assignment = store.load_assignment(result.assignment.id)
    assert assignment.metadata["target_project_id"] == "local-default"
    assert assignment.metadata["target_repo_path"]
    assert assignment.agent_runtime == "llm"
    assert result.confirmation_token


def test_assign_ticket_service_stamps_current_version_assignment_scope(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = TargetProjectRegistry(store).register(
        ensure_demo_target_project(tmp_path),
        "Demo Target",
        target_project_id="local-default",
    )
    current_version = ProjectVersionService(store).create(
        CreateProjectVersionInput(
            target_project_id=target.id,
            version_label="v0.2",
            goal_title="Ship scoped assignment",
            goal_north_star="Current version issue can be assigned to one real agent.",
        )
    )

    result = AssignTicketService(store).assign(
        "ARI-003",
        AssignTicketInput(
            assignee_id="codex",
            assignee_kind="agent",
            backend_name="codex",
            runtime_profile="production",
            target_project_id=target.id,
            idempotency_key="assign-service-current-scope",
        ),
        source="http",
    )

    assignment = store.load_assignment(result.assignment.id)
    assert assignment.metadata["target_project_id"] == target.id
    assert assignment.metadata["project_version_id"] == current_version.id
    assert assignment.metadata["target_version_label"] == "v0.2"
    assert assignment.metadata["issue_ticket_id"] == assignment.ticket_id
    assert assignment.metadata["issue_ticket_key"] == "ARI-003"
    assert assignment.metadata["selected_agent_id"] == "codex"
    assert assignment.metadata["scope_mode"] == "assignment"
    assert assignment.metadata["runtime_backend_intent"] == {
        "backend_name": "codex",
        "planner_name": "llm",
        "agent_runtime": "llm",
        "backlog_planner_name": "llm",
    }


def test_assign_ticket_service_rejects_fallback_for_http(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    target = TargetProjectRegistry(store).register(ensure_demo_target_project(tmp_path), "Demo Target")

    with pytest.raises(Exception, match="not allowed for browser product actions"):
        AssignTicketService(store).assign(
            "ARI-003",
            AssignTicketInput(
                assignee_id="build-team",
                backend_name="fake-codex",
                runtime_profile="deterministic",
                target_project_id=target.id,
            ),
            source="http",
        )
