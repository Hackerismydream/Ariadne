import {
  Bot,
  Monitor,
  Plus,
  Send,
  Settings,
  Target,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { applyRouteRedirect, ensureDefaultHashRoute, pageHash, parseHashRoute, type PageKey } from "./app/routes";
import { WorkbenchSidebar } from "./app/shell/Sidebar";
import { emptyWorkbenchData, loadWorkbenchData, type WorkbenchDataSource } from "./data";
import { selectableProductionRuntimes } from "./entities/runtime/lib";
import { InboxPage as InboxControlPage } from "./pages/inbox/InboxPage";
import { IssuesWorkbenchPage } from "./pages/issues/IssuesPage";
import { PlanChangesPage } from "./pages/plan-changes/PlanChangesPage";
import { RunsPage } from "./pages/runs/RunsPage";
import { SourcesPage } from "./pages/sources/SourcesPage";
import { TeamPage } from "./pages/team/TeamPage";
import { CurrentVersionStrip } from "./widgets/current-version/CurrentVersionStrip";
import {
  createProjectGoal,
  registerTargetProject,
} from "./shared/api/client";
import type {
  AriadneTicket,
  BackendSmokeEvidence,
  RuntimeInfo,
  TimelineEvent,
  WorkbenchData,
} from "./types";

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

function getActiveTargetProject(data: WorkbenchData) {
  const deliveryTargetId = data.currentVersionDelivery?.targetProjectId;
  const goalTargetId = data.goal.targetProjectId;
  return data.projectResources?.find((resource) => resource.id === deliveryTargetId && resource.available)
    ?? data.projectResources?.find((resource) => resource.id === goalTargetId && resource.available)
    ?? data.environment?.activeTargetProject
    ?? data.projectResources?.find((resource) => resource.available)
    ?? data.projectResources?.[0]
    ?? null;
}

function getCurrentVersionTickets(data: WorkbenchData) {
  const deliveryKeys = new Set((data.currentVersionDelivery?.deliveryItems ?? []).map((item) => item.ticketKey));
  const deliveryTickets = data.tickets.filter((ticket) => deliveryKeys.has(ticket.key));
  if (deliveryTickets.length) return deliveryTickets;
  const targetProjectId = data.currentVersionDelivery?.targetProjectId ?? data.goal.targetProjectId ?? getActiveTargetProject(data)?.id;
  const targetTickets = data.tickets.filter((ticket) => targetProjectId && ticket.targetProjectId === targetProjectId);
  return targetTickets.length ? targetTickets : data.tickets;
}

function getCurrentVersionWorkflows(data: WorkbenchData) {
  const currentKeys = new Set(getCurrentVersionTickets(data).map((ticket) => ticket.key));
  return (data.agentWorkflows ?? []).filter((step) => currentKeys.has(step.ticketKey));
}

function projectDisplayName(data: WorkbenchData) {
  return data.currentVersionDelivery?.targetProjectLabel
    ?? getActiveTargetProject(data)?.label
    ?? data.goal.title
    ?? "当前项目";
}

function userFacingStatus(status?: string) {
  if (status === "real_closed") return "已完成真实闭环";
  if (status === "blocked") return "当前阻塞";
  if (status === "ready_for_review") return "等待审核";
  if (status === "in_progress") return "推进中";
  return "待推进";
}

function nextDeliveryAction(data: WorkbenchData) {
  const delivery = data.currentVersionDelivery;
  const inputs = data.projectInputs ?? [];
  const readyInputs = inputs.filter((input) => input.lifecycle.readyForIssueFactory).length;
  const currentTickets = getCurrentVersionTickets(data);
  if (delivery?.status === "real_closed" && delivery.latestRealRun?.reviewVerdict === "pass") {
    return { label: "查看版本证据", detail: `${delivery.latestRealRun.ticketKey} 已由 ${delivery.latestRealRun.backendName} 完成真实执行，测试和 review 通过。`, page: "ready" as PageKey };
  }
  const blockers = [
    ...(delivery?.blockers ?? []),
    ...(data.environment?.blockers.map((blocker) => blocker.message) ?? []),
  ].filter(Boolean);
  if (!inputs.length) {
    return { label: "先添加项目输入", detail: "把博客、GitHub 仓库、论文或本地文件夹放进来。", page: "sources" as PageKey };
  }
  if (!readyInputs) {
    return { label: "先分析项目输入", detail: "已有输入还没有形成可用于任务生成的证据。", page: "sources" as PageKey };
  }
  if (!currentTickets.length) {
    return { label: "生成当前版本任务", detail: "用项目目标和已分析输入生成目标项目 issue。", page: "tasks" as PageKey };
  }
  if (blockers.length) {
    return { label: "处理当前阻塞", detail: blockers[0], page: "ready" as PageKey };
  }
  if (!delivery?.latestRealRun) {
    return { label: "分配给 Codex/Claude", detail: "选择当前 issue，创建 assignment 并让本地运行时执行。", page: "ready" as PageKey };
  }
  if (delivery.latestRealRun.reviewVerdict !== "pass") {
    return { label: "查看执行证据并修复", detail: `${delivery.latestRealRun.ticketKey} 已执行，但 review 还没有通过。`, page: "ready" as PageKey };
  }
  return { label: "查看版本证据", detail: "当前版本已有执行证据，继续检查 diff、tests、review 和 next issue。", page: "ready" as PageKey };
}

export function App() {
  const initialRoute = parseHashRoute();
  const [page, setPage] = useState<PageKey>(initialRoute.page ?? "ready");
  const [data, setData] = useState<WorkbenchData>(emptyWorkbenchData);
  const [dataSource, setDataSource] = useState<WorkbenchDataSource>("disconnected");
  const [readOnly, setReadOnly] = useState(true);
  const [issueRef, setIssueRef] = useState(initialRoute.ticketRef);
  const [agentRef, setAgentRef] = useState(initialRoute.agentRef);
  const [selectedTicketId, setSelectedTicketId] = useState(
    findTicketByRef(emptyWorkbenchData.tickets, initialRoute.ticketRef)?.id ?? "",
  );
  const [selectedRuntime, setSelectedRuntime] = useState("");
  const selectedTicket = data.tickets.find((ticket) => ticket.id === selectedTicketId) ?? data.tickets[0];

  async function refreshWorkbenchData(preferredTicketRef?: string) {
    const result = await loadWorkbenchData();
    setData(result.data);
    setDataSource(result.source);
    setReadOnly(result.readOnly);
    const route = parseHashRoute();
    applyRouteRedirect(route);
    setIssueRef(preferredTicketRef ?? route.ticketRef);
    setAgentRef(route.agentRef);
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

  function navigate(nextPage: PageKey, hashOverride?: string) {
    setPage(nextPage);
    const nextHash = hashOverride ?? pageHash(nextPage);
    if (globalThis.location?.hash !== nextHash) {
      globalThis.history?.replaceState(null, "", nextHash);
    }
  }

  function selectTicket(ticketId: string) {
    const ticket = data.tickets.find((candidate) => candidate.id === ticketId);
    if (!ticket) return;
    setSelectedTicketId(ticket.id);
    setIssueRef(ticket.key);
    setPage("ready");
    if (globalThis.location?.hash !== issueHash(ticket)) {
      globalThis.history?.replaceState(null, "", issueHash(ticket));
    }
  }

  useEffect(() => {
    let mounted = true;
    ensureDefaultHashRoute();
    applyRouteRedirect(parseHashRoute());
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
      applyRouteRedirect(route);
      if (route.page) setPage(route.page);
      setIssueRef(route.ticketRef);
      setAgentRef(route.agentRef);
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
      <WorkbenchSidebar data={data} page={page} onNavigate={navigate} />
      <main className="main">
        <CurrentVersionStrip data={data} dataSource={dataSource} onNavigate={navigate} />
        <PageFrame
          data={data}
          dataSource={dataSource}
          readOnly={readOnly}
          page={page}
          selectedRuntime={selectedRuntime}
          selectedTicket={selectedTicket}
          issueRef={issueRef}
          agentRef={agentRef}
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

function PageFrame({
  data,
  dataSource,
  page,
  selectedRuntime,
  selectedTicket,
  issueRef,
  agentRef,
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
  issueRef?: string;
  agentRef?: string;
  onNavigate: (page: PageKey) => void;
  onRuntimeSelect: (backend: string) => void;
  onTicketSelect: (ticketId: string) => void;
  onRefresh: (preferredTicketRef?: string) => Promise<void>;
}) {
  if (page === "project") return <GoalPage data={data} dataSource={dataSource} onRefresh={onRefresh} onTicketSelect={onTicketSelect} />;
  if (page === "sources") return <SourcesPage data={data} dataSource={dataSource} onNavigate={onNavigate} onRefresh={onRefresh} />;
  if (page === "tasks") {
    return <PlanChangesPage data={data} dataSource={dataSource} onNavigate={onNavigate} onRefresh={onRefresh} />;
  }
  if (page === "team") return <TeamPage agentRef={agentRef} />;
  if (page === "runs") return <RunsPage />;
  if (page === "inbox") return <InboxControlPage />;
  if (page === "ready") {
    return (
      <IssuesWorkbenchPage
        data={data}
        readOnly={readOnly}
        selectedRuntime={selectedRuntime}
        issueRef={issueRef}
        onRefreshWorkbench={onRefresh}
      />
    );
  }
  return <DiagnosticsPage data={data} dataSource={dataSource} selectedRuntime={selectedRuntime} />;
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

function DiagnosticsPage({
  data,
  dataSource,
  selectedRuntime,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  selectedRuntime: string;
}) {
  const currentRuntime = data.runtimes.find((runtime) => runtime.backend === selectedRuntime) ?? data.runtimes[0];
  return (
    <section className="page full-bleed diagnostics-page">
      <PageHeader
        icon={<Settings size={17} />}
        title="Diagnostics"
        description={dataSource === "api" ? "Local FastAPI control plane technical diagnostics." : "Workbench is not connected to the local API."}
      />
      <div className="control-surface-grid">
        <section className="panel">
          <h2><Monitor size={16} /> Daemon</h2>
          <PropertyGrid
            rows={[
              ["Status", statusLabel(data.daemonStatus.status)],
              ["Background loop", data.daemonStatus.backgroundRunning ? "Running" : "Stopped"],
              ["External execution", data.daemonStatus.externalExecutionAuthorized ? "Authorized" : "Not authorized"],
              ["Current issue", data.daemonStatus.currentTicketKey ?? "None"],
              ["Stage", data.daemonStatus.currentStage ?? "Not recorded"],
              ["Claimable", String(data.daemonStatus.claimableAssignmentCount)],
              ["Running", String(data.daemonStatus.runningAssignmentCount)],
              ["Blocked", String(data.daemonStatus.blockedAssignmentCount)],
              ["Heartbeat", data.daemonStatus.heartbeatAt ?? "Not recorded"],
              ["Last error", data.daemonStatus.lastError ?? "None"],
            ]}
          />
        </section>
        <section className="panel">
          <h2><Monitor size={16} /> Selected Runtime</h2>
          {currentRuntime ? <RuntimeCapability runtime={currentRuntime} /> : <p className="empty-column">No runtime snapshot.</p>}
        </section>
        <section className="panel wide">
          <h2>Backend Smoke Evidence</h2>
          <BackendSmokeSummary items={data.backendSmokeEvidence ?? []} />
        </section>
      </div>
    </section>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
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
  const [createIfMissing, setCreateIfMissing] = useState(true);
  const [initGit, setInitGit] = useState(true);
  const [testCommand, setTestCommand] = useState("python3.11 -m pytest");
  const [issuePrefix, setIssuePrefix] = useState("MCA");
  const [goalTitle, setGoalTitle] = useState(goal.id === "GOAL-NOT-CREATED" ? "" : goal.title);
  const [northStar, setNorthStar] = useState(goal.id === "GOAL-NOT-CREATED" ? "" : goal.northStar);
  const [targetState, setTargetState] = useState(goal.targetState);
  const [status, setStatus] = useState("");
  const [isSavingProject, setIsSavingProject] = useState(false);
  const [preferredProjectId, setPreferredProjectId] = useState(goal.targetProjectId ?? data.projectResources?.[0]?.id ?? "");
  const activeProject = data.projectResources?.find((resource) => resource.id === preferredProjectId && resource.available)
    ?? data.projectResources?.find((resource) => resource.available)
    ?? data.projectResources?.[0];

  async function saveProject() {
    if (!projectPath.trim() || isSavingProject) return;
    setIsSavingProject(true);
    setStatus("正在注册目标项目...");
    try {
      const result = await registerTargetProject({
        path: projectPath.trim(),
        label: projectLabel.trim() || undefined,
        create_if_missing: createIfMissing,
        init_git: initGit,
        test_command: testCommand.trim() || undefined,
        issue_prefix: issuePrefix.trim() || undefined,
      }) as {
        target_project?: { id?: string };
      };
      if (result.target_project?.id) setPreferredProjectId(result.target_project.id);
      await onRefresh();
      setStatus("目标项目已注册。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "目标项目注册失败。");
    } finally {
      setIsSavingProject(false);
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
            <label>
              <span>测试命令</span>
              <input
                disabled={dataSource !== "api"}
                placeholder="python3.11 -m pytest"
                value={testCommand}
                onChange={(event) => setTestCommand(event.target.value)}
              />
            </label>
            <label>
              <span>Issue 前缀</span>
              <input
                disabled={dataSource !== "api"}
                placeholder="MCA"
                value={issuePrefix}
                onChange={(event) => setIssuePrefix(event.target.value.toUpperCase())}
              />
            </label>
            <label className="checkbox-line">
              <input
                checked={createIfMissing}
                disabled={dataSource !== "api"}
                type="checkbox"
                onChange={(event) => setCreateIfMissing(event.target.checked)}
              />
              <span>文件夹不存在时自动创建</span>
            </label>
            <label className="checkbox-line">
              <input
                checked={initGit}
                disabled={dataSource !== "api"}
                type="checkbox"
                onChange={(event) => setInitGit(event.target.checked)}
              />
              <span>注册时初始化 git</span>
            </label>
            <button disabled={dataSource !== "api" || isSavingProject || !projectPath.trim()} type="button" onClick={() => void saveProject()}>
              {isSavingProject ? "注册中..." : "注册项目"}
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
