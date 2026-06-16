# Codex Implementation Rules

Codex 在实现本包能力时必须遵守：

1. 不要重写 Ariadne。
2. 不要 fork Multica。
3. 不要引入 Go 后端、Postgres、WebSocket、多租户系统。
4. 不要破坏现有 CLI 主路径。
5. 不要让测试依赖真实 Codex、Claude、DeepSeek、Feishu、GitHub token 或网络。
6. 不要提交 secrets。
7. 真实外部执行必须 gated。
8. 每个新增能力必须有 CLI、模型、持久化、测试、文档。
9. 每个新增能力必须能映射到 Multica 能力面或 Ariadne 的 ticket-backlog update 差异点。
10. 实现不完时必须在 development_report 里标记 blocked 和原因。
