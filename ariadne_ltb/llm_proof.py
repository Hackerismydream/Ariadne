from __future__ import annotations

import json
import os

from pydantic import Field

from ariadne_ltb.llm import DeepSeekClient, LLMUsage, load_local_env, redact_secrets
from ariadne_ltb.llm_agents import LLMAgentResult, LLMAgentRole, run_ticket_llm_agent
from ariadne_ltb.llm_backlog import generate_llm_backlog_artifact
from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    AriadneModel,
    Artifact,
    ArtifactType,
    BuildPacket,
    BuildTicket,
    ExecutionResult,
    FailureReason,
    ReviewReport,
    RunMessageType,
    stable_id,
    utc_now,
)
from ariadne_ltb.planner import LLMPlanner, PlannerResult
from ariadne_ltb.review import review_execution_with_llm
from ariadne_ltb.storage import AriadneStore


class LLMProofOperation(AriadneModel):
    name: str
    succeeded: bool = False
    provider: str = "deepseek"
    model: str | None = None
    run_id: str | None = None
    artifact_id: str | None = None
    artifact_path: str | None = None
    report_id: str | None = None
    usage: LLMUsage = Field(default_factory=LLMUsage)
    error: str | None = None


class LLMProofResult(AriadneModel):
    ticket_id: str
    ticket_key: str
    succeeded: bool
    provider: str = "deepseek"
    operations: dict[str, LLMProofOperation]
    proof_run_id: str
    proof_artifact_id: str | None = None
    proof_artifact_path: str | None = None
    error: str | None = None
    created_at: str = utc_now()


def run_llm_proof_sequence(
    store: AriadneStore,
    ticket_id_or_key: str,
    *,
    client: DeepSeekClient | None = None,
) -> LLMProofResult:
    """Run the auditable DeepSeek proof sequence for one already-executed ticket."""
    load_local_env(store.root)
    ticket = store.resolve_ticket(ticket_id_or_key)
    run = _start_proof_run(store, ticket)
    if not os.environ.get("DEEPSEEK_API_KEY") and client is None:
        return _finish_blocked_proof(
            store,
            ticket,
            run,
            "DEEPSEEK_API_KEY is required for `ari llm proof`.",
        )

    execution = _latest_execution_for_ticket(store, ticket)
    if execution is None:
        return _finish_blocked_proof(
            store,
            ticket,
            run,
            "A ticket execution result is required before `ari llm proof` can prove reviewer and backlog agents.",
        )

    operations: dict[str, LLMProofOperation] = {}
    for role in (LLMAgentRole.BUILD_LEAD, LLMAgentRole.KNOWLEDGE, LLMAgentRole.MEMORY):
        result = run_ticket_llm_agent(store, store.load_ticket(ticket.id), role, client=client)
        operations[role.value] = _operation_from_role_result(role.value, result)

    planner = LLMPlanner(client=client).plan_ticket(store, store.load_ticket(ticket.id))
    operations["planner"] = _operation_from_planner_result(planner)

    packet = _load_llm_packet(store, ticket, planner)
    if packet is None:
        artifact = _write_proof_artifact(store, ticket, run, operations, "LLM planner did not produce a Build Packet.")
        return _finish_proof_run(store, ticket, run, operations, artifact, "LLM planner did not produce a Build Packet.")

    review = review_execution_with_llm(store, store.load_ticket(ticket.id), packet, execution, client=client)
    store.save_review_report(review)
    operations["reviewer"] = _operation_from_review(review)

    fallback = _write_backlog_fallback(store, ticket, run)
    backlog = generate_llm_backlog_artifact(
        store,
        store.load_ticket(ticket.id),
        packet,
        execution,
        review,
        run.id,
        fallback.path,
        client=client,
    )
    operations["backlog"] = LLMProofOperation(
        name="backlog",
        succeeded=backlog.succeeded,
        artifact_id=backlog.artifact.id,
        artifact_path=backlog.artifact.path,
        error=backlog.error,
    )

    error = _proof_error(operations)
    artifact = _write_proof_artifact(store, ticket, run, operations, error)
    return _finish_proof_run(store, ticket, run, operations, artifact, error)


def _start_proof_run(store: AriadneStore, ticket: BuildTicket) -> AgentRun:
    agent_role = "llm:proof"
    attempt = 1 + sum(
        1 for run_id in ticket.agent_run_ids if store.load_run(run_id).agent_role == agent_role
    )
    run = AgentRun(
        id=stable_id("run", ticket.id, agent_role, attempt),
        ticket_id=ticket.id,
        agent_name="LLM Proof Runner",
        agent_role=agent_role,
        input_summary=f"Run DeepSeek proof sequence for {ticket.key}.",
        attempt=attempt,
        backend_name="deepseek",
        metadata={"provider": "deepseek", "llm_proof": True},
    ).mark_running()
    store.save_run(run)
    store.reset_run_messages(run.id)
    store.append_run_message(
        run.id,
        "start",
        RunMessageType.STATUS,
        f"DeepSeek proof sequence started for {ticket.key}.",
        metadata={"ticket_key": ticket.key},
    )
    store.save_ticket(
        ticket.with_run(run.id).append_event(
            "llm_proof_started",
            "LLM Proof Runner",
            "DeepSeek proof sequence started.",
            payload_ref=run.id,
        )
    )
    return run


def _finish_blocked_proof(
    store: AriadneStore,
    ticket: BuildTicket,
    run: AgentRun,
    reason: str,
) -> LLMProofResult:
    safe_reason = redact_secrets(reason)
    artifact = _write_proof_artifact(store, ticket, run, {}, safe_reason)
    return _finish_proof_run(store, ticket, run, {}, artifact, safe_reason)


def _finish_proof_run(
    store: AriadneStore,
    ticket: BuildTicket,
    run: AgentRun,
    operations: dict[str, LLMProofOperation],
    artifact: Artifact,
    error: str | None,
) -> LLMProofResult:
    succeeded = error is None and all(operation.succeeded for operation in operations.values())
    status = AgentRunStatus.SUCCEEDED if succeeded else AgentRunStatus.BLOCKED
    summary = "DeepSeek proof sequence completed." if succeeded else f"DeepSeek proof sequence blocked: {error}"
    finished = run.model_copy(
        deep=True,
        update={
            "artifact_ids": [artifact.id],
            "metadata": run.metadata
            | {
                "succeeded": succeeded,
                "operation_statuses": {
                    name: operation.succeeded for name, operation in operations.items()
                },
            },
        },
    ).mark_finished(
        status,
        summary,
        error=error,
        failure_reason=None if succeeded else FailureReason.AGENT_ERROR,
    )
    store.save_run(finished)
    store.append_run_message(
        finished.id,
        "finish",
        RunMessageType.STATUS if succeeded else RunMessageType.ERROR,
        summary,
        artifact_ref=artifact.id,
        metadata={"succeeded": succeeded},
    )
    store.save_ticket(
        store.load_ticket(ticket.id)
        .with_run(finished.id)
        .with_artifacts([artifact])
        .append_event(
            "llm_proof_finished",
            "LLM Proof Runner",
            summary,
            payload_ref=artifact.id,
        )
    )
    return LLMProofResult(
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        succeeded=succeeded,
        operations=operations,
        proof_run_id=finished.id,
        proof_artifact_id=artifact.id,
        proof_artifact_path=artifact.path,
        error=error,
    )


def _write_proof_artifact(
    store: AriadneStore,
    ticket: BuildTicket,
    run: AgentRun,
    operations: dict[str, LLMProofOperation],
    error: str | None,
) -> Artifact:
    content = {
        "ticket_id": ticket.id,
        "ticket_key": ticket.key,
        "provider": "deepseek",
        "created_at": utc_now(),
        "succeeded": error is None and all(operation.succeeded for operation in operations.values()),
        "error": redact_secrets(error) if error else None,
        "operations": {
            name: operation.model_dump(mode="json", exclude_none=False)
            for name, operation in operations.items()
        },
    }
    return store.write_artifact(
        ticket.id,
        run.id,
        ArtifactType.LLM_AGENT_RESULT,
        "llm_proof.json",
        json.dumps(content, indent=2, sort_keys=True) + "\n",
        "DeepSeek LLM proof sequence result",
        metadata={
            "provider": "deepseek",
            "llm_proof": True,
            "succeeded": content["succeeded"],
            "operation_statuses": {
                name: operation.succeeded for name, operation in operations.items()
            },
        },
    )


def _operation_from_role_result(name: str, result: LLMAgentResult) -> LLMProofOperation:
    return LLMProofOperation(
        name=name,
        succeeded=result.succeeded,
        provider=result.provider,
        model=result.model,
        run_id=result.run_id,
        artifact_id=result.artifact_id,
        artifact_path=result.artifact_path,
        usage=result.usage,
        error=result.error,
    )


def _operation_from_planner_result(result: PlannerResult) -> LLMProofOperation:
    return LLMProofOperation(
        name="planner",
        succeeded=result.succeeded,
        artifact_id=result.build_packet_artifact_id or result.error_artifact_id,
        artifact_path=result.build_packet_artifact_path or result.error_artifact_path,
        error=result.error,
    )


def _operation_from_review(review: ReviewReport) -> LLMProofOperation:
    succeeded = review.reviewer_mode == "llm"
    return LLMProofOperation(
        name="reviewer",
        succeeded=succeeded,
        report_id=review.id,
        error=None if succeeded else "; ".join(review.required_fixes),
    )


def _load_llm_packet(
    store: AriadneStore,
    ticket: BuildTicket,
    planner: PlannerResult,
) -> BuildPacket | None:
    if planner.build_packet_id:
        return store.load_build_packet(planner.build_packet_id)
    latest = store.load_ticket(ticket.id)
    if latest.build_packet_id:
        packet = store.load_build_packet(latest.build_packet_id)
        if packet.metadata.get("planner_mode") == "llm":
            return packet
    return None


def _latest_execution_for_ticket(
    store: AriadneStore,
    ticket: BuildTicket,
) -> ExecutionResult | None:
    executions = [execution for execution in store.list_execution_results() if execution.ticket_id == ticket.id]
    if not executions:
        return None
    return sorted(executions, key=lambda execution: execution.ended_at)[-1]


def _write_backlog_fallback(store: AriadneStore, ticket: BuildTicket, run: AgentRun) -> Artifact:
    return store.write_artifact(
        ticket.id,
        run.id,
        ArtifactType.NEXT_TICKETS,
        "llm_proof_fallback_next_tickets.json",
        json.dumps(
            {
                "source_ticket_id": ticket.id,
                "source_ticket_key": ticket.key,
                "generated_at": utc_now(),
                "planner": "llm_proof_fallback",
                "next_tickets": [],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        "Fallback next tickets path for LLM proof backlog planner.",
        metadata={"source": "llm_proof_fallback", "planner": "llm_proof_fallback"},
    )


def _proof_error(operations: dict[str, LLMProofOperation]) -> str | None:
    failed = [
        f"{name}: {operation.error or 'operation did not succeed'}"
        for name, operation in operations.items()
        if not operation.succeeded
    ]
    if not failed:
        return None
    return redact_secrets("; ".join(failed))
