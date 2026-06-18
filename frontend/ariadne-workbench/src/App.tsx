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
import { loadWorkbenchData, workbenchData } from "./data";
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
      { key: "goal", label: "当前 Goal", icon: Target },
    ],
  },
  {
    label: "工作区",
    items: [
      { key: "knowledge", label: "Knowledge", icon: BookOpenText },
      { key: "issues", label: "Issues", icon: ListTodo },
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
      { key: "skills", label: "Skills", icon: BookOpenText },
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

export function App() {
  const initialRoute = parseHashRoute();
  const [page, setPage] = useState<PageKey>(initialRoute.page ?? "knowledge");
  const [data, setData] = useState<WorkbenchData>(workbenchData);
  const [dataSource, setDataSource] = useState<"local" | "fixture">("fixture");
  const [selectedTicketId, setSelectedTicketId] = useState(
    findTicketByRef(workbenchData.tickets, initialRoute.ticketRef)?.id ?? workbenchData.tickets[0]?.id ?? "",
  );
  const [selectedRuntime, setSelectedRuntime] = useState(workbenchData.runtimes[0]?.backend ?? "fake-codex");
  const selectedTicket = data.tickets.find((ticket) => ticket.id === selectedTicketId) ?? data.tickets[0];

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
    loadWorkbenchData().then((result) => {
      if (!mounted) return;
      setData(result.data);
      setDataSource(result.source);
      const route = parseHashRoute();
      const routeTicket = findTicketByRef(result.data.tickets, route.ticketRef);
      if (route.page) setPage(route.page);
      if (routeTicket) {
        setPage("issues");
        setSelectedTicketId(routeTicket.id);
      } else {
        setSelectedTicketId((current) => result.data.tickets.some((ticket) => ticket.id === current) ? current : result.data.tickets[0]?.id ?? "");
      }
      setSelectedRuntime((current) => result.data.runtimes.some((runtime) => runtime.backend === current) ? current : result.data.runtimes[0]?.backend ?? "fake-codex");
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
          page={page}
          selectedRuntime={selectedRuntime}
          selectedTicket={selectedTicket}
          onNavigate={navigate}
          onRuntimeSelect={setSelectedRuntime}
          onTicketSelect={selectTicket}
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
}: {
  data: WorkbenchData;
  dataSource: "local" | "fixture";
  page: PageKey;
  selectedRuntime: string;
  selectedTicket: AriadneTicket;
  onNavigate: (page: PageKey) => void;
  onRuntimeSelect: (backend: string) => void;
  onTicketSelect: (ticketId: string) => void;
}) {
  if (page === "goal") return <GoalPage data={data} onTicketSelect={onTicketSelect} />;
  if (page === "knowledge") return <KnowledgePage data={data} />;
  if (page === "issues") return <IssuesPage data={data} selectedTicket={selectedTicket} onTicketSelect={onTicketSelect} />;
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

function GoalPage({ data, onTicketSelect }: { data: WorkbenchData; onTicketSelect: (ticketId: string) => void }) {
  const goal = data.goal;
  return (
    <section className="page">
      <PageHeader
        icon={<Target size={17} />}
        title="当前 Goal"
        count={1}
        description="Goal 是输入，ticket 状态机才是执行中心。"
        action={<button className="outline-button" type="button">导入知识</button>}
      />
      <div className="goal-layout">
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
          <h2>由 Goal 派生的当前 tickets</h2>
          <div className="compact-ticket-list">
            {data.tickets.slice(0, 4).map((ticket) => (
              <button key={ticket.id} type="button" onClick={() => onTicketSelect(ticket.id)}>
                <span>{ticket.key}</span>
                <strong>{ticket.title}</strong>
                <em>{ticket.status}</em>
              </button>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function KnowledgePage({ data }: { data: WorkbenchData }) {
  const [selectedSourceId, setSelectedSourceId] = useState(data.sources[0]?.id ?? "");
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

  return (
    <section className="page full-bleed knowledge-page">
      <PageHeader
        icon={<BookOpenText size={17} />}
        title="Knowledge"
        count={data.sources.length}
        action={
          <div className="toolbar">
            <button type="button">Add source</button>
            <button type="button">Ingest folder</button>
            <button type="button">Scan repo</button>
            <button className="primary-action" type="button">Generate tickets</button>
          </div>
        }
      />
      <div className="knowledge-layout">
        <section className="knowledge-column source-column">
          <ColumnHeader title="Source Inbox" meta={`${data.sources.length} inputs`} />
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
                <em className={`source-status ${source.status}`}>{source.status}</em>
                <small>{source.ingestedAt}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="knowledge-column cards-column">
          <ColumnHeader title="Knowledge Cards" meta="Sort: Latest" />
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
                    <small>Source: {selectedSource?.title ?? "unknown"}</small>
                  </div>
                  <span className={card.primary ? "primary-badge" : "secondary-badge"}>{card.primary ? "Primary" : "Secondary"}</span>
                </header>
                <section>
                  <h3>Summary</h3>
                  <p>{card.sourceSummary}</p>
                </section>
                <section>
                  <h3>Evidence</h3>
                  <div className="evidence-list">
                    {card.evidence.map((item) => <code key={item}>{item}</code>)}
                  </div>
                </section>
                <div className="card-meta-grid">
                  <section>
                    <h3>Project relevance</h3>
                    <p>{card.projectRelevance}</p>
                  </section>
                  <section>
                    <h3>Build Decision</h3>
                    <span className={`decision-pill ${card.buildDecision}`}>{card.buildDecision}</span>
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
            )) : <p className="empty-column">No extracted cards for this source.</p>}
          </div>
        </section>

        <section className="knowledge-column changes-column">
          <ColumnHeader title="Backlog Changes" meta="Generated by ticket factory" />
          <BacklogChangeGroup title="Added" kind="added" changes={groupedChanges.added} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="Updated" kind="updated" changes={groupedChanges.updated} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="Deferred" kind="deferred" changes={groupedChanges.deferred} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <BacklogChangeGroup title="Rejected" kind="rejected" changes={groupedChanges.rejected} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <div className="apply-row">
            <button type="button" onClick={() => setPreviewStatus(previewStatus === "applied" ? "preview_only" : "applied")}>
              {previewStatus === "applied" ? "Applied" : "Apply backlog changes"}
            </button>
            <span>{previewStatusLabel(previewStatus)} · Last preview: {data.backlogMutationPreview.lastPreviewAt}</span>
          </div>
        </section>

        <aside className="knowledge-column trace-column">
          <ColumnHeader title="Trace" meta={selectedChange?.ticketKey ?? selectedCard?.title ?? "No selection"} />
          <ol className="trace-list">
            {traceSteps.length ? traceSteps.map((step) => (
              <li key={step.id}>
                <span className="trace-dot" />
                <div>
                  <h3>{step.label}</h3>
                  <p>{step.summary}</p>
                  <code>{step.artifactPath}</code>
                  <small>{step.timestamp}</small>
                </div>
              </li>
            )) : <li className="trace-empty">No trace artifacts for this selection.</li>}
          </ol>
        </aside>
      </div>
      <footer className="mutation-preview">
        <strong>Backlog mutation preview</strong>
        <span className="added">{data.backlogMutationPreview.added} added</span>
        <span className="updated">{data.backlogMutationPreview.updated} updated</span>
        <span className="deferred">{data.backlogMutationPreview.deferred} deferred</span>
        <span className="rejected">{data.backlogMutationPreview.rejected} rejected</span>
        <span className="unsafe">{data.backlogMutationPreview.unsafe} unsafe</span>
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
  kind,
  changes,
  selectedId,
  onSelect,
}: {
  title: string;
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
      )) : <p className="no-changes">No {title.toLowerCase()} tickets.</p>}
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

function sourceTypeLabel(sourceType: WorkbenchData["sources"][number]["sourceType"]) {
  const labels: Record<WorkbenchData["sources"][number]["sourceType"], string> = {
    blog: "Blog",
    paper: "Paper",
    github_readme: "GitHub README",
    repo_note: "Repo note",
    codebase_scan: "Codebase scan",
    review_feedback: "Review feedback",
    execution_result: "Execution result",
    manual_note: "Manual note",
  };
  return labels[sourceType];
}

function previewStatusLabel(status: WorkbenchData["backlogMutationPreview"]["status"]) {
  if (status === "applied") return "Applied";
  if (status === "blocked") return "Blocked: unsafe changes";
  return "Preview only";
}

function IssuesPage({
  data,
  selectedTicket,
  onTicketSelect,
}: {
  data: WorkbenchData;
  selectedTicket: AriadneTicket;
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
        title="Issues"
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
          aria-label="Search issues by key, title, owner, backend, or branch"
          placeholder="Search issue key, title, owner, backend..."
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
        <TicketInspector ticket={selectedTicket} />
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
        <em>{ticket.reviewVerdict}</em>
      </footer>
    </button>
  );
}

function TicketInspector({ ticket }: { ticket: AriadneTicket }) {
  return (
    <aside className="inspector">
      <section className="inspector-header">
        <span className="issue-key">{ticket.key}</span>
        <h2>{ticket.title}</h2>
        <p>{ticket.summary}</p>
      </section>
      <PropertyGrid
        rows={[
          ["状态", ticket.status],
          ["Owner", ticket.owner],
          ["决策", ticket.decision],
          ["来源", ticket.source],
          ["Review", ticket.reviewVerdict],
          ["Memory", ticket.memoryPath ?? "missing"],
          ["Next tickets", ticket.nextTicketsPath ?? "missing"],
        ]}
      />
      <GitHubEvidencePanel ticket={ticket} />
      <BackendSmokePanel smoke={ticket.backendSmoke} />
      <LLMAgentEvidencePanel agents={ticket.llmAgents ?? []} />
      <FeishuEvidencePanel feishu={ticket.feishu} />
      <ReleaseEvidencePanel evidence={ticket.releaseEvidence} />
      <section className="panel nested">
        <h3>Run progress timeline</h3>
        <Timeline items={ticket.progress} />
      </section>
      <section className="panel nested">
        <h3>Acceptance criteria</h3>
        <List items={ticket.acceptance} />
      </section>
      <section className="panel nested">
        <h3>Changed files</h3>
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
        <h3>LLM agents</h3>
        <p className="muted">No upstream LLM agent evidence recorded.</p>
      </section>
    );
  }
  return (
    <section className="panel nested llm-panel">
      <h3>LLM agents</h3>
      <div className="llm-agent-list">
        {agents.map((agent) => (
          <div className="llm-agent-row" key={`${agent.role}-${agent.id}`}>
            <strong>{agent.role}</strong>
            <span className={`state ${agent.succeeded ? "online" : "offline"}`}>
              {agent.succeeded ? "passed" : "blocked"}
            </span>
            <span>{agent.provider}</span>
            <span>{agent.model}</span>
            <span>{agent.totalTokens ? `${agent.totalTokens} tokens` : "usage missing"}</span>
            <p>{agent.summary ?? agent.decision ?? "No summary recorded."}</p>
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
        <p className="muted">No Feishu write evidence recorded.</p>
      </section>
    );
  }
  const status = feishu.ok && !feishu.blocked && !feishu.dryRun ? "passed" : feishu.blocked ? "blocked" : "failed";
  return (
    <section className="panel nested feishu-panel">
      <h3>Feishu</h3>
      <PropertyGrid
        rows={[
          ["Status", status],
          ["Dry run", feishu.dryRun ? "yes" : "no"],
          ["Return code", String(feishu.returncode ?? "missing")],
          ["Document", feishu.documentUrl ?? feishu.documentId ?? "missing"],
          ["Created", feishu.createdAt],
          ["Evidence", feishu.path],
        ]}
      />
      {feishu.documentUrl ? <a href={feishu.documentUrl}>Open Feishu document</a> : null}
      {feishu.operationSummary ? <p>{feishu.operationSummary}</p> : null}
      {feishu.reason ? <p className="muted">{feishu.reason}</p> : null}
    </section>
  );
}

function ReleaseEvidencePanel({ evidence }: { evidence?: ReleaseEvidenceSummary }) {
  if (!evidence) {
    return (
      <section className="panel nested">
        <h3>Release packet</h3>
        <p className="muted">No release evidence packet synced.</p>
      </section>
    );
  }
  const checks = Object.entries(evidence.productReadinessChecks ?? {});
  const readyChecks = checks.filter(([, status]) => status === "ready").length;
  const successEvidenceCount = Object.values(evidence.realSuccessEvidence ?? {}).filter(Boolean).length;
  const failureEvidenceCount = Object.values(evidence.realFailureEvidence ?? {}).filter(Boolean).length;
  return (
    <section className="panel nested release-panel">
      <h3>Release packet</h3>
      <PropertyGrid
        rows={[
          ["Production", evidence.productionAcceptanceStatus ?? "unknown"],
          ["Product readiness", evidence.productReadinessStatus ?? "unknown"],
          ["Run gates", evidence.runGateStatus ?? "unknown"],
          ["Checks", checks.length ? `${readyChecks}/${checks.length} ready` : "missing"],
          ["Real evidence", `${successEvidenceCount} success / ${failureEvidenceCount} failure`],
          ["Executions", `${evidence.executionResultCount ?? 0}`],
          ["Generated", evidence.generatedAt ?? "missing"],
          ["Packet", evidence.packetPath ?? "missing"],
        ]}
      />
      {checks.length ? (
        <div className="check-summary release-checks" aria-label="Product readiness checks">
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
        <h3>Backend smoke</h3>
        <p className="muted">No backend smoke evidence recorded.</p>
      </section>
    );
  }
  return (
    <section className="panel nested smoke-panel">
      <h3>Backend smoke</h3>
      <PropertyGrid
        rows={[
          ["Backend", smoke.backendName],
          ["Succeeded", smoke.succeeded ? "yes" : "no"],
          ["Assignment", smoke.assignmentStatus],
          ["Execution", smoke.executionResultId ?? "missing"],
          ["Exit", String(smoke.exitCode ?? "missing")],
          ["Tests", String(smoke.testExitCode ?? "missing")],
          ["Review", smoke.reviewVerdict ?? "missing"],
          ["Agent runtime", smoke.agentRuntime],
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
        <p className="muted">No GitHub evidence recorded.</p>
      </section>
    );
  }
  const checks = github.checkCounts;
  return (
    <section className="panel nested github-panel">
      <h3>GitHub</h3>
      <PropertyGrid
        rows={[
          ["Operation", github.operation],
          ["Repo", github.repo ?? "missing"],
          ["Issue", github.issueUrl ? `#${github.issueNumber ?? ""}` : "missing"],
          ["PR", github.prUrl ? `#${github.prNumber ?? ""}` : "missing"],
          ["Branch", github.branch ?? "missing"],
          ["Base", github.baseBranch ?? "missing"],
          ["Mergeable", github.mergeable ?? "missing"],
          ["Review", github.reviewDecision ?? "none"],
          ["Checks", github.checksStatus ?? "missing"],
        ]}
      />
      <div className="link-row">
        {github.issueUrl ? <a href={github.issueUrl}>Issue</a> : null}
        {github.prUrl ? <a href={github.prUrl}>Pull request</a> : null}
        {github.commentUrl ? <a href={github.commentUrl}>Comment</a> : null}
      </div>
      {github.commitSha ? <code className="commit-sha">{github.commitSha}</code> : null}
      {checks ? (
        <div className="check-summary">
          <span>pass {checks.pass}</span>
          <span>pending {checks.pending}</span>
          <span>fail {checks.fail}</span>
          <span>total {checks.total}</span>
        </div>
      ) : null}
      <div className="github-history">
        {github.history.map((item) => (
          <span key={`${item.operation}-${item.createdAt}`}>
            {item.operation} · {item.ok ? "ok" : item.blocked ? "blocked" : "failed"}
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
            <span className={`state ${agent.status}`}>{agent.status === "online" ? "在线" : agent.status}</span>
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
  dataSource: "local" | "fixture";
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
        description={dataSource === "local" ? "已接入本地 .ariadne runtime snapshot。" : "使用内置 fixture，运行 sync-local-data 可读取本地状态。"}
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
            <h3>Backend</h3>
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
          <p>{data.runtimes.length} 个运行时 · 当前选择 {currentRuntime?.backend ?? "missing"} · daemon local</p>
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
              <h3>Project resources</h3>
              {data.projectResources.map((resource) => (
                <div className="resource-row" key={resource.id}>
                  <strong>{resource.label}</strong>
                  <span>{resource.resourceType}</span>
                  <code>{resource.localPath ?? "no local path"}</code>
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
        <span>Command</span>
        <strong>{runtime.command ?? runtime.backend}</strong>
      </div>
      <div>
        <span>Path</span>
        <strong>{runtime.commandPath ?? "internal"}</strong>
      </div>
      <div>
        <span>External execution</span>
        <strong>{runtime.externalExecutionEnabled ? "enabled" : "gated / disabled"}</strong>
      </div>
      <div>
        <span>Confirm required</span>
        <strong>{runtime.confirmExecutionRequired ? "yes" : "no"}</strong>
      </div>
      <div>
        <span>Dry run</span>
        <strong>{runtime.supportsDryRun ? "supported" : "not supported"}</strong>
      </div>
      <div>
        <span>Checked</span>
        <strong>{runtime.checkedAt ?? "fixture"}</strong>
      </div>
    </section>
  );
}

function BackendSmokeSummary({ items }: { items: BackendSmokeEvidence[] }) {
  const latest = [...items].sort((a, b) => a.createdAt.localeCompare(b.createdAt)).slice(-6).reverse();
  return (
    <section className="panel resource-panel smoke-summary">
      <h3>Backend smoke evidence</h3>
      {latest.length ? latest.map((item) => (
        <div className="smoke-row" key={item.id}>
          <strong>{item.backendName}</strong>
          <span className={`state ${item.succeeded ? "online" : "offline"}`}>
            {item.succeeded ? "passed" : item.blocked ? "blocked" : "failed"}
          </span>
          <span>{item.ticketKey}</span>
          <span>exit {String(item.exitCode ?? "missing")}</span>
          <span>tests {String(item.testExitCode ?? "missing")}</span>
          <span>{item.reviewVerdict ?? "no review"}</span>
          <code>{item.id}</code>
        </div>
      )) : <p className="muted">No backend smoke evidence synced yet.</p>}
    </section>
  );
}

function SkillsPage({ data }: { data: WorkbenchData }) {
  return (
    <section className="page">
      <PageHeader
        icon={<BookOpenText size={17} />}
        title="Skills"
        count={data.skills.length}
        description="工作区里任何智能体都能使用的指令。"
        action={<button className="outline-button" type="button">新建 skill</button>}
      />
      <div className="search-line">
        <Search size={16} />
        <input placeholder="搜索 skill..." />
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
            <span className={`inbox-kind ${item.kind}`}>{item.kind}</span>
            <strong>{item.title}</strong>
            <p>{item.body}</p>
            <div className="inbox-meta">
              <span>{item.status ?? "open"}</span>
              <span>{item.severity ?? "medium"}</span>
              {item.ticketKey ? <span>{item.ticketKey}</span> : null}
              {item.failureReason ? <span>{item.failureReason}</span> : null}
              {item.repairTicketKey ? <span>repair {item.repairTicketKey}</span> : null}
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
          <span>Runtime</span>
          <select value={selectedRuntime} onChange={(event) => onRuntimeSelect(event.target.value)}>
            {runtimes.map((runtime) => (
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
            <p>它们了解你的工作区：goal、issue、runtime、skill。</p>
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
