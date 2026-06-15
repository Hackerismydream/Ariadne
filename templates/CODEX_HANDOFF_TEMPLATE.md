# Codex Handoff Template

## Goal

State the exact implementation goal.

## Context

Explain why this task exists and where the evidence came from.

## Relevant files/modules

- `path/to/file.py`

## Constraints

- Do not expand scope.
- Do not call external APIs unless explicitly allowed.
- Do not auto-commit, auto-push, or auto-merge.
- Preserve dry-run safety.

## Implementation plan

1.
2.
3.

## Acceptance criteria

- [ ]
- [ ]
- [ ]

## Test plan

```bash
pytest
python -m ariadne_ltb.cli demo
python -m ariadne_ltb.cli export board
```

## Expected output

Describe the expected result.

## Known non-goals

- Do not implement real Feishu API writes.
- Do not require real Codex runtime.
- Do not build full web UI in MVP.
