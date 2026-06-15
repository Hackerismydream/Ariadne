# ARI-014 — Final Safety Gate and Release Readiness

## 目标

确保 Ariadne v1.0 可以安全合并、展示、继续迭代。

本 ARI 是最终收尾，不是新增大功能。

## 需要检查和实现

### 1. Safety gate 审核

确认：

```text
ARIADNE_ENABLE_EXTERNAL_EXECUTION=1
--confirm-execution
```

是所有真实外部执行的必要条件。

确认：

```text
FEISHU_ENABLE_WRITE=1
--confirm-write
```

是所有真实飞书写入的必要条件。

确认：

```text
.env
.env.*
*.secret
secrets/
.ariadne/
```

都在 `.gitignore` 中。

### 2. 无自动 Git 操作

确认 Ariadne 内部不会：

```text
git commit
git push
git merge
gh pr create
```

除非只是 demo target project 初始化 commit。若 demo target project 初始化 commit 存在，必须只发生在 `.ariadne/demo_target_project/` 内，并且文档说明。

### 3. Secrets 检查

新增或完善：

```bash
ari doctor secrets
```

或者在 `ari backend doctor` 中加入 secret safety 检查。

不能打印 secret 值，只打印 set/unset。

测试覆盖：设置假 key 后，输出中不能出现假 key 字符串。

### 4. Release command

新增：

```bash
ari doctor v1
```

它运行一组只读检查：

```text
agent profiles
backend capability
source fixtures
ticket count
assignment queue
journal exists
board exists
safety gates
```

不执行真实外部 backend。

### 5. Final acceptance script

新增：

```text
scripts/verify_v1.sh
```

如果项目已有 script 结构则复用；否则可以新增。

脚本运行：

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md
python3.11 -m ariadne_ltb.cli ticket list
python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to fake-codex
python3.11 -m ariadne_ltb.cli daemon run-once
python3.11 -m ariadne_ltb.cli ticket comments ARI-003
python3.11 -m ariadne_ltb.cli runtime journal
python3.11 -m ariadne_ltb.cli runtime recover
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
```

### 6. Known limitations

在 README 和 development_report 中明确：

```text
不是生产级多 worker 系统
没有 Postgres
没有 WebSocket
没有复杂权限
真实 Codex 依赖本机 CLI
Feishu 真写入默认关闭
```

## 验收标准

1. `ari doctor v1` 通过。
2. `scripts/verify_v1.sh` 通过。
3. 所有 tests 通过。
4. 无 secret 输出。
5. README 指向 v1.0 主路径。
6. development_report 记录最终结果。
7. PR summary 可以清楚说明 v1.0 完成了什么。

## 最终状态

本 ARI 完成后，项目可以定义为：

```text
Ariadne v1.0 — 本地优先、Ticket 驱动、Agent 队友模式的 Learning-to-Build 工作台。
```
