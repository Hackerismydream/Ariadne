# ARI-004 Real CodexBackend Smoke Summary

Date: 2026-06-15

Context: this summary is retained for the Multica architecture alignment pass
after studying `multica-ai/multica`.

## Summary

The ARI-004 smoke-test path exists and remains safety-gated.

Confirmed local result from the previous ARI-004 stage:

- Codex command available: yes, `/opt/homebrew/bin/codex`
- Required gates: `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1` plus
  `--confirm-execution`
- Final successful command template:
  `codex exec -c model_reasoning_effort="none" --cd {target_repo} - < {handoff_file}`
- Execution result: `.ariadne/execution_results/execution_60d17b702878.json`
- Changed files: `demo_todo/cli.py`, `tests/test_cli.py`
- Test exit code: `0`
- Review verdict: `pass`

Earlier blocked attempts were preserved honestly:

- The default-style `--prompt-file` template failed because the local Codex CLI
  did not support `--prompt-file`.
- A stdin template reached the provider layer but failed with the configured
  model/account mismatch.
- Local `~/.codex/config.toml` was fixed outside the repo by changing
  `service_tier` from `priority` to `fast`.

## Safety Status

- No Codex execution is required for automated tests.
- Missing env, missing confirmation, and missing `codex` command produce blocked
  results.
- Ariadne never auto-commits, auto-pushes, auto-merges, or creates PRs from the
  backend path.

## Current ARI-005 Impact

ARI-005 preserves the ARI-004 gate and adds route/resource/runtime/progress
visibility around both fake and real backend paths.
