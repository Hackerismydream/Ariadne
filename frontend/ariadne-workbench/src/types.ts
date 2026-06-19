export type TicketStatus =
  | "inbox"
  | "planning"
  | "ready"
  | "running"
  | "reviewing"
  | "done"
  | "blocked";

export type AriadneTicket = {
  id: string;
  key: string;
  title: string;
  summary: string;
  latestAssignmentId?: string | null;
  targetProjectId?: string | null;
  status: TicketStatus;
  priority: "high" | "medium" | "low";
  owner: string;
  source: string;
  decision: string;
  changedFiles: string[];
  progress: TimelineEvent[];
  reviewVerdict: "pass" | "needs_fix" | "blocked" | "pending";
  memoryPath?: string;
  nextTicketsPath?: string;
  github?: GitHubTicketEvidence;
  backendSmoke?: BackendSmokeEvidence;
  executionEvidence?: TicketExecutionEvidence;
  llmAgents?: LLMAgentEvidence[];
  feishu?: FeishuTicketEvidence;
  releaseEvidence?: ReleaseEvidenceSummary;
  acceptance: string[];
};

export type TicketExecutionEvidence = {
  assignmentId?: string | null;
  assignmentStatus?: string | null;
  assignmentBlocker?: string | null;
  assignmentFailureReason?: string | null;
  executionResultId?: string | null;
  backendName?: string | null;
  dryRun?: boolean | null;
  blocked?: boolean | null;
  blockReason?: string | null;
  failureReason?: string | null;
  command?: string | null;
  exitCode?: number | null;
  stdoutExcerpt: string;
  stderrExcerpt: string;
  changedFiles: string[];
  diffArtifactPath?: string | null;
  executionLogArtifactPath?: string | null;
  handoffFile?: string | null;
  testCommand: string;
  testExitCode?: number | null;
  testStdoutExcerpt: string;
  testStderrExcerpt: string;
  reviewReportId?: string | null;
  reviewVerdict?: string | null;
  memoryPath?: string | null;
  feishuPlanPath?: string | null;
  nextTicketsPath?: string | null;
  warnings: string[];
};

export type BackendSmokeEvidence = {
  id: string;
  backendName: string;
  ticketId: string;
  ticketKey: string;
  assignmentId: string;
  assignmentStatus: string;
  succeeded: boolean;
  blocked: boolean;
  blocker?: string | null;
  executionResultId?: string | null;
  exitCode?: number | null;
  changedFiles: string[];
  testExitCode?: number | null;
  reviewVerdict?: string | null;
  handoffFile?: string | null;
  boardPath?: string | null;
  memoryPath?: string | null;
  feishuPlanPath?: string | null;
  nextTicketsPath?: string | null;
  agentRuntime: string;
  backlogPlannerName: string;
  externalExecutionEnabled: boolean;
  confirmExecution: boolean;
  createdAt: string;
};

export type GitHubTicketEvidence = {
  operation: string;
  ok: boolean;
  blocked: boolean;
  repo?: string | null;
  issueNumber?: number | null;
  issueUrl?: string | null;
  prNumber?: number | null;
  prUrl?: string | null;
  branch?: string | null;
  commitSha?: string | null;
  commentUrl?: string | null;
  checksStatus?: string | null;
  checkCounts?: {
    pass: number;
    pending: number;
    fail: number;
    total: number;
  };
  reviewDecision?: string | null;
  mergeable?: string | null;
  baseBranch?: string | null;
  history: Array<{
    operation: string;
    ok: boolean;
    blocked: boolean;
    createdAt: string;
  }>;
};

export type LLMAgentEvidence = {
  id: string;
  role: string;
  provider: string;
  model: string;
  succeeded: boolean;
  summary?: string | null;
  decision?: string | null;
  totalTokens?: number | null;
  path: string;
  createdAt: string;
};

export type FeishuTicketEvidence = {
  id: string;
  ok: boolean;
  blocked: boolean;
  dryRun: boolean;
  documentUrl?: string | null;
  documentId?: string | null;
  operationSummary?: string | null;
  reason?: string | null;
  returncode?: number | null;
  path: string;
  createdAt: string;
};

export type ReleaseEvidenceSummary = {
  id?: string;
  productionAcceptanceStatus?: string;
  productReadinessStatus?: string;
  runGateStatus?: string;
  productReadinessChecks?: Record<string, string>;
  realSuccessEvidence?: Record<string, unknown>;
  realFailureEvidence?: Record<string, unknown>;
  evidenceRefs?: Record<string, string>;
  ticketCount?: number;
  executionResultCount?: number;
  reviewReportCount?: number;
  inboxItemCount?: number;
  packetPath?: string;
  generatedAt?: string;
};

export type TimelineEvent = {
  time: string;
  actor: string;
  kind: string;
  body: string;
};

export type AriadneGoal = {
  id: string;
  title: string;
  northStar: string;
  targetProjectId?: string | null;
  status: "active" | "reviewing" | "blocked";
  knowledgeInputs: string[];
  feedbackSignals: string[];
  currentState: string;
  targetState: string;
};

export type AgentRole = {
  name: string;
  description: string;
  backend: string;
  status: "online" | "idle" | "offline";
  runs: number;
  reasoning: string;
};

export type RuntimeInfo = {
  machine: string;
  backend: string;
  status: "online" | "offline";
  version: string;
  cost7d: string;
  command?: string;
  commandPath?: string | null;
  externalExecutionEnabled?: boolean;
  commandTemplateSet?: boolean;
  confirmExecutionRequired?: boolean;
  supportsExternalExecution?: boolean;
  supportsDryRun?: boolean;
  canAssign?: boolean;
  canRun?: boolean;
  fallbackOnly?: boolean;
  disabledReasons?: string[];
  checkedAt?: string;
};

export type DaemonStatus = {
  runtimeId: string;
  status: string;
  backgroundRunning: boolean;
  externalExecutionAuthorized: boolean;
  stale?: boolean | null;
  currentAssignmentId?: string | null;
  currentTicketKey?: string | null;
  currentStage?: string | null;
  heartbeatAt?: string | null;
  lastEventId?: string | null;
  lastError?: string | null;
  openAssignmentCount: number;
  claimableAssignmentCount: number;
  runningAssignmentCount: number;
  blockedAssignmentCount: number;
  lastMessage: string;
};

export type ProjectResource = {
  id: string;
  label: string;
  resourceType: string;
  available?: boolean;
  disabledReason?: string;
  localPath?: string;
  testCommand?: string;
  issuePrefix?: string;
};

export type AssignmentSummary = {
  id: string;
  ticketId: string;
  ticketKey: string;
  agentId: string;
  agentName: string;
  backendName?: string | null;
  status: string;
  readinessStatus?: string | null;
  claimable?: boolean | null;
  routeDecisionId?: string | null;
  handoffPacketId?: string | null;
  handoffHash?: string | null;
  buildContextId?: string | null;
  blockedReason?: string | null;
  runtimeScope?: string | null;
  targetProjectId?: string | null;
  createdAt?: string | null;
  blocker?: string | null;
  failureReason?: string | null;
};

export type SourceDocument = {
  id: string;
  sourceType: "blog" | "paper" | "github_readme" | "github_repo" | "repo_note" | "codebase_scan" | "review_feedback" | "execution_result" | "manual_note" | "local_markdown" | "local_folder" | "target_codebase";
  sourceRole?: string;
  title: string;
  status: "new" | "pending" | "analyzed" | "extracted" | "linked" | "applied" | "archived" | "failed" | "blocked";
  analysisStatus?: string;
  ingestedAt: string;
  pathOrUrl: string;
  linkedTicketCount: number;
  artifactIds?: string[];
  licenseRisk?: string;
};

export type SourceArtifact = {
  id: string;
  sourceDocumentId: string;
  artifactType: "knowledge_card" | "reference_project_profile" | "codebase_snapshot";
  payloadHash: string;
  payloadPath: string;
  evidenceIds: string[];
  createdAt: string;
};

export type SourceEvidence = {
  id: string;
  sourceDocumentId: string;
  artifactId?: string | null;
  locator: string;
  quoteOrSummary: string;
  claim: string;
  confidence: number;
  contentHash: string;
  createdAt: string;
};

export type KnowledgeCard = {
  id: string;
  sourceId: string;
  title: string;
  sourceSummary: string;
  evidence: string[];
  projectRelevance: string;
  buildDecision: "archive" | "watchlist" | "doc_update" | "experiment" | "code_task" | "architecture_change" | "reject_for_now";
  affectedModules: string[];
  risks: string[];
  confidence: number;
  primary: boolean;
};

export type BacklogChangeKind = "added" | "updated" | "deferred" | "rejected" | "superseded" | "no_op";

export type BacklogChange = {
  id: string;
  knowledgeCardId: string;
  kind: BacklogChangeKind;
  ticketKey: string;
  title: string;
  reason: string;
  priority: "P1" | "P2" | "P3";
  suggestedOwnerAgent: string;
  buildDecision: KnowledgeCard["buildDecision"];
  previewId?: string;
  previewStatus?: "preview_only" | "applied" | "blocked";
  triggerType?: string;
  operationType?: string;
  appliedUpdateId?: string | null;
  conflictCount?: number;
  evidenceRefs?: string[];
};

export type TraceStep = {
  id: string;
  knowledgeCardId: string;
  backlogChangeId?: string;
  label: "Source" | "Evidence" | "Build Decision" | "Ticket Delta" | "Build Packet" | "Handoff";
  summary: string;
  artifactPath: string;
  timestamp: string;
};

export type BacklogMutationPreview = {
  status: "preview_only" | "applied" | "blocked";
  added: number;
  updated: number;
  deferred: number;
  rejected: number;
  noOp?: number;
  unsafe: number;
  lastPreviewAt: string;
  previewId?: string;
  triggerType?: string;
  appliedUpdateId?: string | null;
};

export type SkillInfo = {
  name: string;
  description: string;
  usedBy: string[];
  updatedAt: string;
};

export type InboxItem = {
  id: string;
  ticketId?: string;
  ticketKey?: string;
  title: string;
  body: string;
  time: string;
  kind: "review" | "blocker" | "memory" | "goal";
  status?: "open" | "acknowledged" | "resolved" | "snoozed";
  severity?: "low" | "medium" | "high" | "critical";
  sourceType?: string;
  sourceId?: string;
  failureReason?: string | null;
  recommendedAction?: string;
  evidenceRef?: string | null;
  resolutionNote?: string | null;
  repairTicketId?: string;
  repairTicketKey?: string;
};

export type WorkbenchData = {
  goal: AriadneGoal;
  tickets: AriadneTicket[];
  sources: SourceDocument[];
  sourceArtifacts?: SourceArtifact[];
  sourceEvidence?: SourceEvidence[];
  knowledgeCards: KnowledgeCard[];
  backlogChanges: BacklogChange[];
  traceSteps: TraceStep[];
  backlogMutationPreview: BacklogMutationPreview;
  agents: AgentRole[];
  runtimes: RuntimeInfo[];
  daemonStatus: DaemonStatus;
  assignments?: AssignmentSummary[];
  projectResources?: ProjectResource[];
  backendSmokeEvidence?: BackendSmokeEvidence[];
  releaseEvidence?: ReleaseEvidenceSummary;
  skills: SkillInfo[];
  inbox: InboxItem[];
};
