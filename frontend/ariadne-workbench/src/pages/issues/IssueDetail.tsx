import { ArrowLeft, FileText, MessageSquare, Play, RotateCcw, UserPlus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { addIssueComment, assignIssue, getAssignmentEvents, getIssue, getIssueEvidence, getTeamAgents, retryAssignment, runIssueNow } from "../../shared/api/client";
import type { ApiAssignmentSummary, ApiIssueDetail, ApiIssueEvidenceDetailResponse, ApiIssueEvidenceItem, ApiTeamAgent, AssignmentEvent } from "../../shared/api/types";
import type { ProjectResource, RuntimeInfo } from "../../types";

function idempotencyKey(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Action failed";
}

function display(value: string | number | null | undefined, fallback = "Not recorded") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function statusLabel(status: string | null | undefined) {
  const labels: Record<string, string> = {
    assigned: "Assigned",
    blocked: "Blocked",
    blocked_before_execution: "Blocked before execution",
    done: "Done",
    executed_failed: "Execution failed",
    failed: "Failed",
    in_progress: "Running",
    open: "Backlog",
    planning: "Planning",
    queued: "Queued",
    ready: "Ready",
    reviewing: "Review",
    review_blocked: "Review blocked",
    running: "Running",
    succeeded: "Succeeded",
    unknown: "Unknown",
  };
  return labels[status ?? ""] ?? status ?? "Unknown";
}

function validityLabel(validity: string) {
  const labels: Record<string, string> = {
    available: "Available",
    dirty_before_run: "Dirty before run",
    empty: "Empty",
    missing: "Missing",
    not_run: "Not run",
    produced_by_run: "Produced by run",
    stale: "Stale",
  };
  return labels[validity] ?? validity;
}

function activeAssignment(assignments: ApiAssignmentSummary[]) {
  return assignments.find((assignment) => ["claimed", "running"].includes(assignment.status)) ?? null;
}

function assignableBackend(value: string | null | undefined): "codex" | "claude-code" | null {
  return value === "codex" || value === "claude-code" ? value : null;
}

export function IssueDetail({
  issueKey,
  readOnly,
  selectedRuntime,
  targetProject,
  runtimes,
  onBack,
  onRefreshWorkbench,
}: {
  issueKey: string;
  readOnly: boolean;
  selectedRuntime: string;
  targetProject?: ProjectResource | null;
  runtimes: RuntimeInfo[];
  onBack: () => void;
  onRefreshWorkbench: (preferredIssueRef?: string) => Promise<void>;
}) {
  const [issue, setIssue] = useState<ApiIssueDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [comment, setComment] = useState("");
  const [confirmationToken, setConfirmationToken] = useState("");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [assignmentEvents, setAssignmentEvents] = useState<AssignmentEvent[]>([]);
  const [agents, setAgents] = useState<ApiTeamAgent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [eventsMessage, setEventsMessage] = useState("");
  const [selectedEvidence, setSelectedEvidence] = useState<ApiIssueEvidenceDetailResponse | null>(null);
  const [evidenceMessage, setEvidenceMessage] = useState("");
  const activeRuntime = useMemo(
    () => runtimes.find((runtime) => runtime.backend === selectedRuntime && runtime.canAssign)
      ?? runtimes.find((runtime) => runtime.canAssign)
      ?? runtimes[0],
    [runtimes, selectedRuntime],
  );
  const active = issue ? activeAssignment(issue.assignments) : null;
  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? agents[0] ?? null;

  async function refreshIssue() {
    setLoading(true);
    try {
      const response = await getIssue(issueKey);
      setIssue(response.issue);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshIssue();
  }, [issueKey]);

  useEffect(() => {
    async function loadAgents() {
      try {
        const response = await getTeamAgents();
        setAgents(response.agents);
        setSelectedAgentId((current) => current || response.agents[0]?.id || "");
      } catch {
        setAgents([]);
      }
    }
    void loadAgents();
  }, []);

  useEffect(() => {
    if (!active?.id) {
      setAssignmentEvents([]);
      setEventsMessage("");
      return undefined;
    }

    const assignmentId = active.id;
    let cancelled = false;
    async function refreshEvents() {
      try {
        const response = await getAssignmentEvents(assignmentId);
        if (!cancelled) {
          setAssignmentEvents(response.events);
          setEventsMessage("");
        }
      } catch (error) {
        if (!cancelled) {
          setEventsMessage(errorMessage(error));
        }
      }
    }

    void refreshEvents();
    const interval = globalThis.setInterval(() => {
      void refreshEvents();
    }, 5000);
    return () => {
      cancelled = true;
      globalThis.clearInterval(interval);
    };
  }, [active?.id]);

  async function runAction(label: string, action: () => Promise<string>) {
    if (busyAction) return;
    setBusyAction(label);
    setMessage(`${label}...`);
    try {
      const nextMessage = await action();
      await refreshIssue();
      await onRefreshWorkbench(issueKey);
      setMessage(nextMessage);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function assignCurrentIssue() {
    if (!targetProject?.id) throw new Error("No target project is registered for the current version.");
    if (!selectedAgent) throw new Error("No real AgentDefinition is available. Create an agent in Team first.");
    const backend = assignableBackend(selectedAgent.backend_name) ?? assignableBackend(activeRuntime?.backend);
    if (!backend) throw new Error("Selected agent has no runtime backend.");
    const response = await assignIssue(issueKey, {
      assignee_id: selectedAgent.id,
      assignee_kind: "agent",
      backend_name: backend,
      runtime_profile: "production",
      target_project_id: targetProject.id,
      idempotency_key: idempotencyKey("phase3-assign"),
    });
    if (response.confirmation_token) setConfirmationToken(response.confirmation_token);
    return `Assigned ${response.assignment.ticket_key} to ${response.assignment.agent_name}.`;
  }

  async function runCurrentIssue() {
    const payload = {
      confirmation_token: confirmationToken,
      idempotency_key: idempotencyKey("phase3-run-now"),
    };
    const response = await runIssueNow(issueKey, payload);
    return response.message || "Run now requested.";
  }

  async function retryAssignmentRow(assignment: ApiAssignmentSummary) {
    const response = await retryAssignment(assignment.id, {
      reason: `retry ${assignment.ticket_key} attempt ${assignment.attempt ?? 1} from Workbench issue detail`,
    });
    return response.message || `Retry requested for ${assignment.id}.`;
  }

  async function submitComment() {
    if (!comment.trim()) throw new Error("Comment is empty.");
    await addIssueComment(issueKey, {
      body: comment.trim(),
      idempotency_key: idempotencyKey("phase3-comment"),
    });
    setComment("");
    return "Comment added.";
  }

  async function openEvidence(item: ApiIssueEvidenceItem) {
    setEvidenceMessage(`Opening ${item.label}...`);
    try {
      const response = await getIssueEvidence(issueKey, item.id);
      setSelectedEvidence(response);
      setEvidenceMessage("");
    } catch (error) {
      setEvidenceMessage(errorMessage(error));
    }
  }

  if (loading && !issue) {
    return (
      <section className="page issue-detail-page">
        <button className="outline-button" type="button" onClick={onBack}><ArrowLeft size={16} /> Back to board</button>
        <p className="empty-column">Loading issue detail...</p>
      </section>
    );
  }

  if (!issue) {
    return (
      <section className="page issue-detail-page">
        <button className="outline-button" type="button" onClick={onBack}><ArrowLeft size={16} /> Back to board</button>
        <p className="action-message">{message || `Issue not found: ${issueKey}`}</p>
      </section>
    );
  }

  return (
    <section className="page issue-detail-page" data-testid="issue-detail">
      <header className="issue-detail-header">
        <button className="outline-button" type="button" onClick={onBack}><ArrowLeft size={16} /> Back to board</button>
        <div>
          <span className="issue-key">{issue.key}</span>
          <h1>{issue.title}</h1>
          <p>{issue.body}</p>
        </div>
        <aside>
          <span className={`state ${issue.status}`}>{statusLabel(issue.status)}</span>
          <span>{issue.priority}</span>
        </aside>
      </header>

      <section className="issue-action-bar">
        <label className="compact-selector">
          Agent
          <select disabled={!agents.length || readOnly || busyAction !== null} value={selectedAgentId} onChange={(event) => setSelectedAgentId(event.target.value)}>
            {!agents.length ? <option value="">No real agents</option> : null}
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} · {agent.backend_name ?? "no backend"} · {(agent.skill_ids ?? []).length} skills
              </option>
            ))}
          </select>
        </label>
        <button disabled={readOnly || busyAction !== null || !selectedAgent} type="button" onClick={() => void runAction("Assign", assignCurrentIssue)}>
          <UserPlus size={15} /> Assign
        </button>
        <button disabled={readOnly || busyAction !== null} type="button" onClick={() => void runAction("Run Now", runCurrentIssue)}>
          <Play size={15} /> Run Now
        </button>
        <input
          aria-label="Add issue comment"
          disabled={readOnly || busyAction !== null}
          placeholder="Add a comment..."
          value={comment}
          onChange={(event) => setComment(event.target.value)}
        />
        <button disabled={readOnly || busyAction !== null || !comment.trim()} type="button" onClick={() => void runAction("Comment", submitComment)}>
          <MessageSquare size={15} /> Comment
        </button>
      </section>
      {message ? <p className="action-message">{message}</p> : null}
      {issue.blocked_reason ? (
        <section className="issue-blocker-callout" data-testid="issue-blocker-link">
          <strong>Blocked</strong>
          <p>{issue.blocked_reason}</p>
          <button type="button" onClick={() => { globalThis.location.hash = "#inbox"; }}>Open Inbox</button>
        </section>
      ) : null}

      <div className="issue-detail-grid">
        <main className="issue-detail-main">
          <section className="panel evidence-center" data-testid="issue-evidence-center" id="evidence-center">
            <h2><FileText size={16} /> Evidence Center</h2>
            {issue.evidence_sections.length ? issue.evidence_sections.map((section) => (
              <div className="evidence-section" key={section.category}>
                <h3>{section.label}</h3>
                <div className="evidence-list">
                  {section.items.map((item) => (
                    <article className="evidence-row" key={item.id}>
                      <header>
                        <strong>{item.label}</strong>
                        <span className={`validity-badge ${item.validity}`}>{validityLabel(item.validity)}</span>
                      </header>
                      <p>{item.summary || item.reason || "No summary recorded."}</p>
                      {item.excerpt ? <pre>{item.excerpt}</pre> : null}
                      <footer>
                        <small>{item.ref_type}{item.ref_id ? ` · ${item.ref_id}` : ""}</small>
                        {item.path_or_url ? <code>{item.path_or_url}</code> : null}
                        <button type="button" onClick={() => void openEvidence(item)}>Open evidence</button>
                      </footer>
                      {item.reason ? <small className="evidence-reason">{item.reason}</small> : null}
                    </article>
                  ))}
                </div>
              </div>
            )) : <p className="empty-column">No evidence has been projected for this issue yet.</p>}
            {evidenceMessage ? <p className="action-message">{evidenceMessage}</p> : null}
            {selectedEvidence ? (
              <article className="evidence-viewer" data-testid="issue-evidence-viewer">
                <header>
                  <strong>{selectedEvidence.evidence.label}</strong>
                  <span className={`validity-badge ${selectedEvidence.evidence.validity}`}>{validityLabel(selectedEvidence.evidence.validity)}</span>
                </header>
                <p>{selectedEvidence.evidence.reason || selectedEvidence.evidence.summary}</p>
                <pre>{selectedEvidence.content_excerpt || selectedEvidence.evidence.excerpt || "No readable content recorded."}</pre>
              </article>
            ) : null}
          </section>

          <section className="panel">
            <h2>Execution Results</h2>
            {issue.execution_results.length ? issue.execution_results.map((result) => (
              <article className="execution-result-row" key={result.id}>
                <header className="execution-result-header">
                  <strong>{result.backend_name}</strong>
                  <span className={result.terminal_verdict === "succeeded" ? "verdict-badge pass" : "verdict-badge blocked"}>
                    {statusLabel(result.terminal_verdict)}
                  </span>
                </header>
                <span>exit {display(result.exit_code)}</span>
                <span>tests {display(result.test_exit_code)}</span>
                <div className="file-list">
                  {result.changed_files.length ? result.changed_files.map((file) => <code key={file}>{file}</code>) : <span>No changed files recorded</span>}
                </div>
                {result.preflight_dirty_files?.length ? (
                  <div className="file-list">
                    <span>Preflight dirty files</span>
                    {result.preflight_dirty_files.map((file) => <code key={file}>{file}</code>)}
                  </div>
                ) : null}
                <div className="artifact-link-row">
                  {result.diff_artifact_path ? <span>Diff artifact: {result.diff_artifact_path}</span> : <span>No diff artifact recorded</span>}
                  {result.execution_log_artifact_path ? <span>Execution log: {result.execution_log_artifact_path}</span> : null}
                </div>
              </article>
            )) : <p className="empty-column">No execution results yet.</p>}
          </section>

          <section className="panel" data-testid="issue-assignment-progress">
            <h2>Assignment Progress</h2>
            {active ? <p><strong>{active.id}</strong> · {statusLabel(active.status)} · polling every 5s</p> : <p className="empty-column">No active assignment is currently claimed or running.</p>}
            {eventsMessage ? <p className="action-message">{eventsMessage}</p> : null}
            {assignmentEvents.length ? (
              <ol className="assignment-event-list">
                {assignmentEvents.map((event) => (
                  <li key={event.id}>
                    <span>{event.timestamp}</span>
                    <strong>{event.stage} / {event.event_type}</strong>
                    <p>{event.summary}</p>
                    <small>{event.actor}{event.ref_id ? ` · ${event.ref_id}` : ""}</small>
                  </li>
                ))}
              </ol>
            ) : active ? <p className="empty-column">No progress events recorded yet.</p> : null}
          </section>

          <section className="panel">
            <h2>Timeline</h2>
            <ol className="phase3-timeline">
              {issue.timeline.map((event) => (
                <li key={event.id}>
                  <span>{event.timestamp}</span>
                  <strong>{event.actor}</strong>
                  <em>{event.event_type}</em>
                  <p>{event.summary}</p>
                </li>
              ))}
            </ol>
          </section>

          <section className="panel">
            <h2>Comments</h2>
            {issue.comments.length ? issue.comments.map((item) => (
              <article className="comment-card" key={item.id}>
                <strong>{item.author}</strong>
                <span>{item.created_at}</span>
                <p>{item.body}</p>
              </article>
            )) : <p className="empty-column">No comments yet.</p>}
          </section>
        </main>

        <aside className="issue-detail-sidebar">
          <section className="panel">
            <h2>Summary</h2>
            <div className="property-grid">
              <div><span>Project</span><strong>{display(issue.target_project_label ?? issue.target_project_id)}</strong></div>
              <div><span>Version</span><strong>{display(issue.target_version)}</strong></div>
              <div><span>Assignee</span><strong>{display(issue.assignee, "Unassigned")}</strong></div>
              <div><span>Runtime</span><strong>{activeRuntime?.backend ?? selectedRuntime}</strong></div>
              <div><span>Last run</span><strong>{display(issue.last_run_status)}</strong></div>
              <div>
                <span>Review</span>
                <strong className={`verdict-badge ${issue.review_verdict ?? "unknown"}`}>{display(issue.review_verdict)}</strong>
              </div>
              <div><span>Evidence</span><strong>{issue.evidence_count}</strong></div>
              <div><span>Blocked</span><strong>{display(issue.blocked_reason, "No")}</strong></div>
            </div>
          </section>
          <section className="panel" data-testid="issue-target-context">
            <h2>Target Context</h2>
            <div className="property-grid">
              <div><span>Project ID</span><strong>{display(issue.target_project_id ?? issue.project)}</strong></div>
              <div><span>Version ID</span><strong>{display(issue.project_version_id)}</strong></div>
              <div><span>Build context</span><strong>{display(issue.build_context_id)}</strong></div>
            </div>
            {issue.target_repo_path ?? issue.target_project_path ? (
              <code className="wide-code">{issue.target_repo_path ?? issue.target_project_path}</code>
            ) : null}
          </section>
          <section className="panel" data-testid="issue-source-grounding">
            <h2>Source Grounding</h2>
            <div className="module-row">
              {(issue.source_document_ids ?? []).map((item) => <code key={`doc-${item}`}>{item}</code>)}
              {(issue.source_artifact_ids ?? []).map((item) => <code key={`artifact-${item}`}>{item}</code>)}
              {(issue.source_evidence_refs ?? []).map((item) => <code key={`evidence-${item}`}>{item}</code>)}
              {!issue.source_document_ids?.length && !issue.source_artifact_ids?.length && !issue.source_evidence_refs?.length ? <span>No source refs recorded</span> : null}
            </div>
            {issue.source_claim_trace?.length ? issue.source_claim_trace.slice(0, 4).map((item) => (
              <article className="evidence-row" key={String(item.evidence_id ?? item.locator ?? item.claim)}>
                <strong>{String(item.evidence_id ?? "source evidence")}</strong>
                <p>{String(item.claim ?? "No claim recorded.")}</p>
                <small>{String(item.locator ?? "No locator recorded.")}</small>
              </article>
            )) : null}
          </section>
          <section className="panel" data-testid="issue-compiler-context">
            <h2>Compiler Context</h2>
            <p>{display(issue.codebase_snapshot_status)}</p>
            {issue.codebase_snapshot_artifact_id ? <code>{issue.codebase_snapshot_artifact_id}</code> : null}
            {issue.codebase_snapshot_reason ? <small>{issue.codebase_snapshot_reason}</small> : null}
            <code className="wide-code">{JSON.stringify(issue.compiler_provenance ?? {}, null, 2)}</code>
          </section>
          <section className="panel">
            <h2>Handoff / Route</h2>
            <code className="wide-code">{JSON.stringify(issue.handoff ?? issue.route_decision ?? {}, null, 2)}</code>
          </section>
          <section className="panel">
            <h2>Diff / Tests / Review</h2>
            <p>{display(issue.diff_summary)}</p>
            <p>{display(issue.test_summary)}</p>
            <p>{display(issue.review_summary)}</p>
          </section>
          <section className="panel">
            <h2>Acceptance / Modules</h2>
            {issue.acceptance_criteria_rationale ? <p>{issue.acceptance_criteria_rationale}</p> : null}
            {issue.acceptance_criteria.length ? (
              <ul className="compact-list">
                {issue.acceptance_criteria.map((item) => <li key={item}>{item}</li>)}
              </ul>
            ) : <p className="empty-column">No acceptance criteria recorded.</p>}
            {issue.affected_module_rationale ? <p>{issue.affected_module_rationale}</p> : null}
            <div className="module-row">
              {issue.affected_modules.length ? issue.affected_modules.map((item) => <code key={item}>{item}</code>) : <span>No affected modules recorded</span>}
            </div>
          </section>
          <section className="panel">
            <h2>Links</h2>
            <div className="module-row">
              {issue.source_links.map((item) => <code key={item}>{item}</code>)}
              {issue.next_issue_links.map((item) => <button type="button" key={item} onClick={() => { globalThis.location.hash = `#issues/${encodeURIComponent(item)}`; }}>{item}</button>)}
            </div>
          </section>
          <section className="panel">
            <h2>Assignments</h2>
            {issue.assignments.length ? issue.assignments.map((assignment) => (
              <div className="assignment-row" key={assignment.id}>
                <strong>{assignment.agent_name}</strong>
                <span>{assignment.backend_name}</span>
                <span>{statusLabel(assignment.status)}</span>
                <span>Attempt {assignment.attempt ?? 1}</span>
                {assignment.parent_assignment_id ? <small>Parent {assignment.parent_assignment_id}</small> : null}
                <code>{assignment.id}</code>
                {assignment.retry_allowed ? (
                  <button
                    disabled={readOnly || busyAction !== null}
                    type="button"
                    onClick={() => void runAction(`Retry ${assignment.id}`, () => retryAssignmentRow(assignment))}
                  >
                    <RotateCcw size={13} /> Retry this attempt
                  </button>
                ) : assignment.retry_blocked_reason ? <small>{assignment.retry_blocked_reason}</small> : null}
              </div>
            )) : <p className="empty-column">No assignments yet.</p>}
          </section>
        </aside>
      </div>
    </section>
  );
}
