# 00 — Start Here: Ariadne 1.0 Workpack

You are implementing **Ariadne 1.0**, not another small kernel-only increment.

Ariadne is a Learning-to-Build Agent Team for AI builders. It converts external knowledge into executable software iterations, delegates execution to a local coding backend such as Codex/Claude Code/Shell, reviews the result, and writes project memory back to local knowledge and optionally Feishu.

## One-run development principle

The human owner wants to minimize intervention. Do not stop after a tiny slice unless you are technically blocked.

When uncertain:

1. make a conservative assumption;
2. document the assumption;
3. keep implementing;
4. record follow-up tickets only after the 1.0 demo works.

## 1.0 product requirement

Ariadne 1.0 must demonstrate one complete chain:

```text
2-3 external inputs
  -> Build Tickets
  -> Build Packets
  -> Project-aware planning
  -> Coding backend execution against a target repo
  -> stdout/stderr/exit code + git diff capture
  -> Reviewer verdict
  -> Memory write-back to local knowledge and Feishu dry-run plan
  -> Board UI/export showing the full trace
```

The demo must include at least three source types:

- paper-style markdown note;
- blog/architecture note;
- GitHub repo/README analysis note.

Real network/API access is optional. The 1.0 demo must pass without external keys by using local fixtures and a safe ShellBackend/FakeCodexBackend. If Codex CLI or Feishu credentials are available, implement optional real adapters behind explicit confirmation flags.

## Current baseline

If this repository already contains Ariadne v0.1 Ticket Kernel, build on it. Do not rewrite from scratch unless impossible.

Expected existing baseline:

- `ariadne_ltb` package;
- BuildTicket / BuildPacket / AgentRun / Artifact models;
- JSON persistence under `.ariadne/`;
- deterministic pipeline;
- dry-run execution;
- static board export;
- tests.

Your job is to evolve it to 1.0.
