from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from pydantic import Field, ValidationError, field_validator

from ariadne_ltb.llm import DeepSeekClient, LLMClientError, load_local_env, redact_secrets
from ariadne_ltb.models import (
    AriadneModel,
    Artifact,
    ArtifactType,
    BuildPacket,
    BuildTicket,
    ExecutionResult,
    ReviewReport,
    utc_now,
)
from ariadne_ltb.storage import AriadneStore


ALLOWED_BACKLOG_SOURCES = {"failed_check", "review", "memory", "changed_file"}


class LLMBacklogSuggestion(AriadneModel):
    title: str
    reason: str
    source: str
    priority: str = "medium"
    suggested_build_decision: str = "code_task"
    acceptance_criteria: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)

    @field_validator("source")
    @classmethod
    def valid_source(cls, value: str) -> str:
        if value not in ALLOWED_BACKLOG_SOURCES:
            msg = f"source must be one of {sorted(ALLOWED_BACKLOG_SOURCES)}"
            raise ValueError(msg)
        return value

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value: str) -> str:
        if value not in {"high", "medium", "low"}:
            return "medium"
        return value


class LLMBacklogPayload(AriadneModel):
    rationale: str
    next_tickets: list[LLMBacklogSuggestion] = Field(default_factory=list)

    @field_validator("next_tickets")
    @classmethod
    def cap_suggestions(cls, value: list[LLMBacklogSuggestion]) -> list[LLMBacklogSuggestion]:
        return value[:5]


@dataclass(frozen=True)
class LLMBacklogPlannerResult:
    planner_name: str
    succeeded: bool
    artifact: Artifact
    effective_next_tickets_path: str
    error: str | None = None


def generate_llm_backlog_artifact(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
    run_id: str,
    deterministic_next_tickets_path: str,
    client: DeepSeekClient | None = None,
) -> LLMBacklogPlannerResult:
    load_local_env(store.root)
    if not os.environ.get("DEEPSEEK_API_KEY") and client is None:
        reason = "DEEPSEEK_API_KEY is required for --backlog-planner llm."
        artifact = _write_blocked_artifact(
            store,
            ticket,
            run_id,
            deterministic_next_tickets_path,
            reason,
        )
        return LLMBacklogPlannerResult(
            planner_name="llm",
            succeeded=False,
            artifact=artifact,
            effective_next_tickets_path=deterministic_next_tickets_path,
            error=reason,
        )

    llm_client = client or DeepSeekClient()
    try:
        data = llm_client.complete_json(
            _prompt(ticket, packet, execution, review),
            "ariadne_backlog_delta",
        )
        payload = LLMBacklogPayload.model_validate(data)
    except (LLMClientError, ValidationError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        reason = redact_secrets(f"LLM backlog planner failed: {exc}")
        artifact = _write_blocked_artifact(
            store,
            ticket,
            run_id,
            deterministic_next_tickets_path,
            reason,
        )
        return LLMBacklogPlannerResult(
            planner_name="llm",
            succeeded=False,
            artifact=artifact,
            effective_next_tickets_path=deterministic_next_tickets_path,
            error=reason,
        )

    artifact = _write_success_artifact(
        store,
        ticket,
        run_id,
        deterministic_next_tickets_path,
        payload,
    )
    return LLMBacklogPlannerResult(
        planner_name="llm",
        succeeded=True,
        artifact=artifact,
        effective_next_tickets_path=artifact.path,
    )


def _write_success_artifact(
    store: AriadneStore,
    ticket: BuildTicket,
    run_id: str,
    deterministic_next_tickets_path: str,
    payload: LLMBacklogPayload,
) -> Artifact:
    content = {
        "source_ticket_id": ticket.id,
        "source_ticket_key": ticket.key,
        "generated_at": utc_now(),
        "planner": "llm",
        "blocked": False,
        "rationale": payload.rationale,
        "fallback_next_tickets_path": deterministic_next_tickets_path,
        "next_tickets": [item.model_dump(mode="json") for item in payload.next_tickets],
    }
    return store.write_artifact(
        ticket.id,
        run_id,
        ArtifactType.NEXT_TICKETS,
        "llm_next_tickets.json",
        json.dumps(content, indent=2) + "\n",
        "LLM-generated backlog delta suggestions",
        metadata={"source": "llm_backlog_planner", "planner": "llm", "blocked": False},
    )


def _write_blocked_artifact(
    store: AriadneStore,
    ticket: BuildTicket,
    run_id: str,
    deterministic_next_tickets_path: str,
    reason: str,
) -> Artifact:
    content = {
        "source_ticket_id": ticket.id,
        "source_ticket_key": ticket.key,
        "generated_at": utc_now(),
        "planner": "llm",
        "blocked": True,
        "reason": reason,
        "fallback_next_tickets_path": deterministic_next_tickets_path,
        "next_tickets": [],
    }
    return store.write_artifact(
        ticket.id,
        run_id,
        ArtifactType.NEXT_TICKETS,
        "llm_next_tickets_blocked.json",
        json.dumps(content, indent=2) + "\n",
        "LLM backlog planner blocked or failed",
        metadata={"source": "llm_backlog_planner", "planner": "llm", "blocked": True},
    )


def _prompt(
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
) -> str:
    payload: dict[str, Any] = {
        "instruction": (
            "Return JSON only. Generate 0-5 ticket backlog delta suggestions that should be "
            "created after this Ariadne ticket run. Use only sources: failed_check, review, "
            "memory, changed_file. Prefer concrete product work over demo-only work."
        ),
        "expected_json_shape": {
            "rationale": "",
            "next_tickets": [
                {
                    "title": "",
                    "reason": "",
                    "source": "failed_check|review|memory|changed_file",
                    "priority": "high|medium|low",
                    "suggested_build_decision": "code_task|doc_update|architecture_change|experiment",
                    "acceptance_criteria": [],
                    "affected_modules": [],
                }
            ],
        },
        "ticket": {
            "id": ticket.id,
            "key": ticket.key,
            "title": ticket.title,
            "status": ticket.status.value,
            "source_type": ticket.source_type,
        },
        "build_packet": {
            "decision": packet.build_decision.value,
            "tasks": packet.tasks,
            "acceptance_criteria": packet.acceptance_criteria,
            "affected_modules": packet.affected_modules,
            "risks": packet.risks,
        },
        "execution": {
            "backend": execution.backend_name,
            "blocked": execution.blocked,
            "exit_code": execution.exit_code,
            "test_exit_code": execution.test_exit_code,
            "changed_files": execution.changed_files,
            "warnings": execution.warnings,
            "failure_reason": execution.failure_reason.value if execution.failure_reason else None,
            "block_reason": execution.block_reason,
        },
        "review": {
            "verdict": review.verdict.value,
            "failed_checks": review.failed_checks,
            "warnings": review.warnings,
            "required_fixes": review.required_fixes,
            "next_ticket_suggestions": review.next_ticket_suggestions,
        },
    }
    return json.dumps(payload, indent=2)
