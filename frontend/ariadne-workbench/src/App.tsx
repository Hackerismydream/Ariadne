import {
  Bot,
  BookOpenText,
  FolderKanban,
  Inbox,
  ListTodo,
  Monitor,
  Plus,
  Search,
  Send,
  Settings,
  Sparkles,
  Target,
  Users,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { loadWorkbenchData, workbenchData, type WorkbenchDataSource } from "./data";
import { addTicketCommentButtonLabel } from "./features/add-ticket-comment/ui";
import { assignTicketButtonLabel } from "./features/assign-ticket/ui";
import { runAssignmentButtonLabel } from "./features/run-assignment/ui";
import { watchRunEventsButtonLabel } from "./features/watch-run-events/ui";
import { useTicketAgentControl } from "./features/agent-control/model";
import { inferSourceInput, sourceAnalysisLabel, type SourceFormType } from "./features/project-inputs/model";
import { selectableProductionRuntimes } from "./entities/runtime/lib";
import {
  analyzeSource,
  applyIssueFactoryPreview,
  createIssueFactoryPreview,
  createProjectGoal,
  createSource,
  registerTargetProject,
} from "./shared/api/client";
import type {
  AriadneTicket,
  BackendSmokeEvidence,
  FeishuTicketEvidence,
  LLMAgentEvidence,
  ReleaseEvidenceSummary,
  RuntimeInfo,
  TicketExecutionEvidence,
  TicketStatus,
  TimelineEvent,
  WorkbenchData,
} from "./types";

type PageKey = "project" | "sources" | "tasks" | "ready" | "diagnostics";

function parseHashRoute(hash = globalThis.location?.hash ?? "") {
  const value = hash.replace(/^#/, "").trim();
  if (!value) return {};
  const issueMatch = value.match(/^issues\/([^/?#]+)$/i) ?? value.match(/^(?:issue|ticket)=([^&]+)/i);
  if (issueMatch) return { page: "ready" as PageKey, ticketRef: decodeURIComponent(issueMatch[1]) };
  const legacyMap: Record<string, PageKey> = {
    goal: "project",
    knowledge: "sources",
    issues: "ready",
    agents: "diagnostics",
    runtimes: "diagnostics",
    runtime: "diagnostics",
    skills: "diagnostics",
    inbox: "diagnostics",
  };
  if (legacyMap[value]) return { page: legacyMap[value] };
  if (["project", "sources", "tasks", "ready", "diagnostics"].includes(value)) {
    return { page: value as PageKey };
  }
  return {};
}

function findTicketByRef(tickets: AriadneTicket[], ticketRef: string | undefined) {
  if (!ticketRef) return undefined;
  const normalized = ticketRef.trim().toLowerCase();
  return tickets.find(
    (ticket) => ticket.id.toLowerCase() === normalized || ticket.key.toLowerCase() === normalized,
  );
}

function issueHash(ticket: AriadneTicket) {
  return `#issues/${encodeURIComponent(ticket.key)}`;
}

const navGroups: Array<{
  label: string;
  items: Array<{ key: PageKey; label: string; icon: typeof Inbox }>;
}> = [
  {
    label: "产品路径",
    items: [
      { key: "project", label: "项目", icon: Target },
      { key: "sources", label: "输入", icon: BookOpenText },
      { key: "tasks", label: "任务", icon: ListTodo },
      { key: "ready", label: "准备运行", icon: Monitor },
    ],
  },
  {
    label: "诊断",
    items: [
      { key: "diagnostics", label: "运行诊断", icon: Settings },
    ],
  },
];

const statusColumns: Array<{ status: TicketStatus; label: string; tone: string }> = [
  { status: "inbox", label: "收件箱", tone: "neutral" },
  { status: "planning", label: "规划中", tone: "neutral" },
  { status: "ready", label: "待执行", tone: "neutral" },
  { status: "running", label: "进行中", tone: "running" },
  { status: "reviewing", label: "审核中", tone: "review" },
  { status: "done", label: "完成", tone: "done" },
  { status: "blocked", label: "阻塞", tone: "blocked" },
];

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    active: "进行中",
    applied: "已应用",
    archived: "已归档",
    blocked: "已阻塞",
    cancelled: "已取消",
    coding: "编码中",
    done: "已完成",
    extracted: "已提取",
    failed: "失败",
    idle: "空闲",
    inbox: "收件箱",
    linked: "已关联",
    low: "低",
    medium: "中",
    high: "高",
    critical: "严重",
    needs_fix: "需要修复",
    new: "新输入",
    no_checks_reported: "未返回检查",
    offline: "离线",
    online: "在线",
    open: "打开",
    pass: "通过",
    passed: "通过",
    pending: "待处理",
    planning: "规划中",
    preview_only: "仅预览",
    queued: "排队中",
    ready: "待执行",
    reviewing: "审核中",
    review: "审核",
    resolved: "已解决",
    running: "运行中",
    claimed: "已领取",
    stopped: "已停止",
    unknown: "未知",
    snoozed: "已稍后处理",
  };
  return labels[status] ?? status;
}

function sourceTypeLabel(sourceType: WorkbenchData["sources"][number]["sourceType"]) {
  const labels: Record<WorkbenchData["sources"][number]["sourceType"], string> = {
    blog: "博客",
    paper: "论文",
    github_repo: "GitHub 仓库",
    github_readme: "GitHub README",
    repo_note: "仓库笔记",
    local_markdown: "本地 Markdown",
    local_folder: "本地文件夹",
    target_codebase: "目标代码库",
    codebase_scan: "代码库扫描",
    review_feedback: "评审反馈",
    execution_result: "执行结果",
    manual_note: "手动笔记",
  };
  return labels[sourceType];
}

function buildDecisionLabel(decision: string) {
  const labels: Record<string, string> = {
    architecture_change: "架构变更",
    archive: "归档",
    code_task: "代码任务",
    doc_update: "文档更新",
    experiment: "实验",
    reject_for_now: "暂不采纳",
    watchlist: "观察",
  };
  return labels[decision] ?? decision;
}

function traceLabel(label: string) {
  const labels: Record<string, string> = {
    Source: "来源",
    Evidence: "证据",
    "Build Decision": "构建决策",
    "Ticket Delta": "任务变更",
    "Build Packet": "构建包",
    Handoff: "交接",
  };
  return labels[label] ?? label;
}

function previewStatusLabel(status: WorkbenchData["backlogMutationPreview"]["status"]) {
  if (status === "applied") return "已应用";
  if (status === "blocked") return "已阻塞：存在不安全变更";
  return "仅预览";
}

function yesNo(value: boolean) {
  return value ? "是" : "否";
}

function availabilityLabel(value: boolean) {
  return value ? "可用" : "不可用";
}

function fallbackText(value: string | null | undefined, fallback = "未记录") {
  return value ?? fallback;
}

function resultLabel(ok: boolean, blocked = false) {
  if (ok) return "通过";
  if (blocked) return "已阻塞";
  return "失败";
}

export function App() {
  const initialRoute = parseHashRoute();
  const [page, setPage] = useState<PageKey>(initialRoute.page ?? "project");
  const [data, setData] = useState<WorkbenchData>(workbenchData);
  const [dataSource, setDataSource] = useState<WorkbenchDataSource>("disconnected");
  const [readOnly, setReadOnly] = useState(true);
  const [selectedTicketId, setSelectedTicketId] = useState(
    findTicketByRef(workbenchData.tickets, initialRoute.ticketRef)?.id ?? workbenchData.tickets[0]?.id ?? "",
  );
  const [selectedRuntime, setSelectedRuntime] = useState(workbenchData.runtimes[0]?.backend ?? "fake-codex");
  const selectedTicket = data.tickets.find((ticket) => ticket.id === selectedTicketId) ?? data.tickets[0];

  async function refreshWorkbenchData(preferredTicketRef?: string) {
    const result = await loadWorkbenchData();
    setData(result.data);
    setDataSource(result.source);
    setReadOnly(result.readOnly);
    const route = parseHashRoute();
    const preferredTicket = findTicketByRef(result.data.tickets, preferredTicketRef);
    const routeTicket = findTicketByRef(result.data.tickets, route.ticketRef);
    if (route.page) setPage(route.page);
    if (preferredTicket) {
      setPage("ready");
      setSelectedTicketId(preferredTicket.id);
      if (globalThis.location?.hash !== issueHash(preferredTicket)) {
        globalThis.history?.replaceState(null, "", issueHash(preferredTicket));
      }
    } else if (routeTicket) {
      setPage("ready");
      setSelectedTicketId(routeTicket.id);
    } else {
      setSelectedTicketId((current) => result.data.tickets.some((ticket) => ticket.id === current) ? current : result.data.tickets[0]?.id ?? "");
    }
    setSelectedRuntime((current) => {
      const productRuntime = result.data.runtimes.find((runtime) => runtime.backend === current && isProductRuntime(runtime.backend))
        ?? result.data.runtimes.find((runtime) => isProductRuntime(runtime.backend));
      return productRuntime?.backend ?? current;
    });
  }

  function navigate(nextPage: PageKey) {
    setPage(nextPage);
    if (globalThis.location?.hash !== `#${nextPage}`) {
      globalThis.history?.replaceState(null, "", `#${nextPage}`);
    }
  }

  function selectTicket(ticketId: string) {
    const ticket = data.tickets.find((candidate) => candidate.id === ticketId);
    if (!ticket) return;
    setSelectedTicketId(ticket.id);
    setPage("ready");
    if (globalThis.location?.hash !== issueHash(ticket)) {
      globalThis.history?.replaceState(null, "", issueHash(ticket));
    }
  }

  useEffect(() => {
    let mounted = true;
    refreshWorkbenchData().then(() => {
      if (!mounted) return;
    });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    function applyHashRoute() {
      const route = parseHashRoute();
      if (route.page) setPage(route.page);
      const routeTicket = findTicketByRef(data.tickets, route.ticketRef);
      if (routeTicket) {
        setPage("ready");
        setSelectedTicketId(routeTicket.id);
      }
    }
    globalThis.addEventListener?.("hashchange", applyHashRoute);
    return () => globalThis.removeEventListener?.("hashchange", applyHashRoute);
  }, [data.tickets]);

  return (
    <div className="app-shell">
      <Sidebar data={data} page={page} onNavigate={navigate} />
      <main className="main">
        <PageFrame
          data={data}
          dataSource={dataSource}
          readOnly={readOnly}
          page={page}
          selectedRuntime={selectedRuntime}
          selectedTicket={selectedTicket}
          onNavigate={navigate}
          onRuntimeSelect={setSelectedRuntime}
          onTicketSelect={selectTicket}
          onRefresh={refreshWorkbenchData}
        />
      </main>
      {page === "sources" ? null : (
        <AgentDock
          compactDefault={true}
          runtimes={data.runtimes}
          selectedRuntime={selectedRuntime}
          selectedTicket={selectedTicket}
          onRuntimeSelect={setSelectedRuntime}
        />
      )}
    </div>
  );
}

function isProductRuntime(backend: string) {
  return backend === "codex" || backend === "claude-code";
}

function Sidebar({
  data,
  page,
  onNavigate,
}: {
  data: WorkbenchData;
  page: PageKey;
  onNavigate: (page: PageKey) => void;
}) {
  return (
    <aside className="sidebar">
      <button className="workspace-switch" type="button">
        <span className="workspace-avatar">A</span>
        <span>Ariadne</span>
      </button>
      <button className="sidebar-command" type="button">
        <Search size={16} />
        <span>搜索...</span>
        <kbd>⌘ K</kbd>
      </button>
      <button className="create-button" type="button">
        <Plus size={16} />
        <span>新建 issue</span>
        <kbd>C</kbd>
      </button>
      {navGroups.map((group) => (
        <nav className="nav-group" key={group.label}>
          <p>{group.label}</p>
          {group.items.map((item) => {
            const Icon = item.icon;
            const enabled = ["project", "sources", "tasks", "ready", "diagnostics"].includes(item.key);
            const active = item.key === page;
            return (
              <button
                className={`nav-item ${active ? "active" : ""}`}
                data-page={item.key}
                disabled={!enabled}
                key={item.key}
                type="button"
                onClick={() => enabled && onNavigate(item.key as PageKey)}
              >
                <Icon size={16} />
                <span>{item.label}</span>
                {item.key === "diagnostics" ? <em>{data.inbox.length}</em> : null}
              </button>
            );
          })}
        </nav>
      ))}
      <button className="help-button" type="button">?</button>
    </aside>
  );
}

function PageFrame({
  data,
  dataSource,
  page,
  selectedRuntime,
  selectedTicket,
  onNavigate,
  onRuntimeSelect,
  onTicketSelect,
  onRefresh,
  readOnly,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  readOnly: boolean;
  page: PageKey;
  selectedRuntime: string;
  selectedTicket: AriadneTicket;
  onNavigate: (page: PageKey) => void;
  onRuntimeSelect: (backend: string) => void;
  onTicketSelect: (ticketId: string) => void;
  onRefresh: (preferredTicketRef?: string) => Promise<void>;
}) {
  if (page === "project") return <GoalPage data={data} dataSource={dataSource} onRefresh={onRefresh} onTicketSelect={onTicketSelect} />;
  if (page === "sources") return <KnowledgePage data={data} dataSource={dataSource} onNavigate={onNavigate} onRefresh={onRefresh} />;
  if (page === "tasks") return <TasksPage data={data} dataSource={dataSource} onRefresh={onRefresh} />;
  if (page === "ready") {
    return (
      <IssuesPage
        data={data}
        dataSource={dataSource}
        readOnly={readOnly}
        selectedRuntime={selectedRuntime}
        selectedTicket={selectedTicket}
        onRefresh={onRefresh}
        onTicketSelect={onTicketSelect}
      />
    );
  }
  return (
    <>
      <RuntimesPage
        data={data}
        dataSource={dataSource}
        selectedRuntime={selectedRuntime}
        onRuntimeSelect={onRuntimeSelect}
      />
      <AgentsPage data={data} />
      <SkillsPage data={data} />
      <InboxPage data={data} onNavigate={onNavigate} onTicketSelect={onTicketSelect} />
    </>
  );
}

function PageHeader({
  icon,
  title,
  count,
  description,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  count?: number;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="page-header">
      <div className="title-row">
        {icon}
        <h1>{title}</h1>
        {typeof count === "number" ? <span>{count}</span> : null}
        {description ? <p>{description}</p> : null}
      </div>
      {action}
    </header>
  );
}

function GoalPage({
  data,
  dataSource,
  onRefresh,
  onTicketSelect,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  onRefresh: () => Promise<void>;
  onTicketSelect: (ticketId: string) => void;
}) {
  const goal = data.goal;
  const [projectPath, setProjectPath] = useState("");
  const [projectLabel, setProjectLabel] = useState(data.projectResources?.[0]?.label ?? "");
  const [goalTitle, setGoalTitle] = useState(goal.id === "GOAL-NOT-CREATED" ? "" : goal.title);
  const [northStar, setNorthStar] = useState(goal.id === "GOAL-NOT-CREATED" ? "" : goal.northStar);
  const [targetState, setTargetState] = useState(goal.targetState);
  const [status, setStatus] = useState("");
  const [preferredProjectId, setPreferredProjectId] = useState(goal.targetProjectId ?? data.projectResources?.[0]?.id ?? "");
  const activeProject = data.projectResources?.find((resource) => resource.id === preferredProjectId && resource.available)
    ?? data.projectResources?.find((resource) => resource.available)
    ?? data.projectResources?.[0];

  async function saveProject() {
    if (!projectPath.trim()) return;
    setStatus("正在注册目标项目...");
    try {
      const result = await registerTargetProject({ path: projectPath.trim(), label: projectLabel.trim() || undefined }) as {
        target_project?: { id?: string };
      };
      if (result.target_project?.id) setPreferredProjectId(result.target_project.id);
      await onRefresh();
      setStatus("目标项目已注册。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "目标项目注册失败。");
    }
  }

  async function saveGoal() {
    if (!goalTitle.trim() || !northStar.trim()) return;
    setStatus("正在创建目标...");
    try {
      await createProjectGoal({
        title: goalTitle.trim(),
        north_star: northStar.trim(),
        current_state: "Builder has provided a folder-backed project and external knowledge sources.",
        target_state: targetState.trim() || "Ariadne generates issues, assigns agents, and records evidence from the Web Workbench.",
        target_project_id: activeProject?.id ?? null,
        knowledge_inputs: data.sources.map((source) => source.title),
        feedback_signals: ["Created from Ariadne Workbench web product path."],
      });
      await onRefresh();
      setStatus("目标已创建。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "目标创建失败。");
    }
  }

  return (
    <section className="page">
      <PageHeader
        icon={<Target size={17} />}
        title="当前目标"
        count={1}
        description="目标是输入，任务状态机才是执行中心。"
        action={<button className="outline-button" type="button" onClick={() => { globalThis.location.hash = "knowledge"; }}>导入知识</button>}
      />
      <div className="goal-layout">
        <section className="panel wide">
          <h2>项目和目标输入</h2>
          <div className="form-grid">
            <label>
              <span>项目文件夹</span>
              <input
                disabled={dataSource !== "api"}
                placeholder="/Users/you/code/project"
                value={projectPath}
                onChange={(event) => setProjectPath(event.target.value)}
              />
            </label>
            <label>
              <span>项目名称</span>
              <input
                disabled={dataSource !== "api"}
                placeholder="Mini Code Agent"
                value={projectLabel}
                onChange={(event) => setProjectLabel(event.target.value)}
              />
            </label>
            <button disabled={dataSource !== "api" || !projectPath.trim()} type="button" onClick={() => void saveProject()}>
              注册项目
            </button>
          </div>
          <div className="form-grid goal-form">
            <label>
              <span>目标标题</span>
              <input
                disabled={dataSource !== "api"}
                placeholder="构建 Mini Code Agent"
                value={goalTitle}
                onChange={(event) => setGoalTitle(event.target.value)}
              />
            </label>
            <label>
              <span>北极星目标</span>
              <textarea
                disabled={dataSource !== "api"}
                placeholder="一个文件夹就是一个项目，外部知识进入后生成 issue，并调度 Codex/Claude 完成版本。"
                value={northStar}
                onChange={(event) => setNorthStar(event.target.value)}
              />
            </label>
            <label>
              <span>目标态</span>
              <textarea
                disabled={dataSource !== "api"}
                value={targetState}
                onChange={(event) => setTargetState(event.target.value)}
              />
            </label>
            <button disabled={dataSource !== "api" || !goalTitle.trim() || !northStar.trim()} type="button" onClick={() => void saveGoal()}>
              创建目标
            </button>
          </div>
          {status ? <p className="action-message">{status}</p> : null}
        </section>
        <section className="goal-hero">
          <div className="status-dot active" />
          <p className="eyebrow">{goal.id}</p>
          <h2>{goal.title}</h2>
          <p>{goal.northStar}</p>
          <div className="state-grid">
            <StateBox label="当前态" value={goal.currentState} />
            <StateBox label="目标态" value={goal.targetState} />
          </div>
        </section>
        <section className="panel">
          <h2>知识输入</h2>
          <List items={goal.knowledgeInputs} />
        </section>
        <section className="panel">
          <h2>反馈信号</h2>
          <List items={goal.feedbackSignals} />
        </section>
        <section className="panel wide">
          <h2>由目标派生的当前任务</h2>
          <div className="compact-ticket-list">
            {data.tickets.slice(0, 4).map((ticket) => (
              <button key={ticket.id} type="button" onClick={() => onTicketSelect(ticket.id)}>
                <span>{ticket.key}</span>
                <strong>{ticket.title}</strong>
                <em>{statusLabel(ticket.status)}</em>
              </button>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function KnowledgePage({
  data,
  dataSource,
  onNavigate,
  onRefresh,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  onNavigate: (page: PageKey) => void;
  onRefresh: () => Promise<void>;
}) {
  const [selectedSourceId, setSelectedSourceId] = useState(data.sources[0]?.id ?? "");
  const [sourceTitle, setSourceTitle] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceType, setSourceType] = useState<SourceFormType>("blog");
  const [sourceContent, setSourceContent] = useState("");
  const [actionStatus, setActionStatus] = useState("");
  const selectedSource = data.sources.find((source) => source.id === selectedSourceId) ?? data.sources[0];
  const selectedUnderstanding = data.sourceUnderstandings.find((item) => item.sourceId === selectedSourceId);
  const [selectedChangeId, setSelectedChangeId] = useState(data.backlogChanges[0]?.id ?? "");
  const selectedChange = data.backlogChanges.find((change) => change.id === selectedChangeId) ?? data.backlogChanges[0];
  const [previewStatus, setPreviewStatus] = useState(data.backlogMutationPreview.status);

  useEffect(() => {
    if (!data.sources.some((source) => source.id === selectedSourceId)) {
      setSelectedSourceId(data.sources[0]?.id ?? "");
    }
    if (!data.backlogChanges.some((change) => change.id === selectedChangeId)) {
      setSelectedChangeId(data.backlogChanges[0]?.id ?? "");
    }
    setPreviewStatus(data.backlogMutationPreview.status);
  }, [data.sources, data.backlogChanges, data.backlogMutationPreview.status, selectedSourceId, selectedChangeId]);

  function selectSource(sourceId: string) {
    setSelectedSourceId(sourceId);
  }

  function updateSourceUrl(value: string) {
    setSourceUrl(value);
    const inferred = inferSourceInput(value);
    if (inferred.title && !sourceTitle.trim()) {
      setSourceTitle(inferred.title);
    }
    setSourceType(inferred.sourceType);
  }

  const groupedChanges = groupBacklogChanges(data.backlogChanges);
  const activeGoal = data.goal.id !== "GOAL-NOT-CREATED" ? data.goal : undefined;
  const activeProject = data.projectResources?.find((resource) => resource.id === activeGoal?.targetProjectId && resource.available)
    ?? data.projectResources?.find((resource) => resource.available)
    ?? data.projectResources?.[0];
  const activePreviewId = data.backlogMutationPreview.previewId;
  const analyzedSourceIds = data.sources
    .filter((source) => ["analyzed", "partial"].includes(source.analysisStatus ?? source.status))
    .filter((source) => (source.artifactIds?.length ?? 0) > 0)
    .map((source) => source.id);
  const selectedSourceEvents = selectedSource
    ? data.sourceEvents.filter((event) => event.sourceId === selectedSource.id)
    : [];
  const selectedOutputs = selectedSource
    ? (data.sourceArtifacts ?? []).filter((artifact) => artifact.sourceDocumentId === selectedSource.id)
    : [];
  const selectedSourceHasFetch = selectedSourceEvents.some((event) => event.eventType.startsWith("source.fetch."));

  async function addSource() {
    if (!sourceUrl.trim()) return;
    const inferred = inferSourceInput(sourceUrl);
    const title = sourceTitle.trim() || inferred.title || sourceUrl.trim();
    const summary = sourceContent.trim() || inferred.summary;
    setActionStatus("正在添加并分析输入...");
    try {
      const result = await createSource({
        title,
        source_type: sourceType || inferred.sourceType,
        source_role: inferred.sourceRole,
        path_or_url: sourceUrl.trim(),
        content: sourceContent.trim(),
        summary,
        auto_analyze: true,
      });
      setSourceTitle("");
      setSourceUrl("");
      setSourceContent("");
      await onRefresh();
      setSelectedSourceId(result.source.id);
      setActionStatus(result.duplicate ? "这个输入已经存在，已打开现有记录。" : "分析完成。Ariadne 已生成理解结果和证据。");
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "添加或分析失败。");
    }
  }

  async function generateIssues() {
    if (!activeGoal) {
      setActionStatus("请先在目标页创建目标。");
      return;
    }
    if (!analyzedSourceIds.length) {
      setActionStatus("还没有分析完成的输入。请先添加并分析项目输入。");
      return;
    }
    setActionStatus(`将使用 ${analyzedSourceIds.length} 个已分析输入生成任务，跳过未分析输入。`);
    try {
      const result = await createIssueFactoryPreview({
        goal_id: activeGoal.id,
        source_ids: analyzedSourceIds,
        target_project_id: activeProject?.id ?? null,
      });
      await onRefresh();
      setSelectedChangeId(result.preview.operations[0]?.id ?? "");
      setActionStatus(`已生成 ${result.preview.operations.length} 个任务建议。请查看任务建议后应用。`);
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "任务建议生成失败。");
    }
  }

  async function analyzeSelectedSource() {
    if (!selectedSource) return;
    setActionStatus("正在重新分析...");
    try {
      await analyzeSource(selectedSource.id);
      await onRefresh();
      setActionStatus("重新分析完成。");
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "重新分析失败。");
    }
  }

  async function applyPreview() {
    if (!activePreviewId) {
      setActionStatus("还没有可应用的任务预览。");
      return;
    }
    setActionStatus("正在应用任务变更...");
    try {
      await applyIssueFactoryPreview(activePreviewId);
      await onRefresh();
      setPreviewStatus("applied");
      setActionStatus("任务建议已应用，新的项目 issue 已写入任务列表。");
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "应用任务变更失败。");
    }
  }

  return (
    <section className="page full-bleed knowledge-page">
      <PageHeader
        icon={<BookOpenText size={17} />}
        title="项目输入"
        count={data.sources.length}
        action={
          <div className="toolbar">
            <button type="button" onClick={() => setActionStatus("粘贴 URL、GitHub 仓库、本地路径或笔记，然后点击添加并分析。")}>添加项目输入</button>
            <button className="primary-action" disabled={dataSource !== "api"} type="button" onClick={() => void generateIssues()}>查看任务建议</button>
          </div>
        }
      />
      <section className="panel source-input-panel">
        <h2>添加项目输入</h2>
        <p className="panel-subtitle">粘贴链接、GitHub 仓库、本地路径、论文或笔记。Ariadne 会自动分析并提取可用于生成任务的证据。</p>
        <ol className="source-cta-sequence">
          <li className={data.sources.length ? "done" : "active"}>添加并分析</li>
          <li className={analyzedSourceIds.length ? "active" : ""}>查看任务建议</li>
          <li className={activePreviewId ? "active" : ""}>应用任务变更</li>
          <li className={previewStatus === "applied" ? "active" : ""}>打开新任务</li>
          <li>分配给智能体</li>
        </ol>
        <div className="form-grid">
          <label>
            <span>类型</span>
            <select disabled={dataSource !== "api"} value={sourceType} onChange={(event) => setSourceType(event.target.value as typeof sourceType)}>
              <option value="blog">博客</option>
              <option value="paper">论文</option>
              <option value="github_repo">GitHub 仓库</option>
              <option value="note">手动笔记</option>
            </select>
          </label>
          <label>
            <span>标题</span>
            <input disabled={dataSource !== "api"} value={sourceTitle} onChange={(event) => setSourceTitle(event.target.value)} placeholder="自动从链接生成，可手动修改" />
          </label>
          <label>
            <span>路径或 URL</span>
            <input disabled={dataSource !== "api"} value={sourceUrl} onChange={(event) => updateSourceUrl(event.target.value)} placeholder="粘贴 URL，例如 https://github.com/SWE-agent/mini-swe-agent/" />
          </label>
          <label className="wide-field">
            <span>摘要或摘录</span>
            <textarea disabled={dataSource !== "api"} value={sourceContent} onChange={(event) => setSourceContent(event.target.value)} placeholder="可选。留空时 Ariadne 会先根据链接生成基础摘要，分析阶段再提取证据。" />
          </label>
          <button disabled={dataSource !== "api" || !sourceUrl.trim()} type="button" onClick={() => void addSource()}>
            添加并分析
          </button>
        </div>
        {actionStatus ? <p className="action-message">{actionStatus}</p> : null}
      </section>
      <div className="knowledge-layout">
        <section className="knowledge-column source-column">
          <ColumnHeader title="项目输入" meta={`${data.sources.length} 个材料`} />
          <div className="source-list">
            {data.sources.map((source) => (
              (() => {
                const understanding = data.sourceUnderstandings.find((item) => item.sourceId === source.id);
                const sourceEvents = data.sourceEvents.filter((event) => event.sourceId === source.id);
                const hasFetch = sourceEvents.some((event) => event.eventType.startsWith("source.fetch."));
                const hasArtifacts = (source.artifactIds?.length ?? 0) > 0;
                const analysis = source.sourceType === "github_repo" && !hasFetch && !hasArtifacts
                  ? "已添加，尚未抓取仓库"
                  : understanding?.analysisLabel ?? sourceAnalysisLabel(source.analysisStatus ?? source.status);
                return (
              <button
                className={`source-row ${source.id === selectedSource?.id ? "selected" : ""}`}
                data-source-id={source.id}
                key={source.id}
                type="button"
                onClick={() => selectSource(source.id)}
              >
                <span className={`source-type ${source.sourceType}`}>{sourceTypeLabel(source.sourceType)}</span>
                <strong>{source.title}</strong>
                <em className={`source-status ${source.analysisStatus ?? source.status}`}>{analysis}</em>
                <small>{source.ingestedAt}</small>
              </button>
                );
              })()
            ))}
          </div>
        </section>

        <section className="knowledge-column understanding-column">
          <ColumnHeader title="Ariadne 理解" meta={selectedUnderstanding?.analysisLabel ?? "已添加"} />
          {selectedUnderstanding ? (
            <article className="understanding-panel">
              <header>
                <div>
                  <strong>{selectedUnderstanding.displayTitle}</strong>
                  <span>{selectedUnderstanding.kindLabel} · {selectedUnderstanding.roleLabel} · 许可证 {selectedUnderstanding.licenseRiskLabel}</span>
                </div>
              </header>
              <section>
                <h3>处理过程</h3>
                {selectedSourceEvents.length ? (
                  <div className="source-timeline">
                    {selectedSourceEvents.map((event) => (
                      <div className="timeline-row" key={event.id}>
                        <span>{event.label}</span>
                        <time>{event.createdAt}</time>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty-column">
                    {selectedSource?.sourceType === "github_repo" && !selectedSourceHasFetch
                      ? "已添加，尚未抓取仓库。点击重新分析会触发仓库抓取和结构化理解。"
                      : "还没有处理事件。"}
                  </p>
                )}
              </section>
              <section>
                <h3>Ariadne 理解到</h3>
                <ul>
                  {selectedUnderstanding.whatAriadneUnderstood.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </section>
              <section>
                <h3>关键证据</h3>
                {selectedUnderstanding.evidenceItems.length ? selectedUnderstanding.evidenceItems.map((item) => (
                  <div className="evidence-row" key={`${item.locator}-${item.claim}`}>
                    <code>{item.locator}</code>
                    <p>{item.summary}</p>
                    <small>{item.claim} · 可信度 {item.confidenceLabel}</small>
                  </div>
                )) : <p className="empty-column">还没有证据。点击重新分析。</p>}
              </section>
              <section>
                <h3>影响的任务</h3>
                <div className="module-row">
                  {selectedUnderstanding.impactedTicketKeys.length ? selectedUnderstanding.impactedTicketKeys.map((key) => (
                    <button type="button" key={key} onClick={() => onNavigate("ready")}>{key}</button>
                  )) : <span>还没有生成任务建议</span>}
                </div>
              </section>
              <section>
                <h3>风险</h3>
                {selectedUnderstanding.risks.length ? (
                  <ul className="risk-list">
                    {selectedUnderstanding.risks.map((risk) => <li key={risk}>{risk}</li>)}
                  </ul>
                ) : <p className="empty-column">暂未发现明显风险。</p>}
              </section>
              <section>
                <h3>已生成产物</h3>
                <div className="module-row">
                  {selectedUnderstanding.generatedOutputs.map((item) => <span key={item}>{item}</span>)}
                  {selectedOutputs.length === 0 ? <span>尚未生成结构化产物</span> : null}
                </div>
              </section>
              <div className="apply-row compact-actions">
                <button disabled={!selectedSource} type="button" onClick={() => void analyzeSelectedSource()}>重新分析</button>
                <button disabled type="button" title="此动作还未接入后端">标记重要</button>
                <button disabled type="button" title="此动作还未接入后端">忽略</button>
              </div>
            </article>
          ) : <p className="empty-column">选择一个输入查看 Ariadne 的理解结果。</p>}
        </section>

        <section className="knowledge-column changes-column">
          <ColumnHeader title="任务建议" meta={`${analyzedSourceIds.length} 个已分析输入`} />
          <p className="hint-text">将使用已分析输入生成任务；跳过未分析输入。</p>
          <BacklogChangeGroup title="新增" emptyLabel="新增" kind="added" changes={groupedChanges.added} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="更新" emptyLabel="更新" kind="updated" changes={groupedChanges.updated} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="延后" emptyLabel="延后" kind="deferred" changes={groupedChanges.deferred} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="拒绝" emptyLabel="拒绝" kind="rejected" changes={groupedChanges.rejected} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <div className="apply-row">
            <button className="primary-action" disabled={dataSource !== "api"} type="button" onClick={() => void generateIssues()}>
              查看任务建议
            </button>
            <span>将使用已分析输入生成任务；跳过未分析输入。</span>
          </div>
          <div className="apply-row">
            <button disabled={dataSource !== "api" || !activePreviewId || previewStatus === "applied"} type="button" onClick={() => void applyPreview()}>
              {previewStatus === "applied" ? "已应用" : "应用任务变更"}
            </button>
            <span>{previewStatusLabel(previewStatus)} · 最近预览：{data.backlogMutationPreview.lastPreviewAt}</span>
          </div>
        </section>
      </div>
      <footer className="mutation-preview">
        <strong>任务变更预览</strong>
        <span className="added">新增 {data.backlogMutationPreview.added}</span>
        <span className="updated">更新 {data.backlogMutationPreview.updated}</span>
        <span className="deferred">延后 {data.backlogMutationPreview.deferred}</span>
        <span className="rejected">拒绝 {data.backlogMutationPreview.rejected}</span>
        <span className="unsafe">不安全 {data.backlogMutationPreview.unsafe}</span>
        <em>{previewStatusLabel(previewStatus)}</em>
      </footer>
    </section>
  );
}

function TasksPage({
  data,
  dataSource,
  onRefresh,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  onRefresh: () => Promise<void>;
}) {
  const [selectedChangeId, setSelectedChangeId] = useState(data.backlogChanges[0]?.id ?? "");
  const [previewStatus, setPreviewStatus] = useState(data.backlogMutationPreview.status);
  const [actionStatus, setActionStatus] = useState("");
  const selectedChange = data.backlogChanges.find((change) => change.id === selectedChangeId)
    ?? data.backlogChanges[0];
  const groupedChanges = groupBacklogChanges(data.backlogChanges);
  const activeGoal = data.goal.id !== "GOAL-NOT-CREATED" ? data.goal : undefined;
  const activeProject = data.projectResources?.find((resource) => resource.id === activeGoal?.targetProjectId && resource.available)
    ?? data.projectResources?.find((resource) => resource.available)
    ?? data.projectResources?.[0];
  const activePreviewId = data.backlogMutationPreview.previewId;
  const analyzedSourceIds = data.sourceUnderstandings
    .filter((item) => item.analysisLabel === "分析完成")
    .map((item) => item.sourceId);
  const traceSteps = selectedChange
    ? data.traceSteps.filter((step) => !step.backlogChangeId || step.backlogChangeId === selectedChange.id)
    : data.traceSteps.slice(0, 8);

  useEffect(() => {
    if (!data.backlogChanges.some((change) => change.id === selectedChangeId)) {
      setSelectedChangeId(data.backlogChanges[0]?.id ?? "");
    }
    setPreviewStatus(data.backlogMutationPreview.status);
  }, [data.backlogChanges, data.backlogMutationPreview.status, selectedChangeId]);

  async function generateIssues() {
    if (!activeGoal) {
      setActionStatus("请先在项目页创建目标。");
      return;
    }
    if (!analyzedSourceIds.length) {
      setActionStatus("还没有分析完成的输入。请先到项目输入页添加并分析。");
      return;
    }
    setActionStatus(`将使用 ${analyzedSourceIds.length} 个已分析输入生成任务，跳过未分析输入。`);
    try {
      const result = await createIssueFactoryPreview({
        goal_id: activeGoal.id,
        source_ids: analyzedSourceIds,
        target_project_id: activeProject?.id ?? null,
      });
      await onRefresh();
      setSelectedChangeId(result.preview.operations[0]?.id ?? "");
      setActionStatus(`已生成 ${result.preview.operations.length} 个任务建议。`);
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "任务建议生成失败。");
    }
  }

  async function applyPreview() {
    if (!activePreviewId) {
      setActionStatus("还没有可应用的任务预览。");
      return;
    }
    setActionStatus("正在应用任务变更...");
    try {
      await applyIssueFactoryPreview(activePreviewId);
      await onRefresh();
      setPreviewStatus("applied");
      setActionStatus("任务变更已应用，新的项目 issue 已写入任务列表。");
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "应用任务变更失败。");
    }
  }

  return (
    <section className="page full-bleed tasks-page">
      <PageHeader
        icon={<ListTodo size={17} />}
        title="任务工厂"
        count={data.backlogChanges.length}
        action={
          <div className="toolbar">
            <button className="primary-action" disabled={dataSource !== "api"} type="button" onClick={() => void generateIssues()}>
              查看任务建议
            </button>
            <button disabled={dataSource !== "api" || !activePreviewId || previewStatus === "applied"} type="button" onClick={() => void applyPreview()}>
              {previewStatus === "applied" ? "已应用" : "应用任务变更"}
            </button>
          </div>
        }
      />
      <section className="panel compiler-summary">
        <div>
          <h2>任务建议生成器</h2>
          <p>输入：项目目标、{analyzedSourceIds.length} 个已分析项目输入、{data.sourceArtifacts?.length ?? 0} 个结构化产物、{data.sourceEvidence?.length ?? 0} 条证据。将使用已分析输入生成任务；跳过未分析输入。</p>
        </div>
        <div className="summary-metrics">
          <span>新增 {data.backlogMutationPreview.added}</span>
          <span>更新 {data.backlogMutationPreview.updated}</span>
          <span>延后 {data.backlogMutationPreview.deferred}</span>
          <span>不安全 {data.backlogMutationPreview.unsafe}</span>
          <em>{previewStatusLabel(previewStatus)}</em>
        </div>
        {actionStatus ? <p className="action-message">{actionStatus}</p> : null}
      </section>
      <div className="knowledge-layout">
        <section className="knowledge-column changes-column">
          <ColumnHeader title="任务变更" meta={data.backlogMutationPreview.previewId ?? "还没有预览"} />
          <BacklogChangeGroup title="新增" emptyLabel="新增" kind="added" changes={groupedChanges.added} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="更新" emptyLabel="更新" kind="updated" changes={groupedChanges.updated} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="延后" emptyLabel="延后" kind="deferred" changes={groupedChanges.deferred} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="拒绝" emptyLabel="拒绝" kind="rejected" changes={groupedChanges.rejected} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
        </section>

        <section className="knowledge-column cards-column">
          <ColumnHeader title="选中任务约束" meta={selectedChange?.ticketKey ?? "未选择"} />
          {selectedChange ? (
            <article className="knowledge-card selected">
              <header>
                <div>
                  <strong>{selectedChange.title}</strong>
                  <small>{selectedChange.ticketKey} · {buildDecisionLabel(selectedChange.buildDecision)}</small>
                </div>
                <span className="primary-badge">{selectedChange.priority}</span>
              </header>
              <section>
                <h3>生成原因</h3>
                <p>{selectedChange.goalReason || selectedChange.reason}</p>
              </section>
              <section>
                <h3>证据引用</h3>
                <div className="evidence-list">
                  {(selectedChange.evidenceRefs ?? []).map((item) => <code key={item}>{item}</code>)}
                </div>
              </section>
              <section>
                <h3>验收标准</h3>
                <ul className="risk-list">
                  {(selectedChange.acceptanceCriteria ?? []).map((item) => <li key={item}>{item}</li>)}
                </ul>
              </section>
              <section>
                <h3>受影响模块</h3>
                <div className="module-row">
                  {(selectedChange.affectedModules ?? []).map((item) => <span key={item}>{item}</span>)}
                </div>
              </section>
              <div className="card-meta-grid">
                <section>
                  <h3>Build Context</h3>
                  <code>{selectedChange.buildContextId ?? "未记录"}</code>
                </section>
                <section>
                  <h3>Source Artifacts</h3>
                  <p>{(selectedChange.sourceArtifactIds ?? []).length} 个 artifact 参与编译。</p>
                </section>
              </div>
            </article>
          ) : (
            <p className="empty-column">还没有任务变更。先添加输入并生成任务。</p>
          )}
        </section>

        <aside className="knowledge-column trace-column">
          <ColumnHeader title="编译追踪" meta={selectedChange?.ticketKey ?? "全部"} />
          <ol className="trace-list">
            {traceSteps.length ? traceSteps.map((step) => (
              <li key={step.id}>
                <span className="trace-dot" />
                <div>
                  <h3>{traceLabel(step.label)}</h3>
                  <p>{step.summary}</p>
                  <code>{step.artifactPath}</code>
                  <small>{step.timestamp}</small>
                </div>
              </li>
            )) : <li className="trace-empty">还没有编译追踪。生成任务后会显示 Source {"->"} Evidence {"->"} Ticket Delta。</li>}
          </ol>
        </aside>
      </div>
    </section>
  );
}

function ColumnHeader({ title, meta }: { title: string; meta?: string }) {
  return (
    <header className="column-header">
      <h2>{title}</h2>
      {meta ? <span>{meta}</span> : null}
    </header>
  );
}

function BacklogChangeGroup({
  title,
  emptyLabel,
  kind,
  changes,
  selectedId,
  onSelect,
}: {
  title: string;
  emptyLabel: string;
  kind: string;
  changes: WorkbenchData["backlogChanges"];
  selectedId?: string;
  onSelect: (changeId: string) => void;
}) {
  return (
    <section className="change-group">
      <h3 className={kind}>{title} ({changes.length})</h3>
      {changes.length ? changes.map((change) => (
        <button
          className={`change-row ${change.id === selectedId ? "selected" : ""}`}
          data-change-id={change.id}
          key={change.id}
          type="button"
          onClick={() => onSelect(change.id)}
        >
          <strong>{change.ticketKey}</strong>
          <span>{change.title}</span>
          <p>{change.reason}</p>
          <em>{change.priority}</em>
          <small>{change.suggestedOwnerAgent}</small>
        </button>
      )) : <p className="no-changes">暂无{emptyLabel}任务。</p>}
    </section>
  );
}

function groupBacklogChanges(changes: WorkbenchData["backlogChanges"]) {
  return {
    added: changes.filter((change) => change.kind === "added"),
    updated: changes.filter((change) => change.kind === "updated"),
    deferred: changes.filter((change) => change.kind === "deferred"),
    rejected: changes.filter((change) => change.kind === "rejected"),
  };
}

function IssuesPage({
  data,
  dataSource,
  readOnly,
  selectedRuntime,
  selectedTicket,
  onRefresh,
  onTicketSelect,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  readOnly: boolean;
  selectedRuntime: string;
  selectedTicket: AriadneTicket;
  onRefresh: (preferredTicketRef?: string) => Promise<void>;
  onTicketSelect: (ticketId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const visibleTickets = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return data.tickets;
    if (/^ari-\d+$/.test(needle)) {
      return data.tickets.filter(
        (ticket) => ticket.key.toLowerCase() === needle || ticket.id.toLowerCase() === needle,
      );
    }
    return data.tickets.filter((ticket) => {
      return [
        ticket.key,
        ticket.title,
        ticket.summary,
        ticket.owner,
        ticket.decision,
        ticket.reviewVerdict,
        ticket.backendSmoke?.backendName ?? "",
        ticket.github?.branch ?? "",
      ]
        .join(" ")
        .toLowerCase()
        .includes(needle);
    });
  }, [data.tickets, query]);
  const grouped = useMemo(() => {
    return statusColumns.map((column) => ({
      ...column,
      tickets: visibleTickets.filter((ticket) => ticket.status === column.status),
    }));
  }, [visibleTickets]);

  return (
    <section className="page full-bleed">
      <PageHeader
        icon={<ListTodo size={17} />}
        title="任务"
        action={
          <div className="toolbar">
            <button type="button">全部</button>
            <button type="button">成员</button>
            <button type="button">智能体</button>
            <button type="button">筛选</button>
            <button type="button">看板</button>
          </div>
        }
      />
      <div className="issue-search-bar">
        <Search size={16} />
        <input
          aria-label="按任务编号、标题、负责人、后端或分支搜索"
          placeholder="搜索任务编号、标题、负责人、后端..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <span>{visibleTickets.length} / {data.tickets.length}</span>
      </div>
      <div className="issues-layout">
        <div className="kanban">
          {grouped.map((column) => (
            <section className={`kanban-column ${column.tone}`} key={column.status}>
              <header>
                <span className="ring" />
                <h2>{column.label}</h2>
                <em>{column.tickets.length}</em>
                <button type="button">•••</button>
                <button type="button">+</button>
              </header>
              {column.tickets.length === 0 ? (
                <p className="empty-column">无 issue</p>
              ) : (
                column.tickets.map((ticket) => (
                  <TicketCard
                    key={ticket.id}
                    ticket={ticket}
                    selected={ticket.id === selectedTicket.id}
                    onSelect={onTicketSelect}
                  />
                ))
              )}
            </section>
          ))}
        </div>
        <TicketInspector
          data={data}
          dataSource={dataSource}
          readOnly={readOnly}
          selectedRuntime={selectedRuntime}
          ticket={selectedTicket}
          onRefresh={onRefresh}
        />
      </div>
    </section>
  );
}

function TicketCard({
  ticket,
  selected,
  onSelect,
}: {
  ticket: AriadneTicket;
  selected: boolean;
  onSelect: (ticketId: string) => void;
}) {
  return (
    <button className={`issue-card ${selected ? "selected" : ""}`} type="button" onClick={() => onSelect(ticket.id)}>
      <span className="issue-key">{ticket.key}</span>
      <strong>{ticket.title}</strong>
      <p>{ticket.summary}</p>
      <span className="project-pill">📁 Ariadne v1.0</span>
      <footer>
        <span>{ticket.owner}</span>
        <em>{statusLabel(ticket.reviewVerdict)}</em>
      </footer>
    </button>
  );
}

function TicketInspector({
  data,
  dataSource,
  readOnly,
  selectedRuntime,
  ticket,
  onRefresh,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  readOnly: boolean;
  selectedRuntime: string;
  ticket: AriadneTicket;
  onRefresh: (preferredTicketRef?: string) => Promise<void>;
}) {
  const targetProject = data.projectResources?.find((resource) => resource.id === ticket.targetProjectId && resource.available)
    ?? data.projectResources?.find((resource) => resource.available)
    ?? data.projectResources?.[0];
  const ticketAssignments = data.assignments?.filter((assignment) =>
    assignment.ticketId === ticket.id || assignment.ticketKey === ticket.key,
  ) ?? [];
  const latestAssignment = ticketAssignments.find((assignment) => assignment.id === ticket.latestAssignmentId)
    ?? [...ticketAssignments].sort((left, right) => (right.createdAt ?? "").localeCompare(left.createdAt ?? ""))[0];
  const productRuntime = selectableProductionRuntimes(data.runtimes).find((runtime) => runtime.backend === selectedRuntime)
    ?? selectableProductionRuntimes(data.runtimes)[0];
  const {
    actionMessage,
    actionState,
    assignmentEvents,
    assignSelectedTicket,
    commentDraft,
    commentState,
    daemonActionState,
    mutationReady,
    postComment,
    runSelectedAssignment,
    setCommentDraft,
    startLocalDaemon,
    stopLocalDaemon,
    watchAssignmentEvents,
  } = useTicketAgentControl({
    dataSource,
    latestAssignment,
    onRefresh,
    productRuntime,
    readOnly,
    targetProject,
    ticket,
  });

  return (
    <aside className="inspector">
      <section className="inspector-header">
        <span className="issue-key">{ticket.key}</span>
        <h2>{ticket.title}</h2>
        <p>{ticket.summary}</p>
      </section>
      <PropertyGrid
        rows={[
          ["状态", statusLabel(ticket.status)],
          ["负责人", ticket.owner],
          ["决策", buildDecisionLabel(ticket.decision)],
          ["来源", ticket.source],
          ["评审", statusLabel(ticket.reviewVerdict)],
          ["记忆", fallbackText(ticket.memoryPath)],
          ["后续任务", fallbackText(ticket.nextTicketsPath)],
        ]}
      />
      <section className="panel nested action-panel">
        <h3>智能体控制</h3>
        <p className="muted">
          {mutationReady
            ? `API 模式 · 目标 ${targetProject?.label} · 后端 ${productRuntime?.backend}`
            : "未连接产品 API，或缺少可用目标/运行时。先启动 ari workbench serve 并注册目标项目。"}
        </p>
        <div className="daemon-strip">
          <strong>本地运行时：{statusLabel(data.daemonStatus.status)}</strong>
          <span>{data.daemonStatus.backgroundRunning ? "后台循环运行中" : "后台循环未运行"}</span>
          <span>{data.daemonStatus.externalExecutionAuthorized ? "已授权 Codex/Claude" : "未授权外部执行"}</span>
          <span>可领取 {data.daemonStatus.claimableAssignmentCount}</span>
          <span>{data.daemonStatus.currentTicketKey ?? "无当前任务"}</span>
        </div>
        <div className="action-row">
          <button disabled={!mutationReady || actionState !== "idle"} type="button" onClick={assignSelectedTicket}>
            {assignTicketButtonLabel(actionState)}
          </button>
          <button disabled={!mutationReady || actionState !== "idle"} type="button" onClick={runSelectedAssignment}>
            {actionState === "running" ? runAssignmentButtonLabel(actionState) : "分配后由运行时自动 claim"}
          </button>
          <button disabled={dataSource !== "api" || daemonActionState !== "idle"} type="button" onClick={() => void startLocalDaemon()}>
            {daemonActionState === "starting" ? "启动中..." : "授权 Codex/Claude 并启动运行时"}
          </button>
          <button disabled={dataSource !== "api" || daemonActionState !== "idle"} type="button" onClick={() => void stopLocalDaemon()}>
            {daemonActionState === "stopping" ? "停止中..." : "停止本地运行时"}
          </button>
          <button disabled={dataSource !== "api" || !latestAssignment?.id} type="button" onClick={() => void watchAssignmentEvents()}>
            {watchRunEventsButtonLabel(assignmentEvents.length ? "watching" : "idle")}
          </button>
        </div>
        <p className="muted">最近 assignment：{fallbackText(latestAssignment?.id)}</p>
        <div className="comment-row">
          <input
            aria-label="添加任务评论"
            disabled={!mutationReady || commentState !== "idle"}
            placeholder="添加任务评论..."
            value={commentDraft}
            onChange={(event) => setCommentDraft(event.target.value)}
          />
          <button disabled={!mutationReady || commentState !== "idle" || !commentDraft.trim()} type="button" onClick={() => void postComment()}>
            {addTicketCommentButtonLabel(commentState)}
          </button>
        </div>
        {assignmentEvents.length ? (
          <div className="event-list">
            {assignmentEvents.map((event) => (
              <p key={event.id}>
                <strong>{event.stage}</strong>
                <span>{event.summary}</span>
              </p>
            ))}
          </div>
        ) : null}
        {actionMessage ? <p className="action-message">{actionMessage}</p> : null}
      </section>
      <GitHubEvidencePanel ticket={ticket} />
      <ExecutionEvidencePanel evidence={ticket.executionEvidence} />
      <BackendSmokePanel smoke={ticket.backendSmoke} />
      <LLMAgentEvidencePanel agents={ticket.llmAgents ?? []} />
      <FeishuEvidencePanel feishu={ticket.feishu} />
      <ReleaseEvidencePanel evidence={ticket.releaseEvidence} />
      <section className="panel nested">
        <h3>运行进度时间线</h3>
        <Timeline items={ticket.progress} />
      </section>
      <section className="panel nested">
        <h3>验收标准</h3>
        <List items={ticket.acceptance} />
      </section>
      <section className="panel nested">
        <h3>变更文件</h3>
        <div className="file-list">
          {ticket.changedFiles.length ? ticket.changedFiles.map((file) => <code key={file}>{file}</code>) : <span>暂无 diff</span>}
        </div>
      </section>
    </aside>
  );
}

function ExecutionEvidencePanel({ evidence }: { evidence?: TicketExecutionEvidence }) {
  if (!evidence) {
    return (
      <section className="panel nested">
        <h3>执行证据</h3>
        <p className="muted">还没有 execution / diff / tests / review 回流。</p>
      </section>
    );
  }
  return (
    <section className="panel nested execution-evidence-panel">
      <h3>执行证据</h3>
      <PropertyGrid
        rows={[
          ["Assignment", fallbackText(evidence.assignmentId)],
          ["状态", statusLabel(evidence.assignmentStatus ?? "unknown")],
          ["后端", fallbackText(evidence.backendName)],
          ["执行结果", fallbackText(evidence.executionResultId)],
          ["阻塞", evidence.blocked ? fallbackText(evidence.blockReason, "已阻塞") : "否"],
          ["失败类型", fallbackText(evidence.failureReason ?? evidence.assignmentFailureReason)],
          ["退出码", String(evidence.exitCode ?? "未记录")],
          ["测试命令", fallbackText(evidence.testCommand)],
          ["测试退出码", String(evidence.testExitCode ?? "未记录")],
          ["评审", statusLabel(evidence.reviewVerdict ?? "pending")],
          ["Handoff", fallbackText(evidence.handoffFile)],
          ["Diff", fallbackText(evidence.diffArtifactPath)],
          ["日志", fallbackText(evidence.executionLogArtifactPath)],
          ["Memory", fallbackText(evidence.memoryPath)],
          ["Feishu Plan", fallbackText(evidence.feishuPlanPath)],
          ["Next Tickets", fallbackText(evidence.nextTicketsPath)],
        ]}
      />
      {evidence.assignmentBlocker ? <p className="muted">{evidence.assignmentBlocker}</p> : null}
      {evidence.command ? <code className="wide-code">{evidence.command}</code> : null}
      {evidence.changedFiles.length ? (
        <div className="file-list">
          {evidence.changedFiles.map((file) => <code key={file}>{file}</code>)}
        </div>
      ) : null}
      {evidence.stdoutExcerpt || evidence.stderrExcerpt || evidence.testStdoutExcerpt || evidence.testStderrExcerpt ? (
        <div className="log-grid">
          {evidence.stdoutExcerpt ? <pre>stdout{`\n${evidence.stdoutExcerpt}`}</pre> : null}
          {evidence.stderrExcerpt ? <pre>stderr{`\n${evidence.stderrExcerpt}`}</pre> : null}
          {evidence.testStdoutExcerpt ? <pre>test stdout{`\n${evidence.testStdoutExcerpt}`}</pre> : null}
          {evidence.testStderrExcerpt ? <pre>test stderr{`\n${evidence.testStderrExcerpt}`}</pre> : null}
        </div>
      ) : null}
      {evidence.warnings.length ? (
        <div className="check-summary">
          {evidence.warnings.map((warning) => <span key={warning}>{warning}</span>)}
        </div>
      ) : null}
    </section>
  );
}

function LLMAgentEvidencePanel({ agents }: { agents: LLMAgentEvidence[] }) {
  if (!agents.length) {
    return (
      <section className="panel nested">
        <h3>上游 LLM 智能体</h3>
        <p className="muted">还没有记录上游 LLM 智能体证据。</p>
      </section>
    );
  }
  return (
    <section className="panel nested llm-panel">
      <h3>上游 LLM 智能体</h3>
      <div className="llm-agent-list">
        {agents.map((agent) => (
          <div className="llm-agent-row" key={`${agent.role}-${agent.id}`}>
            <strong>{agent.role}</strong>
            <span className={`state ${agent.succeeded ? "online" : "offline"}`}>
              {resultLabel(agent.succeeded, true)}
            </span>
            <span>{agent.provider}</span>
            <span>{agent.model}</span>
            <span>{agent.totalTokens ? `${agent.totalTokens} token` : "用量未记录"}</span>
            <p>{agent.summary ?? agent.decision ?? "未记录摘要。"}</p>
            <code>{agent.path}</code>
          </div>
        ))}
      </div>
    </section>
  );
}

function FeishuEvidencePanel({ feishu }: { feishu?: FeishuTicketEvidence }) {
  if (!feishu) {
    return (
      <section className="panel nested">
        <h3>Feishu</h3>
        <p className="muted">还没有记录飞书写入证据。</p>
      </section>
    );
  }
  const status = feishu.ok && !feishu.blocked && !feishu.dryRun ? "通过" : feishu.blocked ? "已阻塞" : "失败";
  return (
    <section className="panel nested feishu-panel">
      <h3>Feishu</h3>
      <PropertyGrid
        rows={[
          ["状态", status],
          ["演练模式", yesNo(feishu.dryRun)],
          ["返回码", String(feishu.returncode ?? "未记录")],
          ["文档", feishu.documentUrl ?? feishu.documentId ?? "未记录"],
          ["创建时间", feishu.createdAt],
          ["证据", feishu.path],
        ]}
      />
      {feishu.documentUrl ? <a href={feishu.documentUrl}>打开飞书文档</a> : null}
      {feishu.operationSummary ? <p>{feishu.operationSummary}</p> : null}
      {feishu.reason ? <p className="muted">{feishu.reason}</p> : null}
    </section>
  );
}

function ReleaseEvidencePanel({ evidence }: { evidence?: ReleaseEvidenceSummary }) {
  if (!evidence) {
    return (
      <section className="panel nested">
        <h3>发布证据包</h3>
        <p className="muted">还没有同步发布证据包。</p>
      </section>
    );
  }
  const checks = Object.entries(evidence.productReadinessChecks ?? {});
  const readyChecks = checks.filter(([, status]) => status === "ready").length;
  const successEvidenceCount = Object.values(evidence.realSuccessEvidence ?? {}).filter(Boolean).length;
  const failureEvidenceCount = Object.values(evidence.realFailureEvidence ?? {}).filter(Boolean).length;
  const nextActions = evidence.readinessNextActions ?? [];
  const staleReasons = evidence.evidencePacketStaleReasons ?? [];
  return (
    <section className="panel nested release-panel">
      <h3>发布证据包</h3>
      <PropertyGrid
        rows={[
          ["生产验收", fallbackText(evidence.productionAcceptanceStatus, "未知")],
          ["产品就绪", fallbackText(evidence.productReadinessStatus, "未知")],
          ["运行门禁", fallbackText(evidence.runGateStatus, "未知")],
          ["证据过期", evidence.evidencePacketStale ? "是" : "否"],
          ["检查项", checks.length ? `${readyChecks}/${checks.length} 就绪` : "未记录"],
          ["真实证据", `${successEvidenceCount} 条成功 / ${failureEvidenceCount} 条失败`],
          ["执行次数", `${evidence.executionResultCount ?? 0}`],
          ["生成时间", fallbackText(evidence.generatedAt)],
          ["证据包", fallbackText(evidence.packetPath)],
        ]}
      />
      {nextActions.length ? (
        <div className="next-actions" aria-label="发布证据下一步">
          <strong>下一步</strong>
          <ul>
            {nextActions.slice(0, 5).map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {staleReasons.length ? (
        <div className="next-actions warning" aria-label="发布证据过期原因">
          <strong>证据包需要重新生成</strong>
          <ul>
            {staleReasons.slice(0, 4).map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {checks.length ? (
        <div className="check-summary release-checks" aria-label="产品就绪检查">
          {checks.slice(0, 8).map(([name, status]) => (
            <span key={name}>
              {name}: {status}
            </span>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function BackendSmokePanel({ smoke }: { smoke?: BackendSmokeEvidence }) {
  if (!smoke) {
    return (
      <section className="panel nested">
        <h3>后端冒烟证据</h3>
        <p className="muted">还没有记录后端冒烟证据。</p>
      </section>
    );
  }
  return (
    <section className="panel nested smoke-panel">
      <h3>后端冒烟证据</h3>
      <PropertyGrid
        rows={[
          ["后端", smoke.backendName],
          ["是否成功", yesNo(smoke.succeeded)],
          ["分配记录", statusLabel(smoke.assignmentStatus)],
          ["执行结果", fallbackText(smoke.executionResultId)],
          ["退出码", String(smoke.exitCode ?? "未记录")],
          ["测试", String(smoke.testExitCode ?? "未记录")],
          ["评审", statusLabel(smoke.reviewVerdict ?? "未记录")],
          ["智能体运行时", smoke.agentRuntime],
        ]}
      />
      <div className="file-list smoke-files">
        {smoke.changedFiles.map((file) => <code key={file}>{file}</code>)}
      </div>
      <div className="link-row">
        {smoke.handoffFile ? <code>{smoke.handoffFile}</code> : null}
        {smoke.boardPath ? <code>{smoke.boardPath}</code> : null}
      </div>
      {smoke.blocker ? <p className="muted">{smoke.blocker}</p> : null}
    </section>
  );
}

function GitHubEvidencePanel({ ticket }: { ticket: AriadneTicket }) {
  const github = ticket.github;
  if (!github) {
    return (
      <section className="panel nested">
        <h3>GitHub</h3>
        <p className="muted">还没有记录 GitHub 证据。</p>
      </section>
    );
  }
  const checks = github.checkCounts;
  return (
    <section className="panel nested github-panel">
      <h3>GitHub</h3>
      <PropertyGrid
        rows={[
          ["操作", github.operation],
          ["仓库", fallbackText(github.repo)],
          ["Issue", github.issueUrl ? `#${github.issueNumber ?? ""}` : "未记录"],
          ["PR", github.prUrl ? `#${github.prNumber ?? ""}` : "未记录"],
          ["分支", fallbackText(github.branch)],
          ["基线", fallbackText(github.baseBranch)],
          ["可合并", fallbackText(github.mergeable)],
          ["评审", fallbackText(github.reviewDecision, "无")],
          ["检查", fallbackText(github.checksStatus)],
        ]}
      />
      <div className="link-row">
        {github.issueUrl ? <a href={github.issueUrl}>Issue</a> : null}
        {github.prUrl ? <a href={github.prUrl}>PR</a> : null}
        {github.commentUrl ? <a href={github.commentUrl}>评论</a> : null}
      </div>
      {github.commitSha ? <code className="commit-sha">{github.commitSha}</code> : null}
      {checks ? (
        <div className="check-summary">
          <span>通过 {checks.pass}</span>
          <span>等待 {checks.pending}</span>
          <span>失败 {checks.fail}</span>
          <span>总数 {checks.total}</span>
        </div>
      ) : null}
      <div className="github-history">
        {github.history.map((item) => (
          <span key={`${item.operation}-${item.createdAt}`}>
            {item.operation} · {resultLabel(item.ok, item.blocked)}
          </span>
        ))}
      </div>
    </section>
  );
}

function AgentsPage({ data }: { data: WorkbenchData }) {
  return (
    <section className="page">
      <PageHeader
        icon={<Bot size={17} />}
        title="智能体"
        count={data.agents.length}
        description="能领取 issue、留下评论、推进状态的 AI 队友。"
        action={<button className="outline-button" type="button">新建智能体</button>}
      />
      <div className="table-card">
        <div className="table-row head">
          <span>智能体</span>
          <span>状态</span>
          <span>推理</span>
          <span>运行时</span>
          <span>运行次数</span>
        </div>
        {data.agents.map((agent) => (
          <div className="table-row" key={agent.name}>
            <strong><Bot size={16} />{agent.name}<small>{agent.description}</small></strong>
            <span className={`state ${agent.status}`}>{statusLabel(agent.status)}</span>
            <span>{agent.reasoning}</span>
            <span>{agent.backend}</span>
            <span>{agent.runs}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function RuntimesPage({
  data,
  dataSource,
  selectedRuntime,
  onRuntimeSelect,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  selectedRuntime: string;
  onRuntimeSelect: (backend: string) => void;
}) {
  const currentRuntime = data.runtimes.find((runtime) => runtime.backend === selectedRuntime) ?? data.runtimes[0];
  return (
    <section className="page full-bleed">
      <PageHeader
        icon={<Monitor size={17} />}
        title="运行时"
        count={data.runtimes.length}
        description={dataSource === "api" ? "已接入本地 FastAPI 控制平面。" : dataSource === "snapshot" ? "使用本地静态快照，只读。" : dataSource === "fixture" ? "显式离线 fixture 模式，只读。" : "未连接本地 API，只读。"}
        action={<button className="outline-button" type="button">刷新快照</button>}
      />
      <div className="runtime-layout">
        <aside className="machine-list">
          <input placeholder="搜索机器..." />
          <button className="machine active" type="button">
            <Monitor size={18} />
            <strong>local-mac</strong>
            <span>{data.runtimes.length} 个运行时</span>
          </button>
          <section className="runtime-picker" aria-label="选择运行时">
            <h3>后端</h3>
            {data.runtimes.map((runtime) => (
              <button
                className={runtime.backend === selectedRuntime ? "active" : ""}
                data-backend={runtime.backend}
                disabled={runtime.status !== "online"}
                key={runtime.backend}
                type="button"
                onClick={() => onRuntimeSelect(runtime.backend)}
              >
                <span>{runtime.backend}</span>
                <em>{runtime.status === "online" ? "可用" : "不可用"}</em>
              </button>
            ))}
          </section>
        </aside>
        <section className="runtime-detail">
          <h2>local-mac <span>在线</span></h2>
          <p>{data.runtimes.length} 个运行时 · 当前选择 {currentRuntime?.backend ?? "未记录"} · 本地 daemon</p>
          <section className="runtime-capability daemon-runtime-status">
            <div>
              <span>Daemon</span>
              <strong>{statusLabel(data.daemonStatus.status)}</strong>
            </div>
            <div>
              <span>后台循环</span>
              <strong>{data.daemonStatus.backgroundRunning ? "运行中" : "未运行"}</strong>
            </div>
            <div>
              <span>运行时授权</span>
              <strong>{data.daemonStatus.externalExecutionAuthorized ? "已授权 Codex/Claude" : "未授权"}</strong>
            </div>
            <div>
              <span>当前任务</span>
              <strong>{data.daemonStatus.currentTicketKey ?? "无"}</strong>
            </div>
            <div>
              <span>阶段</span>
              <strong>{data.daemonStatus.currentStage ?? "未记录"}</strong>
            </div>
            <div>
              <span>可领取</span>
              <strong>{data.daemonStatus.claimableAssignmentCount}</strong>
            </div>
            <div>
              <span>心跳</span>
              <strong>{data.daemonStatus.heartbeatAt ?? "未记录"}</strong>
            </div>
          </section>
          {currentRuntime ? <RuntimeCapability runtime={currentRuntime} /> : null}
          <div className="runtime-table">
            {data.runtimes.map((runtime) => (
              <div className="runtime-row" key={runtime.backend}>
                <strong>{runtime.backend}</strong>
                <span className={`state ${runtime.status}`}>{runtime.status === "online" ? "在线" : "离线"}</span>
                <span>{runtime.version}</span>
                <span>{runtime.cost7d}</span>
              </div>
            ))}
          </div>
          {data.projectResources?.length ? (
            <section className="panel resource-panel">
              <h3>项目资源</h3>
              {data.projectResources.map((resource) => (
                <div className="resource-row" key={resource.id}>
                  <strong>{resource.label}</strong>
                  <span>{resource.resourceType}</span>
                  <code>{resource.available ? "可用" : resource.disabledReason ?? "不可用"}</code>
                </div>
              ))}
            </section>
          ) : null}
          <BackendSmokeSummary items={data.backendSmokeEvidence ?? []} />
        </section>
      </div>
    </section>
  );
}

function RuntimeCapability({ runtime }: { runtime: RuntimeInfo }) {
  return (
    <section className="runtime-capability">
      <div>
        <span>命令</span>
        <strong>{runtime.command ?? runtime.backend}</strong>
      </div>
      <div>
        <span>路径</span>
        <strong>{runtime.commandPath ?? "内部"}</strong>
      </div>
      <div>
        <span>外部执行</span>
        <strong>{runtime.externalExecutionEnabled ? "已开启" : "门禁关闭"}</strong>
      </div>
      <div>
        <span>授权方式</span>
        <strong>{runtime.confirmExecutionRequired ? "运行时启动时确认 Codex/Claude" : "无需确认"}</strong>
      </div>
      <div>
        <span>演练模式</span>
        <strong>{runtime.supportsDryRun ? "支持" : "不支持"}</strong>
      </div>
      <div>
        <span>检查时间</span>
        <strong>{runtime.checkedAt ?? "内置数据"}</strong>
      </div>
    </section>
  );
}

function BackendSmokeSummary({ items }: { items: BackendSmokeEvidence[] }) {
  const latest = [...items].sort((a, b) => a.createdAt.localeCompare(b.createdAt)).slice(-6).reverse();
  return (
    <section className="panel resource-panel smoke-summary">
      <h3>后端冒烟证据</h3>
      {latest.length ? latest.map((item) => (
        <div className="smoke-row" key={item.id}>
          <strong>{item.backendName}</strong>
          <span className={`state ${item.succeeded ? "online" : "offline"}`}>
            {resultLabel(item.succeeded, item.blocked)}
          </span>
          <span>{item.ticketKey}</span>
          <span>退出码 {String(item.exitCode ?? "未记录")}</span>
          <span>测试 {String(item.testExitCode ?? "未记录")}</span>
          <span>{item.reviewVerdict ? statusLabel(item.reviewVerdict) : "未评审"}</span>
          <code>{item.id}</code>
        </div>
      )) : <p className="muted">还没有同步后端冒烟证据。</p>}
    </section>
  );
}

function SkillsPage({ data }: { data: WorkbenchData }) {
  return (
    <section className="page">
      <PageHeader
        icon={<BookOpenText size={17} />}
        title="技能"
        count={data.skills.length}
        description="工作区里任何智能体都能使用的能力说明。"
        action={<button className="outline-button" type="button">新建技能</button>}
      />
      <div className="search-line">
        <Search size={16} />
        <input placeholder="搜索技能..." />
      </div>
      <div className="table-card">
        <div className="table-row skill-head">
          <span>名称</span>
          <span>被谁使用</span>
          <span>更新时间</span>
        </div>
        {data.skills.map((skill) => (
          <div className="table-row skill-row" key={skill.name}>
            <strong>{skill.name}<small>{skill.description}</small></strong>
            <span>{skill.usedBy.join(", ")}</span>
            <span>{skill.updatedAt}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function InboxPage({
  data,
  onNavigate,
  onTicketSelect,
}: {
  data: WorkbenchData;
  onNavigate: (page: PageKey) => void;
  onTicketSelect: (ticketId: string) => void;
}) {
  return (
    <section className="page">
      <PageHeader icon={<Inbox size={17} />} title="收件箱" count={data.inbox.length} />
      <div className="inbox-list">
        {data.inbox.map((item, index) => (
          <button
            key={item.id}
            type="button"
            onClick={() => {
              const fallbackTicket = data.tickets[index % data.tickets.length];
              const targetTicketId = item.repairTicketId ?? item.ticketId;
              const ticket = data.tickets.find((candidate) => candidate.id === targetTicketId) ?? fallbackTicket;
              if (ticket) onTicketSelect(ticket.id);
              onNavigate("ready");
            }}
          >
            <span className={`inbox-kind ${item.kind}`}>{statusLabel(item.kind)}</span>
            <strong>{item.title}</strong>
            <p>{item.body}</p>
            <div className="inbox-meta">
              <span>{statusLabel(item.status ?? "open")}</span>
              <span>{statusLabel(item.severity ?? "medium")}</span>
              {item.ticketKey ? <span>{item.ticketKey}</span> : null}
              {item.failureReason ? <span>{item.failureReason}</span> : null}
              {item.repairTicketKey ? <span>修复任务 {item.repairTicketKey}</span> : null}
            </div>
            {item.recommendedAction ? <p className="inbox-action">{item.recommendedAction}</p> : null}
            {item.evidenceRef ? <code>{item.evidenceRef}</code> : null}
            {item.resolutionNote ? <small>{item.resolutionNote}</small> : null}
            <em>{item.time}</em>
          </button>
        ))}
      </div>
    </section>
  );
}

function AgentDock({
  compactDefault,
  runtimes,
  selectedRuntime,
  selectedTicket,
  onRuntimeSelect,
}: {
  compactDefault: boolean;
  runtimes: RuntimeInfo[];
  selectedRuntime: string;
  selectedTicket?: AriadneTicket;
  onRuntimeSelect: (backend: string) => void;
}) {
  const [open, setOpen] = useState(!compactDefault);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Array<{ actor: "user" | "agent"; body: string }>>([]);

  useEffect(() => {
    if (compactDefault) setOpen(false);
  }, [compactDefault]);

  const selected = runtimes.find((runtime) => runtime.backend === selectedRuntime) ?? runtimes[0];
  const selectableRuntimes = selectableProductionRuntimes(runtimes);
  const runtimeOptions = selectableRuntimes.length ? selectableRuntimes : runtimes;
  const disabledReason = selected?.supportsExternalExecution && !selected.externalExecutionEnabled
    ? "外部执行未开启，只生成安全的本地 handoff 预览。"
    : "当前运行时可用于本地只读编排预览。";

  function sendMessage() {
    const body = draft.trim();
    if (!body) return;
    setMessages((current) => [
      ...current,
      { actor: "user", body },
      {
        actor: "agent",
        body: `已选择 ${selected?.backend ?? selectedRuntime}。当前 ticket: ${selectedTicket?.key ?? "未选择"}。${disabledReason}`,
      },
    ]);
    setDraft("");
  }

  if (!open) {
    return (
      <button className="agent-dock compact" type="button" onClick={() => setOpen(true)}>
        <Bot size={16} />
        <span>对话</span>
      </button>
    );
  }
  return (
    <aside className="agent-dock">
      <header>
        <Plus size={16} />
        <strong>新对话</strong>
        <button aria-label="收起对话" type="button" onClick={() => setOpen(false)}>−</button>
      </header>
      <div className="agent-empty">
        <div className="agent-runtime-line">
          <span>运行时</span>
          <select value={selectedRuntime} onChange={(event) => onRuntimeSelect(event.target.value)}>
            {runtimeOptions.map((runtime) => (
              <option key={runtime.backend} value={runtime.backend}>
                {runtime.backend}
              </option>
            ))}
          </select>
        </div>
        {messages.length ? (
          <div className="agent-messages">
            {messages.map((message, index) => (
              <p className={message.actor} key={`${message.actor}-${index}`}>
                {message.body}
              </p>
            ))}
          </div>
        ) : (
          <>
            <h3>和你的智能体对话</h3>
            <p>它们了解你的工作区：目标、任务、运行时、技能。</p>
            <small>{disabledReason}</small>
          </>
        )}
      </div>
      <footer>
        <input
          placeholder="输入消息..."
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") sendMessage();
          }}
        />
        <button aria-label="发送消息" type="button" onClick={sendMessage}>
          <Send size={15} />
        </button>
      </footer>
    </aside>
  );
}

function StateBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="state-box">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PropertyGrid({ rows }: { rows: Array<[string, string]> }) {
  return (
    <section className="property-grid">
      {rows.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  );
}

function Timeline({ items }: { items: TimelineEvent[] }) {
  if (!items.length) return <p className="muted">暂无进度。</p>;
  return (
    <ol className="timeline">
      {items.map((item) => (
        <li key={`${item.time}-${item.kind}-${item.body}`}>
          <span>{item.time}</span>
          <strong>{item.actor}</strong>
          <p>{item.body}</p>
        </li>
      ))}
    </ol>
  );
}

function List({ items }: { items: string[] }) {
  return (
    <ul className="plain-list">
      {items.map((item) => <li key={item}>{item}</li>)}
    </ul>
  );
}
