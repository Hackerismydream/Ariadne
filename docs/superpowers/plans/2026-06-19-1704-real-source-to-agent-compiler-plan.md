# Real Source-to-Agent Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Ariadne's product path from "link saved and shallow scaffold analysis" into a real local-first compiler flow: project goal + typed external inputs + target codebase -> auditable source artifacts -> issue delta -> frozen route/handoff -> Codex/Claude-ready assignment.

**Architecture:** Keep the current Python, JSON/JSONL, FastAPI, React Workbench architecture. Do not add a graph database or a new agent platform. Tighten the existing boundary: `SourceDocument` is source identity, `SourceFetchRecord` is how content was obtained, `SourceArtifact` is typed understanding output, `SourceEvidence` is the citation layer, `BuildContextManifest` is the frozen compiler input, `IssueFactory` emits issue delta, `BuildLead` emits route decision, and `HandoffPacket` is the immutable execution prompt.

**Tech Stack:** Python 3.11+, Pydantic v2, Typer/FastAPI, local git subprocess with strict read-only scan limits, JSON/JSONL persistence, React/Vite Workbench, pytest, ruff.

---

## Review Inputs Absorbed

This plan is based on:

- GPT Pro's recommendation that external inputs must not be flattened into a single `Knowledge Card`.
- Local code review of:
  - `ariadne_ltb/application/source_analysis.py`
  - `ariadne_ltb/application/source_understanding.py`
  - `ariadne_ltb/application/issue_factory.py`
  - `ariadne_ltb/application/build_context.py`
  - `ariadne_ltb/application/assignment_readiness.py`
  - `ariadne_ltb/application/assign_ticket.py`
  - `ariadne_ltb/models.py`
  - `ariadne_ltb/interfaces/http/routes.py`
  - `frontend/ariadne-workbench/src/App.tsx`
  - `frontend/ariadne-workbench/src/features/project-inputs/model.ts`
  - `frontend/ariadne-workbench/src/shared/api/types.ts`
- Four subagent reviews:
  - backend source-analysis review;
  - issue-factory/runtime routing review;
  - Workbench UX review;
  - architecture cross-review.

## Current Diagnosis

The current product path has the right skeleton but weak truthfulness at key boundaries.

- GitHub repo input is identified in the browser, but backend analysis treats the URL as `Path(source.path_or_url)`. No clone, no fetch, no README download, no commit SHA, no real repo scan.
- `SourceDocument`, `SourceArtifact`, `SourceEvidence`, and `BuildContextManifest` already exist, but `SourceArtifact.artifact_type` is too narrow: `knowledge_card`, `reference_project_profile`, `codebase_snapshot`.
- `knowledge_card` is still valid for text sources, but it must not be the generic abstraction for repos, codebases, execution feedback, or review feedback.
- Issue Factory stores `source_document_ids`, `source_artifact_ids`, `evidence_refs`, and `build_context_id`, but generated issues still mostly come from hard-coded Mini Code Agent or generic templates.
- Production planner paths can still fall back to old demo-oriented assumptions in `ingest.py` and deterministic planner logic, especially `demo_todo export-json`.
- Assignment readiness can synthesize `route_decision_id` and `handoff_packet_id` placeholders. That makes `ready_to_claim` look more mature than it is.
- Workbench has a real API path, but the Sources page does not show a truthful fetch/analyze timeline and still makes shallow GitHub analysis look successful.
- Product GitHub analysis must default to the real local git fetcher. Tests may inject a disabled or fake fetcher, but the browser path must not default to blocked just because no fetcher was wired.

## Non-Goals

- Do not build a new web UI framework.
- Do not introduce a vector DB.
- Do not require network in automated tests.
- Do not require Codex, Claude, DeepSeek, Feishu, or GitHub tokens in automated tests.
- Do not delete deterministic tests.
- Do not remove `knowledge_card`; restrict it to text understanding.
- Do not make Issue Factory depend on LLM before the deterministic compiler contract is solid.
- Do not execute code from fetched reference repositories during source understanding.

## Target Product Flow

```text
User creates Project Workspace
  -> user sets goal and target version
  -> user pastes URL / repo / paper / local folder
  -> Source Intake resolves and fetches or links source
  -> Source Understanding creates typed artifacts and evidence
  -> BuildContextManifest freezes goal + sources + target codebase context
  -> Issue Factory compiles issue delta from typed artifacts
  -> user reviews and applies issue delta
  -> Build Lead writes route_decision.json
  -> Handoff Writer writes immutable handoff packet
  -> assignment enters ready_to_claim
  -> daemon claims and invokes Codex/Claude if runtime gates pass
```

## File Structure

Create:

- `ariadne_ltb/application/source_repository.py`
  - GitHub URL normalization, local repo linking, clone/fetch cache, scan budget.
- `ariadne_ltb/application/repository_scanner.py`
  - Read-only repo tree scanner for README, license, manifests, tests, entrypoints, selected core files.
- `ariadne_ltb/application/issue_compiler.py`
  - Deterministic typed-artifact-to-issue compiler.
- `ariadne_ltb/application/handoff_packets.py`
  - Immutable HandoffPacket schema creation and hash validation.
- `tests/test_source_repository_fetch.py`
  - GitHub URL resolver/fetch/cache tests using local bare repositories or fake fetcher.
- `tests/test_repository_scanner.py`
  - Scanner tests for Python and Node fixtures.
- `tests/test_handoff_packet_readiness.py`
  - Assignment readiness cannot synthesize route/handoff placeholders.
- `docs/architecture/source_to_issue_compiler_contract.md`
  - Human-readable contract for future agents.

Modify:

- `ariadne_ltb/models.py`
  - Add `SourceFetchRecord`, expand `SourceArtifact.artifact_type`, add `HandoffPacket`, add stronger source analysis states.
- `ariadne_ltb/storage.py`
  - Persist fetch records and handoff packets.
- `ariadne_ltb/application/source_analysis.py`
  - Route GitHub repo sources through fetch/cache + scanner.
- `ariadne_ltb/application/source_understanding.py`
  - Project scan diagnostics, partial/blocked state, and typed artifact labels.
- `ariadne_ltb/application/source_assets.py`
  - Include fetch status and snapshot fields.
- `ariadne_ltb/application/build_context.py`
  - Require analyzed or partial artifacts; expose fetch diagnostics in manifest metadata.
- `ariadne_ltb/application/issue_factory.py`
  - Replace template-first logic with `IssueCompiler`.
- `ariadne_ltb/application/issue_delta_validation.py`
  - Enforce provenance and target-project safety.
- `ariadne_ltb/application/assignment_readiness.py`
  - Stop synthesizing fake route/handoff ids.
- `ariadne_ltb/application/assign_ticket.py`
  - Persist real route/handoff before `ready_to_claim`.
- `ariadne_ltb/application/run_assignment.py`
  - Dispatch only already-prepared assignments and preserve frozen handoff metadata.
- `ariadne_ltb/orchestrator.py`
  - Build execution context from persisted HandoffPacket when present.
- `ariadne_ltb/execution.py`
  - Use persisted handoff files without overwriting them.
- `ariadne_ltb/team.py`
  - Remove hard-coded `ariadne-local` assumptions from route resources.
- `ariadne_ltb/planner.py`
  - Consume BuildContextManifest metadata instead of source-type demo rules.
- `ariadne_ltb/ingest.py`
  - Quarantine demo-todo mappings to offline regression paths only.
- `ariadne_ltb/application/dtos.py`
  - Expose fetch records, artifact type, scan diagnostics, handoff readiness.
- `ariadne_ltb/application/mappers.py`
  - Map new fields.
- `ariadne_ltb/application/workbench_projection.py`
  - Populate `source_fetch_records` and source timeline inputs.
- `ariadne_ltb/interfaces/http/routes.py`
  - Add source refetch/reanalyze endpoint and target project stable id support.
- `frontend/ariadne-workbench/src/shared/api/types.ts`
  - Add API types.
- `frontend/ariadne-workbench/src/features/project-inputs/model.ts`
  - Improve inferred type/role consistency.
- `frontend/ariadne-workbench/src/shared/api/client.ts`
  - Add refetch/reanalyze and error parser helpers.
- `frontend/ariadne-workbench/src/App.tsx`
  - Add source-to-issue state machine, event timeline, human-readable evidence mapping.
- `frontend/ariadne-workbench/src/styles.css`
  - Style progress and evidence panels.
- `tests/test_source_analysis.py`
  - Update repo assertions.
- `tests/test_issue_factory_compiler.py`
  - Replace hard-coded-only assertions with artifact-derived assertions.
- `tests/test_web_dogfood_product_path.py`
  - Verify browser/API path does not treat empty GitHub URL analysis as complete.
- `tests/test_frontend_api_contract_static.py`
  - Add static contract guards.
- `tests/test_assignment_claim_state_machine.py`
  - Enforce true readiness.
- `docs/development_report.md`
  - Record implementation results after execution.

---

## Task 0: Write the Source-to-Issue Compiler Contract

**Files:**

- Create: `docs/architecture/source_to_issue_compiler_contract.md`

- [ ] **Step 1: Write the contract doc**

Create `docs/architecture/source_to_issue_compiler_contract.md` with:

```markdown
# Source-to-Issue Compiler Contract

## Product Promise

Ariadne lets an AI Builder give a project goal and external inputs. Ariadne reads those inputs, turns them into auditable source artifacts and evidence, compiles issue deltas, and routes approved issues to Codex or Claude through a frozen handoff packet.

## Object Boundaries

- `SourceDocument`: identity and provenance of an input.
- `SourceFetchRecord`: how a remote or local source was fetched, linked, cached, or blocked.
- `SourceArtifact`: typed understanding output produced from one source.
- `SourceEvidence`: atomic cited claim from a source artifact.
- `BuildContextManifest`: frozen set of goal, target project, source documents, artifacts, evidence, and backlog fingerprint used by Issue Factory.
- `BacklogPreview`: proposed issue delta.
- `RouteDecision`: Build Lead decision for one approved issue.
- `HandoffPacket`: immutable packet sent to Codex or Claude.

## Required Invariants

- A GitHub repo source cannot become `analyzed` without a successful fetch/cache record or an explicit `blocked` fetch record.
- `knowledge_card` is only a text-source artifact, not the universal representation of all inputs.
- Issue Factory consumes `BuildContextManifest`, not raw source dumps.
- Every production issue operation must include source document ids, source artifact ids, evidence refs, target project id, affected modules, and acceptance criteria.
- An assignment cannot become `ready_to_claim` without a persisted RouteDecision and HandoffPacket.
- Runtime backends consume the frozen HandoffPacket and must not silently generate a conflicting prompt.
```

- [ ] **Step 2: Link the contract**

Add a short reference to this contract from `docs/development_report.md` during Task 10.

---

## Task 1: Add Source Contract Tests First

**Files:**

- Create: `tests/test_source_repository_fetch.py`
- Modify: `tests/test_source_analysis.py`
- Modify: `tests/test_web_dogfood_product_path.py`

- [ ] **Step 1: Add failing test for GitHub URL not being analyzed without fetch**

Create `tests/test_source_repository_fetch.py`:

```python
from __future__ import annotations

from hashlib import sha256

from ariadne_ltb.application.source_analysis import SourceAnalysisService
from ariadne_ltb.models import SourceDocument, SourceType, stable_id
from ariadne_ltb.storage import AriadneStore


class DisabledRepositoryFetcher:
    def fetch(self, url, cache_root, timeout_seconds=30):
        from ariadne_ltb.application.source_repository import SourceFetchResult

        return SourceFetchResult(
            status="blocked",
            source_url=url,
            cache_path=None,
            commit_sha=None,
            default_branch=None,
            fetched_ref=None,
            file_count=0,
            warnings=[],
            error="repository_fetcher_disabled_for_test",
        )


def test_github_url_does_not_become_analyzed_when_fetch_is_blocked(tmp_path) -> None:
    store = AriadneStore(tmp_path)
    source = SourceDocument(
        id=stable_id("source", "https://github.com/acme/missing", "missing"),
        source_type=SourceType.GITHUB_REPO,
        title="acme/missing",
        path_or_url="https://github.com/acme/missing",
        content_hash=sha256(b"missing").hexdigest(),
        summary="Reference repository.",
        metadata={"source_role": "reference_project"},
    )
    store.save_source_document(source)

    result = SourceAnalysisService(store, repository_fetcher=DisabledRepositoryFetcher()).analyze_source(source.id)
    reloaded = store.load_source_document(source.id)
    fetch_records = store.list_source_fetch_records(source.id)

    assert result.status == "blocked"
    assert reloaded.metadata["analysis_status"] == "blocked"
    assert reloaded.metadata["analysis_error"] == "repository_fetcher_disabled_for_test"
    assert fetch_records
    assert fetch_records[-1].status == "blocked"
    assert store.list_source_artifacts(source.id) == []
```

- [ ] **Step 2: Run the new test and confirm it fails on current code**

Run:

```bash
python3.11 -m pytest tests/test_source_repository_fetch.py::test_github_url_does_not_become_analyzed_without_fetcher -q
```

Expected before implementation: FAIL because current code marks GitHub URLs `analyzed`.

- [ ] **Step 3: Add failing test for local bare repo fake GitHub clone path**

Append to `tests/test_source_repository_fetch.py`:

```python
import subprocess
from pathlib import Path


class LocalMirrorFetcher:
    def __init__(self, mirror: Path) -> None:
        self.mirror = mirror

    def fetch(self, url: str, cache_root: Path, timeout_seconds: int = 30):
        from ariadne_ltb.application.source_repository import SourceFetchResult

        checkout = cache_root / "github.com" / "acme" / "mini-agent" / "checkout"
        checkout.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth=1", str(self.mirror), str(checkout)], check=True, capture_output=True)
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout, check=True, text=True, capture_output=True).stdout.strip()
        return SourceFetchResult(
            status="cached",
            source_url=url,
            cache_path=str(checkout),
            commit_sha=commit,
            default_branch="main",
            fetched_ref="main",
            file_count=0,
            warnings=[],
        )


def test_github_url_fetch_creates_repository_understanding_artifact(tmp_path) -> None:
    source_repo = tmp_path / "source-repo"
    source_repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=source_repo, check=True, capture_output=True)
    (source_repo / "README.md").write_text("# Mini Agent\n\nAgent loop with actions, observations, tests, and review.\n", encoding="utf-8")
    (source_repo / "pyproject.toml").write_text("[project]\nname='mini-agent'\n", encoding="utf-8")
    (source_repo / "mini_agent.py").write_text("def main():\n    return 'ok'\n", encoding="utf-8")
    (source_repo / "tests").mkdir()
    (source_repo / "tests" / "test_agent.py").write_text("def test_agent():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=source_repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=source_repo, check=True, capture_output=True)

    store = AriadneStore(tmp_path / "store")
    source = SourceDocument(
        id=stable_id("source", "https://github.com/acme/mini-agent", "mini-agent"),
        source_type=SourceType.GITHUB_REPO,
        title="acme/mini-agent",
        path_or_url="https://github.com/acme/mini-agent",
        content_hash=sha256(b"mini-agent").hexdigest(),
        summary="Reference repository.",
        metadata={"source_role": "reference_project"},
    )
    store.save_source_document(source)

    result = SourceAnalysisService(store, repository_fetcher=LocalMirrorFetcher(source_repo)).analyze_source(source.id)
    reloaded = store.load_source_document(source.id)
    artifacts = store.list_source_artifacts(source.id)
    payload = store.load_source_artifact_payload(artifacts[0].id)

    assert result.status == "analyzed"
    assert reloaded.metadata["analysis_status"] == "analyzed"
    assert reloaded.metadata["snapshot"]["commit_sha"]
    assert artifacts[0].artifact_type == "repository_understanding"
    assert payload["identity"]["remote_url"] == "https://github.com/acme/mini-agent"
    assert payload["tests"]["paths"] == ["tests/test_agent.py"]
    assert "pyproject.toml" in payload["manifests"]
```

- [ ] **Step 4: Run the repo fetch tests**

Run:

```bash
python3.11 -m pytest tests/test_source_repository_fetch.py -q
```

Expected before implementation: FAIL because `source_repository.py` and `repository_understanding` do not exist.

---

## Task 2: Add Source Fetch Record and Artifact Types

**Files:**

- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/mappers.py`
- Modify: `frontend/ariadne-workbench/src/shared/api/types.ts`
- Test: `tests/test_source_repository_fetch.py`

- [ ] **Step 1: Add source fetch and artifact models**

In `ariadne_ltb/models.py`, add:

```python
class SourceAnalysisStatus(str, Enum):
    PENDING = "pending"
    RESOLVING = "resolving"
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class SourceFetchRecord(AriadneModel):
    id: str
    source_document_id: str
    source_url: str
    status: Literal["cached", "linked", "blocked"]
    cache_path: str | None = None
    commit_sha: str | None = None
    default_branch: str | None = None
    fetched_ref: str | None = None
    file_count: int = 0
    byte_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: str = Field(default_factory=utc_now)
```

Expand `SourceArtifact.artifact_type` to:

```python
artifact_type: Literal[
    "knowledge_card",
    "text_understanding",
    "reference_project_profile",
    "repository_understanding",
    "codebase_snapshot",
    "target_codebase_snapshot",
    "execution_feedback",
    "review_feedback",
]
```

Do not add `route_decision` or `handoff_packet` to `SourceArtifact`; those are execution artifacts, not source-understanding artifacts.

- [ ] **Step 2: Add storage methods**

In `ariadne_ltb/storage.py`, add methods:

Store records under:

```text
.ariadne/sources/fetch_records.jsonl
```

Implementation requirements:

- `save_source_fetch_record(record)` appends `record.model_dump(mode="json")` as one JSONL line and returns the same record.
- `list_source_fetch_records(source_document_id=None)` reads the JSONL file, validates each line as `SourceFetchRecord`, ignores malformed blank lines only if existing JSONL readers in `AriadneStore` already do so, and filters by source id when provided.
- `latest_source_fetch_record(source_document_id)` returns the newest record for that source by `created_at`, or `None` if no record exists.

- [ ] **Step 3: Expose fetch fields to API**

Add `SourceFetchRecordDTO` to `ariadne_ltb/application/dtos.py`:

```python
class SourceFetchRecordDTO(AriadneDTO):
    id: str
    source_document_id: str
    source_url: str
    status: str
    cache_path: str | None = None
    commit_sha: str | None = None
    default_branch: str | None = None
    fetched_ref: str | None = None
    file_count: int = 0
    byte_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: str
```

Add `source_fetch_records: list[SourceFetchRecordDTO]` to the workbench DTO.

- [ ] **Step 4: Update frontend API type**

In `frontend/ariadne-workbench/src/shared/api/types.ts`, add:

```ts
export type ApiSourceFetchRecord = {
  id: string;
  source_document_id: string;
  source_url: string;
  status: "cached" | "linked" | "blocked";
  cache_path?: string | null;
  commit_sha?: string | null;
  default_branch?: string | null;
  fetched_ref?: string | null;
  file_count: number;
  byte_count: number;
  warnings: string[];
  error?: string | null;
  created_at: string;
};
```

And add it to `ApiWorkbench`.

- [ ] **Step 5: Run focused tests**

Run:

```bash
python3.11 -m pytest tests/test_source_repository_fetch.py -q
ruff check ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/application/dtos.py ariadne_ltb/application/mappers.py
```

Expected: tests may still fail until fetch/scanner exists; ruff should pass.

---

## Task 3: Implement Repository Resolver, Fetcher, and Scanner

**Files:**

- Create: `ariadne_ltb/application/source_repository.py`
- Create: `ariadne_ltb/application/repository_scanner.py`
- Modify: `ariadne_ltb/application/source_analysis.py`
- Test: `tests/test_source_repository_fetch.py`
- Test: `tests/test_repository_scanner.py`

- [ ] **Step 1: Implement GitHub URL normalization and fetch interface**

Create `ariadne_ltb/application/source_repository.py`:

```python
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.models import SourceFetchRecord, stable_id


GITHUB_RE = re.compile(r"^https://github\\.com/([^/]+)/([^/#?]+?)(?:\\.git)?/?(?:[#?].*)?$")


@dataclass(frozen=True)
class GitHubRepoRef:
    owner: str
    repo: str
    url: str


@dataclass(frozen=True)
class SourceFetchResult:
    status: str
    source_url: str
    cache_path: str | None
    commit_sha: str | None
    default_branch: str | None
    fetched_ref: str | None
    file_count: int
    warnings: list[str]
    error: str | None = None


def parse_github_url(value: str) -> GitHubRepoRef | None:
    match = GITHUB_RE.match(value.strip())
    if not match:
        return None
    owner, repo = match.groups()
    repo = repo.removesuffix(".git")
    return GitHubRepoRef(owner=owner, repo=repo, url=f"https://github.com/{owner}/{repo}")


class GitRepositoryFetcher:
    def fetch(self, url: str, cache_root: Path, timeout_seconds: int = 45) -> SourceFetchResult:
        ref = parse_github_url(url)
        if ref is None:
            return SourceFetchResult("blocked", url, None, None, None, None, 0, [], "unsupported_git_url")
        checkout = cache_root / "github.com" / ref.owner / ref.repo / "checkout"
        try:
            if checkout.exists() and (checkout / ".git").exists():
                subprocess.run(["git", "fetch", "--depth=1", "origin"], cwd=checkout, timeout=timeout_seconds, check=True, capture_output=True)
            else:
                checkout.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "clone", "--depth=1", "--filter=blob:none", ref.url, str(checkout)], timeout=timeout_seconds, check=True, capture_output=True)
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout, check=True, text=True, capture_output=True).stdout.strip()
            branch = subprocess.run(["git", "branch", "--show-current"], cwd=checkout, check=True, text=True, capture_output=True).stdout.strip() or None
            file_count = sum(1 for path in checkout.rglob("*") if path.is_file() and ".git" not in path.parts)
            return SourceFetchResult("cached", ref.url, str(checkout), commit, branch, branch, file_count, [])
        except subprocess.TimeoutExpired:
            return SourceFetchResult("blocked", ref.url, None, None, None, None, 0, [], "repository_fetch_timeout")
        except (OSError, subprocess.CalledProcessError) as exc:
            return SourceFetchResult("blocked", ref.url, None, None, None, None, 0, [], f"repository_fetch_failed:{type(exc).__name__}")


def fetch_record_from_result(source_id: str, result: SourceFetchResult) -> SourceFetchRecord:
    return SourceFetchRecord(
        id=stable_id("source_fetch", source_id, result.source_url, result.commit_sha or result.error or result.status),
        source_document_id=source_id,
        source_url=result.source_url,
        status=result.status,  # type: ignore[arg-type]
        cache_path=result.cache_path,
        commit_sha=result.commit_sha,
        default_branch=result.default_branch,
        fetched_ref=result.fetched_ref,
        file_count=result.file_count,
        warnings=result.warnings,
        error=result.error,
    )
```

- [ ] **Step 2: Implement read-only scanner**

Create `ariadne_ltb/application/repository_scanner.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

IGNORE_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".venv", "__pycache__", ".ruff_cache", ".pytest_cache"}
MANIFESTS = ["pyproject.toml", "package.json", "go.mod", "Cargo.toml", "requirements.txt", "uv.lock"]


@dataclass(frozen=True)
class RepositoryScan:
    summary: str
    top_level: list[str]
    manifests: list[str]
    test_paths: list[str]
    entrypoints: list[str]
    selected_files: list[str]
    warnings: list[str] = field(default_factory=list)


def scan_repository(root: Path, *, max_files: int = 3000, max_selected_files: int = 40) -> RepositoryScan:
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(str(root))
    all_files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.is_file():
            all_files.append(path)
        if len(all_files) > max_files:
            break
    rel_files = [path.relative_to(root).as_posix() for path in all_files]
    top_level = sorted({Path(item).parts[0] for item in rel_files if Path(item).parts})
    manifests = sorted(item for item in rel_files if Path(item).name in MANIFESTS)
    test_paths = sorted(item for item in rel_files if _is_test_file(item))
    entrypoints = sorted(item for item in rel_files if _is_entrypoint(item))
    selected = _select_files(rel_files, manifests, test_paths, entrypoints, max_selected_files)
    summary = _read_readme(root) or f"Repository with {len(rel_files)} readable files."
    warnings = ["scan_file_limit_hit"] if len(all_files) > max_files else []
    return RepositoryScan(summary, top_level, manifests, test_paths, entrypoints, selected, warnings)


def _read_readme(root: Path) -> str:
    for name in ["README.md", "readme.md", "README.rst"]:
        path = root / name
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")[:1200]
    return ""


def _is_test_file(path: str) -> bool:
    p = Path(path)
    return "tests" in p.parts or p.name.startswith("test_") or p.name.endswith(".test.ts") or p.name.endswith(".spec.ts")


def _is_entrypoint(path: str) -> bool:
    name = Path(path).name
    return name in {"main.py", "cli.py", "__main__.py", "index.ts", "index.js", "main.ts", "main.js"}


def _select_files(rel_files: list[str], manifests: list[str], tests: list[str], entrypoints: list[str], limit: int) -> list[str]:
    ordered = []
    for bucket in [["README.md", "readme.md"], manifests, entrypoints, tests[:10], rel_files[:20]]:
        for item in bucket:
            if item in rel_files and item not in ordered:
                ordered.append(item)
    return ordered[:limit]


def infer_test_commands(manifests: list[str], test_paths: list[str]) -> list[str]:
    if not test_paths:
        return []
    if "pyproject.toml" in manifests or "requirements.txt" in manifests:
        return ["python3.11 -m pytest"]
    if "package.json" in manifests:
        return ["npm test"]
    if "go.mod" in manifests:
        return ["go test ./..."]
    if "Cargo.toml" in manifests:
        return ["cargo test"]
    return ["python3.11 -m pytest"]
```

- [ ] **Step 3: Add scanner tests**

Create `tests/test_repository_scanner.py`:

```python
from __future__ import annotations

from ariadne_ltb.application.repository_scanner import scan_repository


def test_repository_scanner_reads_python_and_node_signals(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Agent\n\nLoop with actions and observations.", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='agent'\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest"}}', encoding="utf-8")
    (tmp_path / "agent").mkdir()
    (tmp_path / "agent" / "cli.py").write_text("def main(): pass\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_cli.py").write_text("def test_cli(): assert True\n", encoding="utf-8")

    scan = scan_repository(tmp_path)

    assert "pyproject.toml" in scan.manifests
    assert "package.json" in scan.manifests
    assert "agent/cli.py" in scan.entrypoints
    assert "tests/test_cli.py" in scan.test_paths
    assert "README.md" in scan.selected_files
```

- [ ] **Step 4: Integrate into `SourceAnalysisService`**

Modify `SourceAnalysisService.__init__`:

```python
def __init__(
    self,
    store: AriadneStore,
    fetcher: SourceFetcher | None = None,
    repository_fetcher: GitRepositoryFetcher | None = None,
) -> None:
    self.store = store
    self.fetcher = fetcher or RequestsSourceFetcher()
    self.repository_fetcher = repository_fetcher or GitRepositoryFetcher()
```

Modify GitHub path handling:

```python
if source.source_type is SourceType.GITHUB_REPO and source.path_or_url.startswith("https://github.com/"):
    return self._analyze_github_repository(source)
```

Implement `_analyze_github_repository()`:

```python
def _analyze_github_repository(self, source: SourceDocument) -> SourceAnalysisResult:
    cache_root = self.store.root / ".ariadne" / "sources" / "git"
    fetch_result = self.repository_fetcher.fetch(source.path_or_url, cache_root)
    self.store.save_source_fetch_record(fetch_record_from_result(source.id, fetch_result))
    if fetch_result.status != "cached" or not fetch_result.cache_path:
        self._update_source_metadata(source, {"analysis_status": "blocked", "analysis_error": fetch_result.error or "repository_fetch_failed"})
        return SourceAnalysisResult(source.id, "blocked", [], [], fetch_result.error)
    return self._analyze_repository_path(source, Path(fetch_result.cache_path), remote_url=fetch_result.source_url, commit_sha=fetch_result.commit_sha)
```

- [ ] **Step 5: Split local path repo scan into `_analyze_repository_path`**

Move current `_analyze_reference_project` body into:

```python
def _analyze_repository_path(
    self,
    source: SourceDocument,
    repo_path: Path,
    *,
    remote_url: str | None = None,
    commit_sha: str | None = None,
) -> SourceAnalysisResult:
    scan = scan_repository(repo_path)
    evidence = self._save_evidence(
        source,
        artifact_id=None,
        locator="README.md" if (repo_path / "README.md").exists() else str(repo_path),
        quote_or_summary=scan.summary[:240],
        claim="repository structure informs target project issue generation",
    )
    payload = {
        "repo_summary": scan.summary,
        "identity": {
            "name": repo_path.name,
            "remote_url": remote_url or source.path_or_url,
            "commit_sha": commit_sha or _git_commit(repo_path),
        },
        "manifests": scan.manifests,
        "entrypoints": scan.entrypoints,
        "repo_map": {"top_level": scan.top_level, "selected_files": scan.selected_files},
        "tests": {"paths": scan.test_paths, "commands": infer_test_commands(scan.manifests, scan.test_paths)},
        "behavior_patterns": _behavior_patterns(scan.summary, scan.entrypoints, scan.test_paths),
        "reuse_notes": ["Reuse architecture ideas and task decomposition, not source code."],
        "avoid_notes": ["Do not copy implementation files directly from the reference project."],
        "scan_warnings": scan.warnings,
    }
    artifact = self._save_artifact(source, "repository_understanding", payload, [evidence.id])
```

Keep `reference_project_profile` as legacy alias only if loading old data; new repo scans should write `repository_understanding`.

- [ ] **Step 6: Run focused tests**

Run:

```bash
python3.11 -m pytest tests/test_repository_scanner.py tests/test_source_repository_fetch.py tests/test_source_analysis.py -q
ruff check ariadne_ltb/application/source_repository.py ariadne_ltb/application/repository_scanner.py ariadne_ltb/application/source_analysis.py
```

Expected: PASS.

---

## Task 4: Make Issue Factory Consume Typed Artifacts

**Files:**

- Create: `ariadne_ltb/application/issue_compiler.py`
- Modify: `ariadne_ltb/application/issue_factory.py`
- Modify: `ariadne_ltb/application/issue_delta_validation.py`
- Modify: `tests/test_issue_factory_compiler.py`
- Modify: `tests/test_web_dogfood_product_path.py`

- [ ] **Step 1: Add compiler input/output helpers**

Create `ariadne_ltb/application/issue_compiler.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ariadne_ltb.application.build_context import IssueFactoryContext
from ariadne_ltb.models import SourceArtifact, SourceEvidence
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class CompiledIssueSpec:
    title: str
    reason: str
    priority: str
    affected_modules: list[str]
    acceptance_criteria: list[str]
    evidence_refs: list[str]
    owner_agent: str = "Build Lead"
    build_decision: str = "code_task"
    risks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


def compile_issue_specs(store: AriadneStore, *, title: str, north_star: str, context: IssueFactoryContext) -> list[CompiledIssueSpec]:
    artifact_payloads = [(artifact, store.load_source_artifact_payload(artifact.id)) for artifact in context.artifacts]
    if _is_mini_code_context(title, north_star, artifact_payloads):
        return _compile_mini_code_agent_specs(context.evidence, artifact_payloads)
    return _compile_generic_specs(title, context.evidence, artifact_payloads)
```

In the same file, add deterministic helpers:

```python
def _is_mini_code_context(title: str, north_star: str, artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]]) -> bool:
    haystack = " ".join([title, north_star, *[str(payload)[:2000] for _, payload in artifact_payloads]]).lower()
    return any(token in haystack for token in ["mini code", "mini-code", "mini-swe", "minimal agent", "code agent", "coding assistant"])


def _evidence_ids(evidence: list[SourceEvidence]) -> list[str]:
    return [item.id for item in evidence] or ["human_goal"]


def _repo_capability_text(artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]]) -> str:
    parts: list[str] = []
    for _, payload in artifact_payloads:
        parts.extend(str(item) for item in payload.get("behavior_patterns", []))
        parts.extend(str(item) for item in payload.get("entrypoints", []))
        tests = payload.get("tests") or {}
        if isinstance(tests, dict):
            parts.extend(str(item) for item in tests.get("paths", []))
    return "; ".join(parts)[:600]


def _spec(title: str, reason: str, modules: list[str], evidence: list[SourceEvidence], priority: str = "high") -> CompiledIssueSpec:
    return CompiledIssueSpec(
        title=title,
        reason=reason,
        priority=priority,
        affected_modules=modules,
        acceptance_criteria=[
            "The implementation is reachable from the Web Workbench product path.",
            "The behavior writes inspectable run evidence.",
            "Tests cover the behavior without external credentials.",
        ],
        evidence_refs=_evidence_ids(evidence),
        risks=["Keep the issue small enough for one Codex or Claude Code pass."],
        assumptions=["The target project is managed from Ariadne as a local project folder."],
    )


def _compile_mini_code_agent_specs(
    evidence: list[SourceEvidence],
    artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]],
) -> list[CompiledIssueSpec]:
    capability_text = _repo_capability_text(artifact_payloads) or "reference sources describe compact code-agent loops"
    return [
        _spec("Bootstrap Python package and CLI", f"Reference inputs indicate a CLI-first agent shape: {capability_text}", ["pyproject.toml", "mini_code_agent/__main__.py", "mini_code_agent/cli.py", "tests/test_cli.py"], evidence),
        _spec("Add DeepSeek-backed LLM client configuration", "The target agent needs a real upstream model client and local configuration path.", ["mini_code_agent/llm.py", "mini_code_agent/config.py", "tests/test_llm_config.py"], evidence),
        _spec("Define tool protocol and model action schema", "Reference code-agent projects converge on typed action and observation contracts.", ["mini_code_agent/protocol.py", "tests/test_protocol.py"], evidence),
        _spec("Implement shell command tool with allowlist", "Coding agents need shell access bounded by an explicit local safety policy.", ["mini_code_agent/tools/shell.py", "tests/test_shell_tool.py"], evidence),
        _spec("Implement file read and patch tools with review-before-write safety", "A useful code agent needs file operations without uncontrolled writes.", ["mini_code_agent/tools/files.py", "tests/test_file_tools.py"], evidence),
        _spec("Implement agent loop: prompt -> action -> observation -> repeat", "The core agent behavior is the action/observation loop extracted from references.", ["mini_code_agent/agent_loop.py", "tests/test_agent_loop.py"], evidence),
        _spec("Persist session trace and run summary", "AI Builders need inspectable trajectories to debug agent behavior.", ["mini_code_agent/trace.py", "tests/test_trace.py"], evidence, "medium"),
        _spec("Capture git diff and test result", "A code agent run is not reviewable unless it records diff and tests.", ["mini_code_agent/evidence.py", "tests/test_evidence.py"], evidence),
        _spec("Add minimal reviewer checks for task completion", "A conservative reviewer pass is needed before a run is usable.", ["mini_code_agent/reviewer.py", "tests/test_reviewer.py"], evidence, "medium"),
        _spec("Write README quickstart and usage examples", "The first version needs a runnable local quickstart.", ["README.md", "docs/quickstart.md"], evidence, "medium"),
    ]


def _compile_generic_specs(
    title: str,
    evidence: list[SourceEvidence],
    artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]],
) -> list[CompiledIssueSpec]:
    modules = _target_modules_from_artifacts(artifact_payloads)
    return [
        _spec(f"Define product contract for {title}", "Compile the goal and selected sources into a concrete implementation contract.", ["docs/product/contract.md"], evidence),
        _spec(f"Implement first vertical slice for {title}", "Build the smallest end-to-end version supported by the source evidence.", modules or ["src/", "tests/"], evidence),
        _spec(f"Add run evidence and review loop for {title}", "Record diff, tests, review verdict, and next issue suggestions for future iterations.", ["src/evidence", "tests/"], evidence, "medium"),
    ]


def _target_modules_from_artifacts(artifact_payloads: list[tuple[SourceArtifact, dict[str, Any]]]) -> list[str]:
    modules: list[str] = []
    for _, payload in artifact_payloads:
        repo_map = payload.get("repo_map") or {}
        if isinstance(repo_map, dict):
            modules.extend(str(item) for item in repo_map.get("selected_files", [])[:6])
    return modules
```

This is still a v1 deterministic adapter, not a general AI planner. The important improvement is that issue reasons and module choices are derived from typed artifact signals and evidence, not only from goal/source title keywords.

- [ ] **Step 2: Replace `_mini_code_agent_tasks()` direct call**

In `IssueFactoryService._operations`, replace:

```python
tasks = _mini_code_agent_tasks() if _is_mini_code_context(title, north_star, context) else _generic_tasks(title)
```

with:

```python
tasks = compile_issue_specs(self.store, title=title, north_star=north_star, context=context)
```

Then adapt loop to `CompiledIssueSpec`.

- [ ] **Step 3: Strengthen delta validator**

Before generating operations, `assemble_issue_factory_context()` must reject selected sources that have neither analyzed/partial artifacts nor evidence. Add this behavior in `ariadne_ltb/application/build_context.py`:

```python
not_ready = [
    source.id
    for source in sources
    if str(source.metadata.get("analysis_status") or "pending") not in {"analyzed", "partial"}
    or not store.list_source_artifacts(source.id)
]
if not_ready:
    raise ValueError(f"source_not_ready_for_issue_factory:{','.join(not_ready)}")
```

Add a test to `tests/test_issue_factory_compiler.py`:

```python
def test_issue_factory_rejects_unanalyzed_source(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path / "store")
    target = tmp_path / "target"
    target.mkdir()
    store.save_project_resources([store_project_resource(project_id="target_1", path=target, label="Target", issue_prefix="TGT", test_command="python3.11 -m pytest")])
    goal = ProjectGoalService(store).create(
        CreateProjectGoalInput(title="Build Target", north_star="Use sources to create issues.", target_project_id="target_1")
    )
    source_id = _create_source(
        store,
        SourceType.NOTE,
        "unread source",
        "memory://unread",
        "This source has not been analyzed.",
        {"source_role": "requirement_source"},
    )

    with pytest.raises(ValueError, match="source_not_ready_for_issue_factory"):
        IssueFactoryService(store).preview(
            IssueFactoryPreviewInput(goal_id=goal.id, source_ids=[source_id], target_project_id="target_1")
        )
```

In `ariadne_ltb/application/issue_delta_validation.py`, require for `ADD_TICKET`:

```python
required_metadata = [
    "target_project_id",
    "build_context_id",
    "context_fingerprint",
    "source_document_ids",
    "source_artifact_ids",
    "evidence_refs",
    "affected_modules",
    "acceptance_criteria",
]
```

Also reject production operations that mention demo-only paths unless target project label/path is explicitly demo:

```python
for module in metadata.get("affected_modules", []):
    if "demo_todo" in module:
        raise ValueError("demo_path_not_allowed_in_product_issue")
```

- [ ] **Step 4: Update issue factory tests**

In `tests/test_issue_factory_compiler.py`, add assertions:

```python
def test_issue_factory_uses_artifact_payload_not_only_title(tmp_path: Path) -> None:
    store, goal_id, project_id, source_ids = _seed_mini_code_agent_context(tmp_path)
    source = store.load_source_document(source_ids[1])
    artifacts = store.list_source_artifacts(source.id)
    payload = store.load_source_artifact_payload(artifacts[0].id)
    assert "tests" in payload

    preview = IssueFactoryService(store).preview(
        IssueFactoryPreviewInput(goal_id=goal_id, source_ids=source_ids, target_project_id=project_id)
    )

    loop_issue = next(operation for operation in preview.operations if "agent loop" in (operation.title or "").lower())
    assert artifacts[0].id in loop_issue.metadata["source_artifact_ids"]
    assert loop_issue.metadata["evidence_refs"]
    assert "mini_code_agent/agent_loop.py" in loop_issue.metadata["affected_modules"]
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
python3.11 -m pytest tests/test_issue_factory_compiler.py tests/test_web_dogfood_product_path.py -q
ruff check ariadne_ltb/application/issue_compiler.py ariadne_ltb/application/issue_factory.py ariadne_ltb/application/issue_delta_validation.py
```

Expected: PASS.

---

## Task 5: Quarantine Demo Planner Fallbacks

**Files:**

- Modify: `ariadne_ltb/ingest.py`
- Modify: `ariadne_ltb/planner.py`
- Modify: `tests/test_cli_product_defaults.py`
- Modify: `tests/test_v1_planner_quality.py`

- [ ] **Step 1: Find demo-only fallback strings**

Run:

```bash
rg -n "demo_todo|export-json|fake-codex|demo full|Offline regression|fixture" ariadne_ltb tests README.md docs frontend
```

Classify results into:

- test-only allowed;
- offline regression allowed;
- product path prohibited.

- [ ] **Step 2: Gate legacy ingest mapping**

In `ariadne_ltb/ingest.py`, make `demo_todo export-json` only reachable from explicit offline regression fixtures. For product source ingestion, affected modules must be inferred from target project metadata or generated by Issue Factory.

Use a guard:

```python
if metadata.get("entrypoint") != "offline_regression_fixture":
    return []
```

for legacy demo affected modules.

- [ ] **Step 3: Planner consumes build context**

In `ariadne_ltb/planner.py`, when ticket metadata includes `build_context_id`, load referenced source artifacts and evidence. The generated BuildPacket must include:

- target project id;
- source artifact ids;
- evidence refs;
- target-relative affected modules;
- no demo paths unless the target project is a demo fixture.

- [ ] **Step 4: Add tests that production does not emit demo paths**

Add to `tests/test_cli_product_defaults.py`:

```python
def test_product_issue_factory_does_not_emit_demo_todo_paths(tmp_path):
    from hashlib import sha256

    from ariadne_ltb.application.dtos import CreateProjectGoalInput, IssueFactoryPreviewInput
    from ariadne_ltb.application.issue_factory import IssueFactoryService
    from ariadne_ltb.application.project_goals import ProjectGoalService
    from ariadne_ltb.application.source_analysis import SourceAnalysisService
    from ariadne_ltb.models import ProjectResource, SourceDocument, SourceType, stable_id
    from ariadne_ltb.storage import AriadneStore

    store = AriadneStore(tmp_path / "store")
    target = tmp_path / "real-product"
    target.mkdir()
    (target / "README.md").write_text("# real product\n", encoding="utf-8")
    resource = ProjectResource.local_directory("target_real_product", target, label="Real Product").model_copy(
        update={"resource_ref": {"local_path": str(target), "label": "Real Product", "issue_prefix": "RLP"}}
    )
    store.save_project_resources([resource])
    goal = ProjectGoalService(store).create(
        CreateProjectGoalInput(
            title="Build Real Product",
            north_star="Use external inputs to create a real project issue set.",
            target_project_id="target_real_product",
        )
    )
    source = SourceDocument(
        id=stable_id("source", "real", "note"),
        source_type=SourceType.NOTE,
        title="real product note",
        path_or_url="memory://real-product-note",
        content_hash=sha256(b"real product").hexdigest(),
        summary="Build a CLI with tests and inspectable run evidence.",
        metadata={"source_role": "requirement_source", "content": "Build a CLI with tests and inspectable run evidence."},
    )
    store.save_source_document(source)
    SourceAnalysisService(store).analyze_source(source.id)

    preview = IssueFactoryService(store).preview(
        IssueFactoryPreviewInput(goal_id=goal.id, source_ids=[source.id], target_project_id="target_real_product")
    )

    affected = [module for operation in preview.operations for module in operation.metadata["affected_modules"]]
    assert affected
    assert all("demo_todo" not in module for module in affected)
    assert all("export-json" not in module for module in affected)
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
python3.11 -m pytest tests/test_cli_product_defaults.py tests/test_v1_planner_quality.py tests/test_issue_factory_compiler.py -q
```

Expected: PASS.

---

## Task 6: Persist Real Route Decision and Handoff Packet Before Claim

**Files:**

- Create: `ariadne_ltb/application/handoff_packets.py`
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/application/assignment_readiness.py`
- Modify: `ariadne_ltb/application/assign_ticket.py`
- Modify: `ariadne_ltb/application/run_assignment.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Modify: `ariadne_ltb/execution.py`
- Modify: `ariadne_ltb/team.py`
- Test: `tests/test_handoff_packet_readiness.py`
- Test: `tests/test_assignment_claim_state_machine.py`

- [ ] **Step 1: Add HandoffPacket model**

In `ariadne_ltb/models.py`, add:

```python
class HandoffPacket(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    route_decision_id: str
    build_context_id: str | None = None
    target_project_id: str
    target_repo_path: str
    allowed_paths: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    test_command: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    markdown_path: str
    packet_hash: str
    created_at: str = Field(default_factory=utc_now)
```

- [ ] **Step 2: Add handoff packet storage**

In `storage.py`, add:

Persist markdown under:

```text
.ariadne/handoffs/packets/<ticket_key>-<packet_id>.md
```

Implementation requirements:

- `save_handoff_packet(packet, markdown)` writes markdown to `.ariadne/handoffs/packets/<ticket_key>-<packet_id>.md`, stores a JSON index entry under `.ariadne/handoffs/packets/index/<packet_id>.json`, updates `packet.markdown_path`, and returns the persisted packet.
- `load_handoff_packet(packet_id)` reads the JSON index entry and validates it as `HandoffPacket`.
- If the markdown file is missing, store doctor should be able to report a broken handoff packet in a later task; this task only needs persistence and load behavior.

- [ ] **Step 2.5: Make route decisions loadable**

Current route decisions are written as artifacts. Keep that artifact, but add a direct storage index so handoff packets can reference a loadable route decision.

In `storage.py`, add:

- `save_route_decision(route_decision: RouteDecision, artifact_id: str | None = None) -> RouteDecision`
- `load_route_decision(route_decision_id: str) -> RouteDecision`

Persist JSON under:

```text
.ariadne/routes/<route_decision_id>.json
```

The JSON should include the route decision fields plus optional `route_artifact_id`.

- [ ] **Step 3: Create handoff packet writer**

Create `ariadne_ltb/application/handoff_packets.py`:

```python
from __future__ import annotations

from hashlib import sha256

from ariadne_ltb.models import BuildTicket, HandoffPacket, RouteDecision, stable_id
from ariadne_ltb.storage import AriadneStore


def create_handoff_packet(
    store: AriadneStore,
    *,
    ticket: BuildTicket,
    route_decision: RouteDecision,
    target_project_id: str,
    target_repo_path: str,
) -> HandoffPacket:
    criteria = list(ticket.metadata.get("acceptance_criteria") or [])
    affected = list(ticket.metadata.get("affected_modules") or [])
    evidence_refs = list(ticket.metadata.get("evidence_refs") or [])
    markdown = _render_markdown(ticket, route_decision, target_repo_path, criteria, affected, evidence_refs)
    packet_hash = sha256(markdown.encode("utf-8")).hexdigest()
    packet = HandoffPacket(
        id=stable_id("handoff_packet", ticket.id, route_decision.id, packet_hash),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        route_decision_id=route_decision.id,
        build_context_id=str(ticket.metadata.get("build_context_id") or ""),
        target_project_id=target_project_id,
        target_repo_path=target_repo_path,
        allowed_paths=affected,
        forbidden_actions=["Do not commit.", "Do not push.", "Do not copy reference repository source code."],
        acceptance_criteria=criteria,
        test_command=str(ticket.metadata.get("test_command") or "python3.11 -m pytest"),
        evidence_refs=evidence_refs,
        markdown_path="",
        packet_hash=packet_hash,
    )
    return store.save_handoff_packet(packet, markdown)


def _render_markdown(
    ticket: BuildTicket,
    route_decision: RouteDecision,
    target_repo_path: str,
    criteria: list[str],
    affected: list[str],
    evidence_refs: list[str],
) -> str:
    lines = [
        f"# {ticket.key}: {ticket.title}",
        "",
        "## Target Repository",
        target_repo_path,
        "",
        "## Route",
        f"- Backend: `{route_decision.backend_name}`",
        f"- Planner: `{route_decision.planner_name}`",
        "",
        "## Task",
        ticket.description or ticket.summary or ticket.title,
        "",
        "## Allowed Paths",
        *[f"- `{item}`" for item in affected],
        "",
        "## Acceptance Criteria",
        *[f"- {item}" for item in criteria],
        "",
        "## Evidence References",
        *[f"- `{item}`" for item in evidence_refs],
        "",
        "## Forbidden Actions",
        "- Do not commit.",
        "- Do not push.",
        "- Do not copy source code from reference repositories.",
    ]
    return "\n".join(lines).strip() + "\n"
```

- [ ] **Step 4: Stop readiness placeholder synthesis**

In `assignment_readiness.py`, change `readiness_metadata()` so it raises a validation error when `route_decision_id` or `handoff_packet_id` is missing. It must not call `stable_id("route", assignment.id)` or `stable_id("handoff", assignment.id)` as a substitute.

Expected behavior:

```python
if not route_decision_id and not assignment.metadata.get("route_decision_id"):
    raise ValueError("missing_route_decision")
if not handoff_packet_id and not assignment.metadata.get("handoff_packet_id"):
    raise ValueError("missing_handoff_packet")
```

- [ ] **Step 5: Wire build-team route flow**

The current `route_ticket_to_build_team()` calls `prepare_assignment_for_claim()` internally. That means handoff creation cannot happen later in `assign_ticket.py` after `route_ticket_to_build_team()` returns.

Modify `route_ticket_to_build_team()` in `ariadne_ltb/team.py` to accept `target_project_id: str` in addition to `target_repo_path`, and so the order is:

1. resolve lead, implementer, backend, target repo;
2. create `RouteDecision`;
3. write route decision artifact;
4. call `store.save_route_decision(route_decision, artifact_id=route_artifact.id)`;
5. create assignment in non-ready state;
6. create `HandoffPacket` from ticket + route decision + target project id + target repo path;
7. update assignment metadata with route and handoff ids;
8. call `prepare_assignment_for_claim(store, assignment, ticket, route_decision_id=route_decision.id, handoff_packet_id=packet.id, permission_profile_id=route_decision.permission_profile_id, authorization_id=stable_id("runtime_authorization", assignment.id, route_decision.id))`.

`AssignTicketService.assign()` should not attempt to create the packet after route completion. It should rely on `route_ticket_to_build_team()` returning an assignment that is already ready only because route and handoff were persisted first.

For direct agent assignment, use one fixed behavior:

- create the assignment and keep it in `queued` / `awaiting_user_approval`;
- do not call `prepare_assignment_for_claim`;
- do not make it claimable until a later explicit route/handoff preparation endpoint exists.

The product path should prefer build-team assignment so Build Lead owns routing.

- [ ] **Step 5.5: Make runtime consume frozen handoff packets**

Update `ariadne_ltb/application/run_assignment.py`:

- If assignment is already `ready_to_claim`, do not call `prepare_assignment_for_claim()` again.
- If assignment is not ready, require `route_decision_id` and `handoff_packet_id` in metadata before preparing it.
- If either is missing, return a product error instead of synthesizing placeholder readiness.

Update `ariadne_ltb/orchestrator.py` and any `ExecutionContext` construction so:

- when `assignment.metadata["handoff_packet_id"]` exists, load `HandoffPacket`;
- set `ExecutionContext.handoff_file = packet.markdown_path`;
- set `ExecutionContext.handoff_prompt` to the persisted markdown content;
- set `ExecutionContext.target_repo_path = packet.target_repo_path`;
- do not regenerate a conflicting handoff prompt for that assignment.

Update `ariadne_ltb/execution.py`:

- `CodexBackend.write_handoff_file()` should not overwrite an existing `context.handoff_file` when it points to a persisted `HandoffPacket` markdown file; it should verify the file exists and return it.
- If the file is missing, return a blocked `ExecutionResult` with `FailureReason.INVALID_RESOURCE`.

- [ ] **Step 6: Add tests**

Create `tests/test_handoff_packet_readiness.py`:

```python
def test_assignment_cannot_be_ready_without_route_and_handoff(tmp_path):
    from ariadne_ltb.application.assignment_readiness import prepare_assignment_for_claim
    from ariadne_ltb.models import AgentProfile, BuildTicket, SourceType
    from ariadne_ltb.storage import AriadneStore

    store = AriadneStore(tmp_path)
    ticket = BuildTicket(
        id="ticket_1",
        key="MCA-001",
        title="Bootstrap package",
        source_type=SourceType.NOTE,
        source_ref="memory://note",
        status="planning",
        priority="high",
    )
    store.save_ticket(ticket)
    agent = AgentProfile(id="codex-agent", name="Codex", role="implementer", backend_name="codex")
    store.save_agent_profiles([agent])
    assignment = store.create_assignment(ticket, agent, backend_name="codex")

    try:
        prepare_assignment_for_claim(store, assignment, ticket)
    except ValueError as exc:
        assert "missing_route_decision" in str(exc)
    else:
        raise AssertionError("assignment became ready without route/handoff")
```

Add an end-to-end assignment test:

```python
def test_build_team_assignment_persists_route_and_handoff_before_ready(tmp_path):
    from ariadne_ltb.application.assign_ticket import AssignTicketService
    from ariadne_ltb.application.dtos import AssignTicketInput
    from ariadne_ltb.models import AssignmentStatus
    from tests.test_issue_factory_compiler import _seed_mini_code_agent_context

    store, goal_id, project_id, source_ids = _seed_mini_code_agent_context(tmp_path)
    preview = IssueFactoryService(store).preview(
        IssueFactoryPreviewInput(goal_id=goal_id, source_ids=source_ids, target_project_id=project_id)
    )
    applied = IssueFactoryService(store).apply(preview.id)
    ticket_id = applied.created_ticket_ids[0]
    ticket = store.load_ticket(ticket_id)

    result = AssignTicketService(store).assign(
        ticket.key,
        AssignTicketInput(
            assignee_kind="build_team",
            assignee_id="default",
            backend_name="codex",
            target_project_id=project_id,
            runtime_profile="production",
            idempotency_key="assign-mca-001",
        ),
    )

    assignment = store.load_assignment(result.assignment.id)
    assert assignment.status is AssignmentStatus.READY_TO_CLAIM
    assert assignment.metadata["route_decision_id"]
    assert assignment.metadata["handoff_packet_id"]
    packet = store.load_handoff_packet(assignment.metadata["handoff_packet_id"])
    markdown = Path(packet.markdown_path).read_text(encoding="utf-8")
    assert ticket.title in markdown
    assert packet.target_project_id == project_id
    assert packet.acceptance_criteria
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
python3.11 -m pytest tests/test_handoff_packet_readiness.py tests/test_assignment_claim_state_machine.py tests/test_assign_ticket_service.py -q
ruff check ariadne_ltb/application/handoff_packets.py ariadne_ltb/application/assignment_readiness.py ariadne_ltb/application/assign_ticket.py
```

Expected: PASS.

---

## Task 7: Update Workbench Source-to-Issue UX

**Files:**

- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Modify: `frontend/ariadne-workbench/src/features/project-inputs/model.ts`
- Modify: `frontend/ariadne-workbench/src/shared/api/client.ts`
- Modify: `frontend/ariadne-workbench/src/shared/api/types.ts`
- Modify: `frontend/ariadne-workbench/src/styles.css`
- Modify: `tests/test_frontend_api_contract_static.py`

- [ ] **Step 1: Make source states truthful**

In `sourceAnalysisLabel`, add:

```ts
resolving: "解析中",
fetching: "抓取中",
partial: "部分完成",
blocked: "已阻塞",
```

Replace "分析完成" display for GitHub repo with a compound display:

```text
已缓存 commit abc123 · 已读取 README / manifest / tests
```

If no fetch record exists for GitHub repo:

```text
已添加，尚未抓取仓库
```

- [ ] **Step 2: Add source progress timeline**

In `ProjectInputsPage`, render a source timeline from `data.sourceEvents` and fetch records:

```tsx
<section className="source-timeline">
  <h3>处理过程</h3>
  {events.map((event) => (
    <div className="timeline-row" key={event.id}>
      <span>{event.label}</span>
      <time>{event.createdAt}</time>
    </div>
  ))}
</section>
```

`source_events` already exists in the Workbench projection. If it does not contain fetch-level events, synthesize display rows from `source_fetch_records`, source metadata, and artifact creation time in the frontend adapter. Do not add a second event store unless implementation proves it is necessary.

- [ ] **Step 3: Add human-readable evidence mapping**

When showing task suggestions, map each `evidence_ref` to:

- source title;
- locator;
- claim;
- quote_or_summary;
- confidence.

Do not show raw evidence ids as the primary text.

- [ ] **Step 4: Replace fake source actions**

For actions that currently only update local state:

- `标记重要`
- `忽略`
- `重新分析`

Either connect them to API endpoints or disable them with visible text:

```text
此动作还未接入后端
```

Do not leave clickable buttons that only mutate local UI text.

- [ ] **Step 5: Add clear CTA sequence**

The Sources page must show the current next action:

```text
1. 添加并分析
2. 查看任务建议
3. 应用任务变更
4. 打开新任务
5. 分配给智能体
```

Only enable a CTA when prerequisites are satisfied.

- [ ] **Step 6: Add static frontend guards**

In `tests/test_frontend_api_contract_static.py`, add:

```python
def test_sources_page_does_not_label_unfetched_github_as_analyzed():
    app = Path("frontend/ariadne-workbench/src/App.tsx").read_text()
    assert "尚未抓取仓库" in app
    assert "处理过程" in app


def test_frontend_has_source_fetch_record_type():
    types = Path("frontend/ariadne-workbench/src/shared/api/types.ts").read_text()
    assert "ApiSourceFetchRecord" in types
    assert "source_fetch_records" in types
```

- [ ] **Step 7: Build frontend**

Run:

```bash
cd frontend/ariadne-workbench && npm run build
```

Expected: PASS.

---

## Task 8: HTTP Contract and Error Recovery

**Files:**

- Modify: `ariadne_ltb/interfaces/http/routes.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/web_sources.py`
- Modify: `frontend/ariadne-workbench/src/shared/api/client.ts`
- Test: `tests/test_web_source_auto_analysis.py`
- Test: `tests/test_issue_factory_http_errors.py`

- [ ] **Step 1: Add explicit reanalyze endpoint behavior**

Ensure:

```http
POST /api/sources/{source_id}/analyze
```

returns:

```json
{
  "result": {
    "status": "analyzed|partial|blocked",
    "artifact_ids": [],
    "evidence_ids": [],
    "error": null
  },
  "source": {},
  "fetch_records": [],
  "artifacts": [],
  "evidence": []
}
```

- [ ] **Step 2: Add target project stable id to register request**

In `RegisterTargetProjectInput`, add:

```python
target_project_id: str | None = None
issue_prefix: str | None = None
```

Route it into `TargetProjectRegistry.register` by passing `target_project_id=payload.target_project_id` and `issue_prefix=payload.issue_prefix`.

- [ ] **Step 3: Improve HTTP errors**

Keep stale preview as `409`, and add product errors for:

- `repository_fetch_failed`;
- `source_not_ready_for_issue_factory`;
- `missing_route_decision`;
- `missing_handoff_packet`.

Each should return JSON with:

```json
{
  "code": "repository_fetch_failed",
  "message": "Ariadne could not fetch this repository. Check the URL, credentials, or network access and try again.",
  "details": {}
}
```

- [ ] **Step 4: Frontend error parser**

In `client.ts`, parse API error JSON:

```ts
export async function parseApiError(response: Response): Promise<string> {
  const text = await response.text();
  try {
    const body = JSON.parse(text);
    if (body.message) return body.message;
    if (body.detail?.message) return body.detail.message;
    if (Array.isArray(body.detail)) return "表单字段不完整或格式不正确。";
  } catch {
    return text || response.statusText;
  }
  return response.statusText;
}
```

- [ ] **Step 5: Run HTTP tests**

Run:

```bash
python3.11 -m pytest tests/test_web_source_auto_analysis.py tests/test_issue_factory_http_errors.py -q
```

Expected: PASS.

---

## Task 9: Browser Dogfood Acceptance

**Files:**

- Modify: `docs/dogfood/results/2026-06-19-mini-code-agent-source-to-issue-browser-result.md`
- Modify: `docs/development_report.md`

- [ ] **Step 1: Start latest Workbench**

Run:

```bash
screen -S ariadne-workbench-8768 -X quit 2>/dev/null || true
screen -dmS ariadne-workbench-8768 zsh -lc 'cd /Users/martinlos/code/Ariadne && python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8768 > /tmp/ariadne-workbench-8768.log 2>&1'
```

Open:

```text
http://127.0.0.1:8768/?v=real-source-compiler#sources
```

- [ ] **Step 2: Dogfood from browser only**

Using browser UI only:

1. Create or select target project:
   - path: `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`
   - label: `Mini Code Agent`
   - issue prefix: `MCA`
   - test command: `python3.11 -m pytest`
2. Create goal:
   - title: `Build Mini Code Agent v0.1`
   - north star: `A local AI Builder can give a project goal and external references; Ariadne generates issues and routes them to Codex or Claude.`
3. Add sources:
   - `https://github.com/SWE-agent/mini-swe-agent/`
   - `https://github.com/LiuMengxuan04/MiniCode`
   - `https://minimal-agent.com/`
4. Confirm the page shows:
   - fetch/cache status for GitHub repos;
   - commit SHA or blocked reason;
   - user-facing text saying the repository was fetched and read;
   - user-facing text saying the blog/document was understood;
   - developer details can show typed artifact type `repository_understanding` / `text_understanding` / `knowledge_card`;
   - evidence locator and claim;
   - task suggestions with MCA keys.
5. Apply issue delta.
6. Open `MCA-001`.
7. Assign to build team using Codex or Claude backend.
8. Confirm assignment is not `ready_to_claim` unless route decision and handoff packet exist.

- [ ] **Step 3: Record honest result**

Update:

```text
docs/dogfood/results/2026-06-19-mini-code-agent-source-to-issue-browser-result.md
```

Include:

- what ran from browser;
- whether GitHub repos were truly fetched;
- cache path;
- commit SHA;
- artifacts generated;
- issue keys generated;
- route decision id;
- handoff packet id;
- assignment status;
- blockers.

- [ ] **Step 4: Do not claim real Codex/Claude execution unless it actually ran**

If runtime gates block execution, write:

```text
Codex/Claude execution was not run. Blocker: <exact blocker>.
```

Do not turn a blocked state into a success statement.

---

## Task 10: Full Verification and Branch Handling

**Files:**

- Modify: `docs/development_report.md`
- No code files unless previous tasks require fixes.

- [ ] **Step 1: Run backend tests**

Run:

```bash
python3.11 -m pytest
```

Expected: PASS.

- [ ] **Step 2: Run ruff**

Run:

```bash
ruff check .
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd frontend/ariadne-workbench && npm run build
```

Expected: PASS.

- [ ] **Step 4: Run product smoke commands**

Run:

```bash
python3.11 -m ariadne_ltb.cli backend doctor
python3.11 -m ariadne_ltb.cli export board
```

Expected: PASS.

- [ ] **Step 5: Update development report**

Add a section:

```markdown
## 2026-06-19 Real Source-to-Agent Compiler
```

Include:

- files changed;
- GitHub repo fetch behavior;
- source artifact types;
- Issue Factory compiler changes;
- route/handoff readiness changes;
- browser dogfood result;
- commands run;
- known limitations;
- next tickets.

- [ ] **Step 6: Commit and push**

Use a branch:

```bash
git switch -c codex/real-source-to-agent-compiler
git add ariadne_ltb frontend tests docs
git commit -m "feat: compile real source understanding into agent-ready issues"
git push -u origin codex/real-source-to-agent-compiler
```

Open PR:

```bash
gh pr create --repo Hackerismydream/Ariadne --base main --head codex/real-source-to-agent-compiler --title "Compile real source understanding into agent-ready issues" --body-file /tmp/ariadne-real-source-to-agent-compiler-pr.md
```

---

## Acceptance Criteria

The implementation is done only when all of these are true:

- GitHub repo URL no longer becomes `analyzed` without real fetch/cache or an explicit blocked reason.
- GitHub repo analysis creates `repository_understanding`, not generic `knowledge_card`.
- Repo artifacts include remote URL, commit SHA, file/tree summary, manifests, test inventory, entrypoints, scan warnings, and evidence refs.
- Text/blog input still creates a text artifact and evidence.
- Target codebase input still creates a codebase snapshot.
- Issue Factory compiles from `BuildContextManifest` + source artifacts + evidence, not only goal title/source title templates.
- Generated issue operations include target project id, build context id, source document ids, source artifact ids, evidence refs, affected modules, and acceptance criteria.
- Product issue generation does not emit `demo_todo` or `export-json` unless explicitly in offline regression fixtures.
- Assignment cannot enter `ready_to_claim` with synthesized route/handoff placeholder ids.
- Build-team assignment persists real route decision and immutable handoff packet.
- Workbench Sources page shows truthful fetch/analyze state, timeline, readable evidence, and next CTA.
- Browser dogfood can go from project goal + external inputs to MCA issue set without direct CLI intervention.
- Automated tests pass without network, Codex, Claude, DeepSeek, Feishu, or GitHub credentials.

## Known Tradeoffs

- Network-backed GitHub fetch should be product behavior, but automated tests must use local fake fetchers or local git repos.
- `knowledge_card` remains as a legacy/text artifact type to avoid breaking existing data and tests.
- LLM Issue Factory is deliberately not the first implementation step; deterministic compiler must first become truthful and testable.
- Real Codex/Claude execution remains a separate acceptance path after source-to-issue and route/handoff correctness are fixed.

## Recommended Execution Order

1. Task 1 and Task 2 establish failing contracts and models.
2. Task 3 fixes the core GitHub repo truthfulness problem.
3. Task 4 fixes the Issue Factory compiler boundary.
4. Task 5 removes production-path demo leakage.
5. Task 6 fixes agent-ready assignment correctness.
6. Task 7 and Task 8 make the browser experience honest and recoverable.
7. Task 9 proves the flow through dogfood.
8. Task 10 verifies and lands the branch.
