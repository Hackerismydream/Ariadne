# Project Inputs Understanding UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current Sources page from a source inbox into a simple, credible AI Builder flow: paste input -> Ariadne analyzes it -> user sees what Ariadne understood -> user generates evidence-backed task suggestions.

**Architecture:** Hide internal object names (`SourceDocument`, `SourceArtifact`, `SourceEvidence`, `BuildContext`) from users, but expose the product-level understanding trail. Keep the existing local-first FastAPI + JSON store + React Workbench architecture. Add a thin product projection for “Project Input Understanding” instead of making frontend parse raw artifact payloads directly.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, JSON/JSONL store, React + TypeScript + Vite, Pytest, Ruff, browser QA through local Workbench.

---

## Precondition

This plan assumes the typed source-to-issue compiler work from PR #13 is present:

- `SourceEvidence`
- `SourceArtifact`
- `BuildContextManifest`
- `/api/sources/{source_id}/analyze`
- `/api/workbench` includes `source_artifacts` and `source_evidence`
- Workbench pages include `Project`, `Sources`, `Tasks`, `Ready to Run`

If the implementation branch starts from `main` without PR #13 merged, first merge or rebase onto:

```bash
git fetch origin
git switch main
git pull --ff-only
git merge --ff-only origin/codex/typed-source-to-issue-dogfood
```

If fast-forward is impossible, stop and resolve the PR #13 merge first. Do not reimplement typed source foundations in this plan.

## Product Decisions Locked By Review

The reviewers agreed on these principles:

1. Do not expose implementation nouns to users.
2. Do expose what Ariadne understood and why.
3. The Sources page should be renamed in product language to `项目输入`.
4. The main action should be `添加并分析`, not `保存来源`.
5. Adding a source should automatically trigger analysis.
6. After adding, the new source should be selected and visible.
7. The page should show evidence, risks, source role, analysis status, and task impact.
8. `应用任务变更` is not the end; after apply, link users back to issue/agent runtime flow.

## File Structure

Create:

- `ariadne_ltb/application/source_understanding.py`
  - Builds product-facing understanding cards from source documents, artifacts, evidence, and backlog previews.
- `tests/test_source_understanding_projection.py`
  - Verifies source understanding projection does not leak internal object names and includes evidence, risks, and issue impact.
- `frontend/ariadne-workbench/src/features/project-inputs/model.ts`
  - Frontend helpers for URL inference, source status labels, next action labels, and filtering analyzed inputs.
- `tests/test_project_inputs_static.py`
  - Static frontend contract tests for Project Inputs UX.

Modify:

- `ariadne_ltb/application/dtos.py`
  - Add `SourceUnderstandingDTO`, `SourceInputEventDTO`, and expose them from `WorkbenchDTO`.
- `ariadne_ltb/application/mappers.py`
  - Map source documents to browser-safe product vocabulary.
- `ariadne_ltb/application/workbench_projection.py`
  - Include `source_understandings` and `source_events`.
- `ariadne_ltb/application/web_sources.py`
  - Normalize source URLs and detect duplicates.
- `ariadne_ltb/interfaces/http/routes.py`
  - Add `POST /api/sources/analyze-on-create` or update existing create path to support save-and-analyze behavior.
- `frontend/ariadne-workbench/src/shared/api/types.ts`
  - Add API types for source understandings and source events.
- `frontend/ariadne-workbench/src/shared/api/client.ts`
  - Add `analyzeSource()` and `createAndAnalyzeSource()` helper.
- `frontend/ariadne-workbench/src/data.ts`
  - Adapt source understandings into `WorkbenchData`.
- `frontend/ariadne-workbench/src/types.ts`
  - Add `ProjectInputUnderstanding`, `ProjectInputEvent`, and source impact types.
- `frontend/ariadne-workbench/src/App.tsx`
  - Replace current `KnowledgePage` product copy and layout with `ProjectInputsPage`.
- `frontend/ariadne-workbench/src/styles.css`
  - Add compact, non-card-nested styles for the project input page.
- `docs/development_report.md`
  - Record UX correction and remaining limits.
- `docs/dogfood/results/2026-06-19-mini-code-agent-source-to-issue-browser-result.md`
  - Append browser acceptance after this plan is implemented.

## User-Facing Target UX

The user sees this, not backend internals:

```text
项目输入

[ Paste a link, repo, PDF, local path, or note...                   ] [添加并分析]

Project Inputs
- SWE-agent/mini-swe-agent
  GitHub 仓库 · 参考项目
  分析完成 · 3 条证据 · 影响 MCA-003, MCA-006, MCA-007

理解结果
- Ariadne 认为这是一个最小 SWE agent 参考项目
- 可参考 agent loop、工具调用、trajectory、diff/tests
- 不应直接复制代码

关键证据
- README.md: minimal agent loop
- pyproject.toml: CLI entrypoint
- tests/: regression test pattern

下一步
[重新分析] [用已分析输入生成任务]
```

---

## Task 1: Add Product-Level Source Understanding Projection

**Files:**

- Create: `ariadne_ltb/application/source_understanding.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/workbench_projection.py`
- Test: `tests/test_source_understanding_projection.py`

- [ ] **Step 1: Write failing projection test**

Create `tests/test_source_understanding_projection.py`:

```python
from __future__ import annotations

from hashlib import sha256

from ariadne_ltb.application.dtos import WorkbenchDTO
from ariadne_ltb.application.source_analysis import SourceAnalysisService
from ariadne_ltb.application.web_sources import WebSourceService
from ariadne_ltb.application.dtos import CreateSourceInput
from ariadne_ltb.application.workbench_projection import WorkbenchProjectionService
from ariadne_ltb.storage import AriadneStore


def test_workbench_projects_user_facing_source_understanding(tmp_path):
    store = AriadneStore(tmp_path)
    source = WebSourceService(store).create(
        CreateSourceInput(
            title="SWE-agent/mini-swe-agent",
            source_type="github_repo",
            source_role="reference_project",
            path_or_url="https://github.com/SWE-agent/mini-swe-agent/",
            summary="Reference repository for minimal SWE agent architecture.",
            content="The project demonstrates an agent loop, tool calls, trajectory logging, and tests.",
        )
    )
    SourceAnalysisService(store).analyze_source(source.id)

    workbench = WorkbenchProjectionService(store).snapshot()

    assert isinstance(workbench, WorkbenchDTO)
    assert workbench.source_understandings
    understanding = workbench.source_understandings[0]
    assert understanding.source_id == source.id
    assert understanding.display_title == "SWE-agent/mini-swe-agent"
    assert understanding.kind_label == "GitHub 仓库"
    assert understanding.role_label == "参考项目"
    assert understanding.analysis_label == "分析完成"
    assert understanding.what_ariadne_understood
    assert understanding.evidence_items
    assert understanding.generated_outputs
    assert "SourceDocument" not in understanding.model_dump_json()
    assert "SourceArtifact" not in understanding.model_dump_json()
    assert "SourceEvidence" not in understanding.model_dump_json()
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python3.11 -m pytest tests/test_source_understanding_projection.py -q
```

Expected:

```text
AttributeError: 'WorkbenchDTO' object has no attribute 'source_understandings'
```

- [ ] **Step 3: Add DTOs**

Modify `ariadne_ltb/application/dtos.py`:

```python
class SourceEvidenceItemDTO(AriadneDTO):
    locator: str
    summary: str
    claim: str
    confidence_label: str


class SourceUnderstandingDTO(AriadneDTO):
    source_id: str
    display_title: str
    kind_label: str
    role_label: str
    analysis_label: str
    license_risk_label: str = "未知"
    what_ariadne_understood: list[str] = Field(default_factory=list)
    evidence_items: list[SourceEvidenceItemDTO] = Field(default_factory=list)
    generated_outputs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    impacted_ticket_keys: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class SourceInputEventDTO(AriadneDTO):
    id: str
    source_id: str
    event_type: str
    label: str
    created_at: str
```

Add these fields to `WorkbenchDTO`:

```python
source_understandings: list[SourceUnderstandingDTO] = Field(default_factory=list)
source_events: list[SourceInputEventDTO] = Field(default_factory=list)
```

- [ ] **Step 4: Implement projection builder**

Create `ariadne_ltb/application/source_understanding.py`:

```python
from __future__ import annotations

from ariadne_ltb.application.dtos import SourceEvidenceItemDTO, SourceInputEventDTO, SourceUnderstandingDTO
from ariadne_ltb.models import SourceArtifact, SourceDocument, SourceEvidence
from ariadne_ltb.storage import AriadneStore


KIND_LABELS = {
    "blog": "博客",
    "paper": "论文",
    "github_repo": "GitHub 仓库",
    "github_readme": "GitHub README",
    "note": "手动笔记",
    "manual_note": "手动笔记",
    "repo_note": "仓库笔记",
    "local_markdown": "本地 Markdown",
    "local_folder": "本地文件夹",
    "target_codebase": "目标代码库",
}

ROLE_LABELS = {
    "reference_project": "参考项目",
    "requirement_source": "需求来源",
    "background_knowledge": "背景知识",
    "design_constraint": "设计约束",
    "implementation_example": "实现样例",
    "target_codebase": "目标代码库",
}

ANALYSIS_LABELS = {
    "pending": "已添加",
    "analyzing": "分析中",
    "analyzed": "分析完成",
    "blocked": "分析失败",
    "failed": "分析失败",
}

LICENSE_LABELS = {
    "green": "低风险",
    "yellow": "需确认",
    "red": "高风险",
    "unknown": "未知",
}


def build_source_understandings(store: AriadneStore) -> list[SourceUnderstandingDTO]:
    previews = store.list_backlog_previews()
    result: list[SourceUnderstandingDTO] = []
    for source in store.list_source_documents():
        artifacts = store.list_source_artifacts(source.id)
        evidence = store.list_source_evidence(source.id)
        result.append(
            SourceUnderstandingDTO(
                source_id=source.id,
                display_title=source.title,
                kind_label=KIND_LABELS.get(source.source_type.value, source.source_type.value),
                role_label=ROLE_LABELS.get(str(source.metadata.get("source_role") or "background_knowledge"), "背景知识"),
                analysis_label=ANALYSIS_LABELS.get(str(source.metadata.get("analysis_status") or "pending"), "已添加"),
                license_risk_label=LICENSE_LABELS.get(str(source.metadata.get("license_risk") or "unknown"), "未知"),
                what_ariadne_understood=_understood_points(store, source, artifacts),
                evidence_items=[_evidence_item(item) for item in evidence[:5]],
                generated_outputs=[_artifact_label(item.artifact_type) for item in artifacts],
                risks=_risks(store, artifacts, source),
                impacted_ticket_keys=_impacted_ticket_keys(previews, source, artifacts, evidence),
                next_actions=_next_actions(source, artifacts, evidence),
            )
        )
    return result


def build_source_events(store: AriadneStore) -> list[SourceInputEventDTO]:
    events: list[SourceInputEventDTO] = []
    for source in store.list_source_documents():
        status = str(source.metadata.get("analysis_status") or "pending")
        events.append(
            SourceInputEventDTO(
                id=f"source-event-{source.id}-{status}",
                source_id=source.id,
                event_type=f"source.{status}",
                label=f"{source.title}: {ANALYSIS_LABELS.get(status, '已添加')}",
                created_at=source.created_at,
            )
        )
    return sorted(events, key=lambda item: item.created_at, reverse=True)[:20]


def _evidence_item(evidence: SourceEvidence) -> SourceEvidenceItemDTO:
    confidence = "高" if evidence.confidence >= 0.75 else "中" if evidence.confidence >= 0.45 else "低"
    return SourceEvidenceItemDTO(
        locator=evidence.locator,
        summary=evidence.quote_or_summary,
        claim=evidence.claim,
        confidence_label=confidence,
    )


def _artifact_label(artifact_type: str) -> str:
    return {
        "knowledge_card": "知识摘要",
        "reference_project_profile": "参考项目画像",
        "codebase_snapshot": "代码库快照",
    }.get(artifact_type, artifact_type)


def _understood_points(store: AriadneStore, source: SourceDocument, artifacts: list[SourceArtifact]) -> list[str]:
    if not artifacts:
        return ["Ariadne 已保存这个输入，等待分析。"]
    points: list[str] = []
    for artifact in artifacts:
        payload = store.load_source_artifact_payload(artifact.id)
        if artifact.artifact_type == "reference_project_profile":
            points.append(f"这是一个参考项目：{payload.get('repo_summary') or source.summary or source.title}")
            if payload.get("behavior_patterns"):
                points.append(f"可参考模式：{'; '.join(payload['behavior_patterns'][:3])}")
            if payload.get("avoid_notes"):
                points.append(f"避免事项：{'; '.join(payload['avoid_notes'][:2])}")
        elif artifact.artifact_type == "codebase_snapshot":
            points.append(f"这是目标代码库快照，包含 {len(payload.get('top_level') or [])} 个顶层入口。")
            if payload.get("test_commands"):
                points.append(f"识别到测试命令：{', '.join(payload['test_commands'])}")
        else:
            points.append(str(payload.get("summary") or source.summary or source.title))
    return points[:5]


def _risks(store: AriadneStore, artifacts: list[SourceArtifact], source: SourceDocument) -> list[str]:
    risks: list[str] = []
    license_risk = str(source.metadata.get("license_risk") or "unknown")
    if license_risk in {"yellow", "red", "unknown"}:
        risks.append("许可证或复用边界需要确认。")
    for artifact in artifacts:
        payload = store.load_source_artifact_payload(artifact.id)
        risks.extend(str(item) for item in payload.get("avoid_notes", [])[:2])
    return risks[:4]


def _impacted_ticket_keys(previews, source: SourceDocument, artifacts: list[SourceArtifact], evidence: list[SourceEvidence]) -> list[str]:  # noqa: ANN001
    source_ids = {source.id}
    artifact_ids = {artifact.id for artifact in artifacts}
    evidence_ids = {item.id for item in evidence}
    keys: list[str] = []
    for preview in previews:
        for operation in preview.operations:
            metadata = operation.metadata
            if source_ids & set(metadata.get("source_document_ids", [])):
                keys.append(operation.ticket_key or "NEW")
            elif artifact_ids & set(operation.source_artifact_ids):
                keys.append(operation.ticket_key or "NEW")
            elif evidence_ids & set(operation.evidence_refs):
                keys.append(operation.ticket_key or "NEW")
    return sorted(set(keys))[:8]


def _next_actions(source: SourceDocument, artifacts: list[SourceArtifact], evidence: list[SourceEvidence]) -> list[str]:
    status = str(source.metadata.get("analysis_status") or "pending")
    if status in {"pending", "blocked", "failed"}:
        return ["分析这个输入", "忽略这个输入"]
    if artifacts and evidence:
        return ["用已分析输入生成任务", "重新分析", "标记为重要"]
    return ["重新分析", "补充摘要"]
```

- [ ] **Step 5: Wire projection into Workbench snapshot**

Modify `ariadne_ltb/application/workbench_projection.py`:

```python
from ariadne_ltb.application.source_understanding import build_source_events, build_source_understandings
```

When constructing `WorkbenchDTO`, include:

```python
source_understandings=build_source_understandings(self.store),
source_events=build_source_events(self.store),
```

- [ ] **Step 6: Run projection test**

Run:

```bash
python3.11 -m pytest tests/test_source_understanding_projection.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 7: Commit**

```bash
git add ariadne_ltb/application/source_understanding.py ariadne_ltb/application/dtos.py ariadne_ltb/application/workbench_projection.py tests/test_source_understanding_projection.py
git commit -m "feat: project source understanding for workbench"
```

---

## Task 2: Make Add Input Link-First and Auto-Analyze

**Files:**

- Modify: `ariadne_ltb/application/web_sources.py`
- Modify: `ariadne_ltb/interfaces/http/routes.py`
- Modify: `frontend/ariadne-workbench/src/shared/api/client.ts`
- Modify: `frontend/ariadne-workbench/src/features/project-inputs/model.ts`
- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Test: `tests/test_web_source_auto_analysis.py`
- Test: `tests/test_project_inputs_static.py`

- [ ] **Step 1: Write backend test for save-and-analyze**

Create `tests/test_web_source_auto_analysis.py`:

```python
from __future__ import annotations

from fastapi.testclient import TestClient

from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.storage import AriadneStore


def test_create_source_can_auto_analyze_github_repo(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/sources",
        json={
            "title": "SWE-agent/mini-swe-agent",
            "source_type": "github_repo",
            "source_role": "reference_project",
            "path_or_url": "https://github.com/SWE-agent/mini-swe-agent/",
            "summary": "Reference repo",
            "content": "Reference for minimal SWE agent loop, tools, trajectory, and tests.",
            "auto_analyze": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["analysis_status"] == "analyzed"
    assert payload["source"]["artifact_ids"]
    store = AriadneStore(tmp_path)
    assert store.list_source_artifacts(payload["source"]["id"])
    assert store.list_source_evidence(payload["source"]["id"])
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
python3.11 -m pytest tests/test_web_source_auto_analysis.py -q
```

Expected:

```text
extra_forbidden: auto_analyze
```

- [ ] **Step 3: Add request field**

Modify `ariadne_ltb/application/dtos.py` `CreateSourceInput`:

```python
auto_analyze: bool = False
```

- [ ] **Step 4: Auto-analyze in route**

Modify `ariadne_ltb/interfaces/http/routes.py` create source handler:

```python
@router.post("/api/sources")
def create_source(
    payload: CreateSourceInput,
    store: AriadneStore = Depends(get_store),
) -> dict:
    source = WebSourceService(store).create(payload)
    if payload.auto_analyze:
        SourceAnalysisService(store).analyze_source(source.id)
        source = store.load_source_document(source.id)
    return {"source": source_document_dto(store, source).model_dump(mode="json")}
```

- [ ] **Step 5: Add frontend API helper**

Modify `frontend/ariadne-workbench/src/shared/api/types.ts`:

```ts
export type CreateSourceRequest = {
  title: string;
  source_type: "blog" | "paper" | "github_repo" | "github_readme" | "note" | "manual_note" | "repo_note" | "local_markdown" | "local_folder" | "target_codebase";
  source_role?: "reference_project" | "requirement_source" | "background_knowledge" | "design_constraint" | "implementation_example" | "target_codebase";
  path_or_url: string;
  content?: string;
  summary?: string;
  evidence_snippets?: string[];
  auto_analyze?: boolean;
};
```

Modify `frontend/ariadne-workbench/src/shared/api/client.ts`:

```ts
export function analyzeSource(sourceId: string) {
  return requestJson(`/api/sources/${encodeURIComponent(sourceId)}/analyze`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}
```

- [ ] **Step 6: Add frontend URL inference helper**

Create `frontend/ariadne-workbench/src/features/project-inputs/model.ts`:

```ts
export type SourceFormType = "blog" | "paper" | "github_repo" | "note";

export function inferSourceInput(rawValue: string): {
  title: string;
  sourceType: SourceFormType;
  sourceRole: "reference_project" | "requirement_source" | "background_knowledge";
  summary: string;
} {
  const value = rawValue.trim();
  if (!value) return { title: "", sourceType: "blog", sourceRole: "background_knowledge", summary: "" };
  try {
    const url = new URL(value);
    const host = url.hostname.replace(/^www\./, "");
    const parts = url.pathname.split("/").filter(Boolean);
    if (host === "github.com" && parts.length >= 2) {
      const owner = parts[0];
      const repo = parts[1].replace(/\\.git$/, "");
      return {
        title: `${owner}/${repo}`,
        sourceType: "github_repo",
        sourceRole: "reference_project",
        summary: `${owner}/${repo} reference repository. Ariadne will use it as implementation context and avoid direct code copying.`,
      };
    }
    if (value.toLowerCase().endsWith(".pdf") || host.includes("arxiv.org")) {
      return {
        title: parts.at(-1)?.replace(/[-_]/g, " ") || host,
        sourceType: "paper",
        sourceRole: "background_knowledge",
        summary: `${host} paper or PDF source.`,
      };
    }
    return {
      title: parts.at(-1)?.replace(/[-_]/g, " ") || host,
      sourceType: "blog",
      sourceRole: "requirement_source",
      summary: `${host} web source.`,
    };
  } catch {
    const name = value.split(/[\\/]/).filter(Boolean).at(-1) || value;
    return {
      title: name.replace(/[-_]/g, " "),
      sourceType: "note",
      sourceRole: "background_knowledge",
      summary: "Local or manual source.",
    };
  }
}

export function sourceAnalysisLabel(status: string) {
  return {
    pending: "已添加",
    analyzing: "分析中",
    analyzed: "分析完成",
    blocked: "分析失败",
    failed: "分析失败",
  }[status] ?? status;
}
```

- [ ] **Step 7: Update add-source behavior**

Modify the source add handler in `frontend/ariadne-workbench/src/App.tsx`:

```tsx
async function addSource() {
  if (!sourceUrl.trim()) return;
  const inferred = inferSourceInput(sourceUrl);
  const title = sourceTitle.trim() || inferred.title || sourceUrl.trim();
  setActionStatus("正在添加并分析输入...");
  try {
    const result = await createSource({
      title,
      source_type: sourceType,
      source_role: inferred.sourceRole,
      path_or_url: sourceUrl.trim(),
      content: sourceContent.trim(),
      summary: sourceContent.trim() || inferred.summary,
      auto_analyze: true,
    });
    setSourceTitle("");
    setSourceUrl("");
    setSourceContent("");
    await onRefresh();
    setSelectedSourceId(result.source.id);
    setActionStatus("分析完成。Ariadne 已生成理解结果和证据。");
  } catch (error) {
    setActionStatus(error instanceof Error ? error.message : "添加或分析失败。");
  }
}
```

Change button text:

```tsx
<button disabled={dataSource !== "api" || !sourceUrl.trim()} type="button" onClick={() => void addSource()}>
  添加并分析
</button>
```

- [ ] **Step 8: Run backend and frontend tests**

Run:

```bash
python3.11 -m pytest tests/test_web_source_auto_analysis.py tests/test_source_understanding_projection.py -q
cd frontend/ariadne-workbench && npm run build
```

Expected:

```text
passed
✓ built
```

- [ ] **Step 9: Commit**

```bash
git add ariadne_ltb/application/dtos.py ariadne_ltb/interfaces/http/routes.py frontend/ariadne-workbench/src/shared/api/types.ts frontend/ariadne-workbench/src/shared/api/client.ts frontend/ariadne-workbench/src/features/project-inputs/model.ts frontend/ariadne-workbench/src/App.tsx tests/test_web_source_auto_analysis.py
git commit -m "feat: add and analyze project inputs"
```

---

## Task 3: Redesign Sources Page Into Project Inputs Page

**Files:**

- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Modify: `frontend/ariadne-workbench/src/types.ts`
- Modify: `frontend/ariadne-workbench/src/data.ts`
- Modify: `frontend/ariadne-workbench/src/styles.css`
- Test: `tests/test_project_inputs_static.py`

- [ ] **Step 1: Add frontend types**

Modify `frontend/ariadne-workbench/src/types.ts`:

```ts
export type ProjectInputEvidence = {
  locator: string;
  summary: string;
  claim: string;
  confidenceLabel: string;
};

export type ProjectInputUnderstanding = {
  sourceId: string;
  displayTitle: string;
  kindLabel: string;
  roleLabel: string;
  analysisLabel: string;
  licenseRiskLabel: string;
  whatAriadneUnderstood: string[];
  evidenceItems: ProjectInputEvidence[];
  generatedOutputs: string[];
  risks: string[];
  impactedTicketKeys: string[];
  nextActions: string[];
};

export type ProjectInputEvent = {
  id: string;
  sourceId: string;
  eventType: string;
  label: string;
  createdAt: string;
};
```

Add to `WorkbenchData`:

```ts
sourceUnderstandings: ProjectInputUnderstanding[];
sourceEvents: ProjectInputEvent[];
```

- [ ] **Step 2: Add API types**

Modify `frontend/ariadne-workbench/src/shared/api/types.ts`:

```ts
export type ApiSourceEvidenceItem = {
  locator: string;
  summary: string;
  claim: string;
  confidence_label: string;
};

export type ApiSourceUnderstanding = {
  source_id: string;
  display_title: string;
  kind_label: string;
  role_label: string;
  analysis_label: string;
  license_risk_label: string;
  what_ariadne_understood: string[];
  evidence_items: ApiSourceEvidenceItem[];
  generated_outputs: string[];
  risks: string[];
  impacted_ticket_keys: string[];
  next_actions: string[];
};

export type ApiSourceInputEvent = {
  id: string;
  source_id: string;
  event_type: string;
  label: string;
  created_at: string;
};
```

Add to `ApiWorkbench`:

```ts
source_understandings: ApiSourceUnderstanding[];
source_events: ApiSourceInputEvent[];
```

- [ ] **Step 3: Adapt API data**

Modify `frontend/ariadne-workbench/src/data.ts`:

```ts
sourceUnderstandings: apiData.source_understandings.map((item) => ({
  sourceId: item.source_id,
  displayTitle: item.display_title,
  kindLabel: item.kind_label,
  roleLabel: item.role_label,
  analysisLabel: item.analysis_label,
  licenseRiskLabel: item.license_risk_label,
  whatAriadneUnderstood: item.what_ariadne_understood,
  evidenceItems: item.evidence_items.map((evidence) => ({
    locator: evidence.locator,
    summary: evidence.summary,
    claim: evidence.claim,
    confidenceLabel: evidence.confidence_label,
  })),
  generatedOutputs: item.generated_outputs,
  risks: item.risks,
  impactedTicketKeys: item.impacted_ticket_keys,
  nextActions: item.next_actions,
})),
sourceEvents: apiData.source_events.map((event) => ({
  id: event.id,
  sourceId: event.source_id,
  eventType: event.event_type,
  label: event.label,
  createdAt: event.created_at,
})),
```

- [ ] **Step 4: Write static test for product copy**

Create `tests/test_project_inputs_static.py`:

```python
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "ariadne-workbench" / "src" / "App.tsx"


def test_sources_page_uses_project_input_language() -> None:
    text = APP.read_text(encoding="utf-8")
    assert "项目输入" in text
    assert "添加并分析" in text
    assert "Ariadne 理解" in text
    assert "关键证据" in text
    assert "影响的任务" in text
    assert "来源收件箱" not in text


def test_sources_page_does_not_expose_internal_model_names() -> None:
    text = APP.read_text(encoding="utf-8")
    assert "SourceDocument" not in text
    assert "SourceArtifact" not in text
    assert "SourceEvidence" not in text
    assert "BuildContext" not in text
```

- [ ] **Step 5: Replace page title and layout copy**

Modify `frontend/ariadne-workbench/src/App.tsx`:

```tsx
<PageHeader
  icon={<BookOpenText size={17} />}
  title="项目输入"
  count={data.sources.length}
  action={...}
/>
```

Replace the old section title:

```tsx
<h2>添加外部知识</h2>
```

with:

```tsx
<h2>添加项目输入</h2>
<p className="panel-subtitle">粘贴链接、GitHub 仓库、本地路径、论文或笔记。Ariadne 会自动分析并提取可用于生成任务的证据。</p>
```

Replace:

```tsx
<ColumnHeader title="来源收件箱" meta={`${data.sources.length} 个输入`} />
```

with:

```tsx
<ColumnHeader title="项目输入" meta={`${data.sources.length} 个材料`} />
```

- [ ] **Step 6: Add understanding detail panel**

Inside the right side of the source page, replace the primary selected card body with:

```tsx
const selectedUnderstanding = data.sourceUnderstandings.find((item) => item.sourceId === selectedSourceId);
```

Render:

```tsx
<section className="knowledge-column understanding-column">
  <ColumnHeader title="Ariadne 理解" meta={selectedUnderstanding?.analysisLabel ?? "已添加"} />
  {selectedUnderstanding ? (
    <article className="understanding-panel">
      <header>
        <strong>{selectedUnderstanding.displayTitle}</strong>
        <span>{selectedUnderstanding.kindLabel} · {selectedUnderstanding.roleLabel}</span>
      </header>
      <section>
        <h3>Ariadne 理解到</h3>
        <ul>
          {selectedUnderstanding.whatAriadneUnderstood.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>
      <section>
        <h3>关键证据</h3>
        {selectedUnderstanding.evidenceItems.length ? selectedUnderstanding.evidenceItems.map((item) => (
          <div className="evidence-row" key={`${item.locator}-${item.claim}`}>
            <code>{item.locator}</code>
            <p>{item.summary}</p>
            <small>{item.claim} · 可信度 {item.confidenceLabel}</small>
          </div>
        )) : <p className="empty-column">还没有证据。点击重新分析。</p>}
      </section>
      <section>
        <h3>影响的任务</h3>
        <div className="module-row">
          {selectedUnderstanding.impactedTicketKeys.length ? selectedUnderstanding.impactedTicketKeys.map((key) => (
            <button type="button" key={key} onClick={() => onNavigate("ready")}>{key}</button>
          )) : <span>还没有生成任务建议</span>}
        </div>
      </section>
      <section>
        <h3>风险</h3>
        <ul className="risk-list">
          {selectedUnderstanding.risks.map((risk) => <li key={risk}>{risk}</li>)}
        </ul>
      </section>
    </article>
  ) : <p className="empty-column">选择一个输入查看 Ariadne 的理解结果。</p>}
</section>
```

If `onNavigate` is not available in `KnowledgePage`, update the props to pass it from `PageFrame`.

- [ ] **Step 7: Add minimal correction actions**

Add buttons below the understanding panel:

```tsx
<div className="apply-row">
  <button disabled={!selectedSource} type="button" onClick={() => void analyzeSelectedSource()}>
    重新分析
  </button>
  <button disabled={!selectedSource} type="button" onClick={() => setActionStatus("已标记为重要。后续任务生成会优先使用这个输入。")}>
    标记重要
  </button>
  <button disabled={!selectedSource} type="button" onClick={() => setActionStatus("已忽略。后续应从任务生成输入中排除。")}>
    忽略
  </button>
</div>
```

For this MVP, `标记重要` and `忽略` may be frontend status messages only if persistence would require a larger source metadata mutation API. `重新分析` must call the real API:

```tsx
async function analyzeSelectedSource() {
  if (!selectedSource) return;
  setActionStatus("正在重新分析...");
  try {
    await analyzeSource(selectedSource.id);
    await onRefresh();
    setActionStatus("重新分析完成。");
  } catch (error) {
    setActionStatus(error instanceof Error ? error.message : "重新分析失败。");
  }
}
```

- [ ] **Step 8: Run static test and build**

Run:

```bash
python3.11 -m pytest tests/test_project_inputs_static.py -q
cd frontend/ariadne-workbench && npm run build
```

Expected:

```text
passed
✓ built
```

- [ ] **Step 9: Commit**

```bash
git add frontend/ariadne-workbench/src/App.tsx frontend/ariadne-workbench/src/types.ts frontend/ariadne-workbench/src/data.ts frontend/ariadne-workbench/src/styles.css frontend/ariadne-workbench/src/shared/api/types.ts tests/test_project_inputs_static.py
git commit -m "feat: redesign sources as project inputs"
```

---

## Task 4: Make Task Generation Use Clear, Analyzed Inputs

**Files:**

- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Modify: `tests/test_project_inputs_static.py`
- Test: `tests/test_web_dogfood_product_path.py`

- [ ] **Step 1: Add static test for task generation copy**

Append to `tests/test_project_inputs_static.py`:

```python
def test_task_generation_explains_selected_analyzed_inputs() -> None:
    text = APP.read_text(encoding="utf-8")
    assert "将使用已分析输入生成任务" in text
    assert "跳过未分析输入" in text
    assert "查看任务建议" in text
```

- [ ] **Step 2: Update `generateIssues()` input selection**

Modify frontend `generateIssues()`:

```tsx
const analyzedSourceIds = data.sourceUnderstandings
  .filter((item) => item.analysisLabel === "分析完成")
  .map((item) => item.sourceId);

async function generateIssues() {
  if (!activeGoal) {
    setActionStatus("请先在项目页创建目标。");
    return;
  }
  if (!analyzedSourceIds.length) {
    setActionStatus("还没有分析完成的输入。请先添加并分析项目输入。");
    return;
  }
  setActionStatus(`将使用 ${analyzedSourceIds.length} 个已分析输入生成任务，跳过未分析输入。`);
  try {
    const result = await createIssueFactoryPreview({
      goal_id: activeGoal.id,
      source_ids: analyzedSourceIds,
      target_project_id: activeProject?.id ?? null,
    });
    await onRefresh();
    setSelectedChangeId(result.preview.operations[0]?.id ?? "");
    setActionStatus(`已生成 ${result.preview.operations.length} 个任务建议。请查看任务建议后应用。`);
  } catch (error) {
    setActionStatus(error instanceof Error ? error.message : "任务建议生成失败。");
  }
}
```

- [ ] **Step 3: Update button copy**

Change:

```tsx
生成任务
```

to:

```tsx
查看任务建议
```

Use the longer explanation near the button:

```tsx
<p className="hint-text">将使用已分析输入生成任务；未分析或失败的输入会被跳过。</p>
```

- [ ] **Step 4: Verify dogfood expectations still hold**

Run:

```bash
python3.11 -m pytest tests/test_web_dogfood_product_path.py tests/test_project_inputs_static.py -q
cd frontend/ariadne-workbench && npm run build
```

Expected:

```text
passed
✓ built
```

- [ ] **Step 5: Commit**

```bash
git add frontend/ariadne-workbench/src/App.tsx tests/test_project_inputs_static.py
git commit -m "feat: generate tasks from analyzed inputs"
```

---

## Task 5: Add Duplicate Source Detection

**Files:**

- Modify: `ariadne_ltb/application/web_sources.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/mappers.py`
- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Test: `tests/test_web_source_auto_analysis.py`

- [ ] **Step 1: Add duplicate test**

Append to `tests/test_web_source_auto_analysis.py`:

```python
def test_create_source_normalizes_duplicate_github_urls(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    first = {
        "title": "mini-SWE-agent",
        "source_type": "github_repo",
        "source_role": "reference_project",
        "path_or_url": "https://github.com/SWE-agent/mini-SWE-agent",
        "summary": "reference",
        "auto_analyze": False,
    }
    second = {
        **first,
        "title": "SWE-agent/mini-swe-agent",
        "path_or_url": "https://github.com/SWE-agent/mini-swe-agent/",
    }

    first_response = client.post("/api/sources", json=first)
    second_response = client.post("/api/sources", json=second)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["source"]["id"] == first_response.json()["source"]["id"]
    assert second_response.json()["duplicate"] is True
```

- [ ] **Step 2: Add response shape**

Modify route response for `POST /api/sources` to include:

```python
return {
    "source": source_document_dto(store, source).model_dump(mode="json"),
    "duplicate": duplicate,
}
```

If changing the response shape breaks client typing, update `createSource()` return type:

```ts
export function createSource(payload: CreateSourceRequest) {
  return requestJson<{ source: ApiSourceDocument; duplicate?: boolean }>("/api/sources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 3: Normalize URLs in WebSourceService**

Modify `ariadne_ltb/application/web_sources.py`:

```python
def normalized_source_ref(value: str) -> str:
    stripped = value.strip()
    lower = stripped.lower()
    if lower.startswith("https://github.com/"):
        return lower.removesuffix("/").removesuffix(".git")
    return stripped.removesuffix("/")
```

Before creating a new source:

```python
incoming_ref = normalized_source_ref(payload.path_or_url)
for existing in self.store.list_source_documents():
    if normalized_source_ref(existing.path_or_url) == incoming_ref:
        return existing, True
```

If `WebSourceService.create()` currently returns only `SourceDocument`, introduce:

```python
@dataclass(frozen=True)
class CreateSourceResult:
    source: SourceDocument
    duplicate: bool = False
```

Then update call sites.

- [ ] **Step 4: Frontend duplicate feedback**

In `addSource()`:

```tsx
const result = await createSource(...);
await onRefresh();
setSelectedSourceId(result.source.id);
setActionStatus(result.duplicate ? "这个输入已经存在，已打开现有记录。" : "分析完成。Ariadne 已生成理解结果和证据。");
```

- [ ] **Step 5: Run tests**

Run:

```bash
python3.11 -m pytest tests/test_web_source_auto_analysis.py -q
cd frontend/ariadne-workbench && npm run build
```

Expected:

```text
passed
✓ built
```

- [ ] **Step 6: Commit**

```bash
git add ariadne_ltb/application/web_sources.py ariadne_ltb/interfaces/http/routes.py frontend/ariadne-workbench/src/shared/api/client.ts frontend/ariadne-workbench/src/App.tsx tests/test_web_source_auto_analysis.py
git commit -m "feat: detect duplicate project inputs"
```

---

## Task 6: Browser QA Dogfood

**Files:**

- Modify: `docs/dogfood/results/2026-06-19-mini-code-agent-source-to-issue-browser-result.md`
- Modify: `docs/development_report.md`

- [ ] **Step 1: Run full automated verification**

Run:

```bash
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
python3.11 -m ariadne_ltb.cli backend doctor
```

Expected:

```text
356+ passed
All checks passed!
✓ built
backend doctor exits 0 and prints no secrets
```

- [ ] **Step 2: Start Workbench**

Run:

```bash
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8767
```

Expected:

```text
Serving Ariadne Workbench at http://127.0.0.1:8767/
```

- [ ] **Step 3: Browser acceptance**

Use browser automation or the in-app browser. Do not accept CLI-only verification.

Open:

```text
http://127.0.0.1:8767/?v=project-inputs-ux#sources
```

Perform these actions:

1. Paste:

```text
https://github.com/SWE-agent/mini-swe-agent/
```

2. Confirm:

```text
类型 auto-detected as GitHub 仓库
标题 auto-detected as SWE-agent/mini-swe-agent
button says 添加并分析
```

3. Click `添加并分析`.

4. Confirm:

```text
new input is selected
status becomes 分析完成
right side shows Ariadne 理解
right side shows 关键证据
right side shows 风险
right side shows 影响的任务 or "还没有生成任务建议"
```

5. Click `查看任务建议`.

6. Confirm:

```text
only analyzed inputs are used
MCA-001 through MCA-010 can be generated for mini-code-agent dogfood
```

- [ ] **Step 4: Record browser result**

Append to `docs/dogfood/results/2026-06-19-mini-code-agent-source-to-issue-browser-result.md`:

```markdown
## Project Inputs UX Browser Result

- Date:
- URL:
- Input pasted:
- Auto title:
- Auto type:
- Auto analyze result:
- Understanding panel visible:
- Evidence visible:
- Task impact visible:
- Task suggestion generation:
- Failures:
- Follow-up:
```

Fill the fields with real observed values. Do not claim success if a step failed.

- [ ] **Step 5: Update development report**

Append to `docs/development_report.md`:

```markdown
## 2026-06-19 Project Inputs Understanding UX

- Replaced source inbox language with project input language.
- Add source now means add and analyze.
- Ariadne understanding is visible without exposing internal model names.
- Task generation uses analyzed inputs.
- Duplicate GitHub source detection prevents repeated references.
- Browser acceptance:
  - ...

Known limitations:

- ...
```

- [ ] **Step 6: Commit**

```bash
git add docs/dogfood/results/2026-06-19-mini-code-agent-source-to-issue-browser-result.md docs/development_report.md
git commit -m "docs: record project inputs browser QA"
```

---

## Final Verification Before PR

Run:

```bash
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
```

Required outcomes:

- All tests pass.
- Ruff passes.
- Frontend builds.
- Offline regression still works.
- Backend doctor prints no secrets.
- Browser QA confirms URL-only source input -> auto analyze -> visible understanding -> task suggestions.

## Definition of Done

This plan is complete only when:

1. User can paste a GitHub URL and click one button: `添加并分析`.
2. The source is automatically analyzed after creation.
3. New source is selected and visible immediately.
4. Sources page is renamed/reframed as `项目输入`.
5. Page shows `Ariadne 理解`, `关键证据`, `风险`, and `影响的任务`.
6. Internal model names are not visible in the user-facing UI.
7. Task generation uses analyzed inputs and explains skipped pending inputs.
8. Duplicate GitHub URLs select existing source instead of silently creating confusing duplicates.
9. Browser acceptance is recorded with real observed values.
10. Full automated verification passes.

## Out of Scope

- Real Codex/Claude execution of target project code.
- Full GitHub repository cloning and deep static analysis.
- Full persistence for `标记重要` / `忽略` if it expands source metadata mutation scope.
- New hosted auth, multi-user workspaces, or web server deployment.
- Replacing the entire frontend architecture.

## Self-Review

Spec coverage:

- Auto-analyze after save: Task 2.
- Clear destination after save: Task 3 selects and opens the new source.
- Simple user mental model: Task 3 renames Sources to Project Inputs and hides internal names.
- Visible understanding process: Task 1 and Task 3.
- Task generation clarity: Task 4.
- Duplicate handling: Task 5.
- Browser QA: Task 6.

Placeholder scan:

- No `TBD`.
- No unbounded "handle edge cases" steps.
- Every code-changing task includes exact files and concrete snippets.

Type consistency:

- Backend DTOs use snake_case fields.
- Frontend types use camelCase fields.
- Adapter task explicitly maps snake_case to camelCase.
