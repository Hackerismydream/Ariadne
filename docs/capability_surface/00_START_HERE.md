# Ariadne Capability Surface Pack

Status: Updated by
[`ADR-0004`](../adr/ADR-0004-ticket-centered-agent-workbench.md).

本包用于固定 Ariadne 后续实施时的能力面。

它不是单个小功能的需求包，而是给 Codex 的“产品能力面冻结文档”。后续任何开发任务都应该先遵守这里的定位、对标、对象模型、能力优先级和验收标准。

## 当前定位

Ariadne 不是普通 RAG，不是会议总结器，也不是重新造 Codex。

Ariadne 是一个面向 AI Builder 的 **Ticket-centered Agent Workbench**。

它让外部知识、项目上下文、历史记忆、执行反馈和 Review 持续更新 Build Ticket 列表，再把 Ticket 分配给 Research、Knowledge、Planner、Execution、Reviewer、Memory 等 Agent，通过本地 runtime 完成软件迭代。

Goal 可以作为方向输入，但不是 Ariadne v1.x 的中心对象。Ticket 才是工作中心。

## 固定对标

Ariadne 固定对标 Multica。

Multica 是 issue-centered agent work management：

```text
Issue -> Assign to Agent -> Agent executes -> Progress / Review / Result
```

Ariadne 是 ticket-centered local agent workbench：

```text
Knowledge / Feedback / Codebase / Optional Goal
  -> update Ticket backlog
  -> Assign Ticket to Agent
  -> Codex / Claude / fake-codex executes
  -> Review / Comments / Memory / Board
  -> update Ticket backlog again
```

一句话：

```text
Multica 让 agent 做 issue。
Ariadne 让知识和反馈持续改变 ticket，再让 agent 做 ticket。
```

## 本包内容

```text
00_START_HERE.md
01_PRODUCT_POSITIONING.md
02_MULTICA_CAPABILITY_SURFACE.md
03_ARIADNE_CAPABILITY_SURFACE.md
04_CORE_OBJECT_MODEL.md
05_PRIORITY_ROADMAP.md
06_ACCEPTANCE_FRAMEWORK.md
07_CODEX_MASTER_PROMPT.md
aris/ARI-015-architecture-freeze.md
aris/ARI-016-build-goal-and-goal-to-ticket.md
aris/ARI-017-build-team-squad-routing.md
aris/ARI-018-real-codex-teammate-main-demo.md
aris/ARI-019-provider-capability-matrix.md
aris/ARI-020-skill-materialization.md
aris/ARI-021-project-resource-boundaries.md
aris/ARI-022-memory-retrieval.md
aris/ARI-023-review-and-eval-agent.md
aris/ARI-024-autopilot-and-recurring-work.md
aris/ARI-025-workbench-board-productization.md
templates/CAPABILITY_STATUS_TABLE.md
templates/BUILD_GOAL_SCHEMA.md
templates/PROVIDER_CAPABILITY_SCHEMA.md
templates/SKILL_MATERIALIZATION_SCHEMA.md
ops/CODEX_IMPLEMENTATION_RULES.md
```

## 实施原则

1. 不要把 Ariadne 做成 Multica clone。
2. 不要推翻现有 Python 本地优先架构。
3. 不要把全部能力堆成一个大而散的 sprint。
4. 先固定 ticket-centered 能力面，再分批实现。
5. 优先补最能体现大厂 Agent 开发能力的部分：Ticket backlog update loop、多 Agent 协作、真实 Codex teammate、provider capability matrix、memory retrieval、review/eval。
6. 不要实现 BuildGoal-first 根流程；Goal 只能作为 ticket 更新的方向输入。
