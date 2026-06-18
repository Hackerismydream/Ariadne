# Ariadne Production Agent Workbench Execution Plan

Status: active execution plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Ariadne into a production-usable local Agent Workbench with real DeepSeek, Codex, Claude Code, Feishu, and GitHub integrations.

**Architecture:** Ariadne remains ticket-centered and local-first. Real LLM agents handle planning, routing, review, and knowledge work; real coding runtimes execute code changes through Codex or Claude Code; Ariadne records tickets, assignments, runs, reviews, memory, inbox, board, and evidence. Fakes remain only for tests and offline fallback.

**Tech Stack:** Python 3.11+, Pydantic v2, Typer, Pytest, Ruff, JSON/JSONL persistence, DeepSeek OpenAI-compatible API, local Codex CLI, local Claude Code CLI, lark-cli, gh CLI or GitHub token, local Git worktrees.

---

## Operating Position

This plan supersedes the conservative 2034 maturity plan. It keeps safety gates
but changes the execution posture:

```text
real product path first
fake-codex only for tests
dry-run only for preview
real integration failures are product evidence
demo full only for offline regression fixtures
```

Do not commit credentials. The DeepSeek key supplied by the user must be placed
only in environment or an ignored local `.env`, never in tracked files.

## Multica Reference

Multica binds agents to local AI coding tool runtimes. Agents carry
instructions, model selection, custom env, custom CLI args, MCP config, skills,
task lifecycle, comments, and usage tracking.

Ariadne should do the same for coding runtimes, and add one extra layer:
DeepSeek-backed upstream LLM agents for planning, review, routing, knowledge,
and memory.

## Phase 0: State Check And Branch Integration Decision

**Files:**
- Modify: none unless integration is selected.

- [x] **Step 1: Confirm current branches**

Run:

```bash
git -C /Users/martinlos/code/Ariadne.worktrees/ariadne-core-orchestration-backends-3 status --short --branch
git -C /Users/martinlos/code/Ariadne status --short --branch
```

Expected:

- Core and frontend worktrees are clean before integration or new feature work.

Current decision as of 2026-06-18 12:40 CST:

- Active branch is `codex/ariadne-production-frontend-integration`.
- The active branch already contains the local workbench frontend and passes
  `scripts/verify_v1.sh`.
- Do not merge the older standalone frontend lane wholesale unless a future
  diff review proves it contains unique frontend work without stale core
  changes.

- [x] **Step 2: Decide if existing frontend branch should be integrated**

Integrate when:

- core branch is clean;
- frontend branch is clean;
- real backend data contracts are about to change;
- web workbench can help inspect production evidence.

Defer when:

- a real integration bug blocks product capability;
- integration conflicts would delay DeepSeek, Codex, Claude Code, Feishu, or
  GitHub product paths.

- [x] **Step 3: If integrating, create integration branch**

No new integration branch is required for the current slice because the active
branch is already the production/frontend integration branch.

Run:

```bash
cd /Users/martinlos/code/Ariadne.worktrees/ariadne-core-orchestration-backends-3
git switch codex/ariadne-core-orchestration-backends-3
git pull --ff-only
git switch -c codex/ariadne-production-integration
git merge codex/ariadne-workbench-frontend-lane
```

Resolve conflicts once. Prefer core branch semantics for Python runtime,
storage, orchestrator, and safety behavior.

## Phase 1: DeepSeek Upstream LLM Runtime

**Files:**
- Create: `ariadne_ltb/llm.py`
- Create: `ariadne_ltb/llm_agents.py`
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/planner.py`
- Modify: `ariadne_ltb/review.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `ariadne_ltb/doctor.py`
- Test: `tests/test_llm_client.py`
- Test: `tests/test_llm_agents.py`

- [x] **Step 1: Add deterministic tests**

Tests must use a fake transport and cover:

- missing `DEEPSEEK_API_KEY` returns blocked result;
- request payload uses `https://api.deepseek.com`;
- model defaults to `deepseek-v4-pro`;
- JSON output is parsed and validated;
- provider errors are recorded with secret redaction.

- [x] **Step 2: Implement DeepSeek client**

Implement:

```text
DeepSeekClient
LLMRequest
LLMResponse
LLMError
LLMUsage
```

Use environment:

```text
DEEPSEEK_API_KEY
ARIADNE_LLM_PROVIDER=deepseek
ARIADNE_LLM_MODEL=deepseek-v4-pro
ARIADNE_LLM_FAST_MODEL=deepseek-v4-flash
ARIADNE_LLM_TIMEOUT_SECONDS
```

- [x] **Step 3: Add LLM doctor**

Add:

```bash
ari llm doctor
ari llm smoke --provider deepseek --confirm-external
```

Doctor prints set/unset, never key values.

- [x] **Step 4: Wire planner and reviewer**

Add:

```bash
ari ticket plan ARI-003 --planner llm
ari review run ARI-003 --reviewer llm
```

LLM output must be schema-validated. Invalid JSON creates a blocked artifact
instead of silently falling back to deterministic output.

## Phase 2: Real Codex And Claude Code Production Backends

**Files:**
- Modify: `ariadne_ltb/execution.py`
- Modify: `ariadne_ltb/runtime.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `ariadne_ltb/board.py`
- Test: `tests/test_real_backend_gates.py`
- Test: `tests/test_codex_backend_real_path.py`
- Test: `tests/test_claude_backend_real_path.py`

- [x] **Step 1: Make real backend paths first-class**

Required commands:

```bash
ari backend diagnose codex
ari backend diagnose claude-code
ari ticket run ARI-003 --backend codex --runtime-profile production --confirm-execution
ari ticket run ARI-003 --backend claude-code --confirm-execution
```

- [x] **Step 2: Preserve safety gates**

Real execution still requires:

```text
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

But the implementation target is real execution, not dry-run.

- [x] **Step 3: Capture evidence**

Capture:

- handoff file;
- command template;
- stdout;
- stderr;
- exit code;
- git diff;
- changed files;
- test command and test exit code;
- provider auth or quota failures;
- session id when available.

## Phase 3: Real Feishu Write

**Files:**
- Create or modify: `ariadne_ltb/feishu.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `ariadne_ltb/board.py`
- Test: `tests/test_feishu_real_write_gate.py`

- [x] **Step 1: Keep dry-run preview**

`ari feishu plan ARI-003` remains available.

- [x] **Step 2: Add gated write**

Add:

```bash
FEISHU_ENABLE_WRITE=1 ari feishu write ARI-003 --confirm-write
```

Use `lark-cli` first. If not logged in, return blocked evidence with the exact
missing login or credential state.

- [x] **Step 3: Record result**

Persist:

```text
.ariadne/integrations/feishu/<ticket_key>/*.json
```

Include document URL, document id, operation summary, and failure evidence.

## Phase 4: Real GitHub Integration

**Files:**
- Create: `ariadne_ltb/github_integration.py`
- Modify: `ariadne_ltb/cli.py`
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/board.py`
- Test: `tests/test_github_integration.py`

- [x] **Step 1: Add doctor**

Add:

```bash
ari github doctor
```

Prefer `gh auth status`. Support `GITHUB_TOKEN` only from environment.

- [x] **Step 2: Add link and sync**

Add:

```bash
ari github link ARI-003 --issue 123
ari github sync ARI-003 --confirm-write
```

Read operations can run when authenticated. Remote writes need explicit write
commands and confirmation.

- [x] **Step 3: Record evidence**

Persist:

```text
.ariadne/integrations/github/<ticket_key>/*.json
```

Include repo, issue, PR, branch, commit SHA, remote URL, and failure evidence.

## Phase 5: Inbox, Search, Recovery For Real Failures

**Files:**
- Create: `ariadne_ltb/inbox.py`
- Create: `ariadne_ltb/search.py`
- Modify: `ariadne_ltb/storage.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Modify: `ariadne_ltb/cli.py`
- Test: `tests/test_inbox.py`
- Test: `tests/test_local_search.py`

Every real integration failure must create an inbox item:

- [x] missing API key;
- [x] invalid API key;
- [x] CLI not installed;
- [x] not logged in;
- [x] quota exhausted;
- [x] command timeout;
- [x] unsafe resource boundary;
- [x] failed write.

Search must index tickets, comments, memory, artifacts, reviews, inbox, Feishu
results, GitHub results, and execution evidence.

- [x] Add `InboxItem` persistence under `.ariadne/inbox/items.json`.
- [x] Add `ari inbox refresh` and `ari inbox list`.
- [x] Add local lexical evidence search through `ari search`.
- [x] Show inbox count and latest inbox items on the board.
- [x] Add deterministic tests for inbox materialization and local search.

## Phase 6: Review, Eval, Acceptance Evidence

**Files:**
- Modify: `ariadne_ltb/review.py`
- Modify: `ariadne_ltb/models.py`
- Modify: `ariadne_ltb/orchestrator.py`
- Modify: `ariadne_ltb/board.py`
- Test: `tests/test_review_risk_scoring.py`

Use real LLM reviewer when configured:

```bash
ari review run ARI-003 --reviewer llm
```

Automated tests use fake LLM transport.

Review report must include:

- [x] verdict;
- [x] risk score;
- [x] acceptance criterion coverage;
- [x] evidence refs;
- [x] next-ticket suggestions;
- [x] whether the review came from deterministic or real LLM reviewer.

Review evidence is visible through `ari review run`, persisted review reports,
and the board review section.

## Phase 7: Store, Workdir, Release Evidence

**Files:**
- Create or modify: `ariadne_ltb/evidence.py`
- Create or modify: `ariadne_ltb/workdir_policy.py`
- Modify: `ariadne_ltb/store_doctor.py`
- Modify: `scripts/verify_v1.sh`
- Test: `tests/test_release_evidence.py`
- Test: `tests/test_workdir_policy.py`

Add:

```bash
ari evidence packet
ari evidence packet --require-acceptance-ready
ari workdir list
ari workdir cleanup --confirm-cleanup
```

Repeated verification must not pollute the main workspace with stale blocked
assignments.

- [x] Add `ReleaseEvidencePacket` and `.ariadne/evidence/release_evidence_packet.json`.
- [x] Add `ari evidence packet`.
- [x] Add `ari workdir list`.
- [x] Add `ari workdir cleanup --confirm-cleanup`.
- [x] Keep dirty generated workdirs unless `--force-dirty` is explicit.
- [x] Add release evidence and workdir policy tests.
- [x] Add workdir cleanup and evidence packet generation to `scripts/verify_v1.sh`.

## Phase 8: Product Dogfood

Run real dogfood when credentials and logins are present:

```bash
ari llm doctor
ari backend diagnose codex
ari backend diagnose claude-code
ari github doctor
ari ingest examples/sources/*.md --planner llm
ari ticket assign ARI-003 --to codex --runtime-profile production
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
ari review run ARI-003 --reviewer llm
FEISHU_ENABLE_WRITE=1 ari feishu write ARI-003 --confirm-write
ari github sync ARI-003 --confirm-write
ari export board
ari evidence packet --require-acceptance-ready
```

If any real step fails, fix it when safe. If the blocker is external login,
quota, or missing user permission, record exact evidence and next action.

- [x] `ari llm doctor` confirmed DeepSeek configuration without printing the key.
- [x] `ari llm smoke --provider deepseek --confirm-external` completed with real DeepSeek API.
- [x] `ari backend diagnose codex` confirmed local Codex CLI and service tier.
- [x] `ari backend diagnose claude-code` confirmed local Claude Code CLI.
- [x] Real CodexBackend smoke test completed with exit code 0 and review pass after
  reverting unsupported local `service_tier=flex` back to `fast`.
- [x] Real Claude Code ticket run completed with exit code 0 and review pass.
- [x] Real Feishu write completed through `lark-cli` after fixing relative
  content path handling.
- [x] `ari github doctor` confirmed `gh auth status` is ok.
- [x] Added `ari github create-issue <ticket> --confirm-write` so Ariadne can
  create a controlled GitHub issue from a local ticket before sync.
- [x] Real GitHub write completed: `ari github create-issue ARI-003
  --confirm-write` created issue #8 and `ari github sync ARI-003
  --confirm-write` posted a sync comment.

## Verification

For code slices:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
```

For real integration slices, also run the relevant real smoke command when
credentials and confirmations are available.

## Final Acceptance

Ariadne is acceptable when:

- DeepSeek-backed planner and reviewer run with real API when configured.
- Codex and Claude Code run real local coding tasks when enabled.
- Feishu writes real cloud docs when enabled.
- GitHub reads and writes controlled issue/PR/comment artifacts when enabled.
- Failures are visible in inbox and search.
- Board and evidence packet show real execution evidence.
- Tests remain deterministic without credentials.
