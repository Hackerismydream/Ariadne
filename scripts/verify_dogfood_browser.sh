#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT/frontend/ariadne-workbench"
PORT="${ARIADNE_WORKBENCH_PORT:-18766}"
HOST="${ARIADNE_WORKBENCH_HOST:-127.0.0.1}"
URL="${ARIADNE_WORKBENCH_URL:-http://${HOST}:${PORT}}"
TARGET_PATH="${ARIADNE_DOGFOOD_TARGET_PATH:-/Users/martinlos/code/ariadne-dogfood/mini-code-agent}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RESULT_DIR="${ARIADNE_DOGFOOD_RESULT_DIR:-$ROOT/.ariadne/dogfood/browser-$RUN_ID}"
LOG_DIR="$RESULT_DIR/logs"
SERVER_LOG="$LOG_DIR/workbench.log"
MODE="blocked-ok"
STARTED_SERVER=0

usage() {
  cat <<'EOF'
Usage:
  scripts/verify_dogfood_browser.sh --blocked-ok
  ARIADNE_ENABLE_EXTERNAL_EXECUTION=1 scripts/verify_dogfood_browser.sh --real

This is the Ariadne product-path dogfood harness. It may start the local
Workbench server, then mutates Ariadne only through browser UI events.

--blocked-ok records the first browser-path blocker and exits 0 when a blocker
             was captured. This is a rehearsal, not closure evidence.
--real       requires the browser path to reach real Codex/Claude execution.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --blocked-ok)
      MODE="blocked-ok"
      shift
      ;;
    --real)
      MODE="real"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

mkdir -p "$LOG_DIR"

cleanup() {
  if [[ "$STARTED_SERVER" == "1" && -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

wait_for_workbench() {
  local attempts=80
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$URL/api/workbench" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required for browser dogfood verification." >&2
  exit 2
fi

if ! curl -fsS "$URL/api/workbench" >/dev/null 2>&1; then
  (
    cd "$FRONTEND_DIR"
    npm run build
  ) >>"$SERVER_LOG" 2>&1
  (
    cd "$ROOT"
    python3.11 -m ariadne_ltb.cli workbench serve --host "$HOST" --port "$PORT"
  ) >>"$SERVER_LOG" 2>&1 &
  SERVER_PID=$!
  STARTED_SERVER=1
  if ! wait_for_workbench; then
    echo "Workbench did not become ready at $URL. See $SERVER_LOG" >&2
    exit 1
  fi
fi

(
  cd "$FRONTEND_DIR"
  set +e
  ARIADNE_WORKBENCH_URL="$URL" \
    ARIADNE_DOGFOOD_MODE="$MODE" \
    ARIADNE_DOGFOOD_RESULT_DIR="$RESULT_DIR" \
    ARIADNE_DOGFOOD_SERVER_LOG="$SERVER_LOG" \
    ARIADNE_DOGFOOD_TARGET_PATH="$TARGET_PATH" \
    npx playwright test e2e/mini-code-agent-dogfood.spec.ts --reporter=line --trace=retain-on-failure
  status=$?
  set -e

  if [[ "$MODE" == "blocked-ok" && "$status" != "0" && -f "$RESULT_DIR/current-blocker.json" ]]; then
    echo "DOGFOOD_BROWSER_BLOCKED_OK"
    echo "Result directory: $RESULT_DIR"
    echo "Blocker: $RESULT_DIR/current-blocker.json"
    echo "Server log: $SERVER_LOG"
    exit 0
  fi

  if [[ "$status" == "0" && "$MODE" == "real" ]]; then
    echo "DOGFOOD_BROWSER_REAL_PATH_COMPLETED"
    echo "Result directory: $RESULT_DIR"
    echo "Server log: $SERVER_LOG"
  elif [[ "$status" == "0" ]]; then
    echo "DOGFOOD_BROWSER_REHEARSAL_FALSE_GREEN"
    echo "blocked-ok reached the end without recording a blocker. Tighten the harness or rerun with --real."
    echo "Result directory: $RESULT_DIR"
    echo "Server log: $SERVER_LOG"
    exit 1
  else
    echo "DOGFOOD_BROWSER_FAILED_WITHOUT_CAPTURED_BLOCKER"
    echo "Result directory: $RESULT_DIR"
    echo "Server log: $SERVER_LOG"
  fi
  exit "$status"
)
