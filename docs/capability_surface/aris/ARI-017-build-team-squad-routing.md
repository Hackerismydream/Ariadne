# ARI-017 Build Team / Squad Routing

## 目标

实现 Ariadne 的 Build Team，对应 Multica Squads。

## 背景

现在可以把 ticket 分配给一个 agent，但 Ariadne 的多 Agent 卖点需要支持把 goal 或 ticket 分配给一个 team，由 Build Lead 路由。

## 数据模型

新增：

```text
BuildTeam
TeamMember
TeamRoutingPolicy
TeamAssignment
```

默认 team：

```text
build-team
```

成员：

```text
build-lead
research
knowledge
project-context
planner
fake-codex / codex
reviewer
memory
```

## CLI

新增：

```bash
ari team list
ari team show build-team
ari goal assign GOAL-001 --to build-team
ari ticket assign ARI-003 --to build-team
```

## 路由行为

Build Lead 应根据 goal / ticket 判断：

```text
是否需要 research
是否需要 knowledge retrieval
是否需要 repo context
是否是 code_task
执行 backend 用 fake-codex 还是 codex
是否需要 reviewer
是否需要 memory
```

## 验收

```bash
ari team list
ari goal assign GOAL-001 --to build-team
ari daemon run-once
ari ticket comments <generated-ticket>
ari export board
```

Board 应展示 team routing 和 handoff。

