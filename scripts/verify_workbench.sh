#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT/frontend/ariadne-workbench"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to verify the Ariadne workbench frontend." >&2
  exit 1
fi

cd "$FRONTEND_DIR"

if [[ ! -d node_modules ]]; then
  npm ci --prefer-offline --no-audit --no-fund
fi

npm run sync:data
npm run build
