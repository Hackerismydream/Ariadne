# Ariadne v1.0 Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Ariadne v1.0 as a local-first, ticket-driven Agent teammate workbench covering ARI-007 through ARI-014.

**Architecture:** Keep the current JSON/JSONL local kernel and extend it with observable daemon heartbeat, retry queue, agent handoffs, planner quality, workbench board, and release doctors. Do not replace the existing `TicketRunOrchestrator`; make assignment/daemon mode and direct `ticket run` share the same full loop.

**Tech Stack:** Python 3.11+, Pydantic v2, Typer, Pytest, Ruff, JSON/JSONL persistence, Python standard library `http.server`.

---

## Design Position

Build this as one v1.0 sprint branch from `main`, but implement it as eight vertical ARI slices. The branch should be merged directly into `main` after `pytest`, `ruff check .`, `scripts/verify_v1.sh`, and the required CLI smoke commands pass. Do not stack this sprint on another feature branch.

This plan assumes current `main` already contains ARI-006 Agent Teammate Mode. If that stops being true, the first execution step is to update `main` and re-run the existing `pytest` suite before creating the sprint branch.

## Not Building

- No production daemon service manager.
- No Postgres, SQLite migration, WebSocket, auth, or multi-workspace server.
- No real Feishu writes by default.
- No network-dependent tests.
- No automatic commit, push, merge, or PR creation inside Ariadne runtime.
- No fallback from real Codex/Claude to `fake-codex`.

## Component Flow

```text
Source Markdown
  -> SourceDocument
  -> BuildTicket
  -> TicketAssignment
  -> LocalDaemonWorker + WorkerHeartbeat
  -> AgentHandoff chain
  -> TicketRunOrchestrator
  -> Planner + BuildPacketQualityReport
  -> ExecutionBackend
  -> ReviewReport
  -> MemoryRecord + Feishu dry-run
  -> Next Tickets
  -> Board + Journal + Comments
```

## File Structure

- Modify `ariadne_ltb/models.py`: add daemon heartbeat models, handoff models, packet quality report, retry fields on `TicketAssignment`, and optional execution context IDs.
- Modify `ariadne_ltb/storage.py`: persist heartbeats, daemon state, handoffs, retry assignment chains, and quality artifacts.
- Modify `ariadne_ltb/daemon.py`: write heartbeat and stage events around assignment claiming and orchestrator execution.
- Modify `ariadne_ltb/journal.py`: add retry-aware resume plans and event helpers.
- Create `ariadne_ltb/retry.py`: safe retry policy and retry assignment creation.
- Create `ariadne_ltb/handoffs.py`: handoff creation helpers used by orchestrator and daemon.
- Create `ariadne_ltb/planner_quality.py`: deterministic Build Packet quality scoring.
- Modify `ariadne_ltb/ingest.py`: strengthen arbitrary markdown parsing.
- Modify `ariadne_ltb/planner.py`: attach planner mode, blocked artifacts, quality summary, and richer handoff.
- Modify `ariadne_ltb/execution.py`: pass `assignment_id` and `run_id` into Codex/Claude templates and tighten blocked paths.
- Modify `ariadne_ltb/orchestrator.py`: emit handoffs, heartbeat stages, retry hints, and quality metadata without duplicating the loop.
- Modify `ariadne_ltb/board.py`: convert board from artifact dump to v1.0 workbench sections.
- Create `ariadne_ltb/board_server.py`: stdlib static board server entrypoint.
- Create `ariadne_ltb/doctor.py`: secret-safe `doctor secrets` and `doctor v1` checks.
- Modify `ariadne_ltb/cli.py`: add `assignment`, `board`, and `doctor` Typer apps plus new commands.
- Create `examples/sources/ariadne_self_improvement_note.md`: non-fixture source for planner intelligence.
- Create `scripts/verify_v1.sh`: final acceptance script.
- Create docs: `docs/evaluation/v1_0_evaluation.md`, `docs/demo/ARIADNE_V1_DEMO_SCRIPT.md`, `docs/interview/PROJECT_NARRATIVE.md`, `docs/ops/HUMAN_DEMO_SCRIPT.md`, `docs/ops/V1_RELEASE_CHECKLIST.md`.
- Modify `README.md` and `docs/development_report.md`.
- Add tests: `tests/test_v1_daemon_supervision.py`, `tests/test_v1_retry_recovery.py`, `tests/test_v1_handoffs.py`, `tests/test_v1_codex_teammate.py`, `tests/test_v1_planner_quality.py`, `tests/test_v1_board_ux.py`, `tests/test_v1_doctor_release.py`.

---

### Task 0: Sprint Branch and Workpack Placement

**Files:**
- Create: `docs/codex_workpacks/ariadne_v1_0_sprint_plan_pack/*.md`
- Modify: none
- Test: shell verification only

- [ ] **Step 1: Create a clean sprint branch from main**

Run:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/ariadne-v1-0-sprint
```

Expected: branch `codex/ariadne-v1-0-sprint` exists and `git status --short --branch` shows a clean worktree.

- [ ] **Step 2: Place the sprint workpack under repo docs**

Run:

```bash
mkdir -p docs/codex_workpacks/ariadne_v1_0_sprint_plan_pack
unzip -o /Users/martinlos/Downloads/ariadne_v1_0_sprint_plan_pack.zip -d /tmp/ariadne_v1_plan_unpack
cp /tmp/ariadne_v1_plan_unpack/ariadne_v1_0_sprint_plan_pack/*.md docs/codex_workpacks/ariadne_v1_0_sprint_plan_pack/
```

Expected: `docs/codex_workpacks/ariadne_v1_0_sprint_plan_pack/ARI-000-v1-0-completion-contract.md` exists.

- [ ] **Step 3: Commit the workpack**

Run:

```bash
git add docs/codex_workpacks/ariadne_v1_0_sprint_plan_pack
git commit -m "docs: add Ariadne v1 sprint workpack"
```

Expected: commit succeeds.

---

### Task 1: ARI-007 Daemon Supervision and Heartbeat

**Files:**
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/daemon.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `ariadne_ltb/board.py`
- Test: `tests/test_v1_daemon_supervision.py`

- [ ] **Step 1: Write failing daemon heartbeat tests**

Create `tests/test_v1_daemon_supervision.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.daemon import is_stale_heartbeat
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import DaemonStatus, WorkerHeartbeat
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_run_once_writes_worker_heartbeat(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"],
    )
    assert assign.exit_code == 0, assign.output

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "daemon", "run-once", "--runtime-id", "test-worker"],
    )

    heartbeat = store.load_worker_heartbeat("test-worker")
    assert result.exit_code == 0, result.output
    assert heartbeat.runtime_id == "test-worker"
    assert heartbeat.status in {DaemonStatus.STOPPED, DaemonStatus.IDLE, DaemonStatus.RUNNING}
    assert heartbeat.current_assignment_id
    assert heartbeat.current_ticket_key == "ARI-003"
    assert heartbeat.current_stage in {"done", "board", "stopped"}


def test_daemon_status_shows_heartbeat_and_counts(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    heartbeat = WorkerHeartbeat.new(runtime_id="visible-worker", status=DaemonStatus.IDLE)
    store.save_worker_heartbeat(heartbeat)

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "daemon", "status"])

    assert result.exit_code == 0, result.output
    assert "runtime_id: visible-worker" in result.output
    assert "status: idle" in result.output
    assert "stale:" in result.output
    assert "open assignments:" in result.output


def test_stale_heartbeat_by_old_timestamp_and_dead_pid() -> None:
    heartbeat = WorkerHeartbeat(
        runtime_id="stale-worker",
        pid=999999,
        status=DaemonStatus.RUNNING,
        started_at="2000-01-01T00:00:00Z",
        heartbeat_at="2000-01-01T00:00:00Z",
    )

    assert is_stale_heartbeat(heartbeat, stale_after_seconds=1) is True


def test_daemon_start_max_iterations_does_not_block(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "daemon", "start", "--runtime-id", "loop-test", "--max-iterations", "1", "--interval", "0"],
    )

    assert result.exit_code == 0, result.output
    assert "daemon loop finished" in result.output
    data = json.loads((tmp_path / ".ariadne" / "daemon" / "heartbeats" / "loop-test.json").read_text())
    assert data["runtime_id"] == "loop-test"
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest tests/test_v1_daemon_supervision.py -q
```

Expected: failures for missing `DaemonStatus`, `WorkerHeartbeat`, `is_stale_heartbeat`, `load_worker_heartbeat`, and `--runtime-id`.

- [ ] **Step 3: Add daemon heartbeat models**

Modify `ariadne_ltb/models.py` by adding:

```python
import os


class DaemonStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    STOPPED = "stopped"


class WorkerHeartbeat(AriadneModel):
    runtime_id: str
    pid: int
    status: DaemonStatus
    current_assignment_id: str | None = None
    current_ticket_id: str | None = None
    current_ticket_key: str | None = None
    current_stage: str | None = None
    started_at: str
    heartbeat_at: str
    last_event_id: str | None = None
    last_error: str | None = None

    @classmethod
    def new(
        cls,
        runtime_id: str,
        status: DaemonStatus,
        current_stage: str | None = None,
    ) -> WorkerHeartbeat:
        now = utc_now()
        return cls(
            runtime_id=runtime_id,
            pid=os.getpid(),
            status=status,
            current_stage=current_stage,
            started_at=now,
            heartbeat_at=now,
        )
```

- [ ] **Step 4: Add heartbeat persistence**

Modify `ariadne_ltb/storage.py`:

```python
from ariadne_ltb.models import WorkerHeartbeat


# in __init__
self.daemon_heartbeats_dir = self.daemon_dir / "heartbeats"
self.daemon_state_path = self.daemon_dir / "state.json"

# in _ensure_layout directory list
self.daemon_heartbeats_dir,


def save_worker_heartbeat(self, heartbeat: WorkerHeartbeat) -> Path:
    path = self.daemon_heartbeats_dir / f"{heartbeat.runtime_id}.json"
    self._write_model(path, heartbeat)
    self.daemon_state_path.write_text(
        heartbeat.model_dump_json(indent=2, exclude_none=False) + "\n",
        encoding="utf-8",
    )
    return path


def load_worker_heartbeat(self, runtime_id: str) -> WorkerHeartbeat:
    return self._read_model(
        self.daemon_heartbeats_dir / f"{runtime_id}.json",
        WorkerHeartbeat,
    )


def list_worker_heartbeats(self) -> list[WorkerHeartbeat]:
    return [
        self._read_model(path, WorkerHeartbeat)
        for path in sorted(self.daemon_heartbeats_dir.glob("*.json"))
    ]
```

- [ ] **Step 5: Add daemon heartbeat updates**

Modify `ariadne_ltb/daemon.py`:

```python
from datetime import UTC, datetime
import os

from ariadne_ltb.models import DaemonStatus, WorkerHeartbeat, utc_now


def is_stale_heartbeat(heartbeat: WorkerHeartbeat, stale_after_seconds: int = 120) -> bool:
    try:
        heartbeat_at = datetime.fromisoformat(heartbeat.heartbeat_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    age = (datetime.now(UTC) - heartbeat_at).total_seconds()
    if age > stale_after_seconds:
        return True
    try:
        os.kill(heartbeat.pid, 0)
    except OSError:
        return True
    return False
```

Add `LocalDaemonWorker._heartbeat(...)` and call it before/after stages:

```python
def _heartbeat(
    self,
    status: DaemonStatus,
    stage: str,
    assignment: TicketAssignment | None = None,
    ticket=None,
    last_event_id: str | None = None,
    last_error: str | None = None,
) -> WorkerHeartbeat:
    existing = None
    try:
        existing = self.store.load_worker_heartbeat(self.runtime_id)
    except FileNotFoundError:
        existing = None
    started_at = existing.started_at if existing else utc_now()
    heartbeat = WorkerHeartbeat(
        runtime_id=self.runtime_id,
        pid=os.getpid(),
        status=status,
        current_assignment_id=assignment.id if assignment else None,
        current_ticket_id=ticket.id if ticket else None,
        current_ticket_key=ticket.key if ticket else None,
        current_stage=stage,
        started_at=started_at,
        heartbeat_at=utc_now(),
        last_event_id=last_event_id,
        last_error=last_error,
    )
    self.store.save_worker_heartbeat(heartbeat)
    return heartbeat
```

Use stages `idle`, `claiming`, `planning`, `execution`, `review`, `memory`, `next_tickets`, `board`, `done`, `blocked`, `failed`, and `stopped`.

- [ ] **Step 6: Add runtime id CLI options and status output**

Modify `ariadne_ltb/cli.py`:

```python
@daemon_app.command("run-once")
def daemon_run_once(
    runtime_id: Annotated[str, typer.Option("--runtime-id")] = "local",
    confirm_execution: Annotated[bool, typer.Option("--confirm-execution")] = False,
) -> None:
    result = LocalDaemonWorker(AriadneStore(state.root), runtime_id=runtime_id).run_once(
        confirm_execution=confirm_execution,
    )
```

Modify `daemon_start` similarly with `--runtime-id`, and update `daemon_status` to iterate `store.list_worker_heartbeats()` and print:

```text
runtime_id: <id>
pid: <pid>
status: <status>
current ticket: <key>
current assignment: <id>
current stage: <stage>
heartbeat age seconds: <n>
stale: <true|false>
```

- [ ] **Step 7: Update board daemon section**

Modify `ariadne_ltb/board.py` so `Daemon / Worker` includes latest heartbeat fields for every heartbeat returned by `store.list_worker_heartbeats()`.

- [ ] **Step 8: Run daemon tests and commit**

Run:

```bash
pytest tests/test_v1_daemon_supervision.py -q
pytest tests/test_agent_teammate_mode.py -q
```

Expected: all selected tests pass.

Commit:

```bash
git add ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/daemon.py ariadne_ltb/cli.py ariadne_ltb/board.py tests/test_v1_daemon_supervision.py
git commit -m "feat: add daemon heartbeat supervision"
```

---

### Task 2: ARI-008 Retry Queue and Safe Recovery

**Files:**
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/journal.py`
- Create: `ariadne_ltb/retry.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `ariadne_ltb/board.py`
- Test: `tests/test_v1_retry_recovery.py`

- [ ] **Step 1: Write failing retry tests**

Create `tests/test_v1_retry_recovery.py`:

```python
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import AssignmentStatus, FailureReason
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_ticket_retry_creates_new_assignment_chain(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    first = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(first.mark_blocked("review failed", FailureReason.REVIEW_FAILED))

    result = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "ticket", "retry", ticket.key, "--reason", "fix after review"],
    )

    assignments = store.list_assignments_for_ticket(ticket.id)
    latest = store.find_latest_assignment_for_ticket(ticket.id)
    assert result.exit_code == 0, result.output
    assert len(assignments) == 2
    assert latest is not None
    assert latest.id != first.id
    assert latest.parent_assignment_id == first.id
    assert latest.attempt == 2
    assert latest.retry_reason == "fix after review"
    assert latest.status is AssignmentStatus.QUEUED


def test_unsafe_retry_requires_force(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    first = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(first.mark_blocked("scope violation", FailureReason.SCOPE_VIOLATION))

    blocked = CliRunner().invoke(app, ["--root", str(tmp_path), "ticket", "retry", ticket.key])
    forced = CliRunner().invoke(app, ["--root", str(tmp_path), "ticket", "retry", ticket.key, "--force"])

    assert blocked.exit_code == 2
    assert "unsafe" in blocked.output.lower()
    assert forced.exit_code == 0, forced.output
    assert store.find_latest_assignment_for_ticket(ticket.id).attempt == 2


def test_runtime_recover_recommends_retry_for_safe_blocker(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(assignment.mark_blocked("review failed", FailureReason.REVIEW_FAILED))

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "runtime", "recover"])

    assert result.exit_code == 0, result.output
    assert f"recommended: ari ticket retry {ticket.key}" in result.output


def test_board_shows_retry_chain(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    first = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    store.save_assignment(first.mark_blocked("review failed", FailureReason.REVIEW_FAILED))
    retry = CliRunner().invoke(app, ["--root", str(tmp_path), "ticket", "retry", ticket.key])
    board = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])

    assert retry.exit_code == 0, retry.output
    assert board.exit_code == 0, board.output
    text = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")
    assert "Assignment Retry Chain" in text
    assert first.id in text
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest tests/test_v1_retry_recovery.py -q
```

Expected: failures for missing retry fields, retry functions, and assignment CLI.

- [ ] **Step 3: Extend TicketAssignment**

Modify `ariadne_ltb/models.py`:

```python
class TicketAssignment(AriadneModel):
    ...
    parent_assignment_id: str | None = None
    attempt: int = 1
    retry_reason: str | None = None
    retry_policy: str | None = None
```

- [ ] **Step 4: Add storage helpers**

Modify `ariadne_ltb/storage.py`:

```python
def list_assignments_for_ticket(self, ticket_id: str) -> list[TicketAssignment]:
    return sorted(
        [assignment for assignment in self.list_assignments() if assignment.ticket_id == ticket_id],
        key=lambda assignment: (assignment.attempt, assignment.created_at),
    )
```

Update `find_latest_assignment_for_ticket` to use `list_assignments_for_ticket` and sort by `(attempt, created_at)`.

- [ ] **Step 5: Add retry policy module**

Create `ariadne_ltb/retry.py`:

```python
from __future__ import annotations

from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import (
    AssignmentStatus,
    CommentAuthorType,
    CommentKind,
    FailureReason,
    TicketAssignment,
    stable_id,
    utc_now,
)
from ariadne_ltb.storage import AriadneStore


SAFE_RETRY_REASONS = {
    FailureReason.RUNTIME_OFFLINE,
    FailureReason.TIMEOUT,
    FailureReason.COMMAND_UNAVAILABLE,
    FailureReason.REVIEW_FAILED,
}

UNSAFE_RETRY_REASONS = {
    FailureReason.SCOPE_VIOLATION,
    FailureReason.INVALID_RESOURCE,
    FailureReason.RESOURCE_LOCKED,
    FailureReason.UNKNOWN,
    FailureReason.EXTERNAL_EXECUTION_BLOCKED,
}


def is_safe_to_retry(assignment: TicketAssignment) -> bool:
    if assignment.status not in {AssignmentStatus.BLOCKED, AssignmentStatus.FAILED}:
        return False
    if assignment.failure_reason in SAFE_RETRY_REASONS:
        return True
    if assignment.failure_reason in UNSAFE_RETRY_REASONS:
        return False
    return False


def create_retry_assignment(
    store: AriadneStore,
    assignment: TicketAssignment,
    reason: str = "retry requested",
    force: bool = False,
) -> TicketAssignment:
    ticket = store.load_ticket(assignment.ticket_id)
    safe = is_safe_to_retry(assignment)
    if not safe and not force:
        store.append_runtime_event(
            runtime_event(
                ticket,
                assignment.claimed_by_runtime_id or "local",
                "retry",
                "retry_blocked",
                "Ariadne",
                assignment_id=assignment.id,
                failure_reason=assignment.failure_reason,
                metadata={"safe_to_retry": False, "reason": reason},
            )
        )
        raise ValueError(f"unsafe retry for {assignment.id}: {assignment.failure_reason}")
    retry = assignment.model_copy(
        deep=True,
        update={
            "id": stable_id("assignment", assignment.ticket_id, assignment.agent_id, "retry", assignment.attempt + 1, utc_now()),
            "status": AssignmentStatus.QUEUED,
            "parent_assignment_id": assignment.id,
            "attempt": assignment.attempt + 1,
            "retry_reason": reason,
            "retry_policy": "force" if force else "safe",
            "claimed_by_runtime_id": None,
            "claimed_at": None,
            "started_at": None,
            "ended_at": None,
            "failure_reason": None,
            "blocker": None,
        },
    )
    store.save_assignment(retry)
    store.add_comment(
        ticket,
        CommentAuthorType.SYSTEM,
        "Retry",
        CommentKind.RECOVERY,
        f"Retry created: {retry.id} from {assignment.id} attempt {retry.attempt}.",
        payload_ref=retry.id,
    )
    store.append_runtime_event(
        runtime_event(
            ticket,
            assignment.claimed_by_runtime_id or "local",
            "retry",
            "retry_created",
            "Ariadne",
            assignment_id=retry.id,
            payload_ref=retry.id,
            metadata={"parent_assignment_id": assignment.id, "force": force, "reason": reason},
        )
    )
    return retry
```

- [ ] **Step 6: Add assignment CLI**

Modify `ariadne_ltb/cli.py`:

```python
assignment_app = typer.Typer(help="Assignment queue commands.")
app.add_typer(assignment_app, name="assignment")
```

Add commands:

```python
@assignment_app.command("list")
def assignment_list() -> None:
    store = AriadneStore(state.root)
    for assignment in store.list_assignments():
        typer.echo(
            f"{assignment.id}\t{assignment.ticket_key}\t{assignment.agent_id}\t"
            f"{assignment.status.value}\tattempt={assignment.attempt}\tparent={assignment.parent_assignment_id or ''}"
        )


@assignment_app.command("show")
def assignment_show(assignment_id: str) -> None:
    assignment = AriadneStore(state.root).load_assignment(assignment_id)
    typer.echo(f"id: {assignment.id}")
    typer.echo(f"ticket: {assignment.ticket_key}")
    typer.echo(f"agent: {assignment.agent_id}")
    typer.echo(f"status: {assignment.status.value}")
    typer.echo(f"attempt: {assignment.attempt}")
    typer.echo(f"parent: {assignment.parent_assignment_id or ''}")
    typer.echo(f"failure reason: {assignment.failure_reason.value if assignment.failure_reason else ''}")
    typer.echo(f"blocker: {assignment.blocker or ''}")


@assignment_app.command("retry")
def assignment_retry(
    assignment_id: str,
    reason: Annotated[str, typer.Option("--reason")] = "retry requested",
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    store = AriadneStore(state.root)
    try:
        retry = create_retry_assignment(store, store.load_assignment(assignment_id), reason, force)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(2) from exc
    typer.echo(f"retry assignment: {retry.id}")
```

Add `ticket retry` resolving latest assignment and calling `create_retry_assignment`.

- [ ] **Step 7: Enhance runtime recovery**

Modify `ariadne_ltb/journal.py` so blocked/failed assignments with safe failure reasons recommend:

```text
ari ticket retry <ticket_key>
```

Completed assignments must return no recommended command and reason `already done, no resume needed`.

- [ ] **Step 8: Add retry chain to board**

Modify `ariadne_ltb/board.py` ticket section to render:

```markdown
### Assignment Retry Chain

| Assignment | Status | Attempt | Parent | Failure reason | Retry reason | Created | Ended |
|---|---|---:|---|---|---|---|---|
```

Rows come from `store.list_assignments_for_ticket(ticket.id)`.

- [ ] **Step 9: Run retry tests and commit**

Run:

```bash
pytest tests/test_v1_retry_recovery.py -q
pytest tests/test_agent_teammate_mode.py -q
```

Expected: pass.

Commit:

```bash
git add ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/journal.py ariadne_ltb/retry.py ariadne_ltb/cli.py ariadne_ltb/board.py tests/test_v1_retry_recovery.py
git commit -m "feat: add safe assignment retry queue"
```

---

### Task 3: ARI-009 Multi-Agent Handoff Loop

**Files:**
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Create: `ariadne_ltb/handoffs.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `ariadne_ltb/board.py`
- Test: `tests/test_v1_handoffs.py`

- [ ] **Step 1: Write failing handoff tests**

Create `tests/test_v1_handoffs.py`:

```python
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import HandoffStatus
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_ticket_run_generates_agent_handoff_chain(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)

    result = TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")
    handoffs = store.list_handoffs_for_ticket(result.ticket_id)

    assert [handoff.to_agent for handoff in handoffs] == [
        "Planner",
        "Execution",
        "Reviewer",
        "Memory",
        "Build Lead",
    ]
    assert all(handoff.status is HandoffStatus.COMPLETED for handoff in handoffs)


def test_ticket_handoffs_cli_and_comments(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "ticket", "handoffs", "ARI-003"])
    comments = store.list_comments(store.resolve_ticket("ARI-003").id)

    assert result.exit_code == 0, result.output
    assert "Build Lead -> Planner" in result.output
    assert "Execution -> Reviewer" in result.output
    assert any("-> Reviewer" in comment.body for comment in comments)


def test_board_shows_agent_handoffs(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")
    CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])

    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")
    assert "Agent Handoffs" in board
    assert "Reviewer -> Memory" in board
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest tests/test_v1_handoffs.py -q
```

Expected: missing `AgentHandoff`, handoff storage, and CLI.

- [ ] **Step 3: Add handoff models**

Modify `ariadne_ltb/models.py`:

```python
class HandoffStatus(str, Enum):
    CREATED = "created"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class AgentHandoff(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    from_agent: str
    to_agent: str
    from_assignment_id: str | None = None
    to_assignment_id: str | None = None
    reason: str
    payload_ref: str | None = None
    status: HandoffStatus = HandoffStatus.CREATED
    created_at: str = Field(default_factory=utc_now)
    completed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def mark_completed(self) -> AgentHandoff:
        return self.model_copy(update={"status": HandoffStatus.COMPLETED, "completed_at": utc_now()})
```

Add `HANDOFF = "handoff"` to `CommentKind`.

- [ ] **Step 4: Add storage**

Modify `ariadne_ltb/storage.py`:

```python
self.handoffs_dir = self.base / "handoffs"
```

Include `self.handoffs_dir` in layout, then add:

```python
def save_handoff(self, handoff: AgentHandoff) -> None:
    self._write_model(self.handoffs_dir / f"{handoff.id}.json", handoff)


def load_handoff(self, handoff_id: str) -> AgentHandoff:
    return self._read_model(self.handoffs_dir / f"{handoff_id}.json", AgentHandoff)


def list_handoffs_for_ticket(self, ticket_id: str) -> list[AgentHandoff]:
    handoffs = [
        self._read_model(path, AgentHandoff)
        for path in sorted(self.handoffs_dir.glob("*.json"))
    ]
    return sorted(
        [handoff for handoff in handoffs if handoff.ticket_id == ticket_id],
        key=lambda handoff: handoff.created_at,
    )
```

- [ ] **Step 5: Add handoff helper**

Create `ariadne_ltb/handoffs.py`:

```python
from __future__ import annotations

from ariadne_ltb.journal import runtime_event
from ariadne_ltb.models import (
    AgentHandoff,
    CommentAuthorType,
    CommentKind,
    HandoffStatus,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


def record_handoff(
    store: AriadneStore,
    ticket,
    runtime_id: str,
    from_agent: str,
    to_agent: str,
    reason: str,
    assignment_id: str | None = None,
    payload_ref: str | None = None,
    status: HandoffStatus = HandoffStatus.COMPLETED,
) -> AgentHandoff:
    handoff = AgentHandoff(
        id=stable_id("handoff", ticket.id, from_agent, to_agent, reason, payload_ref or ""),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        from_agent=from_agent,
        to_agent=to_agent,
        from_assignment_id=assignment_id,
        reason=reason,
        payload_ref=payload_ref,
        status=status,
    )
    if status is HandoffStatus.COMPLETED:
        handoff = handoff.mark_completed()
    store.save_handoff(handoff)
    store.add_comment(
        ticket,
        CommentAuthorType.AGENT,
        from_agent,
        CommentKind.HANDOFF,
        f"{from_agent} -> {to_agent}: {reason}",
        payload_ref=handoff.id,
    )
    store.append_runtime_event(
        runtime_event(
            ticket,
            runtime_id,
            "handoff",
            status.value,
            from_agent,
            assignment_id=assignment_id,
            payload_ref=handoff.id,
            metadata={"from_agent": from_agent, "to_agent": to_agent, "reason": reason},
        )
    )
    return handoff
```

- [ ] **Step 6: Emit handoffs in orchestrator**

Modify `TicketRunOrchestrator.run_ticket()`:

```python
record_handoff(self.store, ticket, self.runtime_id, "Build Lead", "Planner", "Need Build Packet and coding handoff.", self.assignment_id)
```

Add the remaining handoffs at stage boundaries:

```python
record_handoff(..., "Planner", "Execution", "Build Packet and handoff are ready.", payload_ref=handoff_artifact.id)
record_handoff(..., "Execution", "Reviewer", "Execution produced result, diff, and tests.", payload_ref=execution.id)
record_handoff(..., "Reviewer", "Memory", f"Reviewer verdict={review.verdict.value}.", payload_ref=review_artifact.id)
record_handoff(..., "Memory", "Build Lead", "Memory and next tickets are written.", payload_ref=next_tickets_artifact.id)
```

If `review.verdict.value == "needs_fix"`, also emit:

```python
record_handoff(..., "Reviewer", "Execution", "Reviewer requested a fix.", status=HandoffStatus.BLOCKED)
```

- [ ] **Step 7: Add handoff CLI**

Modify `ariadne_ltb/cli.py`:

```python
@ticket_app.command("handoffs")
def ticket_handoffs(ticket_id: str) -> None:
    store = AriadneStore(state.root)
    ticket = store.resolve_ticket(ticket_id)
    handoffs = store.list_handoffs_for_ticket(ticket.id)
    if not handoffs:
        typer.echo("No handoffs.")
        return
    for handoff in handoffs:
        typer.echo(
            f"{handoff.from_agent} -> {handoff.to_agent}\t{handoff.status.value}\t"
            f"{handoff.reason}\t{handoff.payload_ref or ''}"
        )
```

- [ ] **Step 8: Add board handoff section**

Modify `ariadne_ltb/board.py` to add `### Agent Handoffs` per ticket with rows:

```text
from_agent -> to_agent | status | reason | payload_ref | created_at
```

- [ ] **Step 9: Run handoff tests and commit**

Run:

```bash
pytest tests/test_v1_handoffs.py -q
pytest tests/test_true_mvp_product_loop.py -q
pytest tests/test_agent_teammate_mode.py -q
```

Commit:

```bash
git add ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/handoffs.py ariadne_ltb/orchestrator.py ariadne_ltb/cli.py ariadne_ltb/board.py tests/test_v1_handoffs.py
git commit -m "feat: add visible agent handoff chain"
```

---

### Task 4: ARI-010 Real Codex Teammate Backend

**Files:**
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/execution.py`
- Modify: `ariadne_ltb/daemon.py`
- Modify: `ariadne_ltb/runtime.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `ariadne_ltb/board.py`
- Test: `tests/test_v1_codex_teammate.py`

- [ ] **Step 1: Write failing Codex teammate tests**

Create `tests/test_v1_codex_teammate.py`:

```python
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.execution import ClaudeCodeBackend, CodexBackend, ExecutionContext
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import AssignmentStatus, FailureReason
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_codex_template_supports_assignment_and_run_ids(monkeypatch, tmp_path: Path) -> None:
    target = ensure_demo_target_project(tmp_path)
    monkeypatch.setenv(
        "ARIADNE_CODEX_COMMAND_TEMPLATE",
        "codex exec --cd {target_repo} --prompt-file {handoff_file} --ticket {ticket_key} --assignment {assignment_id} --run {run_id}",
    )
    context = ExecutionContext(
        ticket_id="ticket_123",
        ticket_key="ARI-123",
        build_packet_id="packet_123",
        target_repo_path=str(target),
        handoff_prompt="Add demo-todo export-json support.",
        backend_name="codex",
        allowed_paths=["demo_todo/cli.py", "tests/test_cli.py"],
        command="",
        test_command="pytest",
        assignment_id="assignment_123",
        run_id="run_123",
    )

    command = CodexBackend().render_command(context)

    assert "assignment_123" in command
    assert "run_123" in command


def test_assign_to_codex_blocks_without_gate_and_no_fake_fallback(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "codex"])
    run = runner.invoke(app, ["--root", str(tmp_path), "daemon", "run-once"])

    ticket = store.resolve_ticket("ARI-003")
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    execution_id = store.load_ticket(ticket.id).metadata["execution_result_id"]
    execution = store.load_execution_result(execution_id)
    comments = store.list_comments(ticket.id)

    assert assign.exit_code == 0, assign.output
    assert run.exit_code == 0, run.output
    assert assignment.status is AssignmentStatus.BLOCKED
    assert execution.backend_name == "codex"
    assert execution.failure_reason is FailureReason.EXTERNAL_EXECUTION_BLOCKED
    assert "fake-codex" not in execution.command
    assert any("blocked" in comment.body.lower() for comment in comments)


def test_claude_backend_is_gated(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", raising=False)
    target = ensure_demo_target_project(tmp_path)
    result = ClaudeCodeBackend().execute(
        ExecutionContext(
            ticket_id="ticket_123",
            ticket_key="ARI-123",
            build_packet_id="packet_123",
            target_repo_path=str(target),
            handoff_prompt="Add demo-todo export-json support.",
            backend_name="claude-code",
            allowed_paths=["demo_todo/cli.py", "tests/test_cli.py"],
            command="",
            test_command="pytest",
        )
    )

    assert result.blocked is True
    assert result.failure_reason is FailureReason.EXTERNAL_EXECUTION_BLOCKED


def test_backend_doctor_reports_codex_gate_without_secret(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-value-not-visible")
    monkeypatch.setenv("ARIADNE_ENABLE_EXTERNAL_EXECUTION", "1")
    result = CliRunner().invoke(app, ["--root", str(tmp_path), "backend", "doctor"])

    assert result.exit_code == 0, result.output
    assert "external execution enabled? yes" in result.output.lower()
    assert "confirm required? yes" in result.output.lower()
    assert "secret-value-not-visible" not in result.output
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest tests/test_v1_codex_teammate.py -q
```

Expected: failures for missing `assignment_id` and `run_id` on `ExecutionContext`, weaker doctor output, or daemon result handling.

- [ ] **Step 3: Extend ExecutionContext**

Modify `ariadne_ltb/models.py`:

```python
class ExecutionContext(AriadneModel):
    ...
    assignment_id: str | None = None
    run_id: str | None = None
```

- [ ] **Step 4: Pass assignment and run IDs**

Modify `ariadne_ltb/orchestrator.py` when constructing `ExecutionContext`:

```python
assignment_id=self.assignment_id,
run_id=execution_run.id,
```

- [ ] **Step 5: Extend Codex command rendering**

Modify `CodexBackend.render_command()` in `ariadne_ltb/execution.py`:

```python
return template.format(
    target_repo=context.target_repo_path,
    handoff_file=handoff_file,
    ticket_id=context.ticket_id,
    ticket_key=context.ticket_key or context.ticket_id,
    assignment_id=context.assignment_id or "",
    run_id=context.run_id or "",
)
```

- [ ] **Step 6: Tighten handoff file content**

Modify `ariadne_ltb/planner.py::render_handoff()` so the handoff includes:

```text
## Safety Constraints

- Do not commit, push, merge, or create a PR.
- Do not edit files outside Allowed Paths.
- Do not write secrets.
- Stop after tests pass and report stdout, stderr, exit code, changed files, diff, and tests.
```

- [ ] **Step 7: Enhance backend doctor output**

Modify `backend_doctor` output to include:

```text
Codex command path: <path|missing>
Codex command template set? yes|no
External execution enabled? yes|no
Confirm required? yes
Claude command path: <path|missing>
```

Keep current set/unset lines for compatibility.

- [ ] **Step 8: Run Codex teammate tests and commit**

Run:

```bash
pytest tests/test_v1_codex_teammate.py -q
pytest tests/test_backend_smoke_cli.py -q
pytest tests/test_true_mvp_product_loop.py -q
```

Commit:

```bash
git add ariadne_ltb/models.py ariadne_ltb/execution.py ariadne_ltb/orchestrator.py ariadne_ltb/planner.py ariadne_ltb/cli.py tests/test_v1_codex_teammate.py
git commit -m "feat: promote Codex backend to teammate path"
```

---

### Task 5: ARI-011 Upstream Planner and Source Intelligence

**Files:**
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/ingest.py`
- Modify: `ariadne_ltb/planner.py`
- Create: `ariadne_ltb/planner_quality.py`
- Modify: `ariadne_ltb/board.py`
- Create: `examples/sources/ariadne_self_improvement_note.md`
- Test: `tests/test_v1_planner_quality.py`

- [ ] **Step 1: Write failing planner quality tests**

Create `tests/test_v1_planner_quality.py`:

```python
from __future__ import annotations

from pathlib import Path

from ariadne_ltb.ingest import ingest_sources, source_document_from_path
from ariadne_ltb.models import BuildDecision
from ariadne_ltb.planner import DeterministicPlanner, LLMPlanner
from ariadne_ltb.storage import AriadneStore


def test_arbitrary_markdown_extracts_title_headings_actions_and_evidence(tmp_path: Path) -> None:
    source_path = tmp_path / "generic.md"
    source_path.write_text(
        "# Add Runtime Search\n\n"
        "## Problem\n\n"
        "We should implement memory search before planning.\n\n"
        "## Acceptance\n\n"
        "- add CLI search\n"
        "- evaluate results\n",
        encoding="utf-8",
    )

    source = source_document_from_path(source_path)

    assert source.title == "Add Runtime Search"
    assert source.metadata["headings"] == ["Problem", "Acceptance"]
    assert "implement" in source.metadata["action_verbs"]
    assert len(source.metadata["evidence_snippets"]) >= 2


def test_deterministic_planner_scores_build_packet_quality(tmp_path: Path) -> None:
    source_path = tmp_path / "feature.md"
    source_path.write_text(
        "# CLI Feature\n\nImplementation note: add CLI command and tests for a feature.\n",
        encoding="utf-8",
    )
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source_path])[0]
    result = DeterministicPlanner().plan_ticket(store, ticket)
    packet = store.load_build_packet(result.build_packet_id)

    assert packet.build_decision is BuildDecision.CODE_TASK
    quality = packet.metadata["quality"]
    assert 0 <= quality["overall_quality"] <= 1
    assert quality["evidence_coverage_score"] > 0
    assert quality["acceptance_criteria_score"] > 0


def test_llm_planner_invalid_json_writes_error_artifact(tmp_path: Path) -> None:
    class BadClient:
        def complete_json(self, prompt: str, schema_name: str) -> dict:
            return {"source_summary": "missing required fields"}

    source_path = tmp_path / "llm.md"
    source_path.write_text("# LLM Note\n\nBuild a feature.\n", encoding="utf-8")
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source_path])[0]

    result = LLMPlanner(client=BadClient()).plan_ticket(store, ticket)

    assert result.succeeded is False
    assert result.error_artifact_path
    assert Path(result.error_artifact_path).exists()


def test_self_improvement_source_generates_code_task_or_architecture_change(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "examples" / "sources" / "ariadne_self_improvement_note.md"
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [source])[0]
    packet = store.load_build_packet(ticket.build_packet_id)

    assert packet.build_decision in {BuildDecision.CODE_TASK, BuildDecision.ARCHITECTURE_CHANGE}
    assert len(packet.evidence) >= 2
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest tests/test_v1_planner_quality.py -q
```

Expected: failures for missing source metadata and packet quality.

- [ ] **Step 3: Add packet metadata field**

Modify `ariadne_ltb/models.py`:

```python
class BuildPacket(AriadneModel):
    ...
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Create planner quality module**

Create `ariadne_ltb/planner_quality.py`:

```python
from __future__ import annotations

from ariadne_ltb.models import BuildPacket


def score_build_packet(packet: BuildPacket) -> dict[str, float]:
    evidence_coverage_score = min(len(packet.evidence) / 5, 1.0)
    task_clarity_score = 1.0 if packet.tasks and all(len(task) >= 12 for task in packet.tasks) else 0.4
    acceptance_criteria_score = min(len(packet.acceptance_criteria) / 3, 1.0)
    scope_risk_score = 1.0 if packet.affected_modules and len(packet.affected_modules) <= 6 else 0.5
    overall_quality = round(
        (
            evidence_coverage_score
            + task_clarity_score
            + acceptance_criteria_score
            + scope_risk_score
        )
        / 4,
        3,
    )
    return {
        "evidence_coverage_score": round(evidence_coverage_score, 3),
        "task_clarity_score": round(task_clarity_score, 3),
        "acceptance_criteria_score": round(acceptance_criteria_score, 3),
        "scope_risk_score": round(scope_risk_score, 3),
        "overall_quality": overall_quality,
    }
```

- [ ] **Step 5: Strengthen markdown parsing**

Modify `ariadne_ltb/ingest.py`:

```python
def extract_headings(content: str) -> list[str]:
    return [line.lstrip("#").strip() for line in content.splitlines() if line.startswith("## ")]


def extract_action_verbs(content: str) -> list[str]:
    verbs = ["implement", "add", "compare", "evaluate", "build", "improve", "review", "design"]
    lower = content.lower()
    return [verb for verb in verbs if verb in lower]


def extract_evidence_snippets(content: str) -> list[str]:
    candidates = [
        line.strip("- ").strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return candidates[:5] if len(candidates) >= 2 else candidates[:1]
```

Include metadata in `source_document_from_path()`:

```python
metadata={
    "filename": path.name,
    "headings": extract_headings(content),
    "action_verbs": extract_action_verbs(content),
    "evidence_snippets": extract_evidence_snippets(content),
}
```

- [ ] **Step 6: Improve deterministic decision rules**

Modify `decision_for_source()`:

```python
haystack = f"{source.title} {source.summary} {' '.join(source.metadata.get('action_verbs', []))}".lower()
if any(word in haystack for word in ["implementation", "implement", "cli", "github", "readme", "feature", "add"]):
    return BuildDecision.CODE_TASK
if any(word in haystack for word in ["evaluation", "benchmark", "metric", "paper", "evaluate"]):
    return BuildDecision.EXPERIMENT
if any(word in haystack for word in ["architecture", "decision", "tradeoff", "design"]):
    return BuildDecision.ARCHITECTURE_CHANGE
return BuildDecision.WATCHLIST
```

- [ ] **Step 7: Attach quality summary to packets**

In `build_packet_from_source()` and `_packet_from_llm_json()`, after creating packet:

```python
quality = score_build_packet(packet)
packet = packet.model_copy(update={"metadata": packet.metadata | {"quality": quality, "planner_mode": "deterministic"}})
```

For LLM planner, use `"planner_mode": "llm"`.

- [ ] **Step 8: Add self-improvement source**

Create `examples/sources/ariadne_self_improvement_note.md`:

```markdown
# Ariadne Self Improvement Note

## Current Gap

Ariadne should improve daemon heartbeat, safe retry, handoff visibility, and real Codex teammate execution.

## Build Direction

Implement local runtime supervision, assignment retry commands, agent handoff comments, and board visibility without adding a server.

## Acceptance Signals

- daemon status shows heartbeat and stale detection.
- ticket retry creates a new assignment instead of overwriting history.
- ticket handoffs shows planner, execution, review, memory, and build lead transitions.
- real Codex execution remains safety-gated.
```

- [ ] **Step 9: Show quality on board**

Modify `ariadne_ltb/board.py` Build Packet section to print:

```text
- Quality score: `<overall_quality>`
- Evidence coverage: `<evidence_coverage_score>`
- Task clarity: `<task_clarity_score>`
- Scope risk: `<scope_risk_score>`
- Planner mode: `<planner_mode>`
```

- [ ] **Step 10: Run planner tests and commit**

Run:

```bash
pytest tests/test_v1_planner_quality.py -q
pytest tests/test_true_mvp_product_loop.py -q
```

Commit:

```bash
git add ariadne_ltb/models.py ariadne_ltb/ingest.py ariadne_ltb/planner.py ariadne_ltb/planner_quality.py ariadne_ltb/board.py examples/sources/ariadne_self_improvement_note.md tests/test_v1_planner_quality.py
git commit -m "feat: improve source intelligence and packet quality"
```

---

### Task 6: ARI-012 Workbench Board and Local UX

**Files:**
- Modify: `ariadne_ltb/board.py`
- Create: `ariadne_ltb/board_server.py`
- Modify: `ariadne_ltb/cli.py`
- Create: `docs/ops/HUMAN_DEMO_SCRIPT.md`
- Test: `tests/test_v1_board_ux.py`

- [ ] **Step 1: Write failing board UX tests**

Create `tests/test_v1_board_ux.py`:

```python
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.board_server import board_serve_command
from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.orchestrator import TicketRunOrchestrator
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_board_contains_v1_workbench_sections(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    TicketRunOrchestrator(store).run_ticket("ARI-003", backend_name="fake-codex")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "export", "board"])
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    for heading in [
        "Ariadne v1.0 Workbench",
        "System Summary",
        "Agent Queue",
        "Tickets by Status",
        "Active Assignments",
        "Daemon / Runtime",
        "Agent Comments",
        "Recent Journal Events",
        "Executed Tickets",
        "Next Tickets",
        "Backend Capability",
        "Safety Gates",
        "Assignment Retry Chain",
        "Agent Handoffs",
        "Codex Gate Status",
    ]:
        assert heading in board


def test_board_serve_command_builds_expected_handler(tmp_path: Path) -> None:
    board_dir = tmp_path / ".ariadne" / "board"
    board_dir.mkdir(parents=True)
    (board_dir / "index.html").write_text("<h1>Ariadne</h1>", encoding="utf-8")

    config = board_serve_command(board_dir, port=0, dry_run=True)

    assert config["directory"] == str(board_dir)
    assert config["port"] == 0


def test_cli_outputs_readable_ticket_state(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"])
    show = runner.invoke(app, ["--root", str(tmp_path), "ticket", "show", "ARI-003"])

    assert assign.exit_code == 0, assign.output
    assert show.exit_code == 0, show.output
    assert "Assignment:" in show.output
    assert "Status:" in show.output
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest tests/test_v1_board_ux.py -q
```

Expected: missing `board_server.py` and board sections.

- [ ] **Step 3: Rework board top sections**

Modify `ariadne_ltb/board.py` so `export_board()` starts with:

```markdown
# Ariadne v1.0 Workbench

## System Summary
## Agent Queue
## Tickets by Status
## Active Assignments
## Daemon / Runtime
## Agent Comments
## Recent Journal Events
## Executed Tickets
## Next Tickets
## Backend Capability
## Safety Gates
## Codex Gate Status
```

Use existing store methods only; do not add a server dependency.

- [ ] **Step 4: Add board server helper**

Create `ariadne_ltb/board_server.py`:

```python
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def board_serve_command(board_dir: Path, port: int = 8765, dry_run: bool = False) -> dict[str, str | int]:
    board_dir = board_dir.resolve()
    if not board_dir.exists():
        raise FileNotFoundError(f"board directory does not exist: {board_dir}")
    if dry_run:
        return {"directory": str(board_dir), "port": port}
    handler = partial(SimpleHTTPRequestHandler, directory=str(board_dir))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"Serving Ariadne board at http://127.0.0.1:{server.server_port}/")
    server.serve_forever()
    return {"directory": str(board_dir), "port": server.server_port}
```

- [ ] **Step 5: Add board CLI**

Modify `ariadne_ltb/cli.py`:

```python
board_app = typer.Typer(help="Local board commands.")
app.add_typer(board_app, name="board")


@board_app.command("serve")
def board_serve(
    port: Annotated[int, typer.Option("--port")] = 8765,
) -> None:
    from ariadne_ltb.board_server import board_serve_command

    board_dir = AriadneStore(state.root).board_dir
    board_serve_command(board_dir, port=port)
```

- [ ] **Step 6: Add human demo script**

Create `docs/ops/HUMAN_DEMO_SCRIPT.md`:

```markdown
# Ariadne v1.0 Human Demo Script

## Three Minute Path

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari runtime journal
ari export board
ari board serve
```

## Talk Track

Ariadne turns external knowledge into Build Tickets, assigns a Ticket to an Agent teammate, lets a local daemon claim the work, captures execution and review evidence, writes memory, generates next tickets, and shows the whole process on a local board.

## What To Point At

- Ticket assignment proves the work is visible before execution.
- Comments prove the Agent reports progress.
- Runtime journal proves the local worker is auditable.
- Board proves the full loop can be reviewed without reading JSON files.
```
```

- [ ] **Step 7: Run board tests and commit**

Run:

```bash
pytest tests/test_v1_board_ux.py -q
pytest tests/test_agent_teammate_mode.py -q
```

Commit:

```bash
git add ariadne_ltb/board.py ariadne_ltb/board_server.py ariadne_ltb/cli.py docs/ops/HUMAN_DEMO_SCRIPT.md tests/test_v1_board_ux.py
git commit -m "feat: add v1 workbench board UX"
```

---

### Task 7: ARI-013 Evaluation, Demo, and Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/development_report.md`
- Create: `docs/evaluation/v1_0_evaluation.md`
- Create: `docs/demo/ARIADNE_V1_DEMO_SCRIPT.md`
- Create: `docs/interview/PROJECT_NARRATIVE.md`
- Create: `docs/ops/V1_RELEASE_CHECKLIST.md`
- Test: `tests/test_v1_docs.py`

- [ ] **Step 1: Write failing docs tests**

Create `tests/test_v1_docs.py`:

```python
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v1_docs_exist_and_name_real_limitations() -> None:
    paths = [
        ROOT / "docs" / "evaluation" / "v1_0_evaluation.md",
        ROOT / "docs" / "demo" / "ARIADNE_V1_DEMO_SCRIPT.md",
        ROOT / "docs" / "interview" / "PROJECT_NARRATIVE.md",
        ROOT / "docs" / "ops" / "V1_RELEASE_CHECKLIST.md",
    ]
    for path in paths:
        assert path.exists(), path
        text = path.read_text(encoding="utf-8")
        assert "Ariadne v1.0" in text
        assert "local" in text.lower() or "本地" in text

    narrative = (ROOT / "docs" / "interview" / "PROJECT_NARRATIVE.md").read_text(encoding="utf-8")
    assert "不是普通 RAG" in narrative
    assert "不是重新造 Codex" in narrative
    assert "Multica" in narrative


def test_readme_has_v1_quickstart_and_limitations() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Ariadne v1.0" in readme
    assert "ari daemon run-once" in readme
    assert "ari board serve" in readme
    assert "JSON/JSONL" in readme
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest tests/test_v1_docs.py -q
```

Expected: missing docs.

- [ ] **Step 3: Add evaluation report skeleton with real command slots**

Create `docs/evaluation/v1_0_evaluation.md`:

```markdown
# Ariadne v1.0 Evaluation

## Scope

This report evaluates Ariadne v1.0 as a local-first, Ticket-centered Agent Workbench.

## Commands

- `pytest`
- `ruff check .`
- `python3.11 -m ariadne_ltb.cli demo full`
- `python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md`
- `python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to fake-codex`
- `python3.11 -m ariadne_ltb.cli daemon run-once`
- `python3.11 -m ariadne_ltb.cli export board`
- `python3.11 -m ariadne_ltb.cli doctor v1`

## Results

Planning phase status: evaluation commands are not run while writing this plan. Task 8 Step 7 replaces this sentence with the exact `pytest`, `ruff check .`, and `scripts/verify_v1.sh` results from the implementation branch.

## Safety

Real Codex and Claude execution remain gated by `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and `--confirm-execution`. Feishu real writes remain gated by `FEISHU_ENABLE_WRITE=1` and `--confirm-write`.

## Known Limitations

- Local single-worker runtime.
- JSON/JSONL persistence.
- No production web UI.
- Real Codex depends on the local Codex CLI.
- Feishu real writes are default-off.
```

- [ ] **Step 4: Add demo script doc**

Create `docs/demo/ARIADNE_V1_DEMO_SCRIPT.md` with the command path and expected output for each step.

- [ ] **Step 5: Add interview narrative**

Create `docs/interview/PROJECT_NARRATIVE.md` in Chinese with these sections:

```markdown
# Ariadne v1.0 Project Narrative

## 这个项目解决什么问题
## 为什么不是普通 RAG
## 为什么不是重新造 Codex
## 为什么对标 Multica
## Ariadne 和 Multica 的差异
## Build Ticket / Assignment / Daemon / Review / Memory 的设计价值
## Agent 能力点
## 工程难点
## 已知限制和下一步
```

Every section should contain concrete Ariadne details, not slogans.

- [ ] **Step 6: Add release checklist**

Create `docs/ops/V1_RELEASE_CHECKLIST.md` with checkboxes for tests, CLI path, board, safety gates, no secrets, and limitations.

- [ ] **Step 7: Update README and development report**

Add a `## Ariadne v1.0 Quickstart` section to `README.md` with:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari runtime journal
ari runtime recover
ari export board
ari board serve
```

Add current limitations to README and `docs/development_report.md`.

- [ ] **Step 8: Run docs tests and commit**

Run:

```bash
pytest tests/test_v1_docs.py -q
```

Commit:

```bash
git add README.md docs/development_report.md docs/evaluation/v1_0_evaluation.md docs/demo/ARIADNE_V1_DEMO_SCRIPT.md docs/interview/PROJECT_NARRATIVE.md docs/ops/V1_RELEASE_CHECKLIST.md tests/test_v1_docs.py
git commit -m "docs: finalize Ariadne v1 narrative and demo"
```

---

### Task 8: ARI-014 Final Safety Gate and Release Readiness

**Files:**
- Create: `ariadne_ltb/doctor.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `.gitignore`
- Create: `scripts/verify_v1.sh`
- Modify: `docs/evaluation/v1_0_evaluation.md`
- Modify: `docs/development_report.md`
- Test: `tests/test_v1_doctor_release.py`

- [ ] **Step 1: Write failing release doctor tests**

Create `tests/test_v1_doctor_release.py`:

```python
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_doctor_secrets_does_not_print_secret_values(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-leak-deepseek")
    monkeypatch.setenv("FEISHU_APP_SECRET", "do-not-leak-feishu")

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "doctor", "secrets"])

    assert result.exit_code == 0, result.output
    assert "DEEPSEEK_API_KEY: set" in result.output
    assert "FEISHU_APP_SECRET: set" in result.output
    assert "do-not-leak" not in result.output


def test_doctor_v1_reports_local_readiness(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    runner.invoke(app, ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"])
    runner.invoke(app, ["--root", str(tmp_path), "daemon", "run-once"])
    runner.invoke(app, ["--root", str(tmp_path), "export", "board"])

    result = runner.invoke(app, ["--root", str(tmp_path), "doctor", "v1"])

    assert result.exit_code == 0, result.output
    assert "agent profiles: ok" in result.output
    assert "backend capability: ok" in result.output
    assert "source fixtures: ok" in result.output
    assert "board: ok" in result.output
    assert "safety gates: ok" in result.output


def test_gitignore_contains_v1_secret_patterns() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for pattern in [".env", ".env.*", "*.secret", "secrets/", ".ariadne/"]:
        assert pattern in gitignore


def test_verify_v1_script_exists_and_is_executable() -> None:
    script = ROOT / "scripts" / "verify_v1.sh"
    assert script.exists()
    assert script.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
pytest tests/test_v1_doctor_release.py -q
```

Expected: missing doctor app and verify script.

- [ ] **Step 3: Add doctor module**

Create `ariadne_ltb/doctor.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.storage import AriadneStore


SECRET_ENV_VARS = [
    "DEEPSEEK_API_KEY",
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_TENANT_ACCESS_TOKEN",
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
]


def secret_status_lines() -> list[str]:
    return [f"{name}: {'set' if os.environ.get(name) else 'unset'}" for name in SECRET_ENV_VARS]


def v1_readiness_lines(store: AriadneStore, repo_root: Path) -> list[str]:
    profiles = store.ensure_default_agent_profiles()
    capabilities = collect_runtime_capabilities()
    fixtures_ok = (repo_root / "examples" / "sources").exists()
    board_ok = (store.board_dir / "index.md").exists()
    gitignore_text = (repo_root / ".gitignore").read_text(encoding="utf-8")
    safety_ok = all(pattern in gitignore_text for pattern in [".env", ".env.*", "*.secret", "secrets/", ".ariadne/"])
    lines = [
        f"agent profiles: {'ok' if profiles else 'missing'}",
        f"backend capability: {'ok' if capabilities else 'missing'}",
        f"source fixtures: {'ok' if fixtures_ok else 'missing'}",
        f"ticket count: {len(store.list_tickets())}",
        f"assignment queue: {len(store.list_assignments())}",
        f"journal exists: {'ok' if store.journal_path.exists() else 'missing'}",
        f"board: {'ok' if board_ok else 'missing'}",
        f"safety gates: {'ok' if safety_ok else 'missing'}",
    ]
    return lines
```

- [ ] **Step 4: Add doctor CLI**

Modify `ariadne_ltb/cli.py`:

```python
doctor_app = typer.Typer(help="Release and safety doctors.")
app.add_typer(doctor_app, name="doctor")


@doctor_app.command("secrets")
def doctor_secrets() -> None:
    from ariadne_ltb.doctor import secret_status_lines

    for line in secret_status_lines():
        typer.echo(line)


@doctor_app.command("v1")
def doctor_v1() -> None:
    from ariadne_ltb.doctor import v1_readiness_lines

    store = AriadneStore(state.root)
    for line in v1_readiness_lines(store, state.root):
        typer.echo(line)
```

- [ ] **Step 5: Add final verification script**

Create `scripts/verify_v1.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md
python3.11 -m ariadne_ltb.cli ticket list
python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to fake-codex
python3.11 -m ariadne_ltb.cli daemon run-once
python3.11 -m ariadne_ltb.cli ticket comments ARI-003
python3.11 -m ariadne_ltb.cli runtime journal
python3.11 -m ariadne_ltb.cli runtime recover
python3.11 -m ariadne_ltb.cli daemon status
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
python3.11 -m ariadne_ltb.cli doctor secrets
python3.11 -m ariadne_ltb.cli doctor v1
```

Run:

```bash
chmod +x scripts/verify_v1.sh
```

- [ ] **Step 6: Run doctor tests and final acceptance**

Run:

```bash
pytest tests/test_v1_doctor_release.py -q
pytest
ruff check .
scripts/verify_v1.sh
```

Expected: all commands pass. If `ruff` is unavailable, install dev dependencies with the existing project flow or document the exact blocker in `docs/development_report.md`.

- [ ] **Step 7: Update evaluation and development report with exact results**

Update:

- `docs/evaluation/v1_0_evaluation.md`
- `docs/development_report.md`

Record:

```text
pytest result
ruff result
scripts/verify_v1.sh result
main v1 chain result
CodexBackend gated status
known limitations
```

- [ ] **Step 8: Commit release readiness**

Commit:

```bash
git add ariadne_ltb/doctor.py ariadne_ltb/cli.py .gitignore scripts/verify_v1.sh docs/evaluation/v1_0_evaluation.md docs/development_report.md tests/test_v1_doctor_release.py
git commit -m "chore: add v1 safety doctor and verification"
```

---

## Final Verification

Run the required commands exactly:

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md
python3.11 -m ariadne_ltb.cli ticket list
python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to fake-codex
python3.11 -m ariadne_ltb.cli daemon run-once
python3.11 -m ariadne_ltb.cli ticket comments ARI-003
python3.11 -m ariadne_ltb.cli runtime journal
python3.11 -m ariadne_ltb.cli runtime recover
python3.11 -m ariadne_ltb.cli daemon status
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
python3.11 -m ariadne_ltb.cli doctor v1
```

If `uv run ari` is available, also run:

```bash
uv run ari demo full
uv run ari ticket run ARI-003 --backend fake-codex
uv run ari ticket assign ARI-003 --to fake-codex
uv run ari daemon run-once
uv run ari export board
```

## Branch Completion

After final verification passes:

```bash
git status --short --branch
git push -u origin codex/ariadne-v1-0-sprint
```

Create a PR to `main` or merge directly if the repository policy permits. For this single-user project, prefer a direct feature-to-main PR or direct merge after tests pass; do not create stacked PRs.

After merge:

```bash
git switch main
git pull --ff-only origin main
git branch -d codex/ariadne-v1-0-sprint
git push origin --delete codex/ariadne-v1-0-sprint
```

## Self-Review

- Spec coverage: ARI-000 through ARI-014 are mapped to Tasks 0-8.
- No production server, database, auth, WebSocket, or external-service test dependency is introduced.
- All external execution remains gated by env var plus CLI confirmation.
- Rollback cost is low: feature branch can be deleted, and `.ariadne/` local runtime state is gitignored.
- External dependencies are existing only: optional `codex`, optional `claude`, optional DeepSeek key, optional Feishu/lark-cli. Tests must pass without all of them.
