from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    Artifact,
    BuildTicket,
    RunMessageType,
    RuntimeCapability,
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
        context.store.reset_run_messages(run.id)
        context.store.append_run_message(
            run.id,
            "start",
            RunMessageType.STATUS,
            f"{node.name} started for {context.ticket.key}.",
            metadata={"agent_role": node.role},
        )

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
            context.store.append_run_message(
                failed_run.id,
                "error",
                RunMessageType.ERROR,
                f"{node.name} failed: {exc}",
                metadata={"status": failed_run.status.value},
            )
            context.store.append_run_message(
                failed_run.id,
                "finish",
                RunMessageType.RESULT,
                f"{node.name} failed.",
                metadata={"status": failed_run.status.value},
            )
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
        for artifact in result.artifacts:
            context.store.append_run_message(
                finished_run.id,
                "artifact",
                RunMessageType.ARTIFACT,
                f"Created {artifact.artifact_type.value}: {artifact.summary}",
                artifact_ref=artifact.id,
                metadata={"path": artifact.path},
            )
        context.store.append_run_message(
            finished_run.id,
            "finish",
            RunMessageType.RESULT,
            result.output_summary,
            metadata={
                "status": finished_run.status.value,
                "artifact_ids": [artifact.id for artifact in result.artifacts],
            },
        )

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


def collect_runtime_capabilities() -> list[RuntimeCapability]:
    codex_path = shutil.which("codex")
    claude_path = shutil.which("claude")
    external_enabled = os.environ.get("ARIADNE_ENABLE_EXTERNAL_EXECUTION") == "1"
    return [
        RuntimeCapability(
            backend_name="fake-codex",
            command="internal",
            command_path=None,
            available=True,
            external_execution_enabled=False,
            command_template_set=False,
            confirm_execution_required=False,
            supports_external_execution=False,
            supports_dry_run=False,
        ),
        RuntimeCapability(
            backend_name="shell",
            command="shell",
            command_path=None,
            available=True,
            external_execution_enabled=external_enabled,
            command_template_set=False,
            confirm_execution_required=True,
            supports_external_execution=True,
            supports_dry_run=False,
        ),
        RuntimeCapability(
            backend_name="codex",
            command="codex",
            command_path=codex_path,
            available=codex_path is not None,
            external_execution_enabled=external_enabled,
            command_template_set=bool(os.environ.get("ARIADNE_CODEX_COMMAND_TEMPLATE")),
            confirm_execution_required=True,
            supports_external_execution=True,
            supports_dry_run=False,
        ),
        RuntimeCapability(
            backend_name="claude-code",
            command="claude",
            command_path=claude_path,
            available=claude_path is not None,
            external_execution_enabled=external_enabled,
            command_template_set=bool(os.environ.get("ARIADNE_CLAUDE_COMMAND_TEMPLATE")),
            confirm_execution_required=True,
            supports_external_execution=True,
            supports_dry_run=False,
        ),
        RuntimeCapability(
            backend_name="dry-run",
            command="internal",
            command_path=None,
            available=True,
            external_execution_enabled=False,
            command_template_set=False,
            confirm_execution_required=False,
            supports_external_execution=False,
            supports_dry_run=True,
        ),
    ]
