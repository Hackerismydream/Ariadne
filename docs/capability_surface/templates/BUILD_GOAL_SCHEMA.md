# Directional Goal Metadata Template

Status: Superseded as a root object template by
[`ADR-0004`](../../adr/ADR-0004-ticket-centered-agent-workbench.md).

Do not implement this as Ariadne's central state machine. If goal information is
needed, attach it as optional directional metadata to tickets, planning
artifacts, or backlog updates.

```json
{
  "directional_goal_ref": "goal_note_or_manual_input",
  "summary": "Make Ariadne better at ticket-centered agent work.",
  "why_now": "New knowledge or feedback suggests the ticket backlog should change.",
  "attached_source_refs": [],
  "related_ticket_ids": [],
  "backlog_update_id": null
}
```
