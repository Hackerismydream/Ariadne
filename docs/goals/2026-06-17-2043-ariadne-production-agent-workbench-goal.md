# Goal: 2026-06-17-2043 Ariadne Production Agent Workbench

Status: active goal

You are Codex working on Ariadne.

Your objective is to turn Ariadne into a production-usable, local-first Agent
Workbench for AI builders. Do not continue building demo-only paths.

Read and follow:

```text
docs/superpowers/plans/2026-06-17-2043-ariadne-production-agent-workbench-execution-plan.md
```

Authoritative roadmap:

```text
docs/ops/2026-06-17-2043-ARIADNE_PRODUCTION_AGENT_WORKBENCH_ROADMAP.md
```

Product target:

```text
Knowledge / Feedback / Codebase / optional Goal
  -> update Ticket backlog
  -> Ticket management center
  -> assign to Agent
  -> local Daemon / Runtime
  -> real Codex / real Claude Code / real LLM agents
  -> Review / Comments / Board / Memory
  -> update Ticket backlog again
```

Goal can be input context. Ticket is the runtime center.

The direction is production-first:

- implement real DeepSeek upstream LLM runtime for Build Lead, planner,
  reviewer, memory, and knowledge agents;
- implement real Codex and Claude Code execution as production backends;
- implement gated real Feishu writes through `lark-cli`;
- implement real GitHub issue, PR, branch, status, and comment integration;
- use `fake-codex` only for deterministic tests and offline fallback;
- use dry-run only as preview or safety fallback, not as final product state.

Use DeepSeek as the default upstream LLM provider:

```text
base_url: https://api.deepseek.com
env var: DEEPSEEK_API_KEY
default model: deepseek-v4-pro
fast model: deepseek-v4-flash
```

Never write API keys into source, docs, tests, board exports, artifacts, logs,
or commits. Read credentials from environment or ignored local `.env` only.

First re-check branch state and decide whether to integrate the existing
frontend/workbench branch. Do not develop new frontend features unless required
to resolve integration or consume a stable backend data contract.

For every slice:

```text
inspect current code
declare owned files
implement real product capability
keep tests deterministic with fakes
run verification
commit
push
write Chinese progress evidence
```

Required verification for non-doc code:

```bash
python3.11 -m pytest
python3.11 -m ruff check .
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli export board
python3.11 -m ariadne_ltb.cli backend doctor
scripts/verify_v1.sh
```

Real integration smoke tests should be attempted when credentials, CLI login,
and confirmation flags are available. If they fail, record the exact failure
and fix it when it is safe to do so.

Stop only for true blockers: unsafe external state, missing user login for a
required real service, contradictory product direction, unresolvable merge
conflict, or repeated verification failure after evidence-backed repair.
