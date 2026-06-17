# Ariadne v1.0 Human Demo Script

## Production Path

```bash
ari doctor integrations
ari doctor product --require-acceptance-ready
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
ari board serve
```

## Deterministic Fallback

Use this only when demonstrating the offline regression loop:

```bash
ari ingest examples/sources/*.md
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari export board
```

## Talk Track

Ariadne turns external knowledge into Build Tickets, assigns a Ticket to an Agent teammate, lets a local daemon claim the work, captures execution and review evidence, writes memory, generates next tickets, and shows the whole process on a local board.

The production demo uses real, gated Codex / DeepSeek / Feishu / GitHub evidence
when those credentials and confirmations are available. The fake-codex path is
only the deterministic fallback for local regression.

## What To Point At

- Ticket assignment proves the work is visible before execution.
- Comments prove the Agent reports progress.
- Runtime journal proves the local worker is auditable.
- Board proves the full loop can be reviewed without reading JSON files.
