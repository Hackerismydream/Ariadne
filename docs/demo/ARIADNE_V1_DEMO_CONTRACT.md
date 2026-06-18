# Ariadne v1.0 Walkthrough And Offline Fixture Contract

This document freezes the product walkthroughs and offline regression fixtures
Ariadne v1.0 should support and explain. Offline fixture runs are not
production acceptance evidence.

## Offline Fixture 1: Stable Local Loop

Command path:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari export board
```

Fallback:

```bash
python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md
python3.11 -m ariadne_ltb.cli ticket list
python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to fake-codex
python3.11 -m ariadne_ltb.cli daemon run-once
python3.11 -m ariadne_ltb.cli ticket comments ARI-003
python3.11 -m ariadne_ltb.cli export board
```

What this proves:

- external knowledge enters Ariadne;
- Ariadne creates Build Tickets and Build Packets;
- a task is assigned to an agent teammate;
- a daemon worker claims the assignment;
- the agent reports progress;
- execution produces diff, tests, and artifacts;
- Reviewer checks the result;
- Memory writes back the decision;
- Board shows the full process.

This is the deterministic offline regression fixture. It must not require
Codex, Claude, DeepSeek, Feishu credentials, GitHub tokens, or network access,
and it must not be treated as product acceptance.

## Product Walkthrough 2: Real Codex Path

Command path:

```bash
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

Recommended diagnostic first:

```bash
ari backend doctor
```

What this proves:

- Ariadne does not replace Codex;
- Ariadne prepares the handoff;
- Codex performs the coding work;
- Ariadne captures stdout, stderr, exit code, diff, changed files, and tests;
- Reviewer checks the result;
- Memory creates the next loop.

Safety boundaries:

- real Codex execution is default-off;
- no environment gate means blocked result;
- no `--confirm-execution` means blocked result;
- Codex unavailable means blocked result;
- Ariadne must not fallback to fake-codex;
- Ariadne must not auto-commit, auto-push, auto-merge, or create PRs.

## Product Walkthrough 3: Project Self-Bootstrap

Input review note:

```text
Ariadne 目前缺真实 Codex 主 demo、source intelligence、交互式 board。
```

Expected story:

```text
Review note
  -> Source ingestion / backlog update
  -> Build Tickets
  -> Assignments
  -> Agent execution
  -> Review
  -> Memory
  -> Next Tickets
```

What this proves:

- Ariadne can use project review to keep improving Ariadne itself;
- the system converts learning and critique into build work;
- the loop is ticket-centered, not only a backend execution demo;
- next tickets are first-class artifacts, not notes buried in a report.

## Product Explanation Script

Short explanation:

```text
Ariadne is a local-first Ticket-centered Agent Workbench. Knowledge, feedback,
codebase context, memory, and optional goals update Build Tickets. Ariadne then
assigns tickets to agent teammates, runs a local daemon, calls a production
coding backend when gates are satisfied, reviews the result, writes memory, and
exports the board.
```

Multica comparison:

```text
Multica starts from issues and makes agents work those issues.
Ariadne lets sources, memory, review feedback, repo context, and optional goals
update tickets, then coordinates agents around those tickets.
```

## Demo Outputs To Inspect

- `.ariadne/board/index.md`
- `.ariadne/comments/`
- `.ariadne/journal/events.jsonl`
- `.ariadne/artifacts/<ticket_id>/`
- `.ariadne/memory/`
- `.ariadne/feishu_plans/`

## v1.0 Non-Goals During Demo

Do not present Ariadne v1.0 as:

- a hosted platform;
- a production daemon fleet;
- a full Multica clone;
- a WebSocket collaboration product;
- an automatic merge bot;
- a real Feishu writer by default;
- a Codex replacement.

Present it as:

```text
local-first ticket-centered agent workbench
```
