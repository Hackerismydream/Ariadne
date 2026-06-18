import { getWorkbench } from "./shared/api/client";
import type { ApiWorkbench } from "./shared/api/types";
import type { AriadneTicket, RuntimeInfo, TicketStatus, WorkbenchData } from "./types";

export const workbenchData: WorkbenchData = {
  goal: {
    id: "GOAL-ARIADNE-1",
    title: "Ariadne v1.0: local AI builder workbench",
    northStar:
      "让知识、反馈和代码状态持续更新 ticket，再把明确的 ticket 分配给 Codex / Claude / fake-codex 执行。",
    status: "active",
    knowledgeInputs: [
      "Multica issue-agent-runtime-board architecture",
      "Ariadne ADR-0004 ticket-centered agent workbench",
      "Execution feedback from fake-codex and CodexBackend smoke path",
    ],
    feedbackSignals: [
      "Goal 只能作为输入，不再是中心对象",
      "前端需要对标 Multica 的成熟产品形态",
      "用户需要可见的 ticket lifecycle 和 agent progress",
    ],
    currentState: "Python local core works through CLI and static board.",
    targetState: "Independent workbench frontend with goal, ticket, agent, runtime, skill, inbox, and progress pages.",
  },
  tickets: [
    {
      id: "t-1",
      key: "ARI-FE-001",
      title: "Build Multica-style Ariadne app shell",
      summary: "Sidebar, topbar, workspace navigation, and floating agent chat dock.",
      status: "running",
      priority: "high",
      owner: "Ariadne Codex",
      source: "Multica app-sidebar and issues screenshot",
      decision: "code_task",
      changedFiles: ["frontend/ariadne-workbench/src/App.tsx", "frontend/ariadne-workbench/src/styles.css"],
      progress: [
        { time: "09:10", actor: "Codex", kind: "analysis", body: "Captured Multica issues, agents, runtimes, skills, inbox screenshots." },
        { time: "09:18", actor: "Codex", kind: "implementation", body: "Started local React workbench with Ariadne goal adaptation." },
      ],
      reviewVerdict: "pending",
      acceptance: [
        "Sidebar matches Multica information density.",
        "The /goal page is first-class.",
        "No hosted auth or Multica runtime dependency is introduced.",
      ],
    },
    {
      id: "t-2",
      key: "ARI-FE-002",
      title: "Implement ticket board and detail inspector",
      summary: "Kanban board with status columns and right-hand detail timeline.",
      status: "reviewing",
      priority: "high",
      owner: "Ariadne Implementer",
      source: "Multica Issues and IssueDetail components",
      decision: "code_task",
      changedFiles: ["src/components/IssueBoard.tsx", "src/components/TicketDetail.tsx"],
      progress: [
        { time: "08:42", actor: "Ariadne Implementer", kind: "handoff", body: "Ticket board should expose packet, backend, tests, review, memory." },
        { time: "08:57", actor: "Ariadne Reviewer", kind: "review", body: "Need stronger progress timeline and memory path visibility." },
      ],
      reviewVerdict: "needs_fix",
      memoryPath: ".ariadne/memory/tickets/ARI-003.json",
      nextTicketsPath: ".ariadne/artifacts/ARI-003/next_tickets.json",
      github: {
        operation: "status",
        ok: true,
        blocked: false,
        repo: "Hackerismydream/Ariadne",
        issueNumber: 8,
        issueUrl: "https://github.com/Hackerismydream/Ariadne/issues/8",
        prNumber: 9,
        prUrl: "https://github.com/Hackerismydream/Ariadne/pull/9",
        branch: "codex/ariadne-production-frontend-integration",
        commitSha: "3e419f358adc45c41fbdcb1062e9685d3048e46a",
        checksStatus: "no_checks_reported",
        checkCounts: { pass: 0, pending: 0, fail: 0, total: 0 },
        reviewDecision: "none",
        mergeable: "MERGEABLE",
        baseBranch: "main",
        history: [
          { operation: "create_issue", ok: true, blocked: false, createdAt: "2026-06-17 14:16:20" },
          { operation: "create_pr", ok: true, blocked: false, createdAt: "2026-06-17 14:31:24" },
          { operation: "status", ok: true, blocked: false, createdAt: "2026-06-17 14:32:09" },
        ],
      },
      acceptance: [
        "Each ticket card shows owner, decision, and review state.",
        "Detail inspector shows changed files and acceptance criteria.",
      ],
    },
    {
      id: "t-3",
      key: "ARI-FE-003",
      title: "Expose agent roles and runtime capability",
      summary: "Agents, runtimes, and skills pages adapted to Ariadne local core.",
      status: "planning",
      priority: "medium",
      owner: "Ariadne Reviewer",
      source: "Multica agents, runtimes, skills pages",
      decision: "doc_update",
      changedFiles: [],
      progress: [
        { time: "08:20", actor: "Build Lead", kind: "route", body: "Keep Codex, Reviewer, Release Verifier, and fake-codex visible as teammates." },
      ],
      reviewVerdict: "pending",
      acceptance: [
        "Agent roles are visible.",
        "Runtime capabilities show local safety gates.",
        "Skills show attached BuildSkill packs.",
      ],
    },
    {
      id: "t-4",
      key: "ARI-FE-004",
      title: "Wire inbox into review and blocker events",
      summary: "Show comments, blockers, memory writes, and feedback events as a work queue.",
      status: "inbox",
      priority: "medium",
      owner: "Build Lead",
      source: "Multica inbox page",
      decision: "architecture_change",
      changedFiles: [],
      progress: [],
      reviewVerdict: "pending",
      acceptance: [
        "Inbox separates review, blocker, memory, and goal feedback.",
        "Each item links back to ticket or goal context.",
      ],
    },
    {
      id: "t-5",
      key: "ARI-FE-005",
      title: "Finish deployable frontend package",
      summary: "Build, screenshot verification, and production deployment instructions.",
      status: "done",
      priority: "high",
      owner: "Ariadne Release Verifier",
      source: "User request for independently deployable product frontend",
      decision: "code_task",
      changedFiles: ["package.json", "vite.config.ts", "README.md"],
      progress: [
        { time: "07:51", actor: "Release Verifier", kind: "verification", body: "Build must pass without Ariadne Python runtime." },
      ],
      reviewVerdict: "pass",
      memoryPath: ".ariadne/memory/frontend-release.json",
      nextTicketsPath: ".ariadne/artifacts/frontend/next_tickets.json",
      acceptance: [
        "npm run build succeeds.",
        "Frontend can be deployed as static assets.",
      ],
    },
  ],
  sources: [
    {
      id: "source-structured-handoff",
      sourceType: "blog",
      title: "Why AI Coding Agents Need Structured Handoff",
      status: "new",
      ingestedAt: "10m ago",
      pathOrUrl: "sources/blog/structured-handoff.md",
      linkedTicketCount: 3,
    },
    {
      id: "source-self-improvement",
      sourceType: "paper",
      title: "Reflection for Agent Self-Improvement",
      status: "extracted",
      ingestedAt: "32m ago",
      pathOrUrl: "sources/papers/verbal-rl.md",
      linkedTicketCount: 2,
    },
    {
      id: "source-kit-readme",
      sourceType: "github_readme",
      title: "sveltejs/kit README",
      status: "linked",
      ingestedAt: "1h ago",
      pathOrUrl: "https://github.com/sveltejs/kit",
      linkedTicketCount: 1,
    },
    {
      id: "source-roadmap",
      sourceType: "repo_note",
      title: "Ariadne v0.3 Roadmap",
      status: "new",
      ingestedAt: "2h ago",
      pathOrUrl: "docs/roadmap/v0.3.md",
      linkedTicketCount: 0,
    },
    {
      id: "source-codebase-main",
      sourceType: "codebase_scan",
      title: "ariadne/ariadne main branch scan",
      status: "extracted",
      ingestedAt: "3h ago",
      pathOrUrl: ".ariadne/project/resources.json",
      linkedTicketCount: 4,
    },
    {
      id: "source-review-notes",
      sourceType: "review_feedback",
      title: "ARI-032 PR Review Notes",
      status: "linked",
      ingestedAt: "4h ago",
      pathOrUrl: ".ariadne/reviews/ARI-032.md",
      linkedTicketCount: 2,
    },
  ],
  knowledgeCards: [
    {
      id: "kc-structured-handoff-primary",
      sourceId: "source-structured-handoff",
      title: "Structured handoff is the missing layer",
      sourceSummary:
        "Agents stall when context, acceptance criteria, and next steps are not explicit. The source argues for structured handoff contracts.",
      evidence: [
        "Handoff quality directly affects task success rate.",
        "Define inputs, outputs, checks, and allowed tools.",
      ],
      projectRelevance: "High: aligns with Ariadne's ticket-centered execution and reviewer gate.",
      buildDecision: "code_task",
      affectedModules: ["handoffs", "planner", "reviewer", "memory"],
      risks: ["Overhead if packet schema is too verbose.", "Needs alignment with existing ticket schema."],
      confidence: 0.86,
      primary: true,
    },
    {
      id: "kc-self-improvement-secondary",
      sourceId: "source-self-improvement",
      title: "Reflection loop improves future tickets",
      sourceSummary: "Agents improve through reflection and verbal feedback loops after execution.",
      evidence: [
        "Reflection tokens improve future decision quality.",
        "Verbal feedback outperforms scalar rewards in sparse tasks.",
      ],
      projectRelevance: "Medium: useful for memory and review loop, not a first-page feature.",
      buildDecision: "experiment",
      affectedModules: ["memory", "review", "next_tickets"],
      risks: ["May add noisy memory if reviewer output is weak."],
      confidence: 0.64,
      primary: false,
    },
    {
      id: "kc-codebase-runtime",
      sourceId: "source-codebase-main",
      title: "Runtime capability should drive backend choice",
      sourceSummary: "The local project already writes runtime capability snapshots and project resources.",
      evidence: [
        ".ariadne/runtimes/capability_snapshot.json lists Codex, Claude, fake-codex, shell, dry-run.",
        ".ariadne/project/resources.json identifies local target repositories.",
      ],
      projectRelevance: "High: frontend runtime selection should reflect actual local capability and safety gates.",
      buildDecision: "architecture_change",
      affectedModules: ["runtime", "frontend", "board"],
      risks: ["Frontend must remain read-only until explicit execution gates exist."],
      confidence: 0.9,
      primary: true,
    },
  ],
  backlogChanges: [
    {
      id: "bc-ari-041",
      knowledgeCardId: "kc-structured-handoff-primary",
      kind: "added",
      ticketKey: "ARI-041",
      title: "Implement Build Packet schema",
      reason: "Structured handoff requires explicit packet fields.",
      priority: "P1",
      suggestedOwnerAgent: "Build Lead",
      buildDecision: "code_task",
    },
    {
      id: "bc-ari-042",
      knowledgeCardId: "kc-structured-handoff-primary",
      kind: "added",
      ticketKey: "ARI-042",
      title: "Packet validation in Reviewer",
      reason: "Ensure packets meet acceptance criteria before execution.",
      priority: "P1",
      suggestedOwnerAgent: "Reviewer",
      buildDecision: "code_task",
    },
    {
      id: "bc-ari-043",
      knowledgeCardId: "kc-structured-handoff-primary",
      kind: "added",
      ticketKey: "ARI-043",
      title: "Handoff contract generator",
      reason: "Standardize inputs, outputs, checks, and allowed tools.",
      priority: "P2",
      suggestedOwnerAgent: "Planner",
      buildDecision: "code_task",
    },
    {
      id: "bc-ari-032",
      knowledgeCardId: "kc-structured-handoff-primary",
      kind: "updated",
      ticketKey: "ARI-032",
      title: "Review gate for code changes",
      reason: "Add packet completeness check.",
      priority: "P1",
      suggestedOwnerAgent: "Reviewer",
      buildDecision: "architecture_change",
    },
    {
      id: "bc-ari-018",
      knowledgeCardId: "kc-self-improvement-secondary",
      kind: "updated",
      ticketKey: "ARI-018",
      title: "Memory write-back flow",
      reason: "Link reflection summary to handoff completion event.",
      priority: "P2",
      suggestedOwnerAgent: "Memory Agent",
      buildDecision: "experiment",
    },
    {
      id: "bc-ari-055",
      knowledgeCardId: "kc-self-improvement-secondary",
      kind: "deferred",
      ticketKey: "ARI-055",
      title: "Auto-summarize long context",
      reason: "Depends on context packing refactor.",
      priority: "P3",
      suggestedOwnerAgent: "Build Lead",
      buildDecision: "watchlist",
    },
  ],
  traceSteps: [
    {
      id: "trace-source",
      knowledgeCardId: "kc-structured-handoff-primary",
      label: "Source",
      summary: "Why AI Coding Agents Need Structured Handoff",
      artifactPath: "sources/blog/structured-handoff.md",
      timestamp: "10m ago",
    },
    {
      id: "trace-evidence",
      knowledgeCardId: "kc-structured-handoff-primary",
      label: "Evidence",
      summary: "2 key snippets extracted and cited.",
      artifactPath: "extracted/structured-handoff.md",
      timestamp: "9m ago",
    },
    {
      id: "trace-decision",
      knowledgeCardId: "kc-structured-handoff-primary",
      label: "Build Decision",
      summary: "code_task: high alignment with ticket-centered execution and reviewer gate.",
      artifactPath: "decisions/DEC-2026-06-17-structured-handoff.md",
      timestamp: "8m ago",
    },
    {
      id: "trace-delta",
      knowledgeCardId: "kc-structured-handoff-primary",
      backlogChangeId: "bc-ari-041",
      label: "Ticket Delta",
      summary: "+3 added, 2 updated, 1 deferred, 0 rejected.",
      artifactPath: "delta/2026-06-17-structured-handoff.json",
      timestamp: "7m ago",
    },
    {
      id: "trace-packet",
      knowledgeCardId: "kc-structured-handoff-primary",
      backlogChangeId: "bc-ari-041",
      label: "Build Packet",
      summary: "Packet draft created for ARI-041.",
      artifactPath: "packets/ARI-041-build-packet.md",
      timestamp: "6m ago",
    },
    {
      id: "trace-handoff",
      knowledgeCardId: "kc-structured-handoff-primary",
      backlogChangeId: "bc-ari-041",
      label: "Handoff",
      summary: "Planner -> Execution Agent, backend candidate: Codex.",
      artifactPath: "handoffs/ARI-041-handoff.md",
      timestamp: "5m ago",
    },
    {
      id: "trace-reflection-source",
      knowledgeCardId: "kc-self-improvement-secondary",
      label: "Source",
      summary: "Reflection for Agent Self-Improvement",
      artifactPath: "sources/papers/verbal-rl.md",
      timestamp: "32m ago",
    },
    {
      id: "trace-reflection-evidence",
      knowledgeCardId: "kc-self-improvement-secondary",
      label: "Evidence",
      summary: "2 reflection-loop snippets extracted.",
      artifactPath: "extracted/verbal-rl.md",
      timestamp: "31m ago",
    },
    {
      id: "trace-reflection-decision",
      knowledgeCardId: "kc-self-improvement-secondary",
      label: "Build Decision",
      summary: "experiment: useful for memory quality, not yet a core execution path.",
      artifactPath: "decisions/DEC-2026-06-17-reflection-memory.md",
      timestamp: "30m ago",
    },
    {
      id: "trace-reflection-delta",
      knowledgeCardId: "kc-self-improvement-secondary",
      backlogChangeId: "bc-ari-018",
      label: "Ticket Delta",
      summary: "Updated ARI-018 with reflection summary attached to memory write-back.",
      artifactPath: "delta/2026-06-17-reflection-memory.json",
      timestamp: "29m ago",
    },
    {
      id: "trace-reflection-packet",
      knowledgeCardId: "kc-self-improvement-secondary",
      backlogChangeId: "bc-ari-018",
      label: "Build Packet",
      summary: "Packet notes added for memory write-back flow.",
      artifactPath: "packets/ARI-018-memory-write-back.md",
      timestamp: "28m ago",
    },
    {
      id: "trace-reflection-handoff",
      knowledgeCardId: "kc-self-improvement-secondary",
      backlogChangeId: "bc-ari-018",
      label: "Handoff",
      summary: "Planner -> Memory Agent, backend candidate: fake-codex dry run.",
      artifactPath: "handoffs/ARI-018-memory-handoff.md",
      timestamp: "27m ago",
    },
    {
      id: "trace-runtime-source",
      knowledgeCardId: "kc-codebase-runtime",
      label: "Source",
      summary: "Codebase scan found local runtime and project resource snapshots.",
      artifactPath: ".ariadne/runtimes/capability_snapshot.json",
      timestamp: "3h ago",
    },
    {
      id: "trace-runtime-decision",
      knowledgeCardId: "kc-codebase-runtime",
      label: "Build Decision",
      summary: "architecture_change: frontend backend selection should reflect local safety gates.",
      artifactPath: "decisions/DEC-2026-06-17-runtime-capability.md",
      timestamp: "3h ago",
    },
  ],
  backlogMutationPreview: {
    status: "preview_only",
    added: 3,
    updated: 2,
    deferred: 1,
    rejected: 0,
    unsafe: 0,
    lastPreviewAt: "2m ago",
  },
  agents: [
    { name: "Ariadne Codex", description: "Codex agent for product implementation and integration.", backend: "Codex", status: "online", runs: 18, reasoning: "超高" },
    { name: "Ariadne Implementer", description: "Implementation agent for local-first Python and frontend changes.", backend: "Codex", status: "online", runs: 12, reasoning: "高" },
    { name: "Ariadne Reviewer", description: "Conservative review agent for architecture and regression risks.", backend: "Codex", status: "online", runs: 9, reasoning: "高" },
    { name: "Ariadne Release Verifier", description: "Release gate verifier for tests, CLI smoke, and evidence packets.", backend: "fake-codex", status: "idle", runs: 5, reasoning: "默认" },
  ],
  runtimes: [
    { machine: "local-mac", backend: "codex", status: "online", version: "codex-cli fast", cost7d: "$0.51" },
    { machine: "local-mac", backend: "claude-code", status: "online", version: "claude-code", cost7d: "$0.00" },
    { machine: "local-mac", backend: "fake-codex", status: "online", version: "deterministic", cost7d: "$0.00" },
  ],
  skills: [
    { name: "ariadne-multica-reference-lens", description: "Use Multica as architecture reference without copying backend code.", usedBy: ["Codex", "Reviewer"], updatedAt: "13 小时前" },
    { name: "ariadne-review-diff", description: "Review branch diff against ticket acceptance and safety boundaries.", usedBy: ["Reviewer", "Verifier"], updatedAt: "13 小时前" },
    { name: "ariadne-verification", description: "Run pytest, ruff, demo, export board, backend doctor, and verify_v1.", usedBy: ["Verifier"], updatedAt: "13 小时前" },
    { name: "ariadne-local-first-guardrails", description: "Keep external execution, Feishu writes, and hosted behavior gated.", usedBy: ["Codex", "Implementer"], updatedAt: "13 小时前" },
  ],
  inbox: [
    { id: "i-1", ticketId: "t-2", title: "ARI-FE-002 needs stronger timeline", body: "Reviewer asked for visible progress events in ticket detail.", time: "44 分钟", kind: "review" },
    { id: "i-2", ticketId: "t-4", title: "Goal direction updated", body: "Goal remains an input. Ticket state changes are the product center.", time: "1 小时", kind: "goal" },
    { id: "i-3", ticketId: "t-3", title: "Codex runtime config", body: "当前 provider 不接受 flex，真实 Codex smoke 使用 fast。", time: "2 小时", kind: "blocker" },
    { id: "i-4", ticketId: "t-2", title: "Memory written", body: "Multica alignment notes are available for future planning.", time: "3 小时", kind: "memory" },
  ],
};

export type WorkbenchDataSource = "api" | "snapshot" | "fixture";

export async function loadWorkbenchData(): Promise<{ data: WorkbenchData; source: WorkbenchDataSource; readOnly: boolean }> {
  try {
    const apiData = await getWorkbench();
    return { data: adaptApiWorkbench(apiData), source: "api", readOnly: false };
  } catch {
    // Fall through to the generated static snapshot.
  }
  try {
    const response = await fetch("/web_data/workbench.json", { cache: "no-store" });
    if (!response.ok) {
      return { data: workbenchData, source: "fixture", readOnly: true };
    }
    const localData = (await response.json()) as Partial<WorkbenchData>;
    return {
      data: {
        ...workbenchData,
        ...localData,
        goal: { ...workbenchData.goal, ...localData.goal },
        tickets: localData.tickets?.length ? localData.tickets : workbenchData.tickets,
        agents: localData.agents?.length ? localData.agents : workbenchData.agents,
        runtimes: localData.runtimes?.length ? localData.runtimes : workbenchData.runtimes,
        skills: localData.skills?.length ? localData.skills : workbenchData.skills,
        inbox: localData.inbox?.length ? localData.inbox : workbenchData.inbox,
        sources: localData.sources?.length ? localData.sources : workbenchData.sources,
        knowledgeCards: localData.knowledgeCards?.length ? localData.knowledgeCards : workbenchData.knowledgeCards,
        backlogChanges: localData.backlogChanges?.length ? localData.backlogChanges : workbenchData.backlogChanges,
        traceSteps: localData.traceSteps?.length ? localData.traceSteps : workbenchData.traceSteps,
        backlogMutationPreview: localData.backlogMutationPreview ?? workbenchData.backlogMutationPreview,
        projectResources: localData.projectResources ?? workbenchData.projectResources,
      },
      source: "snapshot",
      readOnly: true,
    };
  } catch {
    return { data: workbenchData, source: "fixture", readOnly: true };
  }
}

function adaptApiWorkbench(apiData: ApiWorkbench): WorkbenchData {
  return {
    ...workbenchData,
    tickets: apiData.tickets.map((ticket) => adaptTicket(ticket, apiData)),
    assignments: apiData.assignments.map((assignment) => ({
      id: assignment.id,
      ticketId: assignment.ticket_id,
      ticketKey: assignment.ticket_key,
      agentId: assignment.agent_id,
      agentName: assignment.agent_name,
      backendName: assignment.backend_name,
      status: assignment.status,
      targetProjectId: assignment.target_project_id,
      blocker: assignment.blocker,
      failureReason: assignment.failure_reason,
    })),
    runtimes: apiData.runtime_capabilities.map(adaptRuntime),
    projectResources: apiData.target_projects.map((project) => ({
      id: project.id,
      label: project.label,
      resourceType: "local_directory",
      available: project.available,
      disabledReason: project.disabled_reason,
    })),
  };
}

function adaptTicket(ticket: ApiWorkbench["tickets"][number], apiData: ApiWorkbench): AriadneTicket {
  const fixture = workbenchData.tickets.find((item) => item.key === ticket.key);
  const assignment = apiData.assignments.find((item) => item.id === ticket.latest_assignment_id)
    ?? apiData.assignments.find((item) => item.ticket_id === ticket.id);
  return {
    ...(fixture ?? workbenchData.tickets[0]),
    id: ticket.id,
    key: ticket.key,
    title: ticket.title,
    summary: fixture?.summary ?? `${ticket.source_type} source ticket managed by Ariadne.`,
    status: adaptTicketStatus(ticket.status),
    priority: ticket.priority === "high" || ticket.priority === "low" ? ticket.priority : "medium",
    owner: assignment?.agent_name ?? ticket.assigned_agent_id ?? "Build Lead",
    source: ticket.source_type,
    decision: fixture?.decision ?? "code_task",
    reviewVerdict: ticket.latest_review_verdict === "pass"
      ? "pass"
      : ticket.latest_review_verdict === "needs_fix"
        ? "needs_fix"
        : ticket.status === "blocked"
          ? "blocked"
          : "pending",
    progress: fixture?.progress ?? [],
    changedFiles: fixture?.changedFiles ?? [],
    acceptance: fixture?.acceptance ?? ["Ticket can be assigned to a product runtime.", "Run progress is visible in Ariadne."],
  };
}

function adaptTicketStatus(status: string): TicketStatus {
  if (status === "ready_for_execution" || status === "waiting_approval") return "ready";
  if (status === "coding") return "running";
  if (status === "done") return "done";
  if (status === "reviewing") return "reviewing";
  if (status === "blocked" || status === "failed" || status === "cancelled") return "blocked";
  if (status === "planning" || status === "analyzing") return "planning";
  return "inbox";
}

function adaptRuntime(runtime: ApiWorkbench["runtime_capabilities"][number]): RuntimeInfo {
  return {
    machine: "local-mac",
    backend: runtime.backend_name,
    status: runtime.available ? "online" : "offline",
    version: runtime.command_template_set ? "template configured" : "default template",
    cost7d: "local",
    externalExecutionEnabled: runtime.external_execution_enabled,
    commandTemplateSet: runtime.command_template_set,
    confirmExecutionRequired: runtime.confirm_execution_required,
    supportsExternalExecution: true,
    disabledReasons: runtime.disabled_reasons,
  };
}
