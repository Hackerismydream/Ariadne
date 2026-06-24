# Ariadne Final 41 Grill List

Date: 2026-06-24

Workflow:
`/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/2026-06-24-final-judge-merge-workflow.md`

Inputs:

- `2026-06-24-multica-parity-final-grill-list.md`
- `2026-06-24-knowledge-orchestration-final-grill-list.md`

Mode: `grill-me` standard, real judge subagents, final merge.

## Execution Evidence

### Step 1 Normalize

Normalized 46 source candidates:

- 24 Multica parity candidates: `MP-001..MP-024`
- 22 knowledge orchestration candidates: `KO-001..KO-022`

### Step 2 Deduplicate With Independent Judge Subagents

Real subagents were used:

- Multica parity judge: `019ef987-e62a-7cf3-9fb5-1f42d7571ec6`
- Knowledge orchestration judge: `019ef988-0e9d-7923-b7ad-2aa7fa11001e`
- Dogfood closure judge: `019ef988-3aa0-7fd2-a6e9-a70527ad461b`
- Evidence quality judge: `019ef988-68c5-7a30-b7ee-881f772b69b1`

The judges independently identified the same high-confidence merges:

- `KO-006 + KO-020`: ProjectKnowledge / fallback provenance.
- `KO-008 + KO-015`: repo understanding depth and visible limitations.
- `KO-001 + KO-022 + MP-019`: current plan / exact next action.
- `KO-003 + KO-010 + KO-011 + MP-014 + MP-017`: evidence and handoff inspectability.
- `MP-015 + MP-024 + KO-002 + KO-017`: terminal verdict truth.
- `MP-016 + MP-018 + KO-016 + KO-017 + KO-018`: blocked/dirty feedback poisoning.

### Step 3 Score With Independent Judge Subagents

Scoring dimensions:

```text
severity
dogfood blocker
Multica parity relevance
knowledge-layer relevance
verifiability
implementation leverage
```

Strongest consensus P0 clusters:

- real browser dogfood closure is not proven;
- current work and current issue set have no single truth;
- execution/blocker verdicts contradict downstream artifacts;
- evidence exists but is hidden, unreadable, or semantically invalid;
- issue generation and handoff can proceed without target codebase or executable fields.

### Step 4 Select Exactly 41 Issues

Final selection:

- 15 lower-layer Multica parity issues.
- 15 upper-layer knowledge orchestration issues.
- 11 cross-layer closure issues.

Cut or merged out as standalone:

- `MP-020`: board mutation before task truth exists.
- `MP-023`: inert sidebar controls are lower-leverage polish.
- `KO-015`: merged into `KO-008`.
- `KO-020`: merged into `KO-006`.
- `KO-021`: issue prefix clarity is useful but lower priority.

### Step 5 Assign Priority

Priority rules:

- P0: blocks real browser dogfood closure.
- P1: blocks Multica-grade maturity but not the first closure path.
- P2: quality/polish after closure.

Self-check:

- Normalize both input lists: yes.
- Run independent judge subagents for deduplication: yes.
- Run independent judge subagents for scoring: yes.
- Select exactly 41 issues: yes.
- Record rejected / merged candidates: yes.
- Every final issue has evidence and verification method: yes.

## Executive Summary

Ariadne's current failure is not one missing button. It is a broken product
state machine.

The lower layer does not yet feel like Multica because assignment, daemon,
runtime, blocker, and run evidence are not reduced into one coherent task
snapshot and one issue-detail execution log.

The upper layer does not yet deliver Ariadne's promise because external sources,
ProjectKnowledge, target codebase state, issue deltas, and handoffs are not
traced as one auditable source-to-work chain.

The cross-layer failure is sharper: blocked or fake/partial execution can still
feed optimistic context, memory, next-ticket, and evidence surfaces. That makes
the Workbench look like a product shell rather than a trustworthy AI Builder
agent team.

## P0: Closure Blockers

## G-001: What single browser dogfood closure ledger proves target project version advancement?

- Priority: P0
- Source: KO-019 + dogfood judge missing cross-layer issue
- Product layer: Cross-layer
- Evidence: Current evidence proves product-visible blocked `M0TR-003`, not browser source input -> real Codex/Claude -> target repo diff/tests/review/memory/next issue -> version advancement.
- Why this matters: Without one closure ledger, Ariadne can keep shipping components without proving the promised AI Builder loop.
- Verification method: Browser-only dogfood must write a ledger linking target project, source ids, selected preview, applied issue set, assignment/run ids, diff/tests/review/memory/next issues, and target version status.
- First fix direction: Create a dogfood closure evidence object and make Workbench display it as the acceptance surface.

## G-002: What invariant proves the current issue set is selected, grounded, and distinct from repair/history previews?

- Priority: P0
- Source: KO-001 + KO-022 + MP-019
- Product layer: Cross-layer
- Evidence: `#plan-changes` selected `review_feedback` preview with `未命名任务`, while original source-generated `manual_goal` preview had grounded `M0TR` operations.
- Why this matters: If the current plan can silently switch to repair/history, users cannot trust what Ariadne will execute.
- Verification method: Plan Changes must show preview type, trigger, target project/version, current-mainline status, and exact next action object.
- First fix direction: Add a current-mainline issue-delta selector and separate mainline, repair, feedback, and history.

## G-003: Why does Current Version Context report readiness when Sources, Issues, and Runs contradict it?

- Priority: P0
- Source: KO-002 + MP-015 + MP-024
- Product layer: Cross-layer
- Evidence: Context strip reports ready/done/applied while `#sources` shows 61 sources with only 9 ready and issue/run evidence shows blocked execution.
- Why this matters: The top product state lies by omission, so users cannot know whether to add sources, review a delta, run an issue, or fix a blocker.
- Verification method: Compare Context Strip state with Sources, Issues, Runs, Inbox, and artifacts; contradictions must render as blocked/stale, not ready.
- First fix direction: Compute context from the same reducer used by current issue set, source artifacts, assignment state, and terminal evidence.

## G-004: What is Ariadne's local-first shared task snapshot across Issues, Team, Runs, Detail, and Context?

- Priority: P0
- Source: MP-001 + MP-002 + MP-021
- Product layer: Cross-layer
- Evidence: `/api/agent-task-snapshot` exposed one `active_assignment`, while daemon status was stopped/stale and other pages projected work differently.
- Why this matters: Multica feels coherent because task state is shared; Ariadne still lets each surface invent its own truth.
- Verification method: With queued, running, blocked, and completed assignments, every surface must show the same task snapshot and terminal state.
- First fix direction: Define a single local task snapshot reducer and make page projections consume it.

## G-005: Why can stale daemon heartbeat still drive active work state?

- Priority: P0
- Source: MP-002
- Product layer: Multica parity
- Evidence: Live daemon status showed `status=stopped`, `stale=true`, but still surfaced `current_assignment_id=assignment_5135cad3b8ca`.
- Why this matters: Users see stopped/stale work as active work, so the runtime feels uncontrolled.
- Verification method: Stop daemon after a terminal/blocking assignment; no page may show it as active without a non-terminal assignment state.
- First fix direction: Ignore stale daemon memory for active work and derive active state from assignment lifecycle.

## G-006: What invariant prevents duplicate runnable attempts for one issue/backend?

- Priority: P0
- Source: MP-003
- Product layer: Multica parity
- Evidence: `/api/runs/assignments` showed `M0TR-003` with one blocked Codex assignment and two additional `ready_to_claim` Codex assignments.
- Why this matters: Broad daemon start or issue-level rerun can claim the wrong attempt.
- Verification method: Assign/rerun the same issue multiple times; Workbench must show one current runnable attempt or explicit lineage.
- First fix direction: Enforce assignment uniqueness or explicit parent/attempt lineage at creation and claim time.

## G-007: Why is Issue Detail not a single execution fact center?

- Priority: P0
- Source: MP-004 + MP-005 + MP-006 + KO-004
- Product layer: Cross-layer
- Evidence: Issue Detail spreads assignments, execution results, progress, timeline, comments, handoff, route, diff, tests, and review across disconnected panels; API detail omits acceptance criteria and affected modules.
- Why this matters: The user must reconstruct "what happened and what to do next" manually.
- Verification method: Open an issue with multiple attempts and source-grounded metadata; one execution log should show active/past attempts, backend, evidence, acceptance, blocker, retry, diff/tests/review.
- First fix direction: Rebuild Issue Detail around a Multica-style execution log plus source/handoff facts.

## G-008: Can a user rerun the exact failed attempt they clicked?

- Priority: P0
- Source: MP-007
- Product layer: Multica parity
- Evidence: Issue Detail top-level rerun calls issue-level rerun; backend resolves latest assignment while live `M0TR-003` had multiple assignments.
- Why this matters: Recovery can target the wrong attempt and make the queue look haunted.
- Verification method: Create multiple attempts, click retry on a specific failed row, and verify the new assignment records parent assignment and source row.
- First fix direction: Add row-level retry actions keyed by assignment id.

## G-009: Can a blocked issue be recovered after browser refresh using persisted assignment state?

- Priority: P0
- Source: MP-008
- Product layer: Multica parity
- Evidence: `runCurrentIssue()` depends on a React `confirmationToken`; refresh loses the token while assignments persist.
- Why this matters: A local workbench cannot require the same browser session to recover agent work.
- Verification method: Assign issue, refresh, then rerun/recover through persisted assignment and visible gate state.
- First fix direction: Persist execution confirmation state or expose explicit gated recovery actions from the backend.

## G-010: Do all failure paths flow through one local failure pipeline?

- Priority: P0
- Source: MP-009 + MP-010 + MP-011 + MP-012
- Product layer: Cross-layer
- Evidence: Stale recovery, execution blocked, retry exhaustion, and inbox recovery create partially different states; `/api/inbox` showed three open `M0TR-003 / external_execution_blocked` items.
- Why this matters: One failure becomes multiple blockers or unsafe actions.
- Verification method: Trigger gate failure, test failure, stale daemon, manual cancel, retry exhaustion; each must produce one canonical blocker/retry/inbox/event path.
- First fix direction: Centralize failure classification, blocker identity, allowed actions, and retry policy.

## G-011: Why does Inbox expose generic actions instead of backend-approved actions?

- Priority: P0
- Source: MP-011
- Product layer: Multica parity
- Evidence: Backend computes allowed actions, but `InboxListItemDTO` omits them and UI renders Repair/Rerun/Acknowledge/Resolve for every item.
- Why this matters: Users can click actions that are semantically unsafe for the failure type.
- Verification method: Create each failure type and assert only backend-approved actions render.
- First fix direction: Include `allowed_actions` in Inbox DTO and render actions from policy.

## G-012: What blocks assignment when ticket title, evidence, acceptance criteria, allowed paths, or test command are missing?

- Priority: P0
- Source: KO-005 + MP-003 + MP-013
- Product layer: Cross-layer
- Evidence: `review_feedback` preview rendered `未命名任务` with 0 artifacts, evidence refs, acceptance criteria, and affected modules.
- Why this matters: Ariadne can feed vague work into Codex/Claude and create meaningless runs.
- Verification method: Attempt to assign a missing-field ticket; backend should block or downgrade to human triage with exact missing fields.
- First fix direction: Add executable-ticket validation before assignment/handoff.

## G-013: What exact scope does Start Daemon claim from?

- Priority: P0
- Source: MP-013
- Product layer: Multica parity
- Evidence: Runs page starts daemon with broad authorization while daemon status showed many open/claimable assignments.
- Why this matters: The user cannot be sure "run this issue" means this issue, backend, and target repo.
- Verification method: With multiple claimable assignments, starting daemon from one issue must claim only the scoped assignment/project/backend.
- First fix direction: Require daemon start scope or make broad daemon start explicit and dangerous.

## G-014: Can every displayed evidence ref be opened and semantically verified?

- Priority: P0
- Source: MP-014 + MP-017 + KO-003 + KO-010 + KO-011
- Product layer: Cross-layer
- Evidence: Issue Detail links artifacts as `#artifact:<path>` without a route; handoffs cite evidence IDs without readable source excerpts; list/detail evidence counts omit source grounding.
- Why this matters: Evidence that cannot be opened or understood is decorative.
- Verification method: Click source, diff, log, review, memory, next-ticket, and evidence refs; each must open readable content with validity status.
- First fix direction: Build an artifact/evidence viewer and categorize evidence by source, handoff, run, review, memory, next issue.

## G-015: What terminal verdict wins when execution, review, landing evidence, and issue projection disagree?

- Priority: P0
- Source: MP-015 + MP-024 + KO-002 + KO-017
- Product layer: Cross-layer
- Evidence: `/api/issues` reported `last_run_status=succeeded` while detail showed blocked execution, `external_execution_blocked`, `exit_code=2`, and blocked review.
- Why this matters: Users may believe a blocked run succeeded.
- Verification method: Blocked execution must dominate issue card, detail, board, timeline, evidence packet, memory, and next-ticket status until superseded by a successful run.
- First fix direction: Implement terminal verdict precedence as a shared reducer.

## G-016: Why does blocked execution feed memory/next tickets as if useful execution happened?

- Priority: P0
- Source: MP-016 + KO-017 + KO-018
- Product layer: Cross-layer
- Evidence: `next_tickets.json` claimed backend not blocked and tests passed while `execution_log.json` said blocked, empty diff, null tests.
- Why this matters: The feedback loop poisons itself with false premises.
- Verification method: After an external-execution gate failure, memory and next tickets must cite the blocker and must not claim code execution/tests/changes.
- First fix direction: Make memory/next-ticket generation consume normalized execution verdict and failure class.

## G-017: Are changed files run output or pre-existing dirty workspace state?

- Priority: P0
- Source: MP-018 + KO-016
- Product layer: Cross-layer
- Evidence: External execution was blocked before Codex ran; `git_status_before` and `git_status_after` were identical, yet changed files included pre-existing untracked target files.
- Why this matters: Ariadne may attribute old user work to the agent.
- Verification method: Run with dirty target repo; Workbench must separate preflight dirty state from backend-produced changes.
- First fix direction: Capture and expose preflight dirty state, per-run diff, and post-run delta separately.

## G-018: Why can target-project issues be generated while `codebase_snapshot_artifact_id` is null?

- Priority: P0
- Source: KO-009
- Product layer: Knowledge orchestration
- Evidence: `build_context_825e3a5124d7` had source/evidence ids but `codebase_snapshot_artifact_id=null`.
- Why this matters: Issue Factory may generate tasks that duplicate or ignore the real target repo state.
- Verification method: Generate target-project issues with and without codebase snapshot; missing snapshot must lower confidence, block, or force explicit warning.
- First fix direction: Make target codebase snapshot a first-class input to issue delta compilation.

## G-019: What proves ProjectKnowledge was used, and where is deterministic fallback disclosed?

- Priority: P0
- Source: KO-006 + KO-020 + MP-022
- Product layer: Cross-layer
- Evidence: `.ariadne/knowledge/resource_56a27abf28d0/` contained outcomes/blocker files but no source insights/themes for the current build context; deterministic fallback paths exist.
- Why this matters: Phase 8 cannot be judged if users cannot distinguish ProjectKnowledge graph output from templates/fallback.
- Verification method: Every issue delta should record compiler path, model/graph status, fallback reason, source insight/theme paths, and runtime mode.
- First fix direction: Add compiler provenance to backlog preview metadata and Plan Changes UI.

## G-020: Why can source artifacts persist raw HTML as knowledge?

- Priority: P0
- Source: KO-007
- Product layer: Knowledge orchestration
- Evidence: Several `knowledge_card` summaries begin with raw `<!doctype html>...`.
- Why this matters: Raw page boilerplate cannot ground issues or handoffs.
- Verification method: Analyze a web source with HTML boilerplate; artifact validation should reject or mark malformed extraction and show limitations.
- First fix direction: Add content extraction and source-artifact quality gates.

## P1: Multica-Grade Maturity Gaps

## G-021: Why is GitHub repo understanding mostly inventory instead of transferable architecture understanding?

- Priority: P1
- Source: KO-008 + KO-015
- Product layer: Knowledge orchestration
- Evidence: Repository understanding captures README/manifests/entrypoints/tests/selected files, but not module responsibility, loop architecture, tool protocol, or safety model.
- Why this matters: AI Builders use repos to reduce build friction, not just list files.
- Verification method: Add a repo source and inspect artifact for architecture map, reusable patterns, avoid notes, confidence, limits, and issue-decision links.
- First fix direction: Upgrade repo scanner from inventory to architecture understanding.

## G-022: Why is there no visible source claim -> issue decision -> acceptance criteria trace?

- Priority: P1
- Source: KO-010
- Product layer: Knowledge orchestration
- Evidence: Plan Changes and Issues show ids/counts, but not claim, locator, confidence, decision rationale, and criteria rationale.
- Why this matters: Users cannot audit why Ariadne created a ticket.
- Verification method: For each issue, show exact source claim, locator, confidence, theme/fallback, affected-module rationale, and criteria rationale.
- First fix direction: Add trace projection from SourceEvidence/ProjectKnowledge to Issue Delta and Issue Detail.

## G-023: Why do handoffs cite evidence IDs without readable excerpts and source claims?

- Priority: P1
- Source: KO-011
- Product layer: Knowledge orchestration
- Evidence: `M0TR-003` handoff includes evidence refs and allowed paths but no readable source excerpts.
- Why this matters: Codex/Claude should not reverse-engineer `.ariadne` state to understand a task.
- Verification method: Generated handoff must include source title, claim summary, locator, confidence, and short excerpt for every evidence ref.
- First fix direction: Render evidence excerpts into handoff packet generation.

## G-024: Why are synthetic task-derived sources visible beside real external inputs?

- Priority: P1
- Source: KO-012
- Product layer: Knowledge orchestration
- Evidence: Sources page includes task-like rows such as `Capture git diff and test result`; `issue_factory.py` can synthesize `SourceDocument` from task titles.
- Why this matters: Output leaking into input destroys source lineage.
- Verification method: Sources UI must distinguish user sources, derived artifacts, review feedback, execution feedback, and synthetic internal sources.
- First fix direction: Add source origin/type filters and stop presenting synthetic internal sources as external inputs.

## G-025: Why can a source lane show 61 sources without an operational queue for the other 52?

- Priority: P1
- Source: KO-013
- Product layer: Knowledge orchestration
- Evidence: `#sources` shows 61 sources, 9 ready, and broad queued messages.
- Why this matters: Users cannot tell whether to wait, re-analyze, delete, prioritize, or ignore pending sources.
- Verification method: Sources page groups queued/analyzing/blocked/analyzed/ignored/stale and shows one next action per source.
- First fix direction: Add source lifecycle projection and source-level actions.

## G-026: Why does source analysis usually create one broad evidence snippet per source?

- Priority: P1
- Source: KO-014
- Product layer: Knowledge orchestration
- Evidence: Current build context used 9 evidence ids across 9 source artifacts for 10 issues.
- Why this matters: Multi-issue decomposition needs multiple precise claims per meaningful source.
- Verification method: Analyze a non-trivial repo/blog and require multiple typed claims with locator/confidence.
- First fix direction: Emit claim-level evidence, not one broad artifact summary.

## G-027: Can Ariadne show active queued/dispatched/parked/running work, not just claimed/running assignments?

- Priority: P1
- Source: MP-005
- Product layer: Multica parity
- Evidence: Issue Detail `activeAssignment()` only accepts `claimed` and `running`; Runs uses daemon current assignment first.
- Why this matters: queued/dispatched work can disappear, while stale daemon memory can appear active.
- Verification method: Create queued, dispatched, claimed, running, blocked assignments and verify correct active/past buckets.
- First fix direction: Normalize assignment status mapping for execution log and Runs.

## G-028: Where are past runs collapsed and labeled as attempts?

- Priority: P1
- Source: MP-006
- Product layer: Multica parity
- Evidence: Issue Detail lists execution results and assignments separately without `Retry #N` or parent lineage.
- Why this matters: repeated attempts become noise and make recovery unclear.
- Verification method: Create retry attempts and verify parent linkage, retry number, timestamp, row-level evidence.
- First fix direction: Add attempt lineage fields to assignment DTO and execution log.

## G-029: Does every action produce a truthful durable state transition?

- Priority: P1
- Source: MP-012
- Product layer: Multica parity
- Evidence: `RunAssignmentService.run()` can append "run requested" comments/events for terminal assignments; frontend converts errors to transient messages.
- Why this matters: The timeline cannot be trusted if rejected/no-op actions look like dispatches.
- Verification method: Attempt unsafe rerun, stale daemon start, invalid inbox action; each must create durable rejected/no-op/blocked evidence or no event.
- First fix direction: Harden action services and event semantics.

## G-030: Can Team and Runs explain agent/backend presence from the same data Issue Detail uses?

- Priority: P1
- Source: MP-021
- Product layer: Multica parity
- Evidence: Team renders projected profiles/counts; Runs renders runtime/daemon state; Issue Detail renders assignments/results separately.
- Why this matters: "Codex blocked", "Codex idle", and "Codex active" must mean one thing.
- Verification method: With one running and one blocked attempt, Team/Runs/Issue Detail must show consistent workload and presence.
- First fix direction: Derive agent/backend presence from the shared task snapshot.

## G-031: Why is dry-run visible beside product Codex/Claude runtimes?

- Priority: P1
- Source: MP-022
- Product layer: Multica parity
- Evidence: `/api/runs/runtimes` includes `Dry-run fallback` beside CodexBackend and ClaudeCodeBackend.
- Why this matters: It risks fake/demo acceptance in the product control plane.
- Verification method: Product runtime list hides dry-run or marks it diagnostic-only and impossible as product acceptance evidence.
- First fix direction: Split product runtime profiles from diagnostic/offline fallback profiles.

## G-032: Can the Issue Board route users to concrete next action objects?

- Priority: P1
- Source: MP-019
- Product layer: Cross-layer
- Evidence: `IssueBoard.tsx` opens detail; blocked cards do not deep-link to blocker, execution evidence, assignment, or review section.
- Why this matters: The board remains a status museum instead of an operations surface.
- Verification method: Click blocked/running/review cards and land on exact relevant section/action.
- First fix direction: Add route anchors and next-action deep links.

## G-033: Why is Plan Changes still a preview browser rather than a reviewed issue-delta decision surface?

- Priority: P1
- Source: KO-022
- Product layer: Knowledge orchestration
- Evidence: Preview history contains `manual_goal`, `execution_result`, `codebase_observation`, `memory_gap`, and `review_feedback`; selected preview may be a repair-feedback preview with empty fields.
- Why this matters: A timeline of previews is not a decision surface for the current version.
- Verification method: Plan Changes separates current mainline delta, pending changes, repair suggestions, rejected/deferred work, and history.
- First fix direction: Rework Plan Changes projection around decision state, not latest preview.

## G-034: Why does issue detail projection hide source grounding even when persisted BuildTicket metadata contains it?

- Priority: P1
- Source: KO-003 + KO-004
- Product layer: Knowledge orchestration
- Evidence: `M0TR` tickets contain evidence refs, source artifact ids, source document ids, modules, and acceptance criteria; issue list/detail reports `0 evidence` or null fields.
- Why this matters: Ariadne may have useful grounding but the product shows fake emptiness.
- Verification method: Compare persisted ticket metadata against `/api/issues` list/detail fields for evidence, modules, criteria, source links.
- First fix direction: Fix issue projection evidence/category fields.

## G-035: Why is fallback/template generation not obvious to the user?

- Priority: P1
- Source: KO-006 + KO-020
- Product layer: Knowledge orchestration
- Evidence: Current issue titles match deterministic compiler shape while active `.ariadne/knowledge` lacks source insight/theme files.
- Why this matters: Fallback is allowed, but hiding it overstates agent capability.
- Verification method: Issue Delta displays compiler mode, fallback reason, model/graph status, and limitations.
- First fix direction: Add compile provenance and fallback disclosure to issue delta output.

## G-036: Why does source-analysis limitation not affect Issue Factory confidence?

- Priority: P1
- Source: KO-015 merged into KO-008
- Product layer: Knowledge orchestration
- Evidence: scanner limitations exist but are not prominent in Plan Changes or handoff risk.
- Why this matters: low-depth source understanding should lower confidence before creating high-priority work.
- Verification method: Low-depth repo scan must show limitations and affect issue priority/confidence.
- First fix direction: Propagate source-analysis limitations into issue compiler and UI.

## P2: Quality And Product Sharpness Gaps

## G-037: Does Workbench avoid presenting stage-level success as task success?

- Priority: P2
- Source: MP-024 merged with MP-015
- Product layer: Cross-layer
- Evidence: assignment events showed route/review/memory/board stages as `succeeded` while executable stage was blocked.
- Why this matters: green internal-stage events can visually overpower a blocked task.
- Verification method: Blocked execution renders stage successes as subordinate process events under an overall blocked attempt.
- First fix direction: Separate stage events from terminal task verdict in UI.

## G-038: What makes an artifact path valid enough to display?

- Priority: P2
- Source: MP-017
- Product layer: Cross-layer
- Evidence: `git_diff.patch` was empty and `test_output.json` had `test_exit_code=null`; path existence still appeared as evidence.
- Why this matters: Users need semantic evidence, not filenames.
- Verification method: Artifact links show validity status: missing, empty, not-run, stale, dirty-before-run, or produced-by-run.
- First fix direction: Add artifact validity metadata.

## G-039: Can one source support multiple independent build decisions?

- Priority: P2
- Source: KO-014
- Product layer: Knowledge orchestration
- Evidence: one broad evidence snippet per source cannot explain multiple issues.
- Why this matters: It limits issue decomposition quality.
- Verification method: A non-trivial repo/blog should generate multiple reusable claims tied to separate issues.
- First fix direction: Split source analysis output into claim-level evidence records.

## G-040: Is board mutation intentionally absent or just missing?

- Priority: P2
- Source: MP-020 cut/demoted
- Product layer: Multica parity
- Evidence: backend exposes issue patch action, but board is read-only navigation.
- Why this matters: Main workboard should either manage work or clearly present itself as read-only.
- Verification method: Either move/update status/assignee safely from board, or show read-only affordance and route to exact actions.
- First fix direction: Decide board interaction contract after task truth is fixed.

## G-041: Which visible sidebar controls are real commands today?

- Priority: P2
- Source: MP-023 cut/demoted
- Product layer: Multica parity
- Evidence: sidebar renders search/create/workspace/help controls without meaningful product actions.
- Why this matters: inert controls increase demo feel.
- Verification method: every visible command works, is explicitly disabled with explanation, or is removed.
- First fix direction: Remove or implement nonfunctional shell commands.

## Cross-Layer Failure Map

| Failure | Final issues |
| --- | --- |
| Closure evidence missing | G-001 |
| Current issue/delta truth unstable | G-002, G-003, G-033 |
| Shared work state missing | G-004, G-005, G-006, G-027, G-030 |
| Issue detail not a fact center | G-007, G-028, G-034 |
| Assignment/recovery unsafe | G-008, G-009, G-010, G-011, G-012, G-013 |
| Evidence unreadable or invalid | G-014, G-022, G-023, G-034, G-038 |
| Terminal verdict contradictions | G-015, G-016, G-017, G-037 |
| Knowledge/source understanding shallow | G-019, G-020, G-021, G-024, G-025, G-026, G-035, G-036, G-039 |
| Product affordance quality | G-032, G-040, G-041 |

## Evidence Appendix

- Live API evidence from Multica parity grill:
  - `/api/issues`
  - `/api/issues/M0TR-003`
  - `/api/runs/runtimes`
  - `/api/runs/assignments`
  - `/api/inbox`
  - `/api/daemon/status`
  - `/api/agent-task-snapshot`
  - `/api/assignments/assignment_5135cad3b8ca/events`
- Browser evidence:
  - `docs/reviews/grill-workflows/results/2026-06-24-knowledge-sources.png`
  - `docs/reviews/grill-workflows/results/2026-06-24-knowledge-plan-changes.png`
  - `docs/reviews/grill-workflows/results/2026-06-24-knowledge-issues.png`
- Artifact evidence:
  - `.ariadne/artifacts/ticket_7ce56b0eebb6/execution_log.json`
  - `.ariadne/artifacts/ticket_7ce56b0eebb6/git_diff.patch`
  - `.ariadne/artifacts/ticket_7ce56b0eebb6/test_output.json`
  - `.ariadne/artifacts/ticket_7ce56b0eebb6/review_report.json`
  - `.ariadne/artifacts/ticket_7ce56b0eebb6/landing_evidence.json`
  - `.ariadne/artifacts/ticket_7ce56b0eebb6/memory_record.json`
  - `.ariadne/artifacts/ticket_7ce56b0eebb6/next_tickets.json`
- Persisted-state evidence:
  - `M0TR-001..010` BuildTicket metadata contains source refs while projections under-report grounding.
  - `backlog_preview_8aa11cc0eca5` was original `manual_goal` source-generated delta.
  - `backlog_preview_d28c447255c1` was selected `review_feedback` preview with ungrounded repair operations.
  - `build_context_825e3a5124d7` had no `codebase_snapshot_artifact_id`.
  - `.ariadne/knowledge/resource_56a27abf28d0/` lacked source insight/theme files for the observed active context.
- Multica reference evidence:
  - `packages/views/issues/components/issue-detail.tsx`
  - `packages/views/issues/components/board-view.tsx`
  - `packages/views/agents/components/agents-page.tsx`
  - `packages/views/runtimes/components/runtimes-page.tsx`
  - `server/internal/handler/task_lifecycle.go`
  - `server/migrations/055_task_lease_and_retry.up.sql`
  - `server/cmd/multica/cmd_daemon.go`

## Rejected / Merged Candidates

Standalone candidates removed from the final 41:

- `KO-020`: merged into G-019 / G-035 fallback provenance.
- `KO-015`: merged into G-021 / G-036 repo-understanding limitations.
- `KO-021`: rejected as lower-priority product clarity; useful later but not central.
- `MP-020`: demoted into G-040 as a P2 contract question, not a P0/P1 blocker.
- `MP-023`: demoted into G-041 as P2 shell quality, not a closure blocker.

Important merge decisions:

- `MP-024` is not standalone P2; its evidence feeds G-015 and G-037.
- `MP-006` remains as G-028, but its attempt-labeling fix is subordinate to G-007.
- `KO-014` remains as G-026/G-039 because source-claim granularity is central to Ariadne's upper layer, even though evidence quality judge marked it weaker.
- `KO-019` is represented by G-001, focused on real target version advancement rather than generic dogfood evidence.
