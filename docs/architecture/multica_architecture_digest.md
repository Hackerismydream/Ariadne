# Multica Architecture Digest

Source studied: `multica-ai/multica` at local checkout `/tmp/multica-ariadne-study`.

## Files Inspected

- `README.md`
- `CLI_AND_DAEMON.md`
- `SELF_HOSTING.md`
- `CONTRIBUTING.md`
- `apps/docs/content/docs/agents.mdx`
- `apps/docs/content/docs/tasks.mdx`
- `apps/docs/content/docs/squads.mdx`
- `apps/docs/content/docs/skills.mdx`
- `apps/docs/content/docs/project-resources.mdx`
- `apps/docs/content/docs/daemon-runtimes.mdx`
- `apps/docs/content/docs/assigning-issues.mdx`
- `apps/docs/content/docs/mentioning-agents.mdx`
- `apps/docs/content/docs/providers.mdx`
- `server/pkg/db/queries/agent.sql`
- `server/pkg/db/queries/project_resource.sql`
- `server/pkg/db/queries/runtime.sql`
- `server/pkg/protocol/events.go`
- `server/pkg/taskfailure/failure.go`
- `server/pkg/taskfailure/classify.go`
- `server/internal/daemon/daemon.go`
- `server/cmd/server/runtime_sweeper.go`
- `packages/core/types/project.ts`
- `packages/core/types/events.ts`

## Architecture Takeaways

Multica treats agents as first-class workspace members. The main work object is
still an issue, but every execution is a separate task with its own lifecycle,
runtime binding, progress stream, result, and failure reason.

The task state machine in `tasks.mdx` and `server/pkg/db/queries/agent.sql` is
the central architecture boundary:

```text
queued -> dispatched -> running -> completed
queued/dispatched/running -> failed|cancelled
dispatched -> waiting_local_directory -> running
```

Multica's daemon/runtime split matters more than the UI. `CLI_AND_DAEMON.md`
and `daemon-runtimes.mdx` describe local daemons that detect available agent
CLIs, register runtime capability, heartbeat, claim work, execute locally, and
report progress. The server coordinates, but code and credentials stay local.

Failure reasons are structured. `server/pkg/taskfailure/failure.go` defines a
wire-stable taxonomy that separates platform/runtime failures from agent-side
failures. `server/pkg/taskfailure/classify.go` maps free-form runner errors
into that taxonomy.

Project resources are typed pointers. `project-resources.mdx`,
`server/pkg/db/queries/project_resource.sql`, and
`packages/core/types/project.ts` show a discriminator pattern:
`resource_type` plus typed `resource_ref`. The two current core types are
`github_repo` and `local_directory`.

The `local_directory` resource deliberately trades parallelism for locality:
it runs in the user's existing checkout, validates path safety, and serializes
tasks on the same resolved directory. It does not auto-stash, auto-commit, or
create PRs.

Skills are knowledge packs, not runtime APIs. `skills.mdx` and `providers.mdx`
show that Multica treats skills as provider-specific context materialization.
Ariadne should keep BuildSkill packs local and visible in handoffs.

Squad leaders are routers, not implementers. `squads.mdx` maps cleanly to
Ariadne's Build Lead: decide route, write a route decision, delegate, and stop.

Progress events are product data. `server/pkg/protocol/events.go` includes
task lifecycle events and progress/message events so the board can show a
timeline instead of only final artifacts.

## Ariadne Mapping

| Multica Object | Ariadne Object |
|---|---|
| Issue | Build Ticket |
| Task | Agent Run |
| Runtime | Execution backend capability |
| Project Resource | ProjectResource JSON |
| Skill | BuildSkill pack |
| Squad leader | Build Lead route decision |
| Task progress events | Ticket event log progress events |
| Failure reason | FailureReason enum |

## Deliberate Non-Alignment

Ariadne should not copy Multica's web app, Go server, PostgreSQL queue,
WebSocket daemon protocol, cloud runtimes, auth, billing, or workspace
permissions. Ariadne remains a local Python workbench with JSON persistence.
