# Issue 40 Three Anchors

## 1. CDP observation

- URL attempted: `http://localhost:3001/local-dev/issues`
- Result: Multica redirected to `/login`; the visible page is the unauthenticated sign-in screen with an email input and disabled Continue button.
- Screenshot: `/tmp/ariadne-issue40-multica-issues-anchor.png`

The current environment cannot observe the authenticated issue board directly. Per `AGENTS.md`, this phase uses the current plan, parity matrix, and local Multica source as the substitute anchor input.

## 2. Multica source read

Files read under `/Users/martinlos/code/multica`:

- `server/internal/handler/issue.go`
  - `IssueResponse` is a product work-object projection with identifier, title, status, priority, assignee, project, metadata, labels, and dates.
  - Issue listing supports filters for status, priority, assignee, creator, project, metadata, and open-only views.
- `server/internal/handler/task_lifecycle.go`
  - Issue execution is driven through task lifecycle endpoints, with rerun support targeting a specific task row.
- `packages/views/issues/components/board-card.tsx`
  - The board card shows priority, identifier, agent activity, title, description, project/labels, assignee, date, and progress.
- `packages/views/issues/components/execution-log-section.tsx`
  - Issue detail separates active task runs from past task runs and makes execution state visible.
- `packages/views/issues/components/issue-detail.tsx`
  - Raw metadata is inspectable from the issue detail surface.

## 3. Ariadne implementation mapping

Multica's issue board maps to Ariadne's BuildTicket-centered current-version projection, not to a new Issue persistence layer.

- Source analysis writes `SourceArtifact` and `SourceEvidence` records from real repository/text analysis.
- Issue Delta remains `BacklogPreview.operations` projected in Workbench `#plan-changes`.
- Applying the delta creates or updates BuildTickets; `/api/issues` continues to project BuildTickets.
- The compiler must use selected Project Version context, source artifacts, source evidence, and target codebase snapshot.
- Fallback compilation is allowed only when provenance says it is deterministic fallback; it cannot masquerade as LLM planning.
- The old mini-code-agent issue template is outside the product path and must not be used for #40 acceptance.
