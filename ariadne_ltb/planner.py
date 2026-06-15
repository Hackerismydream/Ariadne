from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from ariadne_ltb.ingest import (
    build_packet_from_source,
    source_document_from_path,
)
from ariadne_ltb.llm import DeepSeekClient
from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    ArtifactType,
    BuildDecision,
    BuildPacket,
    BuildTicket,
    Evidence,
    SourceDocument,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.planner_quality import score_build_packet
from ariadne_ltb.skills import handoff_skill_references
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class PlannerResult:
    succeeded: bool
    planner_name: str
    ticket_id: str
    build_packet_id: str | None = None
    build_packet_artifact_id: str | None = None
    build_packet_artifact_path: str = ""
    handoff_artifact_id: str | None = None
    handoff_artifact_path: str = ""
    error: str | None = None
    error_artifact_id: str | None = None
    error_artifact_path: str = ""


class PlannerBackend(Protocol):
    name: str

    def plan_ticket(self, store: AriadneStore, ticket: BuildTicket) -> PlannerResult:
        ...


class DeterministicPlanner:
    name = "deterministic"

    def plan_ticket(self, store: AriadneStore, ticket: BuildTicket) -> PlannerResult:
        source = _load_source(store, ticket)
        packet = build_packet_from_source(ticket, source)
        store.save_build_packet(packet)

        run = _start_planner_run(store, ticket, self.name)
        packet_artifact = _write_packet_artifact(store, run.id, packet)
        handoff_artifact = _write_handoff_artifact(store, run.id, ticket, packet)
        run = _finish_planner_run(
            store,
            run,
            AgentRunStatus.SUCCEEDED,
            "Deterministic planner wrote Build Packet and coding handoff.",
            [packet_artifact.id, handoff_artifact.id],
        )
        updated = (
            store.load_ticket(ticket.id)
            .with_run(run.id)
            .with_artifacts([packet_artifact, handoff_artifact])
            .with_status(TicketStatus.READY_FOR_EXECUTION, "Planner")
        )
        updated = updated.model_copy(
            deep=True,
            update={
                "build_packet_id": packet.id,
                "metadata": updated.metadata
                | {
                    "planner_name": self.name,
                    "handoff_artifact_id": handoff_artifact.id,
                    "build_packet_artifact_id": packet_artifact.id,
                },
            },
        )
        store.save_ticket(updated)
        return PlannerResult(
            succeeded=True,
            planner_name=self.name,
            ticket_id=ticket.id,
            build_packet_id=packet.id,
            build_packet_artifact_id=packet_artifact.id,
            build_packet_artifact_path=packet_artifact.path,
            handoff_artifact_id=handoff_artifact.id,
            handoff_artifact_path=handoff_artifact.path,
        )


class LLMPlanner:
    name = "llm"

    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self.client = client

    def plan_ticket(self, store: AriadneStore, ticket: BuildTicket) -> PlannerResult:
        if not os.environ.get("DEEPSEEK_API_KEY") and self.client is None:
            return self._blocked(store, ticket, "DEEPSEEK_API_KEY is required for --planner llm.")

        source = _load_source(store, ticket)
        client = self.client or DeepSeekClient()
        try:
            data = client.complete_json(_llm_prompt(ticket, source), "ariadne_build_packet")
            packet = _packet_from_llm_json(ticket, source, data)
        except (RuntimeError, json.JSONDecodeError, KeyError, TypeError, ValidationError, ValueError) as exc:
            return self._blocked(store, ticket, f"LLM planner failed: {exc}")

        store.save_build_packet(packet)
        run = _start_planner_run(store, ticket, self.name)
        packet_artifact = _write_packet_artifact(store, run.id, packet)
        handoff_artifact = _write_handoff_artifact(store, run.id, ticket, packet)
        run = _finish_planner_run(
            store,
            run,
            AgentRunStatus.SUCCEEDED,
            "LLM planner wrote Build Packet and coding handoff.",
            [packet_artifact.id, handoff_artifact.id],
        )
        updated = (
            store.load_ticket(ticket.id)
            .with_run(run.id)
            .with_artifacts([packet_artifact, handoff_artifact])
            .with_status(TicketStatus.READY_FOR_EXECUTION, "Planner")
        )
        updated = updated.model_copy(
            deep=True,
            update={
                "build_packet_id": packet.id,
                "metadata": updated.metadata
                | {
                    "planner_name": self.name,
                    "handoff_artifact_id": handoff_artifact.id,
                    "build_packet_artifact_id": packet_artifact.id,
                },
            },
        )
        store.save_ticket(updated)
        return PlannerResult(
            succeeded=True,
            planner_name=self.name,
            ticket_id=ticket.id,
            build_packet_id=packet.id,
            build_packet_artifact_id=packet_artifact.id,
            build_packet_artifact_path=packet_artifact.path,
            handoff_artifact_id=handoff_artifact.id,
            handoff_artifact_path=handoff_artifact.path,
        )

    def _blocked(self, store: AriadneStore, ticket: BuildTicket, reason: str) -> PlannerResult:
        run = _start_planner_run(store, ticket, self.name)
        artifact = store.write_artifact(
            ticket.id,
            run.id,
            ArtifactType.PLANNER_ERROR,
            "planner_error.json",
            json.dumps({"planner": self.name, "blocked": True, "reason": reason}, indent=2) + "\n",
            "LLM planner blocked or failed.",
            metadata={"planner_name": self.name, "blocked": True},
        )
        run = _finish_planner_run(store, run, AgentRunStatus.BLOCKED, reason, [artifact.id])
        updated = (
            store.load_ticket(ticket.id)
            .with_run(run.id)
            .with_artifacts([artifact])
            .with_status(TicketStatus.BLOCKED, "Planner", reason)
        )
        store.save_ticket(updated)
        return PlannerResult(
            succeeded=False,
            planner_name=self.name,
            ticket_id=ticket.id,
            error=reason,
            error_artifact_id=artifact.id,
            error_artifact_path=artifact.path,
        )


def planner_for_name(name: str) -> PlannerBackend:
    if name == "deterministic":
        return DeterministicPlanner()
    if name == "llm":
        return LLMPlanner()
    msg = f"unknown planner: {name}"
    raise ValueError(msg)


def render_handoff(ticket: BuildTicket, packet: BuildPacket) -> str:
    tasks = "\n".join(f"- {task}" for task in packet.tasks)
    criteria = "\n".join(f"- {criterion}" for criterion in packet.acceptance_criteria)
    allowed_paths = "\n".join(f"- {path}" for path in packet.affected_modules)
    evidence = "\n".join(
        f"- {item.quote_or_summary} ({item.location}, confidence {item.confidence:.2f})"
        for item in packet.evidence[:5]
    )
    skill_refs = handoff_skill_references()
    return f"""# Ariadne Coding Handoff - {ticket.key}

Ticket: {ticket.title}
Build decision: {packet.build_decision.value}

## Goal

{packet.insight}

## Tasks

{tasks}

## Allowed Paths

{allowed_paths}

## Acceptance Criteria

{criteria}

## Evidence

{evidence}

## Skills

{skill_refs}

## Safety Constraints

- Do not commit, push, merge, or create a PR.
- Write only the files listed in Allowed Paths. Do not create or modify lockfiles such as `uv.lock`.
- Do not write secrets.
- Use `python -m pytest` or `pytest` for verification; do not use `uv` for this handoff.
- Capture stdout, stderr, exit code, changed files, diff, and tests.
- When the acceptance criteria pass, stop and report the result; do not continue iterating.
"""


def _load_source(store: AriadneStore, ticket: BuildTicket) -> SourceDocument:
    source_id = ticket.metadata.get("source_document_id")
    if source_id:
        return store.load_source_document(source_id)
    return source_document_from_path(__import__("pathlib").Path(ticket.source_ref))


def _packet_from_llm_json(
    ticket: BuildTicket,
    source: SourceDocument,
    data: dict,
) -> BuildPacket:
    evidence = [
        Evidence(
            id=stable_id("evidence", source.id, index, item.get("quote_or_summary", "")),
            source_ref=source.path_or_url,
            quote_or_summary=item["quote_or_summary"],
            location=item.get("location") or source.metadata.get("filename", "source"),
            confidence=float(item.get("confidence", 0.7)),
        )
        for index, item in enumerate(data.get("evidence", []), start=1)
    ]
    packet = BuildPacket(
        id=stable_id("packet", ticket.id),
        ticket_id=ticket.id,
        source_summary=data["source_summary"],
        insight=data["insight"],
        evidence=evidence,
        project_relevance=data["project_relevance"],
        build_decision=BuildDecision(data["build_decision"]),
        tasks=list(data.get("tasks", [])),
        acceptance_criteria=list(data.get("acceptance_criteria", [])),
        affected_modules=list(data.get("affected_modules", [])),
        risks=list(data.get("risks", [])),
        assumptions=list(data.get("assumptions", [])),
        confidence=0.75,
    )
    quality = score_build_packet(packet)
    return packet.model_copy(
        update={"metadata": packet.metadata | {"quality": quality, "planner_mode": "llm"}}
    )


def _llm_prompt(ticket: BuildTicket, source: SourceDocument) -> str:
    return (
        "Create an Ariadne Build Packet JSON object using the required schema. "
        "Return JSON only.\n\n"
        f"Ticket: {ticket.key} {ticket.title}\n"
        f"Source type: {source.source_type.value}\n"
        f"Source summary: {source.summary}\n"
        f"Source path: {source.path_or_url}\n"
    )


def _start_planner_run(store: AriadneStore, ticket: BuildTicket, planner_name: str) -> AgentRun:
    attempt = 1 + sum(
        1
        for run_id in ticket.agent_run_ids
        if store.load_run(run_id).agent_role == f"planner:{planner_name}"
    )
    run = AgentRun(
        id=stable_id("run", ticket.id, f"planner:{planner_name}", attempt),
        ticket_id=ticket.id,
        agent_name="Planner",
        agent_role=f"planner:{planner_name}",
        input_summary=f"Plan {ticket.key} with {planner_name} planner.",
        attempt=attempt,
        backend_name=planner_name,
    ).mark_running()
    store.save_run(run)
    updated = ticket.with_run(run.id).append_event(
        "agent_run_started",
        "Planner",
        f"{planner_name} planner started.",
        payload_ref=run.id,
    )
    store.save_ticket(updated)
    return run


def _finish_planner_run(
    store: AriadneStore,
    run: AgentRun,
    status: AgentRunStatus,
    summary: str,
    artifact_ids: list[str],
) -> AgentRun:
    finished = run.model_copy(update={"artifact_ids": artifact_ids}).mark_finished(status, summary)
    store.save_run(finished)
    return finished


def _write_packet_artifact(store: AriadneStore, run_id: str, packet: BuildPacket):
    return store.write_artifact(
        packet.ticket_id,
        run_id,
        ArtifactType.BUILD_PACKET,
        "build_packet.json",
        packet.model_dump_json(indent=2) + "\n",
        "Planner Build Packet",
        metadata={"build_packet_id": packet.id},
    )


def _write_handoff_artifact(
    store: AriadneStore,
    run_id: str,
    ticket: BuildTicket,
    packet: BuildPacket,
):
    handoff = render_handoff(ticket, packet)
    return store.write_artifact(
        ticket.id,
        run_id,
        ArtifactType.CODEX_HANDOFF,
        "handoff.md",
        handoff,
        "Coding backend handoff prompt",
        metadata={"build_packet_id": packet.id},
    )
