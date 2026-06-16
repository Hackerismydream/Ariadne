# 03. Ariadne 需要固定的能力面

本文件定义 Ariadne 未来实施时必须坚持的能力面。

## 一级卖点：Goal-driven Multi-Agent Build Team

Ariadne 的卖点是多 Agent，不是单纯 Learning-to-Build。

Learning-to-Build 是 Ariadne 的业务场景。Ariadne 的产品形态是：

```text
Goal-driven Multi-Agent Build Team
```

核心表达：

```text
用户给出一个 Build Goal。
Ariadne 组织多个 Agent 理解目标、读取知识、分析项目、生成 Build Tickets、分配任务、调用 Codex / Claude、Review、Memory、生成下一轮任务。
```

---

## Ariadne 必须支持的能力

## 1. Build Goal

Ariadne 应从 Build Goal 开始，而不是只从 source 或 ticket 开始。

Build Goal 示例：

```text
把 Ariadne 做成对标 Multica 的多 Agent 构建团队。
把真实 Codex path 变成主 demo。
把外部知识转成 Ariadne 自己的下一轮任务。
```

目标能力：

```bash
ari goal create "把 Ariadne 做成对标 Multica 的多 Agent 构建团队"
ari goal attach-source GOAL-001 docs/notes/*.md
ari goal plan GOAL-001
ari goal assign GOAL-001 --to build-team
```

输出：

```text
多个 Build Tickets
优先级
依赖关系
建议 Agent
验收标准
执行顺序
```

---

## 2. Goal-to-Ticket 多 Agent 规划

这是真正体现 Ariadne 区别于 Multica 的地方。

Multica 从 issue 开始。

Ariadne 从 goal 开始。

需要有这些 Agent：

```text
Build Lead Agent：理解目标和拆分方向
Research Agent：读取论文 / 博客 / GitHub README
Knowledge Agent：检索历史 memory / ticket / decision
Project Context Agent：读取当前 repo / README / tests / modules
Planner Agent：生成 Build Tickets / Build Packets
```

目标链路：

```text
Build Goal
  -> Research / Knowledge / Repo Context
  -> Build Tickets
  -> Ticket Assignment
```

---

## 3. Agent Team / Squad Routing

Ariadne 应支持 Build Team，而不是只把 Ticket 分配给单个 Agent。

Build Team 包括：

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

目标命令：

```bash
ari team list
ari goal assign GOAL-001 --to build-team
ari daemon run-once
```

或者：

```bash
ari ticket assign ARI-003 --to build-team
```

Build Lead 负责路由：

```text
哪些 source 给 Research
哪些历史上下文给 Knowledge
哪些 repo 信息给 Project Context
哪些 ticket 给 Codex
哪些结果给 Reviewer
```

---

## 4. Agent Assignment 与 Teammate Mode

现有能力要继续保留并强化：

```text
AgentProfile
TicketAssignment
TicketComment
RuntimeJournal
LocalDaemonWorker
```

产品体验：

```bash
ari ticket assign ARI-003 --to fake-codex
ari daemon run-once
ari ticket comments ARI-003
ari export board
```

这是 Ariadne 对 Multica “agent as teammate”的本地化。

---

## 5. Handoff 从记录升级为调度

当前 handoff 主要是记录：

```text
Build Lead -> Planner
Planner -> Execution
Execution -> Reviewer
Reviewer -> Memory
```

后续要升级为真正 assignment 接力：

```text
Build Lead Assignment 完成 -> 创建 Planner Assignment
Planner Assignment 完成 -> 创建 Execution Assignment
Execution Assignment 完成 -> 创建 Reviewer Assignment
Reviewer pass -> 创建 Memory Assignment
Reviewer needs_fix -> 创建 Execution retry Assignment
```

这样才更像真正的多 Agent 团队。

---

## 6. 真实 Codex Teammate

fake-codex 只是稳定 demo backend。

Ariadne 必须把真实 Codex path 做成主 demo 能力。

目标命令：

```bash
ari ticket assign ARI-003 --to codex
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
```

要求：

```text
生成 handoff
调用 Codex
捕获 stdout / stderr / exit code
捕获 diff / changed files
运行 tests
Reviewer 审查
Memory 写回
Board 展示
```

没有 Codex 或 gate 未开时：

```text
清晰 blocked
不能 fallback fake-codex
不能假装成功
```

---

## 7. Provider Capability Matrix

Ariadne 需要明确管理不同 backend 的能力。

Backend 包括：

```text
fake-codex
dry-run
shell
codex
claude-code
```

每个 backend 要有：

```text
available
command_path
supports_prompt_file
supports_stdin
supports_session_resume
supports_mcp
skill_materialization_strategy
supports_model_selection
supports_reasoning_effort
supports_timeout
supports_diff_capture
supports_test_capture
requires_confirmation
requires_external_execution_gate
```

这会让 Ariadne 更像真实 Agent 平台。

---

## 8. Skill Materialization

现在 skill 主要是出现在 handoff references。

后续需要 materialization：

```text
CodexBackend：把 skill 展开进 handoff 或写入适合 Codex 的目录
ClaudeBackend：把 skill 展开进 Claude prompt / skill dir
ReviewerAgent：把 review-diff skill 变成 checklist
FeishuAgent：把 feishu-write-plan skill 变成 schema
```

Skill 不是文档列表，而是 Agent 执行方法。

---

## 9. Project Resource Boundaries

Project Resource 不应只支持 local_directory。

应扩展为：

```text
local_directory
github_repo
feishu_space
memory_store
source_collection
target_project
```

每个资源要有访问边界：

```text
read_only
read_write
allowed_paths
blocked_paths
requires_confirmation
```

这对安全很重要。

---

## 10. Memory Retrieval

Memory 不能只写入，还要被下一轮使用。

需要支持：

```bash
ari memory search "codex smoke test"
ari goal plan GOAL-001 --use-memory
ari ticket plan ARI-003 --use-memory
```

Planner 应能引用：

```text
历史 Build Tickets
历史 ReviewReports
历史 ExecutionResults
Decision Log
Next Tickets
```

---

## 11. Review / Eval Agent

Reviewer 不应该只是规则检查。

应增强为：

```text
diff 语义总结
验收标准对齐
测试覆盖判断
风险评分
是否需要人工 review
是否生成返工 ticket
是否可进入 memory
```

还要有评估指标：

```text
Build Packet evidence coverage
Acceptance criteria quality
Changed file scope compliance
Execution success rate
Review pass rate
Retry rate
Human intervention count
```

---

## 12. Autopilot

Ariadne 后续可支持定期任务：

```text
weekly review
daily source inbox triage
periodic Codex smoke check
memory summary
next goal generation
```

这不是当前 P0，但属于对标 Multica 的能力面。

---

## 13. Workbench Board

Board 需要从静态结果页走向本地工作台：

```text
Ticket board
Ticket detail
Comments timeline
Assignment panel
Handoff chain
Runtime status
Retry button
Review report
Diff summary
Memory
Next tickets
```

v1.0 可以保持静态 / simple serve，v1.1 再做交互。

