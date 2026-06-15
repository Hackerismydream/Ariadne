# Ariadne

Ariadne turns external knowledge into local software iterations for coding
agents. It is a single-user, local-first Learning-to-Build workbench: ingest
Markdown sources, create Build Tickets and Build Packets, hand a selected ticket
to a backend, capture the result, review it, write memory, generate next ticket
suggestions, and export a static board.

Repository name: `ariadne-ltb`. Python package: `ariadne_ltb`. CLI target:
`ari`. Fallback CLI: `python -m ariadne_ltb.cli`.

## True MVP Path

The recommended product path is Agent Teammate Mode:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari export board
```

In this mode, a human assigns a Build Ticket to an Agent teammate, the local
daemon claims one assignment, the Agent runs the ticket through Ariadne's full
loop, writes comments and journal events, and updates the board.

The direct ticket-run path remains available:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket run ARI-003 --backend fake-codex
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

`ticket run` performs the complete loop:

```text
Source -> Ticket -> Packet -> Handoff -> Backend -> Diff -> Tests -> Review -> Memory -> Feishu Plan -> Next Tickets
```

Generated outputs are under `.ariadne/`, including:

```text
.ariadne/artifacts/<ticket_id>/
.ariadne/assignments/
.ariadne/comments/
.ariadne/journal/events.jsonl
.ariadne/memory/
.ariadne/feishu_plans/
.ariadne/board/index.md
.ariadne/board/index.html
```

## Agent Teammate Mode

Agent Teammate Mode adds a small local work-management layer:

- `ari agent list` shows assignable local Agent profiles.
- `ari ticket assign <ticket> --to fake-codex` creates a queued assignment.
- `ari daemon run-once` claims one assignment and runs it through
  `TicketRunOrchestrator`.
- `ari ticket comments <ticket>` shows human comments, agent progress, blocker,
  review, memory, and recovery comments.
- `ari runtime journal` shows append-only runtime events.
- `ari runtime recover` prints conservative resume plans.
- `ari runtime locks` shows local directory locks and stale-lock warnings.

`ari daemon start` is a simple polling loop for local use:

```bash
ari daemon start --interval 2 --max-iterations 3
```

It is not a system service, and it does not introduce auth, networking,
PostgreSQL, or WebSockets.

## Demo

`ari demo full` remains available, but it is now a wrapper around the reusable
`TicketRunOrchestrator`. It ensures the demo target project exists, ingests the
fixture sources, selects the code-task ticket, and calls the same full-loop path
as `ari ticket run`.

```bash
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
```

## Planning

Default planning is deterministic and requires no credentials:

```bash
ari ticket plan ARI-003 --planner deterministic
```

Optional LLM planning uses DeepSeek when `DEEPSEEK_API_KEY` is present:

```bash
DEEPSEEK_API_KEY=... ari ticket plan ARI-003 --planner llm
```

If the key is missing, Ariadne writes a blocked planner artifact and exits
gracefully. Tests do not require network access or a DeepSeek key.

## Execution Backends

- `fake-codex`: deterministic local simulator. It only patches the demo target
  when the handoff mentions `export-json` and allowed paths include
  `demo_todo/cli.py` and `tests/test_cli.py`.
- `dry-run`: records an execution result without changing files.
- `shell`: low-level command backend, requires `--confirm-execution`.
- `codex`: gated Codex CLI adapter scaffold.
- `claude-code`: gated Claude Code adapter scaffold.

Real external execution requires both:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

Codex command template:

```bash
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec --cd {target_repo} --prompt-file {handoff_file}'
```

Claude command template:

```bash
ARIADNE_CLAUDE_COMMAND_TEMPLATE='claude --print < {handoff_file}'
```

Supported placeholders are `{target_repo}`, `{handoff_file}`, `{ticket_id}`,
and `{ticket_key}`.

## Real CodexBackend Smoke Test

The default demo uses `FakeCodexBackend`. Real `CodexBackend` execution is
optional, local, safety-gated, and never auto-commits.

Run diagnostics:

```bash
ari backend doctor
```

The full smoke-test runbook is in
[`docs/real_codex_smoke_test.md`](docs/real_codex_smoke_test.md).

## Multica Architecture Alignment

ARI-005 aligns Ariadne's local kernel with selected Multica work-management
concepts without copying Multica's server architecture.

New local foundations:

- `AgentRun.lifecycle_state`
- typed `FailureReason`
- runtime capability snapshots under `.ariadne/runtimes/`
- project resource snapshots under `.ariadne/project/resources.json`
- target repo path validation and directory locking
- local BuildSkill packs under `.skills/`
- `route_decision.json` artifacts
- progress events in the ticket timeline
- board sections for runtime, resources, route, skills, and progress

Architecture notes:

- [`docs/architecture/multica_architecture_digest.md`](docs/architecture/multica_architecture_digest.md)
- [`docs/architecture/ariadne_multica_gap_report.md`](docs/architecture/ariadne_multica_gap_report.md)
- [`docs/adr/ADR-0002-multica-architecture-alignment.md`](docs/adr/ADR-0002-multica-architecture-alignment.md)
- [`docs/adr/ADR-0003-agent-teammate-mode.md`](docs/adr/ADR-0003-agent-teammate-mode.md)

## Feishu

The default loop writes a Feishu dry-run plan only. Real writes use `lark-cli`
and require both:

```bash
FEISHU_ENABLE_WRITE=1
--confirm-write
```

No Feishu credentials are required for tests or the default demo.

## Safety

- No auto-commit, auto-push, auto-merge, or PR creation from Ariadne runtime.
- No network is required for tests.
- External execution is blocked unless explicitly enabled and confirmed.
- Feishu writes are dry-run unless explicitly enabled and confirmed.
- `.env`, `.env.*`, `*.secret`, `secrets/`, and `.ariadne/` are gitignored.

## Verification

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
```
