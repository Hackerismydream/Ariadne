import type {
  AddTicketCommentRequest,
  ApiAssignmentSummary,
  ApiBuildTeamsResponse,
  ApiIssueAssignResponse,
  ApiIssueDetailResponse,
  ApiIssueEvidenceDetailResponse,
  ApiIssueListResponse,
  ApiIssueRunResponse,
  ApiAgentActivityResponse,
  ApiAgentDetailResponse,
  ApiAgentEnvironmentResponse,
  ApiAgentInstructionsResponse,
  ApiAgentRunsResponse,
  ApiAgentSkillsResponse,
  ApiAgentTasksResponse,
  ApiInboxListResponse,
  ApiRunsAssignmentsResponse,
  ApiRunsRuntimesResponse,
  AssignmentEvent,
  AssignmentEventStream,
  ApiSourceDocument,
  ApiProjectInputDetail,
  ApiTeamAgentsResponse,
  ApiTeamSkillsResponse,
  ApiWorkbench,
  AssignTicketRequest,
  CreateAgentRequest,
  CreateProjectGoalRequest,
  CreateSourceRequest,
  InboxActionRequest,
  InboxActionResponse,
  IssueFactoryPreviewRequest,
  RegisterTargetProjectRequest,
  DaemonStartRequest,
  RunAssignmentRequest,
  UpdateAgentRequest,
} from "./types";
import { AriadneApiError } from "./errors";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new AriadneApiError(body || response.statusText, response.status, body);
  }
  return (await response.json()) as T;
}

export function getWorkbench() {
  return requestJson<ApiWorkbench>("/api/workbench");
}

export function getIssues() {
  return requestJson<ApiIssueListResponse>("/api/issues");
}

export function getIssue(issueIdOrKey: string) {
  return requestJson<ApiIssueDetailResponse>(`/api/issues/${encodeURIComponent(issueIdOrKey)}`);
}

export function getIssueEvidence(issueIdOrKey: string, evidenceId: string) {
  return requestJson<ApiIssueEvidenceDetailResponse>(
    `/api/issues/${encodeURIComponent(issueIdOrKey)}/evidence/${encodeURIComponent(evidenceId)}`,
  );
}

export function assignIssue(
  issueIdOrKey: string,
  payload: AssignTicketRequest,
) {
  return requestJson<ApiIssueAssignResponse>(`/api/issues/${encodeURIComponent(issueIdOrKey)}/assign`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}

export function runIssueNow(issueIdOrKey: string, payload: RunAssignmentRequest) {
  return requestJson<ApiIssueRunResponse>(`/api/issues/${encodeURIComponent(issueIdOrKey)}/run-now`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}

export function rerunIssue(issueIdOrKey: string, payload: RunAssignmentRequest) {
  return requestJson<ApiIssueRunResponse>(`/api/issues/${encodeURIComponent(issueIdOrKey)}/rerun`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}

export function addIssueComment(issueIdOrKey: string, payload: AddTicketCommentRequest) {
  return requestJson<{ comment: unknown }>(`/api/issues/${encodeURIComponent(issueIdOrKey)}/comments`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}

export function getRuntimeStatus() {
  return requestJson<{ capabilities: ApiWorkbench["runtime_capabilities"] }>("/api/runtime/status");
}

export function getTeamAgents() {
  return requestJson<ApiTeamAgentsResponse>("/api/team/agents");
}

export function createTeamAgent(payload: CreateAgentRequest) {
  return requestJson<ApiAgentDetailResponse>("/api/team/agents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getTeamAgent(agentId: string) {
  return requestJson<ApiAgentDetailResponse>(`/api/team/agents/${encodeURIComponent(agentId)}`);
}

export function updateTeamAgent(agentId: string, payload: UpdateAgentRequest) {
  return requestJson<ApiAgentDetailResponse>(`/api/team/agents/${encodeURIComponent(agentId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getTeamAgentActivity(agentId: string) {
  return requestJson<ApiAgentActivityResponse>(`/api/team/agents/${encodeURIComponent(agentId)}/activity`);
}

export function getTeamAgentTasks(agentId: string) {
  return requestJson<ApiAgentTasksResponse>(`/api/team/agents/${encodeURIComponent(agentId)}/tasks`);
}

export function getTeamAgentRuns(agentId: string) {
  return requestJson<ApiAgentRunsResponse>(`/api/team/agents/${encodeURIComponent(agentId)}/runs`);
}

export function getTeamAgentSkills(agentId: string) {
  return requestJson<ApiAgentSkillsResponse>(`/api/team/agents/${encodeURIComponent(agentId)}/skills`);
}

export function getTeamAgentInstructions(agentId: string) {
  return requestJson<ApiAgentInstructionsResponse>(`/api/team/agents/${encodeURIComponent(agentId)}/instructions`);
}

export function getTeamAgentEnvironment(agentId: string) {
  return requestJson<ApiAgentEnvironmentResponse>(`/api/team/agents/${encodeURIComponent(agentId)}/environment`);
}

export function getTeamBuildTeams() {
  return requestJson<ApiBuildTeamsResponse>("/api/team/build-teams");
}

export function getTeamSkills() {
  return requestJson<ApiTeamSkillsResponse>("/api/team/skills");
}

export function getRunsRuntimes() {
  return requestJson<ApiRunsRuntimesResponse>("/api/runs/runtimes");
}

export function getRunsAssignments() {
  return requestJson<ApiRunsAssignmentsResponse>("/api/runs/assignments");
}

export function getInbox() {
  return requestJson<ApiInboxListResponse>("/api/inbox");
}

export function registerTargetProject(payload: RegisterTargetProjectRequest) {
  return requestJson("/api/target-projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createProjectGoal(payload: CreateProjectGoalRequest) {
  return requestJson("/api/goals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createSource(payload: CreateSourceRequest) {
  return requestJson<{ source: ApiSourceDocument; duplicate?: boolean; project_input?: ApiProjectInputDetail | null }>("/api/sources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSourceDetail(sourceId: string) {
  return requestJson<{ project_input: ApiProjectInputDetail }>(`/api/sources/${encodeURIComponent(sourceId)}`);
}

export function analyzeSource(sourceId: string) {
  return requestJson<{ project_input?: ApiProjectInputDetail | null }>(`/api/sources/${encodeURIComponent(sourceId)}/analyze`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function createIssueFactoryPreview(payload: IssueFactoryPreviewRequest) {
  return requestJson<{ preview: ApiWorkbench["backlog_previews"][number] }>("/api/issue-factory/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function applyIssueFactoryPreview(previewId: string) {
  return requestJson(`/api/issue-factory/${encodeURIComponent(previewId)}/apply`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function refreshIssueFactoryPreview(previewId: string, payload: IssueFactoryPreviewRequest) {
  return requestJson<{ previous_preview_id: string; preview: ApiWorkbench["backlog_previews"][number] }>(
    `/api/issue-factory/${encodeURIComponent(previewId)}/refresh`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function assignTicket(ticketIdOrKey: string, payload: AssignTicketRequest) {
  return requestJson(`/api/tickets/${encodeURIComponent(ticketIdOrKey)}/assign`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}

export function runAssignment(assignmentId: string, payload: RunAssignmentRequest) {
  return requestJson(`/api/assignments/${encodeURIComponent(assignmentId)}/run`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}

export function getDaemonStatus() {
  return requestJson<ApiWorkbench["daemon_status"]>("/api/daemon/status");
}

export function startDaemon(payload: DaemonStartRequest = {}) {
  return requestJson("/api/daemon/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function stopDaemon() {
  return requestJson("/api/daemon/stop", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function runAssignmentNow(assignmentId: string, payload: RunAssignmentRequest) {
  return requestJson(`/api/assignments/${encodeURIComponent(assignmentId)}/run-now`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}

export function retryAssignment(assignmentId: string, payload: InboxActionRequest = {}) {
  return requestJson<{ assignment: ApiAssignmentSummary; message: string; parent_assignment_id: string }>(
    `/api/assignments/${encodeURIComponent(assignmentId)}/retry`,
    {
    method: "POST",
    body: JSON.stringify(payload),
    },
  );
}

export function getAssignmentEvents(assignmentId: string, since?: string) {
  const query = since ? `?since=${encodeURIComponent(since)}` : "";
  return requestJson<{ assignment: ApiAssignmentSummary; events: AssignmentEvent[] }>(
    `/api/assignments/${encodeURIComponent(assignmentId)}/events${query}`,
  );
}

export function assignmentEventsWebSocketUrl(assignmentId: string, since?: string) {
  const protocol = globalThis.location?.protocol === "https:" ? "wss:" : "ws:";
  const host = globalThis.location?.host || "127.0.0.1:8766";
  const query = since ? `?since=${encodeURIComponent(since)}` : "";
  return `${protocol}//${host}/ws/assignments/${encodeURIComponent(assignmentId)}${query}`;
}

export function openAssignmentEventsSocket(
  assignmentId: string,
  onBatch: (batch: AssignmentEventStream) => void,
  onError?: (error: Event) => void,
  since?: string,
) {
  const socket = new WebSocket(assignmentEventsWebSocketUrl(assignmentId, since));
  socket.addEventListener("message", (event) => {
    onBatch(JSON.parse(event.data) as AssignmentEventStream);
  });
  if (onError) socket.addEventListener("error", onError);
  return socket;
}

export function addTicketComment(ticketIdOrKey: string, payload: AddTicketCommentRequest) {
  return requestJson(`/api/tickets/${encodeURIComponent(ticketIdOrKey)}/comments`, {
    method: "POST",
    headers: payload.idempotency_key ? { "Idempotency-Key": payload.idempotency_key } : undefined,
    body: JSON.stringify(payload),
  });
}

export function createInboxRepairTicket(itemId: string, payload: InboxActionRequest = {}) {
  return requestJson<InboxActionResponse>(`/api/inbox/${encodeURIComponent(itemId)}/repair`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rerunInboxAssignment(itemId: string, payload: InboxActionRequest = {}) {
  return requestJson<InboxActionResponse>(`/api/inbox/${encodeURIComponent(itemId)}/rerun`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function acknowledgeInboxItem(itemId: string, payload: InboxActionRequest = {}) {
  return requestJson<InboxActionResponse>(`/api/inbox/${encodeURIComponent(itemId)}/acknowledge`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function resolveInboxItem(itemId: string, payload: InboxActionRequest = {}) {
  return requestJson<InboxActionResponse>(`/api/inbox/${encodeURIComponent(itemId)}/resolve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
