# Codex Completion Checklist

Before final response, verify:

- [ ] `ari ticket run <key> --backend fake-codex` completes full loop.
- [ ] `demo full` uses the orchestrator.
- [ ] Planner interface exists.
- [ ] FakeCodexBackend blocks invalid tasks.
- [ ] CodexBackend has gated command-template scaffold.
- [ ] ClaudeCodeBackend has gated command-template scaffold.
- [ ] LLM planner missing key fails gracefully.
- [ ] Next tickets artifact is created.
- [ ] Board shows Loop Trace.
- [ ] README updated.
- [ ] development_report updated.
- [ ] pytest passes.
- [ ] ruff passes.
- [ ] no secrets committed.
