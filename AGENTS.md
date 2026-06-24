# Ariadne Agent Execution Rules

## 执行前必读（按顺序，不允许跳过）

1. `README.md` — 产品定义和当前状态
2. `docs/adr/ADR-0004-ticket-centered-agent-workbench.md` — 架构决策
3. `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md` — 核心循环
4. `docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md` — 执行 brief
5. `docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md` — 主计划

## 当前执行阶段

Phase 8: Knowledge Orchestration Layer

范围见 `docs/superpowers/plans/2026-06-23-phase8-knowledge-orchestration-handoff.md`。
旧 `docs/superpowers/plans/2026-06-23-phase8-langgraph-handoff.md.superseded`
已废弃。ADR 见 `docs/adr/ADR-0005-langgraph-source-to-issue-pipeline.md`。

## 核心约束（违反任何一条必须停下来）

1. **Ticket-centered:** BuildTicket 是工作中心，Goal 只是输入，Issue 只是 BuildTicket 的产品投影
2. **No separate Issue persistence:** `/api/issues` 必须从 BuildTicket 投影，不得创建独立的 Issue 数据模型或存储
3. **Local-first:** Python runtime, single-user, JSON/JSONL/.ariadne 存储，不得引入 Go/Postgres/auth/workspace/billing
4. **No fake acceptance:** `fake-codex` 和 `demo full` 只用于 automated tests / offline regression harness，不得作为产品验收证据
5. **Evidence required:** 真实执行（Codex/Claude/Feishu/GitHub）必须有 evidence，失败必须产生 blocker + Inbox item
6. **No mock product data:** 落地的产品代码、Workbench、API projection、CLI product path、agent/runtime/orchestrator 不允许使用 mock / fixture / sample / static fallback 数据。所有产品数据必须来自真实用户输入、外部 source、目标代码库扫描、agent run、review、memory、或 `.ariadne` 持久化 store。Mock/fixture 数据只允许出现在 automated tests、test fixtures、或明确的离线回归测试 harness 中，且不能被产品路径读取。

## 偏移检测

如果你发现自己在做以下任何事情，立即停止并报告 blocker：

- 设计 Goal-first runtime（Goal 驱动调度而非 Ticket 驱动）
- 新增独立 Issue persistence layer（Issue model, Issue table, Issue file）
- `/api/issues` 绕过 BuildTicket 直接读写
- 在 Layer 2 之外新建持久化 wiki / markdown 文件
- 把 ProjectKnowledge 暴露成 HTTP API
- 在 Phase 8 实现 Query / Lint / Memory
- `#issues` 展示所有历史 tickets 而非当前 project/version mainline issue set
- 删除 Delivery 信息导致看不到当前版本目标（应上移为 Context strip，不是删除）
- 页面按钮存在但没有真实 API action
- UI 读取 static fixture 当产品路径
- 在产品代码中新增 mock / fixture / sample / static fallback 数据
- 让 Workbench、API、CLI、agent runtime 从测试 fixture、hardcoded sample、前端内置数据、`web_data` snapshot、或假默认对象读取产品状态
- 引入 React Router 或其他路由库
- 拆分 App.tsx 为多文件路由系统（Phase 1 不做）
- 为了让 UI 能工作而自行创建 Phase 2+ 的 API endpoint
- 引入 Go/Postgres/auth/workspace/billing

## Phase 8 Scope

### 做

1. 新增 `ariadne_ltb/knowledge/` 模块
2. 新增 ProjectKnowledge Layer 2 模型：
   ProjectPurpose, SourceInsight, SynthesisTheme, ContradictionRecord,
   BlockerLearning, OutcomesLog
3. 实现 Ingest LangGraph：prepare_changes, analyze_source, update_themes,
   detect_contradictions
4. 实现 Compile LangGraph：load_knowledge, plan_decomposition,
   ground_evidence, validate_dag, quality_gate
5. `issue_factory.py` 调用 `ariadne_ltb.knowledge.compile_issues()`
6. AgentRun 终态 best-effort 触发 `reflect_on_run()`
7. 无 API key 或 graph 失败时自动 fallback 到现有模板
8. 新增 `langgraph>=0.2` + `langchain-core>=0.3` 依赖
9. 新增模型、store、graph、reflect、fallback integration tests

### 不做

- 不改 HTTP routes
- 不改前端代码
- 不加 langchain-openai / langsmith / langchain-community
- 不加 MemorySaver checkpoint（Layer 2 持久化替代 checkpoint）
- 不实现 human-in-the-loop interrupt
- 不改 source_analysis.py
- 不实现 async
- 不删除旧 issue_compiler.py
- 不实现 Query / Lint / Memory
- 不暴露 ProjectKnowledge HTTP API

### 验收标准

1. `python3.11 -m pytest` — 全部通过（含新测试 + 现有测试 fallback 通过）
2. `ruff check .` — clean
3. `cd frontend/ariadne-workbench && npm run build` — success
4. 有 API key 时：issue delta 生成的 issues 基于 source 内容推理，不是固定模板
5. 无 API key 时：deterministic fallback，现有行为不变

## Multica 参考说明

Multica 源码位于 `/Users/martinlos/code/multica/`，不在本项目目录内。执行时：

- 如果你能访问该路径，按 execution brief 指定的文件列表读取参考
- 如果你不能访问该路径，不要报错或跳过——主计划中已包含 "Multica 对照实现笔记" 章节，直接使用该章节的摘要即可
- 不要因为无法读取 Multica 源码而偏离计划方向

关键 Multica 机制已内化到主计划：

- Persistent context（对应 CurrentVersionContext strip）
- Scoped issue board（对应 #issues 只展示当前 version mainline）
- Issue detail 事实中心（Phase 3）
- Execution log / shared task snapshot（Phase 4）
- Claim / heartbeat / retry / orphan recovery（Phase 6）
