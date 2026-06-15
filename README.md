# Ariadne

Ariadne turns what you learn into what your coding agents build.

This repository contains the v0.1 local deterministic Ticket Kernel for
`ariadne-ltb`. The Python package is `ariadne_ltb`; the intended CLI command is
`ari`, with `python -m ariadne_ltb.cli` as the fallback entrypoint.

## What the MVP does

The demo converts `examples/multica_research_note.md` into a Build Ticket, runs
a deterministic local agent pipeline, writes artifacts under
`.ariadne/artifacts/<ticket_id>/`, and exports a static board under
`.ariadne/board/`.

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
python -m ariadne_ltb.cli demo
python -m ariadne_ltb.cli export board
```

If your shell does not provide a `python` executable, use the environment's
Python 3.11+ command or let `uv` create the environment:

```bash
python3.11 -m ariadne_ltb.cli demo
python3.11 -m ariadne_ltb.cli export board
uv run python -m ariadne_ltb.cli demo
```

If installed as a package, the script entrypoint also works:

```bash
ari demo
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
  artifacts/
  board/index.md
```

## Safety boundaries

- No real Feishu writes.
- No real coding-agent execution.
- No auto-commit, auto-push, auto-merge, or PR creation.
- No web UI, auth, crawler, vector database, or cloud runtime in v0.1.
- Every runtime step creates an Agent Run and reaches a terminal state.
