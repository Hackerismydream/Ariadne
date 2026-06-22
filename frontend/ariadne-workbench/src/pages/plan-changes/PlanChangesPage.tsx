import { AlertTriangle, ListTodo, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { PageKey } from "../../app/routes";
import {
  applyIssueFactoryPreview,
  createIssueFactoryPreview,
  refreshIssueFactoryPreview,
} from "../../shared/api/client";
import { apiErrorCode } from "../../shared/api/errors";
import { groupBacklogChanges } from "../../shared/lib/backlog";
import type { BacklogChange, WorkbenchData } from "../../types";
import type { WorkbenchDataSource } from "../../data";

function buildDecisionLabel(decision: string) {
  const labels: Record<string, string> = {
    architecture_change: "Architecture change",
    archive: "Archive",
    code_task: "Code task",
    doc_update: "Doc update",
    experiment: "Experiment",
    reject_for_now: "Reject for now",
    watchlist: "Watchlist",
  };
  return labels[decision] ?? decision;
}

function previewStatusLabel(status: WorkbenchData["backlogMutationPreview"]["status"]) {
  if (status === "applied") return "Applied";
  if (status === "blocked") return "Blocked: unsafe changes";
  return "Preview only";
}

function traceLabel(label: string) {
  const labels: Record<string, string> = {
    Source: "Source",
    Evidence: "Evidence",
    "Build Decision": "Build decision",
    "Ticket Delta": "Issue delta",
    "Build Packet": "Build packet",
    Handoff: "Handoff",
  };
  return labels[label] ?? label;
}

function operationLabel(kind: string) {
  const labels: Record<string, string> = {
    added: "Added",
    deferred: "Deferred",
    rejected: "Rejected",
    updated: "Updated",
  };
  return labels[kind] ?? kind;
}

function ColumnHeader({ title, meta }: { title: string; meta?: string }) {
  return (
    <header className="column-header">
      <h2>{title}</h2>
      {meta ? <span>{meta}</span> : null}
    </header>
  );
}

function DeltaGroup({
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
    <section className="change-group issue-delta-group">
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
          <p>{change.goalReason || change.reason}</p>
          <em>{change.priority}</em>
          <small>{change.sourceArtifactIds?.length ?? 0} artifacts · {change.acceptanceCriteria?.length ?? 0} acceptance</small>
        </button>
      )) : <p className="no-changes">No {title.toLowerCase()} items.</p>}
    </section>
  );
}

function DeltaDetail({ change }: { change?: BacklogChange }) {
  if (!change) {
    return <p className="empty-column">Generate or select an issue delta item.</p>;
  }
  return (
    <article className="knowledge-card selected issue-delta-detail">
      <header>
        <div>
          <strong>{change.title}</strong>
          <small>{change.ticketKey} · {operationLabel(change.kind)} · {buildDecisionLabel(change.buildDecision)}</small>
        </div>
        <span className="primary-badge">{change.priority}</span>
      </header>
      <section>
        <h3>Reason</h3>
        <p>{change.goalReason || change.reason || "No reason recorded."}</p>
      </section>
      <section>
        <h3>Source artifacts</h3>
        <div className="evidence-list">
          {change.sourceArtifactIds?.length ? change.sourceArtifactIds.map((item) => <code key={item}>{item}</code>) : <span>No source artifacts recorded.</span>}
        </div>
      </section>
      <section>
        <h3>Evidence refs</h3>
        <div className="evidence-list">
          {change.evidenceRefs?.length ? change.evidenceRefs.map((item) => <code key={item}>{item}</code>) : <span>No evidence refs recorded.</span>}
        </div>
      </section>
      <section>
        <h3>Acceptance criteria</h3>
        {change.acceptanceCriteria?.length ? (
          <ul className="risk-list">
            {change.acceptanceCriteria.map((item) => <li key={item}>{item}</li>)}
          </ul>
        ) : <p className="empty-column">No acceptance criteria recorded.</p>}
      </section>
      <section>
        <h3>Affected modules</h3>
        <div className="module-row">
          {change.affectedModules?.length ? change.affectedModules.map((item) => <span key={item}>{item}</span>) : <span>No affected modules recorded.</span>}
        </div>
      </section>
      <div className="card-meta-grid">
        <section>
          <h3>Build context</h3>
          <code>{change.buildContextId ?? "Not recorded"}</code>
        </section>
        <section>
          <h3>Decision confidence</h3>
          <p>{typeof change.confidence === "number" ? change.confidence.toFixed(2) : "Not recorded"}</p>
        </section>
      </div>
    </article>
  );
}

export function PlanChangesPage({
  data,
  dataSource,
  onNavigate,
  onRefresh,
}: {
  data: WorkbenchData;
  dataSource: WorkbenchDataSource;
  onNavigate: (page: PageKey) => void;
  onRefresh: () => Promise<void>;
}) {
  const [selectedChangeId, setSelectedChangeId] = useState(data.backlogChanges[0]?.id ?? "");
  const [previewStatus, setPreviewStatus] = useState(data.backlogMutationPreview.status);
  const [currentPreviewId, setCurrentPreviewId] = useState(data.backlogMutationPreview.previewId ?? "");
  const [stalePreviewId, setStalePreviewId] = useState("");
  const [actionStatus, setActionStatus] = useState("");
  const [showViewIssues, setShowViewIssues] = useState(false);
  const [busy, setBusy] = useState(false);
  const selectedChange = data.backlogChanges.find((change) => change.id === selectedChangeId)
    ?? data.backlogChanges[0];
  const groupedChanges = useMemo(() => groupBacklogChanges(data.backlogChanges), [data.backlogChanges]);
  const activeGoal = data.goal.id !== "GOAL-NOT-CREATED" ? data.goal : undefined;
  const activeProject = data.projectResources?.find((resource) => resource.id === activeGoal?.targetProjectId && resource.available)
    ?? data.projectResources?.find((resource) => resource.available)
    ?? data.projectResources?.[0];
  const activePreviewId = data.backlogMutationPreview.previewId;
  const readySourceIds = (data.projectInputs ?? [])
    .filter((input) => input.lifecycle.readyForIssueFactory)
    .map((input) => input.source.id);
  const analyzedSourceIds = readySourceIds.length
    ? readySourceIds
    : data.sources
      .filter((source) => ["analyzed", "partial"].includes(source.analysisStatus ?? source.status))
      .map((source) => source.id);
  const traceSteps = selectedChange
    ? data.traceSteps.filter((step) => !step.backlogChangeId || step.backlogChangeId === selectedChange.id)
    : data.traceSteps.slice(0, 8);

  useEffect(() => {
    if (!data.backlogChanges.some((change) => change.id === selectedChangeId)) {
      setSelectedChangeId(data.backlogChanges[0]?.id ?? "");
    }
    if (data.backlogMutationPreview.previewId && !currentPreviewId) {
      setCurrentPreviewId(data.backlogMutationPreview.previewId);
      setPreviewStatus(data.backlogMutationPreview.status);
    }
  }, [currentPreviewId, data.backlogChanges, data.backlogMutationPreview.status, data.backlogMutationPreview.previewId, selectedChangeId]);

  async function generateDelta() {
    if (!activeGoal) {
      setActionStatus("Create a project goal before generating an issue delta.");
      return;
    }
    if (!analyzedSourceIds.length) {
      setActionStatus("No analyzed sources are ready. Add and analyze a source first.");
      return;
    }
    setBusy(true);
    setShowViewIssues(false);
    setStalePreviewId("");
    setActionStatus(`Generating issue delta from ${analyzedSourceIds.length} analyzed sources...`);
    try {
      const result = await createIssueFactoryPreview({
        goal_id: activeGoal.id,
        source_ids: analyzedSourceIds,
        target_project_id: activeProject?.id ?? null,
      });
      setCurrentPreviewId(result.preview.id);
      setSelectedChangeId(result.preview.operations[0]?.id ?? "");
      setPreviewStatus("preview_only");
      await onRefresh();
      setActionStatus(`Generated ${result.preview.operations.length} issue delta items.`);
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "Issue delta generation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshStalePreview() {
    const previewId = stalePreviewId || currentPreviewId || activePreviewId;
    if (!previewId || !activeGoal) return;
    setBusy(true);
    setActionStatus("Refreshing stale issue delta preview...");
    try {
      const result = await refreshIssueFactoryPreview(previewId, {
        goal_id: activeGoal.id,
        source_ids: analyzedSourceIds,
        target_project_id: activeProject?.id ?? null,
      });
      setCurrentPreviewId(result.preview.id);
      setSelectedChangeId(result.preview.operations[0]?.id ?? "");
      setStalePreviewId("");
      setPreviewStatus("preview_only");
      await onRefresh();
      setActionStatus(`Preview refreshed. Review ${result.preview.operations.length} delta items before applying.`);
    } catch (error) {
      setActionStatus(error instanceof Error ? error.message : "Preview refresh failed.");
    } finally {
      setBusy(false);
    }
  }

  async function applyPreview() {
    const previewId = currentPreviewId || activePreviewId;
    if (!previewId) {
      setActionStatus("No issue delta preview is ready to apply.");
      return;
    }
    setBusy(true);
    setActionStatus("Applying issue delta...");
    try {
      await applyIssueFactoryPreview(previewId);
      await onRefresh();
      setPreviewStatus("applied");
      setShowViewIssues(true);
      setActionStatus("Issue delta applied. New issues are available on the board.");
    } catch (error) {
      if (apiErrorCode(error) === "stale_preview") {
        setStalePreviewId(previewId);
        setPreviewStatus("preview_only");
        setActionStatus("Preview is stale because the issue backlog changed. Refresh the preview before applying.");
      } else {
        setActionStatus(error instanceof Error ? error.message : "Apply failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page full-bleed plan-changes-page">
      <header className="page-header">
        <div className="title-row">
          <ListTodo size={17} />
          <h1>Plan Changes</h1>
          <span>{data.backlogChanges.length}</span>
          <p>Issue Delta turns analyzed sources into confirmed current-version issues.</p>
        </div>
        <div className="toolbar">
          <button className="primary-action" disabled={dataSource !== "api" || busy} type="button" onClick={() => void generateDelta()}>
            Generate Issue Delta
          </button>
          <button disabled={dataSource !== "api" || busy || !(currentPreviewId || activePreviewId) || previewStatus === "applied"} type="button" onClick={() => void applyPreview()}>
            {previewStatus === "applied" ? "Applied" : "Apply Changes"}
          </button>
          {showViewIssues ? <button type="button" onClick={() => onNavigate("ready")}>View Issues</button> : null}
        </div>
      </header>

      <section className="panel compiler-summary">
        <div>
          <h2>Issue Delta</h2>
          <p>Inputs: project goal, {analyzedSourceIds.length} ready sources, {data.sourceArtifacts?.length ?? 0} typed artifacts, {data.sourceEvidence?.length ?? 0} evidence snippets.</p>
        </div>
        <div className="summary-metrics">
          <span>Added {data.backlogMutationPreview.added}</span>
          <span>Updated {data.backlogMutationPreview.updated}</span>
          <span>Deferred {data.backlogMutationPreview.deferred}</span>
          <span>Rejected {data.backlogMutationPreview.rejected}</span>
          <span>Unsafe {data.backlogMutationPreview.unsafe}</span>
          <em>{previewStatusLabel(previewStatus)}</em>
        </div>
        {stalePreviewId ? (
          <div className="stale-preview-callout">
            <AlertTriangle size={16} />
            <span>Preview is stale. Refresh it before applying.</span>
            <button disabled={busy} type="button" onClick={() => void refreshStalePreview()}>
              <RefreshCw size={14} /> Refresh Preview
            </button>
          </div>
        ) : null}
        {actionStatus ? <p className="action-message">{actionStatus}</p> : null}
      </section>

      <div className="knowledge-layout">
        <section className="knowledge-column changes-column">
          <ColumnHeader title="Delta items" meta={data.backlogMutationPreview.previewId ?? "No preview yet"} />
          <DeltaGroup title="Added" kind="added" changes={groupedChanges.added} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <DeltaGroup title="Updated" kind="updated" changes={groupedChanges.updated} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <DeltaGroup title="Deferred" kind="deferred" changes={groupedChanges.deferred} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
          <DeltaGroup title="Rejected" kind="rejected" changes={groupedChanges.rejected} selectedId={selectedChange?.id} onSelect={setSelectedChangeId} />
        </section>

        <section className="knowledge-column cards-column">
          <ColumnHeader title="Selected delta" meta={selectedChange?.ticketKey ?? "None"} />
          <DeltaDetail change={selectedChange} />
        </section>

        <aside className="knowledge-column trace-column">
          <ColumnHeader title="Compiler trace" meta={selectedChange?.ticketKey ?? "All"} />
          <ol className="trace-list">
            {traceSteps.length ? traceSteps.map((step) => (
              <li key={step.id}>
                <span className="trace-dot" />
                <div>
                  <h3>{traceLabel(step.label)}</h3>
                  <p>{step.summary}</p>
                  <code>{step.artifactPath}</code>
                  <small>{step.timestamp}</small>
                </div>
              </li>
            )) : <li className="trace-empty">Generate an issue delta to see Source {"->"} Evidence {"->"} Issue Delta.</li>}
          </ol>
        </aside>
      </div>
    </section>
  );
}
