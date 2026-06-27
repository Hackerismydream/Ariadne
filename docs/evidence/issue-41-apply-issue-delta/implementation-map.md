# Issue 41 Implementation Map

## Anchors

- CDP observation: `http://localhost:3001/local-dev` was reachable on 2026-06-27, but returned Multica's 404 "Page not found" screen. Per `AGENTS.md`, this phase uses the current plan and parity matrix as the UI-behavior substitute for that unavailable path.
- Multica source comparison:
  - `server/internal/handler/issue.go` projects issues from the issue table with workspace/project/status/metadata filters and keeps metadata in the issue payload.
  - `packages/views/issues/components/issues-page.tsx` narrows the board to the current query scope before board/list rendering.
  - `packages/views/issues/components/issue-detail.tsx` puts project metadata, execution log, attachments, usage, and metadata in the issue detail surface.
  - `server/internal/handler/task_lifecycle.go` binds runtime task lifecycle operations back to the issue, rather than creating a separate work object for the UI.

## Ariadne Mapping

- Multica issue row -> Ariadne `BuildTicket`.
- Multica issue metadata -> Ariadne `BuildTicket.metadata` and `BuildPacket` projection.
- Multica issue board query scope -> Ariadne current `ProjectVersion` mainline BuildTicket set.
- Multica issue detail contextual panels -> Ariadne issue detail fields for target project/version, evidence refs, source refs, acceptance criteria, affected modules, compiler provenance, and build context.
- Multica task lifecycle -> out of scope for #41; Ariadne must not run Codex/Claude here.

## Non-Replication Boundary

- No independent Issue persistence layer.
- No workspace/user/project DB/auth replication from Multica.
- No runtime claim or real agent execution; those remain #42/#43/#44.
- No fake product data in the Workbench path.
