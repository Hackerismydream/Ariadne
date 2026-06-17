import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { dirname, extname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, "..");
const repoRoot = resolve(frontendRoot, "..", "..");
const ariadneRoot = resolve(repoRoot, ".ariadne");

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

function inboxFromStore(item) {
  const kindBySource = {
    review: "review",
    assignment: "blocker",
    execution: "blocker",
    feishu: "memory",
    github: "memory",
    memory: "memory",
  };
  return {
    id: item.id,
    ticketId: item.ticket_id,
    title: item.title,
    body: item.summary,
    time: eventTime(item.created_at),
    kind: kindBySource[item.source_type] ?? "goal",
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
  const inboxPayload = await readJson(resolve(ariadneRoot, "inbox", "items.json"), { items: [] });
  const githubResults = await readNestedJsonFiles(resolve(ariadneRoot, "integrations", "github"));
  const feishuResults = await readNestedJsonFiles(resolve(ariadneRoot, "integrations", "feishu"));
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
    changedFiles,
    comments,
    journalEvents,
    githubResults,
    memoryPaths,
    nextTicketsPath,
    reviews,
  };
  const runtimes = (runtimeSnapshot.capabilities ?? releaseEvidence.runtime_capabilities ?? []).map(runtimeFromCapability);
  const realIntegrationCards = [
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
    backlogChanges,
    traceSteps: journalEvents.slice(-16).map((event, index) => ({
      id: `trace-${index}`,
      knowledgeCardId: `journal-${index}`,
      backlogChangeId: undefined,
      label: "Ticket Delta",
      summary: event.summary ?? event.message ?? `${event.stage ?? "event"} ${event.status ?? ""}`.trim(),
      artifactPath: ".ariadne/journal/events.jsonl",
      timestamp: eventTime(event.created_at ?? event.timestamp),
    })),
    backlogMutationPreview: {
      status: "applied",
      added: backlogChanges.length,
      updated: 0,
      deferred: 0,
      rejected: 0,
      unsafe: releaseEvidence.store_invariants_ok === false ? 1 : 0,
      lastPreviewAt: eventTime(releaseEvidence.generated_at),
    },
    agents: [
      agentFromRuns("Ariadne Codex", "Codex", githubResults.length + feishuResults.length),
      agentFromRuns("Ariadne Reviewer", "Codex", reviews.length),
      agentFromRuns("Ariadne Release Verifier", "fake-codex", releaseEvidence.execution_result_count ?? 0, "idle"),
    ],
    runtimes,
    projectResources: (projectResources.resources ?? []).map(resourceFromProjectResource),
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
    inbox: [...(inboxPayload.items ?? []).slice(0, 12).map(inboxFromStore), ...realIntegrationCards],
  };

  const outputPath = resolve(frontendRoot, "public", "web_data", "workbench.json");
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
  console.log(`Wrote ${outputPath}`);
  console.log(`Synced ${data.tickets.length} tickets, ${data.runtimes.length} runtimes, ${data.inbox.length} inbox items.`);
}

await main();
