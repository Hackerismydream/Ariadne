# Ariadne Multica Downstream Parity Phase

> 把 Ariadne 的下游 Agent / Task / Runtime / Activity / Skills / Inbox 能力做成 Multica 级别的真实工作管理系统，让上层知识编排生成的 issue 能落到可管理的 agent team 执行。

## 元数据

- **创建时间:** 2026-06-25
- **状态:** active
- **前置计划:** `2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md`
- **验收标准:** 浏览器真实创建 / 分配 / claim / run / blocker / repair / evidence 回流
- **最终交付:** `docs/evidence/multica-downstream-parity/closure-result.json`

## 整体链路

```
Sources / Issue Delta
        ↓
Current Issue Set
        ↓
Assign to Agent
        ↓
Agent Task Queue
        ↓
Runtime Claim
        ↓
Codex / Claude Run
        ↓
Activity / Evidence / Review / Inbox
        ↓
Agent Detail + Issue Detail + Version Progress
```

## 三锚点方法

每个 phase 都必须经过三锚点验证：

| 锚点 | 作用 | 来源 |
|------|------|------|
| 浏览器/CDP 看 Multica | 定义真实产品行为 | `http://localhost:3001/local-dev/*` |
| 读 Multica 源码 | 抽取对象边界、状态机、API、页面数据流 | `/Users/martinlos/code/multica/` |
| Ariadne 本地 Python 实现 | 复刻产品语义，不复刻技术栈 | `/Users/martinlos/code/Ariadne/` |

## 不可违反的约束

1. Issue 只是 BuildTicket 的产品投影，不新增 issue store
2. 所有新 API 必须投影现有 ticket / assignment / run / artifact / comment store
3. UI 不允许把 static fixture 当产品数据
4. `fake-codex`、`demo full`、offline fixture 不能作为产品验收
5. 没有真实外部执行时，状态必须是 `BLOCKED_WITH_EVIDENCE`，不能假成功
6. 每个 phase 独立可合并，能在浏览器里证明一个真实能力面
7. 不 fork Multica，不引入 Go/Postgres/auth/multi-workspace/billing
8. 不先做视觉 polish、拖拽、sidebar 美化

## 执行纪律

### Phase 完成后必须执行

每个 phase merge 后，按顺序执行：

1. **`/ponytail`** — 减少代码复杂度
   - 删除被新实现替代的旧代码路径
   - 合并重复抽象
   - 清理不再需要的 DTO/projection/adapter
   - 确保新代码不增加整体圈复杂度

2. **文档清理** — 避免上下文污染
   - 标记或删除被本 phase 超越的旧计划/handoff
   - 更新 README 中的能力描述
   - 删除描述旧行为的 architecture doc 段落
   - 不保留"历史记录式"注释

3. **多 agent 交叉 review** — 写完后用 3 agent 交叉审查
   - Agent A: 对照 Multica 源码验证语义完整性
   - Agent B: 检查 Ariadne 内部一致性（models → store → service → route → frontend）
   - Agent C: 找遗漏的旧代码 / dead path / 上下文污染

### 验收口径

不接受：
```
API 有了 / 页面能显示 / 测试过了
```

必须：
```
浏览器里真实创建 / 分配 / claim / run / blocker / repair / evidence 回流
```

---

## Part A: Multica Parity Evidence Pack

**目标：** 产出规格输入，驱动 Phase 1-2 实现。不是开放式调研。

**产出文件：**
```
docs/architecture/multica_downstream_parity_matrix.md
docs/architecture/multica_agent_work_management_digest.md
```

### 矩阵格式

| 列 | 说明 |
|----|------|
| Multica Surface | 页面/区域名 |
| User Action | 用户操作 |
| Visible Product Behavior | 可观察结果 |
| Underlying Objects | 数据模型 |
| Multica Source Files | 源码位置 |
| Ariadne Current State | 当前对应能力 |
| Gap | 缺失项 |
| Required Ariadne Object/API/UI | 需要新增什么 |
| Browser Acceptance | 浏览器验收标准 |

### 必须覆盖的 surface

**Multica 原生 surface（必须在 Multica 里观察到行为）：**
- Agents list
- Create Agent
- Agent Detail / Activity
- Agent Detail / Instructions
- Agent Detail / Skills
- Agent Detail / Environment
- Agent Detail / Runtime Config
- Runtime page
- Issue assignment to agent
- Inbox blocker / repair
- Task status lifecycle (in activity stream)

**Ariadne 扩展 surface（Multica 没有独立页面，Ariadne 产品决策新增）：**
- Agent Detail / Tasks tab（Multica 的 task 融合在 activity 中，Ariadne 独立出来增强可管理性）
- Agent Detail / Runs tab（独立展示 run history）

> 扩展 surface 同样需要矩阵行，但 "Multica Source Files" 列填写参考来源而非直接对应。

### 浏览器观察入口

```
http://localhost:3001/local-dev/agents
http://localhost:3001/local-dev/agents/<agent-id>
http://localhost:3001/local-dev/issues
http://localhost:3001/local-dev/inbox
http://localhost:3001/local-dev/runtimes
```

### 源码阅读清单

```
# Agent 页面和组件
/Users/martinlos/code/multica/packages/views/agents/components/agents-page.tsx
/Users/martinlos/code/multica/packages/views/agents/components/agent-detail-page.tsx
/Users/martinlos/code/multica/packages/views/agents/components/agent-detail-inspector.tsx
/Users/martinlos/code/multica/packages/views/agents/components/create-agent-dialog.tsx
/Users/martinlos/code/multica/packages/views/agents/components/agent-overview-pane.tsx
/Users/martinlos/code/multica/packages/views/agents/components/agent-profile-card.tsx
/Users/martinlos/code/multica/packages/views/agents/components/avatar-picker.tsx

# Agent detail tabs
/Users/martinlos/code/multica/packages/views/agents/components/tabs/activity-tab.tsx
/Users/martinlos/code/multica/packages/views/agents/components/tabs/instructions-tab.tsx
/Users/martinlos/code/multica/packages/views/agents/components/tabs/skills-tab.tsx
/Users/martinlos/code/multica/packages/views/agents/components/tabs/env-tab.tsx
/Users/martinlos/code/multica/packages/views/agents/components/tabs/runtime-config-tab.tsx
/Users/martinlos/code/multica/packages/views/agents/components/tabs/task-failure.ts

# Agent inspector 面板
/Users/martinlos/code/multica/packages/views/agents/components/inspector/skill-attach.tsx
/Users/martinlos/code/multica/packages/views/agents/components/inspector/model-picker.tsx
/Users/martinlos/code/multica/packages/views/agents/components/inspector/runtime-picker.tsx
/Users/martinlos/code/multica/packages/views/agents/components/inspector/visibility-picker.tsx

# Skills 相关
/Users/martinlos/code/multica/packages/views/agents/components/skill-add-dialog.tsx
/Users/martinlos/code/multica/packages/views/agents/components/skill-multi-select.tsx
/Users/martinlos/code/multica/packages/views/agents/components/skill-picker-list.tsx
/Users/martinlos/code/multica/packages/views/agents/components/instructions-editor.tsx

# Runtime 页面
/Users/martinlos/code/multica/packages/views/runtimes/components/runtimes-page.tsx

# Issue 页面
/Users/martinlos/code/multica/packages/views/issues/components/issue-detail.tsx
/Users/martinlos/code/multica/packages/views/issues/components/terminate-task-confirm-dialog.tsx

# Inbox 页面
/Users/martinlos/code/multica/packages/views/inbox/components/inbox-page.tsx
/Users/martinlos/code/multica/packages/views/inbox/components/inbox-list-item.tsx
/Users/martinlos/code/multica/packages/views/inbox/components/inbox-detail-label.tsx

# Task 状态相关
/Users/martinlos/code/multica/packages/views/chat/components/task-status-pill.tsx
/Users/martinlos/code/multica/packages/views/common/task-transcript/transcript-button.tsx

# Server 端
/Users/martinlos/code/multica/server/internal/handler/task_lifecycle.go
/Users/martinlos/code/multica/server/migrations/055_task_lease_and_retry.up.sql
```

### Part A 与 Phase 1 的关系

Part A 不需要完全完成才能开始 Phase 1。只要 Agents list / Create Agent / Agent Detail 三个 surface 的矩阵行填完，Phase 1 就可以开始。剩余 surface 在后续 phase 开始前补齐。

---

## Part B: Implementation Phases

### Phase 1: Real AgentDefinition Store

**目标：** Agent 不再是 role 投影，而是真实产品对象。

#### 锚点操作

**CDP 观察（实施前必须完成）：**
- 页面: `http://localhost:3001/local-dev/agents`
- 操作: 点击 "Create Agent" → 填写 name/description → 选择 runtime → 保存
- 记录: 创建对话框字段列表、avatar 生成方式、保存后列表刷新行为、agent 卡片展示的字段
- 记录: 列表排序方式、status badge 样式、空状态文案

**源码对照（实施前必须读）：**

| 关注点 | Multica 文件 | 抽取内容 |
|--------|-------------|---------|
| Agent 列表页结构 | `agents/components/agents-page.tsx` | 列表 columns、排序、过滤、toolbar actions |
| 创建对话框字段 | `agents/components/create-agent-dialog.tsx` | 必填/可选字段、校验规则、默认值 |
| Agent 数据模型 | `agents/components/agent-profile-card.tsx` | 卡片展示哪些字段、status 枚举 |
| Avatar 机制 | `agents/components/avatar-picker.tsx` | seed-based 还是 upload |
| Visibility 控制 | `agents/components/inspector/visibility-picker.tsx` | team scope 逻辑 |

**Ariadne 实现映射：**
- Multica `Agent` entity → Ariadne `AgentDefinition` (Pydantic model in `models.py`)
- Multica Postgres `agents` table → Ariadne `.ariadne/agents/{id}.json`
- Multica `POST /api/agents` → Ariadne `POST /api/team/agents`
- 不复刻: multi-workspace ownership、billing seat、OAuth identity binding

**当前状态：**
- `.ariadne/agents/profiles.json` 存在但内容是 BuildLeadAgent / LearningAgent 等 role 定义
- `GET /api/team/agents` 返回这些 role 投影
- 没有用户可创建的 agent entity

**实现对象：**

```python
AgentDefinition:
    agent_id: str
    name: str
    description: str
    avatar_seed: str
    runtime_profile_id: str | None
    status: active | paused | archived
    created_at: str
    updated_at: str

AgentRuntimeProfile:
    profile_id: str
    agent_id: str
    backend: codex | claude
    model: str | None
    working_directory: str | None
    environment_keys: list[str]  # key only, no values

AgentVisibility:
    agent_id: str
    visible: bool
    team_ids: list[str]
```

**持久化：**
```
.ariadne/agents/{agent_id}.json
```

替代现有 `profiles.json` role 投影。

**API：**
```
GET  /api/team/agents           → 列表（真实 AgentDefinition）
POST /api/team/agents           → 创建
GET  /api/team/agents/{id}      → 详情
PATCH /api/team/agents/{id}     → 更新
```

**验收：**
```
用户新建 agent
→ 保存到 .ariadne/agents/{id}.json
→ Team 页面真实显示
→ 刷新后仍存在
→ 没有 mock row
→ 旧 role agent 迁移为 AgentDefinition 或标记为 system agent
```

**Phase 1 完成后清理：**
- `/ponytail`: 删除 `profiles.json` 旧读取逻辑、删除 role-based agent 投影代码
- 文档: 更新 `ARIADNE_V1_OBJECT_MODEL.md` 中 agent 定义段落
- Review: 验证 `workbench_agents.py` 不再引用旧 profiles 结构

---

### Phase 2: Agent Detail Fact Center

**目标：** Agent detail 成为事实中心，聚合该 agent 所有已有数据。

#### 锚点操作

**CDP 观察（实施前必须完成）：**
- 页面: `http://localhost:3001/local-dev/agents/<agent-id>`
- 操作: 依次点击每个 tab（Activity / Tasks / Instructions / Skills / Environment / Runs）
- 记录: 每个 tab 的数据结构、空状态文案、加载方式（lazy vs eager）
- 记录: Inspector 侧边栏字段（右侧面板）、哪些字段可编辑
- 记录: Activity 事件卡片样式、时间戳格式、事件类型 icon

**源码对照（实施前必须读）：**

| 关注点 | Multica 文件 | 抽取内容 |
|--------|-------------|---------|
| Detail 页面布局 | `agents/components/agent-detail-page.tsx` | tab 列表、路由结构、数据加载策略 |
| Inspector 面板 | `agents/components/agent-detail-inspector.tsx` | 右侧面板字段、编辑交互 |
| Activity tab | `agents/components/tabs/activity-tab.tsx` | 事件类型、排序、分页、事件卡片结构 |
| Instructions tab | `agents/components/tabs/instructions-tab.tsx` | 编辑器类型、保存方式 |
| Skills tab | `agents/components/tabs/skills-tab.tsx` | skill 列表渲染、bind/unbind 交互 |
| Env tab | `agents/components/tabs/env-tab.tsx` | key-only 展示、secret 遮蔽方式 |
| Runtime config | `agents/components/tabs/runtime-config-tab.tsx` | runtime 设置项、model picker |
| Overview pane | `agents/components/agent-overview-pane.tsx` | 概览统计数据来源 |

**Ariadne 实现映射：**
- Multica agent detail page → Ariadne `/team/agents/{id}` 前端路由
- Multica tab data fetching → Ariadne `GET /api/team/agents/{id}/{tab}` 按 tab 懒加载
- Multica inspector sidebar → Ariadne agent detail 右侧面板（Phase 2 只读，Phase 5 可编辑）
- 不复刻: live presence indicator、sparkline 图表、concurrency picker（后续 phase 可选）

**页面 tabs：**
```
Activity | Tasks | Instructions | Skills | Environment | Runs
```

> **注意：** Multica agent detail 没有独立 Tasks tab，task 信息融合在 activity stream 中。
> Ariadne 增加独立 Tasks tab 是产品决策：让 agent 工作负载更可管理。
> Multica 的实际 tabs: Activity / Instructions / Skills / Env / Runtime Config / MCP Config / Integrations / Custom Args。
> Ariadne 不复刻 MCP Config / Integrations / Custom Args（非核心下游语义）。

**API projection（全部从现有 store 投影，不新增 store）：**
```
GET /api/team/agents/{id}/activity   → 从 journal + assignment events 投影
GET /api/team/agents/{id}/tasks      → 从 TicketAssignment where agent_id 投影
GET /api/team/agents/{id}/runs       → 从 AgentRun where agent_id 投影
GET /api/team/agents/{id}/skills     → 从 AgentSkillBinding 投影
GET /api/team/agents/{id}/instructions → 从 AgentDefinition.instructions 投影
```

**数据来源映射：**

| Tab | 数据来源 |
|-----|---------|
| Activity | `journal/events.jsonl` filtered by agent_id |
| Tasks | `assignments/*.json` filtered by agent_id |
| Runs | `runs/*.json` filtered by agent_id |
| Instructions | `agents/{id}.json`.instructions |
| Skills | `agents/{id}.json`.skill_bindings |
| Environment | `agents/{id}.json`.runtime_profile.environment_keys |

**验收：**
```
进入 agent detail
→ 能看到真实 runtime/profile
→ 能看到真实 activity（如果有 assignment 历史）
→ 能看到真实 task/runs（如果有）
→ 空状态说明"没有真实数据"，不造数据
```

**Phase 2 完成后清理：**
- `/ponytail`: 合并重复的 assignment query 逻辑；删除旧 agent detail 静态 tab
- 文档: 删除 `2026-06-22-phase2-handoff.md` 中已实现的 TODO
- Review: 验证 activity 事件与 issue detail timeline 共用同一事件源

---

### Phase 3: Agent Task Queue

**目标：** 分配给 agent 的任务真实出现在 Agent Tasks tab，有真实状态机。

#### 锚点操作

**CDP 观察（实施前必须完成）：**
- 页面: `http://localhost:3001/local-dev/agents/<agent-id>` → Tasks tab
- 操作: 从 Issues 页面 assign 一个 issue 给该 agent → 回到 agent detail 观察 task 出现
- 操作: 等待 daemon claim → 观察状态从 queued → running → done/blocked
- 记录: task 列表列定义（title、status badge、attempt count、时间戳）
- 记录: blocked 状态的展示方式（blocker 描述、link to inbox）
- 记录: retry 按钮位置和行为

**源码对照（实施前必须读）：**

| 关注点 | Multica 文件 | 抽取内容 |
|--------|-------------|---------|
| Task 状态机 | `server/internal/handler/task_lifecycle.go` | 状态枚举、转换条件、谁触发转换 |
| Lease & Retry | `server/migrations/055_task_lease_and_retry.up.sql` | lease_until、retry_count、max_attempts 字段 |
| Agent tasks 渲染 | `agents/components/tabs/activity-tab.tsx` + `tabs/task-failure.ts` | task 信息如何在 activity stream 中展示、failure 处理 |
| Issue assign 交互 | `views/issues/components/issue-detail.tsx` | assign agent 的 UI 触发点 |
| Task status pill | `views/chat/components/task-status-pill.tsx` | 状态 badge 样式和枚举 |
| Terminate task | `views/issues/components/terminate-task-confirm-dialog.tsx` | 取消/终止 task 交互 |

**Ariadne 实现映射：**
- Multica `task_lifecycle.go` 状态机 → Ariadne `AgentTaskProjection.status` 枚举
- Multica Postgres lease lock → Ariadne `.ariadne/assignments/.claim.lock` 文件锁
- Multica `retry_count` + `max_attempts` → Ariadne `TicketAssignment.attempt_number` + config
- 不复刻: Postgres advisory lock、distributed lease heartbeat、concurrent worker pool

**实现对象：**

```python
AgentTaskProjection:
    task_id: str           # = assignment_id
    ticket_id: str
    ticket_key: str
    agent_id: str
    status: queued | claimed | running | blocked | done | failed
    attempt_number: int
    retry_count: int
    blocker_id: str | None  # → InboxItem
    claimed_at: str | None
    completed_at: str | None
```

**状态机：**
```
queued → claimed → running → done
                          → blocked → (repair) → queued
                          → failed → (retry) → queued
```

**与现有 assignment 的关系：**

AgentTaskProjection 不是新 store，是 `TicketAssignment` + `AgentRun` + `InboxItem` 的 read projection。写操作仍走现有 `assign_ticket` / `run_assignment` / `inbox` 路径。

**验收：**
```
Issue detail assign 给 agent
→ Agent Tasks tab 出现 queued
→ Daemon claim 后变 running
→ 完成后变 done
→ blocked 后显示 blocker + Inbox link
```

**Phase 3 完成后清理：**
- `/ponytail`: 删除 `agent-task-snapshot` 旧 endpoint（如果被新 projection 完全替代）；合并 assignment status → task status 映射到单一位置
- 文档: 更新 runtime flow doc 中 assignment 状态描述
- Review: 验证 daemon claim 逻辑与新 agent_id 字段兼容

---

### Phase 4: Agent Activity Timeline

**目标：** Activity 是真实事件流，不是装饰 tab。

#### 锚点操作

**CDP 观察（实施前必须完成）：**
- 页面: `http://localhost:3001/local-dev/agents/<agent-id>` → Activity tab
- 操作: 触发一次完整的 assign → claim → run → complete 流程，同时保持 Activity tab 打开
- 记录: 事件卡片结构（icon + title + timestamp + detail expand）
- 记录: 事件顺序（newest first vs oldest first）、分页/infinite scroll
- 记录: 点击事件是否跳转到 assignment/run detail
- 对比: 同一个 assignment 的事件在 Issue Detail timeline 和 Agent Activity 是否一致

**源码对照（实施前必须读）：**

| 关注点 | Multica 文件 | 抽取内容 |
|--------|-------------|---------|
| Activity 事件类型 | `agents/components/tabs/activity-tab.tsx` | 事件 type 枚举、渲染分支 |
| 事件 hover 详情 | `agents/components/agent-activity-hover-content.tsx` | hover card 展示哪些字段 |
| Live peek | `agents/components/agent-live-peek-card.tsx` | 实时运行状态卡片结构 |
| Presence indicator | `agents/components/agent-presence-indicator.tsx` | 在线/运行中状态如何计算 |

**Ariadne 实现映射：**
- Multica activity event stream → Ariadne `journal/events.jsonl` + `assignments/*/events.jsonl` 聚合
- Multica real-time WebSocket push → Ariadne `WS /ws/assignments/{id}` 已有，扩展为 agent 维度
- Multica hover content → Ariadne event detail expand（点击展开，不做 hover card）
- 不复刻: live presence indicator（Phase 8 可选）、sparkline 统计图

**事件类型（从 journal 投影）：**
```
assignment_created
assignment_claimed
run_started
progress_event
backend_blocked
tests_completed
review_completed
inbox_created
run_done
run_failed
```

**实现要点：**
- 不新增 event store — 从 `journal/events.jsonl` + `assignments/*/events.jsonl` 聚合
- 每个事件必须带 `agent_id` 字段（Phase 1 建立后所有新事件自动携带）
- 历史事件通过 assignment → agent_id 反查补全

**验收：**
```
执行一次 assignment
→ Agent Activity 逐步追加事件
→ Issue Detail timeline 和 Agent Detail activity 看到同一套事件
→ 事件可以追到 assignment/run/evidence
```

**Phase 4 完成后清理：**
- `/ponytail`: 删除重复的 timeline 构建逻辑（issue timeline 和 agent activity 应共用 event resolver）
- 文档: 删除旧 activity 相关的 TODO/planning 注释
- Review: 验证事件不重复、时间线排序正确

---

### Phase 5: Skills / Instructions / Env Binding

**目标：** Skill 从"handoff 附件"变成 agent 能力绑定。

#### 锚点操作

**CDP 观察（实施前必须完成）：**
- 页面: `http://localhost:3001/local-dev/agents/<agent-id>` → Skills tab
- 操作: 点击 "Add Skill" → 从列表选择 → bind → 观察 Skills tab 更新
- 操作: 切换到 Instructions tab → 编辑 system instructions → 保存
- 操作: 切换到 Environment tab → 观察 key 列表展示方式
- 记录: Skill 卡片结构（name、description、parameters、bound status）
- 记录: Instructions editor 类型（plaintext / markdown / structured）
- 记录: Env tab 如何显示 "configured" vs "missing" 状态

**源码对照（实施前必须读）：**

| 关注点 | Multica 文件 | 抽取内容 |
|--------|-------------|---------|
| Skills tab 列表 | `agents/components/tabs/skills-tab.tsx` | skill 展示结构、bind/unbind 按钮 |
| Skill 选择器 | `agents/components/skill-add-dialog.tsx` | 可选 skill 来源、搜索/过滤 |
| Skill 多选 | `agents/components/skill-multi-select.tsx` | 批量绑定交互 |
| Skill 列表渲染 | `agents/components/skill-picker-list.tsx` | skill 卡片字段 |
| Skill attach（inspector） | `agents/components/inspector/skill-attach.tsx` | inspector 里的 skill 绑定交互 |
| Instructions editor | `agents/components/instructions-editor.tsx` | 编辑器组件、保存 API |
| Instructions tab | `agents/components/tabs/instructions-tab.tsx` | tab wrapper、加载逻辑 |
| Env tab | `agents/components/tabs/env-tab.tsx` | env key 列表、secret 遮蔽 |
| Model picker | `agents/components/inspector/model-picker.tsx` | model 选择如何影响 agent |
| Runtime picker | `agents/components/inspector/runtime-picker.tsx` | runtime binding 交互 |

**Ariadne 实现映射：**
- Multica `Skill` entity → Ariadne `SkillDefinition` (从 `.skills/` 目录注册)
- Multica `AgentSkill` join table → Ariadne `AgentSkillBinding` (存在 agent JSON 内)
- Multica skill attach UI → Ariadne Agent Detail Skills tab + bind action
- Multica instructions editor → Ariadne plaintext editor（不做 rich markdown，够用即可）
- Multica env secrets → Ariadne key-only 展示 + `runtime_profile.environment_keys`
- 不复刻: MCP config tab、integrations tab、custom args tab（非核心下游语义）

**实现对象：**

```python
SkillDefinition:
    skill_id: str
    name: str
    description: str
    source_path: str       # .skills/ 下的文件
    parameters: dict | None
    version: str

AgentSkillBinding:
    agent_id: str
    skill_id: str
    bound_at: str
    configuration: dict | None

AgentInstructionProfile:
    agent_id: str
    system_instructions: str
    additional_context: list[str]
    updated_at: str

AgentEnvironmentProfile:
    agent_id: str
    env_keys: list[str]    # key only
    runtime_vars: dict[str, str]  # non-secret config
```

**注意：**
- Environment 只显示 key 和配置状态，不显示 secret value
- SkillDefinition 从现有 `.skills/` 目录 + `.ariadne/skills/` 注册

**验收：**
```
Agent 绑定 skill
→ Agent Skills tab 显示
→ Route Decision 引用 selected skills
→ Handoff 写入 selected skills
→ Run evidence 记录 used_skills
```

**Phase 5 完成后清理：**
- `/ponytail`: 删除旧 skill 作为 handoff 附件的拼接逻辑；合并 skill resolution 到单一 service
- 文档: 更新 `ariadne_multica_gap_report.md` 中 "BuildSkill packs" 段落为已完成
- Review: 验证 skill binding 持久化与 agent definition 一致

---

### Phase 6: Route Decision Uses Real Agents

**目标：** Build Lead 选择真实 agent 而不只是 backend 字符串。

#### 锚点操作

**CDP 观察（实施前必须完成）：**
- 页面: `http://localhost:3001/local-dev/issues/<issue-id>`
- 操作: 点击 "Assign" → 观察 agent 选择器（是否列出真实 agent 而非 backend 字符串）
- 操作: 选择 agent → 观察 assignment 创建 → 验证 agent_id 绑定
- 页面: `http://localhost:3001/local-dev/agents` → 观察被分配 agent 的状态变化
- 记录: assign 对话框里 agent 列表的展示方式（avatar + name + skill summary）
- 记录: assignment 创建后 issue detail 里如何展示"已分配给哪个 agent"

**源码对照（实施前必须读）：**

| 关注点 | Multica 文件 | 抽取内容 |
|--------|-------------|---------|
| Issue assign 交互 | `views/issues/components/issue-detail.tsx` | assign agent 的触发点、agent picker |
| Agent row actions | `agents/components/agent-row-actions.tsx` | agent 列表上的快捷操作 |
| Runtime picker | `agents/components/runtime-picker.tsx` | 选择 agent 时如何关联 runtime |
| Task lifecycle: assign | `server/internal/handler/task_lifecycle.go` | assign 后 task 状态如何初始化 |

**Ariadne 实现映射：**
- Multica issue assign → agent picker → Ariadne `POST /api/issues/{id}/assign` body 加 `agent_id`
- Multica route decision by squad leader → Ariadne Build Lead 的 `RouteDecision.agent_id`
- Multica agent + runtime binding → Ariadne `AgentDefinition.runtime_profile_id` 自动带入
- 不复刻: squad leader 自动 routing（Ariadne 保留 Build Lead LLM 决策 + 用户手动 assign 两条路径）

**实现变更：**

```python
RouteDecision:
    agent_id: str              # 新增：指向 AgentDefinition
    agent_reason: str          # 新增：为什么选这个 agent
    selected_skills: list[str] # 新增：该 agent 的哪些 skill 被选中
    runtime_profile_id: str    # 新增：使用哪个 runtime profile
    # 保留现有字段兼容
    backend: str               # deprecated but kept for transition
```

**与 Phase 1 的关系：**
- Phase 1 建立 AgentDefinition 后，Build Lead agent 可以通过 `GET /api/team/agents` 获取可选 agent 列表
- Route decision 写入 agent_id 后，assignment 自动绑定

**验收：**
```
Issue route decision
→ 选择某个真实 agent
→ assignment 绑定 agent_id
→ daemon claim 该 assignment
→ evidence 里显示 agent identity
```

**Phase 6 完成后清理：**
- `/ponytail`: 删除 `backend` 字段相关的旧 routing 逻辑（如果完全被 agent_id 替代）；如果需要过渡期则标记 deprecated
- 文档: 更新 route decision artifact 文档
- Review: 验证 Build Lead prompt 能看到真实 agent 列表和 skill

---

### Phase 7: Inbox / Repair Integrated With Agent

**目标：** 失败回到 agent 工作管理，不只是 inbox item。

#### 锚点操作

**CDP 观察（实施前必须完成）：**
- 页面: `http://localhost:3001/local-dev/inbox`
- 操作: 找到一个 blocked 状态的 inbox item → 点击 repair → 观察 repair assignment 创建
- 页面: `http://localhost:3001/local-dev/agents/<agent-id>` → Tasks tab
- 操作: 验证 repair task 出现在该 agent 的 Tasks 列表中
- 页面: `http://localhost:3001/local-dev/agents/<agent-id>` → Activity tab
- 操作: 验证 blocker event + repair event 出现在 activity 流
- 记录: inbox item 卡片结构（agent avatar + issue link + blocker reason + action buttons）
- 记录: repair 有几种选项（retry same agent / reassign / manual fix）
- 记录: repair 后原 task 状态如何更新

**源码对照（实施前必须读）：**

| 关注点 | Multica 文件 | 抽取内容 |
|--------|-------------|---------|
| Task lifecycle: blocked | `server/internal/handler/task_lifecycle.go` | blocked 状态如何触发、blocker 对象结构 |
| Retry schema | `server/migrations/055_task_lease_and_retry.up.sql` | retry_count、max_attempts、lease_until |
| Inbox 页面 | `views/inbox/components/inbox-page.tsx` | inbox 列表结构、过滤 |
| Inbox item 结构 | `views/inbox/components/inbox-list-item.tsx` | item 卡片字段、action buttons |
| Inbox detail label | `views/inbox/components/inbox-detail-label.tsx` | blocker 描述展示方式 |
| Issue detail: blocked state | `views/issues/components/issue-detail.tsx` | issue 被 block 时的展示方式 |
| Task failure handling | `agents/components/tabs/task-failure.ts` | failure 类型定义、retry 逻辑 |

**Ariadne 实现映射：**
- Multica task blocked → inbox notification → Ariadne `InboxItem` 创建 + `agent_id` 关联
- Multica repair action → new task assignment → Ariadne `RepairAction` → 新 assignment
- Multica retry with same agent → Ariadne `repair_type: retry` + `target_agent_id = original`
- 不复刻: 自动 repair policy（Multica 可能有自动 retry threshold）— Ariadne 保持用户手动触发

**实现变更：**

```python
InboxItem:
    agent_id: str              # 新增：关联 agent
    # repair action 创建 repair assignment for same or selected agent

RepairAction:
    source_inbox_item_id: str
    target_agent_id: str
    repair_type: retry | fix | reassign
    new_assignment_id: str
```

**行为链路：**
```
Agent run blocked
→ InboxItem 创建，带 agent_id
→ Agent Activity 显示 blocker event
→ Inbox 显示同一 blocker
→ 用户点 repair
→ 创建 repair assignment，target_agent_id = same agent（或用户选择其他 agent）
→ Agent Tasks 出现 repair task
→ 原 task 状态标记为 blocked → repair_in_progress
```

**验收：**
```
Agent run blocked
→ Agent Activity 显示 blocker
→ Inbox 显示同一 blocker
→ 点 repair 创建 repair task
→ Agent Tasks 出现 repair assignment
→ repair 完成后原 task 状态更新
```

**Phase 7 完成后清理：**
- `/ponytail`: 删除 inbox repair 中不经过 agent 的旧直接 rerun 路径
- 文档: 更新 inbox 相关 architecture doc
- Review: 验证 repair assignment 与普通 assignment 走同一 daemon claim 路径

---

### Phase 8: Browser Dogfood Closure

**目标：** 端到端浏览器证明 Multica downstream parity。

#### 锚点操作

**CDP 观察（全链路验证）：**
- 全链路操作序列，必须在浏览器中一次性完成：
  1. `http://localhost:3001/local-dev/agents` → Create Agent → 填写完整 profile
  2. Agent Detail → Skills tab → Bind skills
  3. Agent Detail → Instructions tab → 编辑 instructions
  4. Agent Detail → Environment tab → 确认 runtime config
  5. `http://localhost:3001/local-dev/issues/<id>` → Assign to agent
  6. Agent Detail → Tasks tab → 观察 task 出现 (queued)
  7. 等待 daemon claim → 观察 task 变为 running
  8. Agent Detail → Activity tab → 验证事件流实时更新
  9. 执行完成或 blocked → 验证 evidence 回流到 Agent Detail + Issue Detail
  10. 如果 blocked → Inbox → Repair → 验证 repair task 出现在 Agent Tasks

**源码对照（最终验证）：**
- 逐一对照 Multica parity matrix 中每一行的 "Browser Acceptance" 列
- 确认没有遗漏的 Multica surface 行为
- 确认没有 static/mock 数据参与产品路径

**Ariadne 验证清单：**
- 所有 agent 相关页面数据来自 `.ariadne/` store，不来自 fixture
- API response 与前端 types.ts 类型一致
- 空状态展示正确（不是错误，不是假数据）
- Evidence 可追溯到 assignment → run → agent

**验收链路：**
```
新建 agent
→ 绑定 skill / instruction / runtime
→ 从 issue detail assign 给 agent
→ Agent Tasks 出现任务
→ daemon claim
→ Agent Activity 更新
→ Codex/Claude blocked 或执行完成
→ Evidence 回到 Agent Detail + Issue Detail + Inbox
```

**输出：**
```
docs/evidence/multica-downstream-parity/
  parity-matrix.md
  browser-agent-list.png
  browser-agent-detail-activity.png
  browser-agent-detail-tasks.png
  browser-agent-detail-skills.png
  browser-issue-assign-agent.png
  browser-runtime-claim.png
  browser-inbox-repair.png
  closure-result.json
```

**Phase 8 完成后清理：**
- `/ponytail`: 最终清理 — 删除所有标记为 deprecated 的旧字段/endpoint；删除旧计划中的 TODO 注释
- 文档: 标记本计划为 completed；删除被彻底超越的旧 handoff 文件
- Review: 最终 3-agent review 覆盖完整链路

---

## 最脆弱假设与应对

**假设：** Multica 的 agent/task/skill/runtime 语义能压缩到 Ariadne 的 local-first JSON store，不需要 Postgres workspace schema。

**最先爆的点：** Agent activity / task query 性能和一致性（当 assignment 数量 > 200 且需要按 agent 聚合）。

**应对：**
```
1. 先用 projection reducer + JSONL event log
2. 不新增独立 Issue store
3. 不迁移数据库
4. 如果 JSON scan 慢于 200ms，加 .ariadne/agents/{id}/index.json 作为预计算索引
5. 等真实数据量证明 JSON store 不够再讨论 SQLite
```

---

## 推荐执行顺序

```
Part A (够驱动 P1-2 的部分) → Phase 1 + 2 → /ponytail + review
→ Phase 3 + 4 → /ponytail + review
→ Phase 5 + 6 → /ponytail + review
→ Phase 7 → /ponytail + review
→ Phase 8 (closure)
```

**Phase 1 + 2 优先的理由：**
- 立刻消灭最大假象："agent row 不是真的"、"Agent detail tabs 没真实对象"
- 后续 phase 全部依赖 AgentDefinition 存在
- 最小改动量最大验收效果

---

## 被本计划超越的旧文档

以下文档在本计划各 phase 完成后应逐步清理或标记 superseded：

| 文件 | 处理时机 |
|------|---------|
| `2026-06-22-multica-grade-agent-team-workbench-rebuild-plan.md` | Phase 2 完成后 |
| `2026-06-22-multica-grade-workbench-execution-brief.md` | Phase 2 完成后 |
| `2026-06-22-phase2-handoff.md` ~ `phase6-handoff.md` | 对应 phase 完成后 |
| `docs/architecture/ariadne_multica_gap_report.md` | Phase 8 完成后重写 |
| `docs/architecture/ARIADNE_V1_MULTICA_MAPPING.md` | Phase 8 完成后重写 |

---

## 交叉 Review 模板

每个 phase merge 后执行：

```
## Review Round: Phase N

### Agent A — Multica 语义完整性
- 对照 Multica 源码验证：新实现是否覆盖了矩阵中标记的所有 user action？
- 是否遗漏了 Multica 的状态转换或边界条件？
- 产品行为是否与 Multica 观察一致？

### Agent B — Ariadne 内部一致性
- models.py 新增类型是否被 store / service / route / frontend 全链路使用？
- 是否有新增的 dead code 或未接入的 endpoint？
- 新 API 返回值是否与 frontend types.ts 一致？

### Agent C — 旧代码 / Dead Path / 上下文污染
- 是否有被新实现替代但未删除的旧路径？
- 是否有 handoff/plan 文档描述了与当前实现矛盾的行为？
- README / architecture doc 是否与当前产品能力匹配？
```
