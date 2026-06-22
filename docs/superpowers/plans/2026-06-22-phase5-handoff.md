# Phase 5 Handoff: Sources and Plan Changes Integration

> **For Codex:** 先读 `AGENTS.md`（会被更新为 Phase 5），再读本文档。

## 背景

Phase 1-4 已合并到 main。Workbench 现在有：
- `#issues` — board + detail，从 `GET /api/issues` 获取数据
- `#team` — agents + build teams + skills，从 Phase 2 API 获取
- `#runs` — runtimes + assignments + daemon control，从 Phase 2 API 获取
- `#inbox` — inbox items + repair/rerun/acknowledge/resolve actions
- CurrentVersionContext strip 在所有页面顶部

但 Sources (`#sources`) 和 Plan Changes (`#plan-changes`) 仍然是 App.tsx 中的内联 monolithic 组件（`KnowledgePage` ~370 行，`TasksPage` ~210 行），使用中文 label，且 UX 心智仍然是"生成器表单"而不是"issue delta viewer"。

**Phase 5 的目标：** 把 Sources 和 Plan Changes 从 App.tsx 抽离为独立页面组件，改造 UX 心智从"表单填写 → 生成任务"到"外部输入 → typed artifacts → issue delta → confirmed issue set"。

## 核心约束

1. **不改后端 Python 代码。** 现有 API 已覆盖：
   - `POST /api/sources` (创建 + auto_analyze)
   - `POST /api/sources/{id}/analyze` (重新分析)
   - `GET /api/sources/{id}` (detail with project_input)
   - `POST /api/issue-factory/preview` (生成 issue delta preview)
   - `POST /api/issue-factory/{preview_id}/apply` (应用 delta)
   - `POST /api/issue-factory/{preview_id}/refresh` (刷新 stale preview)
2. **Sources 第一交互是"粘贴链接或路径"**，不是填表单。标题/类型/摘要只是可选 override。
3. **Plan Changes 展示 issue delta**，不展示"生成器表单"心智。Delta item 必须展示：操作类型（新增/更新/降级/延后/拒绝）、原因、引用 source artifacts、acceptance criteria。
4. **应用 delta 后 `#issues` 必须更新：** 前端调 apply API 后 refresh workbench data，issues board 看到新 issue。
5. **stale preview 不能 500：** 如果 apply 返回 stale_preview 错误，展示 refresh 选项，不崩溃。

## 实施策略

### Step 1: 抽离 Sources 页面

从 App.tsx 抽出 `KnowledgePage`（第 898-1269 行）到 `src/pages/sources/SourcesPage.tsx`。

重构重点：
- **Primary interaction:** 顶部一个大输入框 "Paste a URL, GitHub repo, or local path"。不需要先选类型。
- **Source lifecycle 可视化：** 添加后立即显示 lifecycle status — queued → analyzing → analyzed / failed
- **Source detail 展示：** 选中 source 后展示 artifacts, evidence snippets, inspected files, relation to goal
- **English labels：** 切换为英文（匹配 Issues/Team/Runs/Inbox 已有的英文风格）
- **去掉"任务建议"按钮：** Sources 页面只管 source 输入和分析。生成 issue delta 的入口移到 Plan Changes 页面。
- **"Go to Plan Changes" CTA：** 当有 analyzed sources 且没有 preview 时，展示按钮导航到 `#plan-changes`

### Step 2: 抽离 Plan Changes 页面

从 App.tsx 抽出 `TasksPage`（第 1270-1480 行）和相关 helper（`ColumnHeader`, `BacklogChangeGroup`, `groupBacklogChanges`）到 `src/pages/plan-changes/PlanChangesPage.tsx`。

重构重点：
- **心智模型改为 "Issue Delta"：** 不叫"任务工厂"或"任务建议"。叫 "Plan Changes" / "Issue Delta"。
- **Primary action: "Generate Issue Delta"** — 调用 `POST /api/issue-factory/preview`
- **Delta 展示按操作类型分组：** Added / Updated / Deferred / Rejected
- **每个 delta item 展示：**
  - 操作类型 badge
  - ticket key + title
  - 原因 (goalReason / reason)
  - 引用的 source artifacts (sourceArtifactIds)
  - acceptance criteria
  - affected modules
  - priority
  - build decision
- **Apply action:** "Apply Changes" → `POST /api/issue-factory/{preview_id}/apply`
- **Stale handling:** 如果 apply 返回 stale_preview，自动 refresh 或展示 "Preview is stale, refresh?" 提示
- **Post-apply navigation:** 应用成功后展示 "View Issues" 按钮 → navigate to `#issues`
- **English labels**

### Step 3: App.tsx cleanup

- 删除内联的 `KnowledgePage`、`TasksPage`、`ColumnHeader`、`BacklogChangeGroup`、`groupBacklogChanges` 函数
- import 新的 `SourcesPage` 和 `PlanChangesPage`
- 在 `PageFrame` 中替换渲染
- 预期 App.tsx 从 ~2012 行减少到 ~1200 行

### Step 4: Shared helpers

一些 helper 被 Sources 和 Plan Changes 共用：
- `groupBacklogChanges` → `src/shared/lib/backlog.ts`
- `sourceTypeLabel`, `inferSourceInput` → 已在 `src/features/project-inputs/model.ts`
- `apiErrorCode` → 已在 App.tsx，可以移到 `src/shared/api/errors.ts`

## 新文件结构

```
frontend/ariadne-workbench/src/
├── pages/
│   ├── sources/
│   │   └── SourcesPage.tsx       (从 KnowledgePage 抽出并重构)
│   ├── plan-changes/
│   │   └── PlanChangesPage.tsx   (从 TasksPage 抽出并重构)
│   └── ...existing...
├── shared/
│   ├── lib/
│   │   └── backlog.ts            (groupBacklogChanges helper)
│   └── api/
│       ├── client.ts             (existing, no changes needed)
│       └── errors.ts             (existing, add apiErrorCode if needed)
```

## API 调用（已有，无需新增）

| Action | Endpoint | 备注 |
|---|---|---|
| 创建 source | `POST /api/sources` | payload: `{title, source_type, source_role, path_or_url, content?, summary?, auto_analyze: true}` |
| 分析 source | `POST /api/sources/{id}/analyze` | |
| Source detail | `GET /api/sources/{id}` | 返回 project_input with lifecycle/artifacts/evidence |
| 生成 issue delta | `POST /api/issue-factory/preview` | payload: `{goal_id, source_ids, target_project_id}` |
| 应用 delta | `POST /api/issue-factory/{preview_id}/apply` | |
| 刷新 stale | `POST /api/issue-factory/{preview_id}/refresh` | payload: same as preview |

所有这些已在 `shared/api/client.ts` 中有对应函数（`createSource`, `analyzeSource`, `createIssueFactoryPreview`, `applyIssueFactoryPreview`）。

## 不做（硬边界）

- 不改后端 Python 代码
- 不新增 API endpoint
- 不引入新 npm 依赖
- 不改 Issues / Team / Runs / Inbox 页面
- 不改 CurrentVersionContext strip
- 不实现 source 删除（不在现有 API 中）
- 不实现 real-time 分析进度（无 WebSocket）
- 不实现 GitHub repo deep clone / file tree browsing（后端已处理这个）
- 不改变 source analysis 逻辑（后端负责）

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

1. **Sources (`#sources`):**
   - 顶部有大输入框 "Paste a URL, GitHub repo, or local path"
   - 粘贴 URL → source 创建 + 自动分析 → lifecycle status 更新
   - 选中 source 展示 artifacts, evidence, lifecycle status
   - 有 "Go to Plan Changes" CTA（当 analyzed sources 存在时）
   - 英文 labels

2. **Plan Changes (`#plan-changes`):**
   - "Generate Issue Delta" 按钮调用 `POST /api/issue-factory/preview`
   - Delta items 按 Added/Updated/Deferred/Rejected 分组
   - 每个 item 展示操作类型、原因、source artifacts、acceptance criteria
   - "Apply Changes" 按钮调用 `POST /api/issue-factory/{id}/apply`
   - 应用成功后有 "View Issues" 导航到 `#issues`
   - Stale preview 不崩溃，展示 refresh 选项
   - 英文 labels

3. **Integration:**
   - 从 Sources 添加 input → 分析完成 → Plan Changes 生成 delta → apply → Issues board 展示新 issue
   - 旧 route 全部正常
   - App.tsx 行数明显减少

4. **其他页面不受影响：**
   - `#issues`, `#team`, `#runs`, `#inbox`, `#diagnostics` 仍正常工作

截图保存到 `docs/evidence/phase5-sources-plan-changes/`。

## 启动命令

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

## 分支和 PR

- Branch: `codex/phase5-sources-plan-changes`
- PR title: `Phase 5: Sources and Plan Changes integration`
- PR base: `main`
