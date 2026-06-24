# Phase 2 Runtime Control Evidence

Timestamp: 2026-06-24

Scope: Grill Closure Campaign Phase 2, Runtime Control And Recovery.

## API Evidence

- `inbox-allowed-actions.json` was captured from `GET /api/inbox`.
- The active `external_execution_blocked` blocker is canonicalized to one
  active inbox item.
- The item exposes backend-approved actions only:
  `acknowledge`, `resolve`.
- `rerun` is not exposed for this external-execution gate blocker.

## Browser Evidence

Screenshots:

- `inbox-allowed-actions.png`
- `runs-scoped-daemon.png`
- `issue-detail-attempt-lineage.png`

Observed browser state:

- Inbox shows allowed actions instead of generic action buttons.
- Runs page exposes Start Daemon and uses scoped daemon start logic.
- Issue Detail for `M0TR-003` shows blocked execution evidence, an Inbox link,
  assignment attempt labels, cancelled duplicate runnable rows, and a
  `external_execution_blocked is not safe for automatic retry` row-level
  explanation instead of an unsafe retry action.

## Verification Commands

```bash
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
```
