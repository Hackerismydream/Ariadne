# Current State and Gaps After PR #2

## What PR #2 has

PR #2 added:

- source fixtures;
- source ingestion;
- Build Tickets and Build Packets;
- `.ariadne/demo_target_project/`;
- `FakeCodexBackend`;
- execution result capture;
- git diff / changed files / test output;
- reviewer;
- local memory write-back;
- Feishu dry-run plan;
- Markdown / HTML board;
- optional DeepSeek client;
- guarded Feishu scaffold.

This is valuable.

## Why it is still not enough

The full chain is still mostly a fixed demo path.

The product needs the full chain to be reusable from a normal ticket workflow.

## Required upgrade

Convert from:

```text
demo-specific orchestration
```

to:

```text
ticket-run orchestration
```

The product API should be centered on:

```text
TicketRunOrchestrator
PlannerBackend
ExecutionBackend
Reviewer
MemoryWriter
NextTicketGenerator
BoardExporter
```

## Main gap list

### Gap 1 — `demo full` owns the best workflow

`demo full` should become a wrapper around reusable ticket orchestration.

### Gap 2 — `ticket run` is not the main loop

`ticket run <ticket>` must become the main command that executes plan -> backend -> review -> memory -> board.

### Gap 3 — FakeCodexBackend is too hard-coded

It currently patches the target project unconditionally. It must validate the handoff/task and allowed paths before changing files.

### Gap 4 — CodexBackend and ClaudeCodeBackend are only thin scaffolds

They need command-template rendering, handoff prompt files, gating, blocked results, and tests for disabled paths.

### Gap 5 — LLM / DeepSeek is not integrated

`DeepSeekClient` exists, but the planning path is still deterministic-only in practice. Add a planner interface with deterministic default and optional LLM planner.

### Gap 6 — Review does not generate next tickets as a product artifact

The loop should produce next Build Tickets from review/memory. That is the self-building story.

## Target outcome

After this pass, the README should truthfully say:

```text
Ariadne 1.0 can ingest sources, create tickets, run a ticket through a backend, review the result, write memory, generate next tickets, and export the board.
```
