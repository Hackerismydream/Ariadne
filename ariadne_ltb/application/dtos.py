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
    available: bool
    external_execution_enabled: bool
    command_template_set: bool
    confirm_execution_required: bool
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


class WorkbenchDTO(AriadneDTO):
    tickets: list[TicketSummaryDTO]
    assignments: list[AssignmentDTO]
    runtime_capabilities: list[RuntimeCapabilityDTO]
    target_projects: list[TargetProjectDTO]


class RegisterTargetProjectInput(AriadneDTO):
    path: str
    label: str | None = None


class AssignTicketInput(AriadneDTO):
    assignee_id: str
    assignee_kind: Literal["agent", "build_team"] = "build_team"
    backend_name: str | None = None
    planner_name: str | None = None
    agent_runtime: str | None = None
    backlog_planner_name: str | None = None
    target_project_id: str
    idempotency_key: str | None = None


class AssignTicketOutput(AriadneDTO):
    ticket: TicketSummaryDTO
    assignment: AssignmentDTO
    route_decision_artifact_path: str | None = None
    idempotent_replay: bool = False


class RunAssignmentInput(AriadneDTO):
    confirm_execution: bool = False
    runtime_id: str = "local"
    agent_runtime: str | None = None
    backlog_planner: str | None = None
    timeout_seconds: int | None = None
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
    author: str = "human"
    reply_to: str | None = None
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
