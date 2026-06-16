# ARI-025 Workbench Board Productization

## 目标

把 Board 从静态报告升级为本地工作台体验。

## 最小功能

```text
Ticket Board
Ticket Detail
Comments Timeline
Assignment Panel
Handoff Chain
Runtime Journal
Review Report
Diff Summary
Memory / Next Tickets
Backend Capability
```

## CLI / Server

```bash
ari board serve
```

可以继续用静态文件 + Python http.server，不要求 FastAPI。

## 可选增强

```text
HTMX / simple JS
assign button
retry button
comment form
run-once button
```

如果要做按钮，必须走 CLI-safe endpoint 或写清楚安全边界。

## 验收

打开 board 后，用户应能理解完整链路：

```text
Goal -> Ticket -> Assignment -> Agent -> Execution -> Review -> Memory -> Next Tickets
```

