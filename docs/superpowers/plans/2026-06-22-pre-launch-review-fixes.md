# Pre-Launch Review: 修复清单

> **For Codex:** 本文档是开工前准备的 review 结果。请按顺序执行所有修复项。每完成一项，在对应标题后标注 `[DONE]`。

## 元数据

- **Review 时间:** 2026-06-22
- **Review 人:** Claude (Opus 4.6)
- **Review 对象:** Ariadne Multica-grade Workbench 重构的开工准备
- **Review 结论:** 需要补充 2 个 P0 项 + 3 个 P1 项后再开工
- **当前 main:** `270db23`

---

## P0-1: 创建 AGENTS.md（Codex 执行入口）

**问题：** 项目根目录没有 `AGENTS.md`。Codex 启动时不会主动读 `docs/superpowers/plans/` 下的文件，导致 execution brief 形同虚设。

**修复：** 在项目根目录创建 `AGENTS.md`，内容如下：

```markdown
# Ariadne Agent Execution Rules

## 执行前必读（按顺序，不允许跳过）

1. `README.md` — 产品定义和当前状态
2. `docs/adr/ADR-0004-ticket-centered-agent-workbench.md` — 架构决策
3. `docs/architecture/ARIADNE_TICKET_CENTERED_ARCHITECTURE.md` — 核心循环
4. `docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md` — 执行 brief
5. `docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md` — 主计划

## 当前执行阶段

Phase 1: Product IA and Current Version Context

范围见下方 Phase 1 Scope 章节。不要执行 Phase 2-7 的任何内容。

## 核心约束（违反任何一条必须停下来）

1. **Ticket-centered:** BuildTicket 是工作中心，Goal 只是输入，Issue 只是 BuildTicket 的产品投影
2. **No separate Issue persistence:** `/api/issues` 必须从 BuildTicket 投影，不得创建独立的 Issue 数据模型或存储
3. **Local-first:** Python runtime, single-user, JSON/JSONL/.ariadne 存储，不得引入 Go/Postgres/auth/workspace/billing
4. **No fake acceptance:** `fake-codex` 和 `demo full` 只用于 offline regression fixture，不得作为产品验收证据
5. **Evidence required:** 真实执行（Codex/Claude/Feishu/GitHub）必须有 evidence，失败必须产生 blocker + Inbox item

## 偏移检测

如果你发现自己在做以下任何事情，立即停止并报告 blocker：

- 设计 Goal-first runtime（Goal 驱动调度而非 Ticket 驱动）
- 新增独立 Issue persistence layer（Issue model, Issue table, Issue file）
- `/api/issues` 绕过 BuildTicket 直接读写
- `#issues` 展示所有历史 tickets 而非当前 project/version mainline issue set
- 删除 Delivery 信息导致看不到当前版本目标（应上移为 Context strip，不是删除）
- 页面按钮存在但没有真实 API action
- UI 读取 static fixture 当产品路径
- 引入 React Router 或其他路由库
- 拆分 App.tsx 为多文件路由系统（Phase 1 不做）
- 为了让 UI 能工作而自行创建 Phase 2+ 的 API endpoint
- 引入 Go/Postgres/auth/workspace/billing

## Phase 1 Scope

### 做

1. 默认 hash route 从 `delivery` 改为 `issues`（修改 `useState<PageKey>` 初始值）
2. 新增 `CurrentVersionContext` 组件 — 固定在所有页面顶部的 persistent strip
   - 数据来源：现有 `GET /api/workbench` 返回的 `currentVersionDelivery`
   - 展示字段：Project, Target Version, Goal, Sources readiness, Issue Delta status, Active Run, Blocked count, Latest Evidence, Next Action
3. 左侧导航 label 更新为：Issues, Sources, Plan Changes, Team, Runs, Inbox, Diagnostics
4. `delivery` 页面内容整合进 `CurrentVersionContext` strip，`#delivery` hash 重定向到 `#issues`
5. 更新 README 默认路由描述
6. 所有现有测试继续通过（pytest 399 passed, ruff clean, npm run build success）

### 不做

- 不新增 API endpoint
- 不拆分 App.tsx 为多文件路由系统
- 不引入 React Router 或任何新前端依赖
- 不创建新的 Issue 数据模型
- 不改后端 Python 代码（除非修复 existing API response 不足以支持 Context strip 的字段）
- 不实现 Phase 2-7 的任何功能

### PageKey 映射表

当前 → Phase 1 后：

| 当前 PageKey | Phase 1 后 | 说明 |
|---|---|---|
| `delivery` | 删除（重定向到 `issues`） | 内容上移为 CurrentVersionContext strip |
| `project` | 保持 | 暂不改动 |
| `sources` | 保持 | 暂不改动 |
| `tasks` | 改名 `plan-changes` | label 改，hash 兼容 |
| `ready` | 改名 `issues` | 成为默认页，hash `#issues` 已有 legacyMap 支持 |
| `diagnostics` | 保持 | Phase 3+ 再拆分为 team/runs/inbox/diagnostics |

### 验收标准

1. 浏览器打开 `http://127.0.0.1:8766/` 默认显示 issues 页面
2. 页面顶部有 CurrentVersionContext strip，展示当前版本核心信息
3. 左侧导航显示新 label
4. `#delivery` 自动跳转到 `#issues`
5. `python3.11 -m pytest` — 全部通过
6. `ruff check .` — clean
7. `cd frontend/ariadne-workbench && npm run build` — success
8. 截图证明以上 1-4 成立

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
```

**验证方式：** 文件存在于 `/Users/martinlos/code/Ariadne/AGENTS.md`，内容覆盖上述所有章节。

---

## P0-2: Execution brief 中的 Multica 绝对路径问题

**问题：** `docs/superpowers/plans/2026-06-22-multica-grade-workbench-execution-brief.md` 第 25-33 行引用 `/Users/martinlos/code/multica/...` 绝对路径。Codex sandbox 内不一定能访问这些文件。

**修复：** 在 execution brief 的 "当前 phase 对应的 Multica 文件" 章节（第 25 行左右）之后，追加一段降级说明：

```markdown
> **降级规则：** 如果执行环境无法访问 Multica 路径，不要报错或跳过。直接使用主计划中的 "Multica 对照实现笔记" 章节作为参考依据。该章节已包含每个 phase 需要的 Multica 机制摘要。
```

**验证方式：** 打开 execution brief，确认降级说明存在。

---

## P1-1: README 默认路由描述更新

**问题：** `README.md` 第 111 行说默认是 "Current Version Delivery"。Codex 读 README 后第一反应是"保持现状"。

**修复：** 在 README.md 第 110 行（`## Workbench 默认画面` 或类似标题）之后、"Current Version Delivery" 描述之前，插入：

```markdown
> **即将变更：** 默认路由将在 Phase 1 从 `#delivery` 变更为 `#issues`。原 Delivery 页面内容将上移为所有页面顶部的 `Current Version Context` persistent strip。见 `docs/superpowers/plans/2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md` Phase 1。
```

**验证方式：** 打开 README，确认变更提示存在于默认画面描述之前。

---

## P1-2: Phase 1 出门门槛补充自动化检查

**问题：** 主计划 Phase 1 出门门槛只有 browser evidence，没有要求测试通过。Phase 1 改动可能破坏 399 个现有测试。

**修复：** 在主计划 Phase 1 的出门门槛（exit criteria）章节追加：

```markdown
- [ ] `python3.11 -m pytest` — 全部通过（不低于 399 passed）
- [ ] `ruff check .` — clean
- [ ] `cd frontend/ariadne-workbench && npm run build` — success
```

**验证方式：** 打开主计划，Phase 1 exit criteria 包含上述三条。

---

## P1-3: 主计划补充 Phase 1 "不做"清单

**问题：** 主计划 Phase 1 描述了要做什么，但没有显式的"不做"边界。Codex 容易滑入 Phase 2（比如为了让 `#issues` 页面有数据而自行创建 `/api/issues` endpoint）。

**修复：** 在主计划 Phase 1 章节末尾追加：

```markdown
### Phase 1 不做

以下属于 Phase 2+ 的范围，Phase 1 严禁触碰：

- 不新增任何 API endpoint（包括 `/api/issues`、`/api/team`、`/api/runs`）
- 不新增 Python 后端代码（除非是修复现有 API 返回数据不足以渲染 Context strip）
- 不拆分 App.tsx 为多文件路由（保持 monolithic shell）
- 不引入 React Router 或任何新前端依赖
- 不创建新的数据模型（Issue model, Agent model, Run model）
- 不实现 issue board view / kanban / drag-drop
- 不实现 issue detail 页面
- 不实现 daemon claim / heartbeat / retry 逻辑
```

**验证方式：** 打开主计划，Phase 1 有明确的 "不做" 子章节。

---

## 执行顺序

1. 创建 `AGENTS.md`（P0-1）
2. 修改 execution brief 追加降级说明（P0-2）
3. 修改 README 追加变更提示（P1-1）
4. 修改主计划 Phase 1 追加 exit criteria（P1-2）
5. 修改主计划 Phase 1 追加"不做"清单（P1-3）
6. 运行验证：
   ```bash
   python3.11 -m pytest
   ruff check .
   cd frontend/ariadne-workbench && npm run build
   ```
7. 确认所有修改不影响现有代码（纯文档变更）

## 完成后

所有修复完成后，Ariadne 可以正式从 Phase 1 开工。Codex 启动时会：

1. 读 `AGENTS.md` → 了解核心约束和当前 phase scope
2. 按指引读 README → 看到变更提示，不会困惑于 "Delivery" 描述
3. 读 ADR-0004 + 架构文档 → 锁定 ticket-centered
4. 读 execution brief → 拿到完整执行规则和偏移检测
5. 读主计划 Phase 1 → 知道做什么、不做什么、怎么验收

这个链路覆盖了从 "Codex 启动" 到 "Phase 1 交付" 的全部上下文需求。
