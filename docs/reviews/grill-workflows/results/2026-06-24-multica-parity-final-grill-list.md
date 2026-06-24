# Ariadne Multica Parity Final Grill List

Date: 2026-06-24

Workflow:
`/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/2026-06-24-multica-parity-grill-workflow.md`

Mode: real subagent-assisted grill, 5 rounds.

Scope:

```text
Issue / Ticket board
Issue detail
Agent team
Runtime / daemon
Assignment claim
Progress events
Inbox / blocker recovery
Execution evidence
Review loop
```

Non-scope:

```text
Knowledge source compiler
Issue Factory quality
ProjectKnowledge internals
Frontend redesign plan
Implementation plan
```

## Execution Self-Check

- Round 1 completed: yes.
- Round 2 completed: yes.
- Round 3 completed: yes.
- Round 4 completed: yes.
- Round 5 completed: yes.
- Each round included exactly 9 candidate grill questions: yes.
- Each round included four independent reviewer outputs: yes.
- Each round included a Judge scoring and merge ledger: yes.
- Final list contains 24 grill issues: yes.

## Evidence Used

Live API evidence:

```bash
curl -s http://127.0.0.1:8766/api/issues
curl -s http://127.0.0.1:8766/api/issues/M0TR-003
curl -s http://127.0.0.1:8766/api/runs/runtimes
curl -s http://127.0.0.1:8766/api/runs/assignments
curl -s http://127.0.0.1:8766/api/inbox
curl -s http://127.0.0.1:8766/api/daemon/status
curl -s http://127.0.0.1:8766/api/agent-task-snapshot
curl -s http://127.0.0.1:8766/api/assignments/assignment_5135cad3b8ca/events
```

Browser evidence collected with headless Google Chrome against
`http://127.0.0.1:8766/`:

- `#issues`, `#team`, `#runs`, `#inbox`, and `#diagnostics` rendered.
- The Current Version Context strip displayed `No persisted project loaded`,
  `Ariadne API is not connected`, and `0 current issues`.
- The same browser page sections loaded real Team/Runs data such as 5 agents,
  3 runtime rows, and daemon state. This shows a frontend data-contract split:
  top context can be disconnected while child pages load real API projections.
- Runs showed `Status: Stopped`, `Current issue: M0TR-003`,
  `Claimable: 8`, `Blocked: 33`, and an active assignment progress panel.

Code evidence:

- Ariadne Workbench frontend:
  `/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src`
- Ariadne HTTP/application/runtime:
  `/Users/martinlos/code/Ariadne/ariadne_ltb/interfaces/http/routes.py`,
  `/Users/martinlos/code/Ariadne/ariadne_ltb/application`,
  `/Users/martinlos/code/Ariadne/ariadne_ltb/daemon.py`,
  `/Users/martinlos/code/Ariadne/ariadne_ltb/models.py`
- Multica reference:
  `/Users/martinlos/code/multica/packages/views/issues/components`,
  `/Users/martinlos/code/multica/packages/views/agents/components`,
  `/Users/martinlos/code/multica/packages/views/runtimes/components`,
  `/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go`,
  `/Users/martinlos/code/multica/server/pkg/db/queries/agent.sql`

Artifact evidence:

```text
/Users/martinlos/code/Ariadne/.ariadne/artifacts/ticket_7ce56b0eebb6/execution_log.json
/Users/martinlos/code/Ariadne/.ariadne/artifacts/ticket_7ce56b0eebb6/git_diff.patch
/Users/martinlos/code/Ariadne/.ariadne/artifacts/ticket_7ce56b0eebb6/test_output.json
/Users/martinlos/code/Ariadne/.ariadne/artifacts/ticket_7ce56b0eebb6/review_report.json
/Users/martinlos/code/Ariadne/.ariadne/artifacts/ticket_7ce56b0eebb6/landing_evidence.json
/Users/martinlos/code/Ariadne/.ariadne/artifacts/ticket_7ce56b0eebb6/memory_record.json
/Users/martinlos/code/Ariadne/.ariadne/artifacts/ticket_7ce56b0eebb6/next_tickets.json
/Users/martinlos/code/Ariadne/.ariadne/artifacts/ticket_7ce56b0eebb6/llm_next_tickets.json
```

## Round 1

### Candidate Generator: 9 Questions

1. A1-1: Why can the Issues board not answer "who is working what right now"?
2. A1-2: What is Ariadne's shared task truth if `/api/agent-task-snapshot`
   exposes only one active assignment?
3. A1-3: Why does Issue Detail poll only claimed/running assignment progress
   instead of showing active plus collapsed past runs?
4. A1-4: Can Ariadne rerun a specific failed attempt, or only the latest
   assignment?
5. A1-5: Where is attempt number, parent attempt, max attempts, and heartbeat
   visible as product state?
6. A1-6: Why does orphan recovery requeue stale work instead of using one
   failure/blocker/Inbox pipeline?
7. A1-7: Why does Runs show stopped daemon state while surfacing a current
   assignment as active work?
8. A1-8: Which Ariadne agents are online, unstable, offline, or recently active?
9. A1-9: How does Inbox avoid duplicate blocker spam and prove each blocker has
   exactly one recovery path?

### Reviewer Outputs

Reviewer 1: Product Operator

- Keep: inert sidebar command buttons, board actionability, next-action
  deep-linking, issue detail action clarity, Inbox deep links.
- Drop: pure internal route naming unless it leaks into user behavior.
- Merge: "Next Action page link" and "blocked issue deep link" into one
  exact-object navigation question.
- Evidence: `Sidebar.tsx`, `IssueBoard.tsx`, `IssueDetail.tsx`,
  `InboxPage.tsx`, live `/api/issues/M0TR-003`.

Reviewer 2: Agent Runtime Engineer

- Keep: stopped daemon with current assignment, multiple ready assignments for
  one issue/backend, shared active assignment on every runtime row, rerun latest
  assignment ambiguity.
- Drop: route artifact path as a standalone runtime issue.
- Merge: daemon heartbeat, task snapshot, and runtime rows into one active-work
  truth question.
- Evidence: live `/api/daemon/status`, `/api/runs/assignments`,
  `/api/runs/runtimes`, `workbench_task_snapshot.py`, `workbench_runtimes.py`.

Reviewer 3: Multica Alignment Reviewer

- Keep: task snapshot, execution log, attempt chain, failure pipeline, Team/Run
  presence.
- Drop: board grouping as first-order issue before task snapshot exists.
- Merge: agents/runtimes presence into shared task snapshot.
- Evidence: Multica `queries.ts`, `agent.go`, `execution-log-section.tsx`,
  `task_lifecycle.go`; Ariadne `workbench_task_snapshot.py`, `IssueDetail.tsx`.

Reviewer 4: Quality And State Reviewer

- Keep: duplicate Inbox blockers, missing allowed actions, terminal rerun
  no-op events, dry-run runtime visibility.
- Drop: generic "state source disagreement" unless tied to visible
  contradiction.
- Merge: duplicate blockers and missing allowed actions into one recovery
  contract problem.
- Evidence: `/api/inbox`, `inbox_recovery.py`, `dtos.py`, `InboxPage.tsx`,
  `run_assignment.py`.

### Judge Scoring And Merge

| Candidate | Importance | Verifiable | Dedup | Mainline Impact | Risk | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| A1-1 | 4 | 5 | 4 | 4 | 3 | keep as board/snapshot issue |
| A1-2 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A1-3 | 5 | 5 | 4 | 5 | 4 | keep P0/P1 |
| A1-4 | 5 | 5 | 4 | 5 | 5 | keep P0 |
| A1-5 | 4 | 5 | 4 | 4 | 4 | merge into execution log |
| A1-6 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A1-7 | 5 | 5 | 4 | 5 | 5 | keep P0 |
| A1-8 | 4 | 5 | 3 | 4 | 3 | keep P1 |
| A1-9 | 5 | 5 | 4 | 5 | 5 | keep P0 |

### Round 1 Ledger

Keep:

- Shared task snapshot.
- Execution log as Issue Detail center.
- Failure pipeline.
- Attempt/rerun lineage.
- Inbox recovery identity.

Drop:

- Pure styling parity.
- Internal route naming alone.
- Board grouping before lifecycle state exists.

Merge:

- Agent presence into task snapshot.
- Retry labels into execution log.
- Inbox duplication into failure pipeline.

Remaining gaps:

- Need more evidence on artifact validity and browser action behavior.

Next focus:

- Runtime truth-source contradictions and queue/daemon state.

## Round 2

### Candidate Generator: 9 Questions

1. A2-1: Which object is the runtime truth source when daemon heartbeat and
   assignment status disagree?
2. A2-2: Why does a blocked assignment remain active after daemon stop?
3. A2-3: What prevents Start Daemon from claiming unintended ready assignments?
4. A2-4: Why are multiple ready Codex assignments allowed for one issue/backend?
5. A2-5: Which assignment does Issue Detail consider the selected runnable
   attempt?
6. A2-6: Why does every runtime row inherit the same active assignment?
7. A2-7: Why does the assignment event stream use current terminal status as
   the creation event type?
8. A2-8: Why does runtime capability say Codex/Claude can run while external
   execution is gated?
9. A2-9: Where is the Multica-style dispatched/running/waiting lifecycle
   boundary in Ariadne's Workbench projection?

### Reviewer Outputs

Reviewer 1: Product Operator

- Keep: Context Strip vs Issues API disagreement, daemon stopped/stale with
  assignment, list/detail mismatch, canonical blocker identity.
- Drop: board mutation for this round.
- Merge: blocker strings across delivery/environment/issue/inbox into one
  canonical blocker object question.
- Evidence: browser showed Current Version Context disconnected while page
  sections loaded real data; live `/api/issues` returned 10 issues.

Reviewer 2: Agent Runtime Engineer

- Keep: stopped daemon with current assignment, multiple ready assignments,
  runtime rows sharing active assignment, event stream rewriting history.
- Drop: session/workdir pin for this round.
- Merge: daemon heartbeat, task snapshot, runtime rows into one runtime truth
  source invariant.
- Evidence: live `/api/daemon/status`, `/api/agent-task-snapshot`,
  `/api/runs/runtimes`, `/api/runs/assignments`, `run_events.py`.

Reviewer 3: Multica Alignment Reviewer

- Keep: Multica workspace task snapshot list, latest terminal task per agent,
  exact-row rerun, orphan recovery through failed-task pipeline.
- Drop: broad board grouping.
- Merge: active/past run grouping and transcript into execution log.
- Evidence: Multica `agent.go`, `queries.ts`, `execution-log-section.tsx`,
  `task_lifecycle.go`; Ariadne `workbench_task_snapshot.py`.

Reviewer 4: Quality And State Reviewer

- Keep: duplicate Inbox blockers, missing `allowed_actions`, no-op rerun
  events, dry-run visibility.
- Drop: generic state-source disagreement unless visible.
- Merge: duplicate blockers and allowed actions into one recovery contract.
- Evidence: `/api/inbox` returned three open `M0TR-003 /
  external_execution_blocked` items.

### Judge Scoring And Merge

| Candidate | Importance | Verifiable | Dedup | Mainline Impact | Risk | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| A2-1 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A2-2 | 5 | 5 | 4 | 5 | 5 | merge into A2-1 |
| A2-3 | 5 | 5 | 4 | 5 | 5 | keep P0/P1 |
| A2-4 | 5 | 5 | 4 | 5 | 5 | keep P0 |
| A2-5 | 5 | 5 | 4 | 5 | 5 | keep P0 |
| A2-6 | 4 | 5 | 4 | 4 | 4 | merge into A2-1 |
| A2-7 | 4 | 5 | 4 | 3 | 4 | keep P2 |
| A2-8 | 4 | 5 | 4 | 4 | 4 | keep P1 |
| A2-9 | 5 | 5 | 4 | 5 | 5 | keep P0 |

### Round 2 Ledger

Keep:

- Active-work truth source.
- Single runnable attempt per issue/backend.
- Start Daemon claim scope.
- Event stream honesty.
- Runtime capability current-vs-structural distinction.

Drop:

- Standalone route artifact gap.
- Generic capability wording.

Merge:

- Stale daemon, active snapshot, and runtime active assignment.
- Multiple ready assignments and rerun latest-assignment ambiguity.

Remaining gaps:

- Need artifact/evidence validity and exact action checks.

Next focus:

- User actions and evidence inspection from Issue Detail/Inbox/Runs.

## Round 3

### Candidate Generator: 9 Questions

1. A3-1: How does an operator mutate the issue board without opening every
   issue?
2. A3-2: Why does Issue Detail show Assign, Run Now, and Rerun when only one can
   be valid?
3. A3-3: Why is Run Now tied to browser-session memory instead of persisted
   assignment state?
4. A3-4: Why does the blocker callout navigate only to `#inbox` instead of the
   exact inbox item?
5. A3-5: Why can Inbox actions run before the operator inspects issue evidence?
6. A3-6: What is the intended behavior of artifact links?
7. A3-7: Why does Next Action navigate to a page bucket rather than a concrete
   object?
8. A3-8: Why are sidebar command/search/create buttons visible if they are inert?
9. A3-9: Why does Issue Detail not have a self-contained execution log with
   active and past runs?

### Reviewer Outputs

Reviewer 1: Product Operator

- Keep: exact-object Next Action, persisted rerun after reload, evidence-before
  recovery, artifact opening, assignment-level actions.
- Drop: disconnected context questions for this actionability round.
- Merge: Run Now token, Rerun blocked assignment, and assignment list actions.
- Evidence: `IssueDetail.tsx`, `InboxPage.tsx`, `Sidebar.tsx`,
  `IssueBoard.tsx`.

Reviewer 2: Agent Runtime Engineer

- Keep: terminal verdict contradiction, route/handoff binding, artifact
  validity, blocked execution feeding downstream evidence.
- Drop: daemon truth source unless it affects evidence display.
- Merge: route id mismatch, handoff packet selection, empty diff, null tests
  into one artifact validity contract.
- Evidence: `execution_log.json`, `git_diff.patch`, `test_output.json`,
  `review_report.json`, `landing_evidence.json`.

Reviewer 3: Multica Alignment Reviewer

- Keep: one execution log section, active/past run buckets, transcript links,
  exact-row retry, Retry #N labels, cancel active attempt.
- Drop: board grouping for this round.
- Merge: active/past runs and transcripts into "inspect every run from one log".
- Evidence: Multica `execution-log-section.tsx`; Ariadne `IssueDetail.tsx`.

Reviewer 4: Quality And State Reviewer

- Keep: durable state transitions for actions, no-op rerun events, artifact
  links, durable errors.
- Drop: generic "buttons have APIs" where endpoints exist.
- Merge: no-op rerun and transient errors into truthful durable action state.
- Evidence: `run_assignment.py`, `IssueDetail.tsx`, `routes.ts`,
  `InboxPage.tsx`.

### Judge Scoring And Merge

| Candidate | Importance | Verifiable | Dedup | Mainline Impact | Risk | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| A3-1 | 4 | 5 | 4 | 4 | 3 | keep P1 |
| A3-2 | 5 | 5 | 4 | 5 | 5 | keep P0 |
| A3-3 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A3-4 | 4 | 5 | 4 | 4 | 4 | merge into Inbox recovery |
| A3-5 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A3-6 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A3-7 | 5 | 5 | 4 | 5 | 5 | keep P0 |
| A3-8 | 3 | 5 | 4 | 2 | 2 | keep P2 |
| A3-9 | 5 | 5 | 5 | 5 | 5 | keep P0 |

### Round 3 Ledger

Keep:

- Issue Detail execution log.
- Evidence link validity.
- Run/Rerun state-aware actions.
- Inbox evidence-before-recovery.
- Concrete next action links.

Drop:

- Generic button/API presence.
- Pure sidebar polish as high priority.

Merge:

- Artifact route and artifact validity.
- Rerun token and exact attempt selection.
- Inbox link and recovery policy.

Remaining gaps:

- Need final priority cut: which questions are closure blockers vs maturity.

Next focus:

- Prioritize and deduplicate.

## Round 4

### Candidate Generator: 9 Questions

1. A4-1: What is Ariadne's one shared task snapshot and why should every surface
   trust it?
2. A4-2: Why is Ariadne Issue Detail not centered on a Multica-style execution
   log?
3. A4-3: Do all Ariadne failure paths produce the same blocker, retry, inbox,
   issue, and event semantics?
4. A4-4: Can the top-level Next Action open the exact current blocker object?
5. A4-5: Can a blocked issue be recovered after browser refresh using persisted
   assignment state?
6. A4-6: Can one blocker produce one recovery item with one backend-approved
   action set?
7. A4-7: Does every displayed evidence ref open and verify real evidence?
8. A4-8: What terminal verdict wins when execution, review, landing evidence,
   and issue projection disagree?
9. A4-9: What exact scope does Start Daemon claim from?

### Reviewer Outputs

Reviewer 1: Product Operator

- Keep P0: Next Action exact object, blocked issue recovery after refresh,
  evidence-before-recovery, evidence opening, canonical blocker identity.
- Drop P0 status for board filters/sidebar controls.
- Merge Next Action/blocker/context into one exact-object question.
- Evidence: `CurrentVersionStrip.tsx`, `IssueDetail.tsx`, `InboxPage.tsx`.

Reviewer 2: Agent Runtime Engineer

- Keep P0: runtime truth source, terminal verdict, assignment uniqueness.
- Keep P1: artifact validity, rerun binding, event semantics.
- Drop standalone duplicate Inbox for runtime list; leave to Quality/State.
- Merge terminal verdict and downstream evidence.
- Evidence: live APIs and `.ariadne/artifacts/ticket_7ce56b0eebb6/*`.

Reviewer 3: Multica Alignment Reviewer

- Keep P0: task snapshot, execution log, failure pipeline.
- Keep P1: attempt chain, Team/Runs presence.
- Keep P2: issue board actionability.
- Drop "copy Multica clone" framing.
- Evidence: Multica shared task snapshot, execution log, failure pipeline.

Reviewer 4: Quality And State Reviewer

- Keep P0: stale state as active, duplicate Inbox blockers, missing allowed
  actions.
- Keep P1: no-op/stale action state, durable errors, artifact validity.
- Keep P2: dry-run runtime visibility.
- Merge duplicate Inbox and action policy.

### Judge Scoring And Merge

| Candidate | Importance | Verifiable | Dedup | Mainline Impact | Risk | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| A4-1 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A4-2 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A4-3 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A4-4 | 5 | 5 | 4 | 5 | 5 | keep P0 |
| A4-5 | 5 | 5 | 4 | 5 | 5 | keep P0 |
| A4-6 | 5 | 5 | 4 | 5 | 5 | keep P0 |
| A4-7 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A4-8 | 5 | 5 | 5 | 5 | 5 | keep P0 |
| A4-9 | 4 | 5 | 4 | 5 | 5 | keep P1 |

### Round 4 Ledger

Keep:

- Shared task snapshot.
- Execution log.
- Failure pipeline.
- Canonical blocker and recovery object.
- Terminal verdict precedence.
- Evidence validity.

Drop:

- Board drag/drop as immediate blocker.
- Inert sidebar controls as P0.
- "More fields" without surface consumption.

Merge:

- Duplicate Inbox + allowed actions.
- No-op rerun + durable action state.
- Stage success + terminal verdict.

Remaining gaps:

- Need final list quality validation: 20-25 items, no duplicates, no implementation
  plan.

Next focus:

- Final validation and exact final issue set.

## Round 5

### Candidate Generator: 9 Questions

1. A5-1: What is Ariadne's local-first equivalent of Multica's workspace task
   snapshot, without copying Postgres/server locks?
2. A5-2: Can every Ariadne surface derive live work state from the same task
   snapshot?
3. A5-3: Can Issue Detail be centered on a single execution log?
4. A5-4: Can every failure path flow through one local failure pipeline?
5. A5-5: Can a user retry the exact failed attempt row they clicked?
6. A5-6: Can every displayed evidence ref be opened and verified?
7. A5-7: Can one blocker produce one recovery item with backend-approved actions?
8. A5-8: Does blocked execution dominate all projections and downstream
   artifacts?
9. A5-9: Can the Issue Board route users to the concrete next action, not just a
   status column?

### Reviewer Outputs

Reviewer 1: Product Operator

- Keep P0 closure blockers from Round 4.
- Drop duplicate Next Action, Inbox link, artifact link formulations.
- Merge blocker identity and exact-object navigation.
- Must not miss: recover after browser refresh, evidence-before-recovery,
  open evidence, exact blocker object.

Reviewer 2: Agent Runtime Engineer

- Keep P0: runtime truth source, terminal verdict, assignment uniqueness.
- Add missing P0: blocked execution still feeds downstream synthesis.
- Drop duplicate handoff packet and route path details as standalone.
- Merge into active-work truth, single runnable attempt, terminal verdict, valid
  evidence bundle.

Reviewer 3: Multica Alignment Reviewer

- Keep P0: shared task snapshot, execution log, failure pipeline.
- Keep P1: attempt chain and agent/runtime presence.
- Drop "Multica clone" framing and Go/Postgres/auth assumptions.
- Merge Inbox duplication into failure pipeline and board actionability into
  concrete next-action routing.

Reviewer 4: Quality And State Reviewer

- Keep P0: stale active-work truth, duplicate Inbox blockers, missing
  `allowed_actions`.
- Keep P1: no-op rerun state, transient errors, artifact/evidence refs.
- Keep P1/P2: dry-run visible beside product runtimes.
- Merge stale state into active-work truth and action failures into durable
  action transition.

### Judge Scoring And Merge

| Candidate | Importance | Verifiable | Dedup | Mainline Impact | Risk | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| A5-1 | 5 | 5 | 5 | 5 | 5 | final MP-001 |
| A5-2 | 5 | 5 | 4 | 5 | 5 | final MP-002 |
| A5-3 | 5 | 5 | 5 | 5 | 5 | final MP-004/005 |
| A5-4 | 5 | 5 | 5 | 5 | 5 | final MP-009 |
| A5-5 | 5 | 5 | 4 | 5 | 5 | final MP-007 |
| A5-6 | 5 | 5 | 5 | 5 | 5 | final MP-014 |
| A5-7 | 5 | 5 | 4 | 5 | 5 | final MP-010/011 |
| A5-8 | 5 | 5 | 5 | 5 | 5 | final MP-015/016 |
| A5-9 | 4 | 5 | 4 | 4 | 4 | final MP-019/020 |

### Round 5 Ledger

Keep:

- 24 final issues.
- Strong P0/P1/P2 split.
- Multica mechanisms, not Multica infrastructure.

Drop:

- Broad essays.
- Implementation tasks.
- Surface polish that does not expose a work-management semantic.

Merge:

- Next Action and blocker identity.
- Inbox duplicates and allowed actions.
- Artifact routing and artifact validity.
- Attempt chain and execution log.

Remaining gaps:

- None for this review workflow. Implementation planning is intentionally next.

Next focus:

- Run Workflow B for knowledge orchestration, then Workflow C to merge final
  41 grill items.

## Final Grill Issues

## MP-001: What is Ariadne's local-first equivalent of Multica's shared task snapshot?

- Priority: P0
- Product surface: Issues, Team, Runs, Issue Detail, Current Version Context
- Multica reference: Multica exposes a workspace task snapshot that includes
  active tasks plus latest terminal task state and drives issues, agents, and
  runtimes.
- Ariadne evidence: `/api/agent-task-snapshot` exposes a singleton
  `active_assignment` plus aggregate counts; live API showed
  `active_assignment=assignment_5135cad3b8ca`, `queued_count=14`,
  `blocked_count=33`.
- Why this must be fixed: without one task truth, every page invents its own
  state and the product cannot feel like an agent workbench.
- Verification method: create running, blocked, completed, and queued
  assignments; verify Issues, Team, Runs, Issue Detail, and Context Strip all
  render from the same task snapshot.
- Suggested owner area: `ariadne_ltb/application/workbench_task_snapshot.py`,
  API projections, frontend shared state.

## MP-002: Why can stale daemon heartbeat still drive active work state?

- Priority: P0
- Product surface: Runs, Current Version Context, task snapshot
- Multica reference: Multica derives running issue indicators from task rows
  with running-like statuses, not stale daemon memory.
- Ariadne evidence: live `/api/daemon/status` reported `status=stopped`,
  `stale=true`, `current_assignment_id=assignment_5135cad3b8ca`,
  `current_ticket_key=M0TR-003`; task snapshot and runtime rows reused it.
- Why this must be fixed: users see stopped/stale work as active work.
- Verification method: stop daemon after a blocked assignment; no surface should
  present the assignment as active unless a non-terminal task state proves it.
- Suggested owner area: `ariadne_ltb/application/daemon_control.py`,
  `ariadne_ltb/application/workbench_task_snapshot.py`,
  `frontend/ariadne-workbench/src/pages/runs/RunsPage.tsx`.

## MP-003: What invariant prevents duplicate runnable attempts for one issue/backend?

- Priority: P0
- Product surface: Runs, Issue Detail, daemon claim
- Multica reference: Multica claim logic prevents duplicate in-flight work for
  the same issue/agent through task lifecycle and claim constraints.
- Ariadne evidence: live `/api/runs/assignments` showed M0TR-003 with one
  blocked Codex assignment and two additional `ready_to_claim` Codex
  assignments.
- Why this must be fixed: broad daemon start or issue-level rerun can claim the
  wrong attempt.
- Verification method: assign/rerun the same issue multiple times; Workbench
  should show one current runnable attempt or explicit attempt lineage, never
  ambiguous duplicates.
- Suggested owner area: assignment creation, retry service, daemon claim
  selection, Workbench assignment projection.

## MP-004: Why is Issue Detail not centered on one execution log?

- Priority: P0
- Product surface: Issue Detail
- Multica reference: Multica Issue Detail uses a single execution log with
  active runs, past runs, row actions, transcript, retry, and cancel.
- Ariadne evidence: Ariadne Issue Detail spreads state across Execution Results,
  Assignment Progress, Timeline, Comments, Handoff/Route, Diff/Tests/Review,
  and Assignments panels.
- Why this must be fixed: users must reconstruct "what happened" from fragments.
- Verification method: open a blocked issue with multiple attempts; one section
  should show active/past attempts, status, actor, backend, evidence, retry, and
  transcript.
- Suggested owner area:
  `frontend/ariadne-workbench/src/pages/issues/IssueDetail.tsx`,
  issue detail DTO.

## MP-005: Can Ariadne show active queued/dispatched/parked/running work, not just claimed/running assignments?

- Priority: P1
- Product surface: Issue Detail, Runs
- Multica reference: Multica treats queued, dispatched, waiting-local-directory,
  and running work as active execution-log rows.
- Ariadne evidence: `activeAssignment()` in Issue Detail only accepts
  `claimed` and `running`; Runs uses `daemon.current_assignment_id` first.
- Why this must be fixed: queued or dispatched work disappears in Issue Detail,
  while stale daemon state can still appear in Runs.
- Verification method: create queued, dispatched, claimed, running, blocked
  assignments; each must render in the correct active/past bucket.
- Suggested owner area: assignment status mapping, execution log DTO, Issue
  Detail and Runs pages.

## MP-006: Where are past runs collapsed and labeled as attempts?

- Priority: P1
- Product surface: Issue Detail execution history
- Multica reference: Multica collapses past runs with count and shows retry
  labels from parent task and attempt number.
- Ariadne evidence: Issue Detail lists execution results and assignments
  separately; assignment rows show agent/backend/status/id but not Retry #N or
  parent lineage.
- Why this must be fixed: repeated attempts become noise or disappear.
- Verification method: create retry attempts; the UI should show "Retry #2",
  parent attempt linkage, status, timestamp, and row-level evidence.
- Suggested owner area: assignment DTO, retry projection, Issue Detail.

## MP-007: Can a user rerun the exact failed attempt they clicked?

- Priority: P0
- Product surface: Issue Detail actions
- Multica reference: Multica rerun accepts a task id from the selected execution
  row.
- Ariadne evidence: Issue Detail top-level Rerun calls issue-level
  `rerunIssue(issueKey, payload)` and backend resolves latest assignment; live
  M0TR-003 had multiple assignments.
- Why this must be fixed: rerun can target the wrong attempt.
- Verification method: create multiple attempts; click retry on a specific
  failed row; new attempt must record parent assignment and source row.
- Suggested owner area: issue action API, retry service, Issue Detail row
  actions.

## MP-008: Can a blocked issue be recovered after browser refresh using persisted assignment state?

- Priority: P0
- Product surface: Issue Detail actions
- Multica reference: Multica task actions are tied to persisted task state, not
  ephemeral browser state.
- Ariadne evidence: `runCurrentIssue()` throws unless `confirmationToken` exists
  in React component state; refresh loses the token even though assignments
  persist.
- Why this must be fixed: a local product cannot require the same browser
  session to recover work.
- Verification method: assign an issue, refresh browser, then recover/rerun
  using persisted assignment state and explicit runtime gate status.
- Suggested owner area: confirmation token lifecycle, assignment action DTO,
  Issue Detail action gating.

## MP-009: Do all failure paths flow through one local failure pipeline?

- Priority: P0
- Product surface: daemon, Inbox, issue timeline, retry, blocker state
- Multica reference: Multica funnels orphan recovery and task failure through a
  shared failure handler that updates retry, issue status, and UI state.
- Ariadne evidence: daemon stale recovery directly calls `assignment.requeue()`;
  execution failure, external-execution blocked, retry exhaustion, and inbox
  recovery create partially different state.
- Why this must be fixed: failure creates duplicate blockers and inconsistent
  recovery semantics.
- Verification method: trigger execution blocked, test failure, stale daemon,
  manual cancel, and retry exhaustion; all should produce one consistent
  blocker/retry/inbox/event path.
- Suggested owner area: `ariadne_ltb/daemon.py`, `ariadne_ltb/inbox.py`,
  retry/failure services.

## MP-010: Can one blocker produce one recovery item with one backend-approved action set?

- Priority: P0
- Product surface: Inbox, Issue Detail blocker callout
- Multica reference: Multica failure handling reconciles task failure and
  recovery into one coherent UI path.
- Ariadne evidence: live `/api/inbox` returned three open `M0TR-003 /
  external_execution_blocked` items created within one second.
- Why this must be fixed: duplicate Inbox rows make the user unsure how many
  problems exist.
- Verification method: trigger one external execution gate failure; Inbox should
  show one blocker item with linked evidence refs.
- Suggested owner area: `ariadne_ltb/inbox.py`,
  `ariadne_ltb/application/workbench_inbox.py`.

## MP-011: Why does Inbox expose all actions instead of backend-approved actions?

- Priority: P0
- Product surface: Inbox
- Multica reference: action affordances should follow task/failure state.
- Ariadne evidence: backend `classify_inbox_item()` computes allowed actions;
  `InboxListItemDTO` omits `allowed_actions`; `InboxPage.tsx` renders Repair,
  Rerun, Acknowledge, Resolve for every item.
- Why this must be fixed: users can click recovery actions that are unsafe or
  semantically wrong.
- Verification method: create each failure type; Inbox must render only the
  valid actions returned by backend policy.
- Suggested owner area: Inbox DTO, Inbox action service, `InboxPage.tsx`.

## MP-012: Does every action produce a truthful durable state transition?

- Priority: P1
- Product surface: Issue Detail, Runs, Inbox, timeline
- Multica reference: task lifecycle events represent actual transitions, not
  transient button messages.
- Ariadne evidence: `RunAssignmentService.run()` can append "run requested"
  comments/events for terminal assignments; frontend often converts errors to
  transient `setMessage(...)`.
- Why this must be fixed: a workbench timeline cannot be trusted if no-op or
  rejected actions look like dispatches.
- Verification method: attempt unsafe rerun, stale daemon start, invalid inbox
  action; each must create durable "rejected/no-op/blocked" state or no event.
- Suggested owner area: action services, runtime events, frontend action error
  handling.

## MP-013: What exact scope does Start Daemon claim from?

- Priority: P1
- Product surface: Runs, daemon control
- Multica reference: Multica task claim operates against explicit task/runtime
  state and avoids unintended concurrent claims.
- Ariadne evidence: Runs page calls `startDaemon({ external_execution_authorized:
  true })` without assignment id, project id, or backend; daemon status showed
  14 open and 8 claimable assignments.
- Why this must be fixed: "Start Daemon" can run work the user did not mean to
  run.
- Verification method: with multiple claimable assignments, starting daemon from
  a selected issue must only claim scoped assignment/project/backend work.
- Suggested owner area: daemon control input defaults, Runs page, runtime scope.

## MP-014: Can every displayed evidence ref be opened and verified from Workbench?

- Priority: P0
- Product surface: Issue Detail, Plan/Artifacts, evidence links
- Multica reference: Multica exposes transcripts and run rows as inspectable
  product surfaces.
- Ariadne evidence: Issue Detail links diff/log as `#artifact:<path>`, but
  router has no artifact route; Plan Changes and Issue Detail show some refs as
  raw `<code>` values.
- Why this must be fixed: evidence that cannot be opened is decorative.
- Verification method: click diff, execution log, review, memory, source, and
  next-ticket refs; each must open a readable evidence surface or local file
  action.
- Suggested owner area: artifact route/viewer, Issue Detail evidence widgets,
  router.

## MP-015: What terminal verdict wins when execution, review, landing evidence, and issue projection disagree?

- Priority: P0
- Product surface: issue list, issue detail, board cards, landing evidence
- Multica reference: a task/issue terminal state should not be contradicted by
  stage-level events.
- Ariadne evidence: `/api/issues` reported M0TR-003 `last_run_status=succeeded`;
  issue detail showed execution `blocked=true`, `failure_reason=
  external_execution_blocked`, `exit_code=2`, and review `blocked`.
- Why this must be fixed: users may believe a blocked run succeeded.
- Verification method: blocked execution must dominate list cards, detail,
  board, timeline, and evidence packet until a successful attempt supersedes it.
- Suggested owner area: issue projection, current state reducer, board cards.

## MP-016: Why does blocked execution continue into downstream memory/next-ticket artifacts as if execution produced useful results?

- Priority: P0
- Product surface: memory, next tickets, review/evidence
- Multica reference: failed execution should produce failure evidence and
  recovery state, not successful-run synthesis.
- Ariadne evidence: M0TR-003 artifacts included blocked execution, empty diff,
  null tests, but downstream memory/next-ticket artifacts contained claims about
  executed Codex, changed files, or passed tests.
- Why this must be fixed: downstream planning becomes poisoned by false run
  evidence.
- Verification method: after a blocked external-execution gate, generated memory
  and next tickets must explicitly cite the blocker and must not claim code
  execution, tests, or changed files succeeded.
- Suggested owner area: orchestrator evidence rollup, memory writer, next-ticket
  generator.

## MP-017: What makes an artifact path valid enough to display as evidence?

- Priority: P1
- Product surface: Issue Detail, evidence packet
- Multica reference: execution-log rows expose real transcript/status content.
- Ariadne evidence: `git_diff.patch` was 0 bytes; `test_output.json` had
  `test_exit_code=null`; route path was null; changed files came from unchanged
  before/after git status.
- Why this must be fixed: path existence is not evidence validity.
- Verification method: evidence links must include validity status: missing,
  empty, not-run, stale, dirty-before-run, or produced-by-run.
- Suggested owner area: evidence projection, execution result mapper, artifact
  writer.

## MP-018: Are changed files execution output or pre-existing dirty workspace state?

- Priority: P1
- Product surface: execution result, review, evidence packet
- Multica reference: execution artifacts should belong to a run attempt.
- Ariadne evidence: external execution was blocked before Codex could run;
  `git_status_before` and `git_status_after` were identical; changed-file
  evidence included pre-existing untracked files/run artifacts.
- Why this must be fixed: users may attribute unrelated workspace dirt to the
  agent.
- Verification method: run with dirty target repo; Workbench must distinguish
  pre-existing dirty files from backend-produced changes.
- Suggested owner area: execution backend, git diff capture, review evidence.

## MP-019: Can the Issue Board route users to the concrete next action, not just a status column?

- Priority: P1
- Product surface: Issues board
- Multica reference: Multica issue board/cards expose agent activity and
  context-aware issue navigation.
- Ariadne evidence: `IssueBoard.tsx` maps cards to open detail; blocked cards do
  not deep-link to blocker, execution evidence, assignment, or review section.
- Why this must be fixed: board remains a status museum instead of an operations
  surface.
- Verification method: click blocked/running/review cards; route should land on
  the exact relevant section/action.
- Suggested owner area: issue board card actions, route hash anchors, Issue
  Detail section ids.

## MP-020: Can the board mutate work state or is it only read-only navigation?

- Priority: P2
- Product surface: Issues board
- Multica reference: Multica board supports work-management interactions like
  status/assignee updates and filters/grouping.
- Ariadne evidence: backend exposes `PATCH /api/issues/{id}`; board only opens
  cards and has fixed status columns.
- Why this must be fixed: users expect the main workboard to manage work, not
  only display it.
- Verification method: from the board, move or update status/assignee safely, or
  make the read-only nature explicit.
- Suggested owner area: issue board controls, issue patch API, board filters.

## MP-021: Can Team and Runs explain agent/backend presence from the same data Issue Detail uses?

- Priority: P1
- Product surface: Team, Runs, Issue Detail
- Multica reference: Multica derives presence and workload from shared task
  snapshot/runtime state.
- Ariadne evidence: Team renders static projected profiles and counts; Runs
  renders runtime capability and daemon state; Issue Detail has separate
  assignments/execution results. These can disagree.
- Why this must be fixed: "Codex blocked", "Codex idle", and "Codex active" must
  mean one thing across the product.
- Verification method: with one running and one blocked attempt, Team/Runs/Issue
  Detail must show consistent presence and workload.
- Suggested owner area: Team/Runs projections, task snapshot, Issue Detail.

## MP-022: Why is dry-run visible beside product Codex/Claude runtimes?

- Priority: P2
- Product surface: Runs, runtime capability
- Multica reference: diagnostic/local fallback modes should not masquerade as
  product execution routes.
- Ariadne evidence: live `/api/runs/runtimes` included `Dry-run fallback` next
  to CodexBackend and ClaudeCodeBackend.
- Why this must be fixed: it risks fake/demo acceptance in the product control
  plane.
- Verification method: product runtime list either hides dry-run or marks it as
  diagnostic-only and impossible to use as product evidence.
- Suggested owner area: runtime projection, Runs UI, product doctor.

## MP-023: Which visible sidebar controls are real commands today?

- Priority: P2
- Product surface: sidebar
- Multica reference: Multica sidebar actions are workspace/context-aware.
- Ariadne evidence: sidebar renders search, create issue, workspace switch, and
  help buttons without meaningful action handlers.
- Why this must be fixed: inert controls make the product feel fake even when
  the backend has real state.
- Verification method: every visible command either works, is explicitly
  disabled with explanation, or is removed.
- Suggested owner area: `Sidebar.tsx`, command palette/create flows.

## MP-024: Does the Workbench avoid presenting stage-level success as task success?

- Priority: P2
- Product surface: timeline, event stream, Issue Detail
- Multica reference: task status and stage logs are distinct; terminal task
  state should dominate.
- Ariadne evidence: assignment events included route/review/memory/board stages
  marked `succeeded` while executable stage was blocked; issue list still showed
  `last_run_status=succeeded`.
- Why this must be fixed: green internal-stage events can visually overpower a
  blocked task.
- Verification method: blocked execution should render stage successes as
  subordinate process events under an overall blocked attempt.
- Suggested owner area: run event projection, timeline component, issue current
  state reducer.

## Top 5 Structural Failures

1. Ariadne lacks one shared task snapshot contract equivalent to Multica's
   active-plus-latest-terminal task view.
2. Issue Detail is not organized around a single execution log; run state is
   fragmented across panels.
3. Failure paths do not converge into one blocker/retry/inbox/evidence pipeline.
4. The product does not consistently distinguish terminal task verdict from
   internal stage success.
5. Evidence links and artifact paths exist, but many are not inspectable or not
   valid proof of backend execution.

## What Ariadne Should Copy From Multica

- Shared task snapshot semantics: active tasks plus sticky latest terminal task.
- Execution log as the issue-detail operations spine.
- Per-attempt row actions: transcript, retry exact row, cancel active row.
- Attempt lineage and retry labels.
- Failure pipeline discipline: failure, retry, blocker, and UI state come from
  one path.
- Agent/runtime presence derived from task state, not static profile tables.

## What Ariadne Must Not Copy From Multica

- Go backend requirement.
- Postgres-backed multi-user workspace model.
- Hosted auth, billing, or tenant system.
- Remote runtime registry.
- Multica's exact schema or deployment model.

Ariadne should copy the work-management semantics into its Python local-first
runtime and `.ariadne` JSON/JSONL store.

## Evidence Appendix

### Live State Snapshot

- `/api/issues`: 10 current issues; M0TR-003 was blocked while reporting
  `last_run_status=succeeded`.
- `/api/issues/M0TR-003`: 3 assignments, blocked execution result, review
  verdict blocked, 24 evidence items.
- `/api/runs/assignments`: two ready Codex assignments for M0TR-003 plus one
  blocked Codex assignment.
- `/api/runs/runtimes`: dry-run, Codex, and Claude rows shared the same
  `active_assignment`.
- `/api/daemon/status`: `stopped`, `stale=true`, `current_ticket_key=M0TR-003`,
  `claimable_assignment_count=8`, `blocked_assignment_count=33`.
- `/api/inbox`: three open `M0TR-003 / external_execution_blocked` items.

### Browser State Snapshot

- `#issues`: Context Strip showed no persisted project/API disconnected while
  the page itself could load issue UI shell.
- `#team`: showed 5 agents and Codex blocked count, while Context Strip still
  showed disconnected state.
- `#runs`: showed stopped daemon, current issue M0TR-003, claimable 8, blocked
  33, and runtime rows.
- `#inbox`: showed Inbox shell and loading/empty state under disconnected strip.
- `#diagnostics`: showed disconnected local API message despite live API curls
  succeeding.

### Key Ariadne Files

```text
/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues/IssueDetail.tsx
/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/issues/IssueBoard.tsx
/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/runs/RunsPage.tsx
/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/pages/inbox/InboxPage.tsx
/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src/widgets/current-version/CurrentVersionStrip.tsx
/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_task_snapshot.py
/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_runtimes.py
/Users/martinlos/code/Ariadne/ariadne_ltb/application/workbench_issues.py
/Users/martinlos/code/Ariadne/ariadne_ltb/application/run_assignment.py
/Users/martinlos/code/Ariadne/ariadne_ltb/application/run_events.py
/Users/martinlos/code/Ariadne/ariadne_ltb/application/inbox_recovery.py
/Users/martinlos/code/Ariadne/ariadne_ltb/daemon.py
```

### Key Multica Files

```text
/Users/martinlos/code/multica/packages/views/issues/components/issues-page.tsx
/Users/martinlos/code/multica/packages/views/issues/components/board-view.tsx
/Users/martinlos/code/multica/packages/views/issues/components/issue-detail.tsx
/Users/martinlos/code/multica/packages/views/issues/components/execution-log-section.tsx
/Users/martinlos/code/multica/packages/views/agents/components/agents-page.tsx
/Users/martinlos/code/multica/packages/views/runtimes/components/runtimes-page.tsx
/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go
/Users/martinlos/code/multica/server/pkg/db/queries/agent.sql
```

