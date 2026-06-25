# Ariadne Agent Execution Rules

## 执行前必读（按顺序，不允许跳过）

1. `README.md` — 产品定义和当前状态
2. `docs/adr/ADR-0004-ticket-centered-agent-workbench.md` — 架构决策
3. `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md` — 核心循环
4. `docs/superpowers/plans/2026-06-25-multica-downstream-parity-phase-plan.md` — **当前执行计划**
5. `docs/reviews/grill-workflows/results/2026-06-24-final-41-grill-list.md` — 历史问题清单（参考）
6. `docs/architecture/multica_downstream_parity_matrix.md` — Multica 对照矩阵（Part A 产出后）

## 当前执行阶段

**Multica Downstream Parity Phase**

计划文件：
```text
docs/superpowers/plans/2026-06-25-multica-downstream-parity-phase-plan.md
```

当前目标：
```text
Sources / Issue Delta
  → Current Issue Set
  → Assign to Agent
  → Agent Task Queue
  → Runtime Claim
  → Codex / Claude Run
  → Activity / Evidence / Review / Inbox
  → Agent Detail + Issue Detail + Version Progress
```

执行节奏：
```text
Part A (Parity Matrix) → Phase 1+2 → /ponytail + review
→ Phase 3+4 → /ponytail + review
→ Phase 5+6 → /ponytail + review
→ Phase 7 → /ponytail + review
→ Phase 8 (closure)
```

## 三锚点方法（每个 phase 实施前必须完成）

每个 phase 开始写代码之前，必须先执行三锚点操作：

1. **CDP 观察 Multica** — 在 `http://localhost:3001/local-dev/` 操作对应页面，记录真实产品行为
2. **读 Multica 源码** — 按 phase 指定的源码清单读取，抽取对象边界、状态机、数据流
3. **写 Ariadne 实现映射** — 明确 Multica → Ariadne 的对应关系和"不复刻"边界

如果无法访问 Multica 路径，使用计划中的源码对照表和 parity matrix 作为替代输入。不要因为无法读取 Multica 源码而跳过锚点或偏离计划方向。

## 核心约束（违反任何一条必须停下来）

1. **Ticket-centered:** BuildTicket 是工作中心，Goal 只是输入，Issue 只是 BuildTicket 的产品投影
2. **No separate Issue persistence:** `/api/issues` 必须从 BuildTicket 投影，不得创建独立的 Issue 数据模型或存储
3. **Local-first:** Python runtime, single-user, JSON/JSONL/.ariadne 存储，不得引入 Go/Postgres/auth/workspace/billing
4. **No fake acceptance:** `fake-codex` 和 `demo full` 只用于 automated tests / offline regression harness，不得作为产品验收证据
5. **Evidence required:** 真实执行（Codex/Claude/Feishu/GitHub）必须有 evidence，失败必须产生 blocker + Inbox item
6. **No mock product data:** 产品代码、Workbench、API projection、agent/runtime/orchestrator 不允许使用 mock / fixture / sample / static fallback 数据。所有产品数据必须来自真实用户输入、外部 source、目标代码库扫描、agent run、review、memory、或 `.ariadne` 持久化 store
7. **Three anchors before code:** 每个 phase 写代码前必须完成 CDP 观察 + 源码对照 + 实现映射。不允许跳过锚点直接实现

## 偏移检测

如果你发现自己在做以下任何事情，立即停止并报告 blocker：

- 设计 Goal-first runtime（Goal 驱动调度而非 Ticket 驱动）
- 新增独立 Issue persistence layer（Issue model, Issue table, Issue file）
- `/api/issues` 绕过 BuildTicket 直接读写
- 在 Layer 2 之外新建持久化 wiki / markdown 文件
- 把 ProjectKnowledge 暴露成 HTTP API
- `#issues` 展示所有历史 tickets 而非当前 project/version mainline issue set
- 页面按钮存在但没有真实 API action
- UI 读取 static fixture 当产品路径
- 在产品代码中新增 mock / fixture / sample / static fallback 数据
- 引入 Go/Postgres/auth/workspace/billing
- **跳过 CDP 观察直接写 UI 代码**
- **跳过源码对照直接设计数据模型**
- **在没有 parity matrix 行对照的情况下声称 parity 达成**

## Phase 完成后必须执行（执行纪律）

每个 phase merge 后，按顺序执行：

### 1. `/ponytail` — 减少代码复杂度
- 删除被新实现替代的旧代码路径
- 合并重复抽象
- 清理不再需要的 DTO/projection/adapter
- 确保新代码不增加整体圈复杂度

### 2. 文档清理 — 避免上下文污染
- 标记或删除被本 phase 超越的旧计划/handoff
- 更新 README 中的能力描述
- 删除描述旧行为的 architecture doc 段落
- 不保留"历史记录式"注释
- 参照计划中"被本计划超越的旧文档"表格执行

### 3. 多 agent 交叉 review
- Agent A: 对照 Multica 源码验证语义完整性
- Agent B: 检查 Ariadne 内部一致性（models → store → service → route → frontend）
- Agent C: 找遗漏的旧代码 / dead path / 上下文污染

## 验收标准

1. `python3.11 -m pytest` — 全部通过或 phase 文档列出确切 blocker
2. `ruff check .` — clean
3. `cd frontend/ariadne-workbench && npm run build` — 前端受影响时必须通过
4. 每个 phase 必须有浏览器 evidence
5. 不得依赖 fake-codex、demo full、mock data、static fixture、CLI-only path
6. 如果真实 Codex/Claude 执行被环境阻塞，必须显示为 `BLOCKED_WITH_EVIDENCE`，不得声称闭环
7. **新增：parity matrix 中对应行的 "Browser Acceptance" 列必须全部通过**

## Multica 参考说明

Multica 源码位于 `/Users/martinlos/code/multica/`，不在本项目目录内。

关键路径：
```
packages/views/agents/components/     — Agent UI 组件 (46 files)
packages/views/agents/components/tabs/ — Agent detail tabs
packages/views/agents/components/inspector/ — Agent inspector 面板
packages/views/runtimes/components/   — Runtime 页面
packages/views/issues/components/     — Issue 页面
server/internal/handler/              — Task lifecycle (Go)
server/migrations/                    — DB schema (参考状态机设计)
```

执行规则：
- 如果你能访问该路径，按 phase 指定的源码对照表读取
- 如果你不能访问该路径，不要报错或跳过——使用计划中的锚点操作表和 parity matrix 作为替代
- 不要因为无法读取 Multica 源码而偏离计划方向

## 历史阶段（参考，不再执行）

以下为已完成或被超越的旧阶段文档，仅作历史参考：

```text
docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md (superseded by current plan)
docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md (superseded)
docs/superpowers/plans/2026-06-24-grill-closure-campaign-plan.md (completed)
docs/superpowers/plans/2026-06-22-phase2-handoff.md ~ phase6-handoff.md (superseded)
docs/superpowers/plans/2026-06-23-phase8-knowledge-orchestration-handoff.md (completed, knowledge layer reference)
```
