from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    Artifact,
    BuildTicket,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


@dataclass
class RuntimeContext:
    store: AriadneStore
    ticket: BuildTicket
    source_text: str
    source_path: Path | None = None
    values: dict = field(default_factory=dict)
    current_run_id: str | None = None


@dataclass
class AgentStepResult:
    output_summary: str
    artifacts: list[Artifact] = field(default_factory=list)
    ticket_status: TicketStatus | None = None
    metadata: dict | None = None


class AgentNode(Protocol):
    name: str
    role: str

    def run(self, context: RuntimeContext, run: AgentRun) -> AgentStepResult:
        ...


class PipelineEngine:
    def __init__(self, nodes: list[AgentNode]) -> None:
        self.nodes = nodes

    def run(self, context: RuntimeContext) -> BuildTicket:
        for node in self.nodes:
            context.ticket = self._run_node(context, node)
        context.ticket = context.ticket.append_event(
            "pipeline_finished",
            "Local Runner",
            "Deterministic local pipeline finished.",
        )
        context.store.save_ticket(context.ticket)
        return context.ticket

    def _run_node(self, context: RuntimeContext, node: AgentNode) -> BuildTicket:
        run = AgentRun(
            id=stable_id("run", context.ticket.id, node.role),
            ticket_id=context.ticket.id,
            agent_name=node.name,
            agent_role=node.role,
            input_summary=f"Run {node.name} against {context.ticket.key}.",
        ).mark_running()
        context.current_run_id = run.id
        context.store.save_run(run)

        ticket = context.ticket.with_run(run.id).append_event(
            "agent_run_started",
            node.name,
            f"{node.name} started.",
            payload_ref=run.id,
        )
        context.store.save_ticket(ticket)
        context.ticket = ticket

        try:
            result = node.run(context, run)
        except Exception as exc:  # pragma: no cover - exercised only on unexpected failures
            failed_run = run.mark_finished(
                AgentRunStatus.FAILED,
                output_summary=f"{node.name} failed.",
                error=str(exc),
            )
            context.store.save_run(failed_run)
            failed_ticket = context.ticket.with_status(
                TicketStatus.FAILED,
                node.name,
                f"{node.name} failed: {exc}",
            ).append_event(
                "agent_run_finished",
                node.name,
                f"{node.name} failed.",
                payload_ref=failed_run.id,
            )
            context.store.save_ticket(failed_ticket)
            raise

        finished_run = run.model_copy(
            deep=True,
            update={"artifact_ids": [artifact.id for artifact in result.artifacts]},
        ).mark_finished(AgentRunStatus.SUCCEEDED, result.output_summary)
        context.store.save_run(finished_run)

        ticket = context.ticket.with_artifacts(result.artifacts).append_event(
            "agent_run_finished",
            node.name,
            result.output_summary,
            payload_ref=finished_run.id,
        )
        for artifact in result.artifacts:
            ticket = ticket.append_event(
                "artifact_created",
                node.name,
                f"Created {artifact.artifact_type.value}: {artifact.summary}",
                payload_ref=artifact.id,
            )
        if result.ticket_status is not None and ticket.status is not result.ticket_status:
            ticket = ticket.with_status(result.ticket_status, node.name)
        if result.metadata:
            merged = ticket.metadata | result.metadata
            ticket = ticket.model_copy(deep=True, update={"metadata": merged})
        context.store.save_ticket(ticket)
        return ticket
