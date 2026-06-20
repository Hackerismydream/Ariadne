# Ariadne v1.0 Release Checklist

## Verification

- [ ] `python3.11 -m pytest`
- [ ] `python3.11 -m ruff check .`
- [ ] `scripts/verify_v1.sh`
- [ ] `python3.11 -m ariadne_ltb.cli doctor v1`
- [ ] Confirm `scripts/verify_v1.sh` prints separate sections for static
      checks, offline deterministic verification, production readiness
      verification, and optional real smoke verification.

## Product Path

- [ ] Open Workbench at `#delivery` and confirm Current Version Delivery is the
      first product surface.
- [ ] Browser path shows target project, source lifecycle, mainline issues,
      scoped daemon state, agent workflow, and execution proof.
- [ ] `ari doctor integrations`
- [ ] `ari doctor product --require-acceptance-ready`
- [ ] `ari ingest examples/sources/*.md --planner llm`
- [ ] `ari ticket list`
- [ ] `ari ticket assign ARI-003 --to codex --runtime-profile production`
- [ ] `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 ari daemon run-once --confirm-execution`
- [ ] `ari review run ARI-003 --reviewer llm`
- [ ] `FEISHU_ENABLE_WRITE=1 ari feishu write ARI-003 --confirm-write`
- [ ] `ari github sync ARI-003 --confirm-write`
- [ ] `ari ticket comments ARI-003`
- [ ] `ari runtime journal`
- [ ] `ari runtime recover`
- [ ] `ari export board`
- [ ] `ari landing gate ARI-003 --require-ready`
- [ ] `ari evidence packet --require-acceptance-ready`
- [ ] `ari board serve`

## Browser Dogfood Closure

- [ ] `ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real`
- [ ] Confirm `.ariadne/dogfood/<run-id>/closure-result.json` exists.
- [ ] Confirm the result packet has `status: REAL_CLOSED`.
- [ ] Confirm the evidence is Codex or Claude, not `fake-codex`, `dry-run`, or
      blocked rehearsal output.
- [ ] If the run is blocked, record `current-blocker.json` and do not mark
      closure complete.

## Offline Regression Fixture

- [ ] `ari ingest examples/sources/*.md`
- [ ] `ari ticket assign ARI-003 --to fake-codex`
- [ ] `ari daemon run-once`
- [ ] `ari export board`
- [ ] `python3.11 -m ariadne_ltb.cli demo full`
- [ ] Confirm `fake-codex`, `dry-run`, and `demo full` are treated as offline
      regression evidence only, not production acceptance.

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
- Local workbench frontend only; no hosted multi-user WebSocket/auth system.
- No Postgres-backed hosted service.
- Real Codex depends on local CLI availability.
- `fake-codex` remains for tests and offline fallback, not product acceptance.
- Feishu writes require an explicit real-write gate and confirmation.
