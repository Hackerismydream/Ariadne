# Codex Master Prompt — Ariadne Capability Surface Freeze

你正在开发 Ariadne。

这次任务不是实现一个小功能，而是固定 Ariadne 后续实施时的能力面。

请先读取本包所有 Markdown：

```text
00_START_HERE.md
01_PRODUCT_POSITIONING.md
02_MULTICA_CAPABILITY_SURFACE.md
03_ARIADNE_CAPABILITY_SURFACE.md
04_CORE_OBJECT_MODEL.md
05_PRIORITY_ROADMAP.md
06_ACCEPTANCE_FRAMEWORK.md
aris/*.md
templates/*.md
ops/CODEX_IMPLEMENTATION_RULES.md
```

## 目标

把 Ariadne 的产品能力面冻结为：

```text
Goal-driven Multi-Agent Build Team
```

并把 Multica 的能力面作为固定对标：

```text
Agent teammate
Task lifecycle
Daemon/runtime
Provider capability
Skills
Squads
Project resources
Comments
Board
Autopilot
```

## 你要完成什么

请把这些文档整合进仓库：

```text
docs/capability_surface/
```

并新增一个总览文档：

```text
docs/capability_surface/ARIADNE_CAPABILITY_SURFACE.md
```

这个总览文档必须说明：

1. Ariadne 的目标用户；
2. Ariadne 的产品定位；
3. 为什么固定对标 Multica；
4. Multica 除上游调度外有哪些能力；
5. Ariadne 已覆盖哪些能力；
6. Ariadne 还需要补哪些能力；
7. 后续 ARI-015 到 ARI-025 的优先级；
8. 为什么 Ariadne 是 Goal-driven，而 Multica 是 Issue-driven；
9. 为什么 Ariadne 的卖点是 Multi-Agent，而 Learning-to-Build 是场景。

## 不要做什么

不要修改核心代码。
不要重构。
不要新增大功能。
不要 fork Multica。
不要改技术栈。

本任务只做能力面冻结和文档落地。

## 必须运行

```bash
pytest
ruff check .
python3.11 -m ariadne_ltb.cli doctor v1
python3.11 -m ariadne_ltb.cli export board
```

如果某个命令无法运行，记录原因。

## 完成报告

最后请报告：

1. 写入了哪些文档；
2. 能力面总览在哪里；
3. Multica 能力面总结在哪里；
4. Ariadne 待补能力在哪里；
5. 后续 ARI 路线在哪里；
6. 测试命令结果。

