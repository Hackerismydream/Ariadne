# Ariadne v1.0 Demo Script

## Path

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari runtime journal
ari export board
ari board serve
```

## What The User Should See

`ari ingest examples/sources/*.md` creates Build Tickets from Markdown source notes and deterministic Build Packets.

`ari ticket list` shows visible work items such as `ARI-003`.

`ari ticket assign ARI-003 --to fake-codex` creates a queued assignment for the local Agent teammate.

`ari daemon run-once` claims the assignment, writes heartbeat and progress events, runs planner, backend, reviewer, memory, Feishu dry-run, next tickets, and board export.

`ari ticket comments ARI-003` shows assignment, handoff, progress, review, memory, and blocker comments.

`ari runtime journal` shows append-only runtime events for assignment claim, execution, handoff, review, memory, retry, and board stages.

`ari export board` writes `.ariadne/board/index.md` and `.ariadne/board/index.html`.

`ari board serve` serves the local read-only board with Python's standard HTTP server.

## Demo Message

Ariadne v1.0 is a local workbench that turns external knowledge into executable Build Tickets, assigns those tickets to Agent teammates, supervises the local daemon loop, captures execution evidence, reviews outcomes, writes memory, and makes the full process inspectable on a local board.
