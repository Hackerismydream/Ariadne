# Ariadne

Ariadne turns what you learn into what your coding agents build.

This repository contains the Ariadne 1.0 local Learning-to-Build MVP for
`ariadne-ltb`. The Python package is `ariadne_ltb`; the intended CLI command is
`ari`, with `python -m ariadne_ltb.cli` as the fallback entrypoint.

## What the MVP does

The full demo ingests three local external source fixtures, creates Build
Tickets and Build Packets, selects a code task, executes it against a separate
demo target project, captures stdout/stderr/exit code, git diff, changed files
and test output, reviews the result, writes local memory, generates a Feishu
dry-run plan, and exports a static board under `.ariadne/board/`.

Pipeline:

```text
Build Lead
  -> Learning
  -> Knowledge
  -> Repo
  -> Planner
  -> Execution Dry Run
  -> Reviewer
  -> Feishu Plan
```

The execution backend is a dry run. It does not call Codex, Claude Code,
Feishu, external APIs, or Git automation.

## Run locally

Install the project in your preferred Python 3.11+ environment, then run:

```bash
pytest
python -m ariadne_ltb.cli demo full
python -m ariadne_ltb.cli export board
```

If your shell does not provide a `python` executable, use the environment's
Python 3.11+ command or let `uv` create the environment:

```bash
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
uv run python -m ariadne_ltb.cli demo full
```

If installed as a package, the script entrypoint also works:

```bash
ari demo full
ari export board
```

Inspect generated output:

```text
.ariadne/
  project_space.json
  tickets/
  runs/
  build_packets/
  reviews/
  feishu_plans/
  memory/
  demo_target_project/
  artifacts/
  board/index.md
  board/index.html
```

## Safety boundaries

- No real Feishu writes.
- Full demo uses `fake-codex`, a deterministic local backend.
- Shell/Codex/Claude-style execution scaffolds require explicit confirmation.
- No auto-commit, auto-push, auto-merge, or PR creation.
- No web UI, auth, crawler, vector database, or cloud runtime in v0.1.
- Every runtime step creates an Agent Run and reaches a terminal state.
