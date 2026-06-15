# Codex Master Prompt — Ariadne True MVP Productization

You are Codex working on Ariadne after PR #2 has been merged.

Your task is to complete the true Ariadne MVP. Do not produce another demo-only pass.

Read all markdown files in this workpack before coding:

```text
00_START_HERE.md
01_CURRENT_STATE_AND_GAP.md
02_TRUE_MVP_DEFINITION.md
03_ARCHITECTURE_TARGET.md
04_TICKET_RUN_ORCHESTRATOR.md
05_AGENT_UPSTREAM_PLANNER.md
06_EXECUTION_BACKENDS.md
07_REVIEW_MEMORY_NEXT_TICKETS.md
08_CLI_BOARD_UX.md
09_TEST_AND_ACCEPTANCE.md
10_SECURITY_ENV.md
```

## Non-negotiable mission

Turn Ariadne from a demo harness into a reusable local Learning-to-Build workbench.

The common path must work:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket run ARI-003 --backend fake-codex
ari export board
```

Fallback must work:

```bash
python -m ariadne_ltb.cli ingest examples/sources/*.md
python -m ariadne_ltb.cli ticket list
python -m ariadne_ltb.cli ticket run ARI-003 --backend fake-codex
python -m ariadne_ltb.cli export board
```

`ticket run` must perform the complete loop:

```text
load ticket
  -> plan / create Build Packet if needed
  -> write handoff artifact
  -> execute backend
  -> capture stdout/stderr/exit code
  -> capture git diff and changed files
  -> run tests
  -> review
  -> update ticket status
  -> write memory
  -> generate Feishu dry-run plan
  -> generate next tickets
  -> export board
```

## Stop conditions

Do not stop after:

- only editing docs;
- only adding scaffolds;
- only making `demo full` work;
- only adding tests around existing behavior;
- only adding another fake backend.

You must implement the reusable ticket-run product workflow.

## Required implementation

### 1. Extract reusable orchestrator

Create `ariadne_ltb/orchestrator.py`.

Implement `TicketRunOrchestrator`.

`demo full` must call this orchestrator instead of owning a separate full-loop implementation.

### 2. Make `ticket run` the main product path

Update CLI so:

```bash
ari ticket run <ticket_id_or_key> --backend fake-codex
```

runs the whole loop.

Low-level `execute`, `review`, and `memory` commands may remain, but they are not the common path.

### 3. Add planner interface

Create or update planner layer.

Required:

```text
DeterministicPlanner
LLMPlanner
```

Default is deterministic.

LLM planner must use the existing optional LLM client. If no key is present, it must fail gracefully and save an error/blocked artifact.

### 4. Upgrade FakeCodexBackend

FakeCodexBackend must:

- read the handoff/task;
- require that it mentions `export-json`;
- require allowed paths to include `demo_todo/cli.py` and `tests/test_cli.py`;
- block instead of patching when requirements are not met;
- still modify the demo target project successfully for the valid demo ticket.

### 5. Upgrade CodexBackend and ClaudeCodeBackend scaffolds

CodexBackend must:

- write handoff file under `.ariadne/handoffs/`;
- render command from `ARIADNE_CODEX_COMMAND_TEMPLATE`;
- support placeholders `{target_repo}`, `{handoff_file}`, `{ticket_id}`, `{ticket_key}`;
- require `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and `--confirm-execution`;
- return blocked result if disabled or unavailable;
- capture stdout/stderr/exit/diff/tests;
- never commit/push/merge/PR.

ClaudeCodeBackend must follow the same pattern with `ARIADNE_CLAUDE_COMMAND_TEMPLATE`.

Tests must not require either tool installed.

### 6. Generate next tickets

After review/memory, generate next ticket suggestions as an artifact:

```text
next_tickets.json
```

or:

```text
next_tickets.md
```

This is required because Ariadne's loop is review -> next Build Tickets -> next Codex iteration.

### 7. Upgrade board

Board must clearly show:

```text
Source -> Ticket -> Packet -> Handoff -> Backend -> Diff -> Tests -> Review -> Memory -> Feishu Plan -> Next Tickets
```

### 8. Update README and development report

The docs must explain the true MVP path, not just `demo full`.

## Required tests

Add or update tests for:

- `TicketRunOrchestrator` full loop;
- `demo full` uses orchestrator;
- `ticket run <key> --backend fake-codex` completes review + memory + board;
- FakeCodexBackend blocked path;
- CodexBackend disabled path;
- CodexBackend command-template rendering;
- ClaudeCodeBackend disabled path;
- deterministic planner;
- LLM planner missing-key graceful failure;
- arbitrary markdown evidence extraction;
- next tickets artifact;
- board Loop Trace.

Tests must not require network, Codex, Claude, DeepSeek, Feishu, or GitHub token.

## Required commands

Run:

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
```

If available, also run:

```bash
uv run ari ingest examples/sources/*.md
uv run ari ticket list
uv run ari ticket run ARI-003 --backend fake-codex
uv run ari export board
```

## Autonomy protocol

Do not ask the user for clarification unless the task is impossible.

When uncertain:

1. make a conservative local-first decision;
2. document it;
3. continue.

Prioritize the reusable product loop over UI polish.

## Final response

Report:

1. files changed;
2. commands run;
3. test results;
4. whether `ticket run` now completes the full loop;
5. whether `demo full` uses orchestrator;
6. board path;
7. memory path;
8. Feishu dry-run plan path;
9. next tickets path;
10. status of CodexBackend / ClaudeCodeBackend scaffolds;
11. known limitations.
