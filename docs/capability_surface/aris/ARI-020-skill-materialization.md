# ARI-020 Skill Materialization

## 目标

把 BuildSkill 从 handoff reference 升级为 provider-specific materialization。

## 背景

Multica 的 Skills 是 agent 工作方法包。Ariadne 现在只是引用 skill，需要真正把 skill 注入到不同 agent/backend。

## 能力

```text
Codex skill materialization
Claude skill materialization
Reviewer checklist materialization
Feishu write schema materialization
```

## CLI

```bash
ari skill list
ari skill show codex-handoff
ari skill materialize ARI-003 --backend codex
```

## 实现方式

v1 可以先做 conservative implementation：

```text
把相关 SKILL.md 展开进 handoff artifact
按 backend 标记不同 section
不写入用户真实 Codex/Claude 配置目录，除非显式 confirm
```

## 验收

```bash
ari skill list
ari ticket plan ARI-003 --planner deterministic
```

handoff 中必须包含实际 skill 内容，不只是 skill 名称。

