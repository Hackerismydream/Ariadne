# Project Version Dogfood Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Ariadne prove its real product promise through one browser-only dogfood loop: project goal + external inputs -> typed understanding -> issue set -> Codex/Claude assignment -> runtime execution -> diff/tests/review/memory/next issues -> visible target-version progress.

**Architecture:** Keep Ariadne local-first, single-user, Python/FastAPI/React, JSON/JSONL, and ticket-centered. Add the missing Project Version Delivery spine: `ProjectVersion`, `VersionIssueSet`, `AssignmentDispatch`, `RuntimeAuthorization`, and `ResultEvidenceBundle`. The Workbench becomes the acceptance surface; CLI/API tests remain support tools, not product proof.

**Tech Stack:** Python 3.11+, Pydantic v2, FastAPI, Typer, local git subprocess, Codex/Claude CLI adapters, JSON persistence, React/Vite Workbench, Playwright browser dogfood, pytest, ruff.

---

## Cross-Review Corrections

This plan was reviewed by independent subagents from product, backend architecture, and real-execution perspectives. The original direction was accepted, but three corrections are mandatory:

1. **Do not do one giant rewrite.** Implement a compatibility-first control-plane spine first, then the browser journey and semantic agent upgrades.
2. **Do not trust UI projection as execution proof.** Real closure requires a `RuntimeExecutionProof` correlated to the current dispatch and emitted by the real Codex/Claude adapter.
3. **Do not let blocked evidence count as closure.** Blocked-path acceptance is useful, but the final status is `blocked-verified`, not `real-closed`, unless real Codex/Claude execution changes or explicitly validates the target project.

## Why This Plan Exists

Ariadne has many real pieces now, but dogfood still fails because each slice was accepted independently. The product must stop accepting "API exists", "page renders", "assignment created", or "tests pass" as dogfood completion.

The only dogfood success condition is:

```text
User uses Workbench in a browser
  -> creates/selects target project and version goal
  -> adds external sources
  -> sees source understanding and evidence
  -> generates and applies target-project issues
  -> assigns one issue to Codex or Claude
  -> authorizes local runtime once
  -> current assignment is claimed and executed
  -> Workbench shows handoff, execution, diff, tests, review, memory, next issues
  -> target project is visibly closer to v0.1
```

## Subagent Review Inputs Absorbed

Four read-only subagents reviewed the current Ariadne state before this plan:

1. **Product chain review:** Workbench still lacks browser-only dogfood acceptance, target-version progress, complete project setup UI, full source type coverage, honest issue-generation provenance, and inbox recovery loop.
2. **Backend architecture review:** The ticket pipeline exists, but Ariadne lacks first-class `ProjectVersion`, `VersionIssueSet`, `AssignmentDispatch`, and `ResultEvidenceBundle`; readiness and claim are still too metadata-driven.
3. **Agent capability review:** The artifact/state pipeline is real, but legacy role agents are scaffold-like; DeepSeek roles exist but are not yet decisive state-transition agents. LLM must handle semantic source understanding, issue decomposition, and review.
4. **Execution review:** Workbench execution is not self-contained because runtime authorization is in-memory, `confirm_execution` is split from env gates, run dispatch can race with daemon claim, and evidence projection is too thin.

## Non-Negotiable Acceptance

- Product acceptance is browser-only through the Workbench.
- API/CLI/manual JSON can be used for setup, tests, and debugging only.
- `fake-codex` is valid only for CI-safe fallback and blocked-path tests.
- A blocked real runtime is acceptable only if Workbench clearly shows the blocker and recovery action.
- Real success cannot be claimed unless Codex or Claude actually runs and Workbench records non-fake execution evidence.
- The target project is `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`, not the Ariadne repo.
- Closed-loop success requires a `RuntimeExecutionProof` emitted by the real Codex/Claude adapter, correlated to the current `AssignmentDispatch`, with command argv, cwd, CLI version, process/session id, transcript/log hashes, start/end time, exit code, and target repo git head before/after. UI projection alone is not execution evidence.
- If real Codex/Claude execution cannot run, the final status must be `blocked-verified`, not `real-closed`.

## Implementation Strategy

Do this in two phases.

**Phase A: Compatibility-first control-plane spine**

1. Add minimal Project Version projection and backfill.
2. Add persistent runtime authorization as the single Workbench execution authority.
3. Add assignment dispatch binding and daemon claim scoping.
4. Add projection-first result evidence bundle and runtime execution proof.
5. Add backend doctor checks for orphaned versions, dispatches, bundles, and authorizations.

Do not start Phase B until Phase A passes migration, legacy CLI, race, and fake/dry-run rejection tests.

**Phase B: Browser product journey and dogfood closure**

1. Make Workbench actions match the dogfood journey.
2. Strengthen agent capability boundaries.
3. Add browser-only dogfood harness.
4. Run blocked-path and real-path dogfood and record honest evidence.

Do not try to solve general autonomous project building first. First make Mini Code Agent v0.1 close through the product path.

## Task 0: Define Closure Invariants

**Purpose:** Prevent future implementation from turning blocked, fake, dry-run, or stale evidence into product success.

**Files:**

- Modify: `docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md`
- Modify: `docs/ops/V1_RELEASE_CHECKLIST.md`
- Modify: `docs/development_report.md`
- Add: `tests/test_dogfood_closure_invariants.py`

**Invariants:**

- `blocked-verified`: Workbench proves the product state machine can carry a blocker through source, issue, assignment, runtime, evidence, inbox, and version progress. This is not product closure.
- `real-closed`: Workbench proves real Codex/Claude execution occurred for the current assignment and produced target-project evidence.
- Real closure requires:
  - `execution_kind=real_cli`;
  - `RuntimeExecutionProof` created after current dispatch;
  - target repo cwd equals `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`;
  - command argv and command template fingerprint recorded;
  - git head before/after recorded;
  - changed files scoped to target project;
  - runtime-run test command output recorded;
  - reviewer criteria coverage recorded as `met | failed | unproven`;
  - Workbench-visible evidence ids match stored ids.

**Steps:**

- [ ] Add docs language that blocked-path acceptance cannot be described as closure.
- [ ] Add tests that reject fake/dry-run/static/snapshot evidence as dogfood success.
- [ ] Add tests that reject target-version pass when evidence comes from Ariadne release evidence instead of `ProjectVersion` and `ResultEvidenceBundle`.
- [ ] Add tests that require real closure to include runtime proof and target repo progress evidence.

**Verification:**

```bash
python3.11 -m pytest tests/test_dogfood_closure_invariants.py -q
```

---

## Task 1: Add Project Version Delivery Models

**Purpose:** Give Ariadne a first-class object that answers "is this target project version actually being delivered?"

**Files:**

- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/mappers.py`
- Modify: `ariadne_ltb/application/workbench_projection.py`
- Add: `tests/test_project_version_state_machine.py`
- Add: `tests/test_issue_set_version_binding.py`

**Model additions:**

- `ProjectVersion`
  - `id`
  - `target_project_id`
  - `goal_id`
  - `name`
  - `target_version`
  - `status`: `draft | sources_ready | issues_ready | running | blocked | passed | failed`
  - `issue_set_id`
  - `test_command`
  - `verification_commands`
  - `created_at`
  - `updated_at`

- `VersionIssueSet`
  - `id`
  - `project_version_id`
  - `build_context_id`
  - `preview_id`
  - `ticket_ids`
  - `issue_keys`
  - `source_document_ids`
  - `source_artifact_ids`
  - `evidence_refs`
  - `fingerprint`
  - `created_at`

- `VersionProgressEvent`
  - `id`
  - `project_version_id`
  - `ticket_id`
  - `assignment_id`
  - `event_type`
  - `message`
  - `severity`
  - `artifact_refs`
  - `created_at`

**Steps:**

- [ ] Add the three Pydantic models and enums in `ariadne_ltb/models.py`.
- [ ] Add `save_project_version`, `load_project_version`, `list_project_versions`, `save_version_issue_set`, `load_version_issue_set`, `append_version_progress_event`, and `list_version_progress_events` to `AriadneStore`.
- [ ] Store files under `.ariadne/project_versions/`, `.ariadne/version_issue_sets/`, and `.ariadne/version_progress/`.
- [ ] Add DTOs and mappers so `/api/workbench` can expose `project_versions`, current version, issue set, and version progress.
- [ ] Update `IssueFactoryService.apply` so applied issue deltas create or update a `VersionIssueSet` when `target_project_id` and `goal_id` exist.
- [ ] Backfill current `ProjectVersion` projection from existing `ProjectGoal.target_project_id`, `ProjectResource` metadata, and applied `BacklogPreview` when explicit version records are missing.
- [ ] Old stores with no `.ariadne/project_versions/`, `.ariadne/version_issue_sets/`, or `.ariadne/version_progress/` must load without mutation and return empty arrays rather than 500.
- [ ] Test that a backlog preview applied for Mini Code Agent creates a version issue set with `MCA-*` tickets and source evidence refs.
- [ ] Test that version progress transitions from `draft` to `issues_ready` after issue-set apply.

**Verification:**

```bash
python3.11 -m pytest tests/test_project_version_state_machine.py tests/test_issue_set_version_binding.py -q
ruff check ariadne_ltb/models.py ariadne_ltb/storage.py ariadne_ltb/application/dtos.py ariadne_ltb/application/mappers.py
```

---

## Task 2: Add Persistent Runtime Authorization

**Purpose:** Replace in-memory confirmation with a local, auditable runtime authorization that the Workbench can show and the daemon can enforce.

**Files:**

- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Add: `ariadne_ltb/application/runtime_authorization.py`
- Modify: `ariadne_ltb/application/runtime_status.py`
- Modify: `ariadne_ltb/application/daemon_control.py`
- Modify: `ariadne_ltb/interfaces/http/routes.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/mappers.py`
- Add: `tests/test_runtime_authorization.py`
- Modify: `tests/test_real_backend_gates.py`
- Modify: `tests/test_frontend_api_contract_static.py`

**Model additions:**

- `RuntimeAuthorization`
  - `id`
  - `runtime_id`
  - `backend_name`
  - `target_project_id`
  - `allowed_assignment_id`
  - `external_execution_enabled`
  - `command_available`
  - `command_template_fingerprint`
  - `capability_snapshot_id`
  - `created_at`
  - `expires_at`
  - `revoked_at`
  - `status`: `active | expired | revoked | blocked`
  - `blocked_reason`

**API additions:**

- `POST /api/runtime/authorize`
- `POST /api/runtime/authorizations/{authorization_id}/revoke`
- `GET /api/runtime/authorizations`

**Steps:**

- [ ] Add `RuntimeAuthorization` model and JSON persistence.
- [ ] Implement `RuntimeAuthorizationService.authorize(payload)` that checks backend name, target project existence, Codex/Claude command availability, `ARIADNE_ENABLE_EXTERNAL_EXECUTION`, and command-template fingerprint.
- [ ] If the env gate or command is missing, persist a blocked authorization with exact reason; do not throw a generic 500.
- [ ] Make `RuntimeAuthorization` the single Workbench execution authority. `confirmation_token` may create or reference an authorization, but daemon/orchestrator must not trust `_DaemonLoopHandle.external_execution_authorized` for Workbench execution.
- [ ] Revalidate env gate, command availability, and command-template fingerprint at claim time and immediately before backend execution.
- [ ] Add HTTP routes and DTOs.
- [ ] Make `DaemonControlService.run_now` load authorization instead of relying only on in-memory daemon handle confirmation.
- [ ] Keep CLI `--confirm-execution` behavior intact for non-Workbench use.
- [ ] Add tests for active, blocked, expired, revoked, and scoped-to-current-assignment authorization.

**Verification:**

```bash
python3.11 -m pytest tests/test_runtime_authorization.py tests/test_real_backend_gates.py tests/test_frontend_api_contract_static.py -q
ruff check ariadne_ltb/application/runtime_authorization.py ariadne_ltb/application/daemon_control.py ariadne_ltb/interfaces/http/routes.py
```

---

## Task 3: Add Assignment Dispatch Binding

**Purpose:** Ensure the browser "run current issue" action cannot be stolen by an old assignment and cannot run against the wrong target repo/backend.

**Files:**

- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/application/run_assignment.py`
- Modify: `ariadne_ltb/application/assignment_readiness.py`
- Modify: `ariadne_ltb/application/assign_ticket.py`
- Modify: `ariadne_ltb/daemon.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Add: `tests/test_assignment_dispatch_binding.py`
- Add: `tests/test_daemon_dispatch_claim_scope.py`
- Modify: `tests/test_assignment_claim_state_machine.py`
- Modify: `tests/test_workbench_daemon_feedback.py`

**Model additions:**

- `AssignmentDispatch`
  - `id`
  - `assignment_id`
  - `ticket_id`
  - `ticket_key`
  - `target_project_id`
  - `target_repo_path`
  - `expected_git_head`
  - `backend_name`
  - `route_decision_id`
  - `handoff_packet_id`
  - `handoff_hash`
  - `runtime_authorization_id`
  - `status`: `created | claimable | claimed | running | blocked | completed | failed`
  - `created_at`
  - `claimed_at`
  - `completed_at`
  - `failure_reason`

**Steps:**

- [ ] Add `AssignmentDispatch` model and persistence under `.ariadne/assignment_dispatches/`.
- [ ] Change `RunAssignmentService.run` to create a dispatch record after validating:
  - assignment exists;
  - assignment ticket exists;
  - target project exists;
  - route decision exists;
  - handoff packet exists;
  - handoff hash matches;
  - runtime authorization exists and is active;
  - expected target repo git head is captured.
- [ ] Stop using run-time metadata synthesis to make assignments claimable.
- [ ] Add `AriadneStore.claim_assignment_dispatch(dispatch_id, runtime_id)` or equivalent helper so daemon claims the specific dispatch.
- [ ] Change `LocalDaemonWorker.run_once` so a browser `run-now` path claims `dispatch_id`, not only `assignment_id`.
- [ ] READY_TO_CLAIM assignments without dispatch are legacy CLI-only and must be skipped by Workbench runtime claim.
- [ ] If current target repo HEAD differs from `dispatch.expected_git_head`, block dispatch with `stale_target_head` and expose refresh-dispatch recovery in Workbench.
- [ ] Keep old `daemon run-once` behavior for CLI, but make it skip assignments whose dispatch scope does not match current runtime/backend.
- [ ] Pass frozen dispatch/handoff information into `TicketRunOrchestrator.run_ticket`.
- [ ] In dispatch path, orchestrator must not recompute critical execution inputs; it must verify and use the frozen route decision, permission profile, target repo, handoff packet, and runtime authorization.
- [ ] Add tests that old queued assignments are not claimed when the user runs a new current assignment.
- [ ] Add race tests for two daemons trying to claim the same dispatch.

**Verification:**

```bash
python3.11 -m pytest tests/test_assignment_dispatch_binding.py tests/test_daemon_dispatch_claim_scope.py tests/test_assignment_claim_state_machine.py tests/test_workbench_daemon_feedback.py -q
ruff check ariadne_ltb/application/run_assignment.py ariadne_ltb/daemon.py ariadne_ltb/orchestrator.py
```

---

## Task 4: Add Result Evidence Bundle and Runtime Execution Proof

**Purpose:** Make execution proof a first-class object instead of scattered projection from runs, comments, metadata, and artifacts.

**Files:**

- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Modify: `ariadne_ltb/application/evidence_projection.py`
- Modify: `ariadne_ltb/application/workbench_projection.py`
- Modify: `ariadne_ltb/application/dtos.py`
- Modify: `ariadne_ltb/application/mappers.py`
- Add: `tests/test_result_evidence_bundle.py`
- Add: `tests/test_runtime_execution_proof.py`
- Add: `tests/test_target_repo_progress_invariant.py`
- Modify: `tests/test_evidence_projection.py`
- Modify: `tests/test_release_evidence.py`

**Model additions:**

- `RuntimeExecutionProof`
  - `id`
  - `dispatch_id`
  - `assignment_id`
  - `runtime_authorization_id`
  - `backend_name`
  - `execution_kind`: `real_cli | fake | dry_run | blocked | offline_fallback`
  - `command_argv`
  - `command_cwd`
  - `cli_version`
  - `process_id_or_session_id`
  - `started_at`
  - `completed_at`
  - `exit_code`
  - `stdout_hash`
  - `stderr_hash`
  - `transcript_hash`
  - `command_template_fingerprint`
  - `git_head_before`
  - `git_head_after`
  - `target_repo_clean_before`
  - `target_repo_dirty_after`

- `ResultEvidenceBundle`
  - `id`
  - `project_version_id`
  - `ticket_id`
  - `ticket_key`
  - `assignment_id`
  - `dispatch_id`
  - `backend_name`
  - `runtime_authorization_id`
  - `runtime_execution_proof_id`
  - `execution_kind`
  - `handoff_packet_id`
  - `handoff_hash`
  - `execution_result_id`
  - `dry_run`
  - `blocked`
  - `failure_reason`
  - `exit_code`
  - `test_command`
  - `test_exit_code`
  - `changed_files`
  - `git_head_before`
  - `git_head_after`
  - `evidence_created_after_dispatch`
  - `git_diff_path`
  - `execution_log_path`
  - `review_report_path`
  - `memory_record_path`
  - `next_tickets_path`
  - `created_at`

**Steps:**

- [ ] First implement `ResultEvidenceBundle` as a stable projection over `ExecutionResult`, artifacts, review, memory, and next tickets.
- [ ] Persist the bundle only after projection tests prove idempotency and exception-before-execution paths are covered.
- [ ] Persist a runtime execution proof from real Codex/Claude adapters when a command is invoked.
- [ ] Fake, dry-run, blocked, and offline fallback paths may create proof-like records, but must set `execution_kind` accordingly and must be rejected as real closure.
- [ ] Persist a result evidence bundle after every orchestrator run, including blocked runs.
- [ ] Attach bundle id to assignment, ticket metadata, and version progress event.
- [ ] Expand `/api/evidence` and `/api/workbench` ticket evidence so the frontend can show exact real/fake/dry-run status.
- [ ] Make release/product evidence reject `fake-codex`, dry-run, and static snapshot as production success.
- [ ] Add target repo progress invariant: real success requires target repo git head/diff evidence, runtime-run tests, and acceptance review coverage.
- [ ] Add tests for passed execution, blocked real backend, failed tests, and evidence projection.

**Verification:**

```bash
python3.11 -m pytest tests/test_result_evidence_bundle.py tests/test_runtime_execution_proof.py tests/test_target_repo_progress_invariant.py tests/test_evidence_projection.py tests/test_release_evidence.py -q
ruff check ariadne_ltb/application/evidence_projection.py ariadne_ltb/application/workbench_projection.py
```

---

## Task 5: Make Workbench Match the Dogfood Journey

**Purpose:** Turn existing pages into a simple product flow: Project -> Sources -> Tasks -> Ready to Run -> Evidence -> Version.

**Files:**

- Modify: `frontend/ariadne-workbench/src/App.tsx`
- Modify: `frontend/ariadne-workbench/src/types.ts`
- Modify: `frontend/ariadne-workbench/src/shared/api/types.ts`
- Modify: `frontend/ariadne-workbench/src/shared/api/client.ts`
- Modify: `frontend/ariadne-workbench/src/features/project-inputs/model.ts`
- Modify: `frontend/ariadne-workbench/src/features/agent-control/model.ts`
- Modify: `frontend/ariadne-workbench/src/features/run-assignment/model.ts`
- Modify: `frontend/ariadne-workbench/src/features/run-assignment/api.ts`
- Modify: `frontend/ariadne-workbench/src/styles.css`
- Modify: `tests/test_project_inputs_static.py`
- Modify: `tests/test_frontend_control_plane_e2e.py`

**UI changes:**

- Project setup:
  - path;
  - create folder;
  - init git;
  - issue prefix;
  - target version;
  - test command;
  - path validity;
  - git status.

- Source input:
  - one primary input box: paste URL or path;
  - optional advanced type override;
  - primary action: `添加并分析`;
  - status timeline: saved -> fetched/linked -> analyzed -> artifacts -> evidence -> task impact.

- Tasks:
  - show preview id;
  - show evidence-backed reason for each issue;
  - show whether issue came from LLM synthesis, deterministic compiler, or explicit template;
  - stale preview should show recoverable action, not 500.

- Ready to Run:
  - show route decision;
  - handoff packet hash;
  - runtime capability;
  - authorization status;
  - dispatch status;
  - current assignment only.

- Evidence:
  - show result evidence bundle fields;
  - distinguish `real`, `blocked`, `dry-run`, `fake`, and `offline fallback`.

- Version:
  - show Mini Code Agent v0.1 progress;
  - show required target commands;
  - show pass/fail/blocked evidence;
  - show remaining issue set.

**Steps:**

- [ ] Add frontend types for project versions, authorizations, dispatches, and result evidence bundles.
- [ ] Add API client methods for runtime authorization and assignment dispatch.
- [ ] Split current agent-control flow into `authorizeRuntime`, `dispatchCurrentAssignment`, and `runCurrentAssignment`.
- [ ] Surface project setup fields that backend already supports: `test_command`, `issue_prefix`, `create_if_missing`, and `init_git`.
- [ ] Add source state timeline and make "where did it go?" visible after save/analyze.
- [ ] Add version progress panel.
- [ ] Add stale preview recovery UI for `stale_preview` instead of exposing raw JSON or generic server error.
- [ ] Update static frontend tests to enforce that product pages do not present fake/static/demo as default product success.

**Verification:**

```bash
python3.11 -m pytest tests/test_project_inputs_static.py tests/test_frontend_control_plane_e2e.py tests/test_frontend_api_contract_static.py -q
cd frontend/ariadne-workbench && npm run build
```

---

## Task 6: Strengthen Agent Capabilities at the State-Transition Boundaries

**Purpose:** Make agent roles produce decisive artifacts, not role-name theater.

**Files:**

- Modify: `ariadne_ltb/application/source_analysis.py`
- Modify: `ariadne_ltb/application/source_understanding.py`
- Modify: `ariadne_ltb/application/repository_scanner.py`
- Modify: `ariadne_ltb/application/issue_compiler.py`
- Modify: `ariadne_ltb/application/issue_factory.py`
- Modify: `ariadne_ltb/llm_agents.py`
- Modify: `ariadne_ltb/review.py`
- Modify: `ariadne_ltb/memory.py`
- Add: `tests/test_llm_source_understanding.py`
- Add: `tests/test_issue_factory_non_template.py`
- Add: `tests/test_semantic_review_acceptance.py`

**Steps:**

- [ ] Extend source artifacts with explicit `claims`, `applicability`, `avoid_copying`, `target_relevance`, `architecture_patterns`, and `implementation_constraints`.
- [ ] Make GitHub repo understanding distinguish docs evidence, code evidence, architecture evidence, test evidence, and reuse boundary evidence.
- [ ] Keep deterministic scanner for tests, but allow DeepSeek-assisted synthesis when key is present and user requests production source analysis.
- [ ] Record `source_understanding_strategy` as `deepseek_live | deterministic | fallback`.
- [ ] For production dogfood, each generated issue must show whether DeepSeek was called, the model/provider evidence id, and fallback reason if no live LLM was used.
- [ ] Deterministic fallback may pass blocked-path tests, but cannot be counted as semantic production source understanding.
- [ ] Replace mini-code-agent hidden hardcoding with an explicit artifact-derived issue compiler output. If deterministic templates are used, label them `compiler_strategy=deterministic_template` and show sources that triggered each issue.
- [ ] Add a non-mini-code fixture to prove Issue Factory is not only dogfood-shaped.
- [ ] Make reviewer produce acceptance criteria coverage: each criterion gets `met | failed | unproven`, evidence refs, and reviewer reason.
- [ ] Make memory write version-level lessons and next issue implications.

**Verification:**

```bash
python3.11 -m pytest tests/test_llm_source_understanding.py tests/test_issue_factory_non_template.py tests/test_semantic_review_acceptance.py tests/test_source_analysis.py tests/test_issue_factory_compiler.py -q
ruff check ariadne_ltb/application/source_analysis.py ariadne_ltb/application/issue_compiler.py ariadne_ltb/review.py ariadne_ltb/memory.py
```

---

## Task 7: Add Browser-Only Dogfood Harness

**Purpose:** Prevent future work from claiming dogfood success without using the actual product.

**Files:**

- Modify: `frontend/ariadne-workbench/package.json`
- Add: `frontend/ariadne-workbench/e2e/mini-code-agent-dogfood.spec.ts`
- Add: `scripts/verify_dogfood_browser.sh`
- Modify: `scripts/verify_v1.sh`
- Add: `docs/dogfood/results/2026-06-20-project-version-dogfood-result.md`

**Harness rules:**

- It may start the Ariadne Workbench server from shell.
- It may set env vars for real backend gates.
- It may not use `page.request` to call Ariadne product APIs.
- It may not edit `.ariadne` JSON directly.
- It may not use `fake-codex` for real success.
- It may record blocked-path evidence when Codex/Claude is unavailable.
- After server startup, it may not mutate Ariadne product state except through browser UI events.
- It must save Playwright trace, final screenshot, browser-visible evidence artifact paths, and server log path.
- It must fail if Workbench is in snapshot/offline mode.
- It must fail if version success is derived from Ariadne release evidence instead of `ProjectVersion` and `ResultEvidenceBundle`.
- The blocked path must assert version status is blocked, not passed.
- The real path must assert non-fake backend, real command fingerprint, dispatch id, authorization id, runtime execution proof id, git head before/after, and target-project verification command output.

**Browser steps:**

1. Open Workbench and assert connected mode.
2. Register `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`.
3. Create folder and initialize git from UI if missing.
4. Set goal `Build Mini Code Agent v0.1`.
5. Set target version `v0.1`.
6. Set issue prefix `MCA`.
7. Set test command `python3.11 -m pytest`.
8. Add and analyze:
   - `https://minimal-agent.com/`
   - `https://github.com/SWE-agent/mini-SWE-agent`
   - `https://github.com/LiuMengxuan04/MiniCode`
9. Generate task preview.
10. Apply issue delta.
11. Open `MCA-001`.
12. Assign to Codex or Claude.
13. Authorize runtime.
14. Dispatch and run current assignment.
15. Watch events until completed or blocked.
16. Assert Workbench shows handoff, execution result, diff or blocked reason, tests, review, memory, and next issues.
17. Assert Version panel shows target version status.

**Verification:**

```bash
cd frontend/ariadne-workbench && npm run build
scripts/verify_dogfood_browser.sh --blocked-ok
```

When Codex or Claude is locally available and env gates are configured:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
```

---

## Task 8: Run Real Dogfood and Record Evidence

**Purpose:** End with a truthful record of whether Ariadne has closed the loop.

**Files:**

- Modify: `docs/dogfood/results/2026-06-20-project-version-dogfood-result.md`
- Modify: `docs/development_report.md`
- Modify: `README.md`

**Steps:**

- [ ] Start Workbench from current branch.
- [ ] Use browser only for product actions.
- [ ] Run blocked-path dogfood first; record blockers and evidence as `blocked-verified`, not closure.
- [ ] Run the real Codex/Claude path. If Codex/Claude or gates are unavailable, record `BLOCKED_NOT_CLOSED`; do not mark dogfood closure complete.
- [ ] Verify target project commands:

```bash
cd /Users/martinlos/code/ariadne-dogfood/mini-code-agent
python3.11 -m mini_code_agent --help
python3.11 -m mini_code_agent run "inspect this project and summarize next steps"
python3.11 -m pytest
```

- [ ] Record exact result:
  - target project path;
  - project version id;
  - source ids/artifacts;
  - issue set id;
  - ticket key;
  - assignment id;
  - dispatch id;
  - runtime authorization id;
  - backend;
  - handoff packet;
  - execution result;
  - changed files;
  - test result;
  - review verdict;
  - memory path;
  - next tickets path;
  - browser evidence URL/screenshot if available.

**Verification:**

```bash
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
python3.11 -m ariadne_ltb.cli backend doctor
python3.11 -m ariadne_ltb.cli doctor store
python3.11 -m ariadne_ltb.cli doctor product --require-acceptance-ready
python3.11 -m ariadne_ltb.cli evidence packet --require-acceptance-ready
python3.11 -m ariadne_ltb.cli doctor project-version \
  --target-project /Users/martinlos/code/ariadne-dogfood/mini-code-agent \
  --target-version v0.1 \
  --require-browser-evidence \
  --require-result-evidence-bundle \
  --reject-fake \
  --reject-dry-run
```

---

## Rollout Order

1. Task 0: Closure invariants.
2. Task 1: Minimal ProjectVersion projection/backfill.
3. Task 2: RuntimeAuthorization as single Workbench execution authority.
4. Task 3: AssignmentDispatch claim and stale repo handling.
5. Task 4: Projection-first ResultEvidenceBundle and RuntimeExecutionProof.
6. Focused backend tests: migration, legacy CLI compatibility, race tests, fake/dry-run rejection.
7. Task 5: Workbench journey.
8. Task 7: Browser dogfood harness.
9. Task 6: Agent capability boundaries and issue compiler honesty.
10. Task 8: Real dogfood evidence.

Do not start semantic agent upgrades before Tasks 1-4 are stable. Stronger agents without a reliable version/run spine will produce more impressive but still non-closed output.

## Definition of Done

This plan is complete only when:

- Workbench can create/select target project and version.
- Sources produce visible typed artifacts and evidence.
- Issue Factory produces and applies a version-scoped issue set.
- Assignment has persisted route decision, handoff packet, dispatch, and runtime authorization.
- Daemon claims the current assignment only.
- Codex/Claude blocked path produces clear evidence when gates are missing.
- Real Codex/Claude path produces real execution evidence when gates are present.
- Workbench shows diff/tests/review/memory/next issues.
- Version panel shows target version progress.
- Browser-only dogfood evidence is recorded.
- Tests, ruff, frontend build, and product doctor are run.
- If real Codex/Claude path is unavailable, final status is `blocked-verified`, not `real-closed`.
- `real-closed` requires target project git head/diff evidence plus target project verification command output.
- Product doctor must reject stale Ariadne release evidence as a substitute for ProjectVersion evidence.
- `doctor project-version` must pass with `--require-browser-evidence`, `--require-result-evidence-bundle`, `--reject-fake`, and `--reject-dry-run`.

## Explicit Non-Success Conditions

Do not mark this plan done if any of these are true:

- Dogfood was completed with CLI instead of Workbench.
- Product success used `fake-codex`.
- Workbench showed assignment events but no result evidence bundle.
- Issue set was generated without source artifacts/evidence.
- Runtime executed a stale or wrong assignment.
- Target project did not change and no explicit blocked reason was recorded.
- Ariadne release evidence was used as a substitute for target project version evidence.
