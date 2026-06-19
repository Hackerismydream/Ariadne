export type ApiWorkbench = {
  goals: ApiProjectGoal[];
  sources: ApiSourceDocument[];
  tickets: ApiTicketSummary[];
  assignments: ApiAssignmentSummary[];
  agents: ApiAgentProfile[];
  runtime_capabilities: ApiRuntimeCapability[];
  target_projects: ApiTargetProject[];
  skills: ApiBuildSkill[];
  inbox: ApiInboxItem[];
  backlog_previews: ApiBacklogPreview[];
  daemon_status: ApiDaemonStatus;
};

export type ApiTicketEvidenceBundle = {
  assignment_id?: string | null;
  assignment_status?: string | null;
  assignment_blocker?: string | null;
  assignment_failure_reason?: string | null;
  execution_result_id?: string | null;
  backend_name?: string | null;
  dry_run?: boolean | null;
  blocked?: boolean | null;
  block_reason?: string | null;
  failure_reason?: string | null;
  command?: string | null;
  exit_code?: number | null;
  stdout_excerpt: string;
  stderr_excerpt: string;
  changed_files: string[];
  diff_artifact_id?: string | null;
  diff_artifact_path?: string | null;
  execution_log_artifact_id?: string | null;
  execution_log_artifact_path?: string | null;
  handoff_file?: string | null;
  test_command: string;
  test_exit_code?: number | null;
  test_stdout_excerpt: string;
  test_stderr_excerpt: string;
  review_report_id?: string | null;
  review_verdict?: string | null;
  memory_path?: string | null;
  feishu_plan_path?: string | null;
  next_tickets_path?: string | null;
  warnings: string[];
};

export type ApiTicketSummary = {
  id: string;
  key: string;
  title: string;
  status: string;
  source_type: string;
  priority: string;
  assigned_agent_id?: string | null;
  latest_assignment_id?: string | null;
  latest_execution_result_id?: string | null;
  latest_review_verdict?: string | null;
  build_packet_id?: string | null;
  summary?: string | null;
  acceptance_criteria?: string[];
  affected_modules?: string[];
  source_ref?: string | null;
  target_project_id?: string | null;
  evidence?: ApiTicketEvidenceBundle | null;
};

export type ApiAssignmentSummary = {
  id: string;
  ticket_id: string;
  ticket_key: string;
  agent_id: string;
  agent_name: string;
  backend_name?: string | null;
  status: string;
  target_project_id?: string | null;
  created_at?: string | null;
  blocker?: string | null;
  failure_reason?: string | null;
};

export type ApiRuntimeCapability = {
  backend_name: string;
  display_name: string;
  available: boolean;
  can_assign: boolean;
  can_run: boolean;
  fallback_only: boolean;
  external_execution_enabled: boolean;
  command_template_set: boolean;
  confirm_execution_required: boolean;
  disabled_reasons: string[];
  notes: string[];
};

export type ApiDaemonStatus = {
  runtime_id: string;
  status: string;
  background_running: boolean;
  external_execution_authorized: boolean;
  stale?: boolean | null;
  current_assignment_id?: string | null;
  current_ticket_key?: string | null;
  current_stage?: string | null;
  heartbeat_at?: string | null;
  last_event_id?: string | null;
  last_error?: string | null;
  open_assignment_count: number;
  claimable_assignment_count: number;
  running_assignment_count: number;
  blocked_assignment_count: number;
  last_message: string;
};

export type ApiTargetProject = {
  id: string;
  label: string;
  available: boolean;
  disabled_reason: string;
};

export type ApiProjectGoal = {
  id: string;
  title: string;
  north_star: string;
  current_state: string;
  target_state: string;
  status: "active" | "reviewing" | "blocked";
  target_project_id?: string | null;
  knowledge_inputs: string[];
  feedback_signals: string[];
  created_at: string;
  updated_at: string;
};

export type CreateProjectGoalRequest = {
  title: string;
  north_star: string;
  current_state?: string;
  target_state?: string;
  target_project_id?: string | null;
  knowledge_inputs?: string[];
  feedback_signals?: string[];
};

export type ApiSourceDocument = {
  id: string;
  source_type: string;
  title: string;
  path_or_url: string;
  summary: string;
  status: string;
  linked_ticket_count: number;
  created_at: string;
  evidence_snippets: string[];
};

export type CreateSourceRequest = {
  title: string;
  source_type: "blog" | "paper" | "github_repo" | "github_readme" | "note" | "manual_note" | "repo_note";
  path_or_url: string;
  content?: string;
  summary?: string;
  evidence_snippets?: string[];
};

export type ApiAgentProfile = {
  id: string;
  name: string;
  role: string;
  backend_name?: string | null;
  planner_name: string;
  agent_runtime: string;
  backlog_planner_name: string;
  description: string;
  capabilities: string[];
  enabled: boolean;
  run_count: number;
};

export type ApiBuildSkill = {
  id: string;
  name: string;
  description: string;
  applies_to_agent_roles: string[];
  updated_at: string;
};

export type ApiInboxItem = {
  id: string;
  source_type: string;
  source_id: string;
  ticket_id?: string | null;
  ticket_key?: string | null;
  title: string;
  summary: string;
  severity: string;
  status: string;
  failure_reason?: string | null;
  evidence_ref?: string | null;
  recommended_action: string;
  resolution_note?: string | null;
  repair_ticket_id?: string | null;
  repair_ticket_key?: string | null;
  created_at: string;
  updated_at: string;
};

export type ApiBacklogOperation = {
  id: string;
  operation_type: string;
  reason: string;
  ticket_id?: string | null;
  ticket_key?: string | null;
  title?: string | null;
  description?: string | null;
  source_type?: string | null;
  source_ref?: string | null;
  priority?: string | null;
  status?: string | null;
  owner_agent?: string | null;
  build_decision?: string | null;
  evidence_refs: string[];
};

export type ApiBacklogPreview = {
  id: string;
  trigger_type: string;
  trigger_ref: string;
  rationale: string;
  operations: ApiBacklogOperation[];
  conflict_count: number;
  evidence_refs: string[];
  created_at: string;
  applied_at?: string | null;
  applied_update_id?: string | null;
};

export type IssueFactoryPreviewRequest = {
  goal_id: string;
  source_ids: string[];
  target_project_id?: string | null;
};

export type RegisterTargetProjectRequest = {
  path: string;
  label?: string | null;
};

export type AssignTicketRequest = {
  assignee_id: string;
  assignee_kind: "agent" | "build_team";
  backend_name?: "codex" | "claude-code";
  runtime_profile: "production";
  target_project_id: string;
  idempotency_key?: string;
};

export type RunAssignmentRequest = {
  confirmation_token: string;
  timeout_seconds?: number;
  idempotency_key?: string;
};

export type DaemonStartRequest = {
  runtime_id?: string;
  interval_seconds?: number;
  max_iterations?: number | null;
  timeout_seconds?: number | null;
  external_execution_authorized?: boolean;
};

export type AddTicketCommentRequest = {
  body: string;
  reply_to?: string;
  assignment_id?: string;
  idempotency_key?: string;
};

export type AssignmentEvent = {
  id: string;
  source: "assignment" | "runtime_event" | "run_message" | "comment" | "artifact";
  cursor: string;
  timestamp: string;
  assignment_id: string;
  ticket_id: string;
  ticket_key: string;
  stage: string;
  event_type: string;
  actor: string;
  summary: string;
  ref_id?: string | null;
};

export type AssignmentEventStream = {
  schema_version: "ariadne.assignment-events.v1";
  assignment: ApiAssignmentSummary;
  events: AssignmentEvent[];
  cursor?: string | null;
  heartbeat: boolean;
};
