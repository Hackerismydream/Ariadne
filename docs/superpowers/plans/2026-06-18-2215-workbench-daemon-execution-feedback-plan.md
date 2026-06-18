# Workbench Daemon Execution Feedback Plan

Timestamp: 2026-06-18-2215

Status: Ready for implementation

## Goal

Turn the current Workbench dispatch path into a full local runtime loop:

```text
Workbench assign/run
  -> local daemon starts or is already running
  -> daemon claims assignment
  -> CodexBackend / ClaudeCodeBackend executes behind safety gates
  -> stdout/stderr/exit code/diff/tests/review are captured
  -> evidence flows back to the issue page without using Ariadne CLI as the product path
```

This is the next step after the Web dogfood readiness branch. The previous work
proved that the browser can create goals, add sources, generate issues, apply
issue deltas, assign `ARI-017`, and dispatch it. The missing product behavior is
that dispatch currently stops at "waiting for a local daemon runtime to claim
it."

## Product Acceptance

A user must be able to complete this from the browser:

1. Open Ariadne Workbench.
2. Select a generated Mini Code Agent issue.
3. Assign it to Codex or Claude Code.
4. Click Run.
5. Start or wake the local daemon from the Workbench if it is not running.
6. Watch the assignment move through:
   - queued;
   - claimed;
   - running;
   - blocked or done.
7. See returned evidence on the issue page:
   - handoff path;
   - execution result id;
   - stdout/stderr/exit code;
   - changed files;
   - git diff path;
   - test command and test exit code;
   - review verdict;
   - memory path;
   - Feishu plan path;
   - next tickets path.

If real Codex / Claude execution gates are closed, the page must show a clear
blocked result with the exact missing gate. It must not silently fall back to
`fake-codex` as the product path.

## Current System Facts

- `RunAssignmentService` already records a dispatch event and says a local daemon
  must claim the assignment.
- `LocalDaemonWorker.run_once()` already claims assignments and calls
  `TicketRunOrchestrator`.
- `RunEventService` already merges assignment records, runtime events, comments,
  and run messages into an assignment event stream.
- The Workbench already has assignment/run buttons and a WebSocket event stream.
- The gap is orchestration: the Web app does not own a local daemon lifecycle,
  cannot start/stop/step the daemon, and does not project enough execution
  evidence after the daemon finishes.

## Implementation Plan

### 1. Add Daemon Control Application Service

Create a small local-only service:

```text
ariadne_ltb/application/daemon_control.py
```

Responsibilities:

- report current daemon heartbeat and claimability;
- run one daemon step for a specific assignment;
- start a background local daemon loop for the current Ariadne root;
- stop a background local daemon loop;
- prevent duplicate daemon loops for the same root;
- write runtime events for start, stop, claim, blocked, and done states.

Do not expose shell execution directly. Use `LocalDaemonWorker` as the only
execution path.

### 2. Add HTTP Endpoints

Add endpoints:

```text
GET  /api/daemon/status
POST /api/daemon/start
POST /api/daemon/stop
POST /api/assignments/{assignment_id}/run-now
```

Expected behavior:

- `run-now` claims and runs exactly one assignment through `LocalDaemonWorker`.
- `start` starts a local background loop only for this workspace root.
- `stop` stops the loop gracefully where possible.
- all endpoints return a structured daemon status DTO.

Safety:

- real external execution still requires the existing confirmation token and
  execution gates;
- no endpoint may commit, push, merge, or create PRs;
- no endpoint may print secrets.

### 3. Add Runtime / Evidence Projection

Extend `/api/workbench` issue projection so the issue inspector can show:

- latest assignment state;
- latest execution result;
- stdout/stderr excerpts;
- exit code;
- changed files;
- diff artifact path;
- test command and result;
- review verdict;
- memory record path;
- Feishu plan path;
- next tickets path;
- blocked reason and typed failure reason.

The projection should be derived from existing store artifacts. Do not invent
fake evidence.

### 4. Update Workbench UI

Update the issue inspector and runtime page:

- show daemon status and heartbeat freshness;
- show buttons:
  - `启动本地运行时`;
  - `停止本地运行时`;
  - `立即 claim 并运行`;
- after `运行`, either start/step the daemon or show why it cannot run;
- stream assignment events until terminal state;
- display the evidence bundle once execution finishes or blocks.

UI text must stay Chinese.

### 5. Browser Dogfood Path

Use the existing Mini Code Agent dogfood:

```text
docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md
```

Browser-only validation target:

```text
ARI-017 -> assign to Codex -> run-now / daemon claim -> blocked or executed result appears in Workbench
```

Blocked is acceptable only if it is the honest safety-gated result from
CodexBackend / ClaudeCodeBackend, with exact gate evidence.

### 6. Tests

Add tests for:

- daemon status endpoint when no daemon is running;
- `run-now` claims a queued assignment and writes claim/start/done or blocked
  events;
- CodexBackend disabled gate returns blocked evidence through Workbench
  projection;
- Workbench projection includes execution result, changed files, test output,
  review, memory, Feishu plan, and next tickets paths when present;
- frontend API contract includes daemon status and evidence fields;
- browser-facing route does not fall back to fixture data in API mode.

Tests must not require:

- Codex installed;
- Claude installed;
- DeepSeek key;
- Feishu credentials;
- network access.

### 7. Verification Commands

Run:

```bash
pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
python3.11 -m ariadne_ltb.cli workbench serve --port 8766
```

Then verify in browser:

```text
http://127.0.0.1:8766/#issues/ARI-017
```

Required browser checks:

- assign button creates an assignment;
- run button dispatches;
- run-now or daemon start claims the assignment;
- timeline shows claim/start/blocked or done;
- evidence panels update without reloading fixture data.

## Review Checklist

- No `fake-codex` is used as the product default.
- `fake-codex` remains available only for deterministic tests and explicit
  offline fallback.
- Real Codex / Claude execution remains gated.
- Browser state is driven by `/api/workbench` and assignment event APIs.
- Daemon lifecycle is local to one Ariadne root.
- Failed execution produces visible evidence instead of disappearing into logs.
- Tests prove the blocked external-execution path without requiring Codex or
  Claude.

## Known Risks

- Running a long daemon loop inside the same server process can create shutdown
  and concurrency bugs. Prefer a minimal managed background task first, then
  graduate to a separate local process only if needed.
- `run-now` is the lowest-friction bridge for product dogfood, but it must not
  become an unsafe bypass around execution gates.
- Evidence projection can become slow if it scans all artifacts on every
  `/api/workbench` call. Start with latest-assignment lookup and only load
  artifacts for selected/latest tickets.

## Definition of Done

This step is done when Workbench can move a browser-created issue from dispatch
to daemon-claimed terminal state and show the resulting execution/review evidence
on the issue page.
