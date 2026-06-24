import { Monitor, Play, RefreshCw, Square } from "lucide-react";
import { useEffect, useState } from "react";
import {
  getAssignmentEvents,
  getDaemonStatus,
  getRunsAssignments,
  getRunsRuntimes,
  startDaemon,
  stopDaemon,
} from "../../shared/api/client";
import type { ApiAssignmentSummary, ApiDaemonStatus, ApiRunsRuntime, AssignmentEvent } from "../../shared/api/types";

function display(value: string | number | boolean | null | undefined, fallback = "Not recorded") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function statusLabel(status: string | null | undefined) {
  const labels: Record<string, string> = {
    assigned: "Assigned",
    blocked: "Blocked",
    claimed: "Claimed",
    done: "Done",
    failed: "Failed",
    idle: "Idle",
    queued: "Queued",
    ready: "Ready",
    running: "Running",
    stopped: "Stopped",
  };
  return labels[status ?? ""] ?? status ?? "Unknown";
}

export function RunsPage() {
  const [runtimes, setRuntimes] = useState<ApiRunsRuntime[]>([]);
  const [assignments, setAssignments] = useState<ApiAssignmentSummary[]>([]);
  const [daemon, setDaemon] = useState<ApiDaemonStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [progressEvents, setProgressEvents] = useState<AssignmentEvent[]>([]);
  const [progressMessage, setProgressMessage] = useState("");
  const activeAssignmentId = assignments.find((assignment) => ["claimed", "running"].includes(assignment.status))?.id
    ?? null;
  const claimableAssignment = assignments.find((assignment) => assignment.status === "ready_to_claim") ?? null;

  async function refreshRuns() {
    setLoading(true);
    setMessage("");
    try {
      const [runtimeResponse, assignmentResponse, daemonResponse] = await Promise.all([
        getRunsRuntimes(),
        getRunsAssignments(),
        getDaemonStatus(),
      ]);
      setRuntimes(runtimeResponse.runtimes);
      setAssignments(assignmentResponse.assignments);
      setDaemon(daemonResponse);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to load runs.");
    } finally {
      setLoading(false);
    }
  }

  async function runDaemonAction(label: string, action: () => Promise<unknown>) {
    if (busyAction) return;
    setBusyAction(label);
    setMessage(`${label}...`);
    try {
      await action();
      await refreshRuns();
      setMessage(`${label} requested.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : `${label} failed.`);
    } finally {
      setBusyAction(null);
    }
  }

  function startScopedDaemon() {
    const assignment = claimableAssignment;
    return startDaemon({
      external_execution_authorized: true,
      allowed_assignment_id: assignment?.id ?? null,
      target_project_id: assignment?.target_project_id ?? null,
      allowed_backends: assignment?.backend_name ? [assignment.backend_name] : [],
      scope_mode: assignment ? "assignment" : "project",
    });
  }

  useEffect(() => {
    void refreshRuns();
  }, []);

  useEffect(() => {
    if (!activeAssignmentId) {
      setProgressEvents([]);
      setProgressMessage("");
      return undefined;
    }

    const assignmentId = activeAssignmentId;
    let cancelled = false;
    async function refreshProgress() {
      try {
        const response = await getAssignmentEvents(assignmentId);
        if (!cancelled) {
          setProgressEvents(response.events);
          setProgressMessage("");
        }
      } catch (error) {
        if (!cancelled) {
          setProgressMessage(error instanceof Error ? error.message : "Failed to load assignment progress.");
        }
      }
    }

    void refreshProgress();
    const interval = globalThis.setInterval(() => {
      void refreshProgress();
    }, 5000);
    return () => {
      cancelled = true;
      globalThis.clearInterval(interval);
    };
  }, [activeAssignmentId]);

  return (
    <section className="page full-bleed runs-page">
      <header className="page-header">
        <div className="title-row">
          <Monitor size={17} />
          <h1>Runs</h1>
          <span>{assignments.length}</span>
          <p>Runtime capability, assignment queue, and local daemon controls.</p>
        </div>
        <div className="toolbar">
          <button type="button" onClick={() => void refreshRuns()}>
            <RefreshCw size={15} /> Refresh
          </button>
          <button
            className="primary-action"
            disabled={busyAction !== null}
            type="button"
            onClick={() => void runDaemonAction("Start Daemon", startScopedDaemon)}
          >
            <Play size={15} /> Start Daemon{claimableAssignment ? ` · ${claimableAssignment.ticket_key}` : ""}
          </button>
          <button
            disabled={busyAction !== null}
            type="button"
            onClick={() => void runDaemonAction("Stop Daemon", stopDaemon)}
          >
            <Square size={15} /> Stop Daemon
          </button>
        </div>
      </header>
      {message ? <p className="action-message">{message}</p> : null}
      {loading ? <p className="empty-column">Loading runs...</p> : null}

      <section className="runtime-capability daemon-runtime-status runs-daemon-strip">
        <div>
          <span>Status</span>
          <strong>{statusLabel(daemon?.status)}</strong>
        </div>
        <div>
          <span>Background</span>
          <strong>{daemon?.background_running ? "Running" : "Stopped"}</strong>
        </div>
        <div>
          <span>Authorized</span>
          <strong>{daemon?.external_execution_authorized ? "Codex/Claude allowed" : "Not authorized"}</strong>
        </div>
        <div>
          <span>Current issue</span>
          <strong>{daemon?.stale ? "Stale heartbeat" : display(daemon?.current_ticket_key)}</strong>
        </div>
        <div>
          <span>Heartbeat</span>
          <strong>{display(daemon?.heartbeat_at)}</strong>
        </div>
        <div>
          <span>Claimable</span>
          <strong>{display(daemon?.claimable_assignment_count, "0")}</strong>
        </div>
        <div>
          <span>Running</span>
          <strong>{display(daemon?.running_assignment_count, "0")}</strong>
        </div>
        <div>
          <span>Blocked</span>
          <strong>{display(daemon?.blocked_assignment_count, "0")}</strong>
        </div>
      </section>
      {daemon?.last_error ? <p className="action-message">{daemon.last_error}</p> : null}

      <section className="panel wide assignment-progress-panel" data-testid="runs-assignment-progress">
        <h2>Active Assignment Progress</h2>
        {activeAssignmentId ? <p><strong>{activeAssignmentId}</strong> · polling every 5s</p> : <p className="empty-column">No active assignment is currently claimed or running.</p>}
        {progressMessage ? <p className="action-message">{progressMessage}</p> : null}
        {progressEvents.length ? (
          <ol className="assignment-event-list">
            {progressEvents.slice(-12).map((event) => (
              <li key={event.id}>
                <span>{event.timestamp}</span>
                <strong>{event.stage} / {event.event_type}</strong>
                <p>{event.summary}</p>
                <small>{event.actor}{event.ref_id ? ` · ${event.ref_id}` : ""}</small>
              </li>
            ))}
          </ol>
        ) : activeAssignmentId ? <p className="empty-column">No progress events recorded yet.</p> : null}
      </section>

      <div className="control-surface-grid">
        <section className="panel wide">
          <h2>Runtimes</h2>
          <div className="table-card compact-table">
            <div className="table-row runs-runtime-row head">
              <span>Runtime</span>
              <span>State</span>
              <span>Available</span>
              <span>Assign / Run</span>
              <span>External</span>
              <span>Queue</span>
              <span>Disabled reasons</span>
            </div>
            {runtimes.map((runtime) => (
              <div className="table-row runs-runtime-row" key={runtime.runtime_id}>
                <strong>{runtime.display_name}<small>{runtime.backend_name}</small></strong>
                <span>{statusLabel(runtime.daemon_state)}</span>
                <span>{runtime.available ? "Available" : "Unavailable"}</span>
                <span>{runtime.can_assign ? "assign" : "no assign"} / {runtime.can_run ? "run" : "no run"}</span>
                <span>{runtime.external_execution_enabled ? "Enabled" : "Gated"}</span>
                <span>{runtime.queue_depth}</span>
                <span>{runtime.disabled_reasons.length ? runtime.disabled_reasons.join("; ") : "None"}</span>
              </div>
            ))}
            {!runtimes.length ? <p className="empty-column">No runtimes projected.</p> : null}
          </div>
        </section>

        <section className="panel wide">
          <h2>Assignments</h2>
          <div className="table-card compact-table">
            <div className="table-row runs-assignment-row head">
              <span>Issue</span>
              <span>Agent</span>
              <span>Backend</span>
              <span>Status</span>
              <span>Attempt</span>
              <span>Created</span>
              <span>Blocked / failure</span>
            </div>
            {assignments.map((assignment) => (
              <div className="table-row runs-assignment-row" key={assignment.id}>
                <strong>{assignment.ticket_key}<small>{assignment.id}</small></strong>
                <span>{assignment.agent_name}</span>
                <span>{display(assignment.backend_name)}</span>
                <span>{statusLabel(assignment.status)}</span>
                <span>{display(assignment.attempt, "1")}</span>
                <span>{display(assignment.created_at)}</span>
                <span>{assignment.blocked_reason ?? assignment.failure_reason ?? assignment.blocker ?? "None"}</span>
              </div>
            ))}
            {!assignments.length ? <p className="empty-column">No assignments projected.</p> : null}
          </div>
        </section>
      </div>
    </section>
  );
}
