# Ariadne True MVP Workpack v4 — Start Here

This workpack is for the next Codex pass after PR #2 has been merged into `main`.

The prior work produced a strong **demo chain**, but the product is not yet the true MVP. The next pass must convert the demo chain into a reusable local product loop.

## Non-negotiable goal

Ariadne must become a reusable Learning-to-Build workbench:

```text
ingest sources
  -> create Build Tickets
  -> create / update Build Packets
  -> plan coding handoff
  -> run a selected ticket through a backend
  -> capture logs / diff / tests
  -> review
  -> write memory
  -> generate next Build Tickets
  -> export board
```

The common user path must be:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket run ARI-003 --backend fake-codex
ari export board
```

This path must complete the whole loop. The user must not manually chain `execute`, `review`, `memory export`, and `export board` for the normal case.

## Current problem

PR #2 implemented `demo full`, but the full loop is still concentrated in demo-specific code. It is a strong demo harness, not yet a reusable MVP product.

This pass must productize it.

## The key distinction

Wrong target:

```text
ari demo full works on fixed fixtures
```

Correct target:

```text
ari ticket run <ticket> --backend <backend> works for real ingested tickets
```

## Quality bar

Do not stop after writing documentation or scaffolds. Implement the reusable loop and make tests pass.

If the implementation cannot use real Codex / Claude Code in tests, that is fine. But the adapter scaffolds must be structurally correct, gated, and testable without external tools.
