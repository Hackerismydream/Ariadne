# Test and Acceptance Plan

## Required tests

Add or update tests for:

```text
architecture docs exist
ADR-0002 exists
gap report exists
AgentRun lifecycle terminal invariants
failure reasons
runtime capability snapshot persistence
backend doctor snapshot does not print secrets
project resources serialization
handoff includes project resources
target repo path validation
directory lock acquisition/release
second lock blocks
BuildSkill discovery
handoff includes skill references
route decision artifact exists
progress events exist in expected order
fake-codex ticket run still passes
real Codex smoke-test path still gated
existing demo full still passes
```

## Required commands

Run:

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
```

If `uv run ari` is available, also run:

```bash
uv run ari demo full
uv run ari ticket list
uv run ari ticket run ARI-003 --backend fake-codex
uv run ari export board
uv run ari backend doctor
```

Do not require:

```text
network
Codex installed
Claude installed
DeepSeek key
Feishu credentials
GitHub token
```

## Acceptance criteria

This task is complete only if:

```text
1. Multica architecture digest exists.
2. Ariadne gap report exists.
3. ADR-0002 exists.
4. Ariadne has stronger lifecycle/failure/resource/skill/routing foundations.
5. Existing True MVP loop still works.
6. Existing Codex smoke-test path remains gated and usable.
7. Tests pass without external credentials.
8. README or development report explains how Multica influenced Ariadne.
```
