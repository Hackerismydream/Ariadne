from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.application.assign_ticket import AssignTicketService
from ariadne_ltb.application.dtos import AssignTicketInput
from ariadne_ltb.application.inbox_actions import InboxActionService
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.inbox import refresh_inbox
from ariadne_ltb.models import (
    AgentDefinition,
    AgentRun,
    AgentRunLifecycleState,
    AgentRunStatus,
    AgentRuntimeProfile,
    AgentVisibility,
    BuildTeam,
    BuildTicket,
    FailureReason,
    RuntimeEvent,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.team import route_ticket_to_build_team


def _ticket() -> BuildTicket:
    return BuildTicket(
        id="ticket-agent-1",
        key="AGT-001",
        title="Implement agent detail",
        description="Exercise the agent definition projections.",
        source_type="manual_goal",
        source_ref="test",
        status=TicketStatus.READY_FOR_EXECUTION,
    )


def _agent() -> AgentDefinition:
    return AgentDefinition(
        agent_id="agent-codex",
        name="Codex Implementer",
        description="Real persisted local agent.",
        avatar_seed="codex",
        runtime_profile_id="agent-codex:runtime",
        runtime_profile=AgentRuntimeProfile(
            profile_id="agent-codex:runtime",
            agent_id="agent-codex",
            backend="codex",
            model="gpt-5-codex",
            working_directory="/tmp/project",
            environment_keys=["CODEX_HOME"],
            reasoning_level="high",
        ),
        visibility=AgentVisibility(agent_id="agent-codex", visible=True),
        instructions="Always cite evidence.",
        skill_ids=["ariadne-review-diff"],
    )


def test_team_agents_starts_empty_without_profile_projection(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))

    response = client.get("/api/team/agents")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source"] == "agent_definition_store"
    assert payload["agents"] == []
    assert not (tmp_path / ".ariadne" / "agents" / "profiles.json").exists()


def test_create_agent_persists_definition_file_and_lists_it(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/api/team/agents",
        json={
            "name": "Mini Code Implementer",
            "description": "Builds target repo code.",
            "backend": "codex",
            "model": "gpt-5-codex",
            "instructions": "Only edit allowed paths.",
            "skill_ids": ["codex-handoff"],
            "environment_keys": ["CODEX_HOME"],
        },
    )

    assert response.status_code == 200, response.text
    agent = response.json()["agent"]
    agent_path = tmp_path / ".ariadne" / "agents" / f"{agent['id']}.json"
    assert agent_path.exists()
    assert agent_path.name != "profiles.json"

    listed = client.get("/api/team/agents").json()["agents"]
    assert [item["id"] for item in listed] == [agent["id"]]
    assert listed[0]["backend_name"] == "codex"
    assert listed[0]["instructions_present"] is True


def test_agent_detail_fact_tabs_project_existing_store(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    agent = _agent()
    store.save_agent_definition(agent)
    ticket = _ticket()
    store.save_ticket(ticket)
    assignment = store.create_assignment(ticket, agent.to_agent_profile(), backend_name="codex")
    run = AgentRun(
        id="run-agent-1",
        ticket_id=ticket.id,
        agent_name=agent.name,
        agent_role=agent.role,
        status=AgentRunStatus.SUCCEEDED,
        lifecycle_state=AgentRunLifecycleState.TERMINAL,
        input_summary="Run the task.",
        output_summary="Done.",
        backend_name="codex",
        metadata={"assignment_id": assignment.id, "agent_id": agent.agent_id},
    )
    store.save_run(run)
    ticket = ticket.model_copy(update={"agent_run_ids": [run.id]})
    store.save_ticket(ticket)
    store.append_runtime_event(
        RuntimeEvent(
            id=stable_id("event", assignment.id, "started"),
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            assignment_id=assignment.id,
            run_id=run.id,
            runtime_id="local:codex",
            stage="execution",
            event_type="started",
            actor=agent.name,
            idempotency_key="agent-detail-started",
        )
    )
    client = TestClient(create_app(tmp_path))

    assert client.get(f"/api/team/agents/{agent.agent_id}").json()["agent"]["instructions"] == "Always cite evidence."
    assert client.get(f"/api/team/agents/{agent.agent_id}/instructions").json()["instructions"] == "Always cite evidence."
    assert client.get(f"/api/team/agents/{agent.agent_id}/environment").json()["environment_keys"] == ["CODEX_HOME"]
    assert client.get(f"/api/team/agents/{agent.agent_id}/tasks").json()["tasks"][0]["assignment"]["id"] == assignment.id
    assert client.get(f"/api/team/agents/{agent.agent_id}/runs").json()["runs"][0]["id"] == run.id
    runtime_event_id = stable_id("event", assignment.id, "started")
    activity = client.get(f"/api/team/agents/{agent.agent_id}/activity").json()["activity"]
    assert any(item["event_type"] == "started" for item in activity)
    issue_timeline = client.get(f"/api/issues/{ticket.key}").json()["issue"]["timeline"]
    assert any(item["id"] == runtime_event_id for item in activity)
    assert any(item["id"] == f"assignment-event:{runtime_event_id}" for item in issue_timeline)
    assert any(item["ref_id"] == assignment.id for item in issue_timeline)


def test_agent_tasks_project_assignment_lifecycle_and_blocker_inbox(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    agent = _agent()
    store.save_agent_definition(agent)
    ticket = _ticket()
    store.save_ticket(ticket)
    assignment = store.create_assignment(ticket, agent.to_agent_profile(), backend_name="codex")
    client = TestClient(create_app(tmp_path))

    queued_task = client.get(f"/api/team/agents/{agent.agent_id}/tasks").json()["tasks"][0]
    assert queued_task["task_id"] == assignment.id
    assert queued_task["ticket_key"] == ticket.key
    assert queued_task["agent_id"] == agent.agent_id
    assert queued_task["status"] == "queued"
    assert queued_task["attempt_number"] == 1
    assert queued_task["retry_count"] == 0
    assert queued_task["current"] is False
    assert queued_task["blocker_id"] is None

    blocked = assignment.mark_blocked("external execution disabled", FailureReason.EXTERNAL_EXECUTION_BLOCKED)
    store.save_assignment(blocked)

    blocked_task = client.get(f"/api/team/agents/{agent.agent_id}/tasks").json()["tasks"][0]
    assert blocked_task["status"] == "blocked"
    assert blocked_task["blocker_reason"] == "external execution disabled"
    assert blocked_task["blocker_id"]


def test_agent_skill_instruction_env_bindings_flow_into_route_and_handoff(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    agent = _agent()
    store.save_agent_definition(agent)
    ticket = _ticket()
    store.save_ticket(ticket)
    target = tmp_path / "target"
    target.mkdir()
    project = TargetProjectRegistry(store).register(target, "Target")

    assigned = AssignTicketService(store).assign(
        ticket.key,
        AssignTicketInput(
            assignee_id=agent.agent_id,
            assignee_kind="agent",
            backend_name="codex",
            runtime_profile="production",
            target_project_id=project.id,
            idempotency_key="agent-binding-route",
        ),
        source="test",
    )

    assignment = store.load_assignment(assigned.assignment.id)
    route = store.load_route_decision(str(assignment.metadata["route_decision_id"]))
    handoff = store.load_handoff_packet(str(assignment.metadata["handoff_packet_id"]))
    markdown = Path(handoff.markdown_path).read_text(encoding="utf-8")
    assert route.agent_id == agent.agent_id
    assert route.agent_reason == "Direct assignment selected real AgentDefinition `Codex Implementer`."
    assert route.runtime_profile_id == agent.runtime_profile_id
    assert route.selected_skills == ["ariadne-review-diff"]
    assert route.selected_agent_id == agent.agent_id
    assert route.skill_refs == ["ariadne-review-diff"]
    assert "## Selected Skills" in markdown
    assert "`ariadne-review-diff`" in markdown
    assert "- Agent id: `agent-codex`" in markdown
    assert "- Runtime profile: `agent-codex:runtime`" in markdown
    assert "- Agent reason: Direct assignment selected real AgentDefinition `Codex Implementer`." in markdown
    assert "## Agent Instructions" in markdown
    assert "Always cite evidence." in markdown
    assert "## Environment Keys" in markdown
    assert "`CODEX_HOME`" in markdown


def test_build_team_route_uses_real_agent_definition_fields(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    agent = _agent()
    store.save_agent_definition(agent)
    ticket = _ticket()
    store.save_ticket(ticket)
    target = tmp_path / "target"
    target.mkdir()
    team = BuildTeam(
        id="team-real-agent",
        name="Real Agent Team",
        lead_agent_id=agent.agent_id,
        implementer_agent_id=agent.agent_id,
        reviewer_agent_id=agent.agent_id,
        memory_agent_id=agent.agent_id,
        default_backend_name="codex",
        skill_refs=["fallback-skill"],
    )

    routed = route_ticket_to_build_team(
        store,
        ticket,
        team,
        backend_name="codex",
        target_repo_path=str(target),
        target_project_id="target-project",
    )

    route = routed.route_decision
    assert route.agent_id == agent.agent_id
    assert route.selected_agent_id == agent.agent_id
    assert route.agent_reason == "Build team `Real Agent Team` selected real AgentDefinition `Codex Implementer` for AGT-001."
    assert route.runtime_profile_id == agent.runtime_profile_id
    assert route.selected_skills == ["ariadne-review-diff"]
    assert route.skill_refs == ["fallback-skill"]
    assert routed.assignment.agent_id == agent.agent_id


def test_inbox_repair_creates_repair_assignment_for_same_agent(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    agent = _agent()
    store.save_agent_definition(agent)
    ticket = _ticket()
    store.save_ticket(ticket)
    target = tmp_path / "target"
    target.mkdir()
    project = TargetProjectRegistry(store).register(target, "Target")
    assigned = AssignTicketService(store).assign(
        ticket.key,
        AssignTicketInput(
            assignee_id=agent.agent_id,
            assignee_kind="agent",
            backend_name="codex",
            runtime_profile="production",
            target_project_id=project.id,
            idempotency_key="phase7-source-assignment",
        ),
        source="test",
    )
    source_assignment = store.load_assignment(assigned.assignment.id)
    store.save_assignment(
        source_assignment.mark_blocked(
            "agent could not repair generated code",
            FailureReason.AGENT_ERROR,
        )
    )
    item = next(item for item in refresh_inbox(store) if item.source_id == source_assignment.id)

    result = InboxActionService(store).create_repair_ticket(item.id)

    assert result.ticket is not None
    assert result.assignment is not None
    assert result.assignment.agent_id == agent.agent_id
    assert result.assignment.parent_assignment_id == source_assignment.id
    assert result.assignment.metadata["source_inbox_item_id"] == item.id
    repair_actions = store.list_repair_actions()
    assert repair_actions[0].source_inbox_item_id == item.id
    assert repair_actions[0].target_agent_id == agent.agent_id
    assert repair_actions[0].new_assignment_id == result.assignment.id
    tasks = TestClient(create_app(tmp_path)).get(f"/api/team/agents/{agent.agent_id}/tasks").json()["tasks"]
    repair_task = next(task for task in tasks if task["task_id"] == result.assignment.id)
    assert repair_task["ticket_key"] == result.ticket.key
    assert repair_task["agent_id"] == agent.agent_id
    assert repair_task["status"] == "queued"
