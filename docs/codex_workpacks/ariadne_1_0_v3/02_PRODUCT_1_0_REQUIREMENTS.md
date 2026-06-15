# 02 — Ariadne 1.0 Product Requirements

## Product definition

Ariadne is a ticket-driven multi-agent workbench for AI builders.

It turns external learning inputs into coding-agent-executable project iterations.

## Target users

- AI builders building personal or open-source projects.
- Students preparing for agent-development roles.
- Developers using Codex, Claude Code, Cursor, or Copilot who need better task context, planning, review, and memory.

## Core objects

- **Project Space**: the current project, target repo, source inbox, local knowledge, Feishu workspace reference, skills, and run history.
- **Build Ticket**: visible work carrier. Similar to an issue/work item.
- **Build Packet**: structured knowledge-to-build object inside a ticket.
- **Agent Run**: one agent's execution attempt against a ticket.
- **Artifact**: durable output: source summary, packet, plan, handoff, execution log, diff, review report, memory write plan, board page.
- **Execution Result**: backend output including command, stdout, stderr, exit code, changed files, git diff, test output.
- **Memory Record**: local and optional Feishu write-back payload.

## Required source types

1. Local markdown notes.
2. Paper-style notes, including title, claims, method, project implications.
3. Blog/architecture notes.
4. GitHub repo/README notes. For 1.0, URL fetching is optional; local pasted README text is required.

## Required 1.0 capabilities

### Capability A — External input to Build Ticket

Ariadne can ingest several source files and create Build Tickets.

Required command:

```bash
ari ingest examples/sources/*.md
```

Fallback:

```bash
python -m ariadne_ltb.cli ingest examples/sources/*.md
```

### Capability B — Project-aware Build Packet generation

Ariadne reads the current Project Space and target repo context, then classifies each input as:

- archive;
- watchlist;
- doc update;
- experiment;
- code task;
- architecture change;
- reject for now.

For code_task packets, evidence and acceptance criteria are mandatory.

### Capability C — Planning and coding-agent handoff

Ariadne produces a handoff prompt with:

- goal;
- source evidence;
- relevant target repo files;
- constraints;
- implementation steps;
- acceptance criteria;
- test command;
- allowed file scope.

### Capability D — Execution backend

Ariadne supports:

- DryRunBackend: no writes;
- ShellBackend: safe local command execution with explicit `--confirm-execution`;
- FakeCodexBackend: deterministic code-writing simulation for demo tests;
- optional CodexBackend: calls installed `codex` command only if available and confirmed;
- optional ClaudeCodeBackend: can be scaffolded but not required to pass tests.

### Capability E — Git diff and test capture

Ariadne captures:

- git status before/after;
- head SHA if available;
- changed files;
- git diff;
- stdout/stderr/exit code;
- test command and test output.

If the target project is not a git repo, Ariadne should initialize git for the demo target project or degrade gracefully for user projects.

### Capability F — Reviewer Agent

Reviewer checks:

- packet evidence exists;
- acceptance criteria exist;
- execution completed;
- exit code is 0;
- tests passed;
- changed files are within allowed scope;
- diff is captured;
- Feishu writes are dry-run unless explicitly confirmed;
- all runs are terminal.

### Capability G — Memory write-back

Ariadne writes local memory:

- ticket summary;
- final Build Packet;
- decision log entry;
- review report;
- execution summary;
- next tickets.

Ariadne generates Feishu dry-run write plans. Optional real Feishu write is allowed only when credentials exist and `--confirm-feishu-write` is provided.

### Capability H — Board visibility

Ariadne shows the full loop:

- ticket cards by status;
- source type;
- latest agent;
- run timeline;
- execution backend;
- exit code;
- test result;
- changed files;
- review verdict;
- memory/Feishu write plan.

Static Markdown/HTML board is required. A local FastAPI read-only board is recommended but optional if time is tight.

## 1.0 CLI surface

Required:

```bash
ari demo full
ari ingest <paths...>
ari ticket list
ari ticket show <ticket_id_or_key>
ari ticket run <ticket_id_or_key>
ari ticket execute <ticket_id_or_key> --backend dry-run|fake-codex|shell|codex
ari ticket review <ticket_id_or_key>
ari memory export <ticket_id_or_key>
ari export board
```

Recommended:

```bash
ari board serve
```

## 1.0 demo target project

Ariadne must create a demo target project under:

```text
.ariadne/demo_target_project/
```

The target project should be a small Python package, for example `tasklet` or `demo_todo`, with tests. The execution backend must implement a small feature derived from the Build Packet, run tests, and capture diff.
