# Ariadne Local API Agent Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Ariadne from a CLI-driven agent loop plus read-only frontend into a local API-driven agent control plane that lets AI builders assign, run, observe, and comment on agent team work from the browser.

**Architecture:** Add a thin application layer that both CLI and HTTP call, then expose a local FastAPI control-plane API over those services. The frontend should prefer `/api/workbench` and typed mutation endpoints, while `/web_data/workbench.json`, `fake-codex`, `dry-run`, and `demo full` remain offline regression fallback only.

**Tech Stack:** Python 3.11, Pydantic v2, Typer, FastAPI, Uvicorn, JSON/JSONL store, React 19, Vite, TypeScript.

---

## Source Review Inputs

This plan implements the problems identified in:

- `docs/reviews/2026-06-18-ariadne-agent-control-plane-review.md`
- Subplan A: application/DDD/API service boundary.
- Subplan B: frontend API-backed AI Builder workflow.
- Subplan C: runtime status, timeline, target project registry, and web redaction.

Cross-review conclusion:

```text
Ariadne has the local execution kernel.
Ariadne does not yet have the browser-operable agent control plane.
P0 is assign/run/watch/comment through a local API, not folder movement.
```

Control-plane data flow:

```text
Browser UI
  -> typed HTTP schema
  -> application service
  -> store / daemon / orchestrator
  -> redacted projection
  -> browser timeline
```

## Non-Negotiable Product Rules

1. Browser mutations may send only stable ids, constrained enums, idempotency keys, bounded timeout, comment body, and server-issued confirmation token.
2. Browser mutations must not send `command`, `command_template`, `target_repo_path`, `repo_path`, `local_path`, `allowed_paths`, `handoff_file`, `test_command`, `stdout`, `stderr`, `shell`, `planner`, `agent_runtime`, `backlog_planner`, `use_memory`, `isolate_worktree`, `lease_seconds`, `runtime_id`, or raw environment fields.
3. Production UI/API actions must require `target_project_id`; they must not call `ensure_demo_target_project()`.
4. `shell` must remain CLI-only and unavailable from web action capability lists.
5. CLI and HTTP must call the same application services. Do not create a parallel HTTP execution pipeline.
6. Raw local evidence must remain available for local audit. Web projections must redact commands, templates, handoff paths, absolute `.ariadne` paths, raw stdout/stderr, and secrets.
7. Frontend P0 is real API-backed `assign -> run -> watch -> comment`. Broad FSD cleanup is P1 after the action path works.
8. Browser/API product actions may expose only production coding backends: `codex` and `claude-code`. `fake-codex` and `dry-run` are allowed only in automated tests or explicitly labeled offline fallback paths; they must not appear as selectable browser action runtimes.
9. The local API server is P0 FastAPI/Uvicorn and local-only: default bind is `127.0.0.1`; `0.0.0.0` requires an explicit CLI warning; request bodies are size-limited; mutation routes require `Content-Type: application/json`; CORS is not opened broadly.
10. Confirmation tokens are server-issued action tokens bound to `assignment_id`, `target_project_id`, and backend. They must not appear in `/api/workbench`, timeline events, logs, or evidence projections.

## Target File Structure

Create these backend modules:

```text
ariadne_ltb/application/__init__.py
ariadne_ltb/application/dtos.py
ariadne_ltb/application/errors.py
ariadne_ltb/application/idempotency.py
ariadne_ltb/application/runtime_status.py
ariadne_ltb/application/target_project_registry.py
ariadne_ltb/application/workbench_projection.py
ariadne_ltb/application/assign_ticket.py
ariadne_ltb/application/run_assignment.py
ariadne_ltb/application/run_events.py
ariadne_ltb/application/comments.py
ariadne_ltb/application/confirmation_tokens.py
ariadne_ltb/application/evidence_projection.py
ariadne_ltb/domain/__init__.py
ariadne_ltb/domain/runtime_policy.py
ariadne_ltb/interfaces/__init__.py
ariadne_ltb/interfaces/http/__init__.py
ariadne_ltb/interfaces/http/app.py
ariadne_ltb/interfaces/http/dependencies.py
ariadne_ltb/interfaces/http/errors.py
ariadne_ltb/interfaces/http/routes.py
ariadne_ltb/interfaces/http/schemas.py
```

Create these frontend modules:

```text
frontend/ariadne-workbench/src/shared/api/types.ts
frontend/ariadne-workbench/src/shared/api/client.ts
frontend/ariadne-workbench/src/shared/api/errors.ts
frontend/ariadne-workbench/src/shared/lib/idempotency.ts
frontend/ariadne-workbench/src/entities/runtime/model.ts
frontend/ariadne-workbench/src/entities/runtime/lib.ts
frontend/ariadne-workbench/src/entities/assignment/model.ts
frontend/ariadne-workbench/src/entities/ticket/model.ts
frontend/ariadne-workbench/src/entities/target-project/model.ts
frontend/ariadne-workbench/src/features/assign-ticket/model.ts
frontend/ariadne-workbench/src/features/assign-ticket/api.ts
frontend/ariadne-workbench/src/features/assign-ticket/ui.tsx
frontend/ariadne-workbench/src/features/run-assignment/model.ts
frontend/ariadne-workbench/src/features/run-assignment/api.ts
frontend/ariadne-workbench/src/features/run-assignment/ui.tsx
frontend/ariadne-workbench/src/features/watch-run-events/model.ts
frontend/ariadne-workbench/src/features/watch-run-events/api.ts
frontend/ariadne-workbench/src/features/watch-run-events/ui.tsx
frontend/ariadne-workbench/src/features/add-ticket-comment/model.ts
frontend/ariadne-workbench/src/features/add-ticket-comment/api.ts
frontend/ariadne-workbench/src/features/add-ticket-comment/ui.tsx
```

Create these tests:

```text
tests/test_application_idempotency.py
tests/test_target_project_registry.py
tests/test_target_project_cli.py
tests/test_runtime_policy.py
tests/test_workbench_projection_service.py
tests/test_runtime_status_service.py
tests/test_assign_ticket_service.py
tests/test_run_assignment_service.py
tests/test_assignment_timeline.py
tests/test_comments_service.py
tests/test_evidence_projection.py
tests/test_control_plane_http.py
tests/test_http_contract_rejects_dangerous_fields.py
tests/test_cli_uses_application_services.py
tests/test_frontend_api_contract_static.py
tests/test_frontend_control_plane_e2e.py
```

## Execution Order

Implement in this order:

1. Backend DTO and policy foundation.
2. Target project registry and user-facing target registration.
3. Read-only projections.
4. Mutation services and CLI sharing.
5. Timeline and evidence projection.
6. HTTP interface.
7. Frontend API client and action slices.
8. Browser-level end-to-end verification.

---

### Task 1: Application DTOs, Errors, Idempotency, Runtime Policy

**Files:**
- Create: `ariadne_ltb/application/__init__.py`
- Create: `ariadne_ltb/application/dtos.py`
- Create: `ariadne_ltb/application/errors.py`
- Create: `ariadne_ltb/application/idempotency.py`
- Create: `ariadne_ltb/domain/__init__.py`
- Create: `ariadne_ltb/domain/runtime_policy.py`
- Modify: `ariadne_ltb/storage.py`
- Test: `tests/test_application_idempotency.py`
- Test: `tests/test_runtime_policy.py`

- [ ] **Step 1: Write failing idempotency tests**

Add tests that create an `AriadneStore` rooted at `tmp_path`, record a mutation result for action `assign_ticket`, replay the same key, and assert the stored response is returned without a duplicate record.

Run:

```bash
python3.11 -m pytest tests/test_application_idempotency.py -q
```

Expected: fail because `MutationIdempotencyStore` does not exist.

- [ ] **Step 2: Write failing runtime policy tests**

Add tests for:

```text
runtime_profile=auto with backend codex -> production values
runtime_profile=auto with backend claude-code -> production values
runtime_profile=auto with backend fake-codex -> deterministic values
source=http rejects shell
source=http rejects fake-codex
source=http rejects dry-run
source=test may use fake-codex for deterministic E2E only
source=test may use dry-run for deterministic E2E only
browser runtime status marks fallback backends as fallback_only and non-selectable
```

Run:

```bash
python3.11 -m pytest tests/test_runtime_policy.py -q
```

Expected: fail because `ariadne_ltb.domain.runtime_policy` does not exist.

- [ ] **Step 3: Implement DTOs and errors**

Create Pydantic models in `ariadne_ltb/application/dtos.py`:

```python
from typing import Literal

from pydantic import ConfigDict, Field

from ariadne_ltb.models import AriadneModel


class StrictApplicationModel(AriadneModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDto(StrictApplicationModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)


class AssignTicketCommand(StrictApplicationModel):
    ticket_id: str
    assignee_id: str
    assignee_kind: Literal["agent", "build_team"] = "agent"
    backend_name: str
    runtime_profile: Literal["auto", "deterministic", "production"] = "auto"
    target_project_id: str
    idempotency_key: str
    source: Literal["cli", "http"] = "http"


class RunAssignmentCommand(StrictApplicationModel):
    assignment_id: str
    confirmation_token: str
    timeout_seconds: int | None = None
    idempotency_key: str
    source: Literal["cli", "http"] = "http"


class AddTicketCommentCommand(StrictApplicationModel):
    ticket_id: str
    body: str
    idempotency_key: str
    parent_comment_id: str | None = None
    assignment_id: str | None = None
    source: Literal["cli", "http"] = "http"


class AssignmentDto(StrictApplicationModel):
    id: str
    ticket_id: str
    ticket_key: str
    agent_id: str
    backend_name: str | None
    status: str
    target_project_id: str | None = None
    confirmation_token: str | None = None


class AssignTicketResultDto(StrictApplicationModel):
    assignment: AssignmentDto
    idempotency_key: str
    reused: bool = False


class RunAssignmentResultDto(StrictApplicationModel):
    assignment_id: str
    did_work: bool
    status: str
    message: str
    idempotency_key: str
    reused: bool = False


class TicketCommentDto(StrictApplicationModel):
    id: str
    ticket_id: str
    author_name: str
    kind: str
    body: str
    created_at: str
    assignment_id: str | None = None


class AddTicketCommentResultDto(StrictApplicationModel):
    comment: TicketCommentDto
    idempotency_key: str
    reused: bool = False
```

Create `ariadne_ltb/application/errors.py`:

```python
class ApplicationError(RuntimeError):
    code = "application_error"

    def __init__(self, message: str, *, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidRequestError(ApplicationError):
    code = "invalid_request"


class InvalidResourceError(ApplicationError):
    code = "invalid_resource"


class ForbiddenBackendError(ApplicationError):
    code = "forbidden_backend"


class IdempotencyConflictError(ApplicationError):
    code = "idempotency_conflict"
```

- [ ] **Step 4: Implement idempotency store**

Store mutation records under `.ariadne/application/idempotency/<action>/<key>.json`.

Public API:

```python
class MutationIdempotencyStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def get(self, action: str, key: str) -> dict[str, object] | None:
        path = self._path(action, key)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def record_success(self, action: str, key: str, response: AriadneModel) -> None:
        path = self._path(action, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "action": action,
            "idempotency_key": key,
            "response": response.model_dump(mode="json"),
            "created_at": utc_now(),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
```

Use a filename-safe key. Reject keys containing `/`, `..`, NUL, or empty string.

- [ ] **Step 5: Implement runtime policy**

Move the CLI profile logic into `ariadne_ltb/domain/runtime_policy.py`:

```python
PRODUCT_BACKENDS = {"codex", "claude-code"}
FALLBACK_BACKENDS = {"fake-codex", "dry-run"}
WEB_FORBIDDEN_BACKENDS = {"shell"}


class RuntimeProfileValues(AriadneModel):
    planner_name: str
    agent_runtime: str
    backlog_planner_name: str


def resolve_runtime_profile(runtime_profile: str, backend_name: str) -> str:
    if runtime_profile == "auto":
        return "production" if backend_name in PRODUCT_BACKENDS else "deterministic"
    return runtime_profile


def runtime_profile_values(runtime_profile: str) -> RuntimeProfileValues:
    if runtime_profile == "production":
        return RuntimeProfileValues(
            planner_name="llm",
            agent_runtime="llm",
            backlog_planner_name="llm",
        )
    return RuntimeProfileValues(
        planner_name="deterministic",
        agent_runtime="deterministic",
        backlog_planner_name="deterministic",
    )
```

Add a function `validate_backend_for_source(source, backend_name, runtime_profile)` that rejects `shell`, `fake-codex`, and `dry-run` for HTTP. The `test` source is the only source allowed to use deterministic fallback backends through the control-plane service layer.

Final policy:

```text
source=http rejects shell
source=http rejects fake-codex
source=http rejects dry-run
source=test may use fake-codex for deterministic E2E only
source=test may use dry-run for deterministic E2E only
```

- [ ] **Step 6: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_application_idempotency.py tests/test_runtime_policy.py -q
git add ariadne_ltb/application ariadne_ltb/domain tests/test_application_idempotency.py tests/test_runtime_policy.py
git commit -m "feat: add application control plane foundation"
```

Expected: tests pass and commit succeeds.

---

### Task 2: Target Project Registry

**Files:**
- Create: `ariadne_ltb/application/target_project_registry.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_target_project_registry.py`
- Test: `tests/test_target_project_cli.py`
- Test: `tests/test_multica_alignment.py`

- [ ] **Step 1: Write failing registry tests**

Test cases:

```text
register local target project from a valid git directory
resolve registered target project by id
reject unknown target_project_id
reject non-directory path
reject production use of demo target project
production assign command without target_project_id fails before ensure_demo_target_project can run
ari target-project register persists a ProjectResource
ari target-project list shows registered project id and label
```

Run:

```bash
python3.11 -m pytest tests/test_target_project_registry.py -q
```

Expected: fail because `TargetProjectRegistry` does not exist.

- [ ] **Step 2: Implement registry**

Create:

```python
class TargetProjectRefDto(StrictApplicationModel):
    id: str
    label: str
    resource_id: str
    server_repo_path: str
    is_demo_target: bool = False


class TargetProjectRegistry:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def list_targets(self) -> list[TargetProjectRefDto]:
        resources = self.store.load_project_resources()
        return [self._to_target(resource) for resource in resources if resource.resource_type == "local_directory"]

    def resolve(self, target_project_id: str, *, runtime_profile: str) -> TargetProjectRefDto:
        for target in self.list_targets():
            if target.id == target_project_id:
                self._validate(target, runtime_profile=runtime_profile)
                return target
        raise InvalidResourceError("Unknown target project", details={"target_project_id": target_project_id})
```

Use existing `ProjectResource` shape. A local target project is a resource with `resource_type == "local_directory"` and canonical local path read from `resource_ref["local_path"]`. `TargetProjectRefDto.server_repo_path` is an internal application-service field only. Web-facing target options expose only `id`, `label`, `available`, and `disabled_reason`; raw `repo_path` remains server-side. Use `validate_target_repo_path(Path(resource.resource_ref["local_path"]))` during validation.

- [ ] **Step 3: Add target project CLI entry point**

Add a Typer command group:

```bash
ari target-project register --id local-default --label "Local default" --repo-path /path/to/repo
ari target-project list
```

Fallback:

```bash
python3.11 -m ariadne_ltb.cli target-project register --id local-default --label "Local default" --repo-path /path/to/repo
python3.11 -m ariadne_ltb.cli target-project list
```

Implementation rules:

```text
register validates repo path with validate_target_repo_path
register persists ProjectResource.local_directory(project_id=id, local_path=repo_path, label=label)
list prints id, label, availability, and validation status
list does not print raw path unless --show-path is passed
```

- [ ] **Step 4: Add store helpers if missing**

If `AriadneStore` already has project-resource load/save helpers, reuse them. If it only writes resources, add a small `load_project_resources()` helper that reads `.ariadne/project/resources.json` and returns `ProjectResource` models.

- [ ] **Step 5: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_target_project_registry.py tests/test_target_project_cli.py tests/test_multica_alignment.py -q
git add ariadne_ltb/application/target_project_registry.py ariadne_ltb/storage.py ariadne_ltb/cli.py tests/test_target_project_registry.py tests/test_target_project_cli.py tests/test_multica_alignment.py
git commit -m "feat: add target project registry"
```

Expected: tests pass and production registry rejects demo fallback.

---

### Task 3: Runtime Status Service And Capability Redaction

**Files:**
- Create: `ariadne_ltb/application/runtime_status.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Test: `tests/test_runtime_status_service.py`
- Test: `tests/test_provider_capability_matrix.py`

- [ ] **Step 1: Write failing runtime status tests**

Test cases:

```text
web runtime status contains codex and claude-code when capability collection reports them
web runtime status never contains shell as action backend
web runtime status marks fake-codex and dry-run as fallback_only
web runtime status does not serialize command
web runtime status does not serialize command_path
web runtime status does not serialize template env vars
web runtime status does not serialize safety gate env vars
```

Run:

```bash
python3.11 -m pytest tests/test_runtime_status_service.py -q
```

Expected: fail because service does not exist.

- [ ] **Step 2: Add DTOs**

Add:

```python
class RedactedRuntimeCapabilityDto(StrictApplicationModel):
    backend_name: str
    display_name: str
    available: bool
    runtime_profile_support: list[str]
    can_assign: bool
    can_run: bool
    requires_confirmation: bool
    fallback_only: bool
    disabled_reasons: list[str] = Field(default_factory=list)


class RuntimeStatusDto(StrictApplicationModel):
    schema_version: Literal["ariadne.runtime-status.v1"] = "ariadne.runtime-status.v1"
    generated_at: str
    daemon_status: str
    current_assignment_id: str | None = None
    queued_assignments: int
    running_assignments: int
    blocked_assignments: int
    capabilities: list[RedactedRuntimeCapabilityDto]
```

- [ ] **Step 3: Implement service**

`RuntimeStatusService.get_status()` should:

1. Load worker heartbeat if present.
2. Count queued/running/blocked assignments.
3. Call `collect_runtime_capabilities()`.
4. Redact to web DTO.
5. Exclude `shell` from `capabilities`.

Do not remove CLI/doctor capability behavior.

- [ ] **Step 4: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_runtime_status_service.py tests/test_provider_capability_matrix.py -q
git add ariadne_ltb/application/runtime_status.py ariadne_ltb/application/dtos.py tests/test_runtime_status_service.py tests/test_provider_capability_matrix.py
git commit -m "feat: add redacted runtime status service"
```

Expected: web capability output is redacted, CLI capability tests still pass.

---

### Task 4: Workbench Projection Service

**Files:**
- Create: `ariadne_ltb/application/workbench_projection.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Test: `tests/test_workbench_projection_service.py`
- Test: `tests/test_workbench_data_sync.py`

- [ ] **Step 1: Write failing projection tests**

Test cases:

```text
snapshot includes schema_version ariadne.workbench.v1
snapshot includes tickets
snapshot includes agents
snapshot includes redacted runtimes
snapshot includes project_resources
snapshot does not require npm run sync:data
snapshot does not expose raw command fields
snapshot does not expose raw target_repo_path as mutation input
```

Run:

```bash
python3.11 -m pytest tests/test_workbench_projection_service.py -q
```

Expected: fail because service does not exist.

- [ ] **Step 2: Add projection DTOs**

Add compact DTOs:

```python
class TicketProjectionDto(StrictApplicationModel):
    id: str
    key: str
    title: str
    status: str
    source_type: str
    build_decision: str | None = None
    latest_assignment_id: str | None = None


class AgentProjectionDto(StrictApplicationModel):
    id: str
    name: str
    role: str
    backend_name: str | None = None
    enabled: bool


class TargetProjectOptionDto(StrictApplicationModel):
    id: str
    label: str
    available: bool
    disabled_reason: str | None = None


class WorkbenchSnapshotDto(StrictApplicationModel):
    schema_version: Literal["ariadne.workbench.v1"] = "ariadne.workbench.v1"
    generated_at: str
    tickets: list[TicketProjectionDto]
    agents: list[AgentProjectionDto]
    runtimes: list[RedactedRuntimeCapabilityDto]
    project_resources: list[TargetProjectOptionDto]
```

- [ ] **Step 3: Implement service**

`WorkbenchProjectionService.get_snapshot()` should use:

- `AriadneStore.list_tickets()`
- `AriadneStore.load_agent_profiles()`
- `RuntimeStatusService.get_status()`
- `TargetProjectRegistry.list_targets()`
- `AriadneStore.find_latest_assignment_for_ticket(ticket.id)`

- [ ] **Step 4: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_workbench_projection_service.py tests/test_workbench_data_sync.py -q
git add ariadne_ltb/application/workbench_projection.py ariadne_ltb/application/dtos.py tests/test_workbench_projection_service.py
git commit -m "feat: add workbench projection service"
```

Expected: projection service passes and snapshot sync regression remains green.

---

### Task 5: Assign Ticket Service And CLI Sharing

**Files:**
- Create: `ariadne_ltb/application/assign_ticket.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_assign_ticket_service.py`
- Test: `tests/test_cli_uses_application_services.py`
- Test: `tests/test_agent_teammate_mode.py`

- [ ] **Step 1: Write failing service tests**

Test cases:

```text
service creates assignment for codex backend using registered target project
service creates assignment through build-team routing using registered target project
service writes assignment comment
service writes queued runtime event
service stores target_project_id in assignment metadata
service rejects shell for source http
service rejects fake-codex for source http
service rejects dry-run for source http
service rejects missing target_project_id for source http
service replay with same idempotency_key returns same assignment id
```

Run:

```bash
python3.11 -m pytest tests/test_assign_ticket_service.py -q
```

Expected: fail because service does not exist.

- [ ] **Step 2: Implement service**

Create:

```python
class AssignTicketService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def execute(self, command: AssignTicketCommand) -> AssignTicketResultDto:
        existing = MutationIdempotencyStore(self.store.root).get("assign_ticket", command.idempotency_key)
        if existing is not None:
            return AssignTicketResultDto.model_validate(existing["response"])  # type: ignore[index]

        effective_profile = resolve_runtime_profile(command.runtime_profile, command.backend_name)
        validate_backend_for_source(command.source, command.backend_name, effective_profile)
        target = TargetProjectRegistry(self.store).resolve(command.target_project_id, runtime_profile=effective_profile)
        ticket = self.store.resolve_ticket(command.ticket_id)
        values = runtime_profile_values(effective_profile)
        if command.assignee_kind == "build_team":
            team = self.store.resolve_build_team(command.assignee_id)
            routed = route_ticket_to_build_team(
                self.store,
                ticket,
                team,
                backend_name=command.backend_name,
                planner_name=values.planner_name,
                agent_runtime=values.agent_runtime,
                backlog_planner_name=values.backlog_planner_name,
                target_repo_path=target.server_repo_path,
            )
            assignment = routed.assignment
        else:
            agent = self.store.resolve_agent_profile(command.assignee_id)
            assignment = self.store.create_assignment(
                ticket,
                agent,
                backend_name=command.backend_name,
                planner_name=values.planner_name,
                agent_runtime=values.agent_runtime,
                backlog_planner_name=values.backlog_planner_name,
            )
        assignment = assignment.model_copy(
            deep=True,
            update={
                "metadata": {
                    **assignment.metadata,
                    "target_project_id": target.id,
                    "target_resource_id": target.resource_id,
                    "target_project_label": target.label,
                }
            },
        )
        self.store.save_assignment(assignment)
        result = AssignTicketResultDto(
            assignment=AssignmentDto(
                id=assignment.id,
                ticket_id=assignment.ticket_id,
                ticket_key=assignment.ticket_key,
                agent_id=assignment.agent_id,
                backend_name=assignment.backend_name,
                status=assignment.status.value,
                target_project_id=target.id,
                confirmation_token=None,
            ),
            idempotency_key=command.idempotency_key,
        )
        MutationIdempotencyStore(self.store.root).record_success("assign_ticket", command.idempotency_key, result)
        return result
```

Keep exact naming aligned with real store APIs while implementing.

- [ ] **Step 3: Update CLI assign to use service**

`ticket assign` should parse Typer options, resolve whether `--to` points to a build team or an agent, create `AssignTicketCommand(source="cli", assignee_kind="build_team" | "agent")`, call service, and print the returned assignment. CLI may still allow fallback backends that HTTP rejects.

- [ ] **Step 4: Add CLI sharing test**

Patch `AssignTicketService.execute` in a test and assert `ari ticket assign` calls it once for direct agent assignment and once for build-team routing. Also keep behavioral CLI tests green.

- [ ] **Step 5: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_assign_ticket_service.py tests/test_cli_uses_application_services.py tests/test_agent_teammate_mode.py -q
git add ariadne_ltb/application/assign_ticket.py ariadne_ltb/cli.py tests/test_assign_ticket_service.py tests/test_cli_uses_application_services.py tests/test_agent_teammate_mode.py
git commit -m "feat: route ticket assignment through application service"
```

Expected: service tests and CLI regressions pass.

---

### Task 6: Run Assignment Service

**Files:**
- Create: `ariadne_ltb/application/run_assignment.py`
- Create: `ariadne_ltb/application/confirmation_tokens.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_run_assignment_service.py`
- Test: `tests/test_v1_daemon_supervision.py`
- Test: `tests/test_backend_smoke_cli.py`

- [ ] **Step 1: Write failing service tests**

Test cases:

```text
service runs one existing assignment through LocalDaemonWorker.run_once
service does not accept backend_name in request
service does not accept command in request
service does not accept target_repo_path in request
service rejects timeout below 1
service rejects timeout above 900
service replay with same idempotency_key does not run twice
blocked backend result remains visible as blocker
confirmation token is bound to assignment_id
confirmation token is bound to target_project_id
confirmation token is not accepted after expiry
```

Run:

```bash
python3.11 -m pytest tests/test_run_assignment_service.py -q
```

Expected: fail because service does not exist.

- [ ] **Step 2: Implement service**

Confirmation token rules:

```text
token is generated by server after assignment creation
token is stored only as a hashed value
token is bound to assignment_id, target_project_id, and backend_name
token has short expiry, default 15 minutes
token is never returned by /api/workbench
token is never returned by assignment timeline
token is never written into logs or evidence projections
```

Service rules:

```text
Load persisted assignment.
Read backend/planner/agent runtime from persisted assignment.
Validate confirmation_token through a server-side confirmation helper.
Call LocalDaemonWorker.run_once(assignment_id=assignment.id).
Record idempotency result.
Return RunAssignmentResultDto.
```

Do not use a static `"local-confirmed"` token for product code. Tests may mint a deterministic token through `ConfirmationTokenService.issue_for_assignment(assignment_id, target_project_id, backend_name)`, then pass that token into `RunAssignmentCommand`.

- [ ] **Step 3: Migrate daemon assignment run path**

Find the CLI command that runs a specific assignment and route it through `RunAssignmentService` when an assignment id is provided. Keep existing daemon loop behavior for background claim-next mode.

- [ ] **Step 4: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_run_assignment_service.py tests/test_v1_daemon_supervision.py tests/test_backend_smoke_cli.py -q
git add ariadne_ltb/application/run_assignment.py ariadne_ltb/application/confirmation_tokens.py ariadne_ltb/cli.py tests/test_run_assignment_service.py tests/test_v1_daemon_supervision.py tests/test_backend_smoke_cli.py
git commit -m "feat: run assignments through application service"
```

Expected: assignment run path still reaches daemon/orchestrator.

---

### Task 7: Comments, Assignment Timeline, Evidence Projection

**Files:**
- Create: `ariadne_ltb/application/comments.py`
- Create: `ariadne_ltb/application/run_events.py`
- Create: `ariadne_ltb/application/evidence_projection.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_comments_service.py`
- Test: `tests/test_assignment_timeline.py`
- Test: `tests/test_evidence_projection.py`
- Test: `tests/test_run_messages.py`
- Test: `tests/test_thread_comments.py`
- Test: `tests/test_workbench_data_sync.py`

- [ ] **Step 1: Write failing comment tests**

Test cases:

```text
AddTicketCommentService persists human comment
idempotency prevents duplicate comment
reply threading still works
comment linked to assignment appears in assignment timeline
```

- [ ] **Step 2: Write failing timeline tests**

Build a fixture ticket with:

```text
assignment queued
assignment claimed
runtime event started
run message status
human comment
blocked assignment
review verdict
```

Assert `RunEventsQueryService.list_assignment_events()` returns deterministic ordered events with cursor values.

- [ ] **Step 3: Write failing evidence projection tests**

Assert web projection excludes:

```text
command
command_path
command_template
command_template_env_var
safety_gate_env_var
handoff_file
target_repo_path
worktree_path
artifact_path
stdout
stderr
.ariadne absolute paths
API key-like values
provider failure payloads
confirmation_token
```

Assert it includes:

```text
artifact id
artifact type
result id
test status
changed file names
```

- [ ] **Step 4: Implement services**

DTO names:

```python
class AssignmentTimelineEventDto(StrictApplicationModel):
    id: str
    source: str
    timestamp: str
    assignment_id: str
    run_id: str | None = None
    stage: str
    event_type: str
    actor: str
    summary: str
    artifact_ref: str | None = None
    result_ref: str | None = None
    severity: Literal["info", "warning", "error"] = "info"
    cursor: str


class AssignmentTimelineDto(StrictApplicationModel):
    assignment_id: str
    events: list[AssignmentTimelineEventDto]
    next_cursor: str | None = None
```

Ordering:

```text
timestamp
source priority: assignment, runtime_event, run_message, comment, review, blocker
stable id or run message sequence
```

Redaction matrix:

| Projection | Must Exclude | May Include |
|---|---|---|
| `/api/workbench` | `confirmation_token`, `command`, `command_path`, `command_template`, `target_repo_path`, `worktree_path`, raw `.ariadne` paths | backend labels, availability, ticket ids, assignment ids, artifact ids |
| `/api/assignments/{assignment_id}/events` | `confirmation_token`, raw stdout, raw stderr, command templates, handoff file path, absolute local paths | safe summaries, event ids, artifact ids, result ids, status labels |
| Evidence projection | raw stdout, raw stderr, provider failure payloads, env var names and values, secret-looking strings | changed file names, test status, artifact type, result id |

- [ ] **Step 5: Migrate CLI comment**

`ari ticket comment` should call `AddTicketCommentService` with `source="cli"` and generated idempotency key.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_comments_service.py tests/test_assignment_timeline.py tests/test_evidence_projection.py tests/test_run_messages.py tests/test_thread_comments.py tests/test_workbench_data_sync.py -q
git add ariadne_ltb/application/comments.py ariadne_ltb/application/run_events.py ariadne_ltb/application/evidence_projection.py ariadne_ltb/application/dtos.py ariadne_ltb/cli.py tests/test_comments_service.py tests/test_assignment_timeline.py tests/test_evidence_projection.py tests/test_run_messages.py tests/test_thread_comments.py tests/test_workbench_data_sync.py
git commit -m "feat: add comments timeline and safe evidence projections"
```

Expected: timeline and redaction tests pass.

---

### Task 8: Local HTTP Control Plane

**Files:**
- Modify: `pyproject.toml`
- Create: `ariadne_ltb/interfaces/__init__.py`
- Create: `ariadne_ltb/interfaces/http/__init__.py`
- Create: `ariadne_ltb/interfaces/http/app.py`
- Create: `ariadne_ltb/interfaces/http/dependencies.py`
- Create: `ariadne_ltb/interfaces/http/errors.py`
- Create: `ariadne_ltb/interfaces/http/routes.py`
- Create: `ariadne_ltb/interfaces/http/schemas.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_control_plane_http.py`
- Test: `tests/test_http_contract_rejects_dangerous_fields.py`

- [ ] **Step 1: Write failing HTTP tests**

Use `fastapi.testclient.TestClient`. Cover:

```text
GET /api/workbench returns schema_version
GET /api/runtime/status excludes shell
POST /api/tickets/{ticket_id}/assign creates assignment
POST /api/assignments/{assignment_id}/run calls run service
GET /api/assignments/{assignment_id}/events returns timeline
POST /api/tickets/{ticket_id}/comments writes human comment
unknown JSON field rejected with 400
command field rejected with 400
target_repo_path field rejected with 400
shell backend rejected with 400 or 403
POST body over max size returns 413
non-JSON mutation body returns 415 or 400
default server host is 127.0.0.1
/api/workbench does not serialize confirmation_token
/api/assignments/{assignment_id}/events does not serialize confirmation_token or raw paths
```

Run:

```bash
python3.11 -m pytest tests/test_control_plane_http.py tests/test_http_contract_rejects_dangerous_fields.py -q
```

Expected: fail because HTTP interface does not exist.

- [ ] **Step 2: Add FastAPI dependencies**

Modify `pyproject.toml`:

```toml
dependencies = [
  "fastapi>=0.115",
  "pydantic>=2.0",
  "typer>=0.12",
  "uvicorn>=0.30",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.27",
  "pytest>=8",
  "ruff>=0.6",
]
```

`httpx` is required for FastAPI `TestClient`. Do not add database, auth, Celery, Redis, or background-worker dependencies for this P0.

- [ ] **Step 3: Implement FastAPI app factory**

Create `ariadne_ltb/interfaces/http/app.py`:

```python
from fastapi import FastAPI

from ariadne_ltb.interfaces.http.errors import install_exception_handlers
from ariadne_ltb.interfaces.http.routes import router


def create_app(root: str | None = None) -> FastAPI:
    app = FastAPI(
        title="Ariadne Local Agent Control Plane",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.state.ariadne_root = root
    install_exception_handlers(app)
    app.include_router(router, prefix="/api")
    return app
```

Create `ariadne_ltb/interfaces/http/dependencies.py`:

```python
from fastapi import Request

from ariadne_ltb.storage import AriadneStore


def get_store(request: Request) -> AriadneStore:
    root = request.app.state.ariadne_root
    return AriadneStore(root)
```

- [ ] **Step 4: Implement route modules**

Create routes using `APIRouter`:

```text
GET /api/health
GET /api/workbench
GET /api/runtime/status
POST /api/tickets/{ticket_id}/assign
POST /api/assignments/{assignment_id}/run
GET /api/assignments/{assignment_id}/events
POST /api/tickets/{ticket_id}/comments
```

All routes must call application services. Routes must not call `AriadneStore.create_assignment`, `LocalDaemonWorker.run_once`, or `TicketRunOrchestrator.run_ticket` directly.

Use response shape:

```json
{
  "ok": true,
  "data": {}
}
```

Use error shape:

```json
{
  "ok": false,
  "error": {
    "code": "invalid_request",
    "message": "Human-readable message",
    "details": {}
  }
}
```

- [ ] **Step 5: Add FastAPI middleware and error handlers**

Server safety defaults:

```text
default host is 127.0.0.1
binding 0.0.0.0 prints an explicit warning before serving
maximum request body is 1 MiB
mutation routes require Content-Type: application/json
CORS is not enabled by default
errors do not include stack traces
errors do not include raw local paths
```

- [ ] **Step 6: Add CLI command**

Add:

```bash
ari api serve --host 127.0.0.1 --port 8766
python3.11 -m ariadne_ltb.cli api serve --host 127.0.0.1 --port 8766
```

The command should print:

```text
Ariadne local API listening on http://127.0.0.1:8766
```

Implementation should call:

```python
import uvicorn

from ariadne_ltb.interfaces.http.app import create_app

uvicorn.run(create_app(root=str(state.root)), host=host, port=port, log_level="info")
```

If `host == "0.0.0.0"`, print an explicit local security warning before serving.

- [ ] **Step 7: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_control_plane_http.py tests/test_http_contract_rejects_dangerous_fields.py -q
git add pyproject.toml ariadne_ltb/interfaces ariadne_ltb/cli.py tests/test_control_plane_http.py tests/test_http_contract_rejects_dangerous_fields.py
git commit -m "feat: add local api control plane"
```

Expected: HTTP tests pass and dangerous fields are rejected.

---

### Task 9: Frontend API Client And Data Source

**Files:**
- Create: `frontend/ariadne-workbench/src/shared/api/types.ts`
- Create: `frontend/ariadne-workbench/src/shared/api/client.ts`
- Create: `frontend/ariadne-workbench/src/shared/api/errors.ts`
- Modify: `frontend/ariadne-workbench/src/data.ts`
- Modify: `frontend/ariadne-workbench/src/types.ts`
- Modify: `frontend/ariadne-workbench/README.md`
- Test: `tests/test_frontend_api_contract_static.py`

- [ ] **Step 1: Write static contract tests**

Use Python tests to read frontend source and assert:

```text
shared/api/client.ts exists
AssignTicketRequest does not contain command
AssignTicketRequest does not contain target_repo_path
AssignTicketRequest contains assignee_id
AssignTicketRequest contains assignee_kind
RunAssignmentRequest does not contain backend_name
RunAssignmentRequest does not contain command
RunAssignmentRequest does not contain target_repo_path
client fetches /api/workbench before /web_data/workbench.json
snapshot fallback is labeled read-only
```

Run:

```bash
python3.11 -m pytest tests/test_frontend_api_contract_static.py -q
```

Expected: fail because frontend API client does not exist.

- [ ] **Step 2: Implement frontend API types**

Define TypeScript types:

```ts
export type ApiDataSource = "api" | "snapshot" | "fixture";

export type AssignTicketRequest = {
  assignee_id: string;
  assignee_kind: "agent" | "build_team";
  backend_name: "codex" | "claude-code";
  runtime_profile: "production";
  target_project_id: string;
  idempotency_key: string;
};

export type RunAssignmentRequest = {
  confirmation_token: string;
  timeout_seconds?: number;
  idempotency_key: string;
};

export type AddTicketCommentRequest = {
  body: string;
  idempotency_key: string;
  parent_comment_id?: string;
  assignment_id?: string;
};
```

- [ ] **Step 3: Implement API client**

Functions:

```text
getWorkbench()
getRuntimeStatus()
assignTicket(ticketId, request)
runAssignment(assignmentId, request)
getAssignmentEvents(assignmentId, since)
addTicketComment(ticketId, request)
```

All functions should parse `{ ok, data }` and `{ ok, error }`.

- [ ] **Step 4: Update data source**

`loadWorkbenchData()` should try:

```text
/api/workbench
/web_data/workbench.json
fixture
```

Return source metadata:

```ts
{ data, source: "api" | "snapshot" | "fixture", readOnly: boolean }
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_frontend_api_contract_static.py -q
cd frontend/ariadne-workbench && npm run typecheck && npm run build
git add frontend/ariadne-workbench/src/shared/api frontend/ariadne-workbench/src/data.ts frontend/ariadne-workbench/src/types.ts frontend/ariadne-workbench/README.md tests/test_frontend_api_contract_static.py
git commit -m "feat: add workbench api client"
```

Expected: frontend builds and static contract test passes.

---

### Task 10: Frontend Entities And Runtime Filtering

**Files:**
- Create: `frontend/ariadne-workbench/src/entities/runtime/model.ts`
- Create: `frontend/ariadne-workbench/src/entities/runtime/lib.ts`
- Create: `frontend/ariadne-workbench/src/entities/assignment/model.ts`
- Create: `frontend/ariadne-workbench/src/entities/ticket/model.ts`
- Create: `frontend/ariadne-workbench/src/entities/target-project/model.ts`
- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Test: `tests/test_frontend_api_contract_static.py`

- [ ] **Step 1: Add static tests**

Add assertions:

```text
runtime filter excludes shell
runtime filter marks fake-codex fallbackOnly
runtime filter marks dry-run fallbackOnly
assign action requires targetProjectId
```

- [ ] **Step 2: Implement runtime entity helper**

Function:

```ts
export function selectableProductionRuntimes(runtimes: RuntimeCapability[]): RuntimeCapability[] {
  return runtimes.filter((runtime) => {
    if (runtime.backendName === "shell") return false;
    if (runtime.fallbackOnly) return false;
    return runtime.canAssign || runtime.canRun;
  });
}
```

- [ ] **Step 3: Wire App runtime options to helper**

Use redacted API runtimes for action controls. Existing display-only runtime panels may still show fallback runtimes with explicit labels.

- [ ] **Step 4: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_frontend_api_contract_static.py -q
cd frontend/ariadne-workbench && npm run typecheck && npm run build
git add frontend/ariadne-workbench/src/entities frontend/ariadne-workbench/src/App.tsx tests/test_frontend_api_contract_static.py
git commit -m "feat: add frontend control plane entities"
```

Expected: frontend build passes and shell is not selectable for actions.

---

### Task 11: Frontend Assign, Run, Watch, Comment Features

**Files:**
- Create: `frontend/ariadne-workbench/src/features/assign-ticket/model.ts`
- Create: `frontend/ariadne-workbench/src/features/assign-ticket/api.ts`
- Create: `frontend/ariadne-workbench/src/features/assign-ticket/ui.tsx`
- Create: `frontend/ariadne-workbench/src/features/run-assignment/model.ts`
- Create: `frontend/ariadne-workbench/src/features/run-assignment/api.ts`
- Create: `frontend/ariadne-workbench/src/features/run-assignment/ui.tsx`
- Create: `frontend/ariadne-workbench/src/features/watch-run-events/model.ts`
- Create: `frontend/ariadne-workbench/src/features/watch-run-events/api.ts`
- Create: `frontend/ariadne-workbench/src/features/watch-run-events/ui.tsx`
- Create: `frontend/ariadne-workbench/src/features/add-ticket-comment/model.ts`
- Create: `frontend/ariadne-workbench/src/features/add-ticket-comment/api.ts`
- Create: `frontend/ariadne-workbench/src/features/add-ticket-comment/ui.tsx`
- Create: `frontend/ariadne-workbench/src/shared/lib/idempotency.ts`
- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Modify: `frontend/ariadne-workbench/src/styles.css`
- Test: `tests/test_frontend_api_contract_static.py`

- [ ] **Step 1: Extend static tests**

Assert source contains:

```text
POST /api/tickets/
POST /api/assignments/
GET /api/assignments/
POST /api/tickets/{ticket_id}/comments path builder
idempotency key generator
readOnly disables assign/run/comment
```

- [ ] **Step 2: Implement idempotency helper**

Use:

```ts
export function createIdempotencyKey(prefix: string): string {
  const randomPart = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${randomPart}`;
}
```

- [ ] **Step 3: Implement feature models**

State machine:

```text
idle
assigning
assigned
running
watching
blocked
completed
api_unavailable_readonly
error
```

- [ ] **Step 4: Implement UI slices**

Expose controls:

```text
Assign selected ticket
Run selected assignment
Watch events
Add ticket comment
```

Disable controls when:

```text
data source is snapshot or fixture
selected ticket missing
selected runtime missing
target project missing
runtime fallback_only true
runtime canAssign false for assign
runtime canRun false for run
```

- [ ] **Step 5: Wire into App**

Keep current `App.tsx` structure for P0, but move new action logic into feature files. Do not perform broad FSD extraction in this task.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
python3.11 -m pytest tests/test_frontend_api_contract_static.py -q
cd frontend/ariadne-workbench && npm run typecheck && npm run build
git add frontend/ariadne-workbench/src/features frontend/ariadne-workbench/src/shared/lib frontend/ariadne-workbench/src/App.tsx frontend/ariadne-workbench/src/styles.css tests/test_frontend_api_contract_static.py
git commit -m "feat: add frontend agent action features"
```

Expected: frontend builds and action controls are API-backed.

---

### Task 12: End-To-End Control Plane Verification

**Files:**
- Create: `tests/test_control_plane_end_to_end.py`
- Create: `tests/test_frontend_control_plane_e2e.py`
- Modify: `README.md`
- Modify: `docs/development_report.md`
- Modify: `frontend/ariadne-workbench/README.md`
- Modify: `frontend/ariadne-workbench/package.json`
- Modify: `scripts/verify_v1.sh`

- [ ] **Step 1: Write end-to-end test**

Test flow:

```text
create test store
register target project
ingest or create one ticket
GET /api/workbench
POST /api/tickets/{ticket_id}/assign
POST /api/assignments/{assignment_id}/run against fallback-safe backend in test mode
GET /api/assignments/{assignment_id}/events
POST /api/tickets/{ticket_id}/comments
assert assignment timeline contains assign, run, event, comment
```

Use deterministic/offline backend only inside automated tests. Do not require Codex, Claude, DeepSeek, Feishu, GitHub, or network.

- [ ] **Step 2: Add browser-level E2E verification**

Add `tests/test_frontend_control_plane_e2e.py` or an equivalent Playwright-backed test.

This test must:

```text
start the local API against a temporary store
register a target project using the same path as ari target-project register
start the Vite workbench on 127.0.0.1
open the browser
select a ticket
select a production-capable runtime
select a registered target project
click Assign
click Run
watch events appear
add a human comment
assert the UI shows assignment id, run status or event timeline, and comment text
```

If Playwright is not already installed, add it as a frontend dev dependency and add a script:

```json
{
  "scripts": {
    "e2e": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.56.0"
  }
}
```

The E2E test must not use real Codex, Claude, DeepSeek, Feishu, GitHub, or network. It may use the `source="test"` application path with fallback-safe backend only inside the test harness. The UI must still hide fallback runtimes in normal product mode.

Run:

```bash
python3.11 -m pytest tests/test_frontend_control_plane_e2e.py -q
cd frontend/ariadne-workbench && npm run typecheck && npm run build
```

Acceptance: static source checks are not sufficient for P0. The implementation is not accepted until the browser UI performs `assign -> run -> watch -> comment` against `/api/*`.

- [ ] **Step 3: Update verification script**

`scripts/verify_v1.sh` should have sections:

```text
static checks
offline deterministic verification
local api control plane verification
frontend build verification
optional real integration smoke verification
```

- [ ] **Step 4: Update docs**

README must say:

```text
Primary product path: local API control plane plus frontend actions.
Offline snapshot path: read-only fallback.
fake-codex and dry-run: tests and fallback only.
```

Development report must include:

```text
implemented application services
HTTP endpoints
frontend actions
what remains P1/P2
commands run
known limitations
```

- [ ] **Step 5: Run full verification**

Run:

```bash
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run typecheck && npm run build
python3.11 -m pytest tests/test_frontend_control_plane_e2e.py -q
python3.11 -m ariadne_ltb.cli doctor product --require-acceptance-ready
python3.11 -m ariadne_ltb.cli api serve --host 127.0.0.1 --port 8766
```

For the API server command, start it in a disposable background process during manual verification, then request:

```bash
curl -s http://127.0.0.1:8766/api/health
curl -s http://127.0.0.1:8766/api/workbench
```

- [ ] **Step 6: Commit**

Run:

```bash
git add tests/test_control_plane_end_to_end.py tests/test_frontend_control_plane_e2e.py README.md docs/development_report.md frontend/ariadne-workbench/README.md frontend/ariadne-workbench/package.json scripts/verify_v1.sh
git commit -m "docs: document local api control plane"
```

Expected: verification passes and documentation reflects the new product path.

---

## P1 Follow-Up Plan

After P0 is accepted, implement:

1. `RouteTicketService` and `POST /api/tickets/{ticket_id}/route`.
2. `RecoverInboxItemService` and `POST /api/inbox/{item_id}/recover`.
3. Frontend `features/route-ticket`.
4. Frontend `features/recover-inbox-item`.
5. Build team and agent profile management UI.
6. Full FSD extraction:
   - `app/`
   - `pages/`
   - `widgets/`
   - `features/`
   - `entities/`
   - `shared/`
7. Split `ariadne_ltb/cli.py` into `ariadne_ltb/interfaces/cli/`.
8. Split `AriadneStore` into smaller repository modules.

## Final Acceptance Criteria

This implementation is done only when:

1. `ari api serve --host 127.0.0.1 --port 8766` starts a local API server.
2. `GET /api/workbench` returns `schema_version="ariadne.workbench.v1"`.
3. Browser data loading prefers `/api/workbench`.
4. Snapshot fallback remains available but is read-only.
5. `ari target-project register` creates a registered target project visible in `GET /api/workbench`.
6. Browser can create an assignment through `POST /api/tickets/{ticket_id}/assign`.
7. Browser can route to either direct agent or build team through the same assign service.
8. Browser can run an assignment through `POST /api/assignments/{assignment_id}/run`.
9. Browser can poll events through `GET /api/assignments/{assignment_id}/events`.
10. Browser can write a ticket comment through `POST /api/tickets/{ticket_id}/comments`.
11. Browser E2E test clicks through `assign -> run -> watch -> comment`.
12. HTTP handlers call application services.
13. CLI assign/comment/assignment-run paths call the same application services or have regression tests proving behavior parity.
14. HTTP mutation schemas reject dangerous fields.
15. Web runtime capability output excludes `shell`.
16. Browser product actions do not expose `fake-codex` or `dry-run`.
17. Production API actions require `target_project_id`.
18. Production API actions do not call `ensure_demo_target_project()`.
19. Raw evidence remains locally persisted.
20. Web evidence projections are redacted.
21. Existing CLI product tests pass.
22. Frontend `npm run typecheck` passes.
23. Frontend `npm run build` passes.
24. `pytest` passes without external credentials.

## Plan Self-Review

Spec coverage:

- Multica-style issue-agent-runtime gap is covered by Tasks 5, 6, 8, 11, and 12.
- API control plane gap is covered by Tasks 1 through 8.
- Frontend action gap is covered by Tasks 9 through 11.
- Target project and demo fallback risk is covered by Task 2.
- Runtime capability redaction is covered by Task 3.
- Timeline and visible progress are covered by Task 7.
- CLI/HTTP shared service boundary is covered by Tasks 5, 6, 7, and 12.

Placeholder scan:

- This plan avoids placeholder words and incomplete task descriptions.
- Every task lists exact files, tests, commands, and acceptance criteria.

Type consistency:

- Backend command DTO names are `AssignTicketCommand`, `RunAssignmentCommand`, and `AddTicketCommentCommand`.
- Backend result DTO names are `AssignTicketResultDto`, `RunAssignmentResultDto`, and `AddTicketCommentResultDto`.
- Frontend request names match backend command intent: `AssignTicketRequest`, `RunAssignmentRequest`, and `AddTicketCommentRequest`.
