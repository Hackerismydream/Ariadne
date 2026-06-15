# Ariadne v1.0 Human Demo Script

## Three Minute Path

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

## Talk Track

Ariadne turns external knowledge into Build Tickets, assigns a Ticket to an Agent teammate, lets a local daemon claim the work, captures execution and review evidence, writes memory, generates next tickets, and shows the whole process on a local board.

## What To Point At

- Ticket assignment proves the work is visible before execution.
- Comments prove the Agent reports progress.
- Runtime journal proves the local worker is auditable.
- Board proves the full loop can be reviewed without reading JSON files.
