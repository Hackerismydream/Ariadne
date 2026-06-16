# ARI-022 Memory Retrieval

## 目标

让 Memory 从“写回”升级为“可检索上下文”。

## 背景

Ariadne 的 Learning-to-Build 需要长期记忆。Memory 只写不读是不够的。

## CLI

```bash
ari memory search "codex smoke test"
ari ticket plan ARI-003 --use-memory
ari goal plan GOAL-001 --use-memory
```

## 实现

v1 可以先用本地 keyword / hybrid 简单检索，不必引入向量数据库。

搜索范围：

```text
memory/tickets/*.md
memory/build_packets/*.json
reviews/*.md
next_tickets.json
decision_log.md
```

## Planner 集成

Planner 应能把检索结果加入 BuildPacket evidence 或 assumptions。

## 验收

```bash
ari memory search "Codex"
ari ticket plan ARI-003 --use-memory
```

输出必须包含 memory evidence。

