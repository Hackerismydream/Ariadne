# Ariadne v1.0 Runtime Flow

Status: Updated by
[`ADR-0004`](../adr/ADR-0004-ticket-centered-agent-workbench.md).

This document freezes the Ariadne v1.0 runtime paths around ticket-centered
agent work. Historical BuildGoal-first command sketches are superseded; a goal
may be an input, but the runtime works tickets and assignments.

## Current v1.0 Product Path

The production local path is Agent Teammate Mode with real integrations when
their credentials, CLIs, and confirmation gates are present:

```bash
ari doctor integrations
ari ingest examples/sources/*.md --planner llm
ari ticket list
ari ticket assign ARI-003 --to codex --runtime-profile production
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
ari review run ARI-003 --reviewer llm
FEISHU_ENABLE_WRITE=1 ari feishu write ARI-003 --confirm-write
ari github sync ARI-003 --confirm-write
ari ticket comments ARI-003
ari runtime journal
ari export board
ari evidence packet --require-acceptance-ready
```

Fallback:

```bash
python3.11 -m ariadne_ltb.cli doctor integrations
python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md --planner llm
python3.11 -m ariadne_ltb.cli ticket list
python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to codex --runtime-profile production
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 python3.11 -m ariadne_ltb.cli daemon run-once --confirm-execution
python3.11 -m ariadne_ltb.cli review run ARI-003 --reviewer llm
FEISHU_ENABLE_WRITE=1 python3.11 -m ariadne_ltb.cli feishu write ARI-003 --confirm-write
python3.11 -m ariadne_ltb.cli github sync ARI-003 --confirm-write
python3.11 -m ariadne_ltb.cli ticket comments ARI-003
python3.11 -m ariadne_ltb.cli runtime journal
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli evidence packet --require-acceptance-ready
```

This path proves:

```text
Source / Knowledge / Feedback
  -> Build Ticket
  -> Build Packet
  -> Assignment
  -> Daemon Worker
  -> Planner / Handoff
  -> Backend Execution
  -> Reviewer
  -> Memory / Feishu Preview or Gated Write / GitHub Evidence / Next Tickets
  -> Board
  -> Backlog update
```

## Backlog Update Rule

When new external knowledge or execution feedback arrives, Ariadne should update
the ticket set instead of rewriting a global goal object:

- add new tickets;
- change priority;
- split or merge work;
- mark work blocked;
- supersede obsolete tickets;
- create next-ticket artifacts with rationale.

## Direct Full-Loop Path

`ticket run` remains available for direct orchestration:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari ticket run ARI-003 --backend codex --runtime-profile production --confirm-execution
```

It performs the complete loop without requiring a separate daemon assignment
step. Agent Teammate Mode is preferred for product demonstrations because it
makes assignment, claim, comments, and runtime state visible.

## Offline Regression Fixture

Use this path only for automated tests, fixture validation, and no-credential
debugging:

```bash
ari ticket run ARI-003 --backend fake-codex
ari demo full
```

This path proves store and loop determinism, not production readiness.

## Real Codex / Claude Code Path

The real Codex and Claude Code paths are production paths and safety-gated:

```bash
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

Required boundaries:

- real Codex and Claude Code execution are off by default;
- both `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and `--confirm-execution` are
  required;
- Codex / Claude Code unavailable, not logged in, quota-limited, or gate missing
  must produce a blocked result;
- Ariadne must not silently fall back to fake-codex;
- Ariadne must not auto-commit, auto-push, auto-merge, or create PRs.

## Runtime Sequence

```mermaid
sequenceDiagram
  participant User
  participant CLI
  participant Store
  participant Daemon
  participant Agent
  participant Backend
  participant Reviewer
  participant Memory
  participant Board

  User->>CLI: ari ticket assign ARI-003 --to codex --runtime-profile production
  CLI->>Store: create TicketAssignment
  User->>CLI: ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
  CLI->>Daemon: start one local worker iteration
  Daemon->>Store: claim queued assignment
  Daemon->>Agent: run ticket through orchestrator
  Agent->>Store: write BuildPacket and handoff
  Agent->>Backend: execute handoff
  Backend-->>Agent: ExecutionResult + diff + tests
  Agent->>Reviewer: review execution result
  Reviewer-->>Agent: ReviewReport
  Agent->>Memory: write memory and Feishu preview plan
  Memory-->>Store: MemoryRecord + NextTickets
  Agent->>Board: export board
  Board-->>User: .ariadne/board/index.md
```

## Failure And Recovery Flow

```mermaid
flowchart TB
  Assignment["Queued Assignment"] --> Claim["Daemon Claims"]
  Claim --> Execute["Run Backend"]
  Execute -->|Success| Review["Review"]
  Execute -->|Blocked / Failed| Classify["FailureReason"]
  Classify --> Retryable{"Retryable?"}
  Retryable -->|"Yes"| Retry["Create Retry Assignment"]
  Retryable -->|"No"| Human["Needs Human Review"]
  Review --> Memory["Memory / Next Tickets"]
  Memory --> Backlog["Ticket Backlog Update"]
  Retry --> Assignment
```

## Visibility Surfaces

Runtime work must be visible through:

- `ari ticket comments <ticket>`;
- `ari runtime journal`;
- `ari runtime recover`;
- `ari daemon status`;
- `.ariadne/artifacts/<ticket_id>/`;
- `.ariadne/memory/`;
- `.ariadne/feishu_plans/`;
- `.ariadne/board/index.md`.
