# Multica Downstream Parity Evidence

Status: `BLOCKED_WITH_EVIDENCE`

Multica reference revalidation: `completed`

Latest Multica reference run:

- Evidence: `revalidation-2026-06-27/`
- Multica project: `Ariadne Dogfood: Mini Coding Agent v0.1`
- Multica issue: `LOC-109 Define mini coding agent v0.1 from external references`
- Agent: `Ariadne Implementer`
- Runtime: `Codex (192.168.5.116)`
- Final task: `18aa1811-4edc-4613-b971-88df69fb25d9`
- Final task status: `completed`
- Final issue status: `in_review`

This confirms the Multica downstream reference behavior exists locally: project resources,
issue assignment, task queue, runtime claim, run messages, retry, failure taxonomy, Inbox,
agent activity, issue comment write-back, and status update.

The `BLOCKED_WITH_EVIDENCE` status below is Ariadne's own prior product-closure evidence,
not a statement that Multica is unavailable.

Canonical browser/API closure run: `M0TR-002` via assignment `assignment_699c4079b8ca` assigned to `Phase 3 Codex 1782402810345`.

What this proves:

- A real persisted AgentDefinition is visible in Workbench.
- A current-version BuildTicket was assigned to that agent.
- Agent Tasks, Activity, Runs, Skills, Instructions, and Environment surfaces are backed by store/API data.
- Runtime claimed the assignment through `run-now`.
- CodexBackend produced an honest gated block because `ARIADNE_ENABLE_EXTERNAL_EXECUTION` was unset.
- The blocked execution result has `changed_files: []` and empty `git_diff`; no target files were falsely attributed.
- Memory, Feishu preview, next tickets, board, issue detail, agent detail, inbox, and assignment events were captured.

Real external execution ran: `false`

External blocker:

```text
External execution blocked: ARIADNE_ENABLE_EXTERNAL_EXECUTION must be 1.
```

Canonical files:

- `runtime-run-now-response-m0tr-002-clean.json`
- `artifact-execution-result.json`
- `artifact-review-report.json`
- `artifact-memory.md`
- `artifact-feishu-plan.json`
- `artifact-next-tickets.json`
- `artifact-board.md` (canonical M0TR-002 excerpt; full generated board remains `.ariadne/board/index.md`)
- `artifact-orchestrator-result.json`
- `artifact-landing-evidence-json.json`
- `issue-M0TR-002-after-runtime.json`
- `agent-tasks-after-runtime.json`
- `agent-activity-after-runtime.json`
- `assignment-events-after-runtime.json`
- `inbox-after-runtime.json`
- `workbench-after-runtime.json`
- `closure-result.json`

Screenshot note: browser screenshot capture timed out in this environment, so DOM snapshots and visible summaries are the canonical browser evidence.
