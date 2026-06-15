# Ariadne v1.0 Evaluation

## Scope

This report evaluates Ariadne v1.0 as a local-first, Ticket-driven Agent teammate workbench.

## Commands

- `pytest`
- `ruff check .`
- `python3.11 -m ariadne_ltb.cli demo full`
- `python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md`
- `python3.11 -m ariadne_ltb.cli ticket list`
- `python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to fake-codex`
- `python3.11 -m ariadne_ltb.cli daemon run-once`
- `python3.11 -m ariadne_ltb.cli ticket comments ARI-003`
- `python3.11 -m ariadne_ltb.cli runtime journal`
- `python3.11 -m ariadne_ltb.cli runtime recover`
- `python3.11 -m ariadne_ltb.cli daemon status`
- `python3.11 -m ariadne_ltb.cli export board`
- `python3.11 -m ariadne_ltb.cli backend doctor`
- `python3.11 -m ariadne_ltb.cli doctor v1`

## Current Planning Result

Implementation-phase final command results are recorded in `docs/development_report.md` after `scripts/verify_v1.sh` runs. The evaluation surface is intentionally local and deterministic: default tests do not require Codex, Claude, DeepSeek, Feishu, network access, or GitHub tokens.

## Expected Evidence

- Main chain passes from source ingest to board export.
- `fake-codex` modifies only the demo target project and target tests pass.
- Reviewer returns a conservative verdict with diff and test evidence.
- Memory, Feishu dry-run plan, and next tickets are written.
- CodexBackend and ClaudeCodeBackend remain gated and blocked when not explicitly enabled.
- Board is exportable as Markdown and HTML.

## Safety

Real Codex and Claude execution remain gated by `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` and `--confirm-execution`. Feishu real writes remain gated by `FEISHU_ENABLE_WRITE=1` and `--confirm-write`.

## Known Limitations

- Local single-worker runtime.
- JSON/JSONL persistence.
- No production web UI.
- Real Codex depends on the local Codex CLI.
- Feishu real writes are default-off.
