import type { ApiIssueListItem } from "../../shared/api/types";

function statusLabel(status: string | null | undefined) {
  const labels: Record<string, string> = {
    assigned: "Assigned",
    blocked: "Blocked",
    closed: "Done",
    done: "Done",
    in_progress: "Running",
    open: "Backlog",
    planning: "Planning",
    ready: "Ready",
    released: "Done",
    review_pending: "Review",
    reviewing: "Review",
    running: "Running",
  };
  return labels[status ?? ""] ?? status ?? "Unknown";
}

export function IssueCard({ issue, onOpen }: { issue: ApiIssueListItem; onOpen: (issueKey: string) => void }) {
  return (
    <button className={`phase3-issue-card ${issue.blocked_reason ? "blocked" : ""}`} type="button" onClick={() => onOpen(issue.key)}>
      <header>
        <span className="issue-key">{issue.key}</span>
        <em>{issue.priority}</em>
      </header>
      <strong>{issue.title}</strong>
      <div className="phase3-card-meta">
        <span>{issue.assignee ?? "Unassigned"}</span>
        <span>{statusLabel(issue.last_run_status)}</span>
        <span>{issue.evidence_count} evidence</span>
      </div>
      <footer>
        {issue.review_verdict ? <span>Review: {issue.review_verdict}</span> : <span>No review</span>}
        {issue.blocked_reason ? <mark>{issue.blocked_reason}</mark> : null}
      </footer>
    </button>
  );
}
