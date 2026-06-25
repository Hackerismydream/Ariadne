import { Bot, BookOpenText, Plus, RefreshCw, Save, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  createTeamAgent,
  getTeamAgent,
  getTeamAgentActivity,
  getTeamAgentEnvironment,
  getTeamAgentInstructions,
  getTeamAgentRuns,
  getTeamAgents,
  getTeamAgentSkills,
  getTeamAgentTasks,
  getTeamBuildTeams,
  getTeamSkills,
  updateTeamAgent,
} from "../../shared/api/client";
import type {
  ApiAgentActivityItem,
  ApiAgentDetail,
  ApiAgentRunItem,
  ApiAgentTaskItem,
  ApiBuildSkill,
  ApiBuildTeam,
  ApiTeamAgent,
  CreateAgentRequest,
} from "../../shared/api/types";

const emptyLabel = "没有真实数据";

function display(value: string | number | boolean | null | undefined, fallback = "Not recorded") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "Enabled" : "Disabled";
  return String(value);
}

function statusText(status?: string) {
  if (status === "archived") return "Archived";
  if (status === "paused") return "Paused";
  return "Active";
}

function agentHash(agentId: string) {
  return `#team/agents/${encodeURIComponent(agentId)}`;
}

export function TeamPage({ agentRef }: { agentRef?: string }) {
  const [agents, setAgents] = useState<ApiTeamAgent[]>([]);
  const [buildTeams, setBuildTeams] = useState<ApiBuildTeam[]>([]);
  const [skills, setSkills] = useState<ApiBuildSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [message, setMessage] = useState("");

  async function refreshTeam() {
    setLoading(true);
    setMessage("");
    try {
      const [agentResponse, teamResponse, skillResponse] = await Promise.all([
        getTeamAgents(),
        getTeamBuildTeams(),
        getTeamSkills(),
      ]);
      setAgents(agentResponse.agents);
      setBuildTeams(teamResponse.build_teams);
      setSkills(skillResponse.skills);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to load team.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshTeam();
  }, []);

  if (agentRef) {
    return <AgentDetailPage agentId={agentRef} allSkills={skills} onBack={() => { globalThis.location.hash = "#team"; }} />;
  }

  return (
    <section className="page full-bleed team-page">
      <header className="page-header">
        <div className="title-row">
          <Users size={17} />
          <h1>Team</h1>
          <span>{agents.length}</span>
          <p>Real local agents, build teams, and skills projected from Ariadne store.</p>
        </div>
        <div className="toolbar">
          <button type="button" onClick={() => setShowCreate((value) => !value)}>
            <Plus size={15} /> New Agent
          </button>
          <button type="button" onClick={() => void refreshTeam()}>
            <RefreshCw size={15} /> Refresh
          </button>
        </div>
      </header>
      {message ? <p className="action-message">{message}</p> : null}
      {showCreate ? <CreateAgentForm skills={skills} onCreated={() => void refreshTeam()} /> : null}
      {loading ? <p className="empty-column">Loading team...</p> : null}
      <div className="control-surface-grid">
        <section className="panel wide">
          <h2><Bot size={16} /> Agents</h2>
          <div className="table-card compact-table">
            <div className="table-row team-agent-row head">
              <span>Agent</span>
              <span>Status</span>
              <span>Backend</span>
              <span>Model</span>
              <span>Assignments</span>
              <span>Blocked</span>
              <span>Skills</span>
            </div>
            {agents.map((agent) => (
              <button
                className="table-row team-agent-row"
                key={agent.id}
                type="button"
                onClick={() => { globalThis.location.hash = agentHash(agent.id); }}
              >
                <strong>{agent.name}<small>{agent.description || "No description"}</small></strong>
                <span>{statusText(agent.status)}</span>
                <span>{display(agent.backend_name)}</span>
                <span>{display(agent.runtime_profile?.model)}</span>
                <span>{agent.active_assignment_count}</span>
                <span>{agent.blocked_count}</span>
                <span>{agent.skill_ids.join(", ") || emptyLabel}</span>
              </button>
            ))}
            {!agents.length && !loading ? <p className="empty-column">{emptyLabel}</p> : null}
          </div>
        </section>

        <section className="panel">
          <h2><Users size={16} /> Build Teams</h2>
          <div className="card-list">
            {buildTeams.map((team) => (
              <article className="control-card" key={team.id}>
                <header>
                  <strong>{team.name}</strong>
                  <span>{display(team.enabled)}</span>
                </header>
                <p>{team.description || "No description."}</p>
                <dl>
                  <div><dt>Lead</dt><dd>{team.lead_agent_id}</dd></div>
                  <div><dt>Implementer</dt><dd>{team.implementer_agent_id}</dd></div>
                  <div><dt>Reviewer</dt><dd>{team.reviewer_agent_id}</dd></div>
                  <div><dt>Backend</dt><dd>{team.default_backend_name}</dd></div>
                </dl>
                <div className="tag-row">
                  {team.skill_refs.length ? team.skill_refs.map((skill) => <span key={skill}>{skill}</span>) : <span>{emptyLabel}</span>}
                </div>
              </article>
            ))}
            {!buildTeams.length && !loading ? <p className="empty-column">{emptyLabel}</p> : null}
          </div>
        </section>

        <section className="panel">
          <h2><BookOpenText size={16} /> Skills</h2>
          <div className="card-list">
            {skills.map((skill) => (
              <article className="control-card" key={skill.id}>
                <header>
                  <strong>{skill.name}</strong>
                  <span>{skill.updated_at}</span>
                </header>
                <p>{skill.description}</p>
                <div className="tag-row">
                  {skill.applies_to_agent_roles.length
                    ? skill.applies_to_agent_roles.map((role) => <span key={role}>{role}</span>)
                    : <span>All roles</span>}
                </div>
              </article>
            ))}
            {!skills.length && !loading ? <p className="empty-column">{emptyLabel}</p> : null}
          </div>
        </section>
      </div>
    </section>
  );
}

function CreateAgentForm({ skills, onCreated }: { skills: ApiBuildSkill[]; onCreated: () => void }) {
  const [form, setForm] = useState<CreateAgentRequest>({
    name: "",
    description: "",
    backend: "codex",
    instructions: "",
    skill_ids: [],
    environment_keys: [],
    max_concurrent_assignments: 1,
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function submit() {
    setSaving(true);
    setMessage("");
    try {
      const response = await createTeamAgent(form);
      setMessage(`Created ${response.agent.name}`);
      setForm({ name: "", description: "", backend: "codex", instructions: "", skill_ids: [], environment_keys: [], max_concurrent_assignments: 1 });
      onCreated();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Create failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <h2><Plus size={16} /> New Agent</h2>
      <div className="form-grid">
        <label>
          Name
          <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        </label>
        <label>
          Backend
          <select value={form.backend} onChange={(event) => setForm({ ...form, backend: event.target.value as "codex" | "claude-code" })}>
            <option value="codex">Codex</option>
            <option value="claude-code">Claude Code</option>
          </select>
        </label>
        <label>
          Model
          <input value={form.model ?? ""} onChange={(event) => setForm({ ...form, model: event.target.value || null })} />
        </label>
        <label>
          Working directory
          <input value={form.working_directory ?? ""} onChange={(event) => setForm({ ...form, working_directory: event.target.value || null })} />
        </label>
      </div>
      <label className="full-width-field">
        Description
        <textarea value={form.description ?? ""} onChange={(event) => setForm({ ...form, description: event.target.value })} />
      </label>
      <label className="full-width-field">
        Instructions
        <textarea value={form.instructions ?? ""} onChange={(event) => setForm({ ...form, instructions: event.target.value })} />
      </label>
      <div className="tag-row">
        {skills.map((skill) => {
          const selected = form.skill_ids?.includes(skill.id) ?? false;
          return (
            <button
              className={selected ? "chip selected" : "chip"}
              key={skill.id}
              type="button"
              onClick={() => {
                const current = new Set(form.skill_ids ?? []);
                if (selected) current.delete(skill.id);
                else current.add(skill.id);
                setForm({ ...form, skill_ids: [...current] });
              }}
            >
              {skill.name}
            </button>
          );
        })}
        {!skills.length ? <span>{emptyLabel}</span> : null}
      </div>
      <div className="toolbar">
        <button type="button" disabled={saving || !form.name.trim()} onClick={() => void submit()}>
          <Save size={15} /> Create
        </button>
      </div>
      {message ? <p className="action-message">{message}</p> : null}
    </section>
  );
}

function AgentDetailPage({
  agentId,
  allSkills,
  onBack,
}: {
  agentId: string;
  allSkills: ApiBuildSkill[];
  onBack: () => void;
}) {
  const [agent, setAgent] = useState<ApiAgentDetail | null>(null);
  const [activity, setActivity] = useState<ApiAgentActivityItem[]>([]);
  const [tasks, setTasks] = useState<ApiAgentTaskItem[]>([]);
  const [runs, setRuns] = useState<ApiAgentRunItem[]>([]);
  const [skills, setSkills] = useState<ApiBuildSkill[]>([]);
  const [environmentKeys, setEnvironmentKeys] = useState<string[]>([]);
  const [instructions, setInstructions] = useState("");
  const [tab, setTab] = useState<"activity" | "tasks" | "instructions" | "skills" | "environment" | "runs">("activity");
  const [message, setMessage] = useState("");

  async function refreshAgent() {
    setMessage("");
    try {
      const [detail, activityResponse, taskResponse, runResponse, skillResponse, instructionResponse, environmentResponse] = await Promise.all([
        getTeamAgent(agentId),
        getTeamAgentActivity(agentId),
        getTeamAgentTasks(agentId),
        getTeamAgentRuns(agentId),
        getTeamAgentSkills(agentId),
        getTeamAgentInstructions(agentId),
        getTeamAgentEnvironment(agentId),
      ]);
      setAgent(detail.agent);
      setActivity(activityResponse.activity);
      setTasks(taskResponse.tasks);
      setRuns(runResponse.runs);
      setSkills(skillResponse.skills);
      setInstructions(instructionResponse.instructions);
      setEnvironmentKeys(environmentResponse.environment_keys);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to load agent.");
    }
  }

  async function saveInstructions() {
    try {
      const response = await updateTeamAgent(agentId, { instructions });
      setAgent(response.agent);
      setMessage("Instructions saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Save failed.");
    }
  }

  useEffect(() => {
    void refreshAgent();
  }, [agentId]);

  const attachedSkillIds = useMemo(() => new Set(agent?.skill_ids ?? []), [agent]);

  return (
    <section className="page full-bleed team-page">
      <header className="page-header">
        <div className="title-row">
          <Bot size={17} />
          <h1>{agent?.name ?? agentId}</h1>
          <span>{agent ? statusText(agent.status) : "Loading"}</span>
          <p>{agent?.description || "Agent detail fact center."}</p>
        </div>
        <div className="toolbar">
          <button type="button" onClick={onBack}>Back to Team</button>
          <button type="button" onClick={() => void refreshAgent()}><RefreshCw size={15} /> Refresh</button>
        </div>
      </header>
      {message ? <p className="action-message">{message}</p> : null}
      {agent ? (
        <div className="control-surface-grid">
          <section className="panel">
            <h2><Bot size={16} /> Profile</h2>
            <dl>
              <div><dt>Backend</dt><dd>{display(agent.backend_name)}</dd></div>
              <div><dt>Model</dt><dd>{display(agent.runtime_profile?.model)}</dd></div>
              <div><dt>Working directory</dt><dd>{display(agent.runtime_profile?.working_directory)}</dd></div>
              <div><dt>Visibility</dt><dd>{agent.visibility?.visible === false ? "Private" : "Visible"}</dd></div>
              <div><dt>Assignments</dt><dd>{agent.active_assignment_count}</dd></div>
              <div><dt>Blocked</dt><dd>{agent.blocked_count}</dd></div>
            </dl>
          </section>
          <section className="panel wide">
            <div className="segmented-tabs">
              {["activity", "tasks", "instructions", "skills", "environment", "runs"].map((item) => (
                <button className={tab === item ? "active" : ""} key={item} type="button" onClick={() => setTab(item as typeof tab)}>
                  {item}
                </button>
              ))}
            </div>
            {tab === "activity" ? <ActivityTab items={activity} tasks={tasks} runs={runs} /> : null}
            {tab === "tasks" ? <TasksTab items={tasks} /> : null}
            {tab === "instructions" ? (
              <div>
                <label className="full-width-field">
                  Instructions
                  <textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} />
                </label>
                <button type="button" onClick={() => void saveInstructions()}><Save size={15} /> Save Instructions</button>
              </div>
            ) : null}
            {tab === "skills" ? (
              <div className="card-list">
                {skills.map((skill) => <SkillCard key={skill.id} skill={skill} />)}
                {!skills.length ? (
                  <p className="empty-column">
                    {allSkills.length ? `Attached skills: ${[...attachedSkillIds].join(", ") || emptyLabel}` : emptyLabel}
                  </p>
                ) : null}
              </div>
            ) : null}
            {tab === "environment" ? (
              <div className="tag-row">
                {environmentKeys.map((key) => <span key={key}>{key}</span>)}
                {!environmentKeys.length ? <span>{emptyLabel}</span> : null}
              </div>
            ) : null}
            {tab === "runs" ? <RunsTab items={runs} /> : null}
          </section>
        </div>
      ) : (
        <p className="empty-column">{message || "Loading agent..."}</p>
      )}
    </section>
  );
}

function ActivityTab({
  items,
  tasks,
  runs,
}: {
  items: ApiAgentActivityItem[];
  tasks: ApiAgentTaskItem[];
  runs: ApiAgentRunItem[];
}) {
  const currentTasks = tasks.filter((item) => item.current || ["queued", "claimed", "running"].includes(item.status));
  const recentTasks = tasks.filter((item) => ["done", "blocked", "failed", "cancelled"].includes(item.status)).slice(0, 5);
  const terminalRuns = runs.filter((item) => item.lifecycle_state === "terminal" || ["succeeded", "failed", "blocked", "cancelled"].includes(item.status));
  const failedRuns = terminalRuns.filter((item) => ["failed", "blocked", "cancelled"].includes(item.status));
  const successPct = terminalRuns.length ? Math.round(((terminalRuns.length - failedRuns.length) / terminalRuns.length) * 100) : null;

  return (
    <div className="agent-activity-layout">
      <section className="control-card">
        <header>
          <strong>Now</strong>
          <span>{currentTasks.length ? `${currentTasks.length} active` : "idle"}</span>
        </header>
        {currentTasks.length ? currentTasks.map((task) => (
          <div className="activity-task-row" key={task.task_id}>
            <strong>{task.ticket_key}</strong>
            <span>{task.status}</span>
            <small>{task.task_id}</small>
          </div>
        )) : <p>{emptyLabel}</p>}
      </section>

      <section className="control-card">
        <header>
          <strong>Last 30 days</strong>
          <span>{terminalRuns.length} runs</span>
        </header>
        {terminalRuns.length ? (
          <div className="activity-metrics">
            <strong>{successPct}% success</strong>
            <span>{failedRuns.length} failed or blocked</span>
          </div>
        ) : <p>{emptyLabel}</p>}
      </section>

      <section className="control-card">
        <header>
          <strong>Recent work</strong>
          <span>{recentTasks.length}</span>
        </header>
        {recentTasks.length ? recentTasks.map((task) => (
          <div className="activity-task-row" key={task.task_id}>
            <strong>{task.ticket_key}</strong>
            <span>{task.status}</span>
            {task.completed_at ? <small>{task.completed_at}</small> : null}
          </div>
        )) : <p>{emptyLabel}</p>}
      </section>

      <section className="control-card wide-activity-card">
        <header>
          <strong>Activity stream</strong>
          <span>{items.length}</span>
        </header>
      {items.map((item) => (
        <article className="activity-event-card" key={item.id}>
          <header>
            <strong>{item.stage}: {item.event_type}</strong>
            <span>{item.timestamp}</span>
          </header>
          <p>{item.summary}</p>
          <div className="tag-row">
            {item.ticket_key ? <span>{item.ticket_key}</span> : null}
            {item.assignment_id ? <span>{item.assignment_id}</span> : null}
          </div>
        </article>
      ))}
      {!items.length ? <p className="empty-column">{emptyLabel}</p> : null}
      </section>
    </div>
  );
}

function TasksTab({ items }: { items: ApiAgentTaskItem[] }) {
  return (
    <div className="card-list">
      {items.map((item) => (
        <article className="control-card" key={item.task_id}>
          <header>
            <strong>{item.ticket_key}</strong>
            <span>{item.status}</span>
          </header>
          <p>{item.assignment.agent_name} · {item.assignment.backend_name ?? "backend not recorded"}</p>
          <div className="tag-row">
            <span>{item.task_id}</span>
            <span>Attempt {item.attempt_number}</span>
            <span>Retry {item.retry_count}</span>
            {item.current ? <span>Current</span> : null}
            {item.blocker_id ? <button type="button" onClick={() => { globalThis.location.hash = "#inbox"; }}>Inbox {item.blocker_id}</button> : null}
          </div>
          {item.blocker_reason ? <p>{item.blocker_reason}</p> : null}
          <div className="tag-row">
            {item.claimed_at ? <span>Claimed {item.claimed_at}</span> : null}
            {item.started_at ? <span>Started {item.started_at}</span> : null}
            {item.completed_at ? <span>Completed {item.completed_at}</span> : null}
          </div>
        </article>
      ))}
      {!items.length ? <p className="empty-column">{emptyLabel}</p> : null}
    </div>
  );
}

function RunsTab({ items }: { items: ApiAgentRunItem[] }) {
  return (
    <div className="card-list">
      {items.map((item) => (
        <article className="control-card" key={item.id}>
          <header>
            <strong>{item.ticket_key ?? item.ticket_id}</strong>
            <span>{item.status}</span>
          </header>
          <p>{item.backend_name ?? "backend not recorded"} · {item.lifecycle_state}</p>
          <div className="tag-row">
            {item.assignment_id ? <span>{item.assignment_id}</span> : null}
            {item.failure_reason ? <span>{item.failure_reason}</span> : null}
          </div>
        </article>
      ))}
      {!items.length ? <p className="empty-column">{emptyLabel}</p> : null}
    </div>
  );
}

function SkillCard({ skill }: { skill: ApiBuildSkill }) {
  return (
    <article className="control-card">
      <header>
        <strong>{skill.name}</strong>
        <span>{skill.id}</span>
      </header>
      <p>{skill.description}</p>
    </article>
  );
}
