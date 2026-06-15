# ARI-007 — Daemon Supervision and Heartbeat

## 目标

让 Ariadne 的 daemon 不再只是一个 `run-once` 函数，而是一个可观察、可诊断、可恢复的本地 worker。

现在已有：

```bash
ari daemon run-once
ari daemon start
ari daemon status
```

但还缺真正的 worker heartbeat、运行状态、当前 stage、当前 assignment、stale worker 检测。

## 需要实现的能力

### 1. DaemonState

新增或完善模型：

```python
class DaemonStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    STOPPED = "stopped"


class WorkerHeartbeat(AriadneModel):
    runtime_id: str
    pid: int
    status: DaemonStatus
    current_assignment_id: str | None = None
    current_ticket_id: str | None = None
    current_ticket_key: str | None = None
    current_stage: str | None = None
    started_at: str
    heartbeat_at: str
    last_event_id: str | None = None
    last_error: str | None = None
```

建议存储：

```text
.ariadne/daemon/heartbeats/<runtime_id>.json
.ariadne/daemon/state.json
```

### 2. Heartbeat 写入

在 daemon 执行以下阶段时更新 heartbeat：

```text
idle
claiming
planning
route
execution
review
memory
next_tickets
board
done
blocked
failed
```

每次阶段切换都要：

1. 写 heartbeat。
2. 写 runtime event。
3. 如有 Ticket，则写 progress comment。

### 3. Daemon status

增强：

```bash
ari daemon status
```

输出：

```text
runtime_id
pid
status
current ticket
current assignment
current stage
heartbeat age
last event
stale?
open assignments
running assignments
blocked assignments
```

### 4. Stale worker 检测

实现：

```python
is_stale_heartbeat(heartbeat, stale_after_seconds=120)
```

规则：

1. heartbeat 缺失：未知。
2. heartbeat 超过阈值：stale。
3. pid 不存在：stale。
4. 当前进程仍存在且 heartbeat 新：active。

测试里不要依赖真实长时间等待，可以构造旧时间。

### 5. Daemon loop 改造

`ari daemon start` 应该在每轮：

1. 写 idle heartbeat。
2. 查找 assignment。
3. 有任务就进入 running。
4. 没任务就 sleep。
5. 支持 `--max-iterations`。
6. 支持 `--runtime-id`。

新增参数：

```bash
ari daemon start --runtime-id local --interval 2 --max-iterations 5
ari daemon run-once --runtime-id local
```

## 验收标准

必须通过：

```bash
ari daemon status
```

并能看到 heartbeat 信息。

测试必须覆盖：

1. `run-once` 写 heartbeat。
2. `daemon status` 展示 heartbeat。
3. stale heartbeat 被识别。
4. `daemon start --max-iterations 1` 不会卡死。
5. heartbeat 不输出任何 secret。
6. daemon 在 no work 时状态为 idle 或 stopped。

## Board 要求

Board 的 `Daemon / Worker` 区块要展示：

```text
runtime_id
status
current_stage
heartbeat_at
stale?
current_assignment
current_ticket
```

## 文档要求

在 README 增加：

```bash
ari daemon status
ari daemon start --max-iterations 3
```

并说明这是本地 worker，不是 production daemon service。
