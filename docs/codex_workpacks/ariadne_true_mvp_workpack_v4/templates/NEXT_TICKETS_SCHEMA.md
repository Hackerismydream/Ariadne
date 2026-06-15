# Next Tickets Schema

Ariadne should generate next ticket suggestions after each completed ticket run.

Use JSON like:

```json
{
  "source_ticket_id": "",
  "source_ticket_key": "",
  "review_verdict": "pass|needs_fix|blocked|needs_human_review",
  "generated_at": "",
  "next_tickets": [
    {
      "title": "",
      "reason": "",
      "source": "review|memory|failed_check|changed_file|source_type",
      "priority": "low|medium|high",
      "suggested_build_decision": "doc_update|experiment|code_task|architecture_change|watchlist",
      "acceptance_criteria": [],
      "affected_modules": []
    }
  ]
}
```

Rules:

- If review failed, generate fix tickets.
- If review passed, generate improvement / next capability tickets.
- Use changed files and review warnings to ground suggestions.
- Do not generate too many tickets. 3 to 5 is enough.
