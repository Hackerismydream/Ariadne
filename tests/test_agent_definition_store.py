from __future__ import annotations

from fastapi.testclient import TestClient

from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.models import (
    AgentDefinition,
    AgentRun,
    AgentRunLifecycleState,
    AgentRunStatus,
    AgentRuntimeProfile,
    AgentVisibility,
    BuildTicket,
    RuntimeEvent,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


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
    activity = client.get(f"/api/team/agents/{agent.agent_id}/activity").json()["activity"]
    assert any(item["event_type"] == "started" for item in activity)
