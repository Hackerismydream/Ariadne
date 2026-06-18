import { getWorkbench } from "./shared/api/client";
import type { ApiWorkbench } from "./shared/api/types";
import type { AriadneTicket, RuntimeInfo, TicketStatus, WorkbenchData } from "./types";

export const workbenchData: WorkbenchData = {
  goal: {
    id: "GOAL-ARIADNE-1",
    title: "Ariadne v1.0：本地 AI Builder 工作台",
    northStar:
      "让知识、反馈和代码状态持续更新任务，再把明确的任务分配给 Codex / Claude 执行。",
    status: "active",
    knowledgeInputs: [
      "Multica 的 issue-agent-runtime-board 架构",
      "Ariadne ADR-0004：以任务为中心的智能体工作台",
      "CodexBackend 冒烟路径产生的执行反馈",
    ],
    feedbackSignals: [
      "目标只能作为输入，不再是中心对象",
      "前端需要对标 Multica 的成熟产品形态",
      "用户需要可见的任务生命周期和智能体进度",
    ],
    currentState: "Python 本地核心已经能通过 CLI 和静态看板运行。",
    targetState: "形成独立工作台前端，覆盖目标、任务、智能体、运行时、技能、收件箱和进度页面。",
  },
  tickets: [
    {
      id: "t-1",
      key: "ARI-FE-001",
      title: "构建 Multica 风格的 Ariadne 应用外壳",
      summary: "侧边栏、顶部区域、工作区导航和浮动智能体对话入口。",
      status: "running",
      priority: "high",
      owner: "Ariadne Codex",
      source: "Multica 应用侧边栏和任务页面截图",
      decision: "code_task",
      changedFiles: ["frontend/ariadne-workbench/src/App.tsx", "frontend/ariadne-workbench/src/styles.css"],
      progress: [
        { time: "09:10", actor: "Codex", kind: "analysis", body: "已采集 Multica 的任务、智能体、运行时、技能和收件箱截图。" },
        { time: "09:18", actor: "Codex", kind: "implementation", body: "已启动本地 React 工作台，并接入 Ariadne 的目标语义。" },
      ],
      reviewVerdict: "pending",
      acceptance: [
        "侧边栏达到 Multica 的信息密度。",
        "目标页面是一等入口。",
        "不引入托管认证或 Multica 运行时依赖。",
      ],
    },
    {
      id: "t-2",
      key: "ARI-FE-002",
      title: "实现任务看板和详情检查器",
      summary: "按状态分列的看板，以及右侧详情时间线。",
      status: "reviewing",
      priority: "high",
      owner: "Ariadne Implementer",
      source: "Multica 任务页和任务详情组件",
      decision: "code_task",
      changedFiles: ["src/components/IssueBoard.tsx", "src/components/TicketDetail.tsx"],
      progress: [
        { time: "08:42", actor: "Ariadne Implementer", kind: "handoff", body: "任务看板需要展示构建包、后端、测试、评审和记忆。" },
        { time: "08:57", actor: "Ariadne Reviewer", kind: "review", body: "需要更清晰的进度时间线和记忆路径。" },
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
        "每张任务卡显示负责人、决策和评审状态。",
        "详情检查器显示变更文件和验收标准。",
      ],
    },
    {
      id: "t-3",
      key: "ARI-FE-003",
      title: "展示智能体角色和运行时能力",
      summary: "把智能体、运行时和技能页面适配到 Ariadne 本地核心。",
      status: "planning",
      priority: "medium",
      owner: "Ariadne Reviewer",
      source: "Multica 智能体、运行时和技能页面",
      decision: "doc_update",
      changedFiles: [],
      progress: [
        { time: "08:20", actor: "Build Lead", kind: "route", body: "保持 Codex、Reviewer 和 Release Verifier 作为可见队友。" },
      ],
      reviewVerdict: "pending",
      acceptance: [
        "智能体角色可见。",
        "运行时能力显示本地安全门禁。",
        "技能页面显示已附加的 BuildSkill 包。",
      ],
    },
    {
      id: "t-4",
      key: "ARI-FE-004",
      title: "把收件箱接入评审和阻塞事件",
      summary: "把评论、阻塞、记忆写入和反馈事件显示为工作队列。",
      status: "inbox",
      priority: "medium",
      owner: "Build Lead",
      source: "Multica 收件箱页面",
      decision: "architecture_change",
      changedFiles: [],
      progress: [],
      reviewVerdict: "pending",
      acceptance: [
        "收件箱区分评审、阻塞、记忆和目标反馈。",
        "每个条目都能回到任务或目标上下文。",
      ],
    },
    {
      id: "t-5",
      key: "ARI-FE-005",
      title: "完成可部署前端包",
      summary: "构建、截图验收和生产部署说明。",
      status: "done",
      priority: "high",
      owner: "Ariadne Release Verifier",
      source: "用户要求独立可部署的产品前端",
      decision: "code_task",
      changedFiles: ["package.json", "vite.config.ts", "README.md"],
      progress: [
        { time: "07:51", actor: "Release Verifier", kind: "verification", body: "构建必须在没有 Ariadne Python 运行时的情况下通过。" },
      ],
      reviewVerdict: "pass",
      memoryPath: ".ariadne/memory/frontend-release.json",
      nextTicketsPath: ".ariadne/artifacts/frontend/next_tickets.json",
      acceptance: [
        "npm run build 成功。",
        "前端可以作为静态资源部署。",
      ],
    },
  ],
  sources: [
    {
      id: "source-structured-handoff",
      sourceType: "blog",
      title: "为什么 AI 编码智能体需要结构化交接",
      status: "new",
      ingestedAt: "10 分钟前",
      pathOrUrl: "sources/blog/structured-handoff.md",
      linkedTicketCount: 3,
    },
    {
      id: "source-self-improvement",
      sourceType: "paper",
      title: "用于智能体自我改进的反思机制",
      status: "extracted",
      ingestedAt: "32 分钟前",
      pathOrUrl: "sources/papers/verbal-rl.md",
      linkedTicketCount: 2,
    },
    {
      id: "source-kit-readme",
      sourceType: "github_readme",
      title: "sveltejs/kit README",
      status: "linked",
      ingestedAt: "1 小时前",
      pathOrUrl: "https://github.com/sveltejs/kit",
      linkedTicketCount: 1,
    },
    {
      id: "source-roadmap",
      sourceType: "repo_note",
      title: "Ariadne v0.3 路线图",
      status: "new",
      ingestedAt: "2 小时前",
      pathOrUrl: "docs/roadmap/v0.3.md",
      linkedTicketCount: 0,
    },
    {
      id: "source-codebase-main",
      sourceType: "codebase_scan",
      title: "ariadne/ariadne main 分支扫描",
      status: "extracted",
      ingestedAt: "3 小时前",
      pathOrUrl: ".ariadne/project/resources.json",
      linkedTicketCount: 4,
    },
    {
      id: "source-review-notes",
      sourceType: "review_feedback",
      title: "ARI-032 PR 评审记录",
      status: "linked",
      ingestedAt: "4 小时前",
      pathOrUrl: ".ariadne/reviews/ARI-032.md",
      linkedTicketCount: 2,
    },
  ],
  knowledgeCards: [
    {
      id: "kc-structured-handoff-primary",
      sourceId: "source-structured-handoff",
      title: "结构化交接是缺失的一层",
      sourceSummary:
        "当上下文、验收标准和下一步不明确时，智能体会停滞；资料强调需要结构化交接契约。",
      evidence: [
        "交接质量会直接影响任务成功率。",
        "需要明确输入、输出、检查项和允许工具。",
      ],
      projectRelevance: "高：与 Ariadne 以任务为中心的执行和评审门禁一致。",
      buildDecision: "code_task",
      affectedModules: ["handoffs", "planner", "reviewer", "memory"],
      risks: ["如果构建包 schema 过于冗长，会增加负担。", "需要与现有任务 schema 对齐。"],
      confidence: 0.86,
      primary: true,
    },
    {
      id: "kc-self-improvement-secondary",
      sourceId: "source-self-improvement",
      title: "反思循环可以改进后续任务",
      sourceSummary: "智能体可以通过执行后的反思和文字反馈循环持续改进。",
      evidence: [
        "反思内容可以提升后续决策质量。",
        "在稀疏任务中，文字反馈优于单一数值奖励。",
      ],
      projectRelevance: "中：对记忆和评审循环有价值，但不是首屏能力。",
      buildDecision: "experiment",
      affectedModules: ["memory", "review", "next_tickets"],
      risks: ["如果评审输出较弱，可能写入噪声记忆。"],
      confidence: 0.64,
      primary: false,
    },
    {
      id: "kc-codebase-runtime",
      sourceId: "source-codebase-main",
      title: "运行时能力应该驱动后端选择",
      sourceSummary: "本地项目已经写入运行时能力快照和项目资源。",
      evidence: [
        ".ariadne/runtimes/capability_snapshot.json 列出 Codex、Claude、fake-codex、shell、dry-run。",
        ".ariadne/project/resources.json identifies local target repositories.",
      ],
      projectRelevance: "高：前端运行时选择应该反映真实本地能力和安全门禁。",
      buildDecision: "architecture_change",
      affectedModules: ["runtime", "frontend", "board"],
      risks: ["在明确执行门禁存在前，前端必须保持只读。"],
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
      title: "实现 Build Packet schema",
      reason: "结构化交接需要明确的构建包字段。",
      priority: "P1",
      suggestedOwnerAgent: "构建负责人",
      buildDecision: "code_task",
    },
    {
      id: "bc-ari-042",
      knowledgeCardId: "kc-structured-handoff-primary",
      kind: "added",
      ticketKey: "ARI-042",
      title: "在 Reviewer 中校验构建包",
      reason: "确保构建包在执行前满足验收标准。",
      priority: "P1",
      suggestedOwnerAgent: "评审智能体",
      buildDecision: "code_task",
    },
    {
      id: "bc-ari-043",
      knowledgeCardId: "kc-structured-handoff-primary",
      kind: "added",
      ticketKey: "ARI-043",
      title: "交接契约生成器",
      reason: "标准化输入、输出、检查项和允许工具。",
      priority: "P2",
      suggestedOwnerAgent: "规划智能体",
      buildDecision: "code_task",
    },
    {
      id: "bc-ari-032",
      knowledgeCardId: "kc-structured-handoff-primary",
      kind: "updated",
      ticketKey: "ARI-032",
      title: "代码变更评审门禁",
      reason: "增加构建包完整性检查。",
      priority: "P1",
      suggestedOwnerAgent: "评审智能体",
      buildDecision: "architecture_change",
    },
    {
      id: "bc-ari-018",
      knowledgeCardId: "kc-self-improvement-secondary",
      kind: "updated",
      ticketKey: "ARI-018",
      title: "记忆写回流程",
      reason: "把反思摘要关联到交接完成事件。",
      priority: "P2",
      suggestedOwnerAgent: "记忆智能体",
      buildDecision: "experiment",
    },
    {
      id: "bc-ari-055",
      knowledgeCardId: "kc-self-improvement-secondary",
      kind: "deferred",
      ticketKey: "ARI-055",
      title: "自动总结长上下文",
      reason: "依赖上下文打包重构。",
      priority: "P3",
      suggestedOwnerAgent: "构建负责人",
      buildDecision: "watchlist",
    },
  ],
  traceSteps: [
    {
      id: "trace-source",
      knowledgeCardId: "kc-structured-handoff-primary",
      label: "Source",
      summary: "为什么 AI 编码智能体需要结构化交接",
      artifactPath: "sources/blog/structured-handoff.md",
      timestamp: "10 分钟前",
    },
    {
      id: "trace-evidence",
      knowledgeCardId: "kc-structured-handoff-primary",
      label: "Evidence",
      summary: "已提取并引用 2 条关键片段。",
      artifactPath: "extracted/structured-handoff.md",
      timestamp: "9 分钟前",
    },
    {
      id: "trace-decision",
      knowledgeCardId: "kc-structured-handoff-primary",
      label: "Build Decision",
      summary: "code_task：与任务中心执行和评审门禁高度一致。",
      artifactPath: "decisions/DEC-2026-06-17-structured-handoff.md",
      timestamp: "8 分钟前",
    },
    {
      id: "trace-delta",
      knowledgeCardId: "kc-structured-handoff-primary",
      backlogChangeId: "bc-ari-041",
      label: "Ticket Delta",
      summary: "新增 3 个，更新 2 个，延后 1 个，拒绝 0 个。",
      artifactPath: "delta/2026-06-17-structured-handoff.json",
      timestamp: "7 分钟前",
    },
    {
      id: "trace-packet",
      knowledgeCardId: "kc-structured-handoff-primary",
      backlogChangeId: "bc-ari-041",
      label: "Build Packet",
      summary: "已为 ARI-041 创建构建包草稿。",
      artifactPath: "packets/ARI-041-build-packet.md",
      timestamp: "6 分钟前",
    },
    {
      id: "trace-handoff",
      knowledgeCardId: "kc-structured-handoff-primary",
      backlogChangeId: "bc-ari-041",
      label: "Handoff",
      summary: "Planner -> 执行智能体，候选后端：Codex。",
      artifactPath: "handoffs/ARI-041-handoff.md",
      timestamp: "5 分钟前",
    },
    {
      id: "trace-reflection-source",
      knowledgeCardId: "kc-self-improvement-secondary",
      label: "Source",
      summary: "用于智能体自我改进的反思机制",
      artifactPath: "sources/papers/verbal-rl.md",
      timestamp: "32 分钟前",
    },
    {
      id: "trace-reflection-evidence",
      knowledgeCardId: "kc-self-improvement-secondary",
      label: "Evidence",
      summary: "已提取 2 条反思循环片段。",
      artifactPath: "extracted/verbal-rl.md",
      timestamp: "31 分钟前",
    },
    {
      id: "trace-reflection-decision",
      knowledgeCardId: "kc-self-improvement-secondary",
      label: "Build Decision",
      summary: "experiment：对记忆质量有用，但还不是核心执行路径。",
      artifactPath: "decisions/DEC-2026-06-17-reflection-memory.md",
      timestamp: "30 分钟前",
    },
    {
      id: "trace-reflection-delta",
      knowledgeCardId: "kc-self-improvement-secondary",
      backlogChangeId: "bc-ari-018",
      label: "Ticket Delta",
      summary: "已更新 ARI-018，把反思摘要附加到记忆写回流程。",
      artifactPath: "delta/2026-06-17-reflection-memory.json",
      timestamp: "29 分钟前",
    },
    {
      id: "trace-reflection-packet",
      knowledgeCardId: "kc-self-improvement-secondary",
      backlogChangeId: "bc-ari-018",
      label: "Build Packet",
      summary: "已为记忆写回流程增加构建包备注。",
      artifactPath: "packets/ARI-018-memory-write-back.md",
      timestamp: "28 分钟前",
    },
    {
      id: "trace-reflection-handoff",
      knowledgeCardId: "kc-self-improvement-secondary",
      backlogChangeId: "bc-ari-018",
      label: "Handoff",
      summary: "Planner -> 记忆智能体，候选后端：fake-codex 演练。",
      artifactPath: "handoffs/ARI-018-memory-handoff.md",
      timestamp: "27 分钟前",
    },
    {
      id: "trace-runtime-source",
      knowledgeCardId: "kc-codebase-runtime",
      label: "Source",
      summary: "代码库扫描发现本地运行时和项目资源快照。",
      artifactPath: ".ariadne/runtimes/capability_snapshot.json",
      timestamp: "3 小时前",
    },
    {
      id: "trace-runtime-decision",
      knowledgeCardId: "kc-codebase-runtime",
      label: "Build Decision",
      summary: "architecture_change：前端后端选择应反映本地安全门禁。",
      artifactPath: "decisions/DEC-2026-06-17-runtime-capability.md",
      timestamp: "3 小时前",
    },
  ],
  backlogMutationPreview: {
    status: "preview_only",
    added: 3,
    updated: 2,
    deferred: 1,
    rejected: 0,
    unsafe: 0,
    lastPreviewAt: "2 分钟前",
  },
  agents: [
    { name: "Ariadne Codex", description: "负责产品实现和集成的 Codex 智能体。", backend: "Codex", status: "online", runs: 18, reasoning: "超高" },
    { name: "Ariadne Implementer", description: "负责本地优先 Python 与前端改动的实现智能体。", backend: "Codex", status: "online", runs: 12, reasoning: "高" },
    { name: "Ariadne Reviewer", description: "负责架构和回归风险的保守评审智能体。", backend: "Codex", status: "online", runs: 9, reasoning: "高" },
    { name: "Ariadne Release Verifier", description: "负责测试、CLI 冒烟和证据包的发布门禁校验。", backend: "fake-codex", status: "idle", runs: 5, reasoning: "默认" },
  ],
  runtimes: [
    { machine: "local-mac", backend: "codex", status: "online", version: "codex-cli fast", cost7d: "$0.51" },
    { machine: "local-mac", backend: "claude-code", status: "online", version: "claude-code", cost7d: "$0.00" },
    { machine: "local-mac", backend: "fake-codex", status: "online", version: "deterministic", cost7d: "$0.00" },
  ],
  skills: [
    { name: "ariadne-multica-reference-lens", description: "把 Multica 作为架构参考，但不复制后端代码。", usedBy: ["Codex", "Reviewer"], updatedAt: "13 小时前" },
    { name: "ariadne-review-diff", description: "按任务验收和安全边界评审分支 diff。", usedBy: ["Reviewer", "Verifier"], updatedAt: "13 小时前" },
    { name: "ariadne-verification", description: "运行 pytest、ruff、导出看板、backend doctor 和 verify_v1。", usedBy: ["Verifier"], updatedAt: "13 小时前" },
    { name: "ariadne-local-first-guardrails", description: "保持外部执行、飞书写入和托管行为都受门禁控制。", usedBy: ["Codex", "Implementer"], updatedAt: "13 小时前" },
  ],
  inbox: [
    { id: "i-1", ticketId: "t-2", title: "ARI-FE-002 需要更强的时间线", body: "Reviewer 要求在任务详情中显示可见进度事件。", time: "44 分钟", kind: "review" },
    { id: "i-2", ticketId: "t-4", title: "目标方向已更新", body: "目标仍然是输入。任务状态变化才是产品中心。", time: "1 小时", kind: "goal" },
    { id: "i-3", ticketId: "t-3", title: "Codex runtime config", body: "当前 provider 不接受 flex，真实 Codex smoke 使用 fast。", time: "2 小时", kind: "blocker" },
    { id: "i-4", ticketId: "t-2", title: "记忆已写入", body: "Multica 对齐记录已经可用于后续规划。", time: "3 小时", kind: "memory" },
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
    summary: fixture?.summary ?? `由 Ariadne 管理的 ${ticket.source_type} 来源任务。`,
    status: adaptTicketStatus(ticket.status),
    priority: ticket.priority === "high" || ticket.priority === "low" ? ticket.priority : "medium",
    owner: assignment?.agent_name ?? ticket.assigned_agent_id ?? "构建负责人",
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
    acceptance: fixture?.acceptance ?? ["任务可以分配给生产运行时。", "运行进度在 Ariadne 中可见。"],
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
    version: runtime.display_name || (runtime.command_template_set ? "已配置命令模板" : "默认命令模板"),
    cost7d: "local",
    externalExecutionEnabled: runtime.external_execution_enabled,
    commandTemplateSet: runtime.command_template_set,
    confirmExecutionRequired: runtime.confirm_execution_required,
    supportsExternalExecution: true,
    canAssign: runtime.can_assign,
    canRun: runtime.can_run,
    fallbackOnly: runtime.fallback_only,
    disabledReasons: runtime.disabled_reasons,
  };
}
