# 04. Ariadne 核心对象模型

Status: Updated by
[`ADR-0004`](../adr/ADR-0004-ticket-centered-agent-workbench.md).

本文件定义 Ariadne 面向 Multica 对标时应固定的核心对象。

## 1. BuildTicket

工作载体，对应 Multica Issue。它是 Ariadne v1.x 的中心对象。

```python
class BuildTicket:
    id: str
    key: str
    title: str
    description: str
    source_type: str
    source_ref: str
    status: str
    priority: str
    owner_agent: str
    directional_goal_ref: str | None
    build_packet_id: str | None
    assignment_ids: list[str]
    agent_run_ids: list[str]
    artifact_ids: list[str]
    event_log: list[TicketEvent]
    metadata: dict
```

状态：

```text
new
planned
assigned
running
blocked
reviewed
done
superseded
cancelled
```

---

## 2. SourceDocument

外部知识输入。

```python
class SourceDocument:
    id: str
    source_type: str
    title: str
    path_or_url: str
    content_hash: str
    summary: str
    metadata: dict
```

source_type：

```text
paper
blog
github_repo
note
office_hour
review
```

---

## 3. BuildPacket

知识、反馈、代码状态或可选目标到构建任务的结构化转换。

```python
class BuildPacket:
    id: str
    ticket_id: str
    source_summary: str
    insight: str
    evidence: list[Evidence]
    project_relevance: str
    build_decision: str
    tasks: list[str]
    acceptance_criteria: list[str]
    affected_modules: list[str]
    risks: list[str]
    assumptions: list[str]
    confidence: float
    metadata: dict
```

build_decision：

```text
archive
watchlist
doc_update
experiment
code_task
architecture_change
reject_for_now
```

---

## 4. BacklogUpdate

Ticket 列表的版本化变化记录。

```python
class BacklogUpdate:
    id: str
    trigger_type: str
    trigger_ref: str
    created_ticket_ids: list[str]
    updated_ticket_ids: list[str]
    superseded_ticket_ids: list[str]
    rationale: str
    evidence_refs: list[str]
    created_at: str
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

---

## 5. Optional Directional Goal

Goal 是方向输入，不是中心状态机。

如果后续需要记录 goal，应作为 ticket/backlog update 的 metadata 或独立 artifact，而不是替代 BuildTicket、TicketAssignment、AgentRun。

---

## 6. AgentProfile

可被分配任务的 Agent 队友。

```python
class AgentProfile:
    id: str
    name: str
    role: str
    backend_name: str | None
    planner_name: str
    description: str
    capabilities: list[str]
    default_confirm_execution: bool
    enabled: bool
```

内置 Agent：

```text
build-lead
research
knowledge
project-context
planner
fake-codex
codex
claude-code
reviewer
memory
```

---

## 7. BuildTeam

对应 Multica Squad 的 Ariadne 版本。

```python
class BuildTeam:
    id: str
    name: str
    leader_agent_id: str
    member_agent_ids: list[str]
    routing_policy: str
    enabled: bool
```

---

## 8. TicketAssignment

Ticket 被分配给 Agent 或 Team。

```python
class TicketAssignment:
    id: str
    ticket_id: str
    ticket_key: str
    agent_id: str
    agent_name: str
    backend_name: str | None
    planner_name: str
    status: str
    priority: str
    parent_assignment_id: str | None
    attempt: int
    claimed_by_runtime_id: str | None
    failure_reason: str | None
    blocker: str | None
    metadata: dict
```

状态：

```text
queued
claimed
running
blocked
done
failed
cancelled
```

---

## 9. AgentHandoff

Agent 接力记录，后续应能驱动 assignment。

---

## 10. TicketComment / RuntimeEvent / Artifact

这些对象让 agent 工作可见、可审计、可恢复：

```text
TicketComment: progress / blocker / review / memory / recovery
RuntimeEvent: claim / execute / review / board export / failure
Artifact: handoff / execution result / review / memory / next tickets / route decision
```
