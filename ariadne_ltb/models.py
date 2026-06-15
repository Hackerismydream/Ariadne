from __future__ import annotations

import os
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
    READY_FOR_EXECUTION = "ready_for_execution"
    CODING = "coding"
    REVIEWING = "reviewing"
    NEEDS_FIX = "needs_fix"
    WRITING_MEMORY = "writing_memory"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssignmentStatus(str, Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            AssignmentStatus.BLOCKED,
            AssignmentStatus.DONE,
            AssignmentStatus.FAILED,
            AssignmentStatus.CANCELLED,
        }


class AgentRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            AgentRunStatus.SUCCEEDED,
            AgentRunStatus.FAILED,
            AgentRunStatus.BLOCKED,
            AgentRunStatus.SKIPPED,
            AgentRunStatus.CANCELLED,
        }


class AgentRunLifecycleState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    TERMINAL = "terminal"


class FailureReason(str, Enum):
    AGENT_ERROR = "agent_error"
    RUNTIME_OFFLINE = "runtime_offline"
    RUNTIME_RECOVERY = "runtime_recovery"
    TIMEOUT = "timeout"
    EXTERNAL_EXECUTION_BLOCKED = "external_execution_blocked"
    COMMAND_UNAVAILABLE = "command_unavailable"
    MODEL_UNSUPPORTED = "model_unsupported"
    TEST_FAILED = "test_failed"
    SCOPE_VIOLATION = "scope_violation"
    REVIEW_FAILED = "review_failed"
    USER_CANCELLED = "user_cancelled"
    PLANNER_FAILED = "planner_failed"
    INVALID_RESOURCE = "invalid_resource"
    RESOURCE_LOCKED = "resource_locked"
    UNKNOWN = "unknown"


class SourceType(str, Enum):
    PAPER = "paper"
    BLOG = "blog"
    GITHUB_REPO = "github_repo"
    NOTE = "note"
    OFFICE_HOUR = "office_hour"
    REVIEW = "review"


class BuildDecision(str, Enum):
    ARCHIVE = "archive"
    WATCHLIST = "watchlist"
    DOC_UPDATE = "doc_update"
    EXPERIMENT = "experiment"
    CODE_TASK = "code_task"
    ARCHITECTURE_CHANGE = "architecture_change"
    REJECT_FOR_NOW = "reject_for_now"


class ArtifactType(str, Enum):
    SOURCE_DOCUMENT = "source_document"
    BUILD_PACKET = "build_packet"
    RESEARCH_SUMMARY = "research_summary"
    REPO_CONTEXT = "repo_context"
    EXECUTION_PLAN = "execution_plan"
    CODEX_HANDOFF = "codex_handoff"
    DRY_RUN_EXECUTION = "dry_run_execution"
    EXECUTION_LOG = "execution_log"
    GIT_DIFF = "git_diff"
    CHANGED_FILES = "changed_files"
    TEST_OUTPUT = "test_output"
    REVIEW_REPORT = "review_report"
    FEISHU_WRITE_PLAN = "feishu_write_plan"
    MEMORY_RECORD = "memory_record"
    NEXT_TICKETS = "next_tickets"
    ROUTE_DECISION = "route_decision"
    RUNTIME_CAPABILITY = "runtime_capability"
    PROJECT_RESOURCES = "project_resources"
    PLANNER_ERROR = "planner_error"
    BOARD_EXPORT = "board_export"
    DEVELOPMENT_REPORT = "development_report"


class ReviewVerdict(str, Enum):
    PASS = "pass"
    NEEDS_FIX = "needs_fix"
    BLOCKED = "blocked"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class CommentAuthorType(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class CommentKind(str, Enum):
    COMMENT = "comment"
    ASSIGNMENT = "assignment"
    PROGRESS = "progress"
    BLOCKER = "blocker"
    REVIEW = "review"
    MEMORY = "memory"
    ROUTE = "route"
    RECOVERY = "recovery"
    HANDOFF = "handoff"


class ResumeSafety(str, Enum):
    SAFE_TO_RESUME = "safe_to_resume"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    UNSAFE = "unsafe"


class DaemonStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    STOPPED = "stopped"


class WorkerHeartbeat(AriadneModel):
    runtime_id: str
    pid: int
    status: DaemonStatus
    current_assignment_id: str | None = None
    current_ticket_id: str | None = None
    current_ticket_key: str | None = None
    current_stage: str | None = None
    started_at: str
    heartbeat_at: str
    last_event_id: str | None = None
    last_error: str | None = None

    @classmethod
    def new(
        cls,
        runtime_id: str,
        status: DaemonStatus,
        current_stage: str | None = None,
    ) -> WorkerHeartbeat:
        now = utc_now()
        return cls(
            runtime_id=runtime_id,
            pid=os.getpid(),
            status=status,
            current_stage=current_stage,
            started_at=now,
            heartbeat_at=now,
        )


class HandoffStatus(str, Enum):
    CREATED = "created"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class AgentHandoff(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    from_agent: str
    to_agent: str
    from_assignment_id: str | None = None
    to_assignment_id: str | None = None
    reason: str
    payload_ref: str | None = None
    status: HandoffStatus = HandoffStatus.CREATED
    created_at: str = Field(default_factory=utc_now)
    completed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def mark_completed(self) -> AgentHandoff:
        return self.model_copy(
            update={"status": HandoffStatus.COMPLETED, "completed_at": utc_now()}
        )


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


class SourceDocument(AriadneModel):
    id: str
    source_type: SourceType
    title: str
    path_or_url: str
    content_hash: str
    summary: str
    created_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentProfile(AriadneModel):
    id: str
    name: str
    role: str
    backend_name: str | None = None
    planner_name: str = "deterministic"
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    default_confirm_execution: bool = False
    enabled: bool = True
    created_at: str = Field(default_factory=utc_now)


class TicketAssignment(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    agent_id: str
    agent_name: str
    backend_name: str | None = None
    planner_name: str = "deterministic"
    status: AssignmentStatus = AssignmentStatus.QUEUED
    priority: str = "medium"
    assigned_by: str = "human"
    claimed_by_runtime_id: str | None = None
    created_at: str = Field(default_factory=utc_now)
    claimed_at: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    failure_reason: FailureReason | None = None
    blocker: str | None = None
    parent_assignment_id: str | None = None
    attempt: int = 1
    retry_reason: str | None = None
    retry_policy: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status.is_terminal

    def mark_claimed(self, runtime_id: str) -> TicketAssignment:
        assignment = self.model_copy(deep=True)
        assignment.status = AssignmentStatus.CLAIMED
        assignment.claimed_by_runtime_id = runtime_id
        assignment.claimed_at = assignment.claimed_at or utc_now()
        return assignment

    def mark_running(self) -> TicketAssignment:
        assignment = self.model_copy(deep=True)
        assignment.status = AssignmentStatus.RUNNING
        assignment.started_at = assignment.started_at or utc_now()
        return assignment

    def mark_done(self, metadata: dict[str, Any] | None = None) -> TicketAssignment:
        assignment = self.model_copy(deep=True)
        assignment.status = AssignmentStatus.DONE
        assignment.ended_at = utc_now()
        if metadata:
            assignment.metadata = assignment.metadata | metadata
        return assignment

    def mark_blocked(
        self,
        blocker: str,
        failure_reason: FailureReason = FailureReason.UNKNOWN,
    ) -> TicketAssignment:
        assignment = self.model_copy(deep=True)
        assignment.status = AssignmentStatus.BLOCKED
        assignment.blocker = blocker
        assignment.failure_reason = failure_reason
        assignment.ended_at = utc_now()
        return assignment

    def mark_failed(
        self,
        blocker: str,
        failure_reason: FailureReason = FailureReason.AGENT_ERROR,
    ) -> TicketAssignment:
        assignment = self.model_copy(deep=True)
        assignment.status = AssignmentStatus.FAILED
        assignment.blocker = blocker
        assignment.failure_reason = failure_reason
        assignment.ended_at = utc_now()
        return assignment


class TicketComment(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    author_type: CommentAuthorType
    author: str
    kind: CommentKind = CommentKind.COMMENT
    body: str
    payload_ref: str | None = None
    created_at: str = Field(default_factory=utc_now)


class RuntimeEvent(AriadneModel):
    id: str
    ticket_id: str | None = None
    ticket_key: str | None = None
    assignment_id: str | None = None
    run_id: str | None = None
    runtime_id: str
    stage: str
    event_type: str
    actor: str
    timestamp: str = Field(default_factory=utc_now)
    payload_ref: str | None = None
    failure_reason: FailureReason | None = None
    idempotency_key: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResumePlan(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    assignment_id: str | None = None
    last_completed_stage: str | None = None
    current_stage: str | None = None
    next_stage: str | None = None
    safety: ResumeSafety
    reasons: list[str] = Field(default_factory=list)
    recommended_command: str | None = None
    created_at: str = Field(default_factory=utc_now)


class ProjectContext(AriadneModel):
    id: str
    project_space_id: str
    target_repo_path: str
    top_level_files: list[str] = Field(default_factory=list)
    important_files: list[str] = Field(default_factory=list)
    readme_summary: str = ""
    package_metadata: dict[str, Any] = Field(default_factory=dict)
    test_command: str = ""
    existing_tickets_summary: str = ""
    created_at: str = Field(default_factory=utc_now)


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
    metadata: dict[str, Any] = Field(default_factory=dict)

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
    lifecycle_state: AgentRunLifecycleState = AgentRunLifecycleState.CREATED
    input_summary: str
    output_summary: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    attempt: int = 1
    parent_run_id: str | None = None
    backend_name: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    error: str | None = None
    failure_reason: FailureReason | None = None
    runtime_id: str | None = None
    session_id: str | None = None
    work_dir: str | None = None
    superseded_by_run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status.is_terminal

    def mark_running(self) -> AgentRun:
        run = self.model_copy(deep=True)
        run.status = AgentRunStatus.RUNNING
        run.lifecycle_state = AgentRunLifecycleState.RUNNING
        run.started_at = run.started_at or utc_now()
        return run

    def mark_finished(
        self,
        status: AgentRunStatus,
        output_summary: str | None = None,
        error: str | None = None,
        failure_reason: FailureReason | None = None,
    ) -> AgentRun:
        if not status.is_terminal:
            msg = "finished AgentRun status must be terminal"
            raise ValueError(msg)
        run = self.model_copy(deep=True)
        run.status = status
        run.lifecycle_state = AgentRunLifecycleState.TERMINAL
        run.output_summary = output_summary
        run.error = error
        run.failure_reason = failure_reason
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
    failure_reasons: list[FailureReason] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class ExecutionContext(AriadneModel):
    ticket_id: str
    ticket_key: str | None = None
    build_packet_id: str
    target_repo_path: str
    handoff_prompt: str
    handoff_file: str | None = None
    backend_name: str
    allowed_paths: list[str] = Field(default_factory=list)
    command: str
    test_command: str
    confirm_execution: bool = False
    timeout_seconds: int = 120
    assignment_id: str | None = None
    run_id: str | None = None


class ExecutionResult(AriadneModel):
    id: str
    ticket_id: str
    backend_name: str
    dry_run: bool
    blocked: bool = False
    block_reason: str | None = None
    failure_reason: FailureReason | None = None
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    started_at: str = Field(default_factory=utc_now)
    ended_at: str = Field(default_factory=utc_now)
    git_head_before: str | None = None
    git_head_after: str | None = None
    git_status_before: str = ""
    git_status_after: str = ""
    changed_files: list[str] = Field(default_factory=list)
    git_diff: str = ""
    diff_artifact_id: str | None = None
    execution_log_artifact_id: str | None = None
    test_command: str = ""
    test_exit_code: int | None = None
    test_stdout: str = ""
    test_stderr: str = ""
    warnings: list[str] = Field(default_factory=list)


class RuntimeCapability(AriadneModel):
    backend_name: str
    command: str
    available: bool
    command_path: str | None = None
    external_execution_enabled: bool = False
    command_template_set: bool = False
    confirm_execution_required: bool = True
    supports_external_execution: bool = False
    supports_dry_run: bool = False
    checked_at: str = Field(default_factory=utc_now)


class ProjectResource(AriadneModel):
    id: str
    project_id: str
    resource_type: str
    resource_ref: dict[str, Any]
    label: str | None = None
    position: int = 0
    created_at: str = Field(default_factory=utc_now)

    @classmethod
    def local_directory(
        cls,
        project_id: str,
        local_path: Any,
        label: str | None = None,
        daemon_id: str = "local",
    ) -> ProjectResource:
        from pathlib import Path

        resolved = str(Path(local_path).resolve())
        return cls(
            id=stable_id("resource", project_id, "local_directory", resolved, daemon_id),
            project_id=project_id,
            resource_type="local_directory",
            resource_ref={
                "local_path": resolved,
                "daemon_id": daemon_id,
                "label": label or "local checkout",
            },
            label=label,
        )


class RouteDecision(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    planner_name: str
    backend_name: str
    selected_agent_role: str = "Execution"
    target_repo_path: str
    build_decision: BuildDecision
    reason: str
    external_execution_enabled: bool = False
    confirm_execution: bool = False
    skill_refs: list[str] = Field(default_factory=list)
    resource_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class MemoryRecord(AriadneModel):
    id: str
    ticket_id: str
    title: str
    decision_log_entry: str
    build_summary: str
    review_summary: str
    source_refs: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
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
