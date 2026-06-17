import {
  Bot,
  BookOpenText,
  FolderKanban,
  Inbox,
  ListTodo,
  Monitor,
  Plus,
  Search,
  Settings,
  Sparkles,
  Target,
  Users,
  Zap,
} from "lucide-react";
import { useMemo, useState } from "react";
import { workbenchData } from "./data";
import type { AriadneTicket, TicketStatus, TimelineEvent } from "./types";

type PageKey = "goal" | "issues" | "agents" | "runtimes" | "skills" | "inbox";

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
  const [page, setPage] = useState<PageKey>("goal");
  const [selectedTicketId, setSelectedTicketId] = useState(workbenchData.tickets[0]?.id ?? "");
  const selectedTicket = workbenchData.tickets.find((ticket) => ticket.id === selectedTicketId) ?? workbenchData.tickets[0];

  return (
    <div className="app-shell">
      <Sidebar page={page} onNavigate={setPage} />
      <main className="main">
        <PageFrame page={page} selectedTicket={selectedTicket} onTicketSelect={setSelectedTicketId} />
      </main>
      <AgentDock compact={page === "issues"} />
    </div>
  );
}

function Sidebar({
  page,
  onNavigate,
}: {
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
            const enabled = ["goal", "issues", "agents", "runtimes", "skills", "inbox"].includes(item.key);
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
                {item.key === "inbox" ? <em>{workbenchData.inbox.length}</em> : null}
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
  page,
  selectedTicket,
  onTicketSelect,
}: {
  page: PageKey;
  selectedTicket: AriadneTicket;
  onTicketSelect: (ticketId: string) => void;
}) {
  if (page === "goal") return <GoalPage onTicketSelect={onTicketSelect} />;
  if (page === "issues") return <IssuesPage selectedTicket={selectedTicket} onTicketSelect={onTicketSelect} />;
  if (page === "agents") return <AgentsPage />;
  if (page === "runtimes") return <RuntimesPage />;
  if (page === "skills") return <SkillsPage />;
  return <InboxPage onTicketSelect={onTicketSelect} />;
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

function GoalPage({ onTicketSelect }: { onTicketSelect: (ticketId: string) => void }) {
  const goal = workbenchData.goal;
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
            {workbenchData.tickets.slice(0, 4).map((ticket) => (
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

function IssuesPage({
  selectedTicket,
  onTicketSelect,
}: {
  selectedTicket: AriadneTicket;
  onTicketSelect: (ticketId: string) => void;
}) {
  const grouped = useMemo(() => {
    return statusColumns.map((column) => ({
      ...column,
      tickets: workbenchData.tickets.filter((ticket) => ticket.status === column.status),
    }));
  }, []);

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

function AgentsPage() {
  return (
    <section className="page">
      <PageHeader
        icon={<Bot size={17} />}
        title="智能体"
        count={workbenchData.agents.length}
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
        {workbenchData.agents.map((agent) => (
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

function RuntimesPage() {
  return (
    <section className="page full-bleed">
      <PageHeader
        icon={<Monitor size={17} />}
        title="运行时"
        count={workbenchData.runtimes.length}
        action={<button className="outline-button" type="button">添加电脑</button>}
      />
      <div className="runtime-layout">
        <aside className="machine-list">
          <input placeholder="搜索机器..." />
          <button className="machine active" type="button">
            <Monitor size={18} />
            <strong>local-mac</strong>
            <span>{workbenchData.runtimes.length} 个运行时</span>
          </button>
        </aside>
        <section className="runtime-detail">
          <h2>local-mac <span>在线</span></h2>
          <p>{workbenchData.runtimes.length} 个运行时 · 全部空闲 · daemon local</p>
          <div className="runtime-table">
            {workbenchData.runtimes.map((runtime) => (
              <div className="runtime-row" key={runtime.backend}>
                <strong>{runtime.backend}</strong>
                <span className={`state ${runtime.status}`}>在线</span>
                <span>{runtime.version}</span>
                <span>{runtime.cost7d}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function SkillsPage() {
  return (
    <section className="page">
      <PageHeader
        icon={<BookOpenText size={17} />}
        title="Skills"
        count={workbenchData.skills.length}
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
        {workbenchData.skills.map((skill) => (
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

function InboxPage({ onTicketSelect }: { onTicketSelect: (ticketId: string) => void }) {
  return (
    <section className="page">
      <PageHeader icon={<Inbox size={17} />} title="收件箱" count={workbenchData.inbox.length} />
      <div className="inbox-list">
        {workbenchData.inbox.map((item, index) => (
          <button key={item.id} type="button" onClick={() => onTicketSelect(workbenchData.tickets[index % workbenchData.tickets.length].id)}>
            <span className={`inbox-kind ${item.kind}`}>{item.kind}</span>
            <strong>{item.title}</strong>
            <p>{item.body}</p>
            <em>{item.time}</em>
          </button>
        ))}
      </div>
    </section>
  );
}

function AgentDock({ compact }: { compact: boolean }) {
  if (compact) {
    return (
      <button className="agent-dock compact" type="button">
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
        <span>⌟</span>
        <span>−</span>
      </header>
      <div className="agent-empty">
        <h3>和你的智能体对话</h3>
        <p>它们了解你的工作区：goal、issue、runtime、skill。</p>
      </div>
      <footer>
        <input placeholder="输入消息..." />
        <button type="button">↑</button>
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
