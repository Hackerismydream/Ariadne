from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from enum import Enum
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ariadne_ltb.defaults import PRODUCT_DEFAULT_BACKEND


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_after(seconds: int) -> str:
    return (
        (datetime.now(UTC) + timedelta(seconds=seconds))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


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
    SUPERSEDED = "superseded"


class BacklogUpdateTrigger(str, Enum):
    SOURCE_INGEST = "source_ingest"
    REVIEW_FEEDBACK = "review_feedback"
    EXECUTION_RESULT = "execution_result"
    MEMORY_GAP = "memory_gap"
    CODEBASE_OBSERVATION = "codebase_observation"
    INBOX_RECOVERY = "inbox_recovery"
    MANUAL_GOAL = "manual_goal"


class TicketChangeType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    REPRIORITIZED = "reprioritized"
    DOWNGRADED = "downgraded"
    SPLIT = "split"
    CLOSED = "closed"
    SUPERSEDED = "superseded"
    NO_OP = "no_op"


class BacklogOperationType(str, Enum):
    ADD_TICKET = "add_ticket"
    UPDATE_TICKET = "update_ticket"
    DEFER_TICKET = "defer_ticket"
    SUPERSEDE_TICKET = "supersede_ticket"
    PROMOTE_TICKET = "promote_ticket"
    NO_OP = "no_op"


class BacklogConflictType(str, Enum):
    DUPLICATE_OPERATION = "duplicate_operation"
    STALE_PREVIEW = "stale_preview"
    SUPERSEDED_TARGET = "superseded_target"
    CONTRADICTORY_UPDATE = "contradictory_update"


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


class RunMessageType(str, Enum):
    STATUS = "status"
    ARTIFACT = "artifact"
    RESULT = "result"
    ERROR = "error"
    TOOL = "tool"


class FailureReason(str, Enum):
    AGENT_ERROR = "agent_error"
    AUTHENTICATION_FAILED = "authentication_failed"
    QUOTA_EXCEEDED = "quota_exceeded"
    PROVIDER_CONFIG_INVALID = "provider_config_invalid"
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
    DIRTY_BASE_CHECKOUT = "dirty_base_checkout"
    UNKNOWN = "unknown"


class StoreInvariantSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class StoreInvariantReason(str, Enum):
    DUPLICATE_TICKET_KEY = "duplicate_ticket_key"
    MALFORMED_JSON = "malformed_json"
    MALFORMED_JSONL = "malformed_jsonl"
    MODEL_VALIDATION_FAILED = "model_validation_failed"
    MISSING_TICKET = "missing_ticket"
    MISSING_BUILD_PACKET = "missing_build_packet"
    MISSING_AGENT_RUN = "missing_agent_run"
    MISSING_ARTIFACT_INDEX = "missing_artifact_index"
    MISSING_ARTIFACT_FILE = "missing_artifact_file"
    ORPHAN_ARTIFACT = "orphan_artifact"
    BROKEN_ASSIGNMENT_LINK = "broken_assignment_link"
    BROKEN_RUN_LINK = "broken_run_link"
    BROKEN_HANDOFF_LINK = "broken_handoff_link"
    BROKEN_MEMORY_LINK = "broken_memory_link"
    BROKEN_REVIEW_LINK = "broken_review_link"
    INVALID_RUN_LIFECYCLE = "invalid_run_lifecycle"
    INVALID_ASSIGNMENT_LIFECYCLE = "invalid_assignment_lifecycle"
    STALE_ASSIGNMENT_LEASE = "stale_assignment_lease"
    STALE_LOCK = "stale_lock"


class SourceType(str, Enum):
    PAPER = "paper"
    BLOG = "blog"
    GITHUB_REPO = "github_repo"
    NOTE = "note"
    LOCAL_MARKDOWN = "local_markdown"
    LOCAL_FOLDER = "local_folder"
    TARGET_CODEBASE = "target_codebase"
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
    PERMISSION_PROFILE = "permission_profile"
    SKILL_BUNDLE = "skill_bundle"
    WORKTREE_ISOLATION = "worktree_isolation"
    ORCHESTRATOR_RESULT = "orchestrator_result"
    LANDING_EVIDENCE = "landing_evidence"
    LANDING_GATE_REPORT = "landing_gate_report"
    STORE_INVARIANT_REPORT = "store_invariant_report"
    PLANNER_ERROR = "planner_error"
    LLM_AGENT_RESULT = "llm_agent_result"
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


class InboxSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InboxStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


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


class TicketChange(AriadneModel):
    ticket_id: str
    ticket_key: str
    change_type: TicketChangeType
    reason: str
    before_status: str | None = None
    after_status: str | None = None
    before_priority: str | None = None
    after_priority: str | None = None


class BacklogUpdate(AriadneModel):
    id: str
    trigger_type: BacklogUpdateTrigger
    trigger_ref: str
    created_ticket_ids: list[str] = Field(default_factory=list)
    updated_ticket_ids: list[str] = Field(default_factory=list)
    superseded_ticket_ids: list[str] = Field(default_factory=list)
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
    ticket_changes: list[TicketChange] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class BacklogOperation(AriadneModel):
    id: str
    operation_type: BacklogOperationType
    reason: str
    ticket_id: str | None = None
    ticket_key: str | None = None
    title: str | None = None
    description: str | None = None
    source_type: str | None = None
    source_ref: str | None = None
    priority: str | None = None
    status: TicketStatus | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BacklogConflict(AriadneModel):
    conflict_type: BacklogConflictType
    message: str
    operation_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    resolution_options: list[str] = Field(default_factory=list)


class BacklogPreview(AriadneModel):
    id: str
    trigger_type: BacklogUpdateTrigger
    trigger_ref: str
    idempotency_key: str
    base_ticket_fingerprint: str
    operations: list[BacklogOperation] = Field(default_factory=list)
    conflicts: list[BacklogConflict] = Field(default_factory=list)
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    applied_at: str | None = None
    applied_update_id: str | None = None


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


class SourceEvidence(AriadneModel):
    id: str
    source_document_id: str
    artifact_id: str | None = None
    locator: str
    quote_or_summary: str
    claim: str
    confidence: float = Field(ge=0.0, le=1.0)
    content_hash: str
    created_at: datetime | str = Field(default_factory=lambda: datetime.now(UTC))


class SourceArtifact(AriadneModel):
    id: str
    source_document_id: str
    artifact_type: Literal[
        "knowledge_card",
        "reference_project_profile",
        "codebase_snapshot",
    ]
    payload_hash: str
    payload_path: str
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime | str = Field(default_factory=lambda: datetime.now(UTC))


class AgentProfile(AriadneModel):
    id: str
    name: str
    role: str
    backend_name: str | None = None
    planner_name: str = "deterministic"
    agent_runtime: str = "deterministic"
    backlog_planner_name: str = "deterministic"
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    default_confirm_execution: bool = False
    enabled: bool = True
    created_at: str = Field(default_factory=utc_now)


class BuildTeam(AriadneModel):
    id: str
    name: str
    description: str = ""
    lead_agent_id: str = "build-lead"
    implementer_agent_id: str = PRODUCT_DEFAULT_BACKEND
    reviewer_agent_id: str = "reviewer"
    memory_agent_id: str = "memory"
    default_backend_name: str = PRODUCT_DEFAULT_BACKEND
    planner_name: str = "deterministic"
    agent_runtime: str = "deterministic"
    backlog_planner_name: str = "deterministic"
    skill_refs: list[str] = Field(default_factory=list)
    resource_policy: str = "local_project_resources"
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
    agent_runtime: str = "deterministic"
    backlog_planner_name: str = "deterministic"
    status: AssignmentStatus = AssignmentStatus.QUEUED
    priority: str = "medium"
    assigned_by: str = "human"
    claimed_by_runtime_id: str | None = None
    created_at: str = Field(default_factory=utc_now)
    claimed_at: str | None = None
    lease_expires_at: str | None = None
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

    def mark_claimed(self, runtime_id: str, lease_seconds: int = 600) -> TicketAssignment:
        assignment = self.model_copy(deep=True)
        assignment.status = AssignmentStatus.CLAIMED
        assignment.claimed_by_runtime_id = runtime_id
        assignment.claimed_at = assignment.claimed_at or utc_now()
        assignment.lease_expires_at = utc_after(lease_seconds)
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
        assignment.lease_expires_at = None
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
        assignment.lease_expires_at = None
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
        assignment.lease_expires_at = None
        return assignment

    def mark_cancelled(
        self,
        blocker: str | None = None,
        failure_reason: FailureReason = FailureReason.USER_CANCELLED,
    ) -> TicketAssignment:
        assignment = self.model_copy(deep=True)
        assignment.status = AssignmentStatus.CANCELLED
        assignment.blocker = blocker
        assignment.failure_reason = failure_reason
        assignment.ended_at = utc_now()
        assignment.lease_expires_at = None
        return assignment


class TicketComment(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    author_type: CommentAuthorType
    author: str
    kind: CommentKind = CommentKind.COMMENT
    body: str
    parent_comment_id: str | None = None
    thread_id: str | None = None
    payload_ref: str | None = None
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def default_thread_id(self) -> TicketComment:
        if self.thread_id is None:
            self.thread_id = self.parent_comment_id or self.id
        return self


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


class RunMessage(AriadneModel):
    run_id: str
    seq: int
    timestamp: str = Field(default_factory=utc_now)
    stage: str
    message_type: RunMessageType = RunMessageType.STATUS
    content: str
    artifact_ref: str | None = None
    tool_name: str | None = None
    result_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("seq")
    @classmethod
    def validate_seq(cls, value: int) -> int:
        if value < 1:
            msg = "run message seq must be greater than 0"
            raise ValueError(msg)
        return value


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
    reviewer_mode: str = "deterministic"
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    acceptance_criteria_coverage: dict[str, bool] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    next_ticket_suggestions: list[str] = Field(default_factory=list)
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
    target_worktree_path: str | None = None
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
    permission_profile_id: str | None = None
    permission_profile_path: str | None = None
    skill_bundle_path: str | None = None
    provider_skill_dir: str | None = None


class ExecutionResult(AriadneModel):
    id: str
    ticket_id: str
    backend_name: str
    target_repo_path: str | None = None
    target_worktree_path: str | None = None
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
    handoff_file: str | None = None
    command_template: str | None = None
    command_template_env_var: str | None = None
    provider_session_id: str | None = None
    provider_failure_kind: str | None = None
    provider_failure_evidence: str | None = None


class ExecutionPermissionProfile(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    backend_name: str
    target_repo_path: str
    allowed_paths: list[str] = Field(default_factory=list)
    env_allowlist: list[str] = Field(default_factory=list)
    network_policy: str = "disabled_by_default"
    git_operations_policy: str = "block_commit_push_merge_pr"
    dangerous_git_operations: list[str] = Field(default_factory=list)
    external_execution_enabled: bool = False
    confirm_execution: bool = False
    command: str
    test_command: str
    created_at: str = Field(default_factory=utc_now)


class WorktreeIsolation(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    branch_policy: str = "codex-ticket-slug-v1"
    branch_slug: str | None = None
    target_repo_path: str | None = None
    base_repo_path: str
    base_branch: str
    base_sha: str
    branch_name: str
    worktree_path: str
    record_path: str
    created_at: str = Field(default_factory=utc_now)
    active: bool = True
    owner_metadata: dict[str, Any] = Field(default_factory=dict)


class WorkdirStatus(AriadneModel):
    ticket_id: str
    ticket_key: str
    worktree_path: str
    branch_name: str
    base_repo_path: str
    active: bool
    exists: bool
    dirty: bool
    git_status: str = ""
    record_path: str


class WorkdirCleanupResult(AriadneModel):
    ticket_key: str
    worktree_path: str
    removed: bool = False
    skipped: bool = False
    reason: str = ""
    dirty: bool = False
    record_path: str


class RuntimeCapability(AriadneModel):
    backend_name: str
    command: str
    available: bool
    command_path: str | None = None
    external_execution_enabled: bool = False
    command_template_set: bool = False
    template_env_var: str | None = None
    safety_gate_env_var: str | None = None
    confirm_execution_required: bool = True
    supports_external_execution: bool = False
    supports_dry_run: bool = False
    supports_prompt_file: bool = False
    supports_stdin_prompt: bool = False
    supports_session_resume: bool = False
    supports_mcp: bool = False
    supports_skill_materialization: bool = False
    supports_model_selection: bool = False
    supports_reasoning_effort: bool = False
    supports_timeout: bool = False
    supports_diff_capture: bool = False
    supports_test_capture: bool = False
    supports_git_status_capture: bool = False
    disabled_reasons: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
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
    agent_runtime: str = "deterministic"
    backlog_planner_name: str = "deterministic"
    backend_name: str
    build_team_id: str | None = None
    build_team_name: str | None = None
    team_role_agent_ids: dict[str, str] = Field(default_factory=dict)
    selected_agent_id: str | None = None
    selected_agent_name: str | None = None
    selected_agent_role: str = "Execution"
    target_repo_path: str
    build_decision: BuildDecision
    reason: str
    external_execution_enabled: bool = False
    confirm_execution: bool = False
    permission_profile_id: str | None = None
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


class FeishuWriteResult(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    plan_id: str
    ok: bool
    blocked: bool = False
    dry_run: bool = False
    failure_reason: FailureReason | None = None
    reason: str | None = None
    lark_cli_path: str | None = None
    command: str = ""
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    content_path: str | None = None
    document_id: str | None = None
    document_url: str | None = None
    operation_summary: str = ""
    created_at: str = Field(default_factory=utc_now)


class GitHubIntegrationResult(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    operation: str
    ok: bool
    blocked: bool = False
    failure_reason: FailureReason | None = None
    reason: str | None = None
    repo: str | None = None
    issue_number: int | None = None
    issue_url: str | None = None
    pr_number: int | None = None
    pr_url: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    remote_url: str | None = None
    comment_url: str | None = None
    command_summaries: list[str] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class BackendSmokeEvidence(AriadneModel):
    id: str
    backend_name: str
    ticket_id: str
    ticket_key: str
    assignment_id: str
    assignment_status: str
    succeeded: bool
    blocked: bool = False
    blocker: str | None = None
    failure_reason: str | None = None
    execution_result_id: str | None = None
    exit_code: int | None = None
    changed_files: list[str] = Field(default_factory=list)
    test_command: str = ""
    test_exit_code: int | None = None
    review_verdict: str | None = None
    agent_runtime: str = "deterministic"
    backlog_planner_name: str = "deterministic"
    handoff_file: str | None = None
    command_template_env_var: str | None = None
    command_template_set: bool = False
    provider_session_id: str | None = None
    provider_failure_kind: str | None = None
    board_path: str | None = None
    memory_path: str | None = None
    feishu_plan_path: str | None = None
    next_tickets_path: str | None = None
    llm_agent_artifact_paths: list[str] = Field(default_factory=list)
    external_execution_enabled: bool = False
    confirm_execution: bool = False
    created_at: str = Field(default_factory=utc_now)


class LandingArtifactRef(AriadneModel):
    kind: str
    artifact_id: str
    path: str
    summary: str = ""


class LandingTestResult(AriadneModel):
    command: str
    exit_code: int | None = None
    status: str
    output_artifact_path: str | None = None


class LandingEvidence(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    ticket_title: str
    ticket_status: TicketStatus
    backend_name: str
    planner_name: str
    agent_runtime: str = "deterministic"
    backlog_planner_name: str = "deterministic"
    branch: str | None = None
    target_repo_path: str
    worktree_path: str | None = None
    execution_result_id: str
    review_report_id: str
    review_verdict: ReviewVerdict
    changed_files: list[str] = Field(default_factory=list)
    git_diff_summary: dict[str, Any] = Field(default_factory=dict)
    test_results: list[LandingTestResult] = Field(default_factory=list)
    memory_path: str
    board_path: str
    next_tickets_path: str
    feishu_plan_path: str
    orchestrator_result_path: str | None = None
    gate_inputs: dict[str, Any] = Field(default_factory=dict)
    linked_artifacts: list[LandingArtifactRef] = Field(default_factory=list)
    partial: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class LandingGateStatus(str, Enum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class LandingGateCheckStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class LandingGateCheck(AriadneModel):
    name: str
    status: LandingGateCheckStatus
    summary: str
    evidence_ref: str | None = None


class LandingGateReport(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    status: LandingGateStatus
    landing_evidence_id: str | None = None
    landing_evidence_path: str | None = None
    checks: list[LandingGateCheck] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_action: str = "review_landing_gate_report"
    created_at: str = Field(default_factory=utc_now)


class InboxItem(AriadneModel):
    id: str
    source_type: str
    source_id: str
    ticket_id: str | None = None
    ticket_key: str | None = None
    title: str
    summary: str
    severity: InboxSeverity = InboxSeverity.MEDIUM
    status: InboxStatus = InboxStatus.OPEN
    failure_reason: FailureReason | None = None
    evidence_ref: str | None = None
    recommended_action: str = "human_review_required"
    resolution_note: str | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class BuildSkill(AriadneModel):
    id: str
    name: str
    description: str
    applies_to_agent_roles: list[str]
    body_markdown: str
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class BuildSkillMaterialization(AriadneModel):
    skill_name: str
    backend_name: str
    materialization_strategy: str = "local_provider_visible_copy"
    source_skill_path: str
    materialized_skill_path: str | None = None
    provider_skill_dir: str
    included: bool = True
    prompt_injection_warning_count: int = 0
    warning: str | None = None
    requires_confirmation: bool = False
    notes: str = (
        "Local BuildSkill materialization only. Do not write to global Codex or Claude config."
    )


class StoreInvariantIssue(AriadneModel):
    reason: StoreInvariantReason
    severity: StoreInvariantSeverity = StoreInvariantSeverity.ERROR
    path: str
    message: str
    entity_type: str | None = None
    entity_id: str | None = None
    related_entity_id: str | None = None


class StoreInvariantReport(AriadneModel):
    id: str
    root_path: str
    ok: bool
    error_count: int
    warning_count: int
    checked_files: int
    issues: list[StoreInvariantIssue] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class ReleaseEvidencePacket(AriadneModel):
    id: str
    root_path: str
    generated_at: str = Field(default_factory=utc_now)
    git_head: str | None = None
    git_branch: str | None = None
    ticket_count: int = 0
    assignment_count: int = 0
    open_assignment_count: int = 0
    execution_result_count: int = 0
    review_report_count: int = 0
    memory_record_count: int = 0
    inbox_item_count: int = 0
    workdir_count: int = 0
    active_workdir_count: int = 0
    dirty_workdir_count: int = 0
    board_path: str | None = None
    store_invariant_report_path: str | None = None
    store_invariants_ok: bool = False
    store_invariant_errors: int = 0
    store_invariant_warnings: int = 0
    secret_scan_ok: bool = False
    secret_finding_count: int = 0
    runtime_capabilities: list[RuntimeCapability] = Field(default_factory=list)
    latest_review_verdicts: dict[str, str] = Field(default_factory=dict)
    product_readiness_status: str | None = None
    production_acceptance_status: str | None = None
    run_gate_status: str | None = None
    product_readiness_checks: dict[str, str] = Field(default_factory=dict)
    real_success_evidence: dict[str, Any] = Field(default_factory=dict)
    real_failure_evidence: dict[str, Any] = Field(default_factory=dict)
    local_success_evidence: dict[str, Any] = Field(default_factory=dict)
    local_failure_evidence: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: dict[str, str] = Field(default_factory=dict)
