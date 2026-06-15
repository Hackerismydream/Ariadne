from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, *parts: object) -> str:
    source = "::".join(str(part) for part in parts)
    digest = sha256(source.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


class AriadneModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class TicketStatus(str, Enum):
    INBOX = "inbox"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    CODING = "coding"
    REVIEWING = "reviewing"
    NEEDS_FIX = "needs_fix"
    WRITING_MEMORY = "writing_memory"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            AgentRunStatus.SUCCEEDED,
            AgentRunStatus.FAILED,
            AgentRunStatus.SKIPPED,
            AgentRunStatus.CANCELLED,
        }


class BuildDecision(str, Enum):
    ARCHIVE = "archive"
    WATCHLIST = "watchlist"
    DOC_UPDATE = "doc_update"
    EXPERIMENT = "experiment"
    CODE_TASK = "code_task"
    ARCHITECTURE_CHANGE = "architecture_change"
    REJECT_FOR_NOW = "reject_for_now"


class ArtifactType(str, Enum):
    BUILD_PACKET = "build_packet"
    RESEARCH_SUMMARY = "research_summary"
    REPO_CONTEXT = "repo_context"
    EXECUTION_PLAN = "execution_plan"
    CODEX_HANDOFF = "codex_handoff"
    DRY_RUN_EXECUTION = "dry_run_execution"
    REVIEW_REPORT = "review_report"
    FEISHU_WRITE_PLAN = "feishu_write_plan"
    BOARD_EXPORT = "board_export"
    DEVELOPMENT_REPORT = "development_report"


class ReviewVerdict(str, Enum):
    PASS = "pass"
    NEEDS_FIX = "needs_fix"
    BLOCKED = "blocked"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class TicketEvent(AriadneModel):
    timestamp: str = Field(default_factory=utc_now)
    ticket_id: str
    event_type: str
    actor: str
    summary: str
    payload_ref: str | None = None


class ProjectSpace(AriadneModel):
    id: str
    display_name: str
    root_path: str
    repo_path: str
    knowledge_paths: list[str] = Field(default_factory=list)
    feishu_space_ref: str | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    settings: dict[str, Any] = Field(default_factory=dict)


class BuildTicket(AriadneModel):
    id: str
    key: str
    title: str
    description: str
    source_type: str
    source_ref: str
    status: TicketStatus = TicketStatus.INBOX
    priority: str = "medium"
    owner_agent: str = "Build Lead"
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    build_packet_id: str | None = None
    agent_run_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    event_log: list[TicketEvent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def with_status(self, status: TicketStatus, actor: str, summary: str | None = None) -> BuildTicket:
        ticket = self.model_copy(deep=True)
        previous = ticket.status
        ticket.status = status
        ticket.updated_at = utc_now()
        ticket.event_log.append(
            TicketEvent(
                ticket_id=ticket.id,
                event_type="status_changed",
                actor=actor,
                summary=summary or f"Status changed from {previous.value} to {status.value}.",
            )
        )
        return ticket

    def append_event(
        self,
        event_type: str,
        actor: str,
        summary: str,
        payload_ref: str | None = None,
    ) -> BuildTicket:
        ticket = self.model_copy(deep=True)
        ticket.updated_at = utc_now()
        ticket.event_log.append(
            TicketEvent(
                ticket_id=ticket.id,
                event_type=event_type,
                actor=actor,
                summary=summary,
                payload_ref=payload_ref,
            )
        )
        return ticket

    def with_run(self, run_id: str) -> BuildTicket:
        ticket = self.model_copy(deep=True)
        ticket.agent_run_ids = [existing for existing in ticket.agent_run_ids if existing != run_id]
        ticket.agent_run_ids.append(run_id)
        ticket.updated_at = utc_now()
        return ticket

    def with_artifacts(self, artifacts: list[Artifact]) -> BuildTicket:
        ticket = self.model_copy(deep=True)
        for artifact in artifacts:
            ticket.artifact_ids = [
                existing for existing in ticket.artifact_ids if existing != artifact.id
            ]
            ticket.artifact_ids.append(artifact.id)
        ticket.updated_at = utc_now()
        return ticket


class Evidence(AriadneModel):
    id: str
    source_ref: str
    quote_or_summary: str
    location: str
    confidence: float = 0.8

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            msg = "confidence must be between 0 and 1"
            raise ValueError(msg)
        return value


class BuildPacket(AriadneModel):
    id: str
    ticket_id: str
    source_summary: str
    insight: str
    evidence: list[Evidence] = Field(default_factory=list)
    project_relevance: str
    build_decision: BuildDecision
    tasks: list[str]
    acceptance_criteria: list[str]
    affected_modules: list[str]
    coding_agent_handoff_id: str | None = None
    feishu_write_plan_id: str | None = None
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_code_task_has_evidence(self) -> BuildPacket:
        if self.build_decision is BuildDecision.CODE_TASK and not self.evidence:
            msg = "code_task build packets require at least one evidence item"
            raise ValueError(msg)
        return self


class AgentRun(AriadneModel):
    id: str
    ticket_id: str
    agent_name: str
    agent_role: str
    status: AgentRunStatus = AgentRunStatus.PENDING
    input_summary: str
    output_summary: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    started_at: str | None = None
    ended_at: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status.is_terminal

    def mark_running(self) -> AgentRun:
        run = self.model_copy(deep=True)
        run.status = AgentRunStatus.RUNNING
        run.started_at = run.started_at or utc_now()
        return run

    def mark_finished(
        self,
        status: AgentRunStatus,
        output_summary: str | None = None,
        error: str | None = None,
    ) -> AgentRun:
        if not status.is_terminal:
            msg = "finished AgentRun status must be terminal"
            raise ValueError(msg)
        run = self.model_copy(deep=True)
        run.status = status
        run.output_summary = output_summary
        run.error = error
        run.ended_at = utc_now()
        return run


class Artifact(AriadneModel):
    id: str
    ticket_id: str
    agent_run_id: str
    artifact_type: ArtifactType
    path: str
    summary: str
    created_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewReport(AriadneModel):
    id: str
    ticket_id: str
    verdict: ReviewVerdict
    passed_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    required_fixes: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class FeishuWritePlan(AriadneModel):
    id: str
    ticket_id: str
    dry_run: bool = True
    proposed_docs: list[dict[str, Any]] = Field(default_factory=list)
    proposed_tasks: list[dict[str, Any]] = Field(default_factory=list)
    decision_log_entry: str
    run_summary: str
    next_actions: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_dry_run(self) -> FeishuWritePlan:
        if not self.dry_run:
            msg = "MVP FeishuWritePlan must be dry_run=true"
            raise ValueError(msg)
        return self


class BuildSkill(AriadneModel):
    id: str
    name: str
    description: str
    applies_to_agent_roles: list[str]
    body_markdown: str
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
