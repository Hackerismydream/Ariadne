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
    metadata: dict[str, Any] = Field(default_factory=dict)
    local_path: str | None = None
    path_exists: bool = False
    is_git_repo: bool = False
    git_branch: str | None = None
    git_dirty: bool | None = None
    test_command: str | None = None
    issue_prefix: str | None = None
    boundary_role: str = "target_repo"


class ProjectVersionDTO(AriadneDTO):
    id: str
    target_project_id: str
    target_project_label: str | None = None
    target_project: TargetProjectDTO | None = None
    version_label: str
    goal_id: str
    goal_title: str
    goal_north_star: str
    status: str
    created_at: str
    updated_at: str
    selected_at: str | None = None


class EnvironmentBlockerDTO(AriadneDTO):
    code: str
    message: str
    severity: str = "warning"


class WorkbenchEnvironmentDTO(AriadneDTO):
    connection_mode: str = "api"
    execution_mode: str
    read_only: bool = False
    ariadne_root: str
    ariadne_store_path: str
    active_target_project_id: str | None = None
    active_target_project: TargetProjectDTO | None = None
    production_backends_available: list[str] = Field(default_factory=list)
    selected_backend_recommendation: str | None = None
    blockers: list[EnvironmentBlockerDTO] = Field(default_factory=list)


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


class TicketEvidenceBundleDTO(AriadneDTO):
    assignment_id: str | None = None
    assignment_status: str | None = None
    assignment_blocker: str | None = None
    assignment_failure_reason: str | None = None
    execution_result_id: str | None = None
    backend_name: str | None = None
    dry_run: bool | None = None
    blocked: bool | None = None
    block_reason: str | None = None
    failure_reason: str | None = None
    command: str | None = None
    exit_code: int | None = None
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    changed_files: list[str] = Field(default_factory=list)
    diff_artifact_id: str | None = None
    diff_artifact_path: str | None = None
    execution_log_artifact_id: str | None = None
    execution_log_artifact_path: str | None = None
    handoff_file: str | None = None
    test_command: str = ""
    test_exit_code: int | None = None
    test_stdout_excerpt: str = ""
    test_stderr_excerpt: str = ""
    review_report_id: str | None = None
    review_verdict: str | None = None
    memory_path: str | None = None
    feishu_plan_path: str | None = None
    next_tickets_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    current_state: str | None = None
    current_assignment_id: str | None = None
    current_run_id: str | None = None
    current_execution_result_id: str | None = None
    current_review_report_id: str | None = None
    historical_blocker_count: int = 0
    active_blocker_count: int = 0
    superseded_inbox_item_ids: list[str] = Field(default_factory=list)


class DeliveryGateDTO(AriadneDTO):
    id: str
    label: str
    status: str
    detail: str = ""
    ref_id: str | None = None


class LatestRealRunDTO(AriadneDTO):
    ticket_key: str
    assignment_id: str | None = None
    backend_name: str
    execution_result_id: str
    exit_code: int | None = None
    test_exit_code: int | None = None
    review_verdict: str | None = None
    dry_run: bool
    blocked: bool
    terminal_verdict: str = "unknown"
    changed_files: list[str] = Field(default_factory=list)
    preflight_dirty_files: list[str] = Field(default_factory=list)
    handoff_file: str | None = None
    diff_artifact_path: str | None = None
    execution_log_artifact_path: str | None = None
    memory_path: str | None = None
    next_tickets_path: str | None = None


class DeliveryItemDTO(AriadneDTO):
    ticket_id: str
    ticket_key: str
    title: str
    status: str
    priority: str
    target_project_id: str | None = None
    assignment_id: str | None = None
    assignment_status: str | None = None
    backend_name: str | None = None
    route_decision_id: str | None = None
    handoff_packet_id: str | None = None
    build_context_id: str | None = None
    execution_result_id: str | None = None
    dry_run: bool | None = None
    blocked: bool | None = None
    exit_code: int | None = None
    test_command: str | None = None
    test_exit_code: int | None = None
    review_verdict: str | None = None
    memory_path: str | None = None
    feishu_plan_path: str | None = None
    next_tickets_path: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    preflight_dirty_files: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    evidence_status: str = "missing"
    terminal_verdict: str = "unknown"


class ProjectVersionDeliveryDTO(AriadneDTO):
    id: str
    version_label: str
    status: str
    goal_id: str | None = None
    target_project_id: str | None = None
    target_project_label: str | None = None
    current_state: str
    target_state: str
    summary: str
    generated_at: str
    product_closure_status: str = "NOT_CLOSED"
    product_closure_mode: str = "not_attempted"
    product_closure_summary: str = ""
    product_closure_reason: str = ""
    product_closure_packet_path: str | None = None
    product_closure_required_command: str = ""
    progress_counts: dict[str, int] = Field(default_factory=dict)
    gates: list[DeliveryGateDTO] = Field(default_factory=list)
    delivery_items: list[DeliveryItemDTO] = Field(default_factory=list)
    latest_real_run: LatestRealRunDTO | None = None
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


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
    evidence: TicketEvidenceBundleDTO | None = None


class AssignmentDTO(AriadneDTO):
    id: str
    ticket_id: str
    ticket_key: str
    agent_id: str
    agent_name: str
    backend_name: str | None = None
    status: str
    readiness_status: str | None = None
    claimable: bool | None = None
    route_decision_id: str | None = None
    handoff_packet_id: str | None = None
    handoff_hash: str | None = None
    build_context_id: str | None = None
    blocked_reason: str | None = None
    runtime_scope: str | None = None
    target_project_id: str | None = None
    parent_assignment_id: str | None = None
    attempt: int = 1
    retry_reason: str | None = None
    retry_policy: str | None = None
    retry_allowed: bool = False
    retry_blocked_reason: str | None = None
    created_at: str
    started_at: str | None = None
    ended_at: str | None = None
    blocker: str | None = None
    failure_reason: str | None = None


class DaemonStatusDTO(AriadneDTO):
    runtime_id: str = "workbench-local"
    status: str = "unknown"
    background_running: bool = False
    external_execution_authorized: bool = False
    stale: bool | None = None
    current_assignment_id: str | None = None
    current_ticket_key: str | None = None
    current_stage: str | None = None
    heartbeat_at: str | None = None
    last_event_id: str | None = None
    last_error: str | None = None
    open_assignment_count: int = 0
    claimable_assignment_count: int = 0
    running_assignment_count: int = 0
    blocked_assignment_count: int = 0
    last_message: str = ""
    scope: RuntimeScopeDTO | None = None
    queue_preview: QueuePreviewDTO | None = None


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
    source_role: str = "background_knowledge"
    title: str
    path_or_url: str
    summary: str
    status: str = "new"
    analysis_status: str = "pending"
    linked_ticket_count: int = 0
    created_at: str
    evidence_snippets: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    license_risk: str = "unknown"
    origin_bucket: str = "external"
    quality_status: str = "unknown"
    quality_limitations: list[str] = Field(default_factory=list)
    claim_count: int = 0


class SourceArtifactDTO(AriadneDTO):
    id: str
    source_document_id: str
    artifact_type: str
    payload_hash: str
    payload_path: str
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: str


class SourceEvidenceDTO(AriadneDTO):
    id: str
    source_document_id: str
    artifact_id: str | None = None
    locator: str
    quote_or_summary: str
    claim: str
    confidence: float
    content_hash: str
    created_at: str


class SourceEvidenceItemDTO(AriadneDTO):
    locator: str
    summary: str
    claim: str
    confidence_label: str


class SourceUnderstandingDTO(AriadneDTO):
    source_id: str
    display_title: str
    kind_label: str
    role_label: str
    analysis_label: str
    license_risk_label: str = "未知"
    what_ariadne_understood: list[str] = Field(default_factory=list)
    evidence_items: list[SourceEvidenceItemDTO] = Field(default_factory=list)
    generated_outputs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    impacted_ticket_keys: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class SourceInputEventDTO(AriadneDTO):
    id: str
    source_id: str
    event_type: str
    label: str
    created_at: str


class SourceNextActionDTO(AriadneDTO):
    id: str
    label: str
    enabled: bool = True
    reason: str = ""
    target_route: str | None = None
    api_action: str | None = None


class SourceLifecycleDTO(AriadneDTO):
    source_id: str
    status: str
    label: str
    detail: str
    terminal: bool
    ready_for_issue_factory: bool
    blocker: str | None = None
    updated_at: str
    next_actions: list[SourceNextActionDTO] = Field(default_factory=list)


class SourceTypedArtifactDTO(AriadneDTO):
    id: str
    kind: str
    label: str
    summary: str
    payload_path: str | None = None
    payload_hash: str | None = None
    evidence_count: int = 0
    key_fields: dict[str, Any] = Field(default_factory=dict)


class ProjectInputDetailDTO(AriadneDTO):
    source: SourceDocumentDTO
    lifecycle: SourceLifecycleDTO
    understanding: SourceUnderstandingDTO | None = None
    artifacts: list[SourceTypedArtifactDTO] = Field(default_factory=list)
    evidence: list[SourceEvidenceItemDTO] = Field(default_factory=list)
    impacted_ticket_keys: list[str] = Field(default_factory=list)


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


class AgentRuntimeProfileDTO(AriadneDTO):
    profile_id: str
    agent_id: str
    backend: str
    model: str | None = None
    working_directory: str | None = None
    environment_keys: list[str] = Field(default_factory=list)
    reasoning_level: str | None = None
    service_tier: str | None = None


class AgentVisibilityDTO(AriadneDTO):
    agent_id: str
    visible: bool = True
    team_ids: list[str] = Field(default_factory=list)


class AgentCreateInput(AriadneDTO):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    backend: Literal["codex", "claude-code"] = "codex"
    model: str | None = Field(default=None, max_length=120)
    working_directory: str | None = Field(default=None, max_length=1000)
    environment_keys: list[str] = Field(default_factory=list)
    reasoning_level: str | None = Field(default=None, max_length=80)
    service_tier: str | None = Field(default=None, max_length=80)
    instructions: str = Field(default="", max_length=8000)
    skill_ids: list[str] = Field(default_factory=list)
    visible: bool = True
    team_ids: list[str] = Field(default_factory=list)
    max_concurrent_assignments: int = Field(default=1, ge=1, le=10)


class AgentUpdateInput(AriadneDTO):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    status: Literal["active", "paused", "archived"] | None = None
    model: str | None = Field(default=None, max_length=120)
    working_directory: str | None = Field(default=None, max_length=1000)
    environment_keys: list[str] | None = None
    reasoning_level: str | None = Field(default=None, max_length=80)
    service_tier: str | None = Field(default=None, max_length=80)
    instructions: str | None = Field(default=None, max_length=8000)
    skill_ids: list[str] | None = None
    visible: bool | None = None
    team_ids: list[str] | None = None
    max_concurrent_assignments: int | None = Field(default=None, ge=1, le=10)


class BuildSkillDTO(AriadneDTO):
    id: str
    name: str
    description: str
    applies_to_agent_roles: list[str] = Field(default_factory=list)
    updated_at: str


class AgentListItemDTO(AriadneDTO):
    id: str
    name: str
    role: str
    backend_name: str | None = None
    runtime_compatibility: str
    active_assignment_count: int = 0
    blocked_count: int = 0
    description: str = ""
    avatar_seed: str = ""
    status: str = "active"
    runtime_profile: AgentRuntimeProfileDTO | None = None
    visibility: AgentVisibilityDTO | None = None
    skill_ids: list[str] = Field(default_factory=list)
    instructions_present: bool = False
    updated_at: str
    configuration: dict[str, Any] = Field(default_factory=dict)


class AgentDetailDTO(AgentListItemDTO):
    instructions: str = ""
    environment_keys: list[str] = Field(default_factory=list)


class AgentActivityItemDTO(AriadneDTO):
    id: str
    timestamp: str
    source: str
    event_type: str
    stage: str
    summary: str
    ticket_id: str | None = None
    ticket_key: str | None = None
    assignment_id: str | None = None
    run_id: str | None = None
    ref_id: str | None = None


class AgentTaskItemDTO(AriadneDTO):
    assignment: AssignmentDTO
    task_id: str
    ticket_id: str
    ticket_key: str
    agent_id: str
    status: str
    attempt_number: int = 1
    retry_count: int = 0
    blocker_id: str | None = None
    blocker_reason: str | None = None
    claimed_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    current: bool = False


class AgentRunItemDTO(AriadneDTO):
    id: str
    ticket_id: str
    ticket_key: str | None = None
    agent_name: str
    agent_role: str
    status: str
    lifecycle_state: str
    backend_name: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    failure_reason: str | None = None
    error: str | None = None
    assignment_id: str | None = None


class AgentListResponse(AriadneDTO):
    schema_version: Literal["ariadne.team-agents.v1"] = "ariadne.team-agents.v1"
    source: Literal["agent_definition_store"] = "agent_definition_store"
    agents: list[AgentListItemDTO] = Field(default_factory=list)


class AgentDetailResponse(AriadneDTO):
    schema_version: Literal["ariadne.team.agent_detail.v1"] = "ariadne.team.agent_detail.v1"
    source: Literal["agent_definition_store"] = "agent_definition_store"
    agent: AgentDetailDTO


class AgentActivityResponse(AriadneDTO):
    schema_version: Literal["ariadne.team.agent_activity.v1"] = "ariadne.team.agent_activity.v1"
    source: Literal["journal_assignments_runs"] = "journal_assignments_runs"
    activity: list[AgentActivityItemDTO] = Field(default_factory=list)


class AgentTasksResponse(AriadneDTO):
    schema_version: Literal["ariadne.team.agent_tasks.v1"] = "ariadne.team.agent_tasks.v1"
    source: Literal["assignments"] = "assignments"
    tasks: list[AgentTaskItemDTO] = Field(default_factory=list)


class AgentRunsResponse(AriadneDTO):
    schema_version: Literal["ariadne.team.agent_runs.v1"] = "ariadne.team.agent_runs.v1"
    source: Literal["runs"] = "runs"
    runs: list[AgentRunItemDTO] = Field(default_factory=list)


class AgentSkillsResponse(AriadneDTO):
    schema_version: Literal["ariadne.team.agent_skills.v1"] = "ariadne.team.agent_skills.v1"
    source: Literal["agent_definition_store_and_build_skills"] = "agent_definition_store_and_build_skills"
    skill_ids: list[str] = Field(default_factory=list)
    skills: list[BuildSkillDTO] = Field(default_factory=list)


class AgentInstructionsResponse(AriadneDTO):
    schema_version: Literal["ariadne.team.agent_instructions.v1"] = "ariadne.team.agent_instructions.v1"
    source: Literal["agent_definition_store"] = "agent_definition_store"
    instructions: str = ""


class AgentEnvironmentResponse(AriadneDTO):
    schema_version: Literal["ariadne.team.agent_environment.v1"] = "ariadne.team.agent_environment.v1"
    source: Literal["agent_definition_store"] = "agent_definition_store"
    environment_keys: list[str] = Field(default_factory=list)


class InboxItemDTO(AriadneDTO):
    id: str
    source_type: str
    source_id: str
    ticket_id: str | None = None
    ticket_key: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
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
    active: bool = True
    current_state: str | None = None
    archive_reason: str | None = None
    superseded_by_ref: str | None = None
    recovery_class: str = "human_required"
    primary_action: str = "manual_review"
    allowed_actions: list[str] = Field(default_factory=list)
    linked_assignment_id: str | None = None
    retry_assignment_id: str | None = None
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
    affected_modules: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)
    build_context_id: str | None = None
    target_project_id: str | None = None
    project_version_id: str | None = None
    target_project_label: str | None = None
    target_project_path: str | None = None
    target_repo_path: str | None = None
    target_project_identity: dict[str, Any] = Field(default_factory=dict)
    compiler_provenance: dict[str, Any] = Field(default_factory=dict)
    codebase_snapshot_artifact_id: str | None = None
    codebase_snapshot_status: str = "missing"
    codebase_snapshot_reason: str | None = None
    source_claim_trace: list[dict[str, Any]] = Field(default_factory=list)
    affected_module_rationale: str = ""
    acceptance_criteria_rationale: str = ""
    goal_reason: str | None = None
    change_intent: str = "add"
    target_version_label: str | None = None
    existing_ticket_key: str | None = None
    before_snapshot: dict[str, Any] = Field(default_factory=dict)
    after_summary: str = ""
    confidence: float = 0.75
    decision_reason: str = ""
    included: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    base_ticket_fingerprint: str | None = None
    context_fingerprint: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)
    target_project_id: str | None = None
    project_version_id: str | None = None
    target_project_label: str | None = None
    target_project_path: str | None = None
    target_repo_path: str | None = None
    target_project_identity: dict[str, Any] = Field(default_factory=dict)
    compiler_provenance: dict[str, Any] = Field(default_factory=dict)
    codebase_snapshot_artifact_id: str | None = None
    codebase_snapshot_status: str = "missing"
    codebase_snapshot_reason: str | None = None
    target_version_label: str | None = None
    stale: bool = False
    stale_reason: str = ""


class IssueChildDTO(AriadneDTO):
    ticket_id: str
    ticket_key: str
    title: str
    issue_class: str
    origin: str
    status: str
    parent_ticket_key: str | None = None
    root_ticket_key: str
    reason: str = ""


class IssueFamilyDTO(AriadneDTO):
    ticket_id: str
    ticket_key: str
    title: str
    status: str
    priority: str
    root_ticket_key: str
    repair_count: int = 0
    open_repair_count: int = 0
    history_count: int = 0
    child_ticket_keys: list[str] = Field(default_factory=list)
    latest_repair_summary: str | None = None


class IssueProjectionDTO(AriadneDTO):
    summary: dict[str, int] = Field(default_factory=dict)
    mainline_tickets: list[IssueFamilyDTO] = Field(default_factory=list)
    repair_items: list[IssueChildDTO] = Field(default_factory=list)
    history_items: list[IssueChildDTO] = Field(default_factory=list)


class IssueListItemDTO(AriadneDTO):
    id: str
    key: str
    title: str
    status: str
    priority: str
    assignee: str | None = None
    project: str | None = None
    target_project_id: str | None = None
    project_version_id: str | None = None
    target_project_label: str | None = None
    target_project_path: str | None = None
    target_repo_path: str | None = None
    target_version: str | None = None
    build_context_id: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)
    source_evidence_refs: list[str] = Field(default_factory=list)
    source_count: int = 0
    evidence_count: int = 0
    last_run_status: str | None = None
    terminal_verdict: str = "unknown"
    review_verdict: str | None = None
    blocked_reason: str | None = None
    updated_at: str


class IssueExecutionResultSummaryDTO(AriadneDTO):
    id: str
    backend_name: str
    blocked: bool = False
    failure_reason: str | None = None
    exit_code: int | None = None
    test_exit_code: int | None = None
    changed_files: list[str] = Field(default_factory=list)
    preflight_dirty_files: list[str] = Field(default_factory=list)
    terminal_verdict: str = "unknown"
    diff_artifact_path: str | None = None
    execution_log_artifact_path: str | None = None
    started_at: str | None = None
    ended_at: str | None = None


class IssueEvidenceItemDTO(AriadneDTO):
    id: str
    category: str
    label: str
    ref_type: str
    ref_id: str | None = None
    path_or_url: str | None = None
    validity: str
    reason: str = ""
    summary: str = ""
    excerpt: str = ""
    assignment_id: str | None = None
    execution_result_id: str | None = None
    created_at: str | None = None


class IssueEvidenceSectionDTO(AriadneDTO):
    category: str
    label: str
    items: list[IssueEvidenceItemDTO] = Field(default_factory=list)


class IssueEvidenceDetailResponse(AriadneDTO):
    schema_version: Literal["ariadne.issue-evidence.v1"] = "ariadne.issue-evidence.v1"
    issue_key: str
    evidence: IssueEvidenceItemDTO
    content_excerpt: str = ""
    source: str = "build_ticket_projection"


class IssueTimelineEventDTO(AriadneDTO):
    id: str
    event_type: str
    actor: str
    summary: str
    timestamp: str
    ref_id: str | None = None


class IssueDetailDTO(IssueListItemDTO):
    body: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    target_project_identity: dict[str, Any] = Field(default_factory=dict)
    compiler_provenance: dict[str, Any] = Field(default_factory=dict)
    codebase_snapshot_artifact_id: str | None = None
    codebase_snapshot_status: str = "missing"
    codebase_snapshot_reason: str | None = None
    source_claim_trace: list[dict[str, Any]] = Field(default_factory=list)
    affected_module_rationale: str = ""
    acceptance_criteria_rationale: str = ""
    comments: list[CommentDTO] = Field(default_factory=list)
    timeline: list[IssueTimelineEventDTO] = Field(default_factory=list)
    assignments: list[AssignmentDTO] = Field(default_factory=list)
    execution_results: list[IssueExecutionResultSummaryDTO] = Field(default_factory=list)
    source_links: list[str] = Field(default_factory=list)
    route_decision: dict[str, Any] | None = None
    handoff: dict[str, Any] | None = None
    diff_summary: str | None = None
    test_summary: str | None = None
    review_summary: str | None = None
    next_issue_links: list[str] = Field(default_factory=list)
    evidence_sections: list[IssueEvidenceSectionDTO] = Field(default_factory=list)


class IssueListResponse(AriadneDTO):
    schema_version: Literal["ariadne.issues.v1"] = "ariadne.issues.v1"
    issues: list[IssueListItemDTO] = Field(default_factory=list)
    scope: str = "current_version_mainline"
    source: str = "build_ticket_projection"


class IssueDetailResponse(AriadneDTO):
    schema_version: Literal["ariadne.issue-detail.v1"] = "ariadne.issue-detail.v1"
    issue: IssueDetailDTO
    source: str = "build_ticket_projection"


class IssuePatchInput(AriadneDTO):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    status: str | None = None
    priority: str | None = Field(default=None, max_length=40)


class InboxListItemDTO(AriadneDTO):
    id: str
    issue_key: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    linked_assignment_id: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    canonical_blocker_id: str | None = None
    failure_reason: str
    severity: str
    action_type: str
    allowed_actions: list[str] = Field(default_factory=list)
    primary_action: str | None = None
    recovery_class: str | None = None
    created_at: str
    status: str
    resolution_note: str | None = None


class InboxListResponse(AriadneDTO):
    schema_version: Literal["ariadne.inbox.v1"] = "ariadne.inbox.v1"
    inbox: list[InboxListItemDTO] = Field(default_factory=list)
    source: str = "inbox_projection"


class AgentTaskSnapshotDTO(AriadneDTO):
    active_assignment: str | None = None
    current_issue_key: str | None = None
    backend: str | None = None
    queued_count: int = 0
    blocked_count: int = 0
    heartbeat: str | None = None
    last_event: str | None = None


class AgentTaskSnapshotResponse(AriadneDTO):
    schema_version: Literal["ariadne.agent-task-snapshot.v1"] = "ariadne.agent-task-snapshot.v1"
    snapshot: AgentTaskSnapshotDTO
    source: str = "assignment_daemon_projection"


class ProjectListResponse(AriadneDTO):
    schema_version: Literal["ariadne.projects.v1"] = "ariadne.projects.v1"
    projects: list[TargetProjectDTO] = Field(default_factory=list)
    source: str = "project_resource_projection"


class ProjectDetailResponse(AriadneDTO):
    schema_version: Literal["ariadne.project-detail.v1"] = "ariadne.project-detail.v1"
    project: TargetProjectDTO
    source: str = "project_resource_projection"


class BuildTeamListItemDTO(AriadneDTO):
    id: str
    name: str
    description: str = ""
    lead_agent_id: str
    implementer_agent_id: str
    reviewer_agent_id: str
    default_backend_name: str
    skill_refs: list[str] = Field(default_factory=list)
    enabled: bool = True


class BuildTeamListResponse(AriadneDTO):
    schema_version: Literal["ariadne.build-teams.v1"] = "ariadne.build-teams.v1"
    build_teams: list[BuildTeamListItemDTO] = Field(default_factory=list)
    source: str = "build_team_projection"


class SkillListResponse(AriadneDTO):
    schema_version: Literal["ariadne.team-skills.v1"] = "ariadne.team-skills.v1"
    skills: list[BuildSkillDTO] = Field(default_factory=list)
    source: str = "build_skill_projection"


class RuntimeListItemDTO(AriadneDTO):
    runtime_id: str
    backend_name: str
    display_name: str
    daemon_state: str
    available: bool
    can_assign: bool
    can_run: bool
    external_execution_enabled: bool
    command_template_set: bool
    queue_depth: int = 0
    active_assignment: str | None = None
    disabled_reasons: list[str] = Field(default_factory=list)


class RuntimeListResponse(AriadneDTO):
    schema_version: Literal["ariadne.runs-runtimes.v1"] = "ariadne.runs-runtimes.v1"
    runtimes: list[RuntimeListItemDTO] = Field(default_factory=list)
    source: str = "runtime_capability_projection"


class AssignmentListResponse(AriadneDTO):
    schema_version: Literal["ariadne.runs-assignments.v1"] = "ariadne.runs-assignments.v1"
    assignments: list[AssignmentDTO] = Field(default_factory=list)
    source: str = "assignment_projection"


class ArtifactRefDTO(AriadneDTO):
    id: str
    artifact_type: str
    path: str | None = None
    summary: str = ""
    created_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentActivityDTO(AriadneDTO):
    id: str
    ticket_id: str | None = None
    ticket_key: str | None = None
    assignment_id: str | None = None
    run_id: str | None = None
    agent_name: str
    stage: str
    event_type: str
    summary: str
    timestamp: str
    ref_id: str | None = None


class AgentWorkflowStepDTO(AriadneDTO):
    id: str
    ticket_id: str
    ticket_key: str
    sequence: int
    agent_name: str
    agent_role: str
    step_kind: str
    status: str
    input_refs: list[ArtifactRefDTO] = Field(default_factory=list)
    output_refs: list[ArtifactRefDTO] = Field(default_factory=list)
    assignment_id: str | None = None
    run_id: str | None = None
    handoff_id: str | None = None
    next_agent: str | None = None
    next_action: str = ""
    latest_activity: AgentActivityDTO | None = None
    blocked_reason: str | None = None


class RuntimeScopeDTO(AriadneDTO):
    mode: str = "paused"
    target_project_id: str | None = None
    ticket_id: str | None = None
    assignment_id: str | None = None
    allowed_backends: list[str] = Field(default_factory=list)


class QueuePreviewDTO(AriadneDTO):
    current: AssignmentDTO | None = None
    same_ticket_ready: list[AssignmentDTO] = Field(default_factory=list)
    same_project_ready: list[AssignmentDTO] = Field(default_factory=list)
    out_of_scope_ready_count: int = 0


class WorkbenchDTO(AriadneDTO):
    schema_version: Literal["ariadne.workbench.v1"] = "ariadne.workbench.v1"
    goals: list[ProjectGoalDTO] = Field(default_factory=list)
    project_versions: list[ProjectVersionDTO] = Field(default_factory=list)
    current_project_version: ProjectVersionDTO | None = None
    sources: list[SourceDocumentDTO] = Field(default_factory=list)
    source_artifacts: list[SourceArtifactDTO] = Field(default_factory=list)
    source_evidence: list[SourceEvidenceDTO] = Field(default_factory=list)
    source_understandings: list[SourceUnderstandingDTO] = Field(default_factory=list)
    source_events: list[SourceInputEventDTO] = Field(default_factory=list)
    tickets: list[TicketSummaryDTO]
    assignments: list[AssignmentDTO]
    agents: list[AgentProfileDTO] = Field(default_factory=list)
    runtime_capabilities: list[RuntimeCapabilityDTO]
    target_projects: list[TargetProjectDTO]
    skills: list[BuildSkillDTO] = Field(default_factory=list)
    inbox: list[InboxItemDTO] = Field(default_factory=list)
    backlog_previews: list[BacklogPreviewDTO] = Field(default_factory=list)
    daemon_status: DaemonStatusDTO = Field(default_factory=DaemonStatusDTO)
    environment: WorkbenchEnvironmentDTO | None = None
    current_version_delivery: ProjectVersionDeliveryDTO | None = None
    project_inputs: list[ProjectInputDetailDTO] = Field(default_factory=list)
    issue_projection: IssueProjectionDTO | None = None
    agent_workflows: list[AgentWorkflowStepDTO] = Field(default_factory=list)
    agent_activities: list[AgentActivityDTO] = Field(default_factory=list)


class RegisterTargetProjectInput(AriadneDTO):
    path: str
    label: str | None = None
    create_if_missing: bool = False
    init_git: bool = False
    test_command: str | None = None
    issue_prefix: str | None = None


class CreateProjectVersionInput(AriadneDTO):
    target_project_id: str | None = None
    target_repo_path: str | None = None
    target_repo_label: str | None = None
    create_if_missing: bool = False
    init_git: bool = False
    test_command: str | None = None
    issue_prefix: str | None = None
    version_label: str = Field(default="v0.1", min_length=1, max_length=80)
    goal_title: str = Field(min_length=1, max_length=200)
    goal_north_star: str = Field(min_length=1, max_length=2000)
    target_state: str = Field(default="", max_length=2000)


class SelectProjectVersionInput(AriadneDTO):
    version_id: str


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
    source_type: Literal[
        "blog",
        "paper",
        "github_repo",
        "github_readme",
        "note",
        "manual_note",
        "repo_note",
        "local_markdown",
        "local_folder",
        "target_codebase",
    ] = "note"
    source_role: Literal[
        "reference_project",
        "requirement_source",
        "background_knowledge",
        "design_constraint",
        "implementation_example",
        "target_codebase",
    ] = "background_knowledge"
    path_or_url: str = Field(min_length=1, max_length=2000)
    content: str = Field(default="", max_length=120_000)
    summary: str = Field(default="", max_length=4000)
    evidence_snippets: list[str] = Field(default_factory=list)
    auto_analyze: bool = False


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
    confirmation_token: str = ""
    timeout_seconds: int | None = Field(default=None, ge=1, le=1800)
    idempotency_key: str | None = None


class RunAssignmentOutput(AriadneDTO):
    assignment: AssignmentDTO
    did_work: bool
    status: str
    message: str
    ticket_run_result: dict[str, Any] | None = None
    idempotent_replay: bool = False


class DaemonStartInput(AriadneDTO):
    runtime_id: str = "workbench-local"
    interval_seconds: float = Field(default=2.0, ge=0.2, le=60.0)
    max_iterations: int | None = Field(default=None, ge=1, le=10_000)
    timeout_seconds: int | None = Field(default=None, ge=1, le=1800)
    external_execution_authorized: bool = False
    allowed_assignment_id: str | None = None
    target_project_id: str | None = None
    allowed_backends: list[str] = Field(default_factory=list)
    scope_mode: Literal["assignment", "ticket", "project", "paused"] = "assignment"


class DaemonControlOutput(AriadneDTO):
    daemon: DaemonStatusDTO
    did_work: bool = False
    assignment: AssignmentDTO | None = None
    status: str = "no_work"
    message: str = ""
    ticket_run_result: dict[str, Any] | None = None


class CreateCommentInput(AriadneDTO):
    body: str
    reply_to: str | None = None
    assignment_id: str | None = None
    idempotency_key: str | None = None


class InboxActionInput(AriadneDTO):
    note: str = Field(default="", max_length=2000)
    priority: str = Field(default="high", max_length=40)
    reason: str = Field(default="", max_length=2000)
    force: bool = False


class InboxActionOutput(AriadneDTO):
    inbox_item: "InboxItemDTO"
    action: str
    message: str = ""
    ticket: "TicketSummaryDTO | None" = None
    assignment: "AssignmentDTO | None" = None
    already_exists: bool = False


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
