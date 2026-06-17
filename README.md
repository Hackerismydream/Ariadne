# Ariadne

Ariadne turns external knowledge into local software iterations for coding
agents. It is a single-user, local-first Learning-to-Build workbench: ingest
Markdown sources, create Build Tickets and Build Packets, hand a selected ticket
to a backend, capture the result, review it, write memory, generate next ticket
suggestions, and export a static board.

Repository name: `ariadne-ltb`. Python package: `ariadne_ltb`. CLI target:
`ari`. Fallback CLI: `python -m ariadne_ltb.cli`.

## Ariadne v1.0 Quickstart

Ariadne v1.0 is a local-first, Ticket-centered Agent Workbench:

```bash
ari ingest examples/sources/*.md
ari backlog history
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari runtime journal
ari runtime recover
ari export board
ari board serve
```

This path shows the full local loop:

```text
Source -> Ticket -> Assignment -> Daemon -> Planner -> Backend -> Review -> Memory -> Board
```

Ticket backlog updates are persisted under `.ariadne/backlog/updates.jsonl` and
shown on the board. The explicit backlog commands are:

```bash
ari backlog update --from-source examples/sources/*.md
ari backlog history
ari ticket supersede ARI-003 --reason "Replaced by narrower follow-up work"
```

## Production Product Path

The recommended product path is the real, gated Agent Teammate Mode:

```bash
ari doctor integrations
ari doctor product
ari ingest examples/sources/*.md --planner llm
ari ticket list
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
ari review run ARI-003 --reviewer llm
FEISHU_ENABLE_WRITE=1 ari feishu write ARI-003 --confirm-write
ari github sync ARI-003 --confirm-write
ari ticket comments ARI-003
ari export board
ari evidence packet
```

In this mode, a human assigns a Build Ticket to an Agent teammate, the local
daemon claims one assignment, the Agent runs the ticket through Ariadne's full
loop, writes comments and journal events, and updates the board.

Real writes and external coding execution remain gated. `ari doctor product`
summarizes which parts of the production path are ready, blocked, or waiting
for an explicit execution/write gate.

The deterministic offline fallback remains available for tests and local
regression checks:

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

Serve the generated local board:

```bash
ari board serve
```

`ticket run` performs the complete loop:

```text
Source -> Ticket -> Packet -> Handoff -> Backend -> Diff -> Tests -> Review -> Memory -> Feishu Plan -> Next Tickets
```

Generated outputs are under `.ariadne/`, including:

```text
.ariadne/artifacts/<ticket_id>/
.ariadne/assignments/
.ariadne/backlog/updates.jsonl
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

Planning can optionally cite prior local memory records. This stays local and
deterministic; it uses keyword search over `.ariadne/memory/tickets/*.json`, not
a vector database or network service:

```bash
ari memory search "planner memory retrieval"
ari ticket plan ARI-003 --planner deterministic --use-memory
ari ticket run ARI-003 --backend fake-codex --use-memory
```

When enabled, planner artifacts include memory evidence with source refs, and
the handoff plus board show a `Memory Context` / `Planner Memory Evidence`
section.

## Review Evidence

Review reports include the conservative verdict plus structured acceptance
evidence:

```bash
ari review run ARI-003
ari review run ARI-003 --reviewer llm
```

Reports record reviewer mode, risk score, acceptance-criterion coverage,
evidence refs, failed checks, required fixes, and next-ticket suggestions. The
board shows the same review evidence for executed tickets.

## Upstream LLM Runtime

Ariadne uses DeepSeek as the default upstream LLM runtime for non-coding agent
roles such as planning and review. Credentials are read from environment or an
ignored local `.env`; doctor commands report only set/unset state and never
print key values.

```bash
ari llm doctor
ari ticket plan ARI-003 --planner llm
ari review run ARI-003 --reviewer llm
```

Real LLM smoke tests are explicit external calls:

```bash
ari llm smoke --provider deepseek --confirm-external
```

If the key is missing, Ariadne writes blocked evidence and exits gracefully.
Tests use fake transports and do not require network access or a DeepSeek key.

## Execution Backends

- `fake-codex`: deterministic local simulator. It only patches the demo target
  when the handoff mentions `export-json` and allowed paths include
  `demo_todo/cli.py` and `tests/test_cli.py`.
- `dry-run`: records an execution result without changing files.
- `shell`: low-level command backend, requires `--confirm-execution`.
- `codex`: gated Codex CLI production backend.
- `claude-code`: gated Claude Code production backend.

Real external execution requires both:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

Codex command template:

```bash
ARIADNE_CODEX_COMMAND_TEMPLATE='codex exec --cd {target_repo} - < {handoff_file}'
```

Claude command template:

```bash
ARIADNE_CLAUDE_COMMAND_TEMPLATE='claude --print --output-format json < {handoff_file}'
```

Supported placeholders are `{target_repo}`, `{handoff_file}`, `{ticket_id}`,
`{ticket_key}`, `{assignment_id}`, `{run_id}`, `{model}`,
`{reasoning_effort}`, `{effort}`, `{service_tier}`, `{max_turns}`,
`{system_prompt}`, and `{system_prompt_file}`.

## Real CodexBackend Smoke Test

The default demo uses `FakeCodexBackend`. Real `CodexBackend` execution is
optional, local, safety-gated, and never auto-commits.

Run diagnostics:

```bash
ari backend doctor
```

Inspect the provider capability matrix used by routing and the board:

```bash
ari backend matrix
```

The matrix records prompt-file/stdin support, skill materialization, timeout,
diff/test capture, command availability, safety gates, and command-template
presence without printing secrets.

Diagnose Codex CLI command/template compatibility:

```bash
ari backend diagnose codex
```

Run the first-class real Codex demo path only when explicitly gated:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ari demo codex --confirm-execution --timeout-seconds 180
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

## Ariadne v1.0 Architecture

Ariadne v1.0 is frozen as a local-first Ticket-centered Agent Workbench:

```text
Knowledge / Feedback / Codebase
  -> Ticket Backlog Update
  -> Ticket Assignment
  -> Agent Run
  -> Review / Memory / Board
  -> Ticket Backlog Update
```

Multica is the fixed benchmark for agent work management. Multica lets agents
work issues. Ariadne lets knowledge and feedback update tickets, then lets
agents work tickets. Ariadne keeps a local-first Python architecture with
JSON/JSONL storage, CLI commands, static/local board output, and explicit safety
gates for Codex, Claude, and Feishu.

Architecture entrypoints:

- [`docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md`](docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md)
- [`docs/architecture/ARIADNE_V1_ARCHITECTURE.md`](docs/architecture/ARIADNE_V1_ARCHITECTURE.md)
- [`docs/architecture/ARIADNE_V1_OBJECT_MODEL.md`](docs/architecture/ARIADNE_V1_OBJECT_MODEL.md)
- [`docs/architecture/ARIADNE_V1_RUNTIME_FLOW.md`](docs/architecture/ARIADNE_V1_RUNTIME_FLOW.md)
- [`docs/architecture/ARIADNE_V1_MULTICA_MAPPING.md`](docs/architecture/ARIADNE_V1_MULTICA_MAPPING.md)
- [`docs/demo/ARIADNE_V1_DEMO_CONTRACT.md`](docs/demo/ARIADNE_V1_DEMO_CONTRACT.md)
- [`docs/adr/ADR-0004-ticket-centered-agent-workbench.md`](docs/adr/ADR-0004-ticket-centered-agent-workbench.md)

Main local demo path:

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari export board
```

Real Codex path remains optional and gated:

```bash
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

## Capability Surface Freeze

Ariadne v1.x is frozen around the product surface:

```text
Ticket-centered Agent Workbench
```

The capability-surface entrypoint is
[`docs/capability_surface/ARIADNE_CAPABILITY_SURFACE.md`](docs/capability_surface/ARIADNE_CAPABILITY_SURFACE.md).
It fixes the Multica benchmark surface, Ariadne's current coverage, remaining
gaps, and the ARI-015 through ARI-025 roadmap.

## Feishu

The default loop writes a Feishu dry-run plan. Real writes use `lark-cli`,
persist an integration result under `.ariadne/integrations/feishu/<ticket>/`,
and require both:

```bash
python3.11 -m ariadne_ltb.cli feishu plan ARI-003
FEISHU_ENABLE_WRITE=1 python3.11 -m ariadne_ltb.cli feishu write ARI-003 --confirm-write
```

No Feishu credentials are required for tests or the default demo. Missing
confirmation, disabled writes, missing `lark-cli`, login failures, and provider
errors are recorded as blocked/failed write results with secrets redacted.

## Workbench Frontend

The local workbench frontend lives under `frontend/ariadne-workbench/`. It is a
read-only React/Vite frontend that adapts Multica's issue-agent-runtime UI shape
to Ariadne's ticket-centered product loop. It does not call Multica APIs and it
does not mutate Ariadne state.

Generate a local data snapshot from `.ariadne/` and run the frontend:

```bash
cd frontend/ariadne-workbench
npm install
npm run sync:data
npm run dev
```

Build static assets:

```bash
npm run build
```

`npm run sync:data` writes `public/web_data/workbench.json` from local tickets,
runtime capability, project resources, inbox items, Feishu/GitHub integration
results, release evidence, and progress events. That generated file is ignored
because it contains machine-local paths.

## GitHub

GitHub integration uses the local `gh` CLI and environment-only credentials.
Tickets can create controlled remote issues, link to existing issues/PRs, then
sync with explicit write confirmation:

```bash
python3.11 -m ariadne_ltb.cli github doctor
python3.11 -m ariadne_ltb.cli github create-issue ARI-003 --repo Hackerismydream/Ariadne --confirm-write
python3.11 -m ariadne_ltb.cli github link ARI-003 --repo Hackerismydream/Ariadne --issue 123
python3.11 -m ariadne_ltb.cli github sync ARI-003 --confirm-write
python3.11 -m ariadne_ltb.cli github create-pr ARI-003 --base main --head codex/my-branch --confirm-write
python3.11 -m ariadne_ltb.cli github status ARI-003
```

Issue creation, PR creation, and sync comments write only through `gh` and only
with `--confirm-write`. Status reads issue, PR, branch, and check information
without remote writes. Results are persisted under
`.ariadne/integrations/github/<ticket>/` with tokens redacted.

## Inbox And Local Search

Real integration failures are materialized into a local inbox so blocked work is
visible instead of buried in command output:

```bash
ari inbox refresh
ari inbox list --refresh
```

Inbox items are persisted under `.ariadne/inbox/items.json` and include source
type, ticket key, typed failure reason, severity, evidence ref, and a suggested
recovery action.

Ariadne also includes local lexical search over the workbench evidence:

```bash
ari search "auth quota" --output json
```

Search indexes tickets, comments, artifacts, reviews, execution results,
memory records, inbox items, Feishu results, and GitHub results. It is local
only and does not require network access or credentials.

## Release Evidence And Workdirs

Generate a local release evidence packet from the current Ariadne store:

```bash
ari doctor product
ari evidence packet
ari evidence packet --output json
```

The packet is written to `.ariadne/evidence/release_evidence_packet.json` and
summarizes tickets, assignments, executions, reviews, memory, inbox items,
runtime capabilities, store invariants, secret scan status, board path, and
managed workdirs. `ari doctor product` writes
`.ariadne/doctor/product_readiness.json` with production-path readiness checks
and next actions.

List and clean Ariadne-generated isolated workdirs:

```bash
ari workdir list
ari workdir cleanup --confirm-cleanup
```

Cleanup only targets workdirs under `.ariadne/worktrees`. Dirty generated
workdirs are skipped unless `--force-dirty` is explicitly supplied.

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

## v1.0 Limitations

- Local single-worker runtime, not a production multi-worker scheduler.
- JSON/JSONL persistence, not Postgres or a hosted database.
- No production Web UI, WebSocket layer, auth, or permissions system.
- Real Codex execution depends on the local Codex CLI and remains default-off.
- Feishu real writes are default-off; the product writes dry-run plans by default.
