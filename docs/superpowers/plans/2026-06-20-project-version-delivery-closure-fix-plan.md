# Project Version Delivery Closure Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current Workbench modules into one browser-first Project Version Delivery loop: project goal + external inputs -> issue delta -> agent team handoff -> scoped daemon -> real Codex/Claude execution -> diff/tests/review/memory/next issues -> visible version progress.

**Architecture:** Add read-model projections over the existing local-first JSON store instead of replacing the runtime. The Workbench becomes delivery-first: `current_version_delivery`, `project_inputs`, `issue_projection`, `agent_workflows`, `environment`, and scoped daemon/inbox recovery all come from real artifacts/events, not static copy.

**Tech Stack:** Python 3.11, Pydantic v2 DTOs, FastAPI-style local control plane, Typer CLI where needed, React/TypeScript Workbench, Playwright browser dogfood, pytest, ruff.

---

## Non-Negotiable Closure Rule

Ariadne is not closed by module tests, CLI demos, blocked-ok rehearsals, static fixture pages, or docs.

Closure means this command succeeds and writes evidence:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
```

The run must prove, through browser UI and target repo evidence:

1. User creates or selects a target project and version.
2. User adds external inputs through the Workbench.
3. Ariadne analyzes sources and shows what it understood.
4. Ariadne proposes issue deltas tied to source evidence and target version.
5. User confirms issue deltas.
6. User selects a current issue/assignment in the Workbench.
7. Daemon is scoped to that assignment or current delivery context.
8. Codex or Claude runs against the target repo.
9. Diff, changed files, tests, review, memory, and next tickets return to the Workbench.
10. The target project has a runnable version or the result is explicitly `BLOCKED_NOT_CLOSED`.

`fake-codex`, `demo full`, `blocked-ok`, and offline fixture flows may remain as regression tools only. They cannot satisfy this plan.

## Subagent Review Inputs Integrated

This plan integrates eight focused reviews:

1. Project Version Delivery read model and first screen.
2. Mainline issue vs repair/history isolation.
3. Current evidence lineage vs historical blocker supersession.
4. Workbench API/offline/environment boundary.
5. Project input lifecycle and typed source detail.
6. Issue Factory task delta confirmation.
7. Agent Team artifact handoff visibility.
8. Scoped runtime/inbox recovery and hard dogfood evidence.

## File Structure

Backend DTOs and projections:

- Modify: `ariadne_ltb/application/dtos.py`
  - Add DTOs for project delivery, issue projection, source lifecycle, environment, agent workflow, runtime scope, inbox recovery, dogfood proof.
- Modify: `ariadne_ltb/application/workbench_projection.py`
  - Compose the new projections into `/api/workbench`.
- Create: `ariadne_ltb/application/project_version_delivery.py`
  - Compute the current version delivery state from goals, sources, tickets, assignments, execution results, review, memory, and next tickets.
- Create: `ariadne_ltb/application/issue_projection.py`
  - Classify tickets into mainline, repair, generated follow-up, and history.
- Create: `ariadne_ltb/application/ticket_current_state.py`
  - Compute current success/blocker/historical blocker state per ticket.
- Create: `ariadne_ltb/application/project_inputs.py`
  - Build source-centric project input details from source documents, fetch records, artifacts, evidence, and previews.
- Create: `ariadne_ltb/application/workbench_environment.py`
  - Project real API/offline mode, target repo path, execution gate, backend availability, and blockers.
- Create: `ariadne_ltb/application/agent_workflow_projection.py`
  - Project agent team steps from artifacts, handoffs, assignments, runs, comments, runtime events, reviews, memory, and next-ticket artifacts.
- Create: `ariadne_ltb/application/inbox_recovery.py`
  - Classify inbox items into safe rerun, repair ticket required, confirmation required, human required, and superseded/historical.
- Modify: `ariadne_ltb/application/inbox_actions.py`
  - Use recovery classification and return next assignment/repair ticket/scope hints.
- Modify: `ariadne_ltb/inbox.py`
  - Stop resurfacing historical blockers after a newer current success.
- Modify: `ariadne_ltb/models.py`
  - Add additive optional lineage fields where needed: execution assignment/run ids, supersession metadata, inbox archive metadata.
- Modify: `ariadne_ltb/orchestrator.py`
  - Record agent-role metadata in progress events; link execution result to assignment/run; avoid flattening all agent stages to one actor.
- Modify: `ariadne_ltb/daemon.py`
  - Propagate target-project/backend scope into assignment claim.
- Modify: `ariadne_ltb/application/daemon_control.py`
  - Make daemon scope explicit and updatable even when the loop is already running.
- Modify: `ariadne_ltb/interfaces/http/routes.py`
  - Expose source detail, issue-factory refresh/apply decisions, scoped daemon status/start, inbox recover, and stronger health mode.

Frontend Workbench:

- Modify: `frontend/ariadne-workbench/src/shared/api/types.ts`
  - Add API types for the new projections.
- Modify: `frontend/ariadne-workbench/src/types.ts`
  - Add UI domain types for delivery, input lifecycle, issue projection, agent workflow, runtime scope, inbox recovery, environment.
- Modify: `frontend/ariadne-workbench/src/data.ts`
  - Map all new API projections. Remove guesswork based on Chinese labels.
- Modify: `frontend/ariadne-workbench/src/App.tsx`
  - Add `#delivery` as default. Rework Sources, Tasks, Issues, Agents, Runtime, Inbox, and TicketInspector around the new projections.
- Modify: `frontend/ariadne-workbench/src/features/agent-control/model.ts`
  - Always scope daemon to the current assignment/delivery before running.
- Create: `frontend/ariadne-workbench/src/features/project-version-delivery/model.ts`
  - Pure view helpers for delivery progress, gates, and evidence labels.
- Create: `frontend/ariadne-workbench/src/features/project-version-delivery/ui.tsx`
  - Delivery first screen components.
- Create: `frontend/ariadne-workbench/src/features/project-inputs/ui.tsx`
  - Source lifecycle/detail components.
- Create: `frontend/ariadne-workbench/src/features/agent-workflow/ui.tsx`
  - Agent Team Run stepper and activity stream.
- Create: `frontend/ariadne-workbench/src/features/runtime-scope/ui.tsx`
  - Scoped daemon queue/status/recovery UI.
- Modify: `frontend/ariadne-workbench/src/styles.css`
  - Layout and state styles for delivery, input lifecycle, agent workflow, and recovery cards.

Verification and docs:

- Modify: `scripts/verify_dogfood_browser.sh`
  - Make real mode the closure path. Blocker recording is not success.
- Modify: `frontend/ariadne-workbench/e2e/mini-code-agent-dogfood.spec.ts`
  - Record successful UI evidence, target repo evidence, and structured closure packet.
- Create: `scripts/verify_dogfood_result_packet.py`
  - Validate result packet shape and target repo evidence.
- Create: `docs/dogfood/templates/REAL_BROWSER_DOGFOOD_RESULT.md`
  - Result packet template for `REAL_CLOSED` or `BLOCKED_NOT_CLOSED`.
- Modify: `docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md`
  - Point to browser-first closure requirements.
- Modify: `README.md`
  - Separate release readiness from real browser dogfood closure.
- Modify: `docs/ops/V1_RELEASE_CHECKLIST.md`
  - Do not allow blocked-ok/demo/doctor to satisfy product closure.
- Modify: `docs/ops/HUMAN_DEMO_SCRIPT.md`
  - Rename demo language to offline/rehearsal where applicable.

Tests:

- Create: `tests/test_project_version_delivery_projection.py`
- Create: `tests/test_issue_projection.py`
- Create: `tests/test_ticket_current_state.py`
- Create: `tests/test_project_inputs_projection.py`
- Create: `tests/test_workbench_environment.py`
- Create: `tests/test_agent_workflow_projection.py`
- Modify: `tests/test_control_plane_http.py`
- Modify: `tests/test_workbench_daemon_feedback.py`
- Modify: `tests/test_inbox.py`
- Modify: `tests/test_assignment_claim_state_machine.py`
- Modify: `tests/test_frontend_api_contract_static.py`
- Modify: `tests/test_workbench_data_sync.py`

---

## Task 1: Add Project Version Delivery Projection

**Files:**
- Create: `ariadne_ltb/application/project_version_delivery.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/workbench_projection.py`
- Create: `tests/test_project_version_delivery_projection.py`
- Modify: `tests/test_control_plane_http.py`

- [ ] **Step 1: Add DTOs**

In `ariadne_ltb/application/dtos.py`, add:

```python
class DeliveryGateDTO(AriadneDTO):
    id: str
    label: str
    status: str
    detail: str = ""
    ref_id: str | None = None


class LatestRealRunDTO(AriadneDTO):
    ticket_key: str
    assignment_id: str | None = None
    backend_name: str
    execution_result_id: str
    exit_code: int | None = None
    test_exit_code: int | None = None
    review_verdict: str | None = None
    dry_run: bool
    blocked: bool
    changed_files: list[str] = Field(default_factory=list)
    handoff_file: str | None = None
    diff_artifact_path: str | None = None
    execution_log_artifact_path: str | None = None
    memory_path: str | None = None
    next_tickets_path: str | None = None


class DeliveryItemDTO(AriadneDTO):
    ticket_id: str
    ticket_key: str
    title: str
    status: str
    priority: str
    target_project_id: str | None = None
    assignment_id: str | None = None
    assignment_status: str | None = None
    backend_name: str | None = None
    route_decision_id: str | None = None
    handoff_packet_id: str | None = None
    build_context_id: str | None = None
    execution_result_id: str | None = None
    dry_run: bool | None = None
    blocked: bool | None = None
    exit_code: int | None = None
    test_command: str | None = None
    test_exit_code: int | None = None
    review_verdict: str | None = None
    memory_path: str | None = None
    feishu_plan_path: str | None = None
    next_tickets_path: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    evidence_status: str = "missing"


class ProjectVersionDeliveryDTO(AriadneDTO):
    id: str
    version_label: str
    status: str
    goal_id: str | None = None
    target_project_id: str | None = None
    target_project_label: str | None = None
    current_state: str
    target_state: str
    summary: str
    generated_at: str
    progress_counts: dict[str, int] = Field(default_factory=dict)
    gates: list[DeliveryGateDTO] = Field(default_factory=list)
    delivery_items: list[DeliveryItemDTO] = Field(default_factory=list)
    latest_real_run: LatestRealRunDTO | None = None
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
```

Add `current_version_delivery: ProjectVersionDeliveryDTO | None = None` to `WorkbenchDTO`.

- [ ] **Step 2: Write projection tests**

In `tests/test_project_version_delivery_projection.py`, create fixture helpers that save:

```python
def test_real_codex_success_sets_real_closed(store):
    delivery = build_current_version_delivery(store_with_real_codex_pass())
    assert delivery.status == "real_closed"
    assert delivery.latest_real_run is not None
    assert delivery.latest_real_run.backend_name == "codex"
    assert delivery.latest_real_run.dry_run is False
    assert delivery.latest_real_run.blocked is False
    assert delivery.latest_real_run.exit_code == 0
    assert delivery.latest_real_run.test_exit_code == 0
    assert delivery.latest_real_run.review_verdict == "pass"


def test_fake_or_dry_run_never_sets_real_closed(store):
    delivery = build_current_version_delivery(store_with_fake_codex_pass())
    assert delivery.status != "real_closed"
    assert "真实 Codex/Claude 执行证据缺失" in delivery.blockers


def test_blocked_real_run_sets_blocked(store):
    delivery = build_current_version_delivery(store_with_blocked_real_run())
    assert delivery.status == "blocked"
    assert delivery.latest_real_run is not None
    assert delivery.latest_real_run.blocked is True
```

Use existing model factories or minimal model construction already used in nearby tests. Do not require external Codex.

- [ ] **Step 3: Implement projection**

Create `ariadne_ltb/application/project_version_delivery.py`:

```python
from __future__ import annotations

from ariadne_ltb.application.dtos import (
    DeliveryGateDTO,
    DeliveryItemDTO,
    LatestRealRunDTO,
    ProjectVersionDeliveryDTO,
)
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.models import utc_now


REAL_BACKENDS = {"codex", "claude-code", "claude"}


def build_current_version_delivery(store: AriadneStore) -> ProjectVersionDeliveryDTO | None:
    goals = store.list_project_goals()
    target_projects = store.load_project_resources()
    tickets = store.list_tickets()
    if not goals and not target_projects and not tickets:
        return None

    goal = goals[-1] if goals else None
    target_project_id = _active_target_project_id(goal, tickets)
    target = next((item for item in target_projects if item.id == target_project_id), None)
    delivery_items = [_delivery_item(store, ticket) for ticket in tickets if _belongs_to_target(ticket, target_project_id)]
    latest_real_run = _latest_real_run(store, delivery_items)
    gates = _gates(store, delivery_items, latest_real_run)
    status = _status(gates, latest_real_run)
    blockers = [gate.detail for gate in gates if gate.status == "blocked"]

    return ProjectVersionDeliveryDTO(
        id=f"delivery:{target_project_id or 'default'}",
        version_label=_version_label(goal, target),
        status=status,
        goal_id=goal.id if goal else None,
        target_project_id=target_project_id,
        target_project_label=target.label if target else None,
        current_state=_current_state(delivery_items, latest_real_run),
        target_state=_target_state(goal),
        summary=_summary(status, delivery_items, latest_real_run),
        generated_at=utc_now().isoformat(),
        progress_counts=_progress_counts(delivery_items),
        gates=gates,
        delivery_items=delivery_items,
        latest_real_run=latest_real_run,
        blockers=blockers,
        next_actions=_next_actions(status, gates),
        evidence_refs=[item.execution_result_id for item in delivery_items if item.execution_result_id],
    )
```

Implement helpers conservatively. `real_closed` requires backend in `REAL_BACKENDS`, `dry_run is False`, `blocked is False`, `exit_code == 0`, `test_exit_code in {0, None}`, and review verdict `pass`.

- [ ] **Step 4: Expose in Workbench projection**

In `ariadne_ltb/application/workbench_projection.py`, import and call:

```python
from ariadne_ltb.application.project_version_delivery import build_current_version_delivery
```

Set:

```python
current_version_delivery=build_current_version_delivery(self.store),
```

- [ ] **Step 5: Verify**

Run:

```bash
python3.11 -m pytest tests/test_project_version_delivery_projection.py tests/test_control_plane_http.py -q
```

Expected: pass.

---

## Task 2: Split Mainline Issues From Repair and History

**Files:**
- Create: `ariadne_ltb/application/issue_projection.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/workbench_projection.py`
- Modify: `ariadne_ltb/application/issue_factory.py`
- Modify: `ariadne_ltb/application/inbox_actions.py`
- Create: `tests/test_issue_projection.py`
- Modify: `frontend/ariadne-workbench/src/shared/api/types.ts`
- Modify: `frontend/ariadne-workbench/src/types.ts`
- Modify: `frontend/ariadne-workbench/src/data.ts`
- Modify: `frontend/ariadne-workbench/src/App.tsx`

- [ ] **Step 1: Add issue projection DTOs**

Add to `ariadne_ltb/application/dtos.py`:

```python
class IssueChildDTO(AriadneDTO):
    ticket_id: str
    ticket_key: str
    title: str
    issue_class: str
    origin: str
    status: str
    parent_ticket_key: str | None = None
    root_ticket_key: str
    reason: str = ""


class IssueFamilyDTO(AriadneDTO):
    ticket_id: str
    ticket_key: str
    title: str
    status: str
    priority: str
    root_ticket_key: str
    repair_count: int = 0
    open_repair_count: int = 0
    history_count: int = 0
    child_ticket_keys: list[str] = Field(default_factory=list)
    latest_repair_summary: str | None = None


class IssueProjectionDTO(AriadneDTO):
    summary: dict[str, int] = Field(default_factory=dict)
    mainline_tickets: list[IssueFamilyDTO] = Field(default_factory=list)
    repair_items: list[IssueChildDTO] = Field(default_factory=list)
    history_items: list[IssueChildDTO] = Field(default_factory=list)
```

Add `issue_projection: IssueProjectionDTO | None = None` to `WorkbenchDTO`.

- [ ] **Step 2: Implement classifier**

Create `ariadne_ltb/application/issue_projection.py` with:

```python
def classify_ticket(ticket: BuildTicket) -> tuple[str, str, str]:
    metadata = ticket.metadata
    if metadata.get("issue_class"):
        return str(metadata["issue_class"]), str(metadata.get("origin") or "manual"), str(metadata.get("root_ticket_key") or ticket.key)
    if metadata.get("source_ticket_key") or metadata.get("parent_ticket_key"):
        return "repair", str(metadata.get("origin") or "inbox_recovery"), str(metadata.get("source_ticket_key") or metadata.get("parent_ticket_key"))
    if metadata.get("generated_from_ticket_key"):
        return "generated_followup", "llm_next_ticket", str(metadata["generated_from_ticket_key"])
    title = ticket.title.lower()
    if title.startswith("repair ") or title.startswith("fix review") or "repair execution" in title:
        return "repair", "repair_inferred", str(metadata.get("root_ticket_key") or ticket.key)
    return "mainline", str(metadata.get("origin") or "issue_factory"), ticket.key
```

Then group children under root. Keep `tickets` backward-compatible in WorkbenchDTO.

- [ ] **Step 3: Add creation metadata**

In `ariadne_ltb/application/issue_factory.py`, when creating `BacklogOperation.metadata`, add:

```python
"issue_class": "mainline",
"origin": "issue_factory",
"root_ticket_key": ticket_key,
"target_version_label": str(context.manifest.metadata.get("target_version_label", "v0.1")) if hasattr(context.manifest, "metadata") else "v0.1",
```

In `ariadne_ltb/application/inbox_actions.py`, when repair ticket is created, save metadata on that repair ticket:

```python
repair_ticket.metadata.setdefault("issue_class", "repair")
repair_ticket.metadata.setdefault("origin", "inbox_recovery")
repair_ticket.metadata.setdefault("parent_ticket_key", item.ticket_key)
repair_ticket.metadata.setdefault("root_ticket_key", item.ticket_key)
```

Save the ticket after mutation.

- [ ] **Step 4: Frontend default issue list uses mainline**

Add types:

```ts
export type IssueProjection = {
  summary: Record<string, number>;
  mainlineTickets: IssueFamily[];
  repairItems: IssueChild[];
  historyItems: IssueChild[];
};
```

In `IssuesPage`, replace empty-search list source:

```ts
const families = data.issueProjection?.mainlineTickets ?? data.tickets.map(ticketToFamily);
```

Add segmented controls: `主线`, `修复`, `历史`, `全部`. Default to `主线`.

- [ ] **Step 5: Verify**

Run:

```bash
python3.11 -m pytest tests/test_issue_projection.py tests/test_frontend_api_contract_static.py -q
cd frontend/ariadne-workbench && npm run build
```

Expected: default `#issues` does not render 200 historical tickets as the main product surface.

---

## Task 3: Add Current Evidence Lineage and Archive Superseded Inbox Noise

**Files:**
- Create: `ariadne_ltb/application/ticket_current_state.py`
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/mappers.py`
- Modify: `ariadne_ltb/inbox.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Modify: `ariadne_ltb/daemon.py`
- Create: `tests/test_ticket_current_state.py`
- Modify: `tests/test_inbox.py`

- [ ] **Step 1: Add additive lineage fields**

In `ExecutionResult`, add optional fields:

```python
assignment_id: str | None = None
run_id: str | None = None
attempt: int = 1
supersedes_execution_ids: list[str] = Field(default_factory=list)
closure_kind: str | None = None
```

In `InboxItem`, add:

```python
active: bool = True
archive_reason: str | None = None
superseded_by_ref: str | None = None
current_state: str | None = None
```

Use defaults so old JSON still loads.

- [ ] **Step 2: Implement current state**

Create `ariadne_ltb/application/ticket_current_state.py`:

```python
def build_ticket_current_state(store: AriadneStore, ticket: BuildTicket) -> TicketCurrentStateDTO:
    current_execution = _current_execution(store, ticket)
    current_review = _current_review(store, ticket)
    historical_blockers = _historical_blockers(store, ticket, current_execution)
    active_blockers = _active_blockers(store, ticket, current_execution)
    if _is_success(ticket, current_execution, current_review):
        state = "current_success"
    elif active_blockers:
        state = "current_blocked"
    else:
        state = "needs_attention"
    return TicketCurrentStateDTO(...)
```

Add `TicketCurrentStateDTO` and fields on `TicketEvidenceBundleDTO`:

```python
current_state: str | None = None
current_assignment_id: str | None = None
current_run_id: str | None = None
current_execution_result_id: str | None = None
current_review_report_id: str | None = None
historical_blocker_count: int = 0
active_blocker_count: int = 0
superseded_inbox_item_ids: list[str] = Field(default_factory=list)
```

- [ ] **Step 3: Use current state in inbox refresh**

In `ariadne_ltb/inbox.py`, before materializing active failures, compute state per ticket. If a blocker occurred before or is superseded by a newer current success:

```python
store.update_inbox_item_status(
    item.id,
    InboxStatus.RESOLVED,
    f"superseded by {state.current_execution_result_id}",
)
```

Do not delete the item. Active inbox should only show blockers newer than current success or blockers for tickets without current success.

- [ ] **Step 4: Link execution result to assignment/run**

In `ariadne_ltb/orchestrator.py`, after backend execution result is produced and before save, set:

```python
execution_result.assignment_id = self.assignment_id
execution_result.run_id = execution_run.id if execution_run else None
```

In `ariadne_ltb/daemon.py`, keep assignment metadata in sync with the execution result id.

- [ ] **Step 5: Frontend evidence panel**

In `TicketInspector`, render current evidence first:

```tsx
<section className="evidence-current">
  <h3>当前版本证据</h3>
  <StatusPill label={ticket.evidence?.currentState ?? "missing"} />
  ...
</section>
```

Move artifact local paths into a collapsible "工程细节". Render historical blockers in a separate collapsed section.

- [ ] **Step 6: Verify**

Run:

```bash
python3.11 -m pytest tests/test_ticket_current_state.py tests/test_inbox.py -q
cd frontend/ariadne-workbench && npm run build
```

Expected: `MCA-001` can show current success while old blocker records remain archived/history.

---

## Task 4: Add Workbench Environment Projection

**Files:**
- Create: `ariadne_ltb/application/workbench_environment.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/mappers.py`
- Modify: `ariadne_ltb/application/workbench_projection.py`
- Modify: `ariadne_ltb/interfaces/http/routes.py`
- Create: `tests/test_workbench_environment.py`
- Modify: `tests/test_control_plane_http.py`
- Modify: `frontend/ariadne-workbench/src/shared/api/types.ts`
- Modify: `frontend/ariadne-workbench/src/types.ts`
- Modify: `frontend/ariadne-workbench/src/data.ts`
- Modify: `frontend/ariadne-workbench/src/App.tsx`

- [ ] **Step 1: Add environment DTO**

Add:

```python
class EnvironmentBlockerDTO(AriadneDTO):
    code: str
    message: str
    severity: str = "warning"


class WorkbenchEnvironmentDTO(AriadneDTO):
    connection_mode: str = "api"
    execution_mode: str
    read_only: bool = False
    ariadne_root: str
    ariadne_store_path: str
    active_target_project_id: str | None = None
    active_target_project: TargetProjectDTO | None = None
    production_backends_available: list[str] = Field(default_factory=list)
    selected_backend_recommendation: str | None = None
    blockers: list[EnvironmentBlockerDTO] = Field(default_factory=list)
```

Extend `TargetProjectDTO`:

```python
local_path: str | None = None
path_exists: bool = False
is_git_repo: bool = False
git_branch: str | None = None
git_dirty: bool | None = None
test_command: str | None = None
issue_prefix: str | None = None
boundary_role: str = "target_repo"
```

- [ ] **Step 2: Implement environment projection**

Create `workbench_environment.py` that reads:

```python
os.environ.get("ARIADNE_ENABLE_EXTERNAL_EXECUTION")
store.load_project_resources()
runtime capability snapshots
shutil.which("codex")
shutil.which("claude")
```

Set execution mode:

- `real_api_ready`: target exists, Codex/Claude available, external execution enabled.
- `api_gate_closed`: target exists, backend available, env gate not enabled.
- `api_runtime_unavailable`: no production backend available.
- `api_target_missing`: no target or target path missing.

- [ ] **Step 3: Upgrade `/health` minimally**

In `routes.py`, return:

```python
{"status": "ok", "mode": "api", "schema_version": "ariadne.health.v1"}
```

Do not put paths or secrets in `/health`.

- [ ] **Step 4: Frontend environment banner**

Render a non-collapsible banner near the top of `#delivery` and `#project`:

```text
真实 API · 外部执行门禁关闭
目标 repo: /Users/.../mini-code-agent
Ariadne 控制面: /Users/.../Ariadne
```

Disable mutation controls when `readOnly` or `executionMode` blocks the specific action. Allow source analysis and issue generation when gate is closed; disable real run.

- [ ] **Step 5: Verify**

Run:

```bash
python3.11 -m pytest tests/test_workbench_environment.py tests/test_control_plane_http.py -q
cd frontend/ariadne-workbench && npm run build
```

Expected: UI makes API/offline/target/execution boundary obvious.

---

## Task 5: Make Project Inputs a First-Class Lifecycle

**Files:**
- Create: `ariadne_ltb/application/project_inputs.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/source_analysis.py`
- Modify: `ariadne_ltb/application/source_understanding.py`
- Modify: `ariadne_ltb/application/workbench_projection.py`
- Modify: `ariadne_ltb/interfaces/http/routes.py`
- Create: `tests/test_project_inputs_projection.py`
- Modify: `frontend/ariadne-workbench/src/shared/api/types.ts`
- Modify: `frontend/ariadne-workbench/src/types.ts`
- Modify: `frontend/ariadne-workbench/src/data.ts`
- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Create: `frontend/ariadne-workbench/src/features/project-inputs/ui.tsx`

- [ ] **Step 1: Add project input DTOs**

Add:

```python
class SourceNextActionDTO(AriadneDTO):
    id: str
    label: str
    enabled: bool = True
    reason: str = ""
    target_route: str | None = None
    api_action: str | None = None


class SourceLifecycleDTO(AriadneDTO):
    source_id: str
    status: str
    label: str
    detail: str
    terminal: bool
    ready_for_issue_factory: bool
    blocker: str | None = None
    updated_at: str
    next_actions: list[SourceNextActionDTO] = Field(default_factory=list)


class SourceTypedArtifactDTO(AriadneDTO):
    id: str
    kind: str
    label: str
    summary: str
    payload_path: str | None = None
    payload_hash: str | None = None
    evidence_count: int = 0
    key_fields: dict[str, Any] = Field(default_factory=dict)


class ProjectInputDetailDTO(AriadneDTO):
    source: SourceDocumentDTO
    lifecycle: SourceLifecycleDTO
    understanding: SourceUnderstandingDTO | None = None
    artifacts: list[SourceTypedArtifactDTO] = Field(default_factory=list)
    evidence: list[SourceEvidenceItemDTO] = Field(default_factory=list)
    impacted_ticket_keys: list[str] = Field(default_factory=list)
```

Add `project_inputs: list[ProjectInputDetailDTO] = Field(default_factory=list)` to `WorkbenchDTO`.

- [ ] **Step 2: Implement source-centric projection**

Create `project_inputs.py`. Rules:

- `ready_for_issue_factory` is true for `analysis_status in {"analyzed", "partial"}` and at least one artifact.
- For GitHub repo artifacts, include key fields: commit, manifests, tests, entrypoints, avoid notes count.
- Next action is typed, not a free string:
  - pending/failed/blocked -> analyze/retry.
  - analyzed without preview -> generate issue suggestions.
  - previewed -> review/apply issue delta.
  - applied -> open impacted ticket.

- [ ] **Step 3: Fix source add/analyze return**

In `/api/sources` and `/api/sources/{id}/analyze`, return lifecycle/detail artifacts with the source output. If analysis blocks, return blocked lifecycle and do not let frontend display "分析完成".

- [ ] **Step 4: Frontend Project Inputs UI**

Use `data.projectInputs` instead of joining `sources`, `sourceEvents`, `sourceArtifacts`, and `sourceUnderstandings` in the component.

Remove disabled fake buttons `标记重要` and `忽略` until real backend actions exist.

When user adds a URL, auto-infer type/title but keep fields editable. After save, show:

```text
已抓取 / 已分析 / 可生成任务建议
```

and a concrete next action button.

- [ ] **Step 5: Verify**

Run:

```bash
python3.11 -m pytest tests/test_project_inputs_projection.py tests/test_control_plane_http.py -q
cd frontend/ariadne-workbench && npm run build
```

Browser check:

1. Add a GitHub repo URL.
2. See lifecycle states, commit/artifact/evidence.
3. Click "查看任务建议".
4. Impacted tickets deep-link to concrete issues.

---

## Task 6: Turn Issue Factory Into Explicit Issue Delta Confirmation

**Files:**
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/issue_factory.py`
- Modify: `ariadne_ltb/application/issue_compiler.py`
- Modify: `ariadne_ltb/backlog.py`
- Modify: `ariadne_ltb/interfaces/http/routes.py`
- Modify: `tests/test_issue_factory_http_errors.py`
- Create: `tests/test_issue_factory_delta_confirmation.py`
- Modify: `frontend/ariadne-workbench/src/shared/api/types.ts`
- Modify: `frontend/ariadne-workbench/src/types.ts`
- Modify: `frontend/ariadne-workbench/src/data.ts`
- Modify: `frontend/ariadne-workbench/src/App.tsx`

- [ ] **Step 1: Add delta metadata**

Extend `BacklogOperationDTO` with:

```python
change_intent: str = "add"
target_version_label: str | None = None
existing_ticket_key: str | None = None
before_snapshot: dict[str, Any] = Field(default_factory=dict)
after_summary: str = ""
confidence: float = 0.75
decision_reason: str = ""
included: bool = True
```

Expose these from `operation.metadata`.

- [ ] **Step 2: Generate more than add/update**

In `IssueFactoryService._operations()`, build a coverage matrix:

- compiled task matches existing ticket by title/modules/evidence -> `update`.
- compiled task is new -> `add`.
- existing open target ticket not covered -> `defer`.
- existing low-value generated follow-up -> `discard`.
- existing done ticket -> `keep`.

Store the change intent in operation metadata even if the underlying MVP operation type still maps to add/update/supersede.

- [ ] **Step 3: Make stale preview safe**

Remove frontend auto-apply-after-stale behavior. Add route:

```python
POST /api/issue-factory/{preview_id}/refresh
```

It generates a fresh preview and returns it. It does not apply.

Apply route accepts:

```json
{
  "decisions": [
    {"operation_id": "...", "action": "apply|skip|defer|discard", "note": ""}
  ]
}
```

No body remains backward-compatible.

- [ ] **Step 4: Frontend confirmation UI**

Rename button:

```text
应用已确认的任务变更
```

Group changes as:

- 建议新增
- 建议更新
- 建议降级
- 建议延后
- 建议废弃
- 保持不变

Each change shows evidence refs, acceptance criteria, affected modules, target version, and include/skip decision.

If apply returns stale 409, show:

```text
任务列表已变化，需要重新生成预览。
```

Only button: `重新生成预览`.

- [ ] **Step 5: Verify**

Run:

```bash
python3.11 -m pytest tests/test_issue_factory_delta_confirmation.py tests/test_issue_factory_http_errors.py -q
cd frontend/ariadne-workbench && npm run build
```

Expected: stale preview never auto-applies.

---

## Task 7: Add Agent Team Workflow Projection

**Files:**
- Create: `ariadne_ltb/application/agent_workflow_projection.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/workbench_projection.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Create: `tests/test_agent_workflow_projection.py`
- Modify: `frontend/ariadne-workbench/src/shared/api/types.ts`
- Modify: `frontend/ariadne-workbench/src/types.ts`
- Modify: `frontend/ariadne-workbench/src/data.ts`
- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Create: `frontend/ariadne-workbench/src/features/agent-workflow/ui.tsx`

- [ ] **Step 1: Add workflow DTOs**

Add:

```python
class ArtifactRefDTO(AriadneDTO):
    id: str
    artifact_type: str
    path: str | None = None
    summary: str = ""
    created_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentActivityDTO(AriadneDTO):
    id: str
    ticket_id: str | None = None
    ticket_key: str | None = None
    assignment_id: str | None = None
    run_id: str | None = None
    agent_name: str
    stage: str
    event_type: str
    summary: str
    timestamp: str
    ref_id: str | None = None


class AgentWorkflowStepDTO(AriadneDTO):
    id: str
    ticket_id: str
    ticket_key: str
    sequence: int
    agent_name: str
    agent_role: str
    step_kind: str
    status: str
    input_refs: list[ArtifactRefDTO] = Field(default_factory=list)
    output_refs: list[ArtifactRefDTO] = Field(default_factory=list)
    assignment_id: str | None = None
    run_id: str | None = None
    handoff_id: str | None = None
    next_agent: str | None = None
    next_action: str = ""
    latest_activity: AgentActivityDTO | None = None
    blocked_reason: str | None = None
```

Add `agent_workflows: list[AgentWorkflowStepDTO]` and `agent_activities: list[AgentActivityDTO]` to `WorkbenchDTO`.

- [ ] **Step 2: Build workflow from real evidence**

Projection must emit these steps only from real refs:

1. Knowledge Agent
2. Repo Understanding Agent
3. Issue Factory
4. Build Lead
5. Handoff
6. Runtime / Daemon
7. Implementer
8. Reviewer
9. Memory Agent

If a ref is missing, status is `not_started` or `waiting_for_evidence`, never `done`.

- [ ] **Step 3: Preserve agent roles in progress events**

In `orchestrator._progress()`, add optional `actor`, `agent_role`, and `metadata`. Use:

- `Build Lead` for route/build packet.
- `Handoff Agent` for handoff packet.
- `Runtime Agent` for daemon/claim.
- `Implementer` for Codex/Claude execution.
- `Reviewer` for review.
- `Memory Agent` for memory/Feishu/next tickets.

- [ ] **Step 4: Frontend Agent Team Run**

Replace static-ish AgentDock chat with a `TeamActivityDock` that shows real activity.

In `TicketInspector`, add:

```tsx
<AgentWorkflowPanel
  ticketKey={ticket.key}
  steps={data.agentWorkflows.filter(step => step.ticketKey === ticket.key)}
/>
```

In `AgentsPage`, show active work per agent from workflow projection, with artifacts and blockers.

- [ ] **Step 5: Verify**

Run:

```bash
python3.11 -m pytest tests/test_agent_workflow_projection.py -q
cd frontend/ariadne-workbench && npm run build
```

Expected: agent team UI has no fake chat-only state; every completed step has a real artifact/event ref.

---

## Task 8: Scope Runtime and Add Recovery Actions

**Files:**
- Create: `ariadne_ltb/application/inbox_recovery.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/daemon.py`
- Modify: `ariadne_ltb/application/daemon_control.py`
- Modify: `ariadne_ltb/application/inbox_actions.py`
- Modify: `ariadne_ltb/retry.py`
- Modify: `ariadne_ltb/interfaces/http/routes.py`
- Modify: `frontend/ariadne-workbench/src/features/agent-control/model.ts`
- Create: `frontend/ariadne-workbench/src/features/runtime-scope/ui.tsx`
- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Modify: `tests/test_assignment_claim_state_machine.py`
- Modify: `tests/test_workbench_daemon_feedback.py`
- Modify: `tests/test_inbox.py`

- [ ] **Step 1: Add runtime scope DTOs**

Add:

```python
class RuntimeScopeDTO(AriadneDTO):
    mode: str = "paused"
    target_project_id: str | None = None
    ticket_id: str | None = None
    assignment_id: str | None = None
    allowed_backends: list[str] = Field(default_factory=list)


class QueuePreviewDTO(AriadneDTO):
    current: AssignmentDTO | None = None
    same_ticket_ready: list[AssignmentDTO] = Field(default_factory=list)
    same_project_ready: list[AssignmentDTO] = Field(default_factory=list)
    out_of_scope_ready_count: int = 0
```

Extend `DaemonStartInput` and `DaemonStatusDTO` with scope fields.

- [ ] **Step 2: Make daemon claim scoped**

In `LocalDaemonWorker.run_once()`, pass `target_project_id` and `allowed_backends` to `store.claim_next_assignment()` when `assignment_id` is absent.

In `DaemonControlService.start()`, if existing loop is alive but scope changed, stop old loop and start a new one scoped to the requested assignment/project.

- [ ] **Step 3: Add inbox recovery classifier**

Create `inbox_recovery.py`:

```python
def classify_inbox_item(item: InboxItem) -> InboxRecoveryDTO:
    if item.failure_reason in {FailureReason.TIMEOUT, FailureReason.RUNTIME_UNAVAILABLE, FailureReason.COMMAND_UNAVAILABLE}:
        return InboxRecoveryDTO(recovery_class="auto_rerunnable", primary_action="rerun")
    if item.failure_reason in {FailureReason.REVIEW_FAILED, FailureReason.TEST_FAILED, FailureReason.AGENT_ERROR}:
        return InboxRecoveryDTO(recovery_class="repair_ticket_required", primary_action="create_repair_ticket")
    if item.failure_reason is FailureReason.EXTERNAL_EXECUTION_DISABLED:
        return InboxRecoveryDTO(recovery_class="confirmation_required", primary_action="authorize_and_rerun")
    return InboxRecoveryDTO(recovery_class="human_required", primary_action="manual_review")
```

Use exact enum names available in `FailureReason`; if names differ, map to existing values.

- [ ] **Step 4: Add recover endpoint**

In `routes.py`:

```python
POST /api/inbox/{item_id}/recover
```

Return next assignment/repair ticket/daemon scope hint. Existing repair/rerun endpoints can remain.

- [ ] **Step 5: Frontend run current assignment**

In `frontend/ariadne-workbench/src/features/agent-control/model.ts`, ensure `runSelectedAssignment()` always:

1. dispatches or marks assignment ready,
2. starts/updates daemon with `allowed_assignment_id`,
3. watches assignment events.

Even if daemon is already running, scope must change to the selected assignment.

- [ ] **Step 6: Verify**

Run:

```bash
python3.11 -m pytest tests/test_assignment_claim_state_machine.py tests/test_workbench_daemon_feedback.py tests/test_inbox.py -q
cd frontend/ariadne-workbench && npm run build
```

Browser check: create two ready assignments, run the second, confirm daemon claims only the second.

---

## Task 9: Add Delivery-First Workbench UI

**Files:**
- Create: `frontend/ariadne-workbench/src/features/project-version-delivery/model.ts`
- Create: `frontend/ariadne-workbench/src/features/project-version-delivery/ui.tsx`
- Create: `frontend/ariadne-workbench/src/features/project-inputs/ui.tsx`
- Create: `frontend/ariadne-workbench/src/features/agent-workflow/ui.tsx`
- Create: `frontend/ariadne-workbench/src/features/runtime-scope/ui.tsx`
- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Modify: `frontend/ariadne-workbench/src/styles.css`
- Modify: `tests/test_frontend_api_contract_static.py`
- Modify: `tests/test_workbench_data_sync.py`

- [ ] **Step 1: Make `#delivery` default**

In route parsing, add:

```ts
type PageKey = "delivery" | ...
```

Default to `delivery`.

Sidebar first item:

```text
当前版本
```

- [ ] **Step 2: Build DeliveryPage**

`DeliveryPage` shows:

- environment banner
- version header
- gate strip
- mainline delivery items
- latest real run proof
- next actions
- blockers

It must answer:

```text
这个项目版本现在交付到哪了？
```

- [ ] **Step 3: Rework Sources/Tasks/Issues/Agents/Runtime/Inbox as drill-down**

Keep existing pages but change the user mental model:

- Sources: project inputs lifecycle.
- Tasks: issue delta confirmation.
- Issues: mainline issue family by default.
- Agents: current team workflow, not static profile list.
- Runtime: scoped queue and daemon control.
- Inbox: recovery queue, not a raw historical failure list.

- [ ] **Step 4: Add `data-testid` attributes for dogfood**

Add stable ids:

```tsx
data-testid="delivery-status"
data-testid="environment-mode"
data-testid="target-project-path"
data-testid="source-lifecycle-card"
data-testid="issue-delta-preview"
data-testid="agent-workflow-step"
data-testid="daemon-scope"
data-testid="execution-proof"
data-testid="target-repo-evidence"
```

These make Playwright assertions structural instead of text-regex based.

- [ ] **Step 5: Verify**

Run:

```bash
cd frontend/ariadne-workbench && npm run build
python3.11 -m pytest tests/test_frontend_api_contract_static.py tests/test_workbench_data_sync.py -q
```

Expected: UI compiles and static contract tests lock delivery-first defaults.

---

## Task 10: Harden Real Browser Dogfood Closure

**Files:**
- Modify: `scripts/verify_dogfood_browser.sh`
- Modify: `frontend/ariadne-workbench/e2e/mini-code-agent-dogfood.spec.ts`
- Create: `scripts/verify_dogfood_result_packet.py`
- Create: `docs/dogfood/templates/REAL_BROWSER_DOGFOOD_RESULT.md`
- Modify: `docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md`
- Modify: `README.md`
- Modify: `docs/ops/V1_RELEASE_CHECKLIST.md`
- Modify: `docs/ops/HUMAN_DEMO_SCRIPT.md`

- [ ] **Step 1: Change script exit semantics**

In `scripts/verify_dogfood_browser.sh`:

- Default mode becomes `real`.
- `--blocked-ok` is replaced or aliased to `--record-blocker`.
- `REAL_CLOSED` exits 0.
- `BLOCKED_NOT_CLOSED` exits 10.
- Product/harness failure exits 1.
- Misuse exits 2.

Add final verifier call:

```bash
python3.11 "$ROOT/scripts/verify_dogfood_result_packet.py" "$RESULT_DIR/real-browser-dogfood-result.json"
```

- [ ] **Step 2: Record successful UI evidence**

In Playwright spec, add:

```ts
async function recordStepEvidence(page, resultDir, stepName) {
  await page.screenshot({ path: `${resultDir}/ui/${stepName}.png`, fullPage: true });
  await fs.promises.appendFile(
    `${resultDir}/browser_steps.jsonl`,
    JSON.stringify({ step: stepName, url: page.url(), at: new Date().toISOString() }) + "\n",
  );
}
```

Call it for project, sources, issue preview, apply, MCA-001, assignment, runtime, execution evidence, version progress.

- [ ] **Step 3: Verify target repo evidence**

At final Playwright step, run read-only target checks:

```ts
git status --short
git diff --stat -- . ':!__pycache__'
python3.11 -m mini_code_agent --help
python3.11 -m mini_code_agent run "inspect this project and summarize next steps"
```

Capture stdout/stderr/exit code into the result packet.

- [ ] **Step 4: Write result packet**

`real-browser-dogfood-result.json` must include:

```json
{
  "status": "REAL_CLOSED",
  "ui_evidence": [],
  "target_repo_evidence": {},
  "runtime_execution_proof": {},
  "version_progress": {},
  "non_success_audit": []
}
```

`BLOCKED_NOT_CLOSED` is allowed only for external blockers like missing CLI, login, quota, OS permission, disabled execution gate, or target repo locked.

- [ ] **Step 5: Docs cleanup**

README and ops docs must say:

```text
Release readiness and browser dogfood closure are different.
Only the real browser dogfood result packet can close the dogfood.
```

Remove language that implies `doctor`, `evidence packet`, `demo full`, `fake-codex`, or `blocked-ok` prove closure.

- [ ] **Step 6: Verify**

Run:

```bash
python3.11 -m pytest tests/test_frontend_api_contract_static.py -q
cd frontend/ariadne-workbench && npm run build
bash scripts/verify_dogfood_browser.sh --record-blocker || test "$?" = "10"
```

Then, when Codex/Claude credentials and execution gate are available:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
```

Expected: no `REAL_CLOSED` without complete result packet.

---

## Task 11: End-to-End Integration Pass

**Files:**
- All files touched above.
- Modify: `docs/development_report.md`

- [ ] **Step 1: Run focused backend tests**

```bash
python3.11 -m pytest \
  tests/test_project_version_delivery_projection.py \
  tests/test_issue_projection.py \
  tests/test_ticket_current_state.py \
  tests/test_project_inputs_projection.py \
  tests/test_workbench_environment.py \
  tests/test_agent_workflow_projection.py \
  tests/test_assignment_claim_state_machine.py \
  tests/test_workbench_daemon_feedback.py \
  tests/test_inbox.py \
  tests/test_control_plane_http.py -q
```

- [ ] **Step 2: Run full backend tests**

```bash
python3.11 -m pytest
```

- [ ] **Step 3: Run lint**

```bash
ruff check .
```

- [ ] **Step 4: Build frontend**

```bash
cd frontend/ariadne-workbench && npm run build
```

- [ ] **Step 5: Run browser blocker rehearsal**

```bash
bash scripts/verify_dogfood_browser.sh --record-blocker
```

Expected: either exits 10 with `BLOCKED_NOT_CLOSED`, or exits 1 for real product/harness failure that must be fixed. It must not exit 0 unless `--real` closes.

- [ ] **Step 6: Run real browser dogfood when available**

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
```

Allowed outcomes:

- `REAL_CLOSED` with full result packet: the plan succeeded.
- `BLOCKED_NOT_CLOSED` with exact external blocker: acceptable but not closure.
- Any harness/product failure: fix before stopping.

- [ ] **Step 7: Update development report**

In `docs/development_report.md`, add:

```markdown
## Project Version Delivery Closure Fix

- Product loop status:
- Real browser dogfood status:
- Files changed:
- Commands run:
- Result packet:
- Remaining blockers:
- Why fake/demo/offline paths did not count as closure:
```

- [ ] **Step 8: Commit**

```bash
git status --short
git add \
  ariadne_ltb \
  frontend/ariadne-workbench \
  scripts \
  tests \
  docs \
  README.md
git commit -m "feat: close project version delivery workbench loop"
git push origin HEAD
```

Do not merge to main inside this plan unless the user explicitly asks after review.

---

## Acceptance Criteria

The implementation is acceptable only if all are true:

1. Workbench opens on `#delivery`, not a component inventory page.
2. User can see the active project/version, target repo, real API/offline mode, and execution gate.
3. Source input cards answer: where it went, what Ariadne understood, which artifacts/evidence were produced, and the next action.
4. Issue Factory shows an explainable issue delta and never auto-applies stale previews.
5. Issues default to mainline project/version work, with repair/history isolated.
6. Ticket evidence shows current success/blocker first and historical blockers separately.
7. Agent Team view shows real artifact handoffs, not static profiles or fake chat.
8. Runtime is scoped to the selected assignment/current delivery, so daemon does not claim old work unexpectedly.
9. Inbox actions are classified and recoverable; superseded historical failures do not look current.
10. `scripts/verify_dogfood_browser.sh --real` is the only closure path.
11. `--record-blocker` or missing external capability cannot be mistaken for success.
12. No tests require external Codex/Claude/DeepSeek/Feishu/GitHub credentials.
13. Real closure is not claimed unless evidence packet includes UI evidence and target repo evidence.

## Known Risks

- This plan intentionally adds several read-model projections. Keep them additive and derived from existing store data to avoid schema migration churn.
- Avoid introducing a persistent `ProjectVersion` model in this pass. Version delivery is a projection until browser closure is stable.
- Do not hide historical evidence. Archive/supersede it so users can inspect it without confusing it with current state.
- Do not silently fall back to `fake-codex` in product mode.
- Do not let Playwright mutate state via direct API calls for dogfood closure; it must drive the browser UI.

## Execution Strategy

Recommended execution is subagent-driven in dependency order:

1. Backend projections: Tasks 1-5.
2. Delta/runtime/recovery mechanics: Tasks 6 and 8.
3. Agent workflow and frontend UI: Tasks 7 and 9.
4. Dogfood closure harness: Task 10.
5. Integration and evidence: Task 11.

Commit after each task or tightly coupled pair. If a task exposes a product blocker, fix the blocker instead of downgrading acceptance.
