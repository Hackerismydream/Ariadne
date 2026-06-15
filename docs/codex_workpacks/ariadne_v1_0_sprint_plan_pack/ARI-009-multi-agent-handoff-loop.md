# ARI-009 — Multi-Agent Handoff Loop

## 目标

让 Ariadne 不只是“一个 Agent 接一个 Ticket 跑完整流程”，而是能看到多个 Agent 在同一个 Ticket 下接力工作。

现在的状态：

```text
用户把 Ticket 分配给 fake-codex
daemon 调用 orchestrator
orchestrator 内部完成 planner / execution / review / memory
```

这虽然能跑，但 Agent 团队感还不够。需要把内部阶段变成可见的 Agent handoff。

## 需要实现的能力

### 1. AgentHandoff 模型

新增：

```python
class HandoffStatus(str, Enum):
    CREATED = "created"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class AgentHandoff(AriadneModel):
    id: str
    ticket_id: str
    ticket_key: str
    from_agent: str
    to_agent: str
    from_assignment_id: str | None = None
    to_assignment_id: str | None = None
    reason: str
    payload_ref: str | None = None
    status: HandoffStatus = HandoffStatus.CREATED
    created_at: str = Field(default_factory=utc_now)
    completed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

存储：

```text
.ariadne/handoffs/<handoff_id>.json
```

### 2. Handoff 事件

在 orchestrator 中写出这些 handoff：

```text
Human / Build Lead -> Planner
Planner -> Execution
Execution -> Reviewer
Reviewer -> Memory
Memory -> Build Lead / Next Tickets
```

不要求真正并发，也不要求每个 handoff 都创建独立 queued assignment；但必须：

1. 写 handoff artifact / model。
2. 写 comment。
3. 写 runtime journal。
4. Board 展示。

### 3. Reviewer 返工逻辑

如果 Reviewer verdict 是 `needs_fix`，生成：

```text
Reviewer -> Execution
```

并创建一个 retry assignment 或 next ticket suggestion。

如果是 `pass`，生成：

```text
Reviewer -> Memory
```

### 4. Handoff CLI

新增：

```bash
ari ticket handoffs <ticket_id_or_key>
```

显示：

```text
from_agent
to_agent
reason
status
payload_ref
```

### 5. Comment 表现

Ticket comments 中应能看到类似：

```text
Build Lead -> Planner: 需要根据 source 生成 Build Packet。
Planner -> Execution: 已生成 handoff，交给 fake-codex。
Execution -> Reviewer: 已产生 diff 和测试结果。
Reviewer -> Memory: verdict=pass，可以写回。
Memory -> Build Lead: 已生成 next tickets。
```

## 验收标准

测试覆盖：

1. `ticket run` 生成 handoff chain。
2. `assign + daemon run-once` 生成 handoff chain。
3. `ari ticket handoffs ARI-003` 可以显示。
4. Board 有 Agent Handoff 区块。
5. Reviewer needs_fix 时会生成返工 handoff 或 next ticket。
6. 不破坏 fake-codex 正常通过路径。

## Board 要求

Board 新增：

```text
Agent Handoffs
```

展示：

```text
from -> to
reason
status
payload
created_at
```

## 文档要求

README 中解释：

```text
Ariadne 的 agent team 是通过 assignment + handoff 实现的。
Assignment 表示 Ticket 分配给谁。
Handoff 表示同一 Ticket 内部不同 agent 之间的交接。
```
