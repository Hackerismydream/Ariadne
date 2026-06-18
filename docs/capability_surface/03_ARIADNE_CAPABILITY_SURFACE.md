# 03. Ariadne 需要固定的能力面

Status: Updated by
[`ADR-0004`](../adr/ADR-0004-ticket-centered-agent-workbench.md).

本文件定义 Ariadne 未来实施时必须坚持的能力面。

## 一级卖点：Ticket-centered Agent Workbench

Ariadne 的卖点是一个本地 agent 工作台，不是单纯 Learning-to-Build。

Learning-to-Build 是 Ariadne 的业务场景。Ariadne 的产品形态是：

```text
Ticket-centered Agent Workbench
```

核心表达：

```text
知识、反馈、代码状态和可选目标进入 Ariadne。
Ariadne 更新 Build Ticket 列表。
Agent 通过 assignment、daemon、runtime、handoff、review、memory、board 完成 ticket。
执行结果再反馈到下一轮 ticket 更新。
```

---

## Ariadne 必须支持的能力

## 1. Ticket Backlog Update Loop

Ariadne 应从 Ticket backlog 开始组织工作。Goal 可以作为方向输入，但不能成为 v1.x 的根状态机。

输入示例：

```text
一篇新博客指出 agent teammate 的关键是 task lifecycle + visible progress。
一次 Review 发现 board 仍然不是 issue-centric。
一次真实 Codex / Claude Code 执行失败并产生 blocker。
当前代码库新增了 runtime capability snapshot。
```

输出应该是 ticket set 的增量变化：

```text
新增 ticket
调整优先级
拆分 ticket
降级 ticket
关闭或 supersede ticket
记录 backlog update rationale
```

目标能力：

```bash
ari ingest examples/sources/*.md
ari ticket list
ari ticket assign ARI-003 --to codex --runtime-profile production
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
ari ticket comments ARI-003
ari export board
```

测试和离线回归可以使用 `fake-codex`，但产品验收不能以它作为主路径。

---

## 2. Knowledge / Feedback To Ticket Planning

这是真正体现 Ariadne 区别于 Multica 的地方。

Multica 从已有 issue 开始。

Ariadne 让知识和反馈改变 ticket 列表。

需要有这些 Agent：

```text
Build Lead Agent：理解当前 ticket 状态和更新方向
Research Agent：读取论文 / 博客 / GitHub README
Knowledge Agent：检索历史 memory / ticket / decision
Project Context Agent：读取当前 repo / README / tests / modules
Planner Agent：生成或更新 Build Tickets / Build Packets
```

目标链路：

```text
Knowledge / Feedback / Repo Context
  -> Ticket Backlog Update
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
ari ticket assign ARI-003 --to build-team
ari daemon run-once
```

Build Lead 负责路由：

```text
哪些 source 给 Research
哪些历史上下文给 Knowledge
哪些 repo 信息给 Project Context
哪些 ticket 给 Codex
哪些结果给 Reviewer
哪些反馈更新 ticket backlog
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
ari ticket assign ARI-003 --to codex --runtime-profile production
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution
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

## 6. 真实 Codex / Claude Code Teammate

`fake-codex` 只是测试和离线 fixture backend。

Ariadne 必须把真实 Codex 和 Claude Code path 做成可验证能力。

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

没有 Codex / Claude Code、CLI 未登录、quota 不足、或 gate 未开时：

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
BuildSkill
SkillPack
skill -> handoff snippet
skill -> backend adapter hint
skill -> review checklist
```

---

## 9. Project Resource Boundaries

Agent 不能只拿一堆无边界上下文。

需要清楚定义：

```text
Source documents
Target repo
Allowed paths
Test commands
Memory records
Feishu preview targets
Feishu / GitHub gated write targets
```

---

## 10. Review / Eval Agent

Reviewer 不能只是检查测试是否通过。

它应该检查：

```text
diff 是否符合 ticket
是否超出 allowed paths
tests 是否覆盖验收标准
是否产生新的风险
是否需要 next tickets
```
