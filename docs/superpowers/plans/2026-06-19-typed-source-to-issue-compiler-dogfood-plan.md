# Typed Source-to-Issue Compiler Dogfood Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Ariadne's Web Workbench product path from a demo-like `Knowledge Card -> hard-coded backlog` flow into a real typed source-to-issue compiler for the Mini Code Agent dogfood project.

**Architecture:** Keep Ariadne ticket-centered and local-first. Extend the existing `SourceDocument`, `BacklogPreview`, `BuildTicket`, `BuildPacket`, `RouteDecision`, `Handoff`, and `TicketAssignment` flow instead of creating a parallel issue system. Typed source analysis and build context stay internal; the user sees only Project, Sources, Task Changes, and Ready to Run.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, JSON/JSONL file store, existing Ariadne Workbench frontend, Playwright/browser QA, pytest.

---

## Product Boundary

This plan covers the missing product chain:

```text
Project folder + goal
  -> external sources
  -> typed source analysis
  -> evidence refs
  -> ephemeral build context manifest
  -> issue delta preview
  -> applied project issue set
  -> route decision
  -> frozen handoff packet
  -> queued assignment ready for runtime
```

This plan intentionally stops before real Codex/Claude execution modifies the target repository. That boundary is deliberate: the implementation must first prove that Ariadne can convert external knowledge and the target codebase state into reviewable, evidence-backed, project-scoped work. The next execution-feedback plan should consume the frozen handoff and ready assignment.

## Product Surface Rule

The Workbench must not expose internal compiler objects as first-class pages.

User-visible pages:

1. `Project`
2. `Sources`
3. `Tasks / Issue Factory`
4. `Ready to Run / Workbench`

Advanced diagnostics may still exist, but the normal dogfood path cannot require the user to understand:

```text
SourceAsset
SourceEvidence
SourceArtifact
ReferenceProjectProfile
CodebaseSnapshot
BuildContext
PatternCard
GapMap
```

Those are implementation details.

## File Structure

Create:

- `ariadne_ltb/application/source_assets.py`
  - Legacy-compatible source asset adapter and source identity helpers.
- `ariadne_ltb/application/source_analysis.py`
  - Typed analyzer service for URL, GitHub repo, local markdown, local folder, and target codebase snapshots.
- `ariadne_ltb/application/build_context.py`
  - Ephemeral issue-factory context assembler and fingerprinting.
- `ariadne_ltb/application/issue_delta_validation.py`
  - Validators for generated `BacklogOperation` objects.
- `tests/test_source_assets.py`
  - Source asset identity, legacy conversion, artifact payload, and evidence invariants.
- `tests/test_source_analysis.py`
  - URL, GitHub, local markdown, target codebase snapshot, and license risk analysis tests.
- `tests/test_issue_factory_compiler.py`
  - Build context to `BacklogPreview` behavior and MCA issue set assertions.
- `tests/test_issue_factory_http_errors.py`
  - Stale preview and invalid preview HTTP behavior.
- `tests/test_assignment_claim_state_machine.py`
  - Project-scoped ready assignment claim rules.

Modify:

- `ariadne_ltb/models.py`
  - Add source-side evidence and artifact models; extend assignment lifecycle states if missing.
- `ariadne_ltb/storage.py`
  - Persist/load source artifacts, evidence refs, and build context manifests.
- `ariadne_ltb/application/web_sources.py`
  - Stop treating user-provided content as ingestion proof; create source records and analysis status.
- `ariadne_ltb/application/issue_factory.py`
  - Replace `_dogfood_tasks()` and `_generic_tasks()` as the main path with compiler output from build context.
- `ariadne_ltb/application/run_assignment.py`
  - Convert Run into explicit assignment readiness state transition.
- `ariadne_ltb/daemon.py`
  - Claim only `ready_to_claim` assignments in the current project/runtime scope.
- `ariadne_ltb/application/daemon_control.py`
  - Pass project/runtime scope into daemon claim loop.
- `ariadne_ltb/orchestrator.py`
  - Do not regenerate route/handoff after claim when an assignment already references frozen route and handoff.
- `ariadne_ltb/interfaces/http/routes.py`
  - Add source analysis endpoints, return 409 for stale preview, and expose ready-to-run state.
- `frontend/ariadne-workbench/src/App.tsx`
  - Collapse product path to Project, Sources, Tasks, Ready to Run.
- `frontend/ariadne-workbench/src/data.ts`
  - Add API types for source analysis status, artifacts, evidence refs, issue reasons, and assignment readiness.
- `tests/test_web_dogfood_product_path.py`
  - Replace weak fixture-style assertions with strict Mini Code Agent web dogfood assertions.
- `tests/test_workbench_daemon_feedback.py`
  - Add project-scoped claim and ready assignment behavior.
- `docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md`
  - Add the refined typed source compiler acceptance boundary.
- `docs/development_report.md`
  - Record that Knowledge Card is no longer the universal source abstraction.

## Internal Data Model

Do not rename every existing object in one pass. Use the current model names where they already exist.

### Source Asset Compatibility

`SourceDocument` remains the persisted compatibility object. Add or normalize these metadata keys:

```json
{
  "source_role": "reference_project",
  "analysis_status": "pending",
  "snapshot": {
    "fetched_at": "2026-06-19T00:00:00+08:00",
    "commit_sha": null,
    "content_hash": "sha256:..."
  },
  "artifact_ids": [],
  "license_risk": "unknown"
}
```

`source_type` continues to represent physical type:

```text
blog
paper
github_repo
local_folder
note
target_codebase
```

`source_role` represents project intent:

```text
reference_project
requirement_source
background_knowledge
design_constraint
implementation_example
target_codebase
```

### SourceEvidence

Add a first-class source-side evidence model. This is not execution evidence.

```python
class SourceEvidence(BaseModel):
    id: str
    source_document_id: str
    artifact_id: str | None = None
    locator: str
    quote_or_summary: str
    claim: str
    confidence: float = Field(ge=0.0, le=1.0)
    content_hash: str
    created_at: datetime
```

Rules:

- `source_document_id` must exist.
- `artifact_id`, when present, must point to a persisted source artifact.
- `quote_or_summary` must be short enough to show in the Workbench.
- Evidence is immutable once written.

### SourceArtifact

Add a typed source artifact model with JSON payload.

```python
class SourceArtifact(BaseModel):
    id: str
    source_document_id: str
    artifact_type: Literal[
        "knowledge_card",
        "reference_project_profile",
        "codebase_snapshot",
    ]
    payload_hash: str
    payload_path: str
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime
```

Allowed v0.1 artifact payloads:

1. `knowledge_card`
2. `reference_project_profile`
3. `codebase_snapshot`

Do not create first-class `PatternCard`, `BuildContext`, `GapMap`, `RepoMap`, or `ReuseAvoidNote` tables. For v0.1:

- repo map lives inside `reference_project_profile.payload["repo_map"]`
- behavior patterns live inside `reference_project_profile.payload["behavior_patterns"]`
- reuse and avoid notes live inside `reference_project_profile.payload["reuse_notes"]` and `payload["avoid_notes"]`
- build context is assembled as an ephemeral read model, with only a light manifest persisted for audit/debug

### BuildContext Manifest

Persist a small manifest only.

```python
class BuildContextManifest(BaseModel):
    id: str
    goal_id: str
    target_project_id: str
    source_document_ids: list[str]
    source_artifact_ids: list[str]
    evidence_ids: list[str]
    codebase_snapshot_artifact_id: str | None
    base_ticket_fingerprint: str
    context_fingerprint: str
    created_at: datetime
```

The full context body can be recomputed from persisted source records and artifacts.

## Task 1: Source Asset Metadata and Evidence Models

**Files:**

- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Create: `ariadne_ltb/application/source_assets.py`
- Test: `tests/test_source_assets.py`

- [ ] **Step 1: Write source asset metadata and evidence tests**

Add tests that define the required behavior before implementation:

```python
def test_legacy_source_document_converts_to_source_asset_metadata(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    source = SourceDocument(
        id="src_legacy",
        source_type=SourceType.GITHUB_REPO,
        title="mini-SWE-agent",
        path_or_url="https://github.com/SWE-agent/mini-SWE-agent",
        content_hash="abc123",
        summary="reference repo",
        metadata={},
    )
    store.save_source_document(source)

    asset = source_asset_from_document(store.load_source_document("src_legacy"))

    assert asset.id == "src_legacy"
    assert asset.kind == "github_repo"
    assert asset.source_role == "reference_project"
    assert asset.snapshot["content_hash"] == "abc123"
    assert asset.analysis_status == "pending"
```

Add a second test:

```python
def test_source_evidence_requires_existing_source(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    evidence = SourceEvidence(
        id="ev_missing",
        source_document_id="missing",
        artifact_id=None,
        locator="README.md#L1-L3",
        quote_or_summary="The project exposes a CLI entrypoint.",
        claim="reference repo has a CLI entrypoint",
        confidence=0.8,
        content_hash="sha256:missing",
        created_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ValueError, match="missing_source_document"):
        store.save_source_evidence(evidence)
```

- [ ] **Step 2: Run source asset tests and verify they fail**

Run:

```bash
pytest tests/test_source_assets.py -v
```

Expected:

```text
NameError: name 'source_asset_from_document' is not defined
```

or missing `SourceEvidence`/storage methods.

- [ ] **Step 3: Implement `SourceAssetView` adapter**

Create `ariadne_ltb/application/source_assets.py`:

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ariadne_ltb.models import SourceDocument


class SourceAssetView(BaseModel):
    id: str
    kind: str
    source_role: str
    title: str
    uri_or_path: str
    analysis_status: str
    snapshot: dict[str, Any] = Field(default_factory=dict)
    artifact_ids: list[str] = Field(default_factory=list)
    license_risk: str = "unknown"


def source_asset_from_document(source: SourceDocument) -> SourceAssetView:
    metadata = source.metadata or {}
    return SourceAssetView(
        id=source.id,
        kind=source.source_type.value,
        source_role=str(metadata.get("source_role") or _default_source_role(source.source_type.value)),
        title=source.title,
        uri_or_path=source.path_or_url,
        analysis_status=str(metadata.get("analysis_status") or "pending"),
        snapshot=dict(metadata.get("snapshot") or {"content_hash": source.content_hash}),
        artifact_ids=list(metadata.get("artifact_ids") or []),
        license_risk=str(metadata.get("license_risk") or "unknown"),
    )


def _default_source_role(source_type: str) -> str:
    if source_type == "github_repo":
        return "reference_project"
    if source_type == "target_codebase":
        return "target_codebase"
    return "background_knowledge"
```

- [ ] **Step 4: Add `SourceEvidence` and `SourceArtifact` models**

Add models to `ariadne_ltb/models.py` near source models. Use the exact fields from the Internal Data Model section.

- [ ] **Step 5: Add storage methods**

Add methods to `AriadneStore`:

```python
def save_source_evidence(self, evidence: SourceEvidence) -> None
def load_source_evidence(self, evidence_id: str) -> SourceEvidence
def list_source_evidence(self, source_document_id: str | None = None) -> list[SourceEvidence]
def save_source_artifact(self, artifact: SourceArtifact, payload: dict[str, Any]) -> None
def load_source_artifact(self, artifact_id: str) -> SourceArtifact
def load_source_artifact_payload(self, artifact_id: str) -> dict[str, Any]
def list_source_artifacts(self, source_document_id: str | None = None) -> list[SourceArtifact]
```

Store manifests under:

```text
.ariadne/project/source_artifacts/<artifact_id>.json
.ariadne/project/source_artifacts/<artifact_id>.payload.json
.ariadne/project/source_evidence.jsonl
```

Validation:

- missing source -> `ValueError("missing_source_document:<id>")`
- missing artifact -> `ValueError("missing_source_artifact:<id>")`
- payload hash mismatch on load -> `ValueError("source_artifact_payload_hash_mismatch:<id>")`

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_source_assets.py -v
```

Expected:

```text
passed
```

- [ ] **Step 7: Commit**

```bash
git add ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/application/source_assets.py tests/test_source_assets.py
git commit -m "feat: add typed source artifact foundations"
```

## Task 2: Real Source Analysis Pipeline

**Files:**

- Create: `ariadne_ltb/application/source_analysis.py`
- Modify: `ariadne_ltb/application/web_sources.py`
- Modify: `ariadne_ltb/interfaces/http/routes.py`
- Test: `tests/test_source_analysis.py`

- [ ] **Step 1: Write failing analyzer tests**

Add tests:

```python
def test_markdown_source_analysis_writes_knowledge_card(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    source = create_source_document(
        store,
        source_type=SourceType.NOTE,
        title="Minimal agent note",
        path_or_url="file://notes/minimal-agent.md",
        content="A minimal agent repeats: query model, parse action, execute, observe.",
        metadata={"source_role": "requirement_source"},
    )

    result = SourceAnalysisService(store).analyze_source(source.id)

    assert result.status == "analyzed"
    artifacts = store.list_source_artifacts(source.id)
    assert artifacts[0].artifact_type == "knowledge_card"
    payload = store.load_source_artifact_payload(artifacts[0].id)
    assert "query model" in payload["summary"].lower()
    assert store.list_source_evidence(source.id)
```

Add GitHub analyzer test with fixture content, not network:

```python
def test_github_repo_analysis_writes_reference_project_profile(tmp_path: Path) -> None:
    repo = tmp_path / "reference"
    repo.mkdir()
    (repo / "README.md").write_text("# MiniCode\n\nCLI coding assistant with sessions and diff review.", encoding="utf-8")
    (repo / "LICENSE").write_text("MIT License", encoding="utf-8")
    (repo / "pyproject.toml").write_text("[project]\nname='minicode'\n[project.scripts]\nminicode='minicode.cli:main'\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_cli.py").write_text("def test_cli():\n    assert True\n", encoding="utf-8")

    store = AriadneStore(tmp_path / "store")
    source = create_source_document(
        store,
        source_type=SourceType.GITHUB_REPO,
        title="MiniCode local fixture",
        path_or_url=str(repo),
        content="",
        metadata={"source_role": "reference_project"},
    )

    SourceAnalysisService(store).analyze_source(source.id)

    artifact = store.list_source_artifacts(source.id)[0]
    payload = store.load_source_artifact_payload(artifact.id)
    assert artifact.artifact_type == "reference_project_profile"
    assert payload["license"]["detected"] == "MIT"
    assert payload["license_risk"] == "green"
    assert payload["entrypoints"]
    assert payload["tests"]["paths"] == ["tests/test_cli.py"]
    assert payload["behavior_patterns"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest tests/test_source_analysis.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'ariadne_ltb.application.source_analysis'
```

- [ ] **Step 3: Implement source analyzer service**

Create `SourceAnalysisService` with:

```python
class SourceAnalysisService:
    def __init__(self, store: AriadneStore) -> None: ...
    def analyze_source(self, source_id: str) -> SourceAnalysisResult: ...
```

Dispatch rules:

- `blog`, `paper`, `note`, `local_markdown` -> `knowledge_card`
- `github_repo`, `local_folder` with `source_role=reference_project` -> `reference_project_profile`
- `target_codebase` -> `codebase_snapshot`

Do not require network in tests. For URL analysis, support injected fetcher:

```python
class SourceAnalysisService:
    def __init__(self, store: AriadneStore, fetcher: SourceFetcher | None = None) -> None:
        self.fetcher = fetcher or RequestsSourceFetcher()
```

If fetch fails, mark:

```json
{"analysis_status": "blocked", "analysis_error": "fetch_failed:<reason>"}
```

- [ ] **Step 4: Implement minimal reference project profile payload**

Payload shape:

```json
{
  "repo_summary": "",
  "identity": {
    "name": "",
    "commit_sha": null,
    "primary_language": "python",
    "package_manager": "python",
    "frameworks": []
  },
  "license": {
    "detected": "MIT",
    "confidence": "high",
    "license_file_path": "LICENSE"
  },
  "license_risk": "green",
  "entrypoints": [],
  "repo_map": {
    "top_level": [],
    "core_modules": [],
    "test_modules": []
  },
  "tests": {
    "paths": [],
    "commands": []
  },
  "behavior_patterns": [],
  "reuse_notes": [],
  "avoid_notes": []
}
```

License risk rules:

- MIT, Apache-2.0, BSD -> `green`
- missing, unknown -> `yellow`
- GPL, AGPL -> `red`

- [ ] **Step 5: Update WebSourceService**

`WebSourceService.create()` should:

- create source record
- set `metadata.analysis_status = "pending"`
- not treat user-provided `content` as successful ingestion proof
- keep `content` only as optional pasted note for local/offline sources

Add endpoint:

```text
POST /api/sources/{source_id}/analyze
```

Response includes:

```json
{
  "source": {},
  "artifacts": [],
  "evidence": []
}
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_source_analysis.py tests/test_web_dogfood_product_path.py -v
```

Expected:

```text
passed
```

- [ ] **Step 7: Commit**

```bash
git add ariadne_ltb/application/source_analysis.py ariadne_ltb/application/web_sources.py ariadne_ltb/interfaces/http/routes.py tests/test_source_analysis.py tests/test_web_dogfood_product_path.py
git commit -m "feat: analyze sources into typed artifacts"
```

## Task 3: Build Context and Issue Factory Compiler

**Files:**

- Create: `ariadne_ltb/application/build_context.py`
- Create: `ariadne_ltb/application/issue_delta_validation.py`
- Modify: `ariadne_ltb/application/issue_factory.py`
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Test: `tests/test_issue_factory_compiler.py`

- [ ] **Step 1: Write strict Mini Code Agent issue factory tests**

Replace weak assertions with:

```python
def test_issue_factory_compiles_mca_issue_set_from_typed_artifacts(tmp_path: Path) -> None:
    store, goal_id, project_id, source_ids = seed_mini_code_agent_context(tmp_path)

    preview = IssueFactoryService(store).preview(
        IssueFactoryPreviewInput(goal_id=goal_id, source_ids=source_ids, target_project_id=project_id)
    )

    keys = [operation.ticket_key for operation in preview.operations]
    titles = [operation.title for operation in preview.operations]

    assert keys[:10] == [
        "MCA-001",
        "MCA-002",
        "MCA-003",
        "MCA-004",
        "MCA-005",
        "MCA-006",
        "MCA-007",
        "MCA-008",
        "MCA-009",
        "MCA-010",
    ]
    assert "Bootstrap Python package and CLI" in titles
    assert "Add DeepSeek-backed LLM client configuration" in titles
    assert "Define tool protocol and model action schema" in titles
    assert "Implement shell command tool with allowlist" in titles
    assert "Implement file read and patch tools with review-before-write safety" in titles
    assert "Implement agent loop: prompt -> action -> observation -> repeat" in titles
    assert "Persist session trace and run summary" in titles
    assert "Capture git diff and test result" in titles
    assert "Add minimal reviewer checks for task completion" in titles
    assert "Write README quickstart and usage examples" in titles

    for operation in preview.operations:
        assert operation.metadata["target_project_id"] == project_id
        assert operation.metadata["build_context_id"]
        assert operation.metadata["evidence_refs"]
        assert operation.metadata["affected_modules"]
        assert operation.metadata["acceptance_criteria"]
        assert operation.metadata["goal_reason"]
```

Add validator test:

```python
def test_issue_delta_validator_rejects_generic_code_task() -> None:
    operation = BacklogOperation(
        id="op_bad",
        operation_type=BacklogOperationType.ADD_TICKET,
        ticket_id="ticket_bad",
        ticket_key="MCA-999",
        title="Implement stuff",
        description="Do useful implementation work.",
        source_type="note",
        source_ref="ariadne://test",
        priority="high",
        status=TicketStatus.PLANNING,
        reason="Too generic",
        metadata={
            "target_project_id": "project_1",
            "build_context_id": "ctx_1",
            "evidence_refs": [],
            "affected_modules": [],
            "acceptance_criteria": [],
        },
    )

    with pytest.raises(ValueError, match="missing_evidence_refs"):
        validate_issue_delta_operation(operation)
```

- [ ] **Step 2: Run compiler tests and verify they fail**

Run:

```bash
pytest tests/test_issue_factory_compiler.py -v
```

Expected:

```text
AssertionError: ARI-...
```

or missing modules.

- [ ] **Step 3: Implement BuildContext assembler**

`assemble_issue_factory_context()` must load:

- `ProjectGoal`
- `TargetProject`
- selected source documents
- source artifacts
- source evidence
- codebase snapshot artifact, creating one if missing and target path exists
- current ticket backlog fingerprint

Persist only the `BuildContextManifest`.

Fingerprint input:

```text
goal_id
target_project_id
sorted source ids
sorted artifact ids
sorted evidence ids
codebase snapshot artifact id
base ticket fingerprint
```

- [ ] **Step 4: Replace hard-coded `_dogfood_tasks()` path**

`IssueFactoryService.preview()` should now:

```python
context = assemble_issue_factory_context(self.store, goal, sources, payload.target_project_id)
capability_rows = derive_capability_matrix(context)
operations = compile_issue_delta(context, capability_rows)
operations = validate_issue_delta_operations(operations)
```

Keep `_dogfood_tasks()` only as test fixture helper under `tests/fixtures` if still needed. It must not be called in product code.

- [ ] **Step 5: Generate project namespace keys**

If `TargetProject` metadata has `issue_prefix`, use it. Otherwise infer:

- `Mini Code Agent` -> `MCA`
- fallback -> first uppercase letters from project label, max 4 characters

`mini-code-agent` must generate:

```text
MCA-001
MCA-002
...
```

Do not use `ARI-*` for target project issues unless the target project is Ariadne itself.

- [ ] **Step 6: Compile Mini Code Agent capability rows**

For the Mini Code Agent dogfood, derive rows from:

- goal text
- `minimal-agent.com` knowledge card
- `mini-SWE-agent` reference project profile
- `MiniCode` reference project profile
- current target project codebase snapshot

Required generated issues:

```text
MCA-001 Bootstrap Python package and CLI
MCA-002 Add DeepSeek-backed LLM client configuration
MCA-003 Define tool protocol and model action schema
MCA-004 Implement shell command tool with allowlist
MCA-005 Implement file read and patch tools with review-before-write safety
MCA-006 Implement agent loop: prompt -> action -> observation -> repeat
MCA-007 Persist session trace and run summary
MCA-008 Capture git diff and test result
MCA-009 Add minimal reviewer checks for task completion
MCA-010 Write README quickstart and usage examples
```

Each operation must include:

- `goal_reason`
- `source_document_ids`
- `source_artifact_ids`
- `evidence_refs`
- `affected_modules`
- `acceptance_criteria`
- `risks`
- `assumptions`
- `target_project_id`
- `build_context_id`

- [ ] **Step 7: Apply preview writes BuildTickets and BuildPackets**

When applying the preview:

- `BuildTicket.key` uses `MCA-*`
- ticket metadata includes `build_context_id`, `source_document_ids`, `source_artifact_ids`, `evidence_refs`, `target_project_id`
- generated `BuildPacket` exists before assignment
- `BuildPacket` references the same evidence and acceptance criteria

- [ ] **Step 8: Run tests**

Run:

```bash
pytest tests/test_issue_factory_compiler.py tests/test_web_dogfood_product_path.py -v
```

Expected:

```text
passed
```

- [ ] **Step 9: Commit**

```bash
git add ariadne_ltb/application/build_context.py ariadne_ltb/application/issue_delta_validation.py ariadne_ltb/application/issue_factory.py ariadne_ltb/models.py ariadne_ltb/storage.py tests/test_issue_factory_compiler.py tests/test_web_dogfood_product_path.py
git commit -m "feat: compile typed sources into project issues"
```

## Task 4: HTTP Error Semantics and Project Setup UX

**Files:**

- Modify: `ariadne_ltb/interfaces/http/routes.py`
- Modify: `ariadne_ltb/application/target_projects.py`
- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Test: `tests/test_issue_factory_http_errors.py`
- Test: `tests/test_web_project_setup.py`

- [ ] **Step 1: Write stale preview HTTP test**

```python
def test_apply_stale_preview_returns_409(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    project_id, goal_id, source_ids = create_web_dogfood_seed(client, tmp_path)
    preview = client.post(
        "/api/issue-factory/preview",
        json={"goal_id": goal_id, "source_ids": source_ids, "target_project_id": project_id},
    ).json()["preview"]

    client.post(
        "/api/issue-factory/preview",
        json={"goal_id": goal_id, "source_ids": source_ids, "target_project_id": project_id},
    )
    force_backlog_change(tmp_path)

    response = client.post(f"/api/issue-factory/{preview['id']}/apply", json={})

    assert response.status_code == 409
    assert response.json()["code"] == "stale_preview"
    assert "regenerate" in response.json()["message"].lower()
```

- [ ] **Step 2: Write project folder create/init tests**

```python
def test_target_project_can_create_missing_folder_and_init_git(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "store"))
    target = tmp_path / "mini-code-agent"

    response = client.post(
        "/api/target-projects",
        json={
            "path": str(target),
            "label": "Mini Code Agent",
            "create_if_missing": True,
            "init_git": True,
            "test_command": "python3.11 -m pytest",
            "issue_prefix": "MCA",
        },
    )

    assert response.status_code == 200
    assert target.exists()
    assert (target / ".git").exists()
    payload = response.json()["target_project"]
    assert payload["metadata"]["test_command"] == "python3.11 -m pytest"
    assert payload["metadata"]["issue_prefix"] == "MCA"
```

- [ ] **Step 3: Convert stale preview exceptions to 409**

In `routes.py`, catch stale preview `ValueError` from `IssueFactoryService.apply()` and return:

```json
{
  "code": "stale_preview",
  "message": "This task-change preview is stale because the project issue set changed. Regenerate task changes and apply the new preview.",
  "details": {
    "preview_id": "..."
  }
}
```

- [ ] **Step 4: Add target project creation flags**

Extend target project input DTO with:

```python
create_if_missing: bool = False
init_git: bool = False
test_command: str | None = None
issue_prefix: str | None = None
```

If the path does not exist and `create_if_missing=False`, return a product error:

```json
{
  "code": "target_path_missing",
  "message": "The target folder does not exist. Create the folder from the Workbench or choose an existing project folder.",
  "action": "create_folder"
}
```

Do not show raw FastAPI validation JSON in the product UI.

- [ ] **Step 5: Update Workbench form states**

Project setup must show:

- create folder
- initialize git
- test command
- issue prefix
- path validity
- git status

For errors, render user-actionable Chinese copy in the UI:

```text
目标文件夹不存在。你可以点击“创建文件夹并初始化 Git”，或选择一个已有项目。
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_issue_factory_http_errors.py tests/test_web_project_setup.py -v
```

Expected:

```text
passed
```

- [ ] **Step 7: Commit**

```bash
git add ariadne_ltb/interfaces/http/routes.py ariadne_ltb/application/target_projects.py frontend/ariadne-workbench/src/App.tsx tests/test_issue_factory_http_errors.py tests/test_web_project_setup.py
git commit -m "fix: make project setup and stale previews recoverable"
```

## Task 5: Ready Assignment State Machine

**Files:**

- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/application/run_assignment.py`
- Modify: `ariadne_ltb/daemon.py`
- Modify: `ariadne_ltb/application/daemon_control.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Test: `tests/test_assignment_claim_state_machine.py`
- Test: `tests/test_workbench_daemon_feedback.py`

- [ ] **Step 1: Write project-scoped claim tests**

```python
def test_daemon_claims_only_ready_assignment_for_current_project(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    old_project = seed_target_project(store, label="Old Project")
    current_project = seed_target_project(store, label="Mini Code Agent")
    old_assignment = seed_assignment(store, target_project_id=old_project.id, lifecycle_state="queued")
    current_assignment = seed_assignment(
        store,
        target_project_id=current_project.id,
        lifecycle_state="ready_to_claim",
        route_decision_id="route_current",
        handoff_packet_id="handoff_current",
        confirmation_id="confirm_current",
        handoff_hash="sha256:current",
        expected_git_head="abc123",
    )

    worker = LocalDaemonWorker(
        store=store,
        runtime_id="runtime_1",
        target_project_id=current_project.id,
        allowed_backends=["codex"],
    )

    claimed = worker.claim_next_assignment()

    assert claimed.id == current_assignment.id
    assert store.load_ticket_assignment(old_assignment.id).lifecycle_state == "queued"
```

- [ ] **Step 2: Add assignment lifecycle states**

Allowed lifecycle states:

```text
draft
routed
handoff_ready
awaiting_user_approval
ready_to_claim
claimed
running
done
blocked
failed
cancelled
```

Terminal states:

```text
done
blocked
failed
cancelled
```

Terminal assignments cannot transition back to non-terminal states.

- [ ] **Step 3: Freeze route and handoff before claim**

Assignment cannot enter `ready_to_claim` unless these fields exist:

```text
target_project_id
route_decision_id
handoff_packet_id
permission_profile_id
confirmation_id or runtime_authorization_id
handoff_hash
target_repo_path
expected_git_head
```

If a field is missing, return blocked product status:

```text
assignment_not_ready:<missing_field>
```

- [ ] **Step 4: Make daemon claim scoped and explicit**

Change daemon claim API to support:

```python
claim_next_assignment(
    runtime_id: str,
    target_project_id: str | None,
    allowed_backends: list[str],
) -> TicketAssignment | None
```

Rules:

- only claim `ready_to_claim`
- match `target_project_id` when provided
- match backend in `allowed_backends`
- prefer explicit assignment id when user clicks run on a specific issue

- [ ] **Step 5: Add claim token/fencing**

When claiming:

```text
claim_token = stable_id("claim", assignment_id, runtime_id, generation)
claim_generation += 1
lease_expires_at = now + lease_seconds
```

Execution result write must verify the same claim token. If mismatch:

```text
blocked: stale_claim_token
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_assignment_claim_state_machine.py tests/test_workbench_daemon_feedback.py -v
```

Expected:

```text
passed
```

- [ ] **Step 7: Commit**

```bash
git add ariadne_ltb/models.py ariadne_ltb/application/run_assignment.py ariadne_ltb/daemon.py ariadne_ltb/application/daemon_control.py ariadne_ltb/orchestrator.py tests/test_assignment_claim_state_machine.py tests/test_workbench_daemon_feedback.py
git commit -m "feat: gate daemon claims on ready assignments"
```

## Task 6: Workbench Product Surface Cleanup

**Files:**

- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Modify: `frontend/ariadne-workbench/src/data.ts`
- Modify: `frontend/ariadne-workbench/src/styles.css`
- Test: `tests/test_frontend_api_contract_static.py`
- Test: `tests/test_web_dogfood_product_path.py`

- [ ] **Step 1: Add frontend contract assertions**

Update static tests so product mode cannot silently reintroduce demo concepts:

```python
def test_workbench_product_copy_does_not_make_knowledge_card_primary() -> None:
    app = Path("frontend/ariadne-workbench/src/App.tsx").read_text(encoding="utf-8")
    product_shell = app[app.index("function App"): app.index("export default App")]
    assert "Knowledge Card" not in product_shell
    assert "Ariadne v1.0" not in product_shell
    assert "fixture" not in product_shell.lower()
```

Allow these strings only in explicit offline fixture files or tests.

- [ ] **Step 2: Collapse normal nav**

Normal user flow:

```text
Project
Sources
Tasks
Ready to Run
```

Move Agents, Runtime, Skills, Inbox under:

```text
Diagnostics
```

or make them secondary tabs inside Ready to Run.

- [ ] **Step 3: Source page UI**

Display each source as:

```text
title
type
role
analysis status
summary
evidence count
artifact count
last analyzed at
```

Do not display `Knowledge Card` as a required user concept.

- [ ] **Step 4: Task changes UI**

For each preview operation, display:

```text
operation type
issue key
title
why this exists
source evidence count
affected modules
acceptance criteria
risk
```

Add a "Why" drawer that shows evidence refs and source titles.

- [ ] **Step 5: Ready to Run UI**

For selected issue, display:

```text
target project
route decision
backend
handoff hash
allowed paths
test command
assignment lifecycle state
runtime readiness
```

If assignment is not ready, show the exact missing gate.

- [ ] **Step 6: Run frontend and static tests**

Run:

```bash
pytest tests/test_frontend_api_contract_static.py tests/test_web_dogfood_product_path.py -v
```

If the frontend package has a test script, run:

```bash
cd frontend/ariadne-workbench && npm test -- --runInBand
```

Expected:

```text
passed
```

- [ ] **Step 7: Commit**

```bash
git add frontend/ariadne-workbench/src/App.tsx frontend/ariadne-workbench/src/data.ts frontend/ariadne-workbench/src/styles.css tests/test_frontend_api_contract_static.py tests/test_web_dogfood_product_path.py
git commit -m "feat: simplify workbench source-to-run product path"
```

## Task 7: Browser Dogfood Acceptance

**Files:**

- Modify: `docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md`
- Modify: `docs/development_report.md`
- Create: `docs/dogfood/results/2026-06-19-mini-code-agent-source-to-issue-browser-result.md`

- [ ] **Step 1: Start Ariadne API and Workbench**

Use the repo's existing server commands. If ports are occupied, choose free ports and record them.

```bash
python3.11 -m ariadne_ltb.interfaces.http.app
```

and frontend dev server command used by the repo.

- [ ] **Step 2: Browser acceptance path**

Using the in-app browser, complete:

1. Open Workbench.
2. Create or register:

   ```text
   /Users/martinlos/code/ariadne-dogfood/mini-code-agent
   ```

3. Enable:

   ```text
   create folder if missing
   initialize git
   test command = python3.11 -m pytest
   issue prefix = MCA
   ```

4. Create goal:

   ```text
   Build a Python mini code agent MVP for local AI Builders.
   ```

5. Add and analyze:

   ```text
   https://minimal-agent.com/
   https://github.com/SWE-agent/mini-SWE-agent
   https://github.com/LiuMengxuan04/MiniCode
   ```

6. Generate task changes.
7. Confirm preview contains `MCA-001` through `MCA-010`.
8. Open "Why" for `MCA-001`.
9. Confirm evidence points to at least one typed artifact.
10. Apply task changes.
11. Select `MCA-001`.
12. Create route decision and handoff.
13. Confirm assignment is queued or ready, but not yet executed unless a separate execution gate is passed.

- [ ] **Step 3: Verify no fake fixture leakage**

In the browser and network responses, confirm:

- no `ARI-*` keys in the Mini Code Agent project issue set
- no `Ariadne v1.0` target label in Mini Code Agent issue cards
- no product-mode fixture fallback
- no hand-entered source content used as ingestion evidence

- [ ] **Step 4: Record result**

Create:

```text
docs/dogfood/results/2026-06-19-mini-code-agent-source-to-issue-browser-result.md
```

Include:

```markdown
# Mini Code Agent Source-to-Issue Browser Result

## Environment

- Date:
- Branch:
- API URL:
- Workbench URL:

## Flow Result

- Target project:
- Goal:
- Sources analyzed:
- Source artifacts:
- Evidence refs:
- Preview id:
- Created issue keys:
- Selected issue:
- Route decision:
- Handoff:
- Assignment:

## Failures

- 

## Follow-up Tickets

- 
```

- [ ] **Step 5: Commit**

```bash
git add docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md docs/development_report.md docs/dogfood/results/2026-06-19-mini-code-agent-source-to-issue-browser-result.md
git commit -m "docs: record mini code agent source-to-issue dogfood"
```

## Verification Commands

Run before merging:

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli backend doctor
python3.11 -m ariadne_ltb.cli export board
```

Browser verification is mandatory for this plan because the product failure is in Workbench behavior, not only backend APIs.

If `uv run ari` is available, also run:

```bash
uv run ari backend doctor
uv run ari export board
```

Do not run real Codex/Claude execution as proof for this plan unless the separate execution gate is explicitly passed and evidence is recorded.

## Absorption Review Matrix

| Input | Required opinion | Covered by |
|---|---|---|
| GPT Pro round 1 | External input must not collapse into `Knowledge Card` | SourceArtifact types and SourceAnalysisService in Tasks 1 and 2 |
| GPT Pro round 1 | GitHub repo requires repo/profile/pattern/license extraction | `reference_project_profile` payload in Task 2 |
| GPT Pro round 1 | Issue Factory input should be Build Context, not `goal + knowledge cards` | BuildContextManifest and compiler in Task 3 |
| GPT Pro round 1 | Evidence should be first-class and immutable | SourceEvidence in Task 1 |
| GPT Pro round 1 | MVP should stay Python/local/JSON, no vector DB | File store payloads and JSON manifests in Tasks 1 to 3 |
| GPT Pro round 2 | Product UI must hide internal compiler objects | Product surface rule and Task 6 |
| GPT Pro round 2 | Do not make Pattern Card, Build Context, Gap Map first-class product objects | Internal data model constraints |
| GPT Pro round 2 | Reuse `BacklogPreview` as Issue Delta | Task 3 keeps `BacklogPreview` and `BacklogOperation` |
| GPT Pro round 2 | Replace hard-coded demo issue generator | Task 3 removes `_dogfood_tasks()` from product path |
| GPT Pro round 2 | Stop before backend execution gate for this slice | Product Boundary and Task 7 |
| Dogfood finding | Missing target folder produced raw 422 | Task 4 creates recoverable project setup UX |
| Dogfood finding | URL/GitHub ingestion was manual note entry | Task 2 requires server-side source analysis |
| Dogfood finding | Generated ARI generic tasks instead of MCA issues | Task 3 requires project issue prefix and MCA issue set |
| Dogfood finding | Stale preview became 500 | Task 4 requires 409 `stale_preview` |
| Dogfood finding | Daemon claimed old assignment | Task 5 gates claim on project-scoped `ready_to_claim` |
| Dogfood finding | Workbench looked like static dashboards | Task 6 collapses UI around source-to-run path |

## Cross-Review Integration

The four parallel reviews changed this plan in concrete ways:

1. Product review required hiding typed artifacts from the default UI and removing `Ariadne v1.0` from target project cards. Task 6 covers this.
2. Data model review required reusing `SourceDocument` and `BacklogPreview` instead of creating a parallel schema. Tasks 1 and 3 follow that.
3. Runtime review required a hard `ready_to_claim` assignment state before daemon claim. Task 5 adds that state machine.
4. Testability review required splitting browser/product proof from API fixture proof. Task 7 makes browser acceptance mandatory and Task 3 strengthens `test_web_dogfood_product_path.py`.

## Known Non-Goals

- No hosted auth.
- No full Multica clone.
- No vector database.
- No source knowledge graph.
- No real Feishu write.
- No automatic Codex/Claude execution in this plan.
- No product-mode fixture fallback.

## Merge Criteria

This plan is complete only when:

1. Workbench can register/create the Mini Code Agent target project.
2. Workbench can create the goal and add the three dogfood sources.
3. Source analysis writes typed artifacts and source evidence.
4. Issue Factory generates `MCA-001` to `MCA-010`, not `ARI-*` generic Ariadne tasks.
5. Applying stale previews returns 409 and is recoverable in the UI.
6. Applied tickets have `target_project_id`, `build_context_id`, evidence refs, affected modules, and acceptance criteria.
7. Ready to Run generates route decision and frozen handoff before assignment claim.
8. Daemon cannot claim old queued assignments outside the current project readiness state.
9. Browser acceptance result is recorded under `docs/dogfood/results/`.
10. `pytest`, `ruff check .`, `backend doctor`, and `export board` pass.
