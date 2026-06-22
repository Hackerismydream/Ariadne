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
  Target,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { applyRouteRedirect, ensureDefaultHashRoute, pageHash, parseHashRoute, type PageKey } from "./app/routes";
import { WorkbenchSidebar } from "./app/shell/Sidebar";
import { loadWorkbenchData, workbenchData, type WorkbenchDataSource } from "./data";
import { inferSourceInput, sourceAnalysisLabel, type SourceFormType } from "./features/project-inputs/model";
import { selectableProductionRuntimes } from "./entities/runtime/lib";
import { IssuesWorkbenchPage } from "./pages/issues/IssuesPage";
import { AriadneApiError } from "./shared/api/errors";
import { CurrentVersionStrip } from "./widgets/current-version/CurrentVersionStrip";
import {
  analyzeSource,
  applyIssueFactoryPreview,
  acknowledgeInboxItem,
  createIssueFactoryPreview,
  createInboxRepairTicket,
  createProjectGoal,
  createSource,
  registerTargetProject,
  rerunInboxAssignment,
  resolveInboxItem,
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

function apiErrorCode(error: unknown) {
  if (!(error instanceof AriadneApiError)) return undefined;
  try {
    const body = JSON.parse(error.body) as { error?: { code?: string } };
    return body.error?.code;
  } catch {
    return undefined;
  }
}

export function App() {
  const initialRoute = parseHashRoute();
  const [page, setPage] = useState<PageKey>(initialRoute.page ?? "ready");
  const [data, setData] = useState<WorkbenchData>(workbenchData);
  const [dataSource, setDataSource] = useState<WorkbenchDataSource>("disconnected");
  const [readOnly, setReadOnly] = useState(true);
  const [issueRef, setIssueRef] = useState(initialRoute.ticketRef);
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
    applyRouteRedirect(route);
    setIssueRef(preferredTicketRef ?? route.ticketRef);
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
      <IssuesWorkbenchPage
        data={data}
        readOnly={readOnly}
        selectedRuntime={selectedRuntime}
        issueRef={issueRef}
        onRefreshWorkbench={onRefresh}
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
      <InboxPage
        data={data}
        readOnly={readOnly}
        onNavigate={onNavigate}
        onRefresh={onRefresh}
        onTicketSelect={onTicketSelect}
      />
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

function DeliveryPage({
  data,
  dataSource,
  onNavigate,
  onTicketSelect,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  onNavigate: (page: PageKey) => void;
  onTicketSelect: (ticketId: string) => void;
}) {
  const delivery = data.currentVersionDelivery;
  const environment = data.environment;
  const latestRun = delivery?.latestRealRun;
  const targetProject = getActiveTargetProject(data);
  const currentTickets = getCurrentVersionTickets(data);
  const currentTicketKeys = new Set(currentTickets.map((ticket) => ticket.key));
  const currentWorkflows = getCurrentVersionWorkflows(data);
  const nextAction = nextDeliveryAction(data);
  const readyInputs = data.projectInputs?.filter((input) => input.lifecycle.readyForIssueFactory).length ?? 0;
  const inputTotal = data.projectInputs?.length ?? data.sources.length;
  const blockedTickets = currentTickets.filter((ticket) => ticket.status === "blocked").length;
  const runningTickets = currentTickets.filter((ticket) => ticket.status === "running").length;
  const doneTickets = currentTickets.filter((ticket) => ticket.status === "done").length;
  const testLabel = targetProject?.testCommand
    || (latestRun?.testExitCode === 0 ? "最近测试通过" : "未设置");

  return (
    <section className="page full-bleed delivery-page">
      <PageHeader
        icon={<FolderKanban size={17} />}
        title="版本工作台"
        count={currentTickets.length}
        description="只看一个项目版本：输入、任务、智能体执行、证据。"
        action={
          <div className="toolbar">
            <button type="button" onClick={() => onNavigate("sources")}>添加输入</button>
            <button type="button" onClick={() => onNavigate("tasks")}>生成任务</button>
            <button className="primary-action" type="button" onClick={() => onNavigate(nextAction.page)}>{nextAction.label}</button>
          </div>
        }
      />
      <section className="version-hero" data-testid="delivery-status">
        <div className="version-heading">
          <p className="eyebrow">{delivery?.versionLabel ?? "v0.1"}</p>
          <h2>{projectDisplayName(data)}</h2>
          <p>{data.goal.northStar}</p>
          <div className="version-meta">
            <span>{targetProject?.localPath ?? "还没有目标项目路径"}</span>
            <span>测试：{testLabel}</span>
            <span>API：{dataSource === "api" ? "已连接" : "未连接"}</span>
          </div>
        </div>
        <aside className={`next-action-card ${delivery?.status ?? "unknown"}`}>
          <span>{userFacingStatus(delivery?.status)}</span>
          <strong>{nextAction.label}</strong>
          <p>{nextAction.detail}</p>
          <button className="primary-action" type="button" onClick={() => onNavigate(nextAction.page)}>继续</button>
        </aside>
      </section>

      <section className="version-metrics" aria-label="当前版本概览">
        <MetricCard label="输入" value={`${readyInputs}/${inputTotal}`} detail="可用于生成任务" />
        <MetricCard label="当前任务" value={String(currentTickets.length)} detail={`${runningTickets} 运行 · ${blockedTickets} 阻塞 · ${doneTickets} 完成`} />
        <MetricCard label="本地运行时" value={statusLabel(data.daemonStatus.status)} detail={data.daemonStatus.currentTicketKey ? `正在处理 ${data.daemonStatus.currentTicketKey}` : "没有当前任务"} />
        <MetricCard label="最近执行" value={latestRun?.ticketKey ?? "无"} detail={latestRun ? `${latestRun.backendName} · ${statusLabel(latestRun.reviewVerdict ?? "pending")}` : "还没有 Codex/Claude 证据"} />
      </section>

      <section className="version-workbench">
        <article className="version-panel">
          <ColumnHeader title="1. 项目输入" meta={`${readyInputs}/${inputTotal} 可用`} />
          <div className="delivery-input-list">
            {(data.projectInputs ?? []).slice(0, 5).map((input) => (
              <button key={input.source.id} type="button" onClick={() => onNavigate("sources")}>
                <strong>{input.source.title}</strong>
                <span>{input.lifecycle.label}</span>
                <small>{input.artifacts.length} 个产物 · {input.evidence.length} 条证据</small>
              </button>
            ))}
            {!data.projectInputs?.length ? <p className="empty-column">还没有项目输入。先粘贴链接或选择本地文件夹。</p> : null}
          </div>
        </article>

        <article className="version-panel">
          <ColumnHeader title="2. 当前版本任务" meta={`${currentTickets.length} 个`} />
          <div className="delivery-issue-list">
            {currentTickets.slice(0, 8).map((ticket) => (
              <button
                key={ticket.id}
                type="button"
                onClick={() => {
                  onTicketSelect(ticket.id);
                  onNavigate("ready");
                }}
              >
                <strong>{ticket.key}</strong>
                <span>{ticket.title}</span>
                <small>{statusLabel(ticket.status)} · {ticket.owner}</small>
              </button>
            ))}
            {!currentTickets.length ? <p className="empty-column">还没有当前版本任务。先生成并应用任务建议。</p> : null}
          </div>
        </article>

        <article className="version-panel" data-testid="execution-proof">
          <ColumnHeader title="3. 智能体执行" meta={latestRun ? latestRun.backendName : "未开始"} />
          {latestRun ? (
            <div className="run-summary">
              <strong>{latestRun.ticketKey}</strong>
              <span>执行结果：{latestRun.executionResultId}</span>
              <span>退出码：{String(latestRun.exitCode ?? "未记录")} · 测试：{String(latestRun.testExitCode ?? "未记录")}</span>
              <span>评审：{statusLabel(latestRun.reviewVerdict ?? "pending")}</span>
              <div className="file-list">
                {latestRun.changedFiles.length ? latestRun.changedFiles.map((file) => <code key={file}>{file}</code>) : <span>没有文件变更</span>}
              </div>
            </div>
          ) : (
            <p className="empty-column">还没有真实执行证据。分配当前任务后，这里会显示 trajectory、diff、tests 和 review。</p>
          )}
        </article>
      </section>

      <details className="technical-details">
        <summary>技术详情：门禁、环境和 Agent 工作流</summary>
        <section className="delivery-grid compact">
          <article className="panel delivery-panel">
            <h2>运行环境</h2>
            <PropertyGrid
              rows={[
                ["连接", environment?.connectionMode ?? dataSource],
                ["执行", environment?.executionMode ?? "unknown"],
                ["推荐后端", fallbackText(environment?.selectedBackendRecommendation)],
                ["生产后端", environment?.productionBackendsAvailable.join(", ") || "无"],
                ["Daemon", statusLabel(data.daemonStatus.status)],
                ["后台循环", data.daemonStatus.backgroundRunning ? "运行中" : "未运行"],
              ]}
            />
            {environment?.blockers.length ? (
              <div className="delivery-blockers">
                {environment.blockers.map((blocker) => (
                  <span key={blocker.code}>{blocker.message}</span>
                ))}
              </div>
            ) : <p className="muted">当前没有环境阻塞。</p>}
          </article>
          <article className="panel delivery-panel">
            <h2>交付门禁</h2>
            <div className="delivery-gates">
              {(delivery?.gates ?? []).map((gate) => (
                <div className={`delivery-gate ${gate.status}`} key={gate.id}>
                  <strong>{gate.label}</strong>
                  <span>{statusLabel(gate.status)}</span>
                  <p>{gate.detail || "已满足"}</p>
                  {gate.refId ? <code>{gate.refId}</code> : null}
                </div>
              ))}
              {!delivery?.gates.length ? <p className="empty-column">还没有门禁证据。</p> : null}
            </div>
          </article>
          <article className="panel delivery-panel wide">
            <h2>Agent 工作流</h2>
            <div className="workflow-list compact">
              {[...currentWorkflows]
                .sort((left, right) => left.ticketKey.localeCompare(right.ticketKey) || left.sequence - right.sequence)
                .slice(0, 24)
                .map((step) => (
                  <div className="workflow-step" data-testid="agent-workflow-step" key={step.id}>
                    <span>{step.ticketKey}</span>
                    <strong>{step.agentName}</strong>
                    <em>{statusLabel(step.status)}</em>
                    <p>{step.nextAction}</p>
                    <small>{step.outputRefs.length} 个输出证据</small>
                  </div>
                ))}
              {!currentWorkflows.length ? <p className="empty-column">还没有当前版本 agent 工作流证据。</p> : null}
            </div>
          </article>
        </section>
      </details>
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
  const [isAddingSource, setIsAddingSource] = useState(false);
  const selectedSource = data.sources.find((source) => source.id === selectedSourceId) ?? data.sources[0];
  const selectedUnderstanding = data.sourceUnderstandings.find((item) => item.sourceId === selectedSourceId);
  const [selectedChangeId, setSelectedChangeId] = useState(data.backlogChanges[0]?.id ?? "");
  const selectedChange = data.backlogChanges.find((change) => change.id === selectedChangeId) ?? data.backlogChanges[0];
  const [previewStatus, setPreviewStatus] = useState(data.backlogMutationPreview.status);
  const [currentPreviewId, setCurrentPreviewId] = useState(data.backlogMutationPreview.previewId ?? "");

  useEffect(() => {
    if (!data.sources.some((source) => source.id === selectedSourceId)) {
      setSelectedSourceId(data.sources[0]?.id ?? "");
    }
    if (!data.backlogChanges.some((change) => change.id === selectedChangeId)) {
      setSelectedChangeId(data.backlogChanges[0]?.id ?? "");
    }
    setPreviewStatus(data.backlogMutationPreview.status);
    if (data.backlogMutationPreview.previewId) {
      setCurrentPreviewId(data.backlogMutationPreview.previewId);
    }
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
    if (!sourceUrl.trim() || isAddingSource) return;
    const inferred = inferSourceInput(sourceUrl);
    const title = sourceTitle.trim() || inferred.title || sourceUrl.trim();
    const summary = sourceContent.trim() || inferred.summary;
    setIsAddingSource(true);
    setActionStatus(`正在添加并分析：${title}`);
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
      setActionStatus(
        result.duplicate
          ? `这个输入已经存在，已打开现有记录：${result.source.title}`
          : `分析完成：${result.source.title}`,
      );
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "添加或分析失败。");
    } finally {
      setIsAddingSource(false);
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
      setCurrentPreviewId(result.preview.id);
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
    const previewId = currentPreviewId || activePreviewId;
    if (!previewId) {
      setActionStatus("还没有可应用的任务预览。");
      return;
    }
    setActionStatus("正在应用任务变更...");
    try {
      await applyIssueFactoryPreview(previewId);
      await onRefresh();
      setPreviewStatus("applied");
      setActionStatus("任务建议已应用，新的项目 issue 已写入任务列表。");
    } catch (error) {
      if (apiErrorCode(error) === "stale_preview" && activeGoal) {
        setPreviewStatus("preview_only");
        setActionStatus("任务列表已变化，正在刷新并应用最新任务建议...");
        try {
          const result = await createIssueFactoryPreview({
            goal_id: activeGoal.id,
            source_ids: analyzedSourceIds,
            target_project_id: activeProject?.id ?? null,
          });
          await applyIssueFactoryPreview(result.preview.id);
          await onRefresh();
          setCurrentPreviewId(result.preview.id);
          setSelectedChangeId(result.preview.operations[0]?.id ?? "");
          setPreviewStatus("applied");
          setActionStatus("任务列表已变化，已自动应用最新任务建议。");
          return;
        } catch (refreshError) {
          setActionStatus(refreshError instanceof Error ? refreshError.message : "任务建议刷新或应用失败。");
          return;
        }
      }
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
          <button disabled={dataSource !== "api" || isAddingSource || !sourceUrl.trim()} type="button" onClick={() => void addSource()}>
            {isAddingSource ? "分析中..." : "添加并分析"}
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
  const [currentPreviewId, setCurrentPreviewId] = useState(data.backlogMutationPreview.previewId ?? "");
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
    if (data.backlogMutationPreview.previewId) {
      setCurrentPreviewId(data.backlogMutationPreview.previewId);
    }
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
      setCurrentPreviewId(result.preview.id);
      setSelectedChangeId(result.preview.operations[0]?.id ?? "");
      setActionStatus(`已生成 ${result.preview.operations.length} 个任务建议。`);
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "任务建议生成失败。");
    }
  }

  async function applyPreview() {
    const previewId = currentPreviewId || activePreviewId;
    if (!previewId) {
      setActionStatus("还没有可应用的任务预览。");
      return;
    }
    setActionStatus("正在应用任务变更...");
    try {
      await applyIssueFactoryPreview(previewId);
      await onRefresh();
      setPreviewStatus("applied");
      setActionStatus("任务变更已应用，新的项目 issue 已写入任务列表。");
    } catch (error) {
      if (apiErrorCode(error) === "stale_preview" && activeGoal) {
        setPreviewStatus("preview_only");
        setActionStatus("任务列表已变化，正在刷新并应用最新任务建议...");
        try {
          const result = await createIssueFactoryPreview({
            goal_id: activeGoal.id,
            source_ids: analyzedSourceIds,
            target_project_id: activeProject?.id ?? null,
          });
          await applyIssueFactoryPreview(result.preview.id);
          await onRefresh();
          setCurrentPreviewId(result.preview.id);
          setSelectedChangeId(result.preview.operations[0]?.id ?? "");
          setPreviewStatus("applied");
          setActionStatus("任务列表已变化，已自动应用最新任务建议。");
          return;
        } catch (refreshError) {
          setActionStatus(refreshError instanceof Error ? refreshError.message : "任务建议刷新或应用失败。");
          return;
        }
      }
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
  readOnly,
  onNavigate,
  onRefresh,
  onTicketSelect,
}: {
  data: WorkbenchData;
  readOnly: boolean;
  onNavigate: (page: PageKey) => void;
  onRefresh: (preferredTicketRef?: string) => Promise<void>;
  onTicketSelect: (ticketId: string) => void;
}) {
  const [actionStatus, setActionStatus] = useState("");

  function openTicketForItem(item: WorkbenchData["inbox"][number], index: number) {
    const fallbackTicket = data.tickets[index % data.tickets.length];
    const targetTicketId = item.repairTicketId ?? item.ticketId;
    const ticket = data.tickets.find((candidate) => candidate.id === targetTicketId) ?? fallbackTicket;
    if (ticket) onTicketSelect(ticket.id);
    onNavigate("ready");
  }

  async function runInboxAction(
    item: WorkbenchData["inbox"][number],
    label: string,
    action: () => Promise<{ ticket?: { key: string } | null; assignment?: { ticket_key?: string } | null; message?: string }>,
  ) {
    if (readOnly) {
      setActionStatus("未连接本地控制面，无法处理收件箱。");
      return;
    }
    setActionStatus(`${label}...`);
    try {
      const result = await action();
      const ticketRef = result.ticket?.key ?? result.assignment?.ticket_key ?? item.ticketKey;
      setActionStatus(result.message || `${label}完成`);
      await onRefresh(ticketRef);
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : `${label}失败`);
    }
  }

  return (
    <section className="page">
      <PageHeader icon={<Inbox size={17} />} title="收件箱" count={data.inbox.length} />
      {actionStatus ? <p className="action-status">{actionStatus}</p> : null}
      <div className="inbox-list">
        {data.inbox.map((item, index) => (
          <article
            className="inbox-card"
            key={item.id}
          >
            <button type="button" className="inbox-main" onClick={() => openTicketForItem(item, index)}>
              <span className={`inbox-kind ${item.kind}`}>{statusLabel(item.kind)}</span>
              <strong>{item.title}</strong>
              <p>{item.body}</p>
            </button>
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
            <div className="inbox-actions">
              <button
                type="button"
                disabled={readOnly}
                onClick={() => runInboxAction(item, "创建修复任务", () => createInboxRepairTicket(item.id))}
              >
                创建修复任务
              </button>
              <button
                type="button"
                disabled={readOnly}
                onClick={() => runInboxAction(item, "重跑关联任务", () => rerunInboxAssignment(item.id))}
              >
                重跑
              </button>
              <button
                type="button"
                disabled={readOnly}
                onClick={() => runInboxAction(item, "确认已读", () => acknowledgeInboxItem(item.id))}
              >
                确认已读
              </button>
              <button
                type="button"
                disabled={readOnly}
                onClick={() => runInboxAction(item, "标记已解决", () => resolveInboxItem(item.id))}
              >
                标记已解决
              </button>
            </div>
            <em>{item.time}</em>
          </article>
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
