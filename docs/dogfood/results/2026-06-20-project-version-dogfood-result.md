# Project Version Dogfood Result - 2026-06-20

## Status

`BLOCKED_NOT_CLOSED`

This run established a browser-first dogfood harness and used it to drive the
Workbench product path. It did not prove real Codex/Claude execution against
the target project.

## Command

```bash
scripts/verify_dogfood_browser.sh --blocked-ok
```

## Latest Evidence

- Result directory: `.ariadne/dogfood/browser-20260620T034405Z/`
- Blocker file: `.ariadne/dogfood/browser-20260620T034405Z/current-blocker.json`
- Server log: `.ariadne/dogfood/browser-20260620T034405Z/logs/workbench.log`
- Browser step reached: `inspect execution evidence and version progress`
- Blocker: `BLOCKED_REHEARSAL_NOT_CLOSURE`

## What Worked

- Browser opened the real local Workbench through `ari workbench serve`.
- Browser registered the Mini Code Agent target project.
- Browser created the Mini Code Agent goal.
- Browser added/analyzed the external source inputs.
- Browser generated `MCA-*` target-project issue suggestions.
- Browser applied the issue delta after stale-preview recovery was fixed.
- Browser opened `MCA-001`.
- Browser drove assignment/runtime controls far enough to reach evidence
  inspection.

## Fixed During This Pass

- Added a Playwright browser dogfood harness.
- Added a shell verifier that starts an isolated local Workbench port and
  records blocker evidence.
- Fixed stale task-change preview UX so `stale_preview` no longer appears as
  raw JSON; the Workbench now refreshes task suggestions and asks the user to
  apply the latest preview.
- Tightened `--blocked-ok` so it cannot be mistaken for real closure.

## Remaining Closure Gap

The product still needs a `--real` browser dogfood run that proves:

```text
Workbench issue -> assignment -> daemon claim -> Codex/Claude CLI execution
-> target repo diff/tests/review/memory/next issue visible in Workbench
```

Until that evidence exists, Ariadne has not closed the Mini Code Agent dogfood.
