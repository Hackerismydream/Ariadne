# ARI-024 Autopilot and Recurring Work

## 目标

规划 Ariadne 的 Autopilot 能力，对应 Multica 的 recurring / webhook / manual autopilot 思想。

## v1 暂不需要完整生产实现

但至少需要设计文档和最小手动 run：

```bash
ari autopilot list
ari autopilot run weekly-review
```

## Autopilot 类型

```text
weekly project review
daily source inbox triage
periodic Codex smoke check
memory summary
next goal generation
```

## 输出

```text
Build Goal
Build Tickets
Weekly Summary
Next Tickets
```

## 验收

可以先实现 `weekly-review` 的本地手动 run。

