# 01. Ariadne 产品定位

## 一句话定位

Ariadne 是一个面向 AI Builder 的目标驱动多 Agent 构建工作台。

它把一个 build goal、相关外部知识、项目上下文和历史记忆，转化成一组可执行、可分配、可审查、可沉淀的软件迭代任务。

## 目标用户

Ariadne 的目标用户是 AI Builder，包括：

1. 正在做 Agent / AI 应用项目的校招生；
2. 使用 Codex / Claude Code / Cursor 等工具的独立开发者；
3. 经常读论文、博客、GitHub 项目并希望把学习内容转化成项目迭代的 AI 工程学习者；
4. 想让 coding agent 按照明确上下文、验收标准和项目记忆持续工作的开发者。

## 核心问题

AI 时代写代码变快了，但这些问题变得更重要：

```text
该 build 什么？
为什么 build？
外部知识和当前项目有什么关系？
如何拆成 coding agent 可执行任务？
如何给 Codex / Claude 足够上下文？
如何审查结果？
如何沉淀决策和下一轮任务？
```

Ariadne 解决的是：

```text
目标 + 知识 + 项目上下文 -> 多 Agent 协作 -> 软件迭代
```

## 产品卖点

Ariadne 的卖点不是“Learning-to-Build”这几个字本身。

Learning-to-Build 是业务场景。真正的产品卖点是：

```text
Goal-driven Multi-Agent Build Team
```

也就是：

```text
目标驱动
多 Agent 协作
工作台式任务管理
Coding agent 执行编排
Review / Memory / Next Tickets 闭环
```

## 与 Multica 的一句话对比

Multica：

```text
Issue-driven Agent Team
已有 issue -> 分配给 agent -> agent 执行
```

Ariadne：

```text
Goal-driven Agent Team
build goal + 外部知识 + 项目上下文 -> 生成 tickets -> 多 Agent 执行
```

## 产品边界

Ariadne v1.x 应坚持本地优先，避免过早进入复杂平台化：

```text
本地优先
单用户优先
Python runtime
JSON/JSONL 可审计存储
真实 Codex/Claude 安全门控
Feishu 默认 dry-run
Board 本地展示
```

暂不做：

```text
完整 Multica clone
Go 后端重写
Postgres / 多租户 / 权限系统
WebSocket 实时平台
Feishu 真写默认开启
自动 commit / push / merge / PR
```

