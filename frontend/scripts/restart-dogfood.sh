#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-3000}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PIDS="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN || true)"
if [[ -n "$PIDS" ]]; then
  echo "Stopping existing frontend on port $PORT: $PIDS"
  kill $PIDS || true
  for _ in {1..20}; do
    if ! lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
      break
    fi
    sleep 0.1
  done
fi
if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is still occupied; refusing to overwrite .next while a server is live." >&2
  exit 1
fi

rm -rf .next
npm run typecheck
npm run build
exec npm run dogfood
