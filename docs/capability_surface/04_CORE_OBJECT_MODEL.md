# 04. Ariadne 核心对象模型

本文件定义 Ariadne 面向 Multica 对标时应固定的核心对象。

## 1. BuildGoal

Ariadne 相比 Multica 的上游差异对象。

Multica 从 Issue 开始，Ariadne 从 Build Goal 开始。

```python
class BuildGoal:
    id: str
    key: str
    title: str
    description: str
    success_criteria: list[str]
    source_refs: list[str]
    project_context_refs: list[str]
    status: str
    generated_ticket_ids: list[str]
    assigned_team_id: str | None
    created_at: str
    updated_at: str
```

状态：

```text
created
analyzing
planned
assigned
running
blocked
done
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

## 3. BuildTicket

工作载体，对应 Multica Issue。

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
    build_goal_id: str | None
    build_packet_id: str | None
    agent_run_ids: list[str]
    artifact_ids: list[str]
    event_log: list[TicketEvent]
    metadata: dict
```

---

## 4. BuildPacket

知识到构建的结构化任务。

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

## 5. AgentProfile

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

## 6. BuildTeam

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

默认 team：

```text
build-team
```

成员：

```text
Build Lead
Research
Knowledge
Project Context
Planner
Execution
Reviewer
Memory
```

---

## 7. TicketAssignment

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

## 8. AgentHandoff

Agent 接力记录，后续应能驱动 assignment。

```python
class AgentHandoff:
    id: str
    ticket_id: str
    from_agent: str
    to_agent: str
    from_assignment_id: str | None
    to_assignment_id: str | None
    reason: str
    payload_ref: str | None
    status: str
    created_at: str
```

目标：

```text
记录 -> 调度
```

即从仅记录 handoff，升级到 handoff 产生下一步 assignment。

---

## 9. RuntimeCapability / ProviderCapability

Backend 能力矩阵。

```python
class ProviderCapability:
    backend_name: str
    available: bool
    command_path: str | None
    supports_prompt_file: bool
    supports_stdin: bool
    supports_session_resume: bool
    supports_mcp: bool
    skill_materialization_strategy: str
    supports_model_selection: bool
    supports_reasoning_effort: bool
    supports_timeout: bool
    supports_diff_capture: bool
    supports_test_capture: bool
    requires_confirmation: bool
    requires_external_execution_gate: bool
```

---

## 10. BuildSkill

Agent 工作方法包。

```python
class BuildSkill:
    id: str
    name: str
    description: str
    applies_to_agent_roles: list[str]
    applies_to_backend_names: list[str]
    body_markdown: str
    materialization_strategy: str
```

---

## 11. MemoryRecord

项目记忆。

```python
class MemoryRecord:
    id: str
    ticket_id: str
    build_goal_id: str | None
    title: str
    decision_log_entry: str
    build_summary: str
    review_summary: str
    source_refs: list[str]
    artifact_refs: list[str]
    next_actions: list[str]
```

---

## 12. ReviewReport

执行结果审查。

```python
class ReviewReport:
    id: str
    ticket_id: str
    verdict: str
    passed_checks: list[str]
    failed_checks: list[str]
    warnings: list[str]
    required_fixes: list[str]
    risk_score: float | None
    quality_score: float | None
```

---

## 13. Autopilot

周期性任务定义。

```python
class Autopilot:
    id: str
    name: str
    trigger_type: str
    schedule: str | None
    goal_template: str
    enabled: bool
    last_run_at: str | None
```

v1 可不实现完整 Autopilot，但需要作为后续设计保留。

