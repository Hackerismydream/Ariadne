import type { WorkbenchDataSource } from "../../data";
import type { PageKey } from "../../app/routes";
import { pageHash } from "../../app/routes";
import type { WorkbenchData } from "../../types";

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    active: "进行中",
    applied: "已应用",
    blocked: "已阻塞",
    done: "已完成",
    failed: "失败",
    in_progress: "推进中",
    pass: "通过",
    pending: "待处理",
    planning: "规划中",
    ready: "待执行",
    REAL_CLOSED: "真实闭环",
    BLOCKED_WITH_EVIDENCE: "阻塞诊断",
    OFFLINE_REGRESSION: "离线回归",
    NOT_CLOSED: "未闭环",
    real_closed: "已完成真实闭环",
    reviewing: "审核中",
    running: "运行中",
    unknown: "未知",
  };
  return labels[status] ?? status;
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
  const targetProjectId = data.currentVersionDelivery?.targetProjectId
    ?? data.goal.targetProjectId
    ?? getActiveTargetProject(data)?.id;
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

function userFacingStatus(status?: string, closureStatus?: string) {
  if (closureStatus === "REAL_CLOSED") return "已完成真实闭环";
  if (closureStatus === "BLOCKED_WITH_EVIDENCE") return "阻塞诊断，不是闭环";
  if (closureStatus === "OFFLINE_REGRESSION") return "离线回归，不是闭环";
  if (closureStatus === "NOT_CLOSED") return "未完成产品闭环";
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
  if (delivery?.productClosureStatus === "REAL_CLOSED" && delivery.latestRealRun?.reviewVerdict === "pass") {
    return { label: "查看版本证据", detail: `${delivery.latestRealRun.ticketKey} 已由 ${delivery.latestRealRun.backendName} 完成真实执行。`, page: "ready" as PageKey };
  }
  const blockers = [
    ...(delivery?.blockers ?? []),
    ...(data.environment?.blockers.map((blocker) => blocker.message) ?? []),
  ].filter(Boolean);
  if (!inputs.length) return { label: "先添加项目输入", detail: "把博客、GitHub 仓库、论文或本地文件夹放进来。", page: "sources" as PageKey };
  if (!readyInputs) return { label: "先分析项目输入", detail: "已有输入还没有形成可用于任务生成的证据。", page: "sources" as PageKey };
  if (!currentTickets.length) return { label: "生成当前版本任务", detail: "用项目目标和已分析输入生成目标项目 issue。", page: "tasks" as PageKey };
  if (blockers.length) return { label: "处理当前阻塞", detail: blockers[0], page: "ready" as PageKey };
  if (!delivery?.latestRealRun) return { label: "分配给 Codex/Claude", detail: "选择当前 issue，创建 assignment 并让本地运行时执行。", page: "ready" as PageKey };
  if (delivery.latestRealRun.reviewVerdict !== "pass") return { label: "查看执行证据并修复", detail: `${delivery.latestRealRun.ticketKey} 已执行，但 review 还没有通过。`, page: "ready" as PageKey };
  if (delivery.productClosureStatus !== "REAL_CLOSED") {
    return {
      label: "运行浏览器闭环验收",
      detail: delivery.productClosureReason || delivery.productClosureRequiredCommand || "真实执行通过，但还没有浏览器 closure-result。",
      page: "ready" as PageKey,
    };
  }
  return { label: "查看版本证据", detail: "当前版本已有执行证据，继续检查 diff、tests、review 和 next issue。", page: "ready" as PageKey };
}

function ContextItem({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="context-item">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

export function CurrentVersionStrip({
  data,
  dataSource,
  onNavigate,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  onNavigate: (page: PageKey, hash?: string) => void;
}) {
  const delivery = data.currentVersionDelivery;
  const targetProject = getActiveTargetProject(data);
  const currentTickets = getCurrentVersionTickets(data);
  const currentWorkflows = getCurrentVersionWorkflows(data);
  const nextAction = nextDeliveryAction(data);
  const inputTotal = data.projectInputs?.length ?? data.sources.length;
  const readyInputs = data.projectInputs?.filter((input) => input.lifecycle.readyForIssueFactory).length ?? 0;
  const blockedCount = (delivery?.blockers.length ?? 0)
    + currentTickets.filter((ticket) => ticket.status === "blocked").length
    + data.inbox.filter((item) => item.active !== false && item.status !== "resolved").length;
  const blockingWorkflow = currentWorkflows.find((step) => ["blocked", "failed"].includes(step.status));
  const runningWorkflow = currentWorkflows.find((step) => ["queued", "claimed", "running", "in_progress"].includes(step.status));
  const activeWorkflow = delivery?.status === "blocked"
    ? blockingWorkflow ?? runningWorkflow
    : runningWorkflow ?? blockingWorkflow;
  const activeDaemonTicket = data.daemonStatus.stale === true ? null : data.daemonStatus.currentTicketKey;
  const activeRun = delivery?.status === "blocked" && !blockingWorkflow
    ? `Blocked · ${delivery.blockers[0] ?? "current version blocked"}`
    : activeWorkflow
        ? `${activeWorkflow.ticketKey} · ${activeWorkflow.agentName} · ${statusLabel(activeWorkflow.status)}`
        : activeDaemonTicket
          ? `${activeDaemonTicket} · ${statusLabel(data.daemonStatus.status)}`
          : "No active run";
  const closureValue = statusLabel(delivery?.productClosureStatus ?? "NOT_CLOSED");
  const latestEvidence = delivery?.latestRealRun
    ? `${delivery.latestRealRun.ticketKey} · ${delivery.latestRealRun.backendName} · ${statusLabel(delivery.latestRealRun.terminalVerdict ?? "unknown")} · tests ${delivery.latestRealRun.testExitCode ?? "n/a"} · review ${statusLabel(delivery.latestRealRun.reviewVerdict ?? "pending")}`
    : delivery?.evidenceRefs[0] ?? "No real execution evidence yet";
  const issueDeltaStatus = data.backlogMutationPreview.status
    ? statusLabel(data.backlogMutationPreview.status)
    : userFacingStatus(delivery?.status);
  const goalText = data.goal.northStar || data.goal.title;
  const versionLabel = delivery?.versionLabel ?? "v0.1";

  return (
    <section className="current-version-context" data-testid="current-version-context" aria-label="Current Version Context">
      <div className="context-primary">
        <span>Current Version Context</span>
        <strong>{projectDisplayName(data)}</strong>
        <p>{goalText}</p>
      </div>
      <div className="context-grid">
        <ContextItem
          label="Project"
          value={targetProject?.label ?? delivery?.targetProjectLabel ?? projectDisplayName(data)}
          detail={targetProject?.localPath ?? "Target project not registered"}
        />
        <ContextItem label="Target Version" value={versionLabel} detail={userFacingStatus(delivery?.status, delivery?.productClosureStatus)} />
        <ContextItem label="Goal" value={data.goal.title} detail={goalText} />
        <ContextItem label="Sources readiness" value={`${readyInputs}/${inputTotal}`} detail={inputTotal ? "ready for issue factory" : "no project inputs"} />
        <ContextItem label="Issue Delta status" value={issueDeltaStatus} detail={`${currentTickets.length} current issues`} />
        <ContextItem label="Active Run" value={activeRun} detail={dataSource === "api" ? "API connected" : "read-only/disconnected"} />
        <ContextItem label="Blocked count" value={String(blockedCount)} detail={delivery?.blockers[0] ?? data.environment?.blockers[0]?.message ?? "no top blocker"} />
        <ContextItem label="Product Closure" value={closureValue} detail={delivery?.productClosureReason || delivery?.productClosureSummary || "browser closure-result required"} />
        <ContextItem label="Latest Evidence" value={latestEvidence} detail={delivery?.latestRealRun?.executionResultId ?? delivery?.generatedAt ?? "not generated"} />
        <button className="context-next-action" type="button" onClick={() => onNavigate(nextAction.page, pageHash(nextAction.page))}>
          <span>Next Action</span>
          <strong>{nextAction.label}</strong>
          <small>{nextAction.detail}</small>
        </button>
      </div>
    </section>
  );
}
