import { Bot, BookOpenText, RefreshCw, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { getTeamAgents, getTeamBuildTeams, getTeamSkills } from "../../shared/api/client";
import type { ApiBuildSkill, ApiBuildTeam, ApiTeamAgent } from "../../shared/api/types";

function display(value: string | number | boolean | null | undefined, fallback = "Not recorded") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "Enabled" : "Disabled";
  return String(value);
}

function statusText(enabled?: boolean) {
  return enabled === false ? "Disabled" : "Enabled";
}

export function TeamPage() {
  const [agents, setAgents] = useState<ApiTeamAgent[]>([]);
  const [buildTeams, setBuildTeams] = useState<ApiBuildTeam[]>([]);
  const [skills, setSkills] = useState<ApiBuildSkill[]>([]);
  const [loading, setLoading] = useState(true);
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

  return (
    <section className="page full-bleed team-page">
      <header className="page-header">
        <div className="title-row">
          <Users size={17} />
          <h1>Team</h1>
          <span>{agents.length}</span>
          <p>Agents, build teams, and skills projected from Ariadne runtime state.</p>
        </div>
        <div className="toolbar">
          <button type="button" onClick={() => void refreshTeam()}>
            <RefreshCw size={15} /> Refresh
          </button>
        </div>
      </header>
      {message ? <p className="action-message">{message}</p> : null}
      {loading ? <p className="empty-column">Loading team...</p> : null}
      <div className="control-surface-grid">
        <section className="panel wide">
          <h2><Bot size={16} /> Agents</h2>
          <div className="table-card compact-table">
            <div className="table-row team-agent-row head">
              <span>Agent</span>
              <span>Role</span>
              <span>Backend</span>
              <span>Runtime</span>
              <span>Assignments</span>
              <span>Blocked</span>
              <span>Capabilities</span>
            </div>
            {agents.map((agent) => (
              <div className="table-row team-agent-row" key={agent.id}>
                <strong>{agent.name}<small>{statusText(agent.configuration.enabled)}</small></strong>
                <span>{agent.role}</span>
                <span>{display(agent.backend_name)}</span>
                <span>{agent.runtime_compatibility}</span>
                <span>{agent.active_assignment_count}</span>
                <span>{agent.blocked_count}</span>
                <span>{(agent.configuration.capabilities ?? []).join(", ") || "Not recorded"}</span>
              </div>
            ))}
            {!agents.length ? <p className="empty-column">No agents projected.</p> : null}
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
                  {team.skill_refs.length ? team.skill_refs.map((skill) => <span key={skill}>{skill}</span>) : <span>No skills</span>}
                </div>
              </article>
            ))}
            {!buildTeams.length ? <p className="empty-column">No build teams projected.</p> : null}
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
            {!skills.length ? <p className="empty-column">No skills projected.</p> : null}
          </div>
        </section>
      </div>
    </section>
  );
}
