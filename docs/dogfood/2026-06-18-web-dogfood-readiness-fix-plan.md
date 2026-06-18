# Web Dogfood Readiness Fix Plan

Date: 2026-06-18

Status: Implemented for browser issue-generation and dispatch readiness

## Goal

Make Ariadne honest and usable enough to attempt the Mini Code Agent dogfood
case from the Workbench web UI, without relying on Ariadne CLI commands as the
product path.

Dogfood reference:

- `docs/dogfood/2026-06-18-mini-code-agent-web-dogfood.md`

## Current Problems To Fix

| Area | Current behavior | Fix target |
|---|---|---|
| Knowledge | Buttons exist but do not call real APIs. | Add web source ingestion actions and live source projection. |
| Goal | Goal is display-only. | Add web project goal creation/update and bind it to a target project. |
| Issues | Assign/run/watch partially works; evidence panels are sparse. | Generate issue candidates from web-created goal/sources and show real evidence state. |
| Agents | Static agent table. | Project real agent profiles and runtime capability status. |
| Runtime | `#runtime` browser route can render the wrong page. | Fix route/page mapping and show live runtime capability/daemon state. |
| Skills | Static skill list. | Project local skill packs and selected skill references when available. |
| Inbox | Static inbox rows. | Project real inbox items and add web recovery actions where existing backend support exists. |

## Product Rules

1. Workbench API mode must not silently mix static fixture data into live
   product state.
2. Empty panels must explain whether data is missing, blocked, unconfigured, or
   not yet run.
3. Dogfood acceptance must be browser-first:
   - register target project;
   - create goal;
   - add external sources;
   - generate/apply issues;
   - assign/run/watch from Workbench.
4. CLI may be used for tests and debugging only.
5. Real external execution remains gated; blocked gate results are valid if
   shown clearly.

## Implementation Plan

### 1. Backend Workbench Projection

Extend `/api/workbench` with live data for:

- project goals;
- source records;
- generated backlog previews / issue deltas;
- agent profiles;
- skills;
- inbox items;
- ticket evidence paths.

The projection should use existing store files and models where possible.

### 2. Web Mutations

Add typed API endpoints for:

- target project registration already exists; make frontend use it;
- project goal create/update;
- source ingestion from URL / GitHub URL / local markdown text;
- issue candidate generation from selected goal + sources;
- issue delta apply;
- inbox recovery for existing blocker/review items where supported.

### 3. Frontend API Mode Cleanup

In API mode:

- do not use `workbenchData` seed values for knowledge, goals, agents, skills,
  inbox, progress, changed files, or acceptance criteria unless explicitly
  marked as offline fixture mode;
- show live API data or an honest empty/configuration state;
- keep fixture mode only behind `?offline=1`.

### 4. Runtime Route Fix

Ensure `#runtime` maps to the runtime page, not the agents page.

### 5. Mini Code Agent Dogfood Attempt

From the browser:

1. register `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`;
2. create the Mini Code Agent goal;
3. add the three external knowledge sources;
4. generate and apply MCA issues;
5. assign and dispatch `MCA-001` if the web path is ready;
6. record whether dogfood is possible or what is still missing.

## Verification

Automated:

```bash
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
```

Manual:

```text
Open Workbench in browser
Confirm API mode
Use web UI for target registration / goal / source / issue generation
Attempt MCA-001 assignment and dispatch
Inspect event/evidence state
```

## Expected Outcome

After this fix, Ariadne should either:

1. complete the first browser-only dogfood issue generation and assignment
   path; or
2. clearly show the remaining missing web capability, with no fake fixture data
   pretending the dogfood path works.

## Implementation Result

Browser validation was performed against:

```text
http://127.0.0.1:8766/?v=20260618dogfoodfix
```

Completed from the Workbench web UI:

- registered and selected a Mini Code Agent target project;
- created the Mini Code Agent product goal;
- added the external dogfood sources;
- generated a six-ticket issue delta from the active goal and sources;
- applied the issue delta through the web API, creating `ARI-017` through
  `ARI-022`;
- opened `ARI-017` from the issue board and confirmed its Mini Code Agent
  target, acceptance criteria, affected module, and source evidence;
- assigned `ARI-017` to Codex from the web UI;
- clicked the web run action and confirmed it writes a dispatch event that is
  waiting for a local daemon runtime to claim the assignment;
- confirmed `#runtime` renders the runtime page instead of the agents page.

Important bug found during browser validation:

- The fixed bottom mutation preview bar overlapped the `应用任务变更` button.
  The UI looked clickable, but the browser click hit the footer instead of the
  button, so no API request was sent. The fix makes the footer non-interactive
  and adds bottom padding to knowledge columns.

Remaining product gaps:

- The browser path now reaches assignment dispatch, but does not yet run the
  local daemon automatically from the Workbench.
- Real Codex / Claude execution is still gated and was not completed in this
  dogfood pass.
- Source selection is coarse: the issue factory currently uses the active goal
  and provided source IDs, but the UI still needs better per-goal source
  scoping and source selection.
- Inbox recovery and agent configuration remain visible but not yet fully
  product-grade workflows.
