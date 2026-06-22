import { ListTodo, RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getIssues } from "../../shared/api/client";
import type { ApiIssueListItem } from "../../shared/api/types";
import type { ProjectResource, WorkbenchData } from "../../types";
import { IssueBoard } from "./IssueBoard";
import { IssueDetail } from "./IssueDetail";

function activeTargetProject(data: WorkbenchData): ProjectResource | null {
  const projects = data.projectResources ?? [];
  return data.currentVersionDelivery?.targetProjectId
    ? projects.find((project) => project.id === data.currentVersionDelivery?.targetProjectId) ?? null
    : projects.find((project) => project.id === data.goal.targetProjectId) ?? projects[0] ?? null;
}

function projectDisplayName(data: WorkbenchData) {
  return data.currentVersionDelivery?.targetProjectLabel
    ?? activeTargetProject(data)?.label
    ?? data.goal.title
    ?? "Current project";
}

function pageTitle(issueRef?: string) {
  return issueRef ? "Issue Detail" : "Issues";
}

export function IssuesWorkbenchPage({
  data,
  readOnly,
  selectedRuntime,
  issueRef,
  onRefreshWorkbench,
}: {
  data: WorkbenchData;
  readOnly: boolean;
  selectedRuntime: string;
  issueRef?: string;
  onRefreshWorkbench: (preferredIssueRef?: string) => Promise<void>;
}) {
  const [issues, setIssues] = useState<ApiIssueListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("");

  async function refreshIssues() {
    setLoading(true);
    setMessage("");
    try {
      const response = await getIssues();
      setIssues(response.issues);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to load issues.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshIssues();
  }, []);

  function openIssue(issueKey: string) {
    globalThis.location.hash = `#issues/${encodeURIComponent(issueKey)}`;
  }

  function backToBoard() {
    globalThis.location.hash = "#issues";
  }

  const visibleIssues = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return issues;
    return issues.filter((issue) =>
      [issue.key, issue.title, issue.status, issue.priority, issue.assignee ?? "", issue.review_verdict ?? ""]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [issues, query]);

  if (issueRef) {
    return (
      <IssueDetail
        issueKey={issueRef}
        readOnly={readOnly}
        selectedRuntime={selectedRuntime}
        targetProject={activeTargetProject(data)}
        runtimes={data.runtimes}
        onBack={backToBoard}
        onRefreshWorkbench={onRefreshWorkbench}
      />
    );
  }

  return (
    <section className="page full-bleed phase3-issues-page">
      <header className="page-header">
        <div className="title-row">
          <ListTodo size={17} />
          <h1>{pageTitle(issueRef)}</h1>
          <span>{visibleIssues.length}</span>
          <p>{projectDisplayName(data)} · current version mainline from /api/issues</p>
        </div>
        <div className="toolbar">
          <button type="button" onClick={() => void refreshIssues()}>
            <RefreshCw size={15} /> Refresh
          </button>
        </div>
      </header>
      <div className="issue-search-bar">
        <Search size={16} />
        <input
          aria-label="Search issues"
          placeholder="Search key, title, status, assignee..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <span>{visibleIssues.length} / {issues.length}</span>
      </div>
      {message ? <p className="action-message">{message}</p> : null}
      {loading ? <p className="empty-column">Loading issues...</p> : <IssueBoard issues={visibleIssues} onOpen={openIssue} />}
    </section>
  );
}
