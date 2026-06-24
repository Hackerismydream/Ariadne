# Ariadne Grill Workflow A: Multica Parity Layer

## Purpose

Use this workflow in a new Codex or Claude thread to grill Ariadne's lower
agent work-management layer against Multica.

This thread must answer one question:

```text
Why does Ariadne still not feel like Multica as an agent workbench?
```

Scope is the lower layer only:

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

Do not review Ariadne's knowledge-source compiler here except where it blocks
the work-management layer.

## Required Reading

Read these Ariadne files first:

```text
/Users/martinlos/code/Ariadne/AGENTS.md
/Users/martinlos/code/Ariadne/README.md
/Users/martinlos/code/Ariadne/docs/adr/ADR-0004-ticket-centered-agent-workbench.md
/Users/martinlos/code/Ariadne/docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md
/Users/martinlos/code/Ariadne/docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md
/Users/martinlos/code/Ariadne/docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md
```

Read these Multica files as reference:

```text
/Users/martinlos/code/multica/packages/views/layout/app-sidebar.tsx
/Users/martinlos/code/multica/packages/views/issues/components/issues-page.tsx
/Users/martinlos/code/multica/packages/views/issues/components/board-view.tsx
/Users/martinlos/code/multica/packages/views/issues/components/issue-detail.tsx
/Users/martinlos/code/multica/packages/views/agents/components/agents-page.tsx
/Users/martinlos/code/multica/packages/views/runtimes/components/runtimes-page.tsx
/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go
/Users/martinlos/code/multica/server/migrations/055_task_lease_and_retry.up.sql
/Users/martinlos/code/multica/server/cmd/multica/cmd_daemon.go
```

Inspect these Ariadne implementation areas:

```text
/Users/martinlos/code/Ariadne/frontend/ariadne-workbench/src
/Users/martinlos/code/Ariadne/ariadne_ltb/interfaces/http/routes.py
/Users/martinlos/code/Ariadne/ariadne_ltb/application
/Users/martinlos/code/Ariadne/ariadne_ltb/daemon.py
/Users/martinlos/code/Ariadne/ariadne_ltb/models.py
```

## Hard Rules

- Do not implement fixes.
- Do not create new feature plans.
- Do not accept mock, sample, fixture, or static fallback product data.
- Do not count CLI-only behavior as Workbench product closure.
- Do not claim real Codex / Claude execution works unless there is evidence.
- Every grill issue must cite concrete evidence: file path, browser behavior,
  API response, persisted artifact, or command output.

## Browser And API Checks

Start or use the running Workbench:

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

Use the browser to inspect:

```text
http://127.0.0.1:8766/#issues
http://127.0.0.1:8766/#team
http://127.0.0.1:8766/#runs
http://127.0.0.1:8766/#inbox
http://127.0.0.1:8766/#diagnostics
```

Also inspect these APIs:

```bash
curl -s http://127.0.0.1:8766/api/issues
curl -s http://127.0.0.1:8766/api/team/agents
curl -s http://127.0.0.1:8766/api/runs/runtimes
curl -s http://127.0.0.1:8766/api/runs/assignments
curl -s http://127.0.0.1:8766/api/inbox
curl -s http://127.0.0.1:8766/api/daemon/status
```

## Five-Round Grill Loop

Run 5 rounds. Each round has 3 roles.

### Role 1: Candidate Generator

At the start of each round, generate exactly 9 candidate grill questions.

Each question must be:

- sharp;
- specific;
- falsifiable;
- non-duplicate;
- tied to a visible product gap;
- tied to a Multica reference behavior;
- answerable by code, browser, API, or artifact evidence.

Question format:

```markdown
### Candidate A<round>-<number>: <question>

- Multica expectation:
- Ariadne observed behavior:
- Evidence to collect:
- Why this matters for AI Builder workbench maturity:
```

### Role 2: Four Independent Reviewers

Create four independent reviewer markdown sections. They must not merge their
opinions before writing.

Reviewer 1: Product Operator

- Focus: can a user understand what to do next?
- Check: navigation, issue board, issue detail, next action, blocked state.

Reviewer 2: Agent Runtime Engineer

- Focus: assignment, daemon claim, runtime capability, execution evidence.
- Check: whether the system can clearly run the selected issue with selected
  backend and return progress.

Reviewer 3: Multica Alignment Reviewer

- Focus: what Multica already does that Ariadne lacks or weakly implements.
- Check: issue work-management semantics, not surface styling.

Reviewer 4: Quality And State Reviewer

- Focus: persisted state, no mock product data, action reliability, error
  recovery.
- Check: API contracts, stale state, hidden queue behavior, Inbox recovery.

Each reviewer must output:

```markdown
## Reviewer <n> Round <round>

### Keep
- ...

### Drop
- ...

### Merge / Rewrite
- ...

### New Grill Questions
1. ...

### Evidence
- ...
```

### Role 3: Judge

Read all four reviewer outputs. Score every candidate using:

```text
importance: 0-5
verifiability: 0-5
deduplication: 0-5
mainline impact: 0-5
risk exposure: 0-5
```

Then update a round ledger:

```markdown
## Round <round> Ledger

### Confirmed Grill Questions
- ...

### Eliminated Questions
- question:
  reason:

### Merged Questions
- from:
  into:
  reason:

### Remaining Gaps
- ...

### Next Round Focus
- ...
```

## Final Output

Write final output to:

```text
/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/results/YYYY-MM-DD-multica-parity-final-grill-list.md
```

The final file must contain exactly 20 to 25 high-quality grill issues for this
layer.

Each final issue must use this format:

```markdown
## MP-001: <question>

- Priority: P0 | P1 | P2
- Product surface:
- Multica reference:
- Ariadne evidence:
- Why this must be fixed:
- Verification method:
- Suggested owner area:
```

Also include:

```markdown
## Top 5 Structural Failures

## What Ariadne Should Copy From Multica

## What Ariadne Must Not Copy From Multica

## Evidence Appendix
```

## Prompt To Paste Into New Thread

```text
You are reviewing Ariadne as the Multica Parity Grill thread.

Read and follow:
/Users/martinlos/code/Ariadne/docs/reviews/grill-workflows/2026-06-24-multica-parity-grill-workflow.md

Your output must be the final markdown file requested by that workflow.
Do not implement fixes. Do not write a broad essay. Run the 5-round grill loop,
use browser/API/code evidence, and produce the final Multica parity grill list.
```
