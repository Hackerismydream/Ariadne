# Project Version Delivery Closure Ledger

Date: 2026-06-28

## Purpose

The Closure Ledger is the single evidence object that answers:

```text
Did Ariadne advance the current target project version through the browser
Project Version Delivery loop?
```

The current closure campaign accepts only:

```text
status: REAL_CLOSED
```

`BLOCKED_WITH_EVIDENCE` is useful for debugging but is not completion for this
campaign because the owner requires real Codex/Claude code modification.

## Ownership

The ledger is written by the browser dogfood verifier:

```bash
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real
```

The verifier must drive Workbench like a user. It must not patch `.ariadne`
files directly, call internal APIs as a replacement for browser actions, or use
CLI-only evidence as product closure.

## Required Location

Each dogfood run writes a run directory:

```text
.ariadne/dogfood/browser-<timestamp>/
```

The canonical ledger path inside that directory is:

```text
closure-result.json
```

PR evidence may copy the ledger and screenshots into:

```text
docs/evidence/<issue-or-campaign>/
```

## Required Status Values

### REAL_CLOSED

The target project repository was modified by a real Codex or Claude backend,
tests were run, review evidence was written, and Workbench displays the current
version progress.

### BLOCKED_WITH_EVIDENCE

Allowed only as a stopped goal state requiring owner intervention. It is not a
successful campaign result.

Valid external blockers:

- Codex CLI unavailable.
- Claude CLI unavailable.
- Required backend not logged in.
- Quota or rate limit prevents real code modification.
- Invalid backend config such as unsupported service tier.
- Target repo permission or git state prevents a safe edit.

Invalid blockers that must be fixed:

- stale browser selector;
- missing Workbench action;
- source not analyzed;
- issue delta not generated;
- apply did not create current-version BuildTickets;
- assignment not created;
- daemon claims wrong assignment;
- handoff empty or not written;
- evidence not returned to Workbench;
- closure ledger missing required fields;
- fake/demo/dry-run execution used as product path.

## Required Schema

The ledger should be JSON with at least these fields:

```json
{
  "schema_version": "ariadne.project_version_closure.v1",
  "status": "REAL_CLOSED",
  "created_at": "",
  "workbench_url": "http://127.0.0.1:8766/",
  "project": {
    "project_id": "",
    "title": "",
    "goal": "",
    "target_version": "",
    "project_version_id": ""
  },
  "target_repo": {
    "path": "/Users/martinlos/code/ariadne-dogfood/mini-code-agent",
    "before_commit": "",
    "after_commit": "",
    "git_status_before": "",
    "git_status_after": ""
  },
  "sources": [
    {
      "source_id": "",
      "type": "",
      "uri_or_path": "",
      "artifact_ids": [],
      "evidence_refs": []
    }
  ],
  "issue_delta": {
    "preview_id": "",
    "compiler_mode": "",
    "applied_at": "",
    "item_count": 0,
    "applied_issue_keys": []
  },
  "selected_issue": {
    "ticket_id": "",
    "ticket_key": "",
    "title": "",
    "acceptance_criteria": [],
    "affected_modules": [],
    "source_evidence_refs": []
  },
  "assignment": {
    "assignment_id": "",
    "agent_id": "",
    "agent_name": "",
    "backend_name": "codex",
    "runtime_profile": "",
    "status": ""
  },
  "handoff": {
    "artifact_id": "",
    "path": "",
    "contains_goal": true,
    "contains_evidence": true,
    "contains_allowed_paths": true,
    "contains_test_command": true
  },
  "execution": {
    "execution_result_id": "",
    "backend_name": "codex",
    "command_summary": "",
    "exit_code": 0,
    "stdout_artifact_path": "",
    "stderr_artifact_path": "",
    "provider_failure_kind": null,
    "changed_files": [],
    "git_diff_artifact_path": "",
    "test_command": "",
    "test_exit_code": 0,
    "test_stdout_artifact_path": "",
    "test_stderr_artifact_path": ""
  },
  "review": {
    "review_report_id": "",
    "verdict": "",
    "summary": "",
    "artifact_path": ""
  },
  "inbox": {
    "open_item_ids": [],
    "resolved_item_ids": []
  },
  "memory": {
    "record_ids": [],
    "artifact_paths": []
  },
  "next_issues": {
    "artifact_path": "",
    "suggested_issue_count": 0
  },
  "workbench_evidence": {
    "screenshots": [],
    "api_snapshots": [],
    "console_log_path": ""
  },
  "merge_gate": {
    "eligible": true,
    "checks": []
  }
}
```

## Invariants

The ledger is valid only when all invariants hold:

1. `target_repo.path` is `/Users/martinlos/code/ariadne-dogfood/mini-code-agent`.
2. `target_repo.before_commit` and `target_repo.after_commit` differ, or
   `git_status_after` shows an intentional uncommitted target repo diff caused
   by the backend run.
3. `execution.backend_name` is `codex` or `claude-code`.
4. `execution.changed_files` is non-empty.
5. `execution.git_diff_artifact_path` exists and contains target repo code diff.
6. `execution.test_command` was run and `test_exit_code` is recorded.
7. `review.verdict` exists.
8. `selected_issue.source_evidence_refs` is non-empty.
9. `issue_delta.applied_issue_keys` includes `selected_issue.ticket_key`.
10. Workbench screenshots or API snapshots prove the same project version,
    issue, assignment, backend, execution, and review.

## Relationship To Existing Objects

Do not create a separate Issue persistence model for the ledger. The ledger
links existing Ariadne objects:

```text
ProjectVersion
  -> SourceDocument / SourceArtifact
  -> Issue Delta preview
  -> BuildTicket current-version issue set
  -> TicketAssignment
  -> AgentDefinition
  -> AgentRun / ExecutionResult
  -> ReviewReport
  -> InboxItem
  -> MemoryRecord
  -> NextTickets artifact
```

The ledger is an evidence artifact, not a new source of truth.

## Rollback

If ledger generation writes incorrect evidence:

1. Do not edit the ledger by hand to claim success.
2. Fix the product or verifier defect.
3. Re-run the browser verifier.
4. Keep the failed ledger as evidence if it explains a blocker.

