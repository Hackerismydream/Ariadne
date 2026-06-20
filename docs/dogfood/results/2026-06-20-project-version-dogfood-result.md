# Project Version Dogfood Result - 2026-06-20

## Status

`REAL_CLOSED`

A browser-only Workbench dogfood run closed the Mini Code Agent path with real
Codex execution against the target project. This is not fake-codex, dry-run, or
CLI-only evidence.

## Command

```bash
ARIADNE_WORKBENCH_PORT=18768 \
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 \
scripts/verify_dogfood_browser.sh --real
```

## Result

- Result directory: `.ariadne/dogfood/browser-20260620T055338Z/`
- Server log: `.ariadne/dogfood/browser-20260620T055338Z/logs/workbench.log`
- Browser result: `DOGFOOD_BROWSER_REAL_PATH_COMPLETED`
- Target project: `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`
- Selected issue: `MCA-001`
- Assignment: `assignment_eebb2b610ce0`
- Backend: `codex`
- Handoff packet: `handoff_packet_da262cca66d5`
- Runtime authorization: `runtime_authorization_a95caa946a17`
- Execution result: `execution_9c5418cea515`
- Codex provider session: `019ee398-8c76-7d01-b8e3-7a69141fc193`
- Exit code: `0`
- Target tests: `/opt/homebrew/bin/pytest`, exit code `0`
- Review: `review_53a4993073f8`, verdict `pass`
- Memory: `.ariadne/memory/tickets/ticket_de51566c81b4.md`
- Feishu plan: `.ariadne/feishu_plans/feishu_b35a449bf2e3.json`
- Next tickets: `.ariadne/artifacts/ticket_de51566c81b4/next_tickets.json`
- Board path: `.ariadne/board/index.md`

## Changed Target Files

- `.mini-code-agent/runs/*/run.json`
- `.mini-code-agent/runs/*/trajectory.jsonl`
- `.mini-code-agent/runs/*/workbench_manifest.json`
- `mini_code_agent/__main__.py`
- `mini_code_agent/cli.py`
- `pyproject.toml`
- `tests/test_cli.py`

## Fixed During Closure

- Bound Workbench daemon execution to the current assignment without worktree
  isolation so target repo diff/tests are captured from the registered project.
- Prevented stale daemon loops from claiming an old assignment.
- Made Workbench event watching poll assignment events until terminal state.
- Made `run assignment` idempotent when an assignment is already claimed,
  running, or terminal, avoiding status regression to `ready_to_claim`.
- Superseded stale non-terminal LLM role runs so the reviewer no longer fails on
  historical stranded runs.
- Allowed `.mini-code-agent/` evidence paths for the Mini Code Agent issue.
- Expanded untracked directory changes into concrete files for review and UI
  evidence.
- Scoped dogfood proof checks to the current execution evidence panel so old
  timeline blockers do not invalidate a successful current run.

## Remaining Limitations

- `.ariadne` contains historical failed dogfood attempts from the repair loop.
  The current execution evidence is real and passing, but the timeline remains
  noisy until old attempts are pruned or filtered.
- Workbench daemon path records the board path without synchronously blocking on
  full board export. Full board export remains available as a separate command.
- The target project now has repeated run evidence files from multiple real
  Codex attempts. That is useful proof, but a later cleanup should compact the
  dogfood target before a demo recording.
