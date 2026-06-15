# Ariadne v1.0 Project Narrative

## 这个项目解决什么问题

Ariadne v1.0 解决的是 AI builder 的知识到执行断层：论文、博客、GitHub README、项目笔记和当前代码上下文进入系统后，不只是被搜索，而是被转成 Build Ticket、Build Packet、handoff、acceptance criteria 和可执行的本地迭代。

## 为什么不是普通 RAG

它不是普通 RAG，因为核心产物不是回答，而是可执行工作单元。RAG 通常停在检索和生成文本，Ariadne 把 source evidence、任务、验收标准、backend execution、diff、测试、review、memory 和 next tickets 串成一个可审计闭环。

## 为什么不是重新造 Codex

它不是重新造 Codex。Codex 是 coding backend，Ariadne 是本地工作管理和上下文准备层。Ariadne 负责把 Ticket 分配给 Agent、生成 handoff、记录 comments/journal、捕获执行结果和评审结论；真正写代码可以交给 `fake-codex`、真实 Codex 或其他 gated backend。

## 为什么对标 Multica

Multica 的启发在于 agent work-management：Issue、Run、Agent、Squad Leader、Project Resource、Board 这些概念让 agent 工作变成可见流程。Ariadne v1.0 吸收的是本地优先版本：Build Ticket、Agent Assignment、Daemon、Agent Handoff、Runtime Journal、Board。

## Ariadne 和 Multica 的差异

Ariadne 不做 Multica clone。它没有服务端多租户、权限系统、生产级调度器或远程 agent 集群。Ariadne 的目标是单用户、本地、确定性、可测试的 Learning-to-Build workbench，适合在开发机上跑通 agent 协作闭环。

## Build Ticket / Assignment / Daemon / Review / Memory 的设计价值

Build Ticket 是可见工作载体，Assignment 表示人把 Ticket 交给某个 Agent，Daemon 负责本地认领和执行，Review 保守检查 diff/tests/result，Memory 把决策和结果写回本地历史。这个分层让失败、重试、恢复和展示都有稳定落点。

## Agent 能力点

Ariadne v1.0 已有 Build Lead、Planner、Execution、Reviewer、Memory、Feishu dry-run 和 Next Ticket generator。Agent Handoff 让同一 Ticket 内部的接力可见，Comments 和 Journal 让协作过程可审计。

## 工程难点

工程难点主要是边界控制：真实外部执行必须安全门控，fake backend 不能掩盖真实 backend 缺失，失败必须带 typed failure reason，retry 不能覆盖历史 assignment，board 必须展示流程而不是堆 artifact。

## 已知限制和下一步

当前限制是本地单 worker、JSON/JSONL persistence、无生产级 Web UI、真实 Codex 依赖本机 CLI、Feishu 真写入默认关闭。下一步应做 daemon supervision hardening、memory retrieval、真实 Codex smoke 扩展和更强的 planner evidence ranking。
