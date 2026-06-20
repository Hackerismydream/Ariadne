# Browser Dogfood First Closure Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` when implementing. Do not reinterpret this as a general architecture cleanup plan. The only product acceptance path is the browser dogfood path described below.

**Goal:** Close Ariadne's real product loop by driving one browser-only dogfood scenario from external inputs to real Codex/Claude execution on the target project, with evidence and version progress visible in Workbench.

**Product Promise:** A user gives Ariadne a local project goal and external knowledge. Ariadne turns that into evidence-backed issues, assigns work to Codex/Claude, runs the target project work, and shows diff, target test output, review, memory, next issue, and version progress in the Workbench.

**Architecture:** Keep Ariadne local-first, single-user, Python/FastAPI/React, JSON/JSONL, and ticket-centered. Add only the smallest state needed to bind the current browser issue to the current target project, current handoff, current runtime authorization, current Codex/Claude run, and current evidence.

**Affected Surface:** This will touch more than 8 files across frontend, FastAPI routes, application services, models/storage, daemon/runtime, execution adapters, source/issue/handoff/review services, dogfood scripts, and docs. That is acceptable because the work is one product path, not unrelated refactoring.

---

## Non-Negotiable Rules

- **Only real browser dogfood proves closure.**
- Do not use CLI, API calls, manual `.ariadne` JSON edits, fixtures, static snapshots, fake-codex, or docs as closure evidence.
- Do not run broad test sweeps as a substitute for product progress.
- Focused checks are allowed only as local guardrails after the browser path exposes a concrete implementation blocker.
- `fake-codex` is allowed only for offline implementation checks. It is never dogfood evidence.
- `--blocked-ok` style flows are blocker rehearsals only. They are never closure.
- A blocker is not an endpoint unless it is an external-state blocker the agent cannot resolve: missing login, quota exhaustion, unavailable Codex/Claude CLI, missing human authorization, or locked target repo access.
- Product/code blockers must be fixed immediately in the same execution loop. Recording them is not enough.
- Do not stop because a harness exists, `--blocked-ok` succeeded, docs were updated, a focused check passed, a branch was pushed, or a blocker was recorded.
- Real closure requires `CodexBackend` or `ClaudeCodeBackend` to run from Workbench-triggered execution against `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`.
- If real Codex/Claude cannot run because login, quota, command, env gate, or configuration is missing, record `BLOCKED_NOT_CLOSED` and treat the task as paused, not done.
- The target project must move toward runnable v0.1. Ariadne improving itself is not sufficient.

## Execution Loop: Blocker Repair Is Mandatory

This plan is not a checklist where each phase can be closed independently. It is a dogfood loop.

Every implementation pass must follow this loop:

```text
run browser dogfood
  -> if real closure succeeds: record real_closed and stop
  -> if blocker appears:
       classify blocker
       if product/code/harness blocker:
         fix it immediately
         rerun the same browser dogfood
       if external-state blocker:
         record BLOCKED_NOT_CLOSED with exact evidence
         stop only because user action or external state is required
```

Blocker classification:

- **Harness blocker:** selector, timing, browser dependency, stale test assumption. Fix the harness and rerun.
- **Product UX blocker:** user cannot recover, raw JSON, ambiguous state, missing next action, wrong page state. Fix the product and rerun.
- **Backend/state blocker:** stale preview, wrong assignment, old daemon claim, missing dispatch binding, evidence projection gap. Fix backend/state and rerun.
- **Agent quality blocker:** source understanding, issue factory, handoff, review, or memory content is too weak for Codex/Claude. Fix the responsible agent layer and rerun.
- **External-state blocker:** Codex/Claude login, quota, command unavailable, OS permission, target repo unavailable, explicit human authorization. Record `BLOCKED_NOT_CLOSED`; do not claim closure.

Forbidden stopping points:

- `scripts/verify_dogfood_browser.sh --blocked-ok` exits 0.
- The harness reaches evidence inspection but not real execution.
- The branch is committed or pushed.
- The stale preview or any single blocker is fixed.
- Unit tests, build, lint, doctor, or API checks pass.
- A result document says `BLOCKED_NOT_CLOSED`.

The next step after any non-external blocker is always: fix, rerun, advance.

## Single Acceptance Chain

```text
Browser Workbench
  -> create/select target project folder
  -> set project goal and target version
  -> add external sources
  -> source understanding produces evidence
  -> issue factory creates target-project issue set
  -> user applies issue delta
  -> user opens current issue
  -> user assigns Codex or Claude
  -> user authorizes local runtime
  -> daemon claims only this assignment
  -> Codex/Claude runs against target repo
  -> Workbench shows handoff, execution proof, diff, target test output, review, memory, next issue
  -> Workbench shows target version progress
```

No other path counts.

## Target Dogfood Case

- Target project: `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`
- Product goal: `Build Mini Code Agent v0.1`
- Issue prefix: `MCA`
- Runtime backends: `codex` or `claude-code`
- External sources:
  - `https://minimal-agent.com/`
  - `https://github.com/SWE-agent/mini-SWE-agent`
  - `https://github.com/LiuMengxuan04/MiniCode`
- Target verification commands must be run by the runtime path and surfaced in Workbench, not manually used as closure proof:
  - `python3.11 -m mini_code_agent --help`
  - `python3.11 -m mini_code_agent run "inspect this project and summarize next steps"`
  - configured target test command for the target repo

## Minimal State Spine

Do not start with a full project-management schema. Use the smallest state spine that closes the current dogfood path:

```text
ProjectVersionProgress
AssignmentDispatch
RuntimeAuthorization
RuntimeExecutionProof
ResultEvidenceProjection
```

Avoid adding full `ProjectVersion`, `VersionIssueSet`, `VersionProgressEvent`, and persistent `ResultEvidenceBundle` as independent fact sources until the browser path proves they are needed.

```text
Source artifacts
       |
       v
Issue preview -> applied tickets
       |
       v
Current issue -> AssignmentDispatch -> RuntimeAuthorization
       |                |                    |
       v                v                    v
Handoff packet -> Daemon claim -> Codex/Claude run
       |
       v
RuntimeExecutionProof -> ResultEvidenceProjection -> ProjectVersionProgress
```

## Required Proof Objects

### AssignmentDispatch

Purpose: bind "run this issue" to one target repo and one backend.

Fields:

- `dispatch_id`
- `ticket_id`
- `ticket_key`
- `assignment_id`
- `target_project_id`
- `target_repo_path`
- `expected_git_head`
- `backend_name`
- `route_decision_id`
- `handoff_packet_id`
- `handoff_hash`
- `runtime_authorization_id`
- `status`
- `failure_reason`

### RuntimeAuthorization

Purpose: make Workbench runtime authorization explicit and auditable.

Fields:

- `authorization_id`
- `backend_name`
- `target_project_id`
- `allowed_assignment_id`
- `external_execution_enabled`
- `command_available`
- `command_template_fingerprint`
- `status`
- `blocked_reason`
- `created_at`
- `expires_at`

### RuntimeExecutionProof

Purpose: prevent UI projection from faking real execution.

Fields:

- `proof_id`
- `execution_kind`: `real_cli | fake | dry_run | blocked | offline_fallback`
- `dispatch_id`
- `assignment_id`
- `runtime_authorization_id`
- `backend_name`
- `command_argv`
- `command_cwd`
- `cli_version`
- `process_or_session_id`
- `started_at`
- `completed_at`
- `exit_code`
- `stdout_hash`
- `stderr_hash`
- `transcript_hash`
- `git_head_before`
- `git_head_after`
- `changed_files`
- `target_test_command`
- `target_test_exit_code`

### ResultEvidenceProjection

Purpose: show current evidence without creating a second source of truth too early.

It should project from existing execution result, artifacts, review, memory, next issue, and runtime proof. Persist only after the projection has proven stable through browser dogfood.

### ProjectVersionProgress

Purpose: answer the user's real question: "Is this target project moving toward v0.1?"

Fields:

- `target_project_id`
- `target_version`
- `status`: `draft | sources_ready | issues_ready | assigned | running | blocked | real_closed`
- `current_issue_key`
- `completed_issue_keys`
- `blocked_issue_keys`
- `evidence_ids`
- `last_blocker`
- `last_real_execution_proof_id`

---

## Phase 1: Build the Failing Browser Dogfood Harness First

**Purpose:** Force the real product path to fail loudly before more architecture is added.

**Files:**

- Add: `frontend/ariadne-workbench/e2e/mini-code-agent-dogfood.spec.ts`
- Add: `scripts/verify_dogfood_browser.sh`
- Add: `docs/dogfood/results/2026-06-20-project-version-dogfood-result.md`
- Modify only if needed: `frontend/ariadne-workbench/package.json`

**Steps:**

- [x] Add a browser harness that opens the real Workbench, not a fixture page.
- [x] The harness may start the Workbench server, but after startup it may mutate Ariadne only through browser UI events.
- [x] Forbid `page.request`, direct API calls, CLI state mutation, and manual `.ariadne` edits inside the product path.
- [x] Make the harness record the first blocker with:
  - browser step name;
  - visible page state;
  - screenshot or trace path;
  - server log path;
  - whether Workbench is connected or in snapshot/offline mode.
- [x] Use the harness to walk:
  - create/select target project;
  - set goal and version;
  - add three sources;
  - generate issue preview;
  - apply issue delta;
  - open `MCA-001`;
  - assign Codex or Claude;
  - authorize runtime;
  - run current assignment;
  - inspect evidence and version progress.

**Acceptance for this phase:**

Phase 1 is complete only as a tooling milestone when the harness can produce a concrete browser-path blocker or a real execution result. It is not a valid endpoint for the overall task.

After Phase 1 produces a blocker, the worker must immediately enter the **Execution Loop: Blocker Repair Is Mandatory** above. A blocker is acceptable only as input to the next fix, not as final delivery. A passing unit test is irrelevant.

**Do not do:**

- Do not add broad test suites.
- Do not call `ari ticket run`.
- Do not seed `.ariadne` manually.
- Do not use `fake-codex` as success.

---

## Phase 2: Fix Project, Source, and Issue Set Flow

**Purpose:** Make the user input side real enough that Codex/Claude gets a meaningful issue.

**Files likely involved:**

- `frontend/ariadne-workbench/src/App.tsx`
- `frontend/ariadne-workbench/src/features/project-inputs/model.ts`
- `frontend/ariadne-workbench/src/shared/api/client.ts`
- `frontend/ariadne-workbench/src/shared/api/types.ts`
- `ariadne_ltb/interfaces/http/routes.py`
- `ariadne_ltb/application/target_project_registry.py`
- `ariadne_ltb/application/web_sources.py`
- `ariadne_ltb/application/source_analysis.py`
- `ariadne_ltb/application/source_understanding.py`
- `ariadne_ltb/application/repository_scanner.py`
- `ariadne_ltb/application/issue_factory.py`
- `ariadne_ltb/application/issue_compiler.py`

**Steps:**

- [ ] Project setup page must support path, create folder, init git, issue prefix, target version, and target test command.
- [ ] After adding a source, the page must show where it went and what state it is in: saved, fetched/linked, analyzed, artifacts, evidence, task impact.
- [ ] GitHub repo sources must show repository understanding, not a generic text note.
- [ ] Each source artifact must expose evidence, applicability, reuse boundary, and target relevance.
- [ ] Issue preview must show why each proposed issue exists and which source artifact/evidence produced it.
- [ ] Applying issue delta must create target-project issues such as `MCA-001`, with evidence attached.
- [ ] A generated issue without evidence must not be allowed into Ready to Run.
- [ ] If deterministic templates are used, Workbench must say so. Do not hide templates as agent intelligence.
- [ ] If DeepSeek is used, Workbench must show `deepseek_live` and evidence id. If fallback is used, Workbench must show the fallback reason.

**Browser acceptance:**

In Workbench, a user can paste the three dogfood sources, click through source understanding, generate `MCA-*` issues, apply them, and see evidence-backed issue reasons without touching CLI or API.

---

## Phase 3: Bind Current Issue to Current Runtime

**Purpose:** Ensure the user can run exactly the current issue, not an old assignment or wrong repo.

**Files likely involved:**

- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/application/assign_ticket.py`
- `ariadne_ltb/application/assignment_readiness.py`
- `ariadne_ltb/application/run_assignment.py`
- `ariadne_ltb/application/daemon_control.py`
- `ariadne_ltb/daemon.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/interfaces/http/routes.py`
- `frontend/ariadne-workbench/src/features/agent-control/model.ts`
- `frontend/ariadne-workbench/src/features/run-assignment/model.ts`
- `frontend/ariadne-workbench/src/features/run-assignment/api.ts`
- `frontend/ariadne-workbench/src/App.tsx`

**Steps:**

- [ ] Add minimal `AssignmentDispatch`.
- [ ] Add minimal `RuntimeAuthorization`.
- [ ] Workbench "run current issue" must create a dispatch bound to:
  - current issue;
  - current assignment;
  - current target project;
  - current target repo git head;
  - current handoff packet;
  - current backend;
  - current runtime authorization.
- [ ] Daemon claim for Workbench run must claim by dispatch id, not by scanning old ready assignments.
- [ ] Existing ready assignments without dispatch are legacy CLI-only and must not be claimed by Workbench runtime.
- [ ] If target repo head changed after dispatch, block with `stale_target_head` and show a refresh/retry action.
- [ ] Runtime authorization must be persisted. In-memory daemon state is not enough.
- [ ] Authorization must recheck command availability, env gate, template fingerprint, and target project at claim time.
- [ ] Workbench must visibly show:
  - assigned backend;
  - runtime authorization status;
  - dispatch id;
  - handoff hash;
  - claim status;
  - exact blocker if blocked.

**Browser acceptance:**

From `MCA-001`, the user can assign Codex or Claude, authorize runtime, run current assignment, and see either:

- current dispatch claimed by daemon; or
- exact blocker on that dispatch.

No old assignment may run.

---

## Phase 4: Capture Real Execution Proof and Evidence

**Purpose:** Show that Codex/Claude really ran against the target repo, or show exactly why it did not.

**Files likely involved:**

- `ariadne_ltb/execution.py`
- `ariadne_ltb/orchestrator.py`
- `ariadne_ltb/application/evidence_projection.py`
- `ariadne_ltb/application/workbench_projection.py`
- `ariadne_ltb/application/dtos.py`
- `ariadne_ltb/application/mappers.py`
- `frontend/ariadne-workbench/src/App.tsx`
- `frontend/ariadne-workbench/src/types.ts`

**Steps:**

- [ ] Add minimal `RuntimeExecutionProof`.
- [ ] CodexBackend and ClaudeCodeBackend must emit proof when they invoke the real CLI.
- [ ] Blocked, fake, dry-run, and offline fallback records must be labeled and rejected as real closure.
- [ ] Evidence projection must show:
  - execution kind;
  - backend;
  - command cwd;
  - command template fingerprint;
  - handoff file/hash;
  - git head before/after;
  - changed files;
  - diff path or no-diff blocker;
  - target test command/output;
  - review verdict;
  - memory record;
  - next issue suggestion.
- [ ] Real success requires the target repo to change or produce an explicit no-op proof accepted by reviewer. For this dogfood, prefer real code change.
- [ ] Workbench version panel must show whether Mini Code Agent v0.1 is draft, running, blocked, or real-closed.

**Browser acceptance:**

After running `MCA-001`, Workbench shows either a real Codex/Claude execution proof with target repo evidence, or a precise blocker such as command missing, login missing, quota, env gate, stale target head, handoff not ready, tests failed, or no diff.

---

## Phase 5: Strengthen Agent Quality Only Where Dogfood Proves It Is Weak

**Purpose:** Improve agent intelligence only after the browser path can carry the state.

**Files likely involved:**

- `ariadne_ltb/application/source_analysis.py`
- `ariadne_ltb/application/source_understanding.py`
- `ariadne_ltb/application/repository_scanner.py`
- `ariadne_ltb/application/issue_compiler.py`
- `ariadne_ltb/application/issue_factory.py`
- `ariadne_ltb/llm_agents.py`
- `ariadne_ltb/review.py`
- `ariadne_ltb/memory.py`
- `ariadne_ltb/application/handoff_packets.py`

**Steps:**

- [ ] Remove hidden mini-code-agent hardcoding from issue success criteria.
- [ ] If a deterministic template remains, label it as `deterministic_template` and show trigger evidence.
- [ ] Add source artifact fields needed by the handoff:
  - claims;
  - applicability;
  - avoid-copying boundary;
  - target relevance;
  - architecture patterns;
  - implementation constraints.
- [ ] Improve repo understanding so GitHub repos produce docs evidence, code evidence, architecture evidence, test evidence, and reuse-boundary evidence.
- [ ] Handoff must include source evidence, allowed paths, target repo context, acceptance criteria, test command, and forbidden actions.
- [ ] Reviewer must grade each acceptance criterion as `met`, `failed`, or `unproven`.
- [ ] Memory must record version-level lesson and next issue implication.

**Browser acceptance:**

`MCA-001` and at least one follow-up issue show evidence-backed issue reason, source understanding strategy, handoff quality, review coverage, and memory in Workbench.

---

## Phase 6: Run Real Dogfood and Record Closure Evidence

**Purpose:** Produce the one result that matters.

**Files:**

- Modify: `docs/dogfood/results/2026-06-20-project-version-dogfood-result.md`
- Modify: `docs/development_report.md`
- Modify only if user-facing instructions changed: `README.md`

**Steps:**

- [ ] Start Workbench.
- [ ] Use browser only for product actions.
- [ ] Run the dogfood path against `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`.
- [ ] If a blocker occurs, classify it. Product/code/harness/backend/agent blockers must be fixed and rerun immediately. Only external-state blockers may be recorded as `BLOCKED_NOT_CLOSED`.
- [ ] If an external-state blocker occurs, record `BLOCKED_NOT_CLOSED` with browser step, visible state, dispatch id, authorization id, and blocker reason.
- [ ] If real Codex/Claude runs, record:
  - source ids and artifacts;
  - issue keys;
  - selected issue;
  - assignment id;
  - dispatch id;
  - runtime authorization id;
  - handoff packet/hash;
  - runtime execution proof id;
  - backend;
  - command cwd;
  - git head before/after;
  - changed files;
  - target test output;
  - review verdict and criterion coverage;
  - memory path;
  - next issue path;
  - Workbench screenshot or trace path;
  - target version status.

**Real closure command:**

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
```

This command is acceptable because it drives the browser path. It must not use API shortcuts or CLI state mutation after Workbench startup.

**Blocked rehearsal command:**

```bash
scripts/verify_dogfood_browser.sh --blocked-ok
```

This command can prove blocked UX, but it cannot close the task.

---

## Rollout Order

1. Phase 1: build failing browser dogfood harness.
2. Run the harness. Classify the first blocker.
3. Fix the blocker in the owning layer and rerun the same browser dogfood.
4. Repeat fix/rerun until the harness reaches `MCA-001`, then daemon claim, then real execution, then evidence projection.
5. Improve source/issue/handoff/review/memory quality only where the harness exposes weakness.
6. Run real dogfood and record closure evidence.

Do not advance by calendar phase if the previous browser blocker remains unresolved. Phase labels are for ownership, not stopping points.

## Definition of Done

This plan is complete only when the browser dogfood path records `real_closed`.

`BLOCKED_NOT_CLOSED` is not done. It is a paused state allowed only for external-state blockers that require user action or external system recovery.

`real_closed` requires:

- browser-created target project, goal, sources, issue set, assignment, dispatch, and runtime authorization;
- real Codex or Claude backend;
- `execution_kind=real_cli`;
- runtime execution proof tied to the current dispatch;
- target repo evidence under `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`;
- Workbench-visible diff or explicit accepted no-op proof;
- target test output surfaced in Workbench;
- review criterion coverage;
- memory and next issue;
- target version progress visible in Workbench.

`BLOCKED_NOT_CLOSED` requires:

- browser evidence of where the path blocked;
- exact blocker reason;
- no claim that dogfood is closed.
- explanation of why the blocker is external-state and cannot be fixed by the agent;
- exact user or external action needed before the next run.

## Explicit Non-Success Conditions

Do not mark this plan done if any of these are true:

- completion happened through CLI/API instead of browser;
- `fake-codex` produced the success;
- broad tests or doctor commands were used as closure evidence;
- source understanding produced issues without evidence;
- current issue was not bound to current dispatch/runtime;
- daemon ran an old assignment;
- Workbench showed events but not execution proof;
- target project did not change and no explicit accepted no-op proof exists;
- Ariadne release evidence was used instead of target project version evidence.
