# Ariadne 1.0 Development Report

## Implemented files

- `pyproject.toml`
- `uv.lock`
- `.gitignore`
- `.env.example`
- `README.md`
- `ariadne_ltb/__init__.py`
- `ariadne_ltb/models.py`
- `ariadne_ltb/storage.py`
- `ariadne_ltb/runtime.py`
- `ariadne_ltb/agents.py`
- `ariadne_ltb/ingest.py`
- `ariadne_ltb/execution.py`
- `ariadne_ltb/git_utils.py`
- `ariadne_ltb/target_project.py`
- `ariadne_ltb/review.py`
- `ariadne_ltb/memory.py`
- `ariadne_ltb/feishu.py`
- `ariadne_ltb/llm.py`
- `ariadne_ltb/full_demo.py`
- `ariadne_ltb/demo.py`
- `ariadne_ltb/board.py`
- `ariadne_ltb/cli.py`
- `examples/multica_research_note.md`
- `examples/sources/paper_agent_workflows.md`
- `examples/sources/blog_multica_lessons.md`
- `examples/sources/github_tiny_cli_readme.md`
- `templates/BUILD_TICKET_TEMPLATE.md`
- `templates/CODEX_HANDOFF_TEMPLATE.md`
- `templates/REVIEW_REPORT_TEMPLATE.md`
- `templates/FEISHU_WRITE_PLAN_TEMPLATE.md`
- `docs/adr/ADR-0001-multica-architecture-extraction.md`
- `docs/codex_workpacks/ariadne_1_0_v3/`
- `tests/test_1_0_full_demo.py`
- `tests/test_models.py`
- `tests/test_storage.py`
- `tests/test_pipeline.py`
- `tests/test_cli.py`

## What was implemented

Ariadne now demonstrates the 1.0 Learning-to-Build loop:

```text
external knowledge -> Build Ticket -> Build Packet -> coding backend -> code diff -> review -> memory
```

The full demo:

- creates/updates `.ariadne/demo_target_project/`;
- ingests three source fixtures: paper, blog, and GitHub README note;
- creates Build Tickets with unique keys and Build Packets;
- selects the GitHub README source as the code task;
- runs `FakeCodexBackend` against the separate demo target project;
- adds `demo-todo export-json`;
- captures stdout, stderr, exit code, changed files, git diff, and test output;
- produces a conservative review verdict;
- writes local memory under `.ariadne/memory/`;
- creates a Feishu dry-run write plan;
- exports `.ariadne/board/index.md` and `.ariadne/board/index.html`.

## Commands run

```bash
pytest
ruff check .
uv run python -m ariadne_ltb.cli demo full
uv run python -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli demo full
python -m ariadne_ltb.cli demo full
```

Verification results:

- `pytest` - passed, 20 tests.
- `ruff check .` - passed.
- `uv run python -m ariadne_ltb.cli demo full` - passed.
- `uv run python -m ariadne_ltb.cli export board` - passed.
- `python3.11 -m ariadne_ltb.cli demo full` - passed.
- `python -m ariadne_ltb.cli demo full` - failed before project code starts because this shell has no `python` executable in `PATH`.

## Full demo output summary

Latest successful full demo output:

```text
sources ingested: 3
tickets created: 3
backend used: fake-codex
changed files: demo_todo/cli.py, tests/test_cli.py
test exit code: 0
reviewer verdict: pass
board: .ariadne/board/index.md
memory: .ariadne/memory/tickets/<ticket_id>.md
feishu plan: .ariadne/feishu_plans/<plan_id>.json
```

## Safety boundaries

- Tests and default demo require no network, Codex, Claude, OpenAI, Anthropic, Feishu, or GitHub credentials.
- `FakeCodexBackend` modifies only `.ariadne/demo_target_project/`.
- `ShellBackend` refuses to run unless `--confirm-execution` is passed.
- `CodexBackend`/`ClaudeCodeBackend` are scaffolds and require explicit enablement plus confirmation.
- Ariadne itself never auto-commits, auto-pushes, auto-merges, or creates PRs.
- Feishu write-back is dry-run by default.
- `.env`, `.env.*`, `*.secret`, and `secrets/` are gitignored.
- The provided DeepSeek key was not committed or written into repo files.

## Optional real adapter instructions

DeepSeek is the preferred future LLM backend for Ariadne agent intelligence. The code includes an optional `DeepSeekClient` using OpenAI-compatible DeepSeek chat completions through:

```bash
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
```

The default runtime uses deterministic rules when no key is present.

Optional external execution:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
ari ticket execute ARI-003 --backend codex --confirm-execution
```

Optional Feishu real write-back uses `lark-cli docs +create --api-version v2`
and remains disabled unless credentials/configuration plus explicit confirmation
are present:

```bash
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_FOLDER_TOKEN=
FEISHU_ENABLE_WRITE=1
```

Command:

```bash
FEISHU_ENABLE_WRITE=1 ari memory sync <ticket_id_or_key> --target feishu --no-dry-run --confirm-write
```

The default 1.0 demo still generates Feishu dry-run plans only.

## Assumptions made

- The 1.0 local demo should prioritize a complete deterministic chain over live LLM/API behavior.
- `FakeCodexBackend` is the default backend for `demo full`.
- The demo target project can be reset/rewritten because it is generated under `.ariadne/`.
- If a local `pytest` executable is available, target project tests use it; otherwise they fall back to `sys.executable -m pytest`.
- The bare `python` command is unavailable on this machine; `python3.11` and `uv run python` were used as documented equivalents.

## Known limitations

- Feishu real write support is only a guarded `lark-cli` document-create scaffold, not a production sync adapter.
- No production Codex/Claude execution adapter yet.
- Source understanding is deterministic and fixture-oriented, not LLM-ranked.
- Static board is intentionally simple; no FastAPI board server yet.
- Local memory is markdown/JSON files, not retrieval-indexed.
- `DeepSeekClient` is optional and not used by deterministic tests.

## Next recommended Build Tickets

- ARI-004 - Knowledge retrieval over local memory, prior tickets, Build Packets, and markdown notes.
- ARI-005 - FastAPI read-only Build Board with filters for source type, status, backend, verdict, and changed files.
- ARI-006 - Build Packet quality evaluator for evidence coverage, acceptance criteria quality, and scope risk.
- ARI-007 - GitHub project analysis adapter for live or cloned repositories.
- ARI-008 - Skill system for reusable `paper-to-build-packet`, `github-project-analysis`, `codex-handoff`, `review-diff`, and `feishu-write-plan` methods.
- ARI-009 - Approval-gated real Codex CLI backend with captured logs, diffs, and test output.
- ARI-010 - Approval-gated Feishu write-back through `lark-cli docs +create --api-version v2`.
