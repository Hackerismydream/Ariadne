# Ticket Run Orchestrator Specification

## Problem

PR #2 has a strong `demo full` chain, but it is not reusable enough.

## Required solution

Create a reusable orchestrator.

Suggested file:

```text
ariadne_ltb/orchestrator.py
```

Suggested API:

```python
class TicketRunOrchestrator:
    def __init__(self, store: AriadneStore) -> None:
        ...

    def run_ticket(
        self,
        ticket_id_or_key: str,
        backend_name: str = "fake-codex",
        target_repo_path: str | None = None,
        command: str | None = None,
        planner: str = "deterministic",
        confirm_execution: bool = False,
    ) -> TicketRunResult:
        ...
```

## Required behavior

`run_ticket()` must:

1. resolve ticket by id or key;
2. load Build Packet if present;
3. create or update Build Packet through planner if missing or requested;
4. write handoff artifact;
5. create Execution AgentRun;
6. execute backend;
7. save ExecutionResult;
8. save execution artifacts;
9. create Reviewer AgentRun;
10. review execution;
11. save ReviewReport artifact;
12. update ticket status;
13. create Memory / Feishu AgentRun;
14. write memory record;
15. generate Feishu dry-run plan;
16. generate next tickets;
17. export board;
18. return a structured result.

## TicketRunResult

Suggested fields:

```text
ticket_id
ticket_key
backend_name
execution_result_id
review_verdict
changed_files
test_exit_code
memory_path
feishu_plan_path
next_tickets_path
board_path
board_html_path
```

## CLI integration

The main command must be:

```bash
ari ticket run <ticket_id_or_key> --backend fake-codex
```

This command must use the orchestrator and complete the whole loop.

Low-level commands can remain, but they are secondary.

## Demo integration

`ari demo full` should:

1. ensure demo target project exists;
2. ingest the fixture sources;
3. select the code_task ticket;
4. call `TicketRunOrchestrator.run_ticket(...)`.

Do not duplicate the full loop in `full_demo.py`.
