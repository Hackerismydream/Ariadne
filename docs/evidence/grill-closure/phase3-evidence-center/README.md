# Phase 3 Evidence Center Verification

Date: 2026-06-25

Branch: `codex/grill-closure-issue-evidence-center`

Issue inspected: `M0TR-003`

Browser URL:

```text
http://127.0.0.1:8766/#issues/M0TR-003
```

## Verified

- Issue Detail renders an `Evidence Center`.
- Evidence is grouped into:
  - Source Evidence
  - Handoff Evidence
  - Route Decision
  - Execution Artifacts
  - Review Artifacts
  - Memory Artifacts
  - Next Tickets
- The inspected issue projected 36 evidence rows from persisted Ariadne store data.
- Evidence rows include semantic validity labels, including:
  - `Available`
  - `Produced by run`
  - `Empty`
  - `Not run`
- Clicking `Open evidence` fetched the per-issue evidence route and opened a readable viewer.

## Artifacts

- `browser-evidence.json` — browser automation assertion output.
- `issue-detail-api.json` — summarized `/api/issues/M0TR-003` response.
- `evidence-item-api.json` — summarized `/api/issues/M0TR-003/evidence/<id>` response.
- `issue-evidence-center.png` — full-page screenshot before opening an evidence item.
- `issue-evidence-viewer.png` — full-page screenshot after opening an evidence item.

## Notes

This verification used the real local Workbench API and persisted `.ariadne`
state. It did not use product mock data, fake-codex acceptance, demo full, or a
CLI-only path as acceptance evidence.
