# 11 — Codex Master Prompt: Build Ariadne 1.0

You are Codex working on Ariadne.

The user wants a single high-quality implementation pass that reaches **Ariadne 1.0**, not another tiny v0.1 increment.

## Required context

Read the whole workpack before coding:

1. `00_START_HERE.md`
2. `01_REVIEW_OF_V2_AND_NEW_TARGET.md`
3. `02_PRODUCT_1_0_REQUIREMENTS.md`
4. `03_ARCHITECTURE_AND_DOMAIN.md`
5. `04_AGENT_TEAM_AND_RUNTIME.md`
6. `05_INPUTS_AND_FIXTURES.md`
7. `06_EXECUTION_BACKENDS.md`
8. `07_FEISHU_AND_MEMORY.md`
9. `08_BOARD_AND_DEMO.md`
10. `09_ACCEPTANCE_CRITERIA.md`
11. `10_ENV_SETUP_AND_SECRETS.md`

If the existing repository already contains Ariadne v0.1 Ticket Kernel, build on it. Do not rewrite unnecessarily.

## Mission

Implement Ariadne 1.0: a local Learning-to-Build Agent Team demo that can ingest multiple external knowledge inputs, create Build Tickets and Build Packets, plan a coding task, execute against a separate demo target project, capture logs/diff/tests, review the result, write memory, generate a Feishu dry-run plan, and show the whole loop on a board.

## One-run autonomy protocol

Do not stop after implementing only the kernel.

Do not ask the user questions unless the task is impossible without the answer.

When uncertain:

1. choose the conservative local implementation;
2. document the assumption;
3. continue;
4. include it in `docs/development_report.md`.

Your goal is to maximize completed 1.0 functionality in this single pass.

## Core 1.0 command

A user must be able to run:

```bash
python -m ariadne_ltb.cli demo full
```

If package script is available:

```bash
ari demo full
```

This must produce the complete chain:

```text
3 source fixtures
  -> 3 Build Tickets
  -> Build Packets
  -> selected code_task
  -> target project execution
  -> stdout/stderr/exit code
  -> git diff and changed files
  -> tests
  -> reviewer verdict
  -> local memory
  -> Feishu dry-run plan
  -> board export
```

## Required implementation plan

Implement all phases in one pass.

### Phase 1 — Harden existing kernel

- Generic ticket creation from arbitrary source.
- Unique ticket keys.
- Ticket list/show/run commands.
- Attempt support for AgentRun.
- Relative artifact paths.
- Keep v0.1 demo compatibility if feasible.

### Phase 2 — Source ingestion

Add `SourceDocument` and source ingestion.

Required command:

```bash
ari ingest examples/sources/*.md
```

Create fixtures:

```text
examples/sources/paper_agent_workflows.md
examples/sources/blog_multica_lessons.md
examples/sources/github_tiny_cli_readme.md
```

### Phase 3 — Project context and target project

Create demo target project under:

```text
.ariadne/demo_target_project/
```

It should be a small Python CLI package with tests.

Initialize git inside the target project so diff capture works.

### Phase 4 — Agent runtime upgrade

Implement/upgrade these agent roles:

- Build Lead
- Source Router
- Research/Learning
- GitHub/Repo Analysis
- Knowledge
- Project Context
- Planner
- Execution
- Reviewer
- Memory/Feishu

The runtime may be deterministic/rule-based by default but must process real source text and project context.

### Phase 5 — Execution backends

Implement:

- DryRunBackend
- FakeCodexBackend
- ShellBackend
- optional CodexBackend scaffold
- optional ClaudeCodeBackend scaffold

Default full demo should use FakeCodexBackend and modify the demo target project by adding `demo-todo export-json`.

ShellBackend and CodexBackend must require explicit confirmation.

### Phase 6 — Git/test capture

Capture:

- git HEAD before/after;
- git status before/after;
- changed files;
- git diff;
- execution stdout/stderr/exit code;
- test stdout/stderr/exit code.

### Phase 7 — Reviewer upgrade

Reviewer must inspect packet quality, execution result, changed files, tests, diff, allowed scope, terminal states, and memory safety.

### Phase 8 — Memory and Feishu

Write local memory records.

Generate Feishu dry-run plans.

Optional real Feishu writes only behind credentials and explicit confirmation.

### Phase 9 — Board

Export Markdown board and preferably HTML board.

Required command:

```bash
ari export board
```

Optional:

```bash
ari board serve
```

### Phase 10 — Tests and report

Add deterministic tests. Tests must not require network, Codex, Claude, OpenAI API, Anthropic API, Feishu, or GitHub credentials.

Update `docs/development_report.md` with:

- what was implemented;
- commands run;
- full demo output summary;
- safety boundaries;
- optional real adapter instructions;
- known limitations;
- next Build Tickets after 1.0.

## Required checks

Run:

```bash
pytest
ruff check .
python -m ariadne_ltb.cli demo full
python -m ariadne_ltb.cli export board
```

If `python` is unavailable, run equivalent `python3.11` or `uv run python` commands and document the environment issue.

If `ruff` is unavailable, document it.

## Non-goals

Do not build a full Multica clone.

Do not implement multi-workspace auth.

Do not implement a production Feishu integration if it risks breaking the local demo.

Do not require real external APIs for tests.

Do not auto-commit, auto-push, auto-merge, or create PRs from inside Ariadne.

## Quality bar

The final PR should be credible as **Ariadne 1.0 MVP**, not just a kernel.

The generated board and report must demonstrate:

```text
external knowledge -> build ticket -> coding backend -> code diff -> review -> memory
```

If time is limited, prioritize the complete full demo chain over optional web UI or optional real API adapters.
