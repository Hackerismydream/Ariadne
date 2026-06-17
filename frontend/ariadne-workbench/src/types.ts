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
  llmAgents?: LLMAgentEvidence[];
  feishu?: FeishuTicketEvidence;
  releaseEvidence?: ReleaseEvidenceSummary;
  acceptance: string[];
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
  checkedAt?: string;
};

export type ProjectResource = {
  id: string;
  label: string;
  resourceType: string;
  localPath?: string;
};

export type SourceDocument = {
  id: string;
  sourceType: "blog" | "paper" | "github_readme" | "repo_note" | "codebase_scan" | "review_feedback" | "execution_result" | "manual_note";
  title: string;
  status: "new" | "extracted" | "linked" | "applied" | "archived" | "failed";
  ingestedAt: string;
  pathOrUrl: string;
  linkedTicketCount: number;
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
  title: string;
  body: string;
  time: string;
  kind: "review" | "blocker" | "memory" | "goal";
};

export type WorkbenchData = {
  goal: AriadneGoal;
  tickets: AriadneTicket[];
  sources: SourceDocument[];
  knowledgeCards: KnowledgeCard[];
  backlogChanges: BacklogChange[];
  traceSteps: TraceStep[];
  backlogMutationPreview: BacklogMutationPreview;
  agents: AgentRole[];
  runtimes: RuntimeInfo[];
  projectResources?: ProjectResource[];
  backendSmokeEvidence?: BackendSmokeEvidence[];
  releaseEvidence?: ReleaseEvidenceSummary;
  skills: SkillInfo[];
  inbox: InboxItem[];
};
