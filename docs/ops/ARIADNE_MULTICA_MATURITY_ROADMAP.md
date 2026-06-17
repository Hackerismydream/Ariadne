# Ariadne Multica Maturity Roadmap

Status: superseded

Superseded by:

```text
docs/ops/2026-06-17-2043-ARIADNE_PRODUCTION_AGENT_WORKBENCH_ROADMAP.md
```

Reason: this roadmap was too conservative for the current product goal. The
active direction is now production-first: real DeepSeek upstream LLM runtime,
real Codex, real Claude Code, gated real Feishu writes, and real GitHub
integration. `fake-codex` remains only for deterministic tests and offline
fallback.

Date: 2026-06-17

This document is the handoff for future Ariadne development. It records the
current target, the current branch reality, what has already landed, what still
needs work, and the order in which future agents should continue.

## North Star

Ariadne should reach Multica-level agent work-management maturity while staying
local-first, Python-based, single-user, deterministic, and safety-gated.

The product is not a Multica fork. The product is a local Python workbench that
absorbs Multica's issue, agent, runtime, skill, resource, progress, review, and
board model.

The current product loop is:

```text
Knowledge / Feedback / Codebase / optional Goal
  -> update Ticket backlog
  -> Ticket management center
  -> assign to Agent
  -> local Daemon / Runtime
  -> Codex / Claude / fake-codex
  -> Review / Comments / Board / Memory
  -> update Ticket backlog again
```

Goal can be input. Goal is not the center object. Build Ticket is the work
center, audit center, assignment center, review center, and board center.

## Authoritative Direction

Use these files as the source of truth:

```text
docs/adr/ADR-0004-ticket-centered-agent-workbench.md
docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
docs/ops/CODEX_NON_FRONTEND_SECTION_PLAN.md
docs/architecture/multica_architecture_digest.md
docs/architecture/ariadne_multica_gap_report.md
```

Do not revive the older BuildGoal-first direction. Files under
`docs/capability_surface/07_CODEX_MASTER_PROMPT.md` and older capability
surface docs are historical unless they explicitly defer to ADR-0004.

## Current Branch Reality

There are two important unmerged branches.

### Core branch

```text
branch: codex/ariadne-core-orchestration-backends-3
latest checked commit: 7421df7 feat: add memory retrieval planning
path: /Users/martinlos/code/Ariadne.worktrees/ariadne-core-orchestration-backends-3
status: pushed and clean when this document was written
```

This branch owns the Python product kernel:

- ticket backlog update engine;
- assignment claim and lease behavior;
- unified failure pipeline;
- run message stream;
- thread-aware comments;
- skill materialization;
- Build Team routing;
- provider capability matrix;
- real Codex teammate demo path;
- memory retrieval into planning;
- store doctor, secret doctor, prompt guard, permission profiles;
- orchestrator result manifests and board runtime evidence.

The last full local verification on this branch passed:

```text
python3.11 -m pytest
python3.11 -m ruff check .
scripts/verify_v1.sh
```

`scripts/verify_v1.sh` passed, but it also revealed a product hygiene issue:
repeated verification against the same persistent `.ariadne` root can leave
blocked assignments and stale heartbeat evidence from earlier runs. This is not
a failing test today, but future work should fix verification isolation or add a
cleanup/resume policy.

### Frontend branch

```text
branch: codex/ariadne-workbench-frontend-lane
latest checked commit: 21b1ff9 feat: add knowledge intake workbench page
path: /Users/martinlos/code/Ariadne
status: pushed and clean when this document was written
```

This branch owns the local web workbench lane:

- `frontend/ariadne-workbench`;
- Vite React local app;
- static local data sync script;
- knowledge intake workbench page;
- interaction fixes;
- frontend parity analysis.

The last local verification on this branch passed:

```text
python3.11 -m pytest -q
python3.11 -m ruff check .
npm --prefix frontend/ariadne-workbench run build
```

### Integration warning

Do not merge both branches independently into `main`.

The branches touch the same core files:

```text
README.md
ariadne_ltb/board.py
ariadne_ltb/cli.py
ariadne_ltb/execution.py
ariadne_ltb/models.py
ariadne_ltb/orchestrator.py
ariadne_ltb/storage.py
docs/development_report.md
tests/test_v1_board_ux.py
```

Create an integration branch from the core branch, merge the frontend branch
into it, resolve conflicts once, then verify the combined result.

Recommended branch:

```text
codex/ariadne-core-frontend-integration
```

## What Is Already Done

The core product is past the demo-only stage. These capabilities exist or have
been implemented on the current branches:

- reusable `ticket run` full loop;
- agent teammate mode with assignment and daemon surfaces;
- ticket comments, run messages, progress events, and board trace;
- knowledge and feedback driven backlog update engine;
- ticket relationship graph and dependency-aware promotion;
- lifecycle gates for tickets and assignments;
- retry, backoff, dead-letter, cancel, pause, resume, and supersede behavior;
- provider execution audit artifacts;
- store invariant doctor;
- secret and sensitive-file doctor;
- prompt injection guard;
- execution permission profiles;
- Build Team and Squad-style routing;
- provider capability matrix;
- fake-codex, real Codex, Claude scaffold, and shell backend surfaces;
- real Codex demo path with external execution gates;
- memory retrieval used by planner and handoff;
- worktree isolation, branch naming, target resource rebinding, landing
  evidence, merge gate policy, and conflict report foundations;
- first local React workbench branch.

Multica still remains ahead in end-to-end product maturity because it has a
hosted issue board, runtime registration, task lifecycle, inbox, agent
assignment UI, project resource UI, progress stream UI, and richer team
operations. Ariadne should close those gaps locally, not by copying Multica's
server stack.

## Remaining Work By Priority

### Phase 0: Integrate current branches

This must happen before more broad feature work.

Actions:

1. Create `codex/ariadne-core-frontend-integration` from
   `codex/ariadne-core-orchestration-backends-3`.
2. Merge `codex/ariadne-workbench-frontend-lane`.
3. Resolve conflicts by treating the core branch as the source of truth for
   Python models, storage, orchestrator, runtime, and CLI behavior.
4. Keep frontend branch additions where they consume stable `.ariadne` data or
   CLI JSON output.
5. Run the full combined verification:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
npm --prefix frontend/ariadne-workbench run build
```

Done means the integration branch is pushed, clean, and ready for review or
direct merge to `main`.

### Phase 1: Resource and execution safety

Purpose: make local execution safe enough for repeated real-agent work.

Primary issues:

```text
LOC-16 / ARI-MUL-11: Typed project resource boundaries
LOC-50 / ARI-MUL-45: Manual approval checkpoints
LOC-59 / ARI-MUL-54: Skill trust and provenance workflow
LOC-60 / ARI-MUL-55: Project resource permission profiles
```

Expected product changes:

- typed `ProjectResource` support beyond local directory;
- explicit resource permissions for local directory, GitHub repo, memory store,
  Feishu space, and future integrations;
- approval checkpoint artifacts before external execution, sensitive writes, or
  high-risk file changes;
- skill provenance metadata visible in handoff and board;
- no backend can silently widen its allowed resource scope.

Acceptance:

- `backend doctor` and board show resource and permission state;
- external execution remains blocked unless env gate and confirmation are both
  present;
- tests require no network, Codex, Claude, Feishu, DeepSeek, or GitHub token.

### Phase 2: Inbox, blocker handling, and local search

Purpose: make blocked work visible and searchable instead of buried in logs.

Primary issues:

```text
LOC-17 / ARI-MUL-12: Local inbox for blockers and follow-ups
LOC-18 / ARI-MUL-13: Local search over tickets/comments/memory
LOC-83 / ARI-MUL-78: Failure and blocker view
LOC-88 / ARI-MUL-83: Local search UI
```

Expected product changes:

- `.ariadne/inbox/` records for blockers, review follow-ups, failed approvals,
  and human decisions;
- `ari inbox list`, `ari inbox show`, and `ari inbox resolve`;
- `ari search` across tickets, comments, memory, artifacts, reviews, and
  inbox records;
- frontend consumes the same indexed JSON, not a separate UI-only cache.

Acceptance:

- every blocked run creates an inbox item with typed failure reason and next
  action;
- search can find a ticket by source evidence, comment text, memory text, and
  failure reason;
- board and web workbench show the same blocker state.

### Phase 3: Review and acceptance quality

Purpose: make the reviewer useful as a conservative teammate, not just a pass or
blocked flag.

Primary issues:

```text
LOC-19 / ARI-MUL-14: Review/eval agent with risk scoring
LOC-33 / ARI-MUL-28: Acceptance criteria quality gate
LOC-75 / ARI-MUL-70: Acceptance criteria evidence panel
LOC-86 / ARI-MUL-81: Review report UI
```

Expected product changes:

- review risk score;
- acceptance criterion coverage table;
- evidence links from diff, tests, comments, and artifacts;
- reviewer can distinguish product failure, test gap, safety risk, unclear
  requirement, and follow-up suggestion;
- risky passes become conditional passes with required follow-up tickets.

Acceptance:

- review reports are machine-readable and board-visible;
- every acceptance criterion is covered, failed, waived, or marked not
  applicable with evidence;
- ticket status cannot move to done when required acceptance criteria are
  missing evidence.

### Phase 4: Workdir reuse, cleanup, and store durability

Purpose: make repeated local agent runs boring and recoverable.

Primary issues:

```text
LOC-20 / ARI-MUL-15: Session/workdir reuse policy
LOC-45 / ARI-MUL-40: Local store schema version and migrations
LOC-46 / ARI-MUL-41: Store compaction and corruption recovery
LOC-47 / ARI-MUL-42: Workspace backup/export/import snapshots
LOC-107 / ARI-MUL-102: Worktree cleanup and rollback policy
```

Expected product changes:

- explicit workdir reuse rules for direct runs, daemon assignments, and real
  Codex or Claude execution;
- stale isolated worktree detection and cleanup command;
- store schema version file;
- read migrations for older JSON shapes;
- backup/export/import commands for `.ariadne`;
- verification script runs in an isolated temp root or cleans up after itself.

Acceptance:

- `scripts/verify_v1.sh` does not accumulate stale blocked state in the main
  project root;
- interrupted runs produce a deterministic resume, cleanup, or rollback path;
- store doctor can distinguish corruption, old schema, missing refs, and stale
  operational state.

### Phase 5: Board and web workbench parity

Purpose: make local state inspectable without reading raw JSON.

Primary issues:

```text
LOC-62 / ARI-MUL-57: Static board semantic parity with CLI state
LOC-66 / ARI-MUL-61: Local web workbench architecture ADR
LOC-67 / ARI-MUL-62: Local web data adapter
LOC-68 / ARI-MUL-63: Web command gateway
LOC-69 / ARI-MUL-64: Web safety gate model
LOC-70 to LOC-95: Web workbench views and parity tests
```

Expected product changes:

- board and web use the same typed local data;
- command gateway is local-only and explicit about unsafe operations;
- safety gate model is visible before any execution or write;
- web views cover tickets, details, relationships, backlog previews, sources,
  assignments, run timeline, runtime capability, blockers, artifacts, diffs,
  review reports, settings, and release evidence.

Acceptance:

- CLI, static board, and web workbench agree on ticket state;
- frontend tests cover the main local flows;
- no hosted auth, WebSocket server, multi-tenant workspace, or Postgres is
  introduced for v1.x.

### Phase 6: Dogfood and release readiness

Purpose: make Ariadne demonstrable as a real AI builder workbench.

Primary issues:

```text
LOC-51 / ARI-MUL-46: Local onboarding and doctor golden path
LOC-52 / ARI-MUL-47: Dogfood branch and merge policy evidence
LOC-53 / ARI-MUL-48: Release evidence packet
LOC-64 / ARI-MUL-59: End-to-end dogfood scenario pack
LOC-65 / ARI-MUL-60: Issue metadata governance and lint
LOC-93 / ARI-MUL-88: Web smoke tests
LOC-94 / ARI-MUL-89: CLI, static board, and web parity tests
```

Expected product changes:

- one-command local onboarding check;
- dogfood scenario that starts from sources and ends with reviewed code changes;
- release evidence packet with commands, artifacts, board path, memory path,
  next tickets, and limitations;
- issue metadata lint so the backlog stays useful;
- parity tests between CLI, board, and web.

Acceptance:

- a new local checkout can run the golden path without external credentials;
- real Codex and real Feishu remain optional and gated;
- release evidence can be reviewed without trusting agent prose.

## Deferred Or Avoided Work

Defer unless directly needed by a dogfood scenario:

- gated auto-commit and auto-push inside Ariadne runtime;
- optional auto-merge;
- Multica landing status sync;
- real Feishu writes;
- provider token and cost usage capture;
- recurring autopilot jobs.

Avoid for v1.x:

- copying Multica's Go server;
- requiring Postgres;
- requiring WebSockets;
- adding auth or multi-tenant hosted workspace behavior;
- making Multica a runtime dependency of Ariadne;
- default external execution or default external writes.

## Development Rules For Future Agents

Use this execution model:

```text
Human owner
  -> product direction and final main-merge judgment

Codex
  -> implementation lead
  -> local reviewer, verifier, integrator
  -> commit and push after checks pass

Multica
  -> campaign board and evidence log
  -> optional read-only review and planning assistant
```

For each code slice:

1. Start from the latest integration branch or `main`, not from a stale feature
   branch.
2. Declare the issue numbers and touched file set in the local progress note or
   Multica comment.
3. Keep the slice independently mergeable.
4. Add or update tests for the product behavior, not just the command surface.
5. Run the required verification commands.
6. Commit and push.
7. Write a Chinese closeout note with changed files, commands, result, risk,
   and next step.

Do not ask the human for reversible implementation choices. Stop only when a
choice would produce a materially different product direction.

## Required Verification Commands

For non-doc code slices:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
```

For frontend slices:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
npm --prefix frontend/ariadne-workbench run build
```

For integration branches, run both sets.

For docs-only slices:

```bash
git diff --check
```

## Merge Strategy

The next merge should be the integration branch, not either feature branch by
itself.

Recommended order:

1. `codex/ariadne-core-frontend-integration`
2. merge core branch into it;
3. merge frontend branch into it;
4. resolve conflicts once;
5. run full combined verification;
6. push integration branch;
7. merge integration branch to `main`;
8. delete or archive superseded feature branches only after `main` is green.

If conflicts appear between core product behavior and frontend assumptions,
keep the core model and adapt the frontend. The frontend is a consumer of local
state. It is not the source of truth for ticket, assignment, run, review,
memory, or safety semantics.

## Definition Of Multica-Level Local Maturity

Ariadne is close to the target when a local user can do this without reading raw
JSON:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to codex
ari daemon run-once --confirm-execution
ari inbox list
ari search "blocked export-json"
ari export board
ari workbench open
```

The user should see:

- why tickets exist;
- how knowledge changed the backlog;
- which agent owns each ticket;
- what runtime or backend will execute;
- what resources are allowed;
- what skills are referenced;
- what progress happened;
- what failed and why;
- what tests ran;
- what changed in git;
- what the reviewer decided;
- what memory was written;
- what next tickets were generated.

This is the local version of Multica maturity. It keeps the useful work
management architecture and removes the hosted product weight that Ariadne does
not need yet.
