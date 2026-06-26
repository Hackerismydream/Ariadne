import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { dirname, extname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, "..");
const repoRoot = resolve(frontendRoot, "..", "..");
const ariadneRoot = resolve(process.env.ARIADNE_WORKBENCH_ARIADNE_ROOT ?? resolve(repoRoot, ".ariadne"));
const outputPath = resolve(
  process.env.ARIADNE_WORKBENCH_OUTPUT_PATH ?? resolve(frontendRoot, "public", "web_data", "workbench.json"),
);

async function readJson(path, fallback) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch {
    return fallback;
  }
}

async function readJsonFiles(dir) {
  try {
    const names = await readdir(dir);
    const files = names.filter((name) => extname(name) === ".json").sort();
    return (await Promise.all(files.map((name) => readJson(resolve(dir, name), null)))).filter(Boolean);
  } catch {
    return [];
  }
}

async function readNestedJsonFiles(dir) {
  try {
    const names = await readdir(dir, { withFileTypes: true });
    const nested = await Promise.all(
      names
        .filter((entry) => entry.isDirectory())
        .map((entry) => readJsonFiles(resolve(dir, entry.name))),
    );
    return nested.flat();
  } catch {
    return [];
  }
}

async function readJsonl(path) {
  try {
    const text = await readFile(path, "utf8");
    return text
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line));
  } catch {
    return [];
  }
}

function runtimeFromCapability(capability) {
  return {
    machine: "local-mac",
    backend: capability.backend_name,
    status: capability.available ? "online" : "offline",
    version: capability.command_path ?? capability.command ?? "internal",
    cost7d: "$0.00",
    command: capability.command,
    commandPath: capability.command_path,
    externalExecutionEnabled: capability.external_execution_enabled,
    commandTemplateSet: capability.command_template_set,
    confirmExecutionRequired: capability.confirm_execution_required,
    supportsExternalExecution: capability.supports_external_execution,
    supportsDryRun: capability.supports_dry_run,
    checkedAt: capability.checked_at,
  };
}

function resourceFromProjectResource(resource) {
  return {
    id: resource.id,
    label: resource.label,
    resourceType: resource.resource_type,
    localPath: resource.resource_ref?.local_path,
  };
}

function normalizeStatus(status) {
  const mapping = {
    inbox: "inbox",
    planning: "planning",
    ready_for_execution: "ready",
    assigned: "running",
    running: "running",
    in_review: "reviewing",
    reviewing: "reviewing",
    done: "done",
    blocked: "blocked",
  };
  return mapping[status] ?? "planning";
}

function normalizePriority(priority) {
  if (["high", "medium", "low"].includes(priority)) return priority;
  if (priority === "P1") return "high";
  if (priority === "P3") return "low";
  return "medium";
}

function eventTime(value) {
  if (!value) return "";
  return String(value).replace("T", " ").replace("Z", "");
}

function latestByTicket(items, ticketKey, ticketId, predicate = () => true) {
  return items
    .filter((item) => (item.ticket_key === ticketKey || item.ticket_id === ticketId) && predicate(item))
    .sort((a, b) => String(a.created_at ?? "").localeCompare(String(b.created_at ?? "")))
    .at(-1);
}

function byTicket(items, ticketKey, ticketId) {
  return items
    .filter((item) => item.ticket_key === ticketKey || item.ticket_id === ticketId)
    .sort((a, b) => String(a.created_at ?? "").localeCompare(String(b.created_at ?? "")));
}

function githubCheckCounts(checks) {
  const counts = { pass: 0, pending: 0, fail: 0, total: Array.isArray(checks) ? checks.length : 0 };
  if (!Array.isArray(checks)) return counts;
  for (const check of checks) {
    const bucket = String(check?.bucket ?? "").toLowerCase();
    const conclusion = String(check?.conclusion ?? "").toLowerCase();
    const state = String(check?.state ?? check?.status ?? "").toLowerCase();
    if (["pass", "success"].includes(bucket) || ["success", "neutral", "skipped"].includes(conclusion)) {
      counts.pass += 1;
    } else if (bucket === "pending" || ["pending", "queued", "in_progress", "waiting"].includes(state)) {
      counts.pending += 1;
    } else {
      counts.fail += 1;
    }
  }
  return counts;
}

function githubEvidenceForTicket(ticket, githubResults) {
  const history = byTicket(githubResults, ticket.key, ticket.id);
  if (!history.length) return undefined;
  const latest = [...history].reverse().find((item) => item.operation === "status") ?? history.at(-1);
  const evidence = latest.evidence ?? {};
  const pr = evidence.pr ?? {};
  return {
    operation: latest.operation,
    ok: Boolean(latest.ok),
    blocked: Boolean(latest.blocked),
    repo: latest.repo,
    issueNumber: latest.issue_number,
    issueUrl: latest.issue_url ?? evidence.issue?.url,
    prNumber: latest.pr_number ?? pr.number,
    prUrl: latest.pr_url ?? pr.url,
    branch: latest.branch ?? pr.headRefName,
    commitSha: latest.commit_sha ?? pr.headRefOid,
    commentUrl: latest.comment_url,
    checksStatus: evidence.checks_status,
    checkCounts: githubCheckCounts(evidence.checks),
    reviewDecision: pr.reviewDecision || "none",
    mergeable: pr.mergeable,
    baseBranch: pr.baseRefName,
    history: history.slice(-5).map((item) => ({
      operation: item.operation,
      ok: Boolean(item.ok),
      blocked: Boolean(item.blocked),
      createdAt: eventTime(item.created_at),
    })),
  };
}

function backendSmokeFromStore(item) {
  return {
    id: item.id,
    backendName: item.backend_name,
    ticketId: item.ticket_id,
    ticketKey: item.ticket_key,
    assignmentId: item.assignment_id,
    assignmentStatus: item.assignment_status,
    succeeded: Boolean(item.succeeded),
    blocked: Boolean(item.blocked),
    blocker: item.blocker,
    executionResultId: item.execution_result_id,
    exitCode: item.exit_code,
    changedFiles: item.changed_files ?? [],
    testExitCode: item.test_exit_code,
    reviewVerdict: item.review_verdict,
    handoffFile: item.handoff_file,
    boardPath: item.board_path,
    memoryPath: item.memory_path,
    feishuPlanPath: item.feishu_plan_path,
    nextTicketsPath: item.next_tickets_path,
    agentRuntime: item.agent_runtime ?? "deterministic",
    backlogPlannerName: item.backlog_planner_name ?? "deterministic",
    externalExecutionEnabled: Boolean(item.external_execution_enabled),
    confirmExecution: Boolean(item.confirm_execution),
    createdAt: eventTime(item.created_at),
  };
}

function backendSmokeForTicket(ticket, backendSmokeResults) {
  return backendSmokeResults
    .filter((item) => item.ticket_key === ticket.key || item.ticket_id === ticket.id)
    .sort((a, b) => String(a.created_at ?? "").localeCompare(String(b.created_at ?? "")))
    .map(backendSmokeFromStore)
    .at(-1);
}

async function llmAgentResultsFromIndex(artifactIndex) {
  const llmArtifacts = artifactIndex.filter((artifact) => artifact.artifact_type === "llm_agent_result");
  return (
    await Promise.all(
      llmArtifacts.map(async (artifact) => {
        const payload = await readJson(artifact.path, {});
        const metadata = artifact.metadata ?? {};
        const output = payload.output_json ?? {};
        return {
          id: artifact.id,
          ticketId: artifact.ticket_id,
          role: metadata.llm_role ?? payload.role ?? "unknown",
          provider: metadata.provider ?? payload.provider ?? "unknown",
          model: metadata.model ?? payload.model ?? "unknown",
          succeeded: Boolean(metadata.succeeded ?? payload.succeeded),
          summary: output.summary ?? null,
          decision: output.decision ?? null,
          totalTokens: payload.usage?.total_tokens ?? null,
          path: artifact.path,
          createdAt: eventTime(artifact.created_at),
        };
      }),
    )
  ).filter((item) => item.role !== "unknown");
}

function llmAgentsForTicket(ticket, llmAgentResults) {
  const latestByRole = new Map();
  for (const result of llmAgentResults
    .filter((item) => item.ticketId === ticket.id)
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt))) {
    latestByRole.set(result.role, result);
  }
  return Array.from(latestByRole.values()).sort((a, b) => a.role.localeCompare(b.role));
}

function feishuEvidenceForTicket(ticket, feishuResults) {
  const history = byTicket(feishuResults, ticket.key, ticket.id);
  if (!history.length) return undefined;
  const latest = [...history].reverse().find((item) => item.ok && !item.blocked && !item.dry_run) ?? history.at(-1);
  return {
    id: latest.id,
    ok: Boolean(latest.ok),
    blocked: Boolean(latest.blocked),
    dryRun: Boolean(latest.dry_run),
    documentUrl: latest.document_url,
    documentId: latest.document_id,
    operationSummary: latest.operation_summary,
    reason: latest.reason,
    returncode: latest.returncode,
    path: `.ariadne/integrations/feishu/${latest.ticket_key}/${latest.id}.json`,
    createdAt: eventTime(latest.created_at),
  };
}

function releaseEvidenceSummary(releaseEvidence) {
  if (!releaseEvidence?.id) return undefined;
  return {
    id: releaseEvidence.id,
    productionAcceptanceStatus: releaseEvidence.production_acceptance_status,
    productReadinessStatus: releaseEvidence.product_readiness_status,
    productClosureStatus: releaseEvidence.product_closure_status,
    productClosureMode: releaseEvidence.product_closure_mode,
    productClosureSummary: releaseEvidence.product_closure_summary,
    productClosureReason: releaseEvidence.product_closure_reason,
    productClosurePacketPath: releaseEvidence.product_closure_packet_path,
    productClosureRequiredCommand: releaseEvidence.product_closure_required_command,
    productClosureAcceptancePath: releaseEvidence.product_closure_acceptance_path,
    runGateStatus: releaseEvidence.run_gate_status,
    productReadinessChecks: releaseEvidence.product_readiness_checks ?? {},
    readinessNextActions: releaseEvidence.readiness_next_actions ?? [],
    readinessBlockers: releaseEvidence.readiness_blockers ?? [],
    evidencePacketStale: Boolean(releaseEvidence.evidence_packet_stale),
    evidencePacketStaleReasons: releaseEvidence.evidence_packet_stale_reasons ?? [],
    realSuccessEvidence: releaseEvidence.real_success_evidence ?? {},
    realFailureEvidence: releaseEvidence.real_failure_evidence ?? {},
    evidenceRefs: releaseEvidence.evidence_refs ?? {},
    ticketCount: releaseEvidence.ticket_count ?? 0,
    executionResultCount: releaseEvidence.execution_result_count ?? 0,
    reviewReportCount: releaseEvidence.review_report_count ?? 0,
    inboxItemCount: releaseEvidence.inbox_item_count ?? 0,
    packetPath: ".ariadne/evidence/release_evidence_packet.json",
    generatedAt: eventTime(releaseEvidence.generated_at),
  };
}

function ticketProgress(ticket, comments, journalEvents) {
  const commentEvents = comments
    .filter((comment) => comment.ticket_id === ticket.id || comment.ticket_key === ticket.key)
    .slice(-8)
    .map((comment) => ({
      time: eventTime(comment.created_at),
      actor: comment.actor ?? comment.agent ?? "Ariadne",
      kind: comment.comment_type ?? comment.event_type ?? "progress",
      body: comment.body ?? comment.summary ?? "",
    }));
  if (commentEvents.length) return commentEvents;
  return journalEvents
    .filter((event) => event.ticket_id === ticket.id || event.ticket_key === ticket.key)
    .slice(-8)
    .map((event) => ({
      time: eventTime(event.created_at ?? event.timestamp),
      actor: event.actor ?? event.agent ?? "Ariadne",
      kind: event.stage ?? event.event_type ?? "progress",
      body: event.summary ?? event.message ?? event.status ?? "",
    }));
}

function ticketFromStore(ticket, context) {
  const buildPacket = context.buildPackets[ticket.id] ?? {};
  const review = latestByTicket(context.reviews, ticket.key, ticket.id);
  const changedFiles = context.changedFiles[ticket.id] ?? [];
  const nextTicketsPath = context.nextTicketsPath[ticket.id];
  const memoryPath = context.memoryPaths[ticket.id];
  const github = githubEvidenceForTicket(ticket, context.githubResults);
  const backendSmoke = backendSmokeForTicket(ticket, context.backendSmokeResults);
  const llmAgents = llmAgentsForTicket(ticket, context.llmAgentResults);
  const feishu = feishuEvidenceForTicket(ticket, context.feishuResults);
  return {
    id: ticket.id,
    key: ticket.key,
    title: ticket.title,
    summary: ticket.description,
    status: normalizeStatus(ticket.status),
    priority: normalizePriority(ticket.priority),
    owner: ticket.owner_agent ?? "Build Lead",
    source: ticket.source_ref ?? ticket.source_type ?? "",
    decision: buildPacket.build_decision ?? ticket.source_type ?? "unknown",
    changedFiles,
    progress: ticketProgress(ticket, context.comments, context.journalEvents),
    reviewVerdict: review?.verdict ?? "pending",
    memoryPath,
    nextTicketsPath,
    github,
    backendSmoke,
    llmAgents,
    feishu,
    releaseEvidence: context.releaseEvidenceSummary,
    acceptance: buildPacket.acceptance_criteria ?? [],
  };
}

function sourceFromTicket(ticket) {
  return {
    id: `source-${ticket.id}`,
    sourceType: ticket.source_type,
    title: ticket.title,
    status: ticket.build_packet_id ? "extracted" : "new",
    ingestedAt: eventTime(ticket.created_at),
    pathOrUrl: ticket.source_ref,
    linkedTicketCount: 1,
  };
}

function knowledgeCardFromPacket(packet, ticket) {
  return {
    id: `knowledge-${packet.id}`,
    sourceId: `source-${ticket.id}`,
    title: packet.insight || ticket.title,
    sourceSummary: packet.source_summary || ticket.description,
    evidence: (packet.evidence ?? []).map((item) => item.quote_or_summary ?? item.location ?? "").filter(Boolean),
    projectRelevance: packet.project_relevance ?? "",
    buildDecision: packet.build_decision ?? "watchlist",
    affectedModules: packet.affected_modules ?? [],
    risks: packet.risks ?? [],
    confidence: packet.confidence ?? 0.5,
    primary: packet.build_decision === "code_task" || packet.build_decision === "architecture_change",
  };
}

function backlogChangeFromNextTicket(nextTicket, index, ticket) {
  return {
    id: `${ticket.key}-next-${index + 1}`,
    knowledgeCardId: `knowledge-${ticket.build_packet_id ?? ticket.id}`,
    kind: "added",
    ticketKey: `${ticket.key}-NEXT-${index + 1}`,
    title: nextTicket.title,
    reason: nextTicket.reason,
    priority: nextTicket.priority === "high" ? "P1" : nextTicket.priority === "low" ? "P3" : "P2",
    suggestedOwnerAgent: "Build Lead",
    buildDecision: nextTicket.suggested_build_decision ?? "code_task",
  };
}

function backlogKindFromOperation(operationType) {
  const mapping = {
    add_ticket: "added",
    update_ticket: "updated",
    promote_ticket: "updated",
    defer_ticket: "deferred",
    supersede_ticket: "superseded",
    no_op: "no_op",
  };
  return mapping[operationType] ?? "updated";
}

function backlogChangeFromPreviewOperation(preview, operation, index) {
  const suggestion = operation.metadata?.suggestion ?? {};
  const sourcePacket = operation.metadata?.source_packet ?? {};
  const priority = operation.priority ?? suggestion.priority ?? "medium";
  const priorityLabel = priority === "high" || priority === "P1" ? "P1" : priority === "low" || priority === "P3" ? "P3" : "P2";
  return {
    id: `${preview.id}-${operation.id ?? index}`,
    knowledgeCardId: `knowledge-${sourcePacket.id ?? operation.ticket_id ?? preview.trigger_ref}`,
    kind: backlogKindFromOperation(operation.operation_type),
    ticketKey: operation.ticket_key ?? operation.ticket_id ?? preview.trigger_ref,
    title: operation.title ?? suggestion.title ?? operation.reason,
    reason: operation.reason ?? preview.rationale,
    priority: priorityLabel,
    suggestedOwnerAgent: operation.metadata?.suggested_owner_agent ?? "Build Lead",
    buildDecision: suggestion.suggested_build_decision ?? sourcePacket.build_decision ?? "code_task",
    previewId: preview.id,
    previewStatus: preview.applied_update_id ? "applied" : preview.conflicts?.length ? "blocked" : "preview_only",
    triggerType: preview.trigger_type,
    operationType: operation.operation_type,
    appliedUpdateId: preview.applied_update_id,
    conflictCount: preview.conflicts?.length ?? 0,
    evidenceRefs: preview.evidence_refs ?? [],
  };
}

function backlogChangesFromPreviews(previews) {
  return previews
    .sort((a, b) => String(a.created_at ?? "").localeCompare(String(b.created_at ?? "")))
    .flatMap((preview) => (preview.operations ?? []).map((operation, index) => backlogChangeFromPreviewOperation(preview, operation, index)));
}

function backlogMutationPreviewFromPreviews(previews, fallbackChanges, releaseEvidence) {
  if (!previews.length) {
    return {
      status: "applied",
      added: fallbackChanges.filter((change) => change.kind === "added").length,
      updated: fallbackChanges.filter((change) => change.kind === "updated").length,
      deferred: fallbackChanges.filter((change) => change.kind === "deferred").length,
      rejected: fallbackChanges.filter((change) => change.kind === "rejected").length,
      noOp: fallbackChanges.filter((change) => change.kind === "no_op").length,
      unsafe: releaseEvidence.store_invariants_ok === false ? 1 : 0,
      lastPreviewAt: eventTime(releaseEvidence.generated_at),
    };
  }
  const sorted = [...previews].sort((a, b) => String(a.created_at ?? "").localeCompare(String(b.created_at ?? "")));
  const latest = sorted.at(-1);
  const operations = sorted.flatMap((preview) => preview.operations ?? []);
  const conflictCount = sorted.reduce((total, preview) => total + (preview.conflicts?.length ?? 0), 0);
  return {
    status: latest?.applied_update_id ? "applied" : conflictCount ? "blocked" : "preview_only",
    added: operations.filter((operation) => backlogKindFromOperation(operation.operation_type) === "added").length,
    updated: operations.filter((operation) => backlogKindFromOperation(operation.operation_type) === "updated").length,
    deferred: operations.filter((operation) => backlogKindFromOperation(operation.operation_type) === "deferred").length,
    rejected: operations.filter((operation) => backlogKindFromOperation(operation.operation_type) === "rejected").length,
    noOp: operations.filter((operation) => backlogKindFromOperation(operation.operation_type) === "no_op").length,
    unsafe: conflictCount,
    lastPreviewAt: eventTime(latest?.created_at),
    previewId: latest?.id,
    triggerType: latest?.trigger_type,
    appliedUpdateId: latest?.applied_update_id,
  };
}

function inboxFromStore(item, repairTicketByInboxId = new Map()) {
  const kindBySource = {
    review: "review",
    assignment: "blocker",
    agent_run: "blocker",
    execution: "blocker",
    feishu: "memory",
    github: "memory",
    memory: "memory",
  };
  const repairTicket = repairTicketByInboxId.get(item.id);
  return {
    id: item.id,
    ticketId: item.ticket_id,
    ticketKey: item.ticket_key,
    title: item.title,
    body: item.summary,
    time: eventTime(item.created_at),
    kind: kindBySource[item.source_type] ?? "goal",
    status: item.status ?? "open",
    severity: item.severity ?? "medium",
    sourceType: item.source_type,
    sourceId: item.source_id,
    failureReason: item.failure_reason,
    recommendedAction: item.recommended_action,
    evidenceRef: item.evidence_ref,
    resolutionNote: item.resolution_note,
    repairTicketId: repairTicket?.id,
    repairTicketKey: repairTicket?.key,
  };
}

function agentFromRuns(name, backend, runs, status = "online") {
  return {
    name,
    description: `${name} backed by ${backend}.`,
    backend,
    status,
    runs,
    reasoning: backend === "Codex" ? "高" : "默认",
  };
}

async function main() {
  const runtimeSnapshot = await readJson(resolve(ariadneRoot, "runtimes", "capability_snapshot.json"), {
    capabilities: [],
  });
  const releaseEvidence = await readJson(resolve(ariadneRoot, "evidence", "release_evidence_packet.json"), {});
  const projectResources = await readJson(resolve(ariadneRoot, "project", "resources.json"), {
    resources: [],
  });
  const tickets = await readJsonFiles(resolve(ariadneRoot, "tickets"));
  const repairTicketByInboxId = new Map(
    tickets
      .filter((ticket) => ticket.metadata?.generated_from_inbox_item_id)
      .map((ticket) => [ticket.metadata.generated_from_inbox_item_id, ticket]),
  );
  const inboxPayload = await readJson(resolve(ariadneRoot, "inbox", "items.json"), { items: [] });
  const githubResults = await readNestedJsonFiles(resolve(ariadneRoot, "integrations", "github"));
  const feishuResults = await readNestedJsonFiles(resolve(ariadneRoot, "integrations", "feishu"));
  const backendSmokeResults = await readNestedJsonFiles(resolve(ariadneRoot, "evidence", "backend_smoke"));
  const backlogPreviews = await readJsonFiles(resolve(ariadneRoot, "backlog", "previews"));
  const artifactIndex = await readJsonFiles(resolve(ariadneRoot, "artifact_index"));
  const llmAgentResults = await llmAgentResultsFromIndex(artifactIndex);
  const journalEvents = await readJsonl(resolve(ariadneRoot, "journal", "events.jsonl"));
  const comments = (await Promise.all(tickets.map((ticket) => readJsonl(resolve(ariadneRoot, "comments", `${ticket.id}.jsonl`))))).flat();

  const buildPackets = {};
  const changedFiles = {};
  const nextTicketsPath = {};
  const memoryPaths = {};
  const reviews = [];
  const backlogChanges = [];
  const knowledgeCards = [];

  for (const ticket of tickets) {
    const artifactDir = resolve(ariadneRoot, "artifacts", ticket.id);
    const packet = await readJson(resolve(artifactDir, "build_packet.json"), null);
    const changed = await readJson(resolve(artifactDir, "changed_files.json"), []);
    const review = await readJson(resolve(artifactDir, "review_report.json"), null);
    const nextTickets = await readJson(resolve(artifactDir, "next_tickets.json"), null);
    if (packet) {
      buildPackets[ticket.id] = packet;
      knowledgeCards.push(knowledgeCardFromPacket(packet, ticket));
    }
    if (Array.isArray(changed)) changedFiles[ticket.id] = changed;
    if (review) reviews.push(review);
    if (nextTickets?.next_tickets?.length) {
      nextTicketsPath[ticket.id] = `.ariadne/artifacts/${ticket.id}/next_tickets.json`;
      backlogChanges.push(...nextTickets.next_tickets.map((item, index) => backlogChangeFromNextTicket(item, index, ticket)));
    }
    try {
      await readFile(resolve(ariadneRoot, "memory", "tickets", `${ticket.id}.md`), "utf8");
      memoryPaths[ticket.id] = `.ariadne/memory/tickets/${ticket.id}.md`;
    } catch {
      // Missing memory is valid for not-yet-run tickets.
    }
  }

  const context = {
    buildPackets,
    backendSmokeResults,
    changedFiles,
    comments,
    feishuResults,
    journalEvents,
    githubResults,
    llmAgentResults,
    memoryPaths,
    nextTicketsPath,
    releaseEvidenceSummary: releaseEvidenceSummary(releaseEvidence),
    reviews,
  };
  const previewBacklogChanges = backlogChangesFromPreviews(backlogPreviews);
  const effectiveBacklogChanges = previewBacklogChanges.length ? previewBacklogChanges : backlogChanges;
  const runtimes = (runtimeSnapshot.capabilities ?? releaseEvidence.runtime_capabilities ?? []).map(runtimeFromCapability);
  const backendSmokeEvidence = backendSmokeResults.map(backendSmokeFromStore);
  const realIntegrationCards = [
    ...backendSmokeEvidence.filter((item) => item.succeeded).map((item) => ({
      id: `backend-smoke-${item.id}`,
      title: `${item.backendName} smoke passed`,
      body: `${item.ticketKey} · tests ${item.testExitCode ?? "missing"} · review ${item.reviewVerdict ?? "missing"}`,
      time: item.createdAt,
      kind: "memory",
      ticketId: item.ticketId,
    })),
    ...githubResults.filter((item) => item.ok).map((item) => ({
      id: `github-${item.id}`,
      title: `GitHub ${item.operation}`,
      body: item.comment_url ?? item.issue_url ?? item.repo ?? "GitHub result",
      time: eventTime(item.created_at),
      kind: "memory",
      ticketId: item.ticket_id,
    })),
    ...feishuResults.filter((item) => item.ok).map((item) => ({
      id: `feishu-${item.id}`,
      title: "Feishu write",
      body: item.document_url ?? item.operation_summary ?? "Feishu result",
      time: eventTime(item.created_at),
      kind: "memory",
      ticketId: item.ticket_id,
    })),
  ].slice(-6);

  const data = {
    goal: {
      id: "GOAL-2026-06-17-2043",
      title: "Ariadne Production Agent Workbench",
      northStar: "Knowledge, feedback, codebase state, and optional goals update tickets; agents execute tickets through real runtimes.",
      status: "active",
      knowledgeInputs: [
        "Multica issue-agent-runtime-board reference architecture",
        "Ariadne ticket-centered roadmap",
        "Release evidence packet",
      ],
      feedbackSignals: [
        `tickets=${releaseEvidence.ticket_count ?? tickets.length}`,
        `executions=${releaseEvidence.execution_result_count ?? 0}`,
        `inbox=${releaseEvidence.inbox_item_count ?? inboxPayload.items?.length ?? 0}`,
      ],
      currentState: `Branch ${releaseEvidence.git_branch ?? "unknown"} at ${String(releaseEvidence.git_head ?? "").slice(0, 12)}`,
      targetState: "Production-usable local Agent Workbench with real LLM, coding, Feishu, and GitHub integrations.",
    },
    tickets: tickets.map((ticket) => ticketFromStore(ticket, context)),
    sources: tickets.map(sourceFromTicket),
    knowledgeCards,
    backlogChanges: effectiveBacklogChanges,
    traceSteps: journalEvents.slice(-16).map((event, index) => ({
      id: `trace-${index}`,
      knowledgeCardId: `journal-${index}`,
      backlogChangeId: undefined,
      label: "Ticket Delta",
      summary: event.summary ?? event.message ?? `${event.stage ?? "event"} ${event.status ?? ""}`.trim(),
      artifactPath: ".ariadne/journal/events.jsonl",
      timestamp: eventTime(event.created_at ?? event.timestamp),
    })),
    backlogMutationPreview: backlogMutationPreviewFromPreviews(backlogPreviews, effectiveBacklogChanges, releaseEvidence),
    agents: [
      agentFromRuns("Ariadne Codex", "Codex", githubResults.length + feishuResults.length + backendSmokeEvidence.filter((item) => item.backendName === "codex").length),
      agentFromRuns("Ariadne Reviewer", "Codex", reviews.length),
      agentFromRuns("Ariadne Release Verifier", "fake-codex", releaseEvidence.execution_result_count ?? 0, "idle"),
    ],
    runtimes,
    projectResources: (projectResources.resources ?? []).map(resourceFromProjectResource),
    backendSmokeEvidence,
    releaseEvidence: releaseEvidenceSummary(releaseEvidence),
    skills: [
      {
        name: "ariadne-local-workbench-data-sync",
        description: "Read .ariadne tickets, runtimes, inbox, integrations, and evidence into the frontend.",
        usedBy: ["Frontend", "Release Verifier"],
        updatedAt: eventTime(new Date().toISOString()),
      },
      {
        name: "ariadne-real-integration-evidence",
        description: "Surface Codex, Claude, Feishu, and GitHub dogfood evidence without exposing secrets.",
        usedBy: ["Reviewer", "Verifier"],
        updatedAt: eventTime(releaseEvidence.generated_at),
      },
    ],
    inbox: [...(inboxPayload.items ?? []).slice(0, 12).map((item) => inboxFromStore(item, repairTicketByInboxId)), ...realIntegrationCards],
  };

  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
  console.log(`Wrote ${outputPath}`);
  console.log(`Synced ${data.tickets.length} tickets, ${data.runtimes.length} runtimes, ${data.inbox.length} inbox items.`);
}

await main();
