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
  blocker?: string | null;
  failure_reason?: string | null;
};

export type ApiRuntimeCapability = {
  backend_name: string;
  available: boolean;
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
  planner_name?: "deterministic" | "llm";
  agent_runtime?: "deterministic" | "llm";
  backlog_planner_name?: "deterministic" | "llm";
  target_project_id: string;
  idempotency_key?: string;
};

export type RunAssignmentRequest = {
  confirm_execution: boolean;
  runtime_id: string;
  agent_runtime?: "deterministic" | "llm";
  backlog_planner?: "deterministic" | "llm";
  timeout_seconds?: number;
  idempotency_key?: string;
};

export type AddTicketCommentRequest = {
  body: string;
  author?: string;
  reply_to?: string;
  idempotency_key?: string;
};
