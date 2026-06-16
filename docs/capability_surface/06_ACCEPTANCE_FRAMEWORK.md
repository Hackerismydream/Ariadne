# 06. 能力验收框架

Status: Updated by
[`ADR-0004`](../adr/ADR-0004-ticket-centered-agent-workbench.md).

后续每个 ARI 必须按以下框架验收。

## 1. 产品验收

必须回答：

```text
这个能力是否让 Ariadne 更像 Ticket-centered Agent Workbench？
是否增强了与 Multica 的 issue / agent / runtime / board 对标能力？
是否让知识、反馈或代码状态更明确地更新 ticket backlog？
是否服务 AI Builder 的 Learning-to-Build 场景？
是否减少人工介入？
是否提高 Codex / Claude 执行质量？
```

## 2. Agent 能力验收

至少命中以下一种能力：

```text
Ticket backlog update
Knowledge / feedback planning
Multi-agent routing
Agent assignment
Daemon/runtime
Backend orchestration
Review/eval
Memory retrieval
Skill materialization
Provider capability
Recovery/retry
Autopilot
Board/workbench
```

## 3. 工程验收

必须有：

```text
CLI 命令
数据模型
持久化
测试
README / docs 更新
safety gate
失败路径
```

## 4. 安全验收

真实外部执行必须要求：

```text
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

真实 Feishu 写入必须要求：

```text
FEISHU_ENABLE_WRITE=1
--confirm-write
```

不允许：

```text
auto commit
auto push
auto merge
auto PR
secret commit
silent external execution
```

## 5. Demo 验收

至少能跑：

```bash
pytest
ruff check .
ari doctor v1
ari export board
```

能力相关命令必须可运行。

## 6. 文档验收

每个能力都要在以下位置体现：

```text
README.md
docs/development_report.md
相关 ADR 或 architecture docs
```

## 7. 面试可讲性验收

每个能力都要能解释：

```text
为什么需要它？
它解决了 Agent 系统什么问题？
它和 Multica 什么能力对应？
它如何改变 ticket 状态或 agent runtime？
它体现了什么工程能力？
它当前限制是什么？
```
