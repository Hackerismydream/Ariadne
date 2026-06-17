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
  acceptance: string[];
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
  agents: AgentRole[];
  runtimes: RuntimeInfo[];
  projectResources?: ProjectResource[];
  skills: SkillInfo[];
  inbox: InboxItem[];
};
