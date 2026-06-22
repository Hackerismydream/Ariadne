# Phase 6 Handoff: Lifecycle Hardening and Execution Evidence

> **For Codex:** 先读 `AGENTS.md`（会被更新为 Phase 6），再读本文档。

## 背景

Phase 1-5 已合并到 main。Workbench 现在有完整的 UI：Issues board + detail, Team, Runs, Inbox, Sources, Plan Changes — 全部从真实 API 获取数据。

但 execution lifecycle 仍有几个 gap：
1. Daemon 跑完后，orphaned/stale assignments 没有自动恢复
2. 可 retry 的 failure 没有自动 retry
3. Issue Detail 已经展示 execution results，但缺少 progress events 实时更新
4. Runs 页面只展示 daemon status，没有展示当前 assignment 的 progress events
5. Inbox items 已由 `refresh_inbox` 从 blocked executions 自动生成，但前端 Inbox 只展示 static list 不刷新

**Phase 6 的目标：** 让执行生命周期可靠、可观测——stale assignments 被回收，可 retry 的失败自动重试，progress 实时可见，evidence 完整回流。

## 现有基础设施（已实现，不需要重写）

| 机制 | 文件 | 状态 |
|---|---|---|
| Assignment lifecycle (queued → claimed → running → done/blocked/failed) | `daemon.py` | ✅ 完整 |
| Heartbeat writes | `daemon.py:_heartbeat()` | ✅ 完整 |
| Stale heartbeat detection | `daemon.py:is_stale_heartbeat()` | ✅ 完整 |
| `record_assignment_failure` + typed FailureReason | `failure.py` | ✅ 完整 |
| Inbox auto-generation from blocked executions | `inbox.py:refresh_inbox()` | ✅ 完整 |
| Inbox repair ticket creation | `inbox.py:create_repair_ticket_from_inbox()` | ✅ 完整 |
| Runtime events (claim/start/blocked/done) | `daemon.py` writes | ✅ 完整 |
| Assignment event stream (GET + WebSocket) | `routes.py` | ✅ 完整 |
| Execution result storage | `TicketRunOrchestrator` | ✅ 完整 |

## 需要新增的部分

### 6a: Orphan recovery + auto-retry (后端)

**文件：** `ariadne_ltb/daemon.py`

1. **Orphan recovery in `_next_assignment()`：** 在选择下一个 assignment 时，检查是否有 stale 的 CLAIMED/RUNNING assignments（heartbeat 超时）。如果有，先 reclaim 它们（reset to QUEUED + 写 event）再选择。

```python
def _recover_stale_assignments(self) -> int:
    """Reset assignments whose heartbeat is stale back to QUEUED."""
    recovered = 0
    for assignment in self.store.list_assignments():
        if assignment.status not in (AssignmentStatus.CLAIMED, AssignmentStatus.RUNNING):
            continue
        if assignment.claimed_by_runtime_id != self.runtime_id:
            continue
        heartbeat = self.store.load_heartbeat(self.runtime_id)
        if heartbeat and is_stale_heartbeat(heartbeat):
            requeued = assignment.requeue("Stale heartbeat — orphan recovery")
            self.store.save_assignment(requeued)
            recovered += 1
    return recovered
```

2. **Auto-retry on safe failures：** 在 `run_once()` 中，当 assignment 被 blocked/failed 且 failure_reason 在 `SAFE_RETRY_FAILURE_REASONS` 中，且 retry_count < max_retries（默认 2），自动 requeue 而不是停止。

```python
# After recording failure:
if failure.retry_recommendation == "auto_retry" and assignment.retry_count < 2:
    retried = failure.assignment.requeue(f"Auto-retry #{assignment.retry_count + 1}")
    retried = retried.model_copy(update={"retry_count": assignment.retry_count + 1})
    self.store.save_assignment(retried)
```

注意：如果 `TicketAssignment` model 没有 `retry_count` 字段，需要在 `metadata` 中追踪：`metadata.get("retry_count", 0)`。**不新增 model 字段到 `models.py`** — 用 metadata。

3. **`requeue` method on TicketAssignment：** 如果不存在，在 `models.py` 的 `TicketAssignment` class 中增加：

```python
def requeue(self, reason: str) -> "TicketAssignment":
    return self.model_copy(update={
        "status": AssignmentStatus.QUEUED,
        "blocker": None,
        "failure_reason": None,
        "metadata": {**self.metadata, "requeue_reason": reason, "retry_count": self.metadata.get("retry_count", 0) + 1},
    })
```

### 6b: Progress events polling in frontend

**文件：** `src/pages/runs/RunsPage.tsx`, `src/pages/issues/IssueDetail.tsx`

1. **Runs page — daemon progress section：** 当 daemon status 有 `current_assignment_id`，展示 assignment events（从 `GET /api/assignments/{id}/events`）。每 5 秒 polling refresh。

2. **Issue Detail — execution progress：** 当 issue 有 active assignment (status = claimed/running)，展示 assignment event stream。每 5 秒 polling。用已有的 `GET /api/assignments/{id}/events` endpoint。

3. **Inbox page — auto-refresh：** 每次 navigate 到 `#inbox` 时 refetch `GET /api/inbox`。

### 6c: Evidence surface enhancement in Issue Detail

**文件：** `src/pages/issues/IssueDetail.tsx`

当前 Issue Detail 已展示 execution results（backend_name, exit_code, test_exit_code, blocked, changed_files）。Phase 6 增加：

1. **Stdout/stderr excerpts：** 从 execution result 中展示（如果 API 返回这些字段）。检查 `GET /api/issues/{key}` 返回的 `execution_results` 是否已包含 stdout/stderr — 如果不包含，**不改后端**，只展示已有字段。
2. **Diff artifact link：** 展示 `diff_artifact_path` 作为可点击路径
3. **Review verdict badge：** 从 issue detail 的 `review_verdict` 展示明确的 pass/fail badge
4. **Blocker reason + inbox link：** 如果 issue 被 blocked，展示 blocker reason 并指向 `#inbox`

## 不做（硬边界）

- 不实现 WebSocket real-time push（用 polling）
- 不引入 interval 库或新 npm 依赖
- 不实现跨 runtime 的 orphan recovery（只回收本 runtime 的 stale assignments）
- 不实现 retry policy 配置 UI（用 metadata 硬编码 max_retries=2）
- 不改 Sources / Plan Changes 页面
- 不改 CurrentVersionContext strip
- 不新增 API endpoint（全部用已有的）
- 不改 Issue board view

## 验收标准

### 自动化

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m pytest
ruff check .
cd frontend/ariadne-workbench && npm run build
```

### 后端行为验收

1. **Orphan recovery test：** 创建一个 assignment 标记为 CLAIMED，模拟 heartbeat 过期。调用 daemon `run_once()`。验证 assignment 被 requeued 后重新 claimed 并执行。
2. **Auto-retry test：** 创建一个 assignment，让 execution 返回 safe-retry failure（如 `command_unavailable`）。验证 assignment 被 requeue 且 retry_count 增加。第 3 次 fail 后不再 retry。

### 浏览器验收

启动 workbench：
```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

确认：
1. `#runs` — daemon start 后，当前 assignment 的 progress events 可见
2. `#issues/{key}` — active assignment 的 progress events polling 更新
3. `#issues/{key}` — execution results 展示 diff_artifact_path, review verdict badge
4. `#issues/{key}` — blocked issue 展示 blocker reason + link to inbox
5. `#inbox` — navigate 时 auto-refresh
6. 所有已有页面不受影响

截图保存到 `docs/evidence/phase6-lifecycle-evidence/`。

## 启动命令

```bash
cd /Users/martinlos/code/Ariadne
python3.11 -m ariadne_ltb.cli workbench serve --host 127.0.0.1 --port 8766
```

## 分支和 PR

- Branch: `codex/phase6-lifecycle-evidence`
- PR title: `Phase 6: Lifecycle hardening and execution evidence`
- PR base: `main`
