#!/usr/bin/env bash
set -euo pipefail

section() {
  printf '\n== %s ==\n' "$1"
}

section "Static checks"
python3.11 -m pytest
python3.11 -m ruff check .

section "Production readiness verification"
python3.11 -m ariadne_ltb.cli backend doctor
python3.11 -m ariadne_ltb.cli doctor integrations
python3.11 -m ariadne_ltb.cli doctor product --require-acceptance-ready
python3.11 -m ariadne_ltb.cli doctor secrets
python3.11 -m ariadne_ltb.cli doctor store
python3.11 -m ariadne_ltb.cli doctor v1
python3.11 -m ariadne_ltb.cli evidence packet --require-acceptance-ready
scripts/verify_workbench.sh

section "Offline deterministic verification (non-acceptance)"
echo "This section validates fixtures and deterministic regression only; it is not product acceptance."
python3.11 -m ariadne_ltb.cli demo full
python3.11 -m ariadne_ltb.cli ingest examples/sources/*.md
python3.11 -m ariadne_ltb.cli ticket list
python3.11 -m ariadne_ltb.cli workdir cleanup --confirm-cleanup --force-dirty
assignment_output="$(python3.11 -m ariadne_ltb.cli ticket assign ARI-003 --to fake-codex)"
printf '%s\n' "$assignment_output"
assignment_id="$(printf '%s\n' "$assignment_output" | awk '/^Assignment created:/ {print $3}')"
python3.11 -m ariadne_ltb.cli daemon run-once --assignment-id "$assignment_id"
python3.11 -m ariadne_ltb.cli landing gate ARI-003 --require-ready
python3.11 -m ariadne_ltb.cli ticket comments ARI-003
python3.11 -m ariadne_ltb.cli runtime journal
python3.11 -m ariadne_ltb.cli runtime recover
python3.11 -m ariadne_ltb.cli daemon status
python3.11 -m ariadne_ltb.cli workdir list
python3.11 -m ariadne_ltb.cli workdir cleanup --confirm-cleanup --force-dirty
python3.11 -m ariadne_ltb.cli export board

section "Optional real smoke verification"
if [[ "${ARIADNE_RUN_REAL_SMOKE:-0}" != "1" ]]; then
  echo "Skipped. Set ARIADNE_RUN_REAL_SMOKE=1 plus provider credentials/login gates to run real smoke tests."
else
  python3.11 -m ariadne_ltb.cli llm smoke --provider deepseek --confirm-external
  if command -v codex >/dev/null 2>&1; then
    ARIADNE_ENABLE_EXTERNAL_EXECUTION="${ARIADNE_ENABLE_EXTERNAL_EXECUTION:-1}" \
      python3.11 -m ariadne_ltb.cli backend smoke-test codex \
        --runtime-profile production \
        --confirm-execution \
        --timeout-seconds 180
  else
    echo "Codex CLI missing; Codex real smoke skipped."
  fi
  if command -v claude >/dev/null 2>&1; then
    ARIADNE_ENABLE_EXTERNAL_EXECUTION="${ARIADNE_ENABLE_EXTERNAL_EXECUTION:-1}" \
      python3.11 -m ariadne_ltb.cli backend smoke-test claude-code \
        --runtime-profile production \
        --confirm-execution \
        --timeout-seconds 180
  else
    echo "Claude CLI missing; Claude real smoke skipped."
  fi
fi
