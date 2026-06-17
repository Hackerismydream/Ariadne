# Ariadne v1.0 Release Checklist

## Verification

- [ ] `python3.11 -m pytest`
- [ ] `python3.11 -m ruff check .`
- [ ] `scripts/verify_v1.sh`
- [ ] `python3.11 -m ariadne_ltb.cli doctor v1`

## Product Path

- [ ] `ari doctor integrations`
- [ ] `ari doctor product --require-acceptance-ready`
- [ ] `ari ingest examples/sources/*.md --planner llm`
- [ ] `ari ticket list`
- [ ] `ari ticket assign ARI-003 --to codex --agent-runtime llm --backlog-planner llm`
- [ ] `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution`
- [ ] `ari review run ARI-003 --reviewer llm`
- [ ] `FEISHU_ENABLE_WRITE=1 ari feishu write ARI-003 --confirm-write`
- [ ] `ari github sync ARI-003 --confirm-write`
- [ ] `ari ticket comments ARI-003`
- [ ] `ari runtime journal`
- [ ] `ari runtime recover`
- [ ] `ari export board`
- [ ] `ari evidence packet --require-acceptance-ready`
- [ ] `ari board serve`

## Deterministic Regression Path

- [ ] `ari ingest examples/sources/*.md`
- [ ] `ari ticket assign ARI-003 --to fake-codex`
- [ ] `ari daemon run-once`
- [ ] `ari export board`
- [ ] Confirm this path is treated as offline regression evidence only, not
      production acceptance.

## Safety Gates

- [ ] External execution requires `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1`.
- [ ] External execution requires `--confirm-execution`.
- [ ] Real Feishu write requires `FEISHU_ENABLE_WRITE=1`.
- [ ] Real Feishu write requires `--confirm-write`.
- [ ] No secrets are printed by doctor commands.
- [ ] `.env`, `.env.*`, `*.secret`, `secrets/`, and `.ariadne/` are gitignored.

## Known Limitations

- Local single-worker runtime.
- JSON/JSONL persistence.
- No production Web UI.
- No Postgres, WebSocket, auth, or permissions system.
- Real Codex depends on local CLI availability.
- `fake-codex` remains for tests and offline fallback, not product acceptance.
- Feishu writes require an explicit real-write gate and confirmation.
