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
ari ticket assign ARI-003 --to codex --runtime-profile production
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
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
ari ticket assign ARI-003 --to codex --runtime-profile production
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
ari review run ARI-003 --reviewer llm
FEISHU_ENABLE_WRITE=1 ari feishu write ARI-003 --confirm-write
ari github sync ARI-003 --confirm-write
ari ticket comments ARI-003
ari export board
ari evidence packet --require-acceptance-ready
```

In this mode, a human assigns a Build Ticket to an Agent teammate, the local
daemon claims one assignment, the Agent runs the ticket through Ariadne's full
loop, writes comments and journal events, and updates the board.

## Local API Control Plane

Ariadne now exposes the same local Agent Workbench loop through a FastAPI
control plane for the frontend. The API is local-only by default and uses the
same store, assignment queue, daemon, and orchestrator as the CLI.

```bash
python3.11 -m ariadne_ltb.cli api serve --host 127.0.0.1 --port 8766
```

For the browser product entrypoint, build the frontend once and serve the
Workbench, API, and WebSocket control plane from one local origin:

```bash
cd frontend/ariadne-workbench
npm install
npm run build
cd ../..
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

Register an explicit target repository before browser-triggered runs:

```bash
python3.11 -m ariadne_ltb.cli target-project register /absolute/path/to/repo --label "Target repo"
python3.11 -m ariadne_ltb.cli target-project list
```

For development hot reload, run the frontend separately:

```bash
cd frontend/ariadne-workbench
npm run dev
```

The browser product path is API-only. If `/api/workbench` is unavailable, the
UI shows a disconnected read-only state instead of silently treating snapshot
or fixture data as product evidence. Browser actions can create assignments,
dispatch a run request for the local daemon/runtime to claim, watch WebSocket
assignment events, and add comments. They do not send raw shell commands or
local filesystem paths; target paths stay server-side in
`.ariadne/project/resources.json`.

Each completed ticket run also writes a landing evidence packet under the
ticket artifact directory. The packet has JSON and Markdown forms and links the
execution log, diff, changed files, tests, review, memory, Feishu plan, next
tickets, and orchestrator result. It is the local evidence input for later
review and merge-gating work.

Evaluate that packet with the local landing gate before a human or confirmed
merge workflow treats the ticket as landable:

```bash
ari landing gate ARI-003
ari landing gate ARI-003 --require-ready
```

The gate writes `landing_gate_report.json`, updates the ticket progress events,
and performs no git merge, push, pull request, or remote write.

`ari evidence packet` and `ari doctor product` include this landing gate as a
local production-readiness check. A release packet without a ready landing gate
will tell you to run `ari landing gate <ticket>` before treating the work as
acceptance-ready.

For recovery-oriented automation, run one bounded supervisor pass:

```bash
ari supervisor run-once --output json
ari supervisor run-once --run-daemon --confirm-execution
ari supervisor loop --max-cycles 12 --interval-seconds 300 --output json
```

The default supervisor pass refreshes inbox evidence, creates repair tickets
from open inbox items, and dispatches those repair tickets to the production
Codex profile. It does not run the daemon unless `--run-daemon` is explicit, so
real Codex or Claude execution still requires the normal external execution
gate. `ari supervisor loop` repeats the same bounded pass, stops after an idle
cycle by default, and writes a compact report under `.ariadne/supervisor/`.

Real writes and external coding execution remain gated. `ari doctor product`
summarizes which parts of the production path are ready, blocked, or waiting
for an explicit execution/write gate. It reports production acceptance
separately from current run gates: the product can be acceptance-ready while
`ARIADNE_ENABLE_EXTERNAL_EXECUTION` and `FEISHU_ENABLE_WRITE` remain unset until
a confirmed real run.

Fallback:

```bash
python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md
python3.11 -m ariadne_ltb.cli ticket list
python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to codex --runtime-profile production
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 python3.11 -m ariadne_ltb.cli daemon run-once --confirm-execution
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
- `ari ticket assign <ticket> --to codex --runtime-profile production`
  creates a queued production assignment for the Codex teammate.
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

For deterministic regression tests or offline local development, use
`ari ticket assign <ticket> --to fake-codex`. That path is intentionally not
the production acceptance path.

## Offline Regression Fixture

`ari demo full` remains available only as an offline regression fixture and
fixture validation command. It is not the product path and it is not production
acceptance evidence. The product path is the ticket/assignment/daemon loop with
production runtime profiles and gated real backends.

```bash
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
```

## Planning

Offline fixture planning is deterministic and requires no credentials:

```bash
ari ticket plan ARI-003 --planner deterministic
```

Production runtime profiles use the LLM planner/agent runtime/backlog planner.
Planning can optionally cite prior local memory records. Memory search stays
local and deterministic; it uses keyword search over
`.ariadne/memory/tickets/*.json`, not a vector database or network service:

```bash
ari memory search "planner memory retrieval"
ari ticket plan ARI-003 --planner deterministic --use-memory
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari ticket run ARI-003 --backend codex --use-memory --confirm-execution
```

When enabled, planner artifacts include memory evidence with source refs, and
the handoff plus board show a `Memory Context` / `Planner Memory Evidence`
section.

Feedback-to-backlog updates can also use the DeepSeek-backed LLM backlog
planner. Ariadne still writes deterministic next-ticket suggestions first; when
`--runtime-profile production` or `--backlog-planner llm` succeeds, those LLM
suggestions become the input to the backlog update engine. If the key or
provider is unavailable, Ariadne records a blocked `llm_next_tickets_blocked.json`
artifact and keeps the deterministic fallback evidence visible.

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ari ticket run ARI-003 --backend codex --runtime-profile production --confirm-execution
```

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
ari llm run-agent build_lead --ticket ARI-003 --confirm-external
ari llm run-agent knowledge --ticket ARI-003 --confirm-external
ari llm run-agent memory --ticket ARI-003 --confirm-external
ari ticket plan ARI-003 --planner llm
ari review run ARI-003 --reviewer llm
ari llm proof --ticket ARI-003 --confirm-external
```

`ari llm proof` is the auditable one-command proof flow for DeepSeek-backed
upstream agents. It runs Build Lead, Knowledge, Memory, LLM planner, LLM
reviewer, and LLM backlog planning for one ticket, then writes a proof artifact.
The ticket must already have an execution result so reviewer/backlog evidence is
grounded in a real run rather than fabricated input.

The full ticket loop can also run upstream DeepSeek role agents directly:

```bash
ari ticket run ARI-003 --backend codex --runtime-profile production --confirm-execution
```

The daemon / assignment path can use the same upstream runtime. This keeps the
normal product flow ticket-centered instead of requiring manual role-agent calls:

```bash
ari ticket assign ARI-003 --to codex --runtime-profile production
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

`--runtime-profile production` sets the planner, upstream role agents, and
feedback backlog planner to `llm`. `daemon run-once` also accepts
`--runtime-profile`, `--agent-runtime`, and `--backlog-planner` as runtime
overrides for one worker pass.

Real LLM smoke tests are explicit external calls:

```bash
ari llm smoke --provider deepseek --confirm-external
```

If the key is missing, Ariadne writes blocked evidence and exits gracefully.
Tests use fake transports and do not require network access or a DeepSeek key.

## Execution Backends

- `codex`: gated Codex CLI production backend.
- `claude-code`: gated Claude Code production backend.
- `shell`: low-level confirmed command backend for local debugging.
- `fake-codex`: deterministic local simulator for automated tests, offline
  regression fixtures, and explicit debug runs only. It only patches the
  fixture target when the handoff mentions `export-json` and allowed paths
  include `demo_todo/cli.py` and `tests/test_cli.py`.
- `dry-run`: preview/safety/no-credential fallback that records an execution
  result without changing files. It is not production execution evidence.

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

## Real Backend Smoke Tests

Product backend smoke tests use real `CodexBackend` and `ClaudeCodeBackend`
when local credentials, CLI login, and safety gates are present. Offline
fixtures may use `FakeCodexBackend`, but those runs do not satisfy production
acceptance. Real backend execution is local, safety-gated, and never
auto-commits.

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

Diagnose Codex or Claude Code CLI command/template compatibility:

```bash
ari backend diagnose codex
ari backend diagnose claude-code
```

Run first-class real backend smoke tests only when explicitly gated. These use
the product path: source fixtures -> ticket -> assignment -> local daemon ->
backend execution -> review -> memory -> board.

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ari backend smoke-test codex --confirm-execution --timeout-seconds 180

ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ari backend smoke-test claude-code --confirm-execution --timeout-seconds 180
```

`ari backend smoke-test` defaults to the production runtime profile. Pass
`--runtime-profile deterministic` only for local regression fixtures or tests.

Each smoke run now writes first-class backend evidence under
`.ariadne/evidence/backend_smoke/<backend>/`. Product doctor and release
evidence read that artifact before falling back to legacy execution-result
inference.

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

Offline regression path:

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
ari ticket assign ARI-003 --to codex --runtime-profile production
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

Ticket runs write a Feishu preview plan. Real writes use `lark-cli`, persist an
integration result under `.ariadne/integrations/feishu/<ticket>/`, and require
both:

```bash
python3.11 -m ariadne_ltb.cli feishu plan ARI-003
FEISHU_ENABLE_WRITE=1 python3.11 -m ariadne_ltb.cli feishu write ARI-003 --confirm-write
```

No Feishu credentials are required for tests or offline regression fixtures.
Missing confirmation, disabled writes, missing `lark-cli`, login failures, and
provider errors are recorded as blocked/failed write results with secrets
redacted.

## Workbench Frontend

The local workbench frontend lives under `frontend/ariadne-workbench/`. It is a
React/Vite frontend for Ariadne's local API control plane. In API mode it can
assign tickets to product coding agents, trigger a local run, watch assignment
events, and add human comments back into the ticket timeline. It does not call
Multica APIs, and browser mutations are constrained to stable ids, enums,
idempotency keys, bounded timeouts, comment bodies, and server-issued
confirmation tokens.

Run the product Workbench:

```bash
cd frontend/ariadne-workbench
npm install
npm run build
cd ../..
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

For frontend development, keep the API on `127.0.0.1:8766` and use Vite:

```bash
python3.11 -m ariadne_ltb.cli api serve --host 127.0.0.1 --port 8766
cd frontend/ariadne-workbench
npm run dev
```

`npm run sync:data` still exists for explicit offline snapshot regression. Use
`?offline=1` or `VITE_ARIADNE_OFFLINE_FIXTURE=1` to view snapshot/fixture data.
Those modes are read-only and are not product-path evidence.

Build static assets:

```bash
npm run build
```

Verify the workbench frontend build and offline snapshot regression:

```bash
scripts/verify_workbench.sh
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
ari inbox recover --output json
ari inbox dispatch-repairs --to codex --runtime-profile production
```

Inbox items are persisted under `.ariadne/inbox/items.json` and include source
type, ticket key, typed failure reason, severity, evidence ref, and a suggested
recovery action.
`ari inbox recover` converts actionable open inbox items into repair Build
Tickets through the backlog preview/apply path. Use `--preview-only` to write
repair previews without mutating tickets, and `--include-acknowledged` to verify
that previously acknowledged failures still point at existing repair tickets.
`ari inbox dispatch-repairs` then assigns those repair tickets to an Agent
teammate. It defaults to the production Codex profile and skips repair tickets
that already have queued, claimed, or running assignments.

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
ari evidence packet --require-acceptance-ready
ari evidence packet --output json
```

The packet is written to `.ariadne/evidence/release_evidence_packet.json` and
summarizes tickets, assignments, executions, reviews, memory, inbox items,
runtime capabilities, store invariants, secret scan status, board path, and
managed workdirs. `ari doctor product` writes
`.ariadne/doctor/product_readiness.json` with production-path readiness checks
and next actions. The product doctor checks both local integration readiness and
recorded real-success evidence for LLM agents, Codex, Claude Code, Feishu, and
GitHub. LLM agent acceptance requires planner, reviewer, and backlog-update
evidence; `ari llm proof --ticket <ticket> --confirm-external` generates that
DeepSeek proof sequence for an already-executed ticket. GitHub acceptance is
checked at the operation level and requires issue creation, PR creation, issue
comment sync, and status snapshot evidence. Unset write/execution gates are
reported as `action_required` instead of being hidden.
`ari evidence packet --require-acceptance-ready` also embeds the product readiness status, readiness check
statuses, production acceptance status, run-gate status, real-success evidence
summary, and latest redacted failure summary. It exits non-zero when production
acceptance is not ready, so release evidence cannot silently pass with only
`fake-codex` or dry-run evidence. Use `--require-run-gates-ready` when the
current run must also prove that real external execution/write gates are set.

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
- Feishu writes remain preview-only unless explicitly enabled and confirmed.
- `.env`, `.env.*`, `*.secret`, `secrets/`, and `.ariadne/` are gitignored.

## Verification

```bash
python3.11 -m pytest
python3.11 -m ruff check .
scripts/verify_v1.sh
```

`scripts/verify_v1.sh` is split into static checks, offline deterministic
verification, production readiness verification, and optional real smoke
verification. The offline section validates fixtures only; product acceptance is
gated by `ari doctor product --require-acceptance-ready` and real integration
evidence.

## v1.0 Limitations

- Local single-worker runtime, not a production multi-worker scheduler.
- JSON/JSONL persistence, not Postgres or a hosted database.
- Local workbench frontend, not a hosted multi-user WebSocket/auth system.
- Real Codex execution depends on the local Codex CLI and remains default-off.
- Feishu real writes are default-off; ticket runs write preview plans until a
  real write is explicitly enabled and confirmed.
