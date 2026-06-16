# ARI-016 Ticket Backlog Update Loop

Status: Implemented.

Implementation notes:

- `BacklogUpdate`, `TicketChange`, `BacklogUpdateTrigger`, and
  `TicketChangeType` are implemented in `ariadne_ltb.models`.
- Backlog updates are persisted as JSONL at `.ariadne/backlog/updates.jsonl`.
- `ari ingest ...` and `ari backlog update --from-source ...` record
  `source_ingest` backlog updates.
- `ari backlog history` shows update rationale, evidence refs, and ticket
  counts.
- `ari ticket supersede <ticket> --reason ...` marks a ticket superseded,
  writes a backlog update, appends a comment, and adds ticket events.
- `ari export board` shows `Ticket Backlog Updates` and per-ticket
  `Backlog Update Trace`.
- The older BuildGoal-first direction remains superseded.

Do not implement a BuildGoal-first root workflow from the old version of this
file. This ticket keeps the historical filename for link stability, but its
current scope is ticket-centered.

## 目标

让 Ariadne 能根据外部知识、执行反馈、Review、Memory 和当前代码状态，持续更新 Build Ticket 列表。

Goal 可以作为方向输入，但不是中心对象。

## 为什么重要

Multica 从已有 issue 开始，并把 issue 分配给 agent。

Ariadne 的差异是：

```text
知识 / 反馈 / 代码状态
  -> 更新 ticket set
  -> agent 执行 ticket
  -> review / memory
  -> 再更新 ticket set
```

## 数据模型

优先新增或强化：

```text
BacklogUpdate
TicketChange
TicketSupersession
TicketPriorityChange
BacklogUpdateReason
```

BacklogUpdate 字段建议：

```text
id
trigger_type
trigger_ref
created_ticket_ids
updated_ticket_ids
superseded_ticket_ids
rationale
evidence_refs
created_at
```

trigger_type：

```text
source_ingest
review_feedback
execution_result
memory_gap
codebase_observation
manual_goal
```

## CLI

优先围绕已有 ticket path：

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari export board
```

可以新增：

```bash
ari backlog update --from-source examples/sources/*.md
ari backlog history
ari ticket supersede ARI-003 --reason "..."
```

不要新增 BuildGoal-first 根命令作为主路径。

## 行为

backlog update 应该：

```text
读取新 source / review / memory / execution result / repo observation
读取已有 tickets 概要
判断新增、更新、降级、拆分、关闭或 supersede 哪些 tickets
写 BacklogUpdate 本地持久化记录
更新相关 ticket comments / event log
让 board 展示 backlog update rationale
```

## 验收

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari export board
```

必须能看到：

```text
ticket set 的变化记录
变化原因
引用的 source / review / memory evidence
board 上的 backlog update trace
```
