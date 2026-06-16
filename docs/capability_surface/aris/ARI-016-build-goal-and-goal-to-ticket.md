# ARI-016 Build Goal and Goal-to-Ticket Planning

## 目标

新增 Build Goal，使 Ariadne 从 goal 开始，而不是只从 source 或 ticket 开始。

## 为什么重要

Multica 从 issue 开始。Ariadne 的差异是从 build goal 和外部知识开始，把目标变成 tickets。

## 数据模型

新增：

```text
BuildGoal
GoalStatus
GoalSourceRef
GoalPlanningResult
```

BuildGoal 字段：

```text
id
key
title
description
success_criteria
source_refs
project_context_refs
status
generated_ticket_ids
assigned_team_id
created_at
updated_at
```

## CLI

新增：

```bash
ari goal create "goal title" --description "..."
ari goal list
ari goal show GOAL-001
ari goal attach-source GOAL-001 path.md
ari goal plan GOAL-001
```

## 行为

`ari goal plan` 应该：

```text
读取 goal
读取 attached sources
读取已有 memory / tickets 概要
生成多个 Build Tickets
设置优先级
写 GoalPlanningResult artifact
更新 generated_ticket_ids
```

## 验收

```bash
ari goal create "Make Ariadne more like a multi-agent build team"
ari goal attach-source GOAL-001 examples/real_inputs/ariadne_review_to_build.md
ari goal plan GOAL-001
ari ticket list
```

必须看到由 goal 生成的多个 tickets。

