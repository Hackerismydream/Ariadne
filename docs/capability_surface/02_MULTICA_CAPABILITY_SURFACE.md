# 02. Multica 能力面拆解

本文件固定 Ariadne 对 Multica 的理解。Codex 后续实现时，不应该只理解“Multica 有上游调度”，而要吸收 Multica 的完整 Agent 工作管理能力。

## 1. Agent as teammate

Multica 的核心不是“有多个 Agent”，而是让 coding agent 像 teammate 一样工作。

能力特征：

```text
Agent 有身份
Agent 能被 assign issue
Agent 能评论
Agent 能汇报进度
Agent 能报告 blocker
Agent 能更新状态
Agent 出现在 board / conversation / task timeline 里
```

Ariadne 对应能力：

```text
AgentProfile
TicketAssignment
TicketComment
LocalDaemonWorker
Board: Agent Assignment / Comments / Journal
```

Ariadne 仍需增强：

```text
Agent Team / Squad 概念
Build Lead 自动路由
Agent 接力 assignment
Codex 作为真实 teammate 的主 demo
```

---

## 2. Issue / Task lifecycle

Multica 的 issue 是协作载体，task 是每一次 agent run 的工作单元。

能力特征：

```text
issue 可以多次 assign / mention / rerun
task 有 queue / claimed / running / completed / failed / cancelled 等状态
task 和 issue 分离
task failure 可分类
task 可 retry / timeout / recover
```

Ariadne 对应能力：

```text
BuildTicket
TicketAssignment
AgentRun
RuntimeEvent
ExecutionResult
FailureReason
Retry assignment
```

Ariadne 仍需增强：

```text
更严格 task lifecycle
retryable / non-retryable 策略
stage checkpoint
artifact idempotency
resume from stage
```

---

## 3. Daemon / Runtime 管理

Multica 的执行不在 server 内部，而是由本地 daemon 认领 task 并调用本地 coding tools。

能力特征：

```text
local daemon
runtime capability
heartbeat
runtime availability
claim / dispatch
local tool execution
stale runtime cleanup
```

Ariadne 对应能力：

```text
LocalDaemonWorker
WorkerHeartbeat
runtime journal
backend doctor
RuntimeCapability
DirectoryLock
```

Ariadne 仍需增强：

```text
更真实的长期 daemon
heartbeat + stage checkpoint
stale worker 自动诊断
resume / retry 更强
多 worker 暂不做，但要文档解释边界
```

---

## 4. Provider capability matrix

Multica 不只是“支持多个 coding tools”，而是理解不同 provider 的能力差异。

能力特征：

```text
provider 是否可用
是否支持 prompt file
是否支持 stdin
是否支持 session resume
是否支持 MCP
技能注入方式
模型选择
reasoning 参数
timeout
stderr / exit code 语义
```

Ariadne 对应能力：

```text
fake-codex / dry-run / shell / codex / claude-code
backend doctor
RuntimeCapability
Command template
```

Ariadne 仍需增强：

```text
ProviderCapabilityMatrix
Codex / Claude 具体能力字段
命令模板兼容诊断
provider-specific skill materialization
真实 Codex 主 demo
```

---

## 5. Skills

Multica 的 Skills 是 agent 工作方法包，不是普通文档。

能力特征：

```text
SKILL.md
workspace skills
local skills
agent 执行时注入 skill
可复用工作方法
```

Ariadne 对应能力：

```text
.skills/
BuildSkill
codex-handoff
review-diff
feishu-write-plan
handoff skill references
```

Ariadne 仍需增强：

```text
Skill materialization
Codex skill 注入方式
Claude skill 注入方式
Reviewer skill checklist
Feishu write skill schema
```

---

## 6. Squads / Leader routing

Multica 的 Squad 让用户不必总是手动选 agent，而是把 issue 分配给 squad，由 leader 判断谁接手。

能力特征：

```text
Squad
Leader Agent
members
leader reads issue
leader routes to best agent
```

Ariadne 对应能力应升级为：

```text
Build Team
Build Lead Agent
Research Agent
Knowledge Agent
Project Context Agent
Planner Agent
Execution Agent
Reviewer Agent
Memory Agent
```

Ariadne 仍需实现：

```text
ari goal assign GOAL-001 --to build-team
Build Lead 自动生成 tickets
Build Lead 自动分配 assignments
Handoff 从记录变成真实 assignment 接力
```

---

## 7. Project resources

Multica 把项目上下文作为 typed resources，而不是自由文本。

能力特征：

```text
github_repo
local_directory
resource attached to project
agent 执行时获得 scoped context
```

Ariadne 对应能力：

```text
ProjectResource.local_directory
target_repo_path validation
project resources snapshot
```

Ariadne 仍需增强：

```text
github_repo resource
feishu_space resource
memory_store resource
source_collection resource
resource-level access policy
```

---

## 8. Comments / Conversation surface

Multica 的 agent 工作过程能被人在 conversation surface 看到。

能力特征：

```text
comments
agent progress
blocker report
human intervention
mentions
status updates
```

Ariadne 对应能力：

```text
TicketComment
progress / blocker / review / memory / handoff comments
ari ticket comments
board comments section
```

Ariadne 仍需增强：

```text
更可读的 comment timeline
Human approval comments
Reviewer 返工评论
comment -> action trigger 暂不做，但可规划
```

---

## 9. Board / Workbench UI

Multica 的 board 让 agent 工作可视化。

能力特征：

```text
Ticket board
Agent status
Runtime status
Progress timeline
Comments
Task state
```

Ariadne 对应能力：

```text
static board
board serve
Agent Assignment / Comments / Runtime Journal / Handoffs / Memory / Next Tickets
```

Ariadne 仍需增强：

```text
本地交互式 board
ticket detail
assign / retry / comment button
review / diff view
无需生产级 UI，但需要 demo 质感
```

---

## 10. Autopilot / recurring work

Multica 有 autopilot 思想：定时或事件触发 agent 创建和执行工作。

能力特征：

```text
cron
webhook
manual run
recurring review
status report
```

Ariadne 对应未来能力：

```text
weekly project review
auto next ticket generation
daily source inbox triage
periodic Codex smoke check
periodic memory summary
```

Ariadne v1 可以不实现完整 autopilot，但应作为后续能力保留。

---

## 总结

Multica 的核心能力面是：

```text
Agent teammate
Task lifecycle
Daemon runtime
Provider capability
Skills
Squads
Project resources
Comments
Board
Autopilot
```

Ariadne 不应该只做“上游调度”。Ariadne 的差异是让外部知识、执行反馈、Review、Memory 和代码状态持续更新 Ticket backlog，但它也必须具备这些 Agent 工作管理能力，才能像真正的大厂 Agent 项目。
