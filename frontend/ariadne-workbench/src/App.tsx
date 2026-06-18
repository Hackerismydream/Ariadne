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
import { selectableProductionRuntimes } from "./entities/runtime/lib";
import {
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
  TicketStatus,
  TimelineEvent,
  WorkbenchData,
} from "./types";

type PageKey = "goal" | "knowledge" | "issues" | "agents" | "runtimes" | "skills" | "inbox";

function parseHashRoute(hash = globalThis.location?.hash ?? "") {
  const value = hash.replace(/^#/, "").trim();
  if (!value) return {};
  const issueMatch = value.match(/^issues\/([^/?#]+)$/i) ?? value.match(/^(?:issue|ticket)=([^&]+)/i);
  if (issueMatch) return { page: "issues" as PageKey, ticketRef: decodeURIComponent(issueMatch[1]) };
  if (value === "runtime") return { page: "runtimes" as PageKey };
  if (["goal", "knowledge", "issues", "agents", "runtimes", "skills", "inbox"].includes(value)) {
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
  items: Array<{ key: PageKey | "projects" | "automation" | "squads" | "usage" | "settings"; label: string; icon: typeof Inbox }>;
}> = [
  {
    label: "个人",
    items: [
      { key: "inbox", label: "收件箱", icon: Inbox },
      { key: "goal", label: "当前目标", icon: Target },
    ],
  },
  {
    label: "工作区",
    items: [
      { key: "knowledge", label: "知识", icon: BookOpenText },
      { key: "issues", label: "任务", icon: ListTodo },
      { key: "projects", label: "目标库", icon: FolderKanban },
      { key: "automation", label: "自动化", icon: Zap },
      { key: "agents", label: "智能体", icon: Bot },
      { key: "squads", label: "小队", icon: Users },
      { key: "usage", label: "用量", icon: Sparkles },
    ],
  },
  {
    label: "配置",
    items: [
      { key: "runtimes", label: "运行时", icon: Monitor },
      { key: "skills", label: "技能", icon: BookOpenText },
      { key: "settings", label: "设置", icon: Settings },
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
    ready: "待执行",
    reviewing: "审核中",
    review: "审核",
    resolved: "已解决",
    running: "运行中",
    snoozed: "已稍后处理",
  };
  return labels[status] ?? status;
}

function sourceTypeLabel(sourceType: WorkbenchData["sources"][number]["sourceType"]) {
  const labels: Record<WorkbenchData["sources"][number]["sourceType"], string> = {
    blog: "博客",
    paper: "论文",
    github_readme: "GitHub README",
    repo_note: "仓库笔记",
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
  const [page, setPage] = useState<PageKey>(initialRoute.page ?? "knowledge");
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
      setPage("issues");
      setSelectedTicketId(preferredTicket.id);
      if (globalThis.location?.hash !== issueHash(preferredTicket)) {
        globalThis.history?.replaceState(null, "", issueHash(preferredTicket));
      }
    } else if (routeTicket) {
      setPage("issues");
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
    setPage("issues");
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
        setPage("issues");
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
      {page === "knowledge" ? null : (
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
            const enabled = ["goal", "knowledge", "issues", "agents", "runtimes", "skills", "inbox"].includes(item.key);
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
                {item.key === "inbox" ? <em>{data.inbox.length}</em> : null}
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
  if (page === "goal") return <GoalPage data={data} dataSource={dataSource} onRefresh={onRefresh} onTicketSelect={onTicketSelect} />;
  if (page === "knowledge") return <KnowledgePage data={data} dataSource={dataSource} onRefresh={onRefresh} />;
  if (page === "issues") {
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
  if (page === "agents") return <AgentsPage data={data} />;
  if (page === "runtimes") {
    return (
      <RuntimesPage
        data={data}
        dataSource={dataSource}
        selectedRuntime={selectedRuntime}
        onRuntimeSelect={onRuntimeSelect}
      />
    );
  }
  if (page === "skills") return <SkillsPage data={data} />;
  return <InboxPage data={data} onNavigate={onNavigate} onTicketSelect={onTicketSelect} />;
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
  onRefresh,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  onRefresh: () => Promise<void>;
}) {
  const [selectedSourceId, setSelectedSourceId] = useState(data.sources[0]?.id ?? "");
  const [sourceTitle, setSourceTitle] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceType, setSourceType] = useState<"blog" | "paper" | "github_repo" | "note">("blog");
  const [sourceContent, setSourceContent] = useState("");
  const [actionStatus, setActionStatus] = useState("");
  const sourceCards = data.knowledgeCards.filter((card) => card.sourceId === selectedSourceId);
  const fallbackCard = sourceCards[0] ?? data.knowledgeCards[0];
  const [selectedCardId, setSelectedCardId] = useState(fallbackCard?.id ?? "");
  const selectedSource = data.sources.find((source) => source.id === selectedSourceId) ?? data.sources[0];
  const selectedCard = data.knowledgeCards.find((card) => card.id === selectedCardId && card.sourceId === selectedSourceId)
    ?? fallbackCard;
  const cardChanges = selectedCard
    ? data.backlogChanges.filter((change) => change.knowledgeCardId === selectedCard.id)
    : [];
  const [selectedChangeId, setSelectedChangeId] = useState(cardChanges[0]?.id ?? "");
  const selectedChange = cardChanges.find((change) => change.id === selectedChangeId) ?? cardChanges[0];
  const [previewStatus, setPreviewStatus] = useState(data.backlogMutationPreview.status);

  useEffect(() => {
    if (!data.sources.some((source) => source.id === selectedSourceId)) {
      setSelectedSourceId(data.sources[0]?.id ?? "");
    }
    setPreviewStatus(data.backlogMutationPreview.status);
  }, [data.sources, data.backlogMutationPreview.status, selectedSourceId]);

  function selectSource(sourceId: string) {
    const nextCard = data.knowledgeCards.find((card) => card.sourceId === sourceId) ?? data.knowledgeCards[0];
    const nextChange = nextCard ? data.backlogChanges.find((change) => change.knowledgeCardId === nextCard.id) : undefined;
    setSelectedSourceId(sourceId);
    setSelectedCardId(nextCard?.id ?? "");
    setSelectedChangeId(nextChange?.id ?? "");
  }

  function selectCard(cardId: string) {
    const nextChange = data.backlogChanges.find((change) => change.knowledgeCardId === cardId);
    setSelectedCardId(cardId);
    setSelectedChangeId(nextChange?.id ?? "");
  }

  const groupedChanges = groupBacklogChanges(cardChanges);
  const traceSteps = data.traceSteps.filter((step) => {
    if (!selectedCard) return false;
    if (step.knowledgeCardId !== selectedCard.id) return false;
    return !step.backlogChangeId || !selectedChange || step.backlogChangeId === selectedChange.id;
  });
  const activeGoal = data.goal.id !== "GOAL-NOT-CREATED" ? data.goal : undefined;
  const activeProject = data.projectResources?.find((resource) => resource.id === activeGoal?.targetProjectId && resource.available)
    ?? data.projectResources?.find((resource) => resource.available)
    ?? data.projectResources?.[0];
  const activePreviewId = data.backlogMutationPreview.previewId;

  async function addSource() {
    if (!sourceTitle.trim() || !sourceUrl.trim()) return;
    setActionStatus("正在添加来源...");
    try {
      await createSource({
        title: sourceTitle.trim(),
        source_type: sourceType,
        path_or_url: sourceUrl.trim(),
        content: sourceContent.trim(),
      });
      setSourceTitle("");
      setSourceUrl("");
      setSourceContent("");
      await onRefresh();
      setActionStatus("来源已添加。");
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "来源添加失败。");
    }
  }

  async function generateIssues() {
    if (!activeGoal) {
      setActionStatus("请先在目标页创建目标。");
      return;
    }
    setActionStatus("正在生成任务预览...");
    try {
      const result = await createIssueFactoryPreview({
        goal_id: activeGoal.id,
        source_ids: data.sources.map((source) => source.id),
        target_project_id: activeProject?.id ?? null,
      });
      await onRefresh();
      setSelectedChangeId(result.preview.operations[0]?.id ?? "");
      setActionStatus(`已生成 ${result.preview.operations.length} 个任务变更。`);
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "任务预览生成失败。");
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
      setActionStatus("任务变更已应用，新的 issue 已写入任务列表。");
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "应用任务变更失败。");
    }
  }

  return (
    <section className="page full-bleed knowledge-page">
      <PageHeader
        icon={<BookOpenText size={17} />}
        title="知识"
        count={data.sources.length}
        action={
          <div className="toolbar">
            <button type="button" onClick={() => setActionStatus("请在下方表单填写来源并保存。")}>添加来源</button>
            <button type="button" onClick={() => setActionStatus("文件夹导入会复用来源表单；当前版本先登记路径或 URL。")}>导入文件夹</button>
            <button type="button" onClick={() => setActionStatus("仓库扫描会复用来源表单；当前版本先登记仓库 URL。")}>扫描仓库</button>
            <button className="primary-action" disabled={dataSource !== "api"} type="button" onClick={() => void generateIssues()}>生成任务</button>
          </div>
        }
      />
      <section className="panel source-input-panel">
        <h2>添加外部知识</h2>
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
            <input disabled={dataSource !== "api"} value={sourceTitle} onChange={(event) => setSourceTitle(event.target.value)} placeholder="minimal-agent 博客" />
          </label>
          <label>
            <span>路径或 URL</span>
            <input disabled={dataSource !== "api"} value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://minimal-agent.com/" />
          </label>
          <label className="wide-field">
            <span>摘要或摘录</span>
            <textarea disabled={dataSource !== "api"} value={sourceContent} onChange={(event) => setSourceContent(event.target.value)} placeholder="粘贴关键观点，Ariadne 会把它作为 issue factory 的证据。" />
          </label>
          <button disabled={dataSource !== "api" || !sourceTitle.trim() || !sourceUrl.trim()} type="button" onClick={() => void addSource()}>
            保存来源
          </button>
        </div>
        {actionStatus ? <p className="action-message">{actionStatus}</p> : null}
      </section>
      <div className="knowledge-layout">
        <section className="knowledge-column source-column">
          <ColumnHeader title="来源收件箱" meta={`${data.sources.length} 个输入`} />
          <div className="source-list">
            {data.sources.map((source) => (
              <button
                className={`source-row ${source.id === selectedSource?.id ? "selected" : ""}`}
                data-source-id={source.id}
                key={source.id}
                type="button"
                onClick={() => selectSource(source.id)}
              >
                <span className={`source-type ${source.sourceType}`}>{sourceTypeLabel(source.sourceType)}</span>
                <strong>{source.title}</strong>
                <em className={`source-status ${source.status}`}>{statusLabel(source.status)}</em>
                <small>{source.ingestedAt}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="knowledge-column cards-column">
          <ColumnHeader title="知识卡片" meta="排序：最新" />
          <div className="knowledge-card-list">
            {sourceCards.length ? sourceCards.map((card) => (
              <button
                className={`knowledge-card ${card.id === selectedCard?.id ? "selected" : ""}`}
                data-card-id={card.id}
                key={card.id}
                type="button"
                onClick={() => selectCard(card.id)}
              >
                <header>
                  <div>
                    <strong>{card.title}</strong>
                    <small>来源：{selectedSource?.title ?? "未知"}</small>
                  </div>
                  <span className={card.primary ? "primary-badge" : "secondary-badge"}>{card.primary ? "主要" : "次要"}</span>
                </header>
                <section>
                  <h3>摘要</h3>
                  <p>{card.sourceSummary}</p>
                </section>
                <section>
                  <h3>证据</h3>
                  <div className="evidence-list">
                    {card.evidence.map((item) => <code key={item}>{item}</code>)}
                  </div>
                </section>
                <div className="card-meta-grid">
                  <section>
                    <h3>项目相关性</h3>
                    <p>{card.projectRelevance}</p>
                  </section>
                  <section>
                    <h3>构建决策</h3>
                    <span className={`decision-pill ${card.buildDecision}`}>{buildDecisionLabel(card.buildDecision)}</span>
                  </section>
                </div>
                <div className="module-row">
                  {card.affectedModules.map((module) => <span key={module}>{module}</span>)}
                  <em>{Math.round(card.confidence * 100)}%</em>
                </div>
                <ul className="risk-list">
                  {card.risks.map((risk) => <li key={risk}>{risk}</li>)}
                </ul>
              </button>
            )) : <p className="empty-column">这个来源还没有提取出的知识卡片。</p>}
          </div>
        </section>

        <section className="knowledge-column changes-column">
          <ColumnHeader title="任务列表变更" meta="由任务工厂生成" />
          <BacklogChangeGroup title="新增" emptyLabel="新增" kind="added" changes={groupedChanges.added} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="更新" emptyLabel="更新" kind="updated" changes={groupedChanges.updated} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="延后" emptyLabel="延后" kind="deferred" changes={groupedChanges.deferred} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="拒绝" emptyLabel="拒绝" kind="rejected" changes={groupedChanges.rejected} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <div className="apply-row">
            <button disabled={dataSource !== "api" || !activePreviewId || previewStatus === "applied"} type="button" onClick={() => void applyPreview()}>
              {previewStatus === "applied" ? "已应用" : "应用任务变更"}
            </button>
            <span>{previewStatusLabel(previewStatus)} · 最近预览：{data.backlogMutationPreview.lastPreviewAt}</span>
          </div>
        </section>

        <aside className="knowledge-column trace-column">
          <ColumnHeader title="追踪" meta={selectedChange?.ticketKey ?? selectedCard?.title ?? "未选择"} />
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
            )) : <li className="trace-empty">当前选择还没有追踪产物。</li>}
          </ol>
        </aside>
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
    mutationReady,
    postComment,
    runSelectedAssignment,
    setCommentDraft,
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
        <div className="action-row">
          <button disabled={!mutationReady || actionState !== "idle"} type="button" onClick={assignSelectedTicket}>
            {assignTicketButtonLabel(actionState)}
          </button>
          <button disabled={!mutationReady || actionState !== "idle"} type="button" onClick={runSelectedAssignment}>
            {runAssignmentButtonLabel(actionState)}
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
  return (
    <section className="panel nested release-panel">
      <h3>发布证据包</h3>
      <PropertyGrid
        rows={[
          ["生产验收", fallbackText(evidence.productionAcceptanceStatus, "未知")],
          ["产品就绪", fallbackText(evidence.productReadinessStatus, "未知")],
          ["运行门禁", fallbackText(evidence.runGateStatus, "未知")],
          ["检查项", checks.length ? `${readyChecks}/${checks.length} 就绪` : "未记录"],
          ["真实证据", `${successEvidenceCount} 条成功 / ${failureEvidenceCount} 条失败`],
          ["执行次数", `${evidence.executionResultCount ?? 0}`],
          ["生成时间", fallbackText(evidence.generatedAt)],
          ["证据包", fallbackText(evidence.packetPath)],
        ]}
      />
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
        <span>需要确认</span>
        <strong>{yesNo(Boolean(runtime.confirmExecutionRequired))}</strong>
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
              onNavigate("issues");
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
