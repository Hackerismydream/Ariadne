# Ariadne Production Agent Workbench Roadmap

Status: active roadmap

Timestamp: 2026-06-17-2043

This roadmap supersedes:

```text
docs/ops/ARIADNE_MULTICA_MATURITY_ROADMAP.md
docs/goals/2026-06-17-2034-ariadne-multica-maturity-goal.md
docs/superpowers/plans/2026-06-17-2034-ariadne-multica-maturity-execution-plan.md
```

## Product Target

Ariadne is not a demo harness. Ariadne is a production-usable, local-first
Agent Workbench for AI builders.

The target user is an AI builder who wants real agent teammates to turn
knowledge, feedback, and codebase state into software iterations.

The product loop remains ticket-centered:

```text
Knowledge / Feedback / Codebase / optional Goal
  -> update Ticket backlog
  -> Ticket management center
  -> assign to Agent
  -> local Daemon / Runtime
  -> real Codex / real Claude Code / real LLM agents
  -> Review / Comments / Board / Memory
  -> update Ticket backlog again
```

Goal can be input context. Ticket is still the runtime center.

## Direction Change

The previous roadmap was too conservative. It protected correctness, but it
could keep future work stuck in fake backends, dry-runs, and demo paths.

The new rule is:

```text
Real capability first.
Safety gates stay.
Evidence is mandatory.
Demo backends are test tools, not the product destination.
```

`fake-codex` remains allowed only for deterministic tests, CI-style checks, and
offline local development. It must not define product acceptance for production
agent capability.

Dry-run remains allowed only as a safety preview or fallback. It must not be
treated as the final state for Feishu, GitHub, Codex, Claude Code, or upstream
LLM agent runtime integration.

## Required Real Integrations

### Upstream LLM Agent Runtime

Ariadne needs a real upstream LLM runtime for non-coding agent roles:

- Build Lead
- Research
- Knowledge
- Project Context
- Planner
- Reviewer
- Memory
- Feishu planning
- GitHub planning

Default provider for this roadmap:

```text
provider: deepseek
base_url: https://api.deepseek.com
env var: DEEPSEEK_API_KEY
default model: deepseek-v4-pro
fast model: deepseek-v4-flash
```

The DeepSeek key must come from environment or a local `.env` file ignored by
git. Do not write real API keys into source, docs, tests, commits, logs, board
exports, or artifacts.

Implementation must support:

- real DeepSeek request path;
- JSON mode or strict JSON validation for planner outputs;
- retry and timeout policy;
- token usage capture when available;
- raw provider error capture with secret redaction;
- doctor command showing key presence without printing the value;
- deterministic fake/stub path only for automated tests.

### Real Codex

Codex is a production backend, not just a smoke-test backend.

Required behavior:

- execute real local Codex when enabled;
- write handoff prompt;
- pass target repo and prompt file correctly;
- capture stdout, stderr, exit code, git diff, changed files, and tests;
- record execution result artifacts;
- support service tier and reasoning settings through configuration;
- fail with exact evidence when login, quota, CLI, or config is broken.

### Real Claude Code

Claude Code is also a production backend.

Required behavior:

- execute real local Claude Code when enabled;
- support model, max-turns, and system-prompt args when the CLI supports them;
- capture stdout, stderr, exit code, git diff, changed files, and tests;
- record execution result artifacts;
- fail with exact evidence when login, quota, CLI, or config is broken.

### Real Feishu

Feishu must move beyond dry-run.

Required behavior:

- keep dry-run as preview;
- implement gated real write through `lark-cli` first;
- require `FEISHU_ENABLE_WRITE=1` and `--confirm-write`;
- write docs, decision logs, review summaries, and release evidence where
  configured;
- record URLs, document IDs, request summaries, and failure evidence;
- never print or commit Feishu credentials.

### Real GitHub

GitHub must be a real integration, not only local git.

Required behavior:

- read issues, PRs, branches, and check status through `gh` or GitHub token;
- create or update issue comments when explicitly requested;
- link Ariadne tickets to GitHub issues or PRs;
- push branches through local git auth;
- keep merge and destructive actions explicitly confirmed;
- record remote URLs, commit SHAs, PR numbers, and failure evidence.

## Multica Reference

Multica's main lesson is not "use a generic LLM API for every agent." Multica
treats an agent as a workspace member bound to a runtime, and that runtime is
usually a local AI coding tool. Agents have instructions, model selection,
custom environment variables, custom CLI args, MCP config, skills, comments,
assignments, task lifecycle, runtime capability, and usage tracking.

Ariadne should absorb that model, then add its own upstream LLM layer for
knowledge-to-ticket and feedback-to-ticket work.

In Ariadne:

```text
real LLM runtime -> thinks, plans, routes, reviews, writes structured packets
real coding runtime -> modifies code through Codex or Claude Code
ticket runtime -> records assignment, progress, artifacts, review, memory
```

## Product Acceptance

Ariadne is not production-ready until this real path works:

```bash
ari doctor integrations
ari ingest examples/sources/*.md --planner llm
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
ari review run ARI-003 --reviewer llm
FEISHU_ENABLE_WRITE=1 ari feishu write ARI-003 --confirm-write
ari github sync ARI-003 --confirm-write
ari export board
ari evidence packet
```

Tests can use fakes. The product path must use real integrations when the
required credentials and confirmations are present.

## Roadmap Order

### Phase 0: Branch Integration

Integrate the current core and existing frontend/workbench branch when it is
safe. Do not develop new frontend features first. The existing frontend branch
should be integrated when it helps product usability and does not block real
runtime work.

### Phase 1: DeepSeek Upstream LLM Runtime

Implement the real LLM client and agent runtime abstraction for non-coding
agents.

Commands:

```bash
ari llm doctor
ari llm smoke --provider deepseek --confirm-external
ari ticket plan ARI-003 --planner llm
ari review run ARI-003 --reviewer llm
```

### Phase 2: Real Coding Backends

Harden Codex and Claude Code as production backends.

Commands:

```bash
ari backend diagnose codex
ari backend diagnose claude-code
ari ticket run ARI-003 --backend codex --confirm-execution
ari ticket run ARI-003 --backend claude-code --confirm-execution
```

### Phase 3: Real Feishu Write

Implement gated Feishu write through `lark-cli`.

Commands:

```bash
ari feishu plan ARI-003
FEISHU_ENABLE_WRITE=1 ari feishu write ARI-003 --confirm-write
```

### Phase 4: Real GitHub Integration

Implement GitHub issue, PR, branch, status, and comment sync.

Commands:

```bash
ari github doctor
ari github link ARI-003 --issue <number>
ari github sync ARI-003 --confirm-write
```

### Phase 5: Inbox, Search, Recovery

Expose failures, blockers, quota issues, auth issues, and external integration
errors as inbox items and searchable evidence.

### Phase 6: Review, Eval, Acceptance Evidence

Use real LLM review when configured and deterministic review in tests.

### Phase 7: Workdir, Store, Release Durability

Make repeated production runs boring: cleanup, backup, migration, recovery,
and release evidence.

### Phase 8: Product Dogfood

Run a real AI Builder workflow end to end with real integrations where
credentials are configured. Failures are acceptable only if they are recorded
with exact evidence and next actions.

## Safety Rules

Real integrations are required. Unsafe defaults are not allowed.

- Real external execution requires `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and
  `--confirm-execution`.
- Real Feishu write requires `FEISHU_ENABLE_WRITE=1` and `--confirm-write`.
- Real GitHub writes require explicit write commands and confirmation where the
  action changes remote state.
- API keys must be read from environment or ignored local `.env`.
- Doctor commands may report set/unset, never values.
- Tests must pass without real credentials.

## Definition Of Done

The roadmap is complete when Ariadne can run a real local product workflow:

- DeepSeek-backed planner and reviewer work with real API when configured.
- Codex and Claude Code run real local tasks when enabled.
- Feishu writes real docs when enabled.
- GitHub sync reads and writes controlled remote artifacts when enabled.
- Board, memory, inbox, search, review, and evidence packet record the outcome.
- `fake-codex` is used only for tests and offline fallback.
- All default test paths remain deterministic and credential-free.
