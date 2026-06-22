# Phase 4 Handoff: Team, Runs, and Inbox Control Surfaces

> **For Codex:** 先读 `AGENTS.md`（会被更新为 Phase 4），再读本文档。

## 背景

Phase 1-3 已合并到 main。Workbench 现在有：
- 默认 `#issues` board + issue detail，从 `GET /api/issues` 获取数据
- CurrentVersionContext strip 在所有页面顶部
- Sidebar 7 项导航：Issues / Sources / Plan Changes / Team / Runs / Inbox / Diagnostics

但 Team、Runs、Inbox 三项仍然 fallback 到 diagnostics 页面。Phase 2 已提供后端 API：
- `GET /api/team/agents`
- `GET /api/team/build-teams`
- `GET /api/team/skills`
- `GET /api/runs/runtimes`
- `GET /api/runs/assignments`
- `GET /api/inbox`
- `POST /api/daemon/start`
- `POST /api/daemon/stop`
- `GET /api/daemon/status`

**Phase 4 的目标：** 把 Team、Runs、Inbox 从 diagnostics fallback 拆为独立页面，消费 Phase 2 API，让用户能看到 agent 能力、runtime 状态、daemon 控制和 inbox actions。

## 核心约束

1. **不改后端 Python 代码。** Phase 2 已提供所有需要的 API。如果 API 不足，报 blocker。
2. **Inbox actions 必须调用真实 API：** repair、rerun、acknowledge、resolve 已有 endpoint（`POST /api/inbox/{item_id}/repair|rerun|acknowledge|resolve`）。
3. **Daemon start/stop 必须调用真实 API：** `POST /api/daemon/start`、`POST /api/daemon/stop`。
4. **不能出现自相矛盾的状态：** 如果 runtime 显示 available=false，必须展示 disabled_reasons。

## 实施策略

### Step 1: 路由拆分

当前 Sidebar 中 Team/Runs/Inbox 的 hash (`#team`, `#runs`, `#inbox`) 都映射到 `PageKey = "diagnostics"`。

Phase 4 需要：
1. 扩展 `PageKey` 加入 `"team" | "runs" | "inbox"`
2. 更新 `app/routes.ts` 的 `legacyMap` — 把 `team`、`runs`、`inbox` 从映射到 `diagnostics` 改为映射到自己的 PageKey
3. 更新 `pageHash()` 为新 PageKey 返回正确 hash
4. 更新 Sidebar 的 `enabled` check 加入新 PageKey
5. 在 App.tsx 的 `PageFrame` 中为新 PageKey 渲染对应页面组件

### Step 2: Team 页面

文件: `src/pages/team/TeamPage.tsx`

消费 `GET /api/team/agents` + `GET /api/team/build-teams` + `GET /api/team/skills`。

展示三个 panel：

**Agents Panel:**
| 字段 | 来源 |
|---|---|
| name | agent.name |
| role | agent.role |
| backend | agent.backend_name |
| runtime compatibility | agent.runtime_compatibility |
| active assignments | agent.active_assignment_count |
| blocked | agent.blocked_count |
| enabled | agent.configuration.enabled |
| capabilities | agent.configuration.capabilities |

**Build Teams Panel:**
| 字段 | 来源 |
|---|---|
| name | team.name |
| description | team.description |
| lead agent | team.lead_agent_id |
| implementer | team.implementer_agent_id |
| reviewer | team.reviewer_agent_id |
| default backend | team.default_backend_name |
| skills | team.skill_refs |
| enabled | team.enabled |

**Skills Panel:**
| 字段 | 来源 |
|---|---|
| name | skill.name |
| description | skill.description |
| applies to | skill.applies_to_agent_roles |

Phase 4 不做 agent 配置编辑（enabled/disabled toggle 等）— 只展示。

### Step 3: Runs 页面

文件: `src/pages/runs/RunsPage.tsx`

消费 `GET /api/runs/runtimes` + `GET /api/runs/assignments` + `GET /api/daemon/status`。

**Runtimes Panel:**
| 字段 | 来源 |
|---|---|
| backend name | runtime.backend_name |
| display name | runtime.display_name |
| daemon state | runtime.daemon_state |
| available | runtime.available |
| can assign / can run | runtime.can_assign / runtime.can_run |
| external execution | runtime.external_execution_enabled |
| queue depth | runtime.queue_depth |
| active assignment | runtime.active_assignment |
| disabled reasons | runtime.disabled_reasons (展示为 list) |

**Daemon Control:**
- "Start Daemon" button → `POST /api/daemon/start` (payload: `{ "external_execution_authorized": true }`)
- "Stop Daemon" button → `POST /api/daemon/stop`
- 当前 daemon 状态从 `GET /api/daemon/status` 获取，展示：status, current_ticket_key, heartbeat, last_error, open/claimable/running/blocked assignment counts

**Assignments Panel:**
| 字段 | 来源 |
|---|---|
| ticket key | assignment.ticket_key |
| agent | assignment.agent_name |
| backend | assignment.backend_name |
| status | assignment.status |
| blocked reason | assignment.blocked_reason / failure_reason |
| created at | assignment.created_at |

### Step 4: Inbox 页面

文件: `src/pages/inbox/InboxPage.tsx`

消费 `GET /api/inbox`。

**Inbox list:**
| 字段 | 来源 |
|---|---|
| issue key | item.issue_key |
| failure reason | item.failure_reason |
| severity | item.severity |
| recommended action | item.action_type |
| status | item.status |
| created at | item.created_at |
| resolution note | item.resolution_note |

**Actions per item (buttons):**
- Repair → `POST /api/inbox/{item_id}/repair` (payload: `{}`)
- Rerun → `POST /api/inbox/{item_id}/rerun` (payload: `{}`)
- Acknowledge → `POST /api/inbox/{item_id}/acknowledge` (payload: `{}`)
- Resolve → `POST /api/inbox/{item_id}/resolve` (payload: `{ "note": "..." }`)

每个 action 调用后 refresh inbox list。如果 API 返回错误，展示错误信息。

### Step 5: Diagnostics cleanup

Diagnostics 页面（`#diagnostics`）只保留当前 App.tsx 中的技术诊断内容（doctor/integration/backend smoke），不再承载 team/runs/inbox 信息。

## 新文件结构

```
frontend/ariadne-workbench/src/
├── pages/
│   ├── team/
│   │   └── TeamPage.tsx
│   ├── runs/
│   │   └── RunsPage.tsx
│   ├── inbox/
│   │   └── InboxPage.tsx
│   └── ...existing...
```

## API client 新增（shared/api/client.ts）

```typescript
export function getTeamAgents() {
  return requestJson<{ schema_version: string; agents: AgentListItem[] }>("/api/team/agents");
}
export function getTeamBuildTeams() {
  return requestJson<{ schema_version: string; build_teams: BuildTeamListItem[] }>("/api/team/build-teams");
}
export function getTeamSkills() {
  return requestJson<{ schema_version: string; skills: SkillListItem[] }>("/api/team/skills");
}
export function getRunsRuntimes() {
  return requestJson<{ schema_version: string; runtimes: RuntimeListItem[] }>("/api/runs/runtimes");
}
export function getRunsAssignments() {
  return requestJson<{ schema_version: string; assignments: AssignmentSummary[] }>("/api/runs/assignments");
}
export function getDaemonStatus() {
  return requestJson<DaemonStatus>("/api/daemon/status");
}
export function startDaemon(payload?: { external_execution_authorized?: boolean }) {
  return requestJson<DaemonStatus>("/api/daemon/start", { method: "POST", body: JSON.stringify(payload ?? {}) });
}
export function stopDaemon() {
  return requestJson<DaemonStatus>("/api/daemon/stop", { method: "POST", body: JSON.stringify({}) });
}
export function inboxRepair(itemId: string) {
  return requestJson<InboxActionResponse>(`/api/inbox/${itemId}/repair`, { method: "POST", body: JSON.stringify({}) });
}
export function inboxRerun(itemId: string) {
  return requestJson<InboxActionResponse>(`/api/inbox/${itemId}/rerun`, { method: "POST", body: JSON.stringify({}) });
}
export function inboxAcknowledge(itemId: string) {
  return requestJson<InboxActionResponse>(`/api/inbox/${itemId}/acknowledge`, { method: "POST", body: JSON.stringify({}) });
}
export function inboxResolve(itemId: string, note: string) {
  return requestJson<InboxActionResponse>(`/api/inbox/${itemId}/resolve`, { method: "POST", body: JSON.stringify({ note }) });
}
```

## 不做（硬边界）

- 不改后端 Python 代码
- 不新增 API endpoint
- 不实现 agent 配置编辑（enable/disable toggle、model selection）
- 不实现 daemon claim/heartbeat/retry/orphan recovery 逻辑（Phase 6）
- 不实现 WebSocket 实时 daemon 事件流
- 不引入新 npm 依赖
- 不动 Issues 页面（Phase 3 已完成）
- 不动 Sources / Plan Changes 页面（Phase 5）
- 不修改 CurrentVersionContext strip

## 验收标准

### 自动化

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
```

### 浏览器验收

启动 workbench：
```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

确认：
1. `http://127.0.0.1:8766/#team` — 展示 agents + build teams + skills 信息
2. `http://127.0.0.1:8766/#runs` — 展示 runtimes + assignments + daemon status
3. `http://127.0.0.1:8766/#runs` — "Start Daemon" / "Stop Daemon" 按钮调用真实 API
4. `http://127.0.0.1:8766/#inbox` — 展示 active inbox items
5. Inbox item 的 repair/rerun/acknowledge/resolve actions 调用真实 API
6. 如果 runtime available=false，展示 disabled_reasons（不是空白）
7. `#issues`、`#sources`、`#plan-changes`、`#diagnostics` 仍然正常工作
8. CurrentVersionContext strip 仍然正常

截图保存到 `docs/evidence/phase4-team-runs-inbox/`。

## 启动命令

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

## 分支和 PR

- Branch: `codex/phase4-team-runs-inbox`
- PR title: `Phase 4: Team, Runs, and Inbox control surfaces`
- PR base: `main`
