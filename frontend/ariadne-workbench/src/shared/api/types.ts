export type ApiWorkbench = {
  goals: ApiProjectGoal[];
  project_versions: ApiProjectVersion[];
  current_project_version?: ApiProjectVersion | null;
  sources: ApiSourceDocument[];
  source_artifacts: ApiSourceArtifact[];
  source_evidence: ApiSourceEvidence[];
  source_understandings: ApiSourceUnderstanding[];
  source_events: ApiSourceInputEvent[];
  tickets: ApiTicketSummary[];
  assignments: ApiAssignmentSummary[];
  agents: ApiAgentProfile[];
  runtime_capabilities: ApiRuntimeCapability[];
  target_projects: ApiTargetProject[];
  skills: ApiBuildSkill[];
  inbox: ApiInboxItem[];
  backlog_previews: ApiBacklogPreview[];
  daemon_status: ApiDaemonStatus;
  environment?: ApiWorkbenchEnvironment | null;
  current_version_delivery?: ApiProjectVersionDelivery | null;
  project_inputs?: ApiProjectInputDetail[];
  issue_projection?: ApiIssueProjection | null;
  agent_workflows?: ApiAgentWorkflowStep[];
  agent_activities?: ApiAgentActivity[];
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
  current_state?: string | null;
  current_assignment_id?: string | null;
  current_run_id?: string | null;
  current_execution_result_id?: string | null;
  current_review_report_id?: string | null;
  historical_blocker_count?: number;
  active_blocker_count?: number;
  superseded_inbox_item_ids?: string[];
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
  readiness_status?: string | null;
  claimable?: boolean | null;
  route_decision_id?: string | null;
  handoff_packet_id?: string | null;
  handoff_hash?: string | null;
  build_context_id?: string | null;
  blocked_reason?: string | null;
  runtime_scope?: string | null;
  target_project_id?: string | null;
  parent_assignment_id?: string | null;
  attempt?: number | null;
  retry_reason?: string | null;
  retry_policy?: string | null;
  retry_allowed?: boolean;
  retry_blocked_reason?: string | null;
  created_at?: string | null;
  blocker?: string | null;
  failure_reason?: string | null;
};

export type ApiIssueExecutionResultSummary = {
  id: string;
  backend_name: string;
  blocked: boolean;
  failure_reason?: string | null;
  exit_code?: number | null;
  test_exit_code?: number | null;
  changed_files: string[];
  preflight_dirty_files?: string[];
  terminal_verdict?: string;
  diff_artifact_path?: string | null;
  execution_log_artifact_path?: string | null;
  started_at: string;
  ended_at: string;
};

export type ApiIssueEvidenceItem = {
  id: string;
  category: string;
  label: string;
  ref_type: string;
  ref_id?: string | null;
  path_or_url?: string | null;
  validity: string;
  reason: string;
  summary: string;
  excerpt: string;
  assignment_id?: string | null;
  execution_result_id?: string | null;
  created_at?: string | null;
};

export type ApiIssueEvidenceSection = {
  category: string;
  label: string;
  items: ApiIssueEvidenceItem[];
};

export type ApiIssueEvidenceDetailResponse = {
  schema_version: "ariadne.issue-evidence.v1";
  issue_key: string;
  evidence: ApiIssueEvidenceItem;
  content_excerpt: string;
  source: string;
};

export type ApiIssueTimelineEvent = {
  id: string;
  event_type: string;
  actor: string;
  summary: string;
  timestamp: string;
  ref_id?: string | null;
};

export type ApiIssueComment = {
  id: string;
  ticket_id: string;
  ticket_key: string;
  author: string;
  author_type: string;
  kind: string;
  body: string;
  created_at: string;
  thread_id?: string | null;
  payload_ref?: string | null;
};

export type ApiIssueListItem = {
  id: string;
  key: string;
  title: string;
  status: string;
  priority: string;
  assignee?: string | null;
  project?: string | null;
  target_project_id?: string | null;
  project_version_id?: string | null;
  target_project_label?: string | null;
  target_project_path?: string | null;
  target_repo_path?: string | null;
  target_version?: string | null;
  build_context_id?: string | null;
  source_document_ids?: string[];
  source_artifact_ids?: string[];
  source_evidence_refs?: string[];
  source_count: number;
  evidence_count: number;
  last_run_status?: string | null;
  terminal_verdict?: string;
  review_verdict?: string | null;
  blocked_reason?: string | null;
  updated_at: string;
};

export type ApiIssueDetail = ApiIssueListItem & {
  body: string;
  acceptance_criteria: string[];
  affected_modules: string[];
  target_project_identity?: Record<string, unknown>;
  compiler_provenance?: Record<string, unknown>;
  codebase_snapshot_artifact_id?: string | null;
  codebase_snapshot_status?: string;
  codebase_snapshot_reason?: string | null;
  source_claim_trace?: Array<Record<string, unknown>>;
  affected_module_rationale?: string;
  acceptance_criteria_rationale?: string;
  comments: ApiIssueComment[];
  timeline: ApiIssueTimelineEvent[];
  assignments: ApiAssignmentSummary[];
  execution_results: ApiIssueExecutionResultSummary[];
  source_links: string[];
  route_decision?: Record<string, unknown> | null;
  handoff?: Record<string, unknown> | null;
  diff_summary?: string | null;
  test_summary?: string | null;
  review_summary?: string | null;
  next_issue_links: string[];
  evidence_sections: ApiIssueEvidenceSection[];
};

export type ApiIssueListResponse = {
  schema_version: string;
  source: string;
  issues: ApiIssueListItem[];
};

export type ApiIssueDetailResponse = {
  schema_version: string;
  issue: ApiIssueDetail;
};

export type ApiIssueAssignResponse = {
  ticket: ApiTicketSummary;
  assignment: ApiAssignmentSummary;
  confirmation_token?: string | null;
  route_decision_artifact_path?: string | null;
  idempotent_replay?: boolean;
};

export type ApiIssueRunResponse = {
  assignment?: ApiAssignmentSummary | null;
  did_work?: boolean;
  status: string;
  message: string;
  ticket_run_result?: Record<string, unknown> | null;
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
  scope?: ApiRuntimeScope | null;
  queue_preview?: ApiQueuePreview | null;
};

export type ApiRuntimeScope = {
  mode: string;
  target_project_id?: string | null;
  ticket_id?: string | null;
  assignment_id?: string | null;
  allowed_backends: string[];
};

export type ApiQueuePreview = {
  current?: ApiAssignmentSummary | null;
  same_ticket_ready: ApiAssignmentSummary[];
  same_project_ready: ApiAssignmentSummary[];
  out_of_scope_ready_count: number;
};

export type ApiTargetProject = {
  id: string;
  label: string;
  available: boolean;
  disabled_reason: string;
  metadata?: Record<string, unknown>;
  local_path?: string | null;
  path_exists?: boolean;
  is_git_repo?: boolean;
  git_branch?: string | null;
  git_dirty?: boolean | null;
  test_command?: string | null;
  issue_prefix?: string | null;
  boundary_role?: string;
};

export type ApiProjectVersion = {
  id: string;
  target_project_id: string;
  target_project_label?: string | null;
  target_project?: ApiTargetProject | null;
  version_label: string;
  goal_id: string;
  goal_title: string;
  goal_north_star: string;
  status: string;
  created_at: string;
  updated_at: string;
  selected_at?: string | null;
};

export type ApiEnvironmentBlocker = {
  code: string;
  message: string;
  severity: string;
};

export type ApiWorkbenchEnvironment = {
  connection_mode: string;
  execution_mode: string;
  read_only: boolean;
  ariadne_root: string;
  ariadne_store_path: string;
  active_target_project_id?: string | null;
  active_target_project?: ApiTargetProject | null;
  production_backends_available: string[];
  selected_backend_recommendation?: string | null;
  blockers: ApiEnvironmentBlocker[];
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
  source_role: string;
  title: string;
  path_or_url: string;
  summary: string;
  status: string;
  analysis_status: string;
  linked_ticket_count: number;
  created_at: string;
  evidence_snippets: string[];
  artifact_ids: string[];
  license_risk: string;
  origin_bucket: string;
  quality_status: string;
  quality_limitations: string[];
  claim_count: number;
};

export type ApiSourceArtifact = {
  id: string;
  source_document_id: string;
  artifact_type: "knowledge_card" | "text_understanding" | "reference_project_profile" | "repository_understanding" | "codebase_snapshot" | "target_codebase_snapshot" | "execution_feedback" | "review_feedback";
  payload_hash: string;
  payload_path: string;
  evidence_ids: string[];
  created_at: string;
};

export type ApiSourceEvidence = {
  id: string;
  source_document_id: string;
  artifact_id?: string | null;
  locator: string;
  quote_or_summary: string;
  claim: string;
  confidence: number;
  content_hash: string;
  created_at: string;
};

export type ApiSourceEvidenceItem = {
  locator: string;
  summary: string;
  claim: string;
  confidence_label: string;
};

export type ApiSourceUnderstanding = {
  source_id: string;
  display_title: string;
  kind_label: string;
  role_label: string;
  analysis_label: string;
  license_risk_label: string;
  what_ariadne_understood: string[];
  evidence_items: ApiSourceEvidenceItem[];
  generated_outputs: string[];
  risks: string[];
  impacted_ticket_keys: string[];
  next_actions: string[];
};

export type ApiSourceInputEvent = {
  id: string;
  source_id: string;
  event_type: string;
  label: string;
  created_at: string;
};

export type ApiSourceNextAction = {
  id: string;
  label: string;
  enabled: boolean;
  reason: string;
  target_route?: string | null;
  api_action?: string | null;
};

export type ApiSourceLifecycle = {
  source_id: string;
  status: string;
  label: string;
  detail: string;
  terminal: boolean;
  ready_for_issue_factory: boolean;
  blocker?: string | null;
  updated_at: string;
  next_actions: ApiSourceNextAction[];
};

export type ApiSourceTypedArtifact = {
  id: string;
  kind: string;
  label: string;
  summary: string;
  payload_path?: string | null;
  payload_hash?: string | null;
  evidence_count: number;
  key_fields: Record<string, unknown>;
};

export type ApiProjectInputDetail = {
  source: ApiSourceDocument;
  lifecycle: ApiSourceLifecycle;
  understanding?: ApiSourceUnderstanding | null;
  artifacts: ApiSourceTypedArtifact[];
  evidence: ApiSourceEvidenceItem[];
  impacted_ticket_keys: string[];
};

export type CreateSourceRequest = {
  title: string;
  source_type: "blog" | "paper" | "github_repo" | "github_readme" | "note" | "manual_note" | "repo_note" | "local_markdown" | "local_folder" | "target_codebase";
  source_role?: "reference_project" | "requirement_source" | "background_knowledge" | "design_constraint" | "implementation_example" | "target_codebase";
  path_or_url: string;
  content?: string;
  summary?: string;
  evidence_snippets?: string[];
  auto_analyze?: boolean;
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

export type ApiTeamAgent = {
  id: string;
  name: string;
  role: string;
  backend_name?: string | null;
  runtime_compatibility: string;
  active_assignment_count: number;
  blocked_count: number;
  description: string;
  avatar_seed: string;
  status: string;
  runtime_profile?: ApiAgentRuntimeProfile | null;
  visibility?: ApiAgentVisibility | null;
  skill_ids: string[];
  instructions_present: boolean;
  updated_at: string;
  configuration: {
    enabled?: boolean;
    capabilities?: string[];
    max_concurrent_assignments?: number;
    [key: string]: unknown;
  };
};

export type ApiAgentRuntimeProfile = {
  profile_id: string;
  agent_id: string;
  backend: string;
  model?: string | null;
  working_directory?: string | null;
  environment_keys: string[];
  reasoning_level?: string | null;
  service_tier?: string | null;
};

export type ApiAgentVisibility = {
  agent_id: string;
  visible: boolean;
  team_ids: string[];
};

export type ApiAgentDetail = ApiTeamAgent & {
  instructions: string;
  environment_keys: string[];
};

export type CreateAgentRequest = {
  name: string;
  description?: string;
  backend: "codex" | "claude-code";
  model?: string | null;
  working_directory?: string | null;
  environment_keys?: string[];
  reasoning_level?: string | null;
  service_tier?: string | null;
  instructions?: string;
  skill_ids?: string[];
  visible?: boolean;
  team_ids?: string[];
  max_concurrent_assignments?: number;
};

export type UpdateAgentRequest = Partial<CreateAgentRequest> & {
  status?: "active" | "paused" | "archived";
};

export type ApiAgentActivityItem = {
  id: string;
  timestamp: string;
  source: string;
  event_type: string;
  stage: string;
  summary: string;
  ticket_id?: string | null;
  ticket_key?: string | null;
  assignment_id?: string | null;
  run_id?: string | null;
  ref_id?: string | null;
};

export type ApiAgentTaskItem = {
  assignment: ApiAssignmentSummary;
  task_id: string;
  ticket_id: string;
  ticket_key: string;
  agent_id: string;
  status: string;
  attempt_number: number;
  retry_count: number;
  blocker_id?: string | null;
  blocker_reason?: string | null;
  claimed_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  current: boolean;
};

export type ApiAgentRunItem = {
  id: string;
  ticket_id: string;
  ticket_key?: string | null;
  agent_name: string;
  agent_role: string;
  status: string;
  lifecycle_state: string;
  backend_name?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  failure_reason?: string | null;
  error?: string | null;
  assignment_id?: string | null;
};

export type ApiBuildTeam = {
  id: string;
  name: string;
  description: string;
  lead_agent_id: string;
  implementer_agent_id: string;
  reviewer_agent_id: string;
  default_backend_name: string;
  skill_refs: string[];
  enabled: boolean;
};

export type ApiRunsRuntime = {
  runtime_id: string;
  backend_name: string;
  display_name: string;
  daemon_state: string;
  available: boolean;
  can_assign: boolean;
  can_run: boolean;
  external_execution_enabled: boolean;
  command_template_set: boolean;
  queue_depth: number;
  active_assignment?: string | null;
  disabled_reasons: string[];
};

export type ApiInboxListItem = {
  id: string;
  issue_key?: string | null;
  source_type?: string | null;
  source_id?: string | null;
  linked_assignment_id?: string | null;
  agent_id?: string | null;
  agent_name?: string | null;
  canonical_blocker_id?: string | null;
  failure_reason: string;
  severity: string;
  action_type: string;
  allowed_actions?: string[];
  primary_action?: string | null;
  recovery_class?: string | null;
  created_at: string;
  status: string;
  resolution_note?: string | null;
};

export type ApiTeamAgentsResponse = {
  schema_version: string;
  source: string;
  agents: ApiTeamAgent[];
};

export type ApiAgentDetailResponse = {
  schema_version: string;
  source: string;
  agent: ApiAgentDetail;
};

export type ApiAgentActivityResponse = {
  schema_version: string;
  source: string;
  activity: ApiAgentActivityItem[];
};

export type ApiAgentTasksResponse = {
  schema_version: string;
  source: string;
  tasks: ApiAgentTaskItem[];
};

export type ApiAgentRunsResponse = {
  schema_version: string;
  source: string;
  runs: ApiAgentRunItem[];
};

export type ApiAgentSkillsResponse = {
  schema_version: string;
  source: string;
  skill_ids: string[];
  skills: ApiBuildSkill[];
};

export type ApiAgentInstructionsResponse = {
  schema_version: string;
  source: string;
  instructions: string;
};

export type ApiAgentEnvironmentResponse = {
  schema_version: string;
  source: string;
  environment_keys: string[];
};

export type ApiBuildTeamsResponse = {
  schema_version: string;
  source: string;
  build_teams: ApiBuildTeam[];
};

export type ApiTeamSkillsResponse = {
  schema_version: string;
  source: string;
  skills: ApiBuildSkill[];
};

export type ApiRunsRuntimesResponse = {
  schema_version: string;
  source: string;
  runtimes: ApiRunsRuntime[];
};

export type ApiRunsAssignmentsResponse = {
  schema_version: string;
  source: string;
  assignments: ApiAssignmentSummary[];
};

export type ApiInboxListResponse = {
  schema_version: string;
  source: string;
  inbox: ApiInboxListItem[];
};

export type ApiDeliveryGate = {
  id: string;
  label: string;
  status: string;
  detail: string;
  ref_id?: string | null;
};

export type ApiLatestRealRun = {
  ticket_key: string;
  assignment_id?: string | null;
  backend_name: string;
  execution_result_id: string;
  exit_code?: number | null;
  test_exit_code?: number | null;
  review_verdict?: string | null;
  dry_run: boolean;
  blocked: boolean;
  terminal_verdict?: string;
  changed_files: string[];
  preflight_dirty_files?: string[];
  handoff_file?: string | null;
  diff_artifact_path?: string | null;
  execution_log_artifact_path?: string | null;
  memory_path?: string | null;
  next_tickets_path?: string | null;
};

export type ApiDeliveryItem = {
  ticket_id: string;
  ticket_key: string;
  title: string;
  status: string;
  priority: string;
  target_project_id?: string | null;
  assignment_id?: string | null;
  assignment_status?: string | null;
  backend_name?: string | null;
  execution_result_id?: string | null;
  test_exit_code?: number | null;
  review_verdict?: string | null;
  evidence_status: string;
  terminal_verdict?: string;
  changed_files: string[];
  preflight_dirty_files?: string[];
};

export type ApiProjectVersionDelivery = {
  id: string;
  version_label: string;
  status: string;
  goal_id?: string | null;
  target_project_id?: string | null;
  target_project_label?: string | null;
  current_state: string;
  target_state: string;
  summary: string;
  generated_at: string;
  product_closure_status: string;
  product_closure_mode: string;
  product_closure_summary: string;
  product_closure_reason: string;
  product_closure_packet_path?: string | null;
  product_closure_required_command: string;
  progress_counts: Record<string, number>;
  gates: ApiDeliveryGate[];
  delivery_items: ApiDeliveryItem[];
  latest_real_run?: ApiLatestRealRun | null;
  blockers: string[];
  next_actions: string[];
  evidence_refs: string[];
};

export type ApiIssueChild = {
  ticket_id: string;
  ticket_key: string;
  title: string;
  issue_class: string;
  origin: string;
  status: string;
  parent_ticket_key?: string | null;
  root_ticket_key: string;
  reason: string;
};

export type ApiIssueFamily = {
  ticket_id: string;
  ticket_key: string;
  title: string;
  status: string;
  priority: string;
  root_ticket_key: string;
  repair_count: number;
  open_repair_count: number;
  history_count: number;
  child_ticket_keys: string[];
  latest_repair_summary?: string | null;
};

export type ApiIssueProjection = {
  summary: Record<string, number>;
  mainline_tickets: ApiIssueFamily[];
  repair_items: ApiIssueChild[];
  history_items: ApiIssueChild[];
};

export type ApiArtifactRef = {
  id: string;
  artifact_type: string;
  path?: string | null;
  summary: string;
  created_at?: string | null;
  metadata: Record<string, unknown>;
};

export type ApiAgentActivity = {
  id: string;
  ticket_id?: string | null;
  ticket_key?: string | null;
  assignment_id?: string | null;
  run_id?: string | null;
  agent_name: string;
  stage: string;
  event_type: string;
  summary: string;
  timestamp: string;
  ref_id?: string | null;
};

export type ApiAgentWorkflowStep = {
  id: string;
  ticket_id: string;
  ticket_key: string;
  sequence: number;
  agent_name: string;
  agent_role: string;
  step_kind: string;
  status: string;
  input_refs: ApiArtifactRef[];
  output_refs: ApiArtifactRef[];
  assignment_id?: string | null;
  run_id?: string | null;
  handoff_id?: string | null;
  next_agent?: string | null;
  next_action: string;
  latest_activity?: ApiAgentActivity | null;
  blocked_reason?: string | null;
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
  active?: boolean;
  current_state?: string | null;
  archive_reason?: string | null;
  superseded_by_ref?: string | null;
  recovery_class?: string;
  primary_action?: string;
  allowed_actions?: string[];
  linked_assignment_id?: string | null;
  retry_assignment_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type InboxActionRequest = {
  note?: string;
  priority?: string;
  reason?: string;
  force?: boolean;
};

export type InboxActionResponse = {
  inbox_item: ApiInboxItem;
  action: string;
  message: string;
  ticket?: ApiWorkbench["tickets"][number] | null;
  assignment?: ApiAssignmentSummary | null;
  already_exists: boolean;
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
  affected_modules: string[];
  acceptance_criteria: string[];
  source_artifact_ids: string[];
  build_context_id?: string | null;
  target_project_id?: string | null;
  project_version_id?: string | null;
  target_project_label?: string | null;
  target_project_path?: string | null;
  target_repo_path?: string | null;
  target_project_identity?: Record<string, unknown>;
  compiler_provenance: Record<string, unknown>;
  codebase_snapshot_artifact_id?: string | null;
  codebase_snapshot_status: string;
  codebase_snapshot_reason?: string | null;
  source_claim_trace: Array<Record<string, unknown>>;
  affected_module_rationale: string;
  acceptance_criteria_rationale: string;
  goal_reason?: string | null;
  change_intent?: string;
  target_version_label?: string | null;
  existing_ticket_key?: string | null;
  before_snapshot?: Record<string, unknown>;
  after_summary?: string;
  confidence?: number;
  decision_reason?: string;
  included?: boolean;
  metadata?: Record<string, unknown>;
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
  base_ticket_fingerprint?: string | null;
  target_project_id?: string | null;
  project_version_id?: string | null;
  target_project_label?: string | null;
  target_project_path?: string | null;
  target_repo_path?: string | null;
  target_project_identity?: Record<string, unknown>;
  target_version_label?: string | null;
  compiler_provenance?: Record<string, unknown>;
  codebase_snapshot_status?: string;
  codebase_snapshot_reason?: string | null;
  stale?: boolean;
  stale_reason?: string;
  build_context_manifest_id?: string | null;
  context_fingerprint?: string | null;
  source_document_ids?: string[];
  source_artifact_ids?: string[];
  codebase_snapshot_artifact_id?: string | null;
};

export type IssueFactoryPreviewRequest = {
  goal_id: string;
  source_ids: string[];
  target_project_id?: string | null;
};

export type RegisterTargetProjectRequest = {
  path: string;
  label?: string | null;
  create_if_missing?: boolean;
  init_git?: boolean;
  test_command?: string | null;
  issue_prefix?: string | null;
};

export type CreateProjectVersionRequest = {
  target_project_id?: string | null;
  target_repo_path?: string | null;
  target_repo_label?: string | null;
  create_if_missing?: boolean;
  init_git?: boolean;
  test_command?: string | null;
  issue_prefix?: string | null;
  version_label: string;
  goal_title: string;
  goal_north_star: string;
  target_state?: string;
};

export type SelectProjectVersionRequest = {
  version_id: string;
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
  allowed_assignment_id?: string | null;
  target_project_id?: string | null;
  allowed_backends?: string[];
  scope_mode?: string;
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
