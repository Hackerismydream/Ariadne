export type ApiWorkbench = {
  tickets: ApiTicketSummary[];
  assignments: ApiAssignmentSummary[];
  runtime_capabilities: ApiRuntimeCapability[];
  target_projects: ApiTargetProject[];
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

export type ApiTargetProject = {
  id: string;
  label: string;
  available: boolean;
  disabled_reason: string;
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
