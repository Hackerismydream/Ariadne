from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationError

from ariadne_ltb.llm import DeepSeekClient, LLMClientError, LLMUsage, load_local_env, redact_secrets
from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    AriadneModel,
    Artifact,
    ArtifactType,
    BuildTicket,
    FailureReason,
    RunMessageType,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


class LLMAgentRole(str, Enum):
    BUILD_LEAD = "build_lead"
    RESEARCH = "research"
    KNOWLEDGE = "knowledge"
    PROJECT_CONTEXT = "project_context"
    PLANNER = "planner"
    REVIEWER = "reviewer"
    MEMORY = "memory"
    FEISHU_PLANNER = "feishu_planner"
    GITHUB_PLANNER = "github_planner"


class LLMAgentResult(AriadneModel):
    role: LLMAgentRole
    schema_name: str
    succeeded: bool
    output_json: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    provider: str = "deepseek"
    model: str | None = None
    usage: LLMUsage = Field(default_factory=LLMUsage)
    run_id: str | None = None
    artifact_id: str | None = None
    artifact_path: str | None = None


class LLMAgentPayload(AriadneModel):
    summary: str
    decision: str
    evidence: list[str] = Field(default_factory=list, max_length=8)
    risks: list[str] = Field(default_factory=list, max_length=8)
    recommended_actions: list[str] = Field(default_factory=list, max_length=8)


class JSONLLMAgent:
    def __init__(
        self,
        role: LLMAgentRole,
        client: DeepSeekClient | None = None,
        root: str | Path = ".",
    ) -> None:
        self.role = role
        self.client = client
        self.root = Path(root)

    def run(self, prompt: str, schema_name: str) -> LLMAgentResult:
        load_local_env(self.root)
        client = self.client or DeepSeekClient()
        try:
            response = client.complete_json_response(prompt, schema_name)
        except LLMClientError as exc:
            return LLMAgentResult(
                role=self.role,
                schema_name=schema_name,
                succeeded=False,
                error=redact_secrets(exc.error.message),
            )
        return LLMAgentResult(
            role=self.role,
            schema_name=schema_name,
            succeeded=True,
            output_json=response.content_json,
            model=response.model,
            usage=response.usage,
        )


def run_ticket_llm_agent(
    store: AriadneStore,
    ticket: BuildTicket,
    role: LLMAgentRole,
    client: DeepSeekClient | None = None,
) -> LLMAgentResult:
    """Run one real upstream LLM role against a ticket and persist run evidence."""
    schema_name = f"ariadne_{role.value}_agent_result"
    run = _start_llm_run(store, ticket, role)
    try:
        prompt = _role_prompt(store, ticket, role)
        result = JSONLLMAgent(role, client=client, root=store.root).run(prompt, schema_name)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        result = LLMAgentResult(
            role=role,
            schema_name=schema_name,
            succeeded=False,
            error=redact_secrets(
                f"LLM role agent failed before completion: {exc}",
                extra_secrets=[getattr(client, "api_key", None)],
            ),
        )
        artifact = _write_llm_agent_artifact(store, run, role, result)
        _finish_llm_run(store, ticket, run, role, result, artifact)
        return result.model_copy(
            update={
                "run_id": run.id,
                "artifact_id": artifact.id,
                "artifact_path": artifact.path,
            }
        )

    if result.succeeded:
        try:
            payload = LLMAgentPayload.model_validate(result.output_json)
        except ValidationError as exc:
            result = LLMAgentResult(
                role=role,
                schema_name=schema_name,
                succeeded=False,
                error=redact_secrets(f"LLM role output failed schema validation: {exc}"),
                model=result.model,
                usage=result.usage,
            )
            artifact = _write_llm_agent_artifact(store, run, role, result)
            _finish_llm_run(store, ticket, run, role, result, artifact)
            return result.model_copy(
                update={
                    "run_id": run.id,
                    "artifact_id": artifact.id,
                    "artifact_path": artifact.path,
                }
            )
        result = result.model_copy(update={"output_json": payload.model_dump(mode="json")})

    artifact = _write_llm_agent_artifact(store, run, role, result)
    _finish_llm_run(store, ticket, run, role, result, artifact)
    return result.model_copy(
        update={
            "run_id": run.id,
            "artifact_id": artifact.id,
            "artifact_path": artifact.path,
        }
    )


def _start_llm_run(store: AriadneStore, ticket: BuildTicket, role: LLMAgentRole) -> AgentRun:
    agent_role = f"llm:{role.value}"
    attempt = 1 + sum(
        1
        for run_id in ticket.agent_run_ids
        if store.load_run(run_id).agent_role == agent_role
    )
    run = AgentRun(
        id=stable_id("run", ticket.id, agent_role, attempt),
        ticket_id=ticket.id,
        agent_name=f"LLM {role.value.replace('_', ' ').title()}",
        agent_role=agent_role,
        input_summary=f"Run {role.value} upstream LLM agent for {ticket.key}.",
        attempt=attempt,
        backend_name="deepseek",
        metadata={"llm_role": role.value, "provider": "deepseek"},
    ).mark_running()
    store.save_run(run)
    store.reset_run_messages(run.id)
    store.append_run_message(
        run.id,
        "start",
        RunMessageType.STATUS,
        f"DeepSeek LLM role `{role.value}` started for {ticket.key}.",
        metadata={"role": role.value, "attempt": attempt},
    )
    updated = ticket.with_run(run.id).append_event(
        "llm_agent_started",
        run.agent_name,
        f"DeepSeek LLM role `{role.value}` started.",
        payload_ref=run.id,
    )
    store.save_ticket(updated)
    return run


def _write_llm_agent_artifact(
    store: AriadneStore,
    run: AgentRun,
    role: LLMAgentRole,
    result: LLMAgentResult,
) -> Artifact:
    artifact = store.write_artifact(
        run.ticket_id,
        run.id,
        ArtifactType.LLM_AGENT_RESULT,
        f"llm_{role.value}.json",
        result.model_dump_json(indent=2, exclude_none=False) + "\n",
        f"DeepSeek LLM {role.value} agent {'result' if result.succeeded else 'blocked result'}",
        metadata={
            "llm_role": role.value,
            "provider": result.provider,
            "model": result.model,
            "succeeded": result.succeeded,
            "schema_name": result.schema_name,
        },
    )
    store.append_run_message(
        run.id,
        "artifact",
        RunMessageType.ARTIFACT,
        f"Wrote LLM role artifact for `{role.value}`.",
        artifact_ref=artifact.id,
        metadata={"path": artifact.path, "succeeded": result.succeeded},
    )
    return artifact


def _finish_llm_run(
    store: AriadneStore,
    ticket: BuildTicket,
    run: AgentRun,
    role: LLMAgentRole,
    result: LLMAgentResult,
    artifact: Artifact,
) -> AgentRun:
    status = AgentRunStatus.SUCCEEDED if result.succeeded else AgentRunStatus.BLOCKED
    summary = (
        f"DeepSeek LLM role `{role.value}` completed."
        if result.succeeded
        else f"DeepSeek LLM role `{role.value}` blocked: {result.error}"
    )
    finished = run.model_copy(
        deep=True,
        update={
            "artifact_ids": [artifact.id],
            "metadata": run.metadata
            | {
                "llm_role": role.value,
                "provider": result.provider,
                "model": result.model,
                "usage": result.usage.model_dump(mode="json"),
                "succeeded": result.succeeded,
            },
        },
    ).mark_finished(
        status,
        summary,
        error=result.error,
        failure_reason=None if result.succeeded else FailureReason.AGENT_ERROR,
    )
    store.save_run(finished)
    store.append_run_message(
        finished.id,
        "finish",
        RunMessageType.RESULT if result.succeeded else RunMessageType.ERROR,
        summary,
        artifact_ref=artifact.id,
        metadata={"status": status.value, "role": role.value},
    )
    updated_ticket = (
        store.load_ticket(ticket.id)
        .with_run(finished.id)
        .with_artifacts([artifact])
        .append_event(
            "llm_agent_finished",
            finished.agent_name,
            summary,
            payload_ref=artifact.id,
        )
    )
    store.save_ticket(updated_ticket)
    return finished


def _role_prompt(store: AriadneStore, ticket: BuildTicket, role: LLMAgentRole) -> str:
    packet_summary = "missing"
    if ticket.build_packet_id:
        try:
            packet = store.load_build_packet(ticket.build_packet_id)
            packet_summary = packet.model_dump_json(indent=2)
        except FileNotFoundError:
            packet_summary = "ticket references missing Build Packet"
    memory_summary = "\n".join(
        (
            f"- {record.title} ({record.ticket_id}): "
            f"{record.review_summary} / {record.build_summary}"
        )
        for record in store.list_memory_records()[-5:]
    ) or "- no local memory records"
    return f"""Return JSON only with this exact shape:
{{
  "summary": "short role-specific summary",
  "decision": "recommended next decision",
  "evidence": ["2-5 evidence bullets"],
  "risks": ["0-5 risks"],
  "recommended_actions": ["1-5 concrete actions"]
}}

You are the Ariadne `{role.value}` upstream LLM agent.

Ticket:
- key: {ticket.key}
- title: {ticket.title}
- status: {ticket.status.value}
- source_type: {ticket.source_type}
- source_ref: {ticket.source_ref}

Build Packet:
{packet_summary}

Recent memory:
{memory_summary}

Product posture:
- Ticket is the runtime center.
- Goal is optional input context, not the center object.
- Real Codex, Claude Code, DeepSeek, Feishu, and GitHub are production paths
  when safety gates and confirmations are present.
- fake-codex and dry-run are deterministic test or safety fallback paths only.

Role instructions:
{_role_instruction(role)}
"""


def _role_instruction(role: LLMAgentRole) -> str:
    instructions = {
        LLMAgentRole.BUILD_LEAD: (
            "Route the ticket, identify the next responsible agent/backend, and call out any "
            "approval gates before execution."
        ),
        LLMAgentRole.RESEARCH: "Extract research lessons that should change or create tickets.",
        LLMAgentRole.KNOWLEDGE: "Ground the ticket in prior memory, roadmap, and local architecture decisions.",
        LLMAgentRole.PROJECT_CONTEXT: "Summarize codebase or project-context implications for this ticket.",
        LLMAgentRole.PLANNER: "Recommend build tasks and acceptance criteria; do not replace the BuildPacket schema.",
        LLMAgentRole.REVIEWER: "Review evidence conservatively and call out missing checks.",
        LLMAgentRole.MEMORY: "Decide what should be written to memory and what future planning should retrieve.",
        LLMAgentRole.FEISHU_PLANNER: "Plan external Feishu write-back content without claiming a write occurred.",
        LLMAgentRole.GITHUB_PLANNER: "Plan GitHub issue, PR, branch, status, or comment sync actions.",
    }
    return instructions[role]
