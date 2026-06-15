# ADR-0003: Agent Teammate Mode

Status: Accepted

Date: 2026-06-15

## Context

Ariadne's True MVP can run a Build Ticket through planning, backend execution,
review, memory, Feishu dry-run, next-ticket generation, and board export. That
loop works, but the user still drives it as a command flow.

ARI-006 changes the interaction model:

```text
human assigns ticket -> local daemon claims assignment -> agent reports progress -> full loop runs
```

The goal is teammate behavior, not a Multica clone.

## Decision

Ariadne will add five local-first work-management layers:

- Agent Registry
- Ticket Assignments
- Ticket Comments
- Local Daemon Worker
- Runtime Journal and conservative recovery plans

The local daemon MVP centers on `run-once`. It is deterministic, testable, and
safe for a single-user local workbench. `daemon start` is only a simple polling
loop over `run-once`.

## Rationale

Assignments make ownership visible. Without them, a ticket run is just an
imperative command.

Daemon Worker makes Ariadne feel like a teammate: the agent claims queued work,
reports progress, executes through `TicketRunOrchestrator`, and records the
result.

Comments make progress legible to the user without requiring them to inspect
every artifact JSON file.

Runtime Journal gives Ariadne an append-only record of assignment, claim,
execution, review, memory, next-ticket, board, and recovery events. This is the
local foundation for future resume and retry work.

`run-once` is the right MVP boundary because it is deterministic, easy to test,
and avoids background process management.

## Multica Alignment

Absorbed:

- Agent as assignable teammate.
- Task/assignment lifecycle.
- Progress and blocker reporting.
- Runtime event journal.
- Local-directory lock visibility.
- Conservative recovery planning.

Not copied:

- Go server.
- PostgreSQL queue.
- WebSocket progress stream.
- Multi-workspace permissions.
- Cloud runtime management.
- Full daemon heartbeat protocol.

## Consequences

Positive:

- Users can assign tickets to agents and let the daemon claim work.
- Board now presents assignment, comments, journal, and worker state.
- Existing direct `ticket run` mode remains intact.
- Tests still require no network or external credentials.

Trade-offs:

- Recovery is conservative and does not implement complex session resume.
- `daemon start` is a polling loop, not a managed OS service.
- Assignments are JSON files, not a database-backed queue.

## Safety

Real Codex and Claude execution remain gated by:

```text
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

Ariadne still does not auto-commit, auto-push, merge, or create PRs during
runtime execution.
