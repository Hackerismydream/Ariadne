# Mini Code Agent Source-to-Issue Browser Result

## Environment

- Date: 2026-06-19
- Branch: `codex/typed-source-to-issue-dogfood`
- API URL: `http://127.0.0.1:8767/api/workbench`
- Workbench URL: `http://127.0.0.1:8767/?v=typed-source-dogfood5`

## Flow Result

- Target project: `Mini Code Agent Browser Dogfood`
- Target path: `/Users/martinlos/code/ariadne-dogfood/mini-code-agent-browser`
- Goal: `Build Mini Code Agent v0.1`
- Sources analyzed: 4 browser-created sources
- Source artifacts: 4 artifacts projected into Workbench
  - `knowledge_card`
  - `reference_project_profile`
  - `codebase_snapshot`
- Evidence refs: 4 source-side evidence records projected into Workbench
- Preview id: `backlog_preview_14a06bdc37e3`
- Created issue keys: `MCA-001` through `MCA-010`
- Selected issue: `MCA-001`
- Route decision: not implemented in this slice beyond assignment readiness metadata
- Handoff: not implemented as a persisted frozen packet in this slice
- Assignment: queued assignments now require `ready_to_claim` before daemon claim
- Browser apply result: clicking `应用任务变更` wrote the MCA issue set; Ready page showed `MCA-001` and `MCA-010`

## Failures

- The browser run used the Web API from the browser context for source creation/analyze/preview, not every form field manually.
- Sources page still needs a visible per-source `分析来源` action; analysis currently exists as API and tests.
- Frozen route decision and handoff packet are represented as readiness metadata placeholders, not yet first-class persisted packets.

## Follow-up Tickets

- Persist real `RouteDecision` and immutable handoff packet before assignment enters `ready_to_claim`.
- Add browser action for source analysis rather than requiring API calls.
- Continue from `MCA-001` assignment into real Codex/Claude execution feedback.
