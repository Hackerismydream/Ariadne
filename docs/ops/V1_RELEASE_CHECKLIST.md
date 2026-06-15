# Ariadne v1.0 Release Checklist

## Verification

- [ ] `pytest`
- [ ] `ruff check .`
- [ ] `scripts/verify_v1.sh`
- [ ] `python3.11 -m ariadne_ltb.cli doctor v1`

## Product Path

- [ ] `ari ingest examples/sources/*.md`
- [ ] `ari ticket list`
- [ ] `ari ticket assign ARI-003 --to fake-codex`
- [ ] `ari daemon run-once`
- [ ] `ari ticket comments ARI-003`
- [ ] `ari runtime journal`
- [ ] `ari runtime recover`
- [ ] `ari export board`
- [ ] `ari board serve`

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
- Feishu writes are dry-run by default.
