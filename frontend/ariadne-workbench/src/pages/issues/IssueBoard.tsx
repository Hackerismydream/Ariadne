import type { ApiIssueListItem } from "../../shared/api/types";
import { IssueCard } from "./IssueCard";

const columns: Array<{ id: string; label: string; statuses: string[] }> = [
  { id: "backlog", label: "Backlog", statuses: ["open", "planning", "inbox"] },
  { id: "ready", label: "Ready", statuses: ["ready"] },
  { id: "assigned", label: "Assigned", statuses: ["assigned", "queued", "claimed"] },
  { id: "running", label: "Running", statuses: ["running", "in_progress", "coding"] },
  { id: "review", label: "Review", statuses: ["reviewing", "review_pending", "review"] },
  { id: "blocked", label: "Blocked", statuses: ["blocked", "failed", "needs_fix"] },
  { id: "done", label: "Done", statuses: ["done", "closed", "released"] },
];

function columnFor(issue: ApiIssueListItem) {
  return columns.find((column) => column.statuses.includes(issue.status)) ?? columns[0];
}

export function IssueBoard({ issues, onOpen }: { issues: ApiIssueListItem[]; onOpen: (issueKey: string) => void }) {
  const grouped = columns.map((column) => ({
    ...column,
    issues: issues.filter((issue) => columnFor(issue).id === column.id),
  }));
  return (
    <div className="phase3-board" data-testid="issues-board">
      {grouped.map((column) => (
        <section className={`phase3-board-column ${column.id}`} key={column.id}>
          <header>
            <h2>{column.label}</h2>
            <span>{column.issues.length}</span>
          </header>
          {column.issues.length ? (
            column.issues.map((issue) => <IssueCard issue={issue} key={issue.id} onOpen={onOpen} />)
          ) : (
            <p className="empty-column">No issues</p>
          )}
        </section>
      ))}
    </div>
  );
}
