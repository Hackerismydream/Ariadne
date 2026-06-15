# Multica Reading Plan

Clone or inspect the Multica repository:

```bash
git clone https://github.com/multica-ai/multica /tmp/multica
cd /tmp/multica
```

If cloning is not possible, use GitHub file browsing/search.

## Read docs first

Read:

```text
README.md
README.zh-CN.md if useful
CLI_AND_DAEMON.md
SELF_HOSTING.md
CONTRIBUTING.md
LICENSE

apps/docs/content/docs/agents.mdx
apps/docs/content/docs/tasks.mdx
apps/docs/content/docs/squads.mdx
apps/docs/content/docs/skills.mdx
apps/docs/content/docs/project-resources.mdx
apps/docs/content/docs/daemon-runtimes.mdx
apps/docs/content/docs/assigning-issues.mdx
apps/docs/content/docs/mentioning-agents.mdx
apps/docs/content/docs/providers.mdx
```

## Read server/runtime code

Inspect at least:

```text
server/internal/daemon/
server/internal/handler/
server/internal/service/
server/internal/daemonws/
server/internal/realtime/
server/internal/events/
server/pkg/protocol/
server/pkg/taskfailure/
server/cmd/server/runtime_sweeper.go
server/pkg/db/
```

Search:

```bash
rg "AgentTask|TaskQueue|ClaimTask|StartTask|CompleteTask|FailTask|MaybeRetryFailedTask"
rg "RecoverOrphanedTasks|runtime_sweeper|heartbeat|last_seen|liveness"
rg "ProjectResource|local_directory|github_repo|resource_ref|resource_type"
rg "Skill|SKILL.md|local skill|workspace skill"
rg "Squad|leader|is_leader_task|force_fresh_session"
rg "session_id|work_dir|PriorSessionID|PriorWorkDir"
rg "failure_reason|taskfailure|timeout|runtime_offline|runtime_recovery"
rg "ReportProgress|ReportTaskMessages|usage|token"
rg "mention|trigger_comment|TriggerComment"
```

## Read frontend only for concepts

Do not copy the UI.

Skim:

```text
apps/web/
```

Look only for:

```text
Board concepts
Issue status surfaces
Execution timeline
Runtime status
Assignee/agent/squad interaction
```

## What to extract

For each major architectural element, write down:

```text
What problem it solves
Domain object(s)
Lifecycle
Failure modes
Ariadne equivalent
Whether Ariadne should implement now, defer, or avoid
```

Do not copy code.
