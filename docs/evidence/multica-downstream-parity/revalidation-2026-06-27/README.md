# Multica Downstream Parity Revalidation — 2026-06-27

## Scope

This evidence records a real Multica downstream work-management run for the Ariadne dogfood scenario:

```text
AI Builder wants to build a mini coding agent
  -> create Multica project
  -> attach external GitHub resources
  -> create an issue
  -> assign it to a real Multica agent
  -> local Codex runtime claims task
  -> task reports progress/failure/retry/result
  -> agent writes issue comment
  -> issue moves to in_review
```

This is not Ariadne product closure. It is the Multica reference behavior Ariadne must reproduce locally in Python.

## Multica Objects Created

- Workspace: `local-dev`
- Project: `Ariadne Dogfood: Mini Coding Agent v0.1`
- Project ID: `3de2e771-0049-4fa5-9a05-e124cbf26e9e`
- Resources:
  - `https://github.com/SWE-agent/mini-swe-agent`
  - `https://github.com/e10nMa2k/cc-mini`
- Issue: `LOC-109 Define mini coding agent v0.1 from external references`
- Issue ID: `773afe86-ea82-4c8c-beb2-cb076484f0fd`
- Agent: `Ariadne Implementer`
- Agent ID: `9348ede6-68bf-4e94-86da-641274158d14`
- Runtime: `Codex (192.168.5.116)`

## Result

Final result: **real Multica downstream loop completed with evidence**.

The successful task was:

- Task ID: `18aa1811-4edc-4613-b971-88df69fb25d9`
- Status: `completed`
- Attempt: `2`
- Started: `2026-06-27T10:54:06+08:00`
- Completed: `2026-06-27T10:57:19+08:00`
- Issue final status: `in_review`

The agent wrote a substantive issue comment defining:

- reference takeaways from `mini-swe-agent` and `cc-mini`;
- a v0.1 coding-agent architecture;
- three draft build issues;
- blockers and missing resources.

## Evidence Files

- `project.json`
- `issue.json`
- `runs.json`
- `comments.json`
- `run-messages.json`
- `multica-project-dogfood.png`
- `multica-issue-loc-109.png`
- `multica-agent-implementer.png`
- `multica-inbox-after-run.png`
- matching `.txt` DOM snapshots for each screenshot

## Observed Multica Behaviors

| Surface | Observed Behavior | Evidence |
| --- | --- | --- |
| Project resources | Project stores attached GitHub repos as resources. | `project.json`, project screenshot |
| Issue assignment | Issue assigned to `Ariadne Implementer`. | `issue.json` |
| Task queue | Assignment enqueued task automatically. | `runs.json`, server logs |
| Runtime claim | Codex runtime claimed and started task. | `runs.json`, `run-messages.json` |
| Progress/activity | Agent detail page shows active/recent tasks and run stats. | `multica-agent-implementer.png` |
| Failure taxonomy | Failed attempts recorded typed reasons: `agent_error.provider_server_error`, `api_invalid_request`, `codex_semantic_inactivity`. | `runs.json`, `comments.json` |
| Inbox | Runtime failures appear in Inbox. | `multica-inbox-after-run.png` |
| Retry | Multica retried after `codex_semantic_inactivity` and completed attempt 2. | `runs.json` |
| Issue result | Agent wrote final comment and moved issue to `in_review`. | `comments.json`, `issue.json` |

## Configuration Fix Applied

The first task failed because the copied Codex config still used:

```toml
service_tier = "priority"
```

Current Codex CLI rejected that value. The source config was updated locally to:

```toml
service_tier = "fast"
default-service-tier = "fast"
```

`flex` was also tested, but the provider returned `Unsupported service_tier: flex` for this model/account path. `fast` was required to complete this real run.

## Meaning For Ariadne

This revalidation confirms Ariadne must implement the downstream layer as real work-management semantics, not as static pages:

```text
AgentDefinition
  -> Agent detail fact center
  -> Skill binding
  -> Project resources
  -> Issue assignment
  -> Runtime claim
  -> Run messages / transcript
  -> Failure reason / Inbox
  -> Retry / completion
  -> Issue comment / status update
```

For Ariadne #42/#43/#44, the gate is now concrete:

- assigning an issue in the browser must create a real queued assignment;
- the local daemon must claim exactly that assignment;
- run progress and transcript must flow back to the issue detail page;
- failures must become typed blockers and Inbox items;
- completion must write an evidence-backed comment/result and update current-version progress.

