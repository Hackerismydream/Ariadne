# ARI-008 — Retry Queue and Safe Recovery

## 目标

让失败或 blocked 的 Assignment 可以安全重试，并让 `runtime recover` 不只是打印信息，而是能给出明确的下一步。

当前状态：

```text
Assignment 可以 queued / claimed / running / done / blocked / failed
runtime recover 有保守 ResumePlan
```

但还缺：

```text
retry queue
attempt chain
retry reason
safe retry policy
resume checkpoint
```

## 需要实现的能力

### 1. Assignment retry chain

扩展 `TicketAssignment`：

```python
parent_assignment_id: str | None = None
attempt: int = 1
retry_reason: str | None = None
retry_policy: str | None = None
```

如果已有 attempt 字段，可以复用。

### 2. Retry 命令

新增 CLI：

```bash
ari assignment list
ari assignment show <assignment_id>
ari assignment retry <assignment_id>
ari ticket retry <ticket_id_or_key>
```

行为：

```bash
ari ticket retry ARI-003
```

应该：

1. 找到该 Ticket 最新 blocked / failed assignment。
2. 判断是否允许重试。
3. 创建新的 queued assignment。
4. parent_assignment_id 指向旧 assignment。
5. attempt + 1。
6. 写 comment：retry created。
7. 写 journal：retry_created。
8. 不覆盖旧 assignment。

### 3. Safe retry policy

实现基本策略：

可以自动重试：

```text
runtime_offline
timeout
command_unavailable
review_failed
```

需要人工确认或默认 blocked：

```text
scope_violation
invalid_resource
resource_locked
unknown
external_execution_blocked
```

命令支持：

```bash
ari ticket retry ARI-003 --force
ari assignment retry <id> --force
```

只有 `--force` 才能对不安全 failure 创建 retry。

### 4. ResumePlan 增强

`runtime recover` 需要输出：

```text
ticket
latest assignment
assignment status
failure reason
safe to retry?
recommended command
```

例如：

```text
ARI-003 blocked review_failed
recommended: ari ticket retry ARI-003
```

### 5. Resume 不要重复已完成工作

如果 ticket 已经 done，`ticket resume` 应该返回：

```text
already done, no resume needed
```

如果 assignment done，不要重新执行。

如果 assignment blocked 且 safe retry，推荐 retry，不要直接重放。

### 6. Runtime Journal

新增事件类型：

```text
retry_requested
retry_created
retry_blocked
resume_plan_created
```

每次 retry 都要写 journal。

## 验收标准

必须通过：

```bash
ari ticket retry ARI-003
ari assignment list
ari assignment show <assignment_id>
```

测试覆盖：

1. blocked assignment 可以 retry。
2. retry 不覆盖旧 assignment。
3. retry attempt +1。
4. parent_assignment_id 正确。
5. unsafe failure 没有 `--force` 时拒绝。
6. `--force` 可以创建 retry。
7. board 展示 retry chain。
8. runtime recover 给出 retry 建议。

## Board 要求

Board 中新增或增强：

```text
Assignment Retry Chain
```

展示：

```text
assignment id
status
attempt
parent
failure reason
retry reason
created_at
ended_at
```

## 文档要求

README 增加：

```bash
ari ticket retry ARI-003
ari assignment list
```

说明 retry 不会覆盖历史 assignment。
