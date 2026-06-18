from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AriadneDTO(BaseModel):
    model_config = {"extra": "forbid"}


class TargetProjectDTO(AriadneDTO):
    id: str
    label: str
    available: bool
    disabled_reason: str = ""


class RuntimeCapabilityDTO(AriadneDTO):
    backend_name: str
    display_name: str
    available: bool
    can_assign: bool
    can_run: bool
    fallback_only: bool
    confirm_execution_required: bool
    external_execution_enabled: bool
    command_template_set: bool
    disabled_reasons: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TicketSummaryDTO(AriadneDTO):
    id: str
    key: str
    title: str
    status: str
    source_type: str
    priority: str
    assigned_agent_id: str | None = None
    latest_assignment_id: str | None = None
    latest_execution_result_id: str | None = None
    latest_review_verdict: str | None = None
    build_packet_id: str | None = None
    summary: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    source_ref: str | None = None
    target_project_id: str | None = None


class AssignmentDTO(AriadneDTO):
    id: str
    ticket_id: str
    ticket_key: str
    agent_id: str
    agent_name: str
    backend_name: str | None = None
    status: str
    target_project_id: str | None = None
    created_at: str
    started_at: str | None = None
    ended_at: str | None = None
    blocker: str | None = None
    failure_reason: str | None = None


class ProjectGoalDTO(AriadneDTO):
    id: str
    title: str
    north_star: str
    current_state: str = ""
    target_state: str = ""
    status: Literal["active", "reviewing", "blocked"] = "active"
    target_project_id: str | None = None
    knowledge_inputs: list[str] = Field(default_factory=list)
    feedback_signals: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class SourceDocumentDTO(AriadneDTO):
    id: str
    source_type: str
    title: str
    path_or_url: str
    summary: str
    status: str = "new"
    linked_ticket_count: int = 0
    created_at: str
    evidence_snippets: list[str] = Field(default_factory=list)


class AgentProfileDTO(AriadneDTO):
    id: str
    name: str
    role: str
    backend_name: str | None = None
    planner_name: str
    agent_runtime: str
    backlog_planner_name: str
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    enabled: bool
    run_count: int = 0


class BuildSkillDTO(AriadneDTO):
    id: str
    name: str
    description: str
    applies_to_agent_roles: list[str] = Field(default_factory=list)
    updated_at: str


class InboxItemDTO(AriadneDTO):
    id: str
    source_type: str
    source_id: str
    ticket_id: str | None = None
    ticket_key: str | None = None
    title: str
    summary: str
    severity: str
    status: str
    failure_reason: str | None = None
    evidence_ref: str | None = None
    recommended_action: str
    resolution_note: str | None = None
    repair_ticket_id: str | None = None
    repair_ticket_key: str | None = None
    created_at: str
    updated_at: str


class BacklogOperationDTO(AriadneDTO):
    id: str
    operation_type: str
    reason: str
    ticket_id: str | None = None
    ticket_key: str | None = None
    title: str | None = None
    description: str | None = None
    source_type: str | None = None
    source_ref: str | None = None
    priority: str | None = None
    status: str | None = None
    owner_agent: str | None = None
    build_decision: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class BacklogPreviewDTO(AriadneDTO):
    id: str
    trigger_type: str
    trigger_ref: str
    rationale: str
    operations: list[BacklogOperationDTO] = Field(default_factory=list)
    conflict_count: int = 0
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str
    applied_at: str | None = None
    applied_update_id: str | None = None


class WorkbenchDTO(AriadneDTO):
    schema_version: Literal["ariadne.workbench.v1"] = "ariadne.workbench.v1"
    goals: list[ProjectGoalDTO] = Field(default_factory=list)
    sources: list[SourceDocumentDTO] = Field(default_factory=list)
    tickets: list[TicketSummaryDTO]
    assignments: list[AssignmentDTO]
    agents: list[AgentProfileDTO] = Field(default_factory=list)
    runtime_capabilities: list[RuntimeCapabilityDTO]
    target_projects: list[TargetProjectDTO]
    skills: list[BuildSkillDTO] = Field(default_factory=list)
    inbox: list[InboxItemDTO] = Field(default_factory=list)
    backlog_previews: list[BacklogPreviewDTO] = Field(default_factory=list)


class RegisterTargetProjectInput(AriadneDTO):
    path: str
    label: str | None = None


class CreateProjectGoalInput(AriadneDTO):
    title: str = Field(min_length=1, max_length=200)
    north_star: str = Field(min_length=1, max_length=2000)
    current_state: str = Field(default="", max_length=2000)
    target_state: str = Field(default="", max_length=2000)
    target_project_id: str | None = None
    knowledge_inputs: list[str] = Field(default_factory=list)
    feedback_signals: list[str] = Field(default_factory=list)


class CreateSourceInput(AriadneDTO):
    title: str = Field(min_length=1, max_length=240)
    source_type: Literal["blog", "paper", "github_repo", "github_readme", "note", "manual_note", "repo_note"] = "note"
    path_or_url: str = Field(min_length=1, max_length=2000)
    content: str = Field(default="", max_length=120_000)
    summary: str = Field(default="", max_length=4000)
    evidence_snippets: list[str] = Field(default_factory=list)


class IssueFactoryPreviewInput(AriadneDTO):
    goal_id: str
    source_ids: list[str] = Field(default_factory=list)
    target_project_id: str | None = None


class IssueFactoryApplyOutput(AriadneDTO):
    preview: BacklogPreviewDTO
    created_ticket_ids: list[str] = Field(default_factory=list)
    updated_ticket_ids: list[str] = Field(default_factory=list)
    superseded_ticket_ids: list[str] = Field(default_factory=list)
    already_applied: bool = False


class AssignTicketInput(AriadneDTO):
    assignee_id: str
    assignee_kind: Literal["agent", "build_team"] = "build_team"
    backend_name: str | None = None
    runtime_profile: Literal["auto", "production", "deterministic"] = "production"
    target_project_id: str
    idempotency_key: str | None = None


class AssignTicketOutput(AriadneDTO):
    ticket: TicketSummaryDTO
    assignment: AssignmentDTO
    confirmation_token: str | None = None
    route_decision_artifact_path: str | None = None
    idempotent_replay: bool = False


class RunAssignmentInput(AriadneDTO):
    confirmation_token: str
    timeout_seconds: int | None = Field(default=None, ge=1, le=1800)
    idempotency_key: str | None = None


class RunAssignmentOutput(AriadneDTO):
    assignment: AssignmentDTO
    did_work: bool
    status: str
    message: str
    ticket_run_result: dict[str, Any] | None = None
    idempotent_replay: bool = False


class CreateCommentInput(AriadneDTO):
    body: str
    reply_to: str | None = None
    assignment_id: str | None = None
    idempotency_key: str | None = None


class CommentDTO(AriadneDTO):
    id: str
    ticket_id: str
    ticket_key: str
    author_type: str
    author: str
    kind: str
    body: str
    thread_id: str | None = None
    parent_comment_id: str | None = None
    created_at: str


class TimelineDTO(AriadneDTO):
    ticket: TicketSummaryDTO
    comments: list[CommentDTO]
    runtime_events: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]


class AssignmentEventDTO(AriadneDTO):
    id: str
    source: Literal["assignment", "runtime_event", "run_message", "comment", "artifact"]
    cursor: str
    timestamp: str
    assignment_id: str
    ticket_id: str
    ticket_key: str
    stage: str
    event_type: str
    actor: str
    summary: str
    ref_id: str | None = None


class AssignmentEventsDTO(AriadneDTO):
    assignment: AssignmentDTO
    events: list[AssignmentEventDTO]


class AssignmentEventStreamDTO(AriadneDTO):
    schema_version: Literal["ariadne.assignment-events.v1"] = "ariadne.assignment-events.v1"
    assignment: AssignmentDTO
    events: list[AssignmentEventDTO]
    cursor: str | None = None
    heartbeat: bool = False


class ExecutionEvidenceDTO(AriadneDTO):
    id: str
    ticket_id: str
    backend_name: str
    dry_run: bool
    blocked: bool
    block_reason: str | None = None
    failure_reason: str | None = None
    exit_code: int
    changed_files: list[str] = Field(default_factory=list)
    test_exit_code: int | None = None
    warnings: list[str] = Field(default_factory=list)
    diff_artifact_id: str | None = None
    execution_log_artifact_id: str | None = None


class EvidenceProjectionDTO(AriadneDTO):
    schema_version: Literal["ariadne.evidence-projection.v1"] = "ariadne.evidence-projection.v1"
    execution_results: list[ExecutionEvidenceDTO] = Field(default_factory=list)
