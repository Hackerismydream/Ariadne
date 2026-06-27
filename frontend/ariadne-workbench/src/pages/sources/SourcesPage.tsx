import { BookOpenText, ExternalLink, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { PageKey } from "../../app/routes";
import { inferSourceInput, sourceAnalysisLabel, type SourceFormType } from "../../features/project-inputs/model";
import { analyzeSource, createSource, getSourceDetail } from "../../shared/api/client";
import type { ProjectInputDetail, SourceDocument, WorkbenchData } from "../../types";
import { adaptProjectInputDetail, type WorkbenchDataSource } from "../../data";

function sourceTypeLabel(sourceType: SourceDocument["sourceType"]) {
  const labels: Record<SourceDocument["sourceType"], string> = {
    blog: "Blog",
    paper: "Paper",
    github_repo: "GitHub repo",
    github_readme: "GitHub README",
    repo_note: "Repo note",
    local_markdown: "Local markdown",
    local_folder: "Local folder",
    target_codebase: "Target codebase",
    codebase_scan: "Codebase scan",
    review_feedback: "Review feedback",
    execution_result: "Execution result",
    manual_note: "Manual note",
  };
  return labels[sourceType];
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    analyzed: "Analyzed",
    analyzing: "Analyzing",
    blocked: "Blocked",
    failed: "Failed",
    fetching: "Fetching",
    partial: "Partial",
    pending: "Queued",
    resolving: "Resolving",
  };
  return labels[status] ?? sourceAnalysisLabel(status);
}

function originLabel(origin?: string) {
  const labels: Record<string, string> = {
    external: "External inputs",
    target_codebase: "Target codebase",
    feedback: "Run / review feedback",
    internal_synthetic: "Internal derived sources",
  };
  return labels[origin ?? "external"] ?? "External inputs";
}

function sourceQualityLabel(source: SourceDocument) {
  const status = source.qualityStatus ?? "unknown";
  const claims = source.claimCount ?? 0;
  return `${status}${claims ? ` · ${claims} claims` : ""}`;
}

function firstProjectInput(data: WorkbenchData) {
  return data.projectInputs?.[0] ?? null;
}

export function SourcesPage({
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
  const [selectedSourceId, setSelectedSourceId] = useState(firstProjectInput(data)?.source.id ?? data.sources[0]?.id ?? "");
  const [rawInput, setRawInput] = useState("");
  const [overrideTitle, setOverrideTitle] = useState("");
  const [overrideSummary, setOverrideSummary] = useState("");
  const [overrideType, setOverrideType] = useState<SourceFormType>("blog");
  const [showOverrides, setShowOverrides] = useState(false);
  const [selectedDetail, setSelectedDetail] = useState<ProjectInputDetail | null>(firstProjectInput(data));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const inferred = useMemo(() => inferSourceInput(rawInput), [rawInput]);
  const projectInputs = data.projectInputs ?? [];
  const selectedSource = data.sources.find((source) => source.id === selectedSourceId) ?? data.sources[0] ?? null;
  const dataDetail = projectInputs.find((input) => input.source.id === selectedSource?.id) ?? null;
  const detail = selectedDetail?.source.id === selectedSource?.id ? selectedDetail : dataDetail;
  const readyInputs = projectInputs.filter((input) => input.lifecycle.readyForIssueFactory);
  const selectedEvents = selectedSource ? data.sourceEvents.filter((event) => event.sourceId === selectedSource.id) : [];
  const groupedSources = useMemo(() => {
    const groups = new Map<string, SourceDocument[]>();
    for (const source of data.sources) {
      const bucket = source.originBucket ?? "external";
      groups.set(bucket, [...(groups.get(bucket) ?? []), source]);
    }
    return Array.from(groups.entries());
  }, [data.sources]);

  useEffect(() => {
    if (!data.sources.some((source) => source.id === selectedSourceId)) {
      const next = firstProjectInput(data)?.source.id ?? data.sources[0]?.id ?? "";
      setSelectedSourceId(next);
      setSelectedDetail(projectInputs.find((input) => input.source.id === next) ?? null);
    }
  }, [data.sources, projectInputs, selectedSourceId]);

  useEffect(() => {
    if (rawInput.trim()) {
      setOverrideType(inferred.sourceType);
    }
  }, [inferred.sourceType, rawInput]);

  async function selectSource(sourceId: string) {
    setSelectedSourceId(sourceId);
    setMessage("");
    setSelectedDetail(projectInputs.find((input) => input.source.id === sourceId) ?? null);
    if (dataSource !== "api") return;
    try {
      const response = await getSourceDetail(sourceId);
      setSelectedDetail(adaptProjectInputDetail(response.project_input));
    } catch {
      // The aggregate workbench snapshot is enough for display; detail refresh is opportunistic.
    }
  }

  async function addSource() {
    if (!rawInput.trim() || busy) return;
    setBusy(true);
    const title = overrideTitle.trim() || inferred.title || rawInput.trim();
    setMessage(`Adding and analyzing ${title}...`);
    try {
      const result = await createSource({
        title,
        source_type: overrideType || inferred.sourceType,
        source_role: inferred.sourceRole,
        path_or_url: rawInput.trim(),
        content: overrideSummary.trim(),
        summary: overrideSummary.trim() || inferred.summary,
        auto_analyze: true,
      });
      setRawInput("");
      setOverrideTitle("");
      setOverrideSummary("");
      setSelectedSourceId(result.source.id);
      await onRefresh();
      if (result.project_input) {
        setSelectedDetail(adaptProjectInputDetail(result.project_input));
      }
      setMessage(result.duplicate ? `Existing source opened: ${result.source.title}` : `Analyzed source: ${result.source.title}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Source creation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function analyzeSelectedSource() {
    if (!selectedSource || busy) return;
    setBusy(true);
    setMessage(`Analyzing ${selectedSource.title}...`);
    try {
      const result = await analyzeSource(selectedSource.id);
      await onRefresh();
      if (result.project_input) {
        setSelectedDetail(adaptProjectInputDetail(result.project_input));
      }
      setMessage(`Analysis complete: ${selectedSource.title}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Source analysis failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page full-bleed sources-page">
      <header className="page-header">
        <div className="title-row">
          <BookOpenText size={17} />
          <h1>Sources</h1>
          <span>{data.sources.length}</span>
          <p>External inputs become typed artifacts and evidence for issue delta generation.</p>
        </div>
        <div className="toolbar">
          <button type="button" disabled={!readyInputs.length} onClick={() => onNavigate("tasks")}>
            Go to Plan Changes
          </button>
        </div>
      </header>

      <section className="panel source-input-panel primary-source-input">
        <label>
          <span>Paste a URL, GitHub repo, or local path</span>
          <div className="paste-row">
            <input
              disabled={dataSource !== "api" || busy}
              value={rawInput}
              onChange={(event) => setRawInput(event.target.value)}
              placeholder="https://github.com/SWE-agent/mini-swe-agent or /path/to/local/project"
            />
            <button disabled={dataSource !== "api" || busy || !rawInput.trim()} type="button" onClick={() => void addSource()}>
              {busy ? "Working..." : "Add and Analyze"}
            </button>
          </div>
        </label>
        <div className="source-inference-row">
          <span>Detected: {sourceTypeLabel(inferred.sourceType === "note" ? "manual_note" : inferred.sourceType)}</span>
          <span>Role: {inferred.sourceRole.replace(/_/g, " ")}</span>
          <button type="button" onClick={() => setShowOverrides((value) => !value)}>
            {showOverrides ? "Hide overrides" : "Optional overrides"}
          </button>
        </div>
        {showOverrides ? (
          <div className="form-grid source-overrides">
            <label>
              <span>Type</span>
              <select disabled={dataSource !== "api" || busy} value={overrideType} onChange={(event) => setOverrideType(event.target.value as SourceFormType)}>
                <option value="blog">Blog</option>
                <option value="paper">Paper</option>
                <option value="github_repo">GitHub repo</option>
                <option value="note">Manual note</option>
              </select>
            </label>
            <label>
              <span>Title override</span>
              <input disabled={dataSource !== "api" || busy} value={overrideTitle} onChange={(event) => setOverrideTitle(event.target.value)} placeholder={inferred.title || "Optional"} />
            </label>
            <label className="wide-field">
              <span>Summary or excerpt override</span>
              <textarea disabled={dataSource !== "api" || busy} value={overrideSummary} onChange={(event) => setOverrideSummary(event.target.value)} placeholder={inferred.summary || "Optional context for the source analyzer"} />
            </label>
          </div>
        ) : null}
        {message ? <p className="action-message">{message}</p> : null}
      </section>

      <div className="knowledge-layout sources-workbench">
        <section className="knowledge-column source-column">
          <header className="column-header">
            <h2>Source lifecycle</h2>
            <span>{readyInputs.length} ready</span>
          </header>
          <div className="source-list grouped-source-list">
            {groupedSources.map(([origin, sources]) => (
              <section className="source-origin-group" key={origin}>
                <h3>{originLabel(origin)} ({sources.length})</h3>
                {sources.map((source) => {
                  const input = projectInputs.find((candidate) => candidate.source.id === source.id);
                  const lifecycle = input?.lifecycle;
                  return (
                    <button
                      className={`source-row ${source.id === selectedSource?.id ? "selected" : ""}`}
                      data-source-id={source.id}
                      key={source.id}
                      type="button"
                      onClick={() => void selectSource(source.id)}
                    >
                      <span className={`source-type ${source.sourceType}`}>{sourceTypeLabel(source.sourceType)}</span>
                      <strong>{source.title}</strong>
                      <em className={`source-status ${source.analysisStatus ?? source.status}`}>{statusLabel(lifecycle?.status ?? source.analysisStatus ?? source.status)}</em>
                      <small>{lifecycle?.detail || source.ingestedAt}</small>
                      <small>{sourceQualityLabel(source)}</small>
                    </button>
                  );
                })}
              </section>
            ))}
          </div>
        </section>

        <section className="knowledge-column understanding-column">
          <header className="column-header">
            <h2>Source detail</h2>
            <span>{detail?.lifecycle.label ?? (selectedSource ? statusLabel(selectedSource.analysisStatus ?? selectedSource.status) : "No source")}</span>
          </header>
          {selectedSource ? (
            <article className="understanding-panel">
              <header>
                <div>
                  <strong>{selectedSource.title}</strong>
                  <span>{sourceTypeLabel(selectedSource.sourceType)} · {selectedSource.pathOrUrl}</span>
                </div>
                {selectedSource.pathOrUrl ? (
                  <a href={selectedSource.pathOrUrl} target="_blank" rel="noreferrer">
                    <ExternalLink size={14} /> Open
                  </a>
                ) : null}
              </header>
              <section>
                <h3>Lifecycle</h3>
                <div className="source-lifecycle-card">
                  <strong>{detail?.lifecycle.label ?? statusLabel(selectedSource.analysisStatus ?? selectedSource.status)}</strong>
                  <p>{detail?.lifecycle.detail ?? "Lifecycle details are not available in this snapshot."}</p>
                  <span>{detail?.lifecycle.readyForIssueFactory ? "Ready for issue factory" : "Not ready for issue factory"}</span>
                  <span>{originLabel(selectedSource.originBucket)} · {sourceQualityLabel(selectedSource)}</span>
                  {selectedSource.qualityLimitations?.length ? (
                    <ul className="risk-list">
                      {selectedSource.qualityLimitations.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  ) : null}
                  {detail?.lifecycle.blocker ? <code>{detail.lifecycle.blocker}</code> : null}
                </div>
              </section>
              <section>
                <h3>Processing events</h3>
                {selectedEvents.length ? (
                  <div className="source-timeline">
                    {selectedEvents.map((event) => (
                      <div className="timeline-row" key={event.id}>
                        <span>{event.label}</span>
                        <time>{event.createdAt}</time>
                      </div>
                    ))}
                  </div>
                ) : <p className="empty-column">No processing events recorded yet.</p>}
              </section>
              <section>
                <h3>Typed artifacts</h3>
                <div className="artifact-grid">
                  {(detail?.artifacts ?? []).map((artifact) => (
                    <article className="artifact-card" key={artifact.id}>
                      <strong>{artifact.label}</strong>
                      <span>{artifact.kind}</span>
                      <p>{artifact.summary}</p>
                      <small>{artifact.evidenceCount} evidence items</small>
                      {Object.keys(artifact.keyFields).length ? (
                        <div className="artifact-key-fields">
                          {Object.entries(artifact.keyFields).map(([key, value]) => (
                            <p key={key}><strong>{key}</strong>: {Array.isArray(value) ? value.join("; ") : String(value)}</p>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  ))}
                  {!detail?.artifacts.length ? <p className="empty-column">No typed artifacts yet.</p> : null}
                </div>
              </section>
              <section>
                <h3>Evidence snippets</h3>
                {detail?.evidence.length ? detail.evidence.map((item) => (
                  <div className="evidence-row" key={`${item.locator}-${item.claim}`}>
                    <code>{item.locator}</code>
                    <p>{item.summary}</p>
                    <small>{item.claim} · {item.confidenceLabel}</small>
                  </div>
                )) : <p className="empty-column">No evidence yet. Run analysis to extract snippets.</p>}
              </section>
              {detail?.understanding ? (
                <section>
                  <h3>Relation to goal</h3>
                  <ul>
                    {detail.understanding.whatAriadneUnderstood.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </section>
              ) : null}
              <div className="apply-row compact-actions">
                <button disabled={dataSource !== "api" || busy} type="button" onClick={() => void analyzeSelectedSource()}>
                  <RefreshCw size={14} /> Re-analyze
                </button>
                <button disabled={!readyInputs.length} type="button" onClick={() => onNavigate("tasks")}>
                  Go to Plan Changes
                </button>
              </div>
            </article>
          ) : <p className="empty-column">Add a source to inspect its lifecycle, artifacts, and evidence.</p>}
        </section>
      </div>
    </section>
  );
}
