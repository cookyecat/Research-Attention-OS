#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-}"
PROFILE="$ROOT/config/runtime/research-dogfood-v1.yaml"

usage() {
  echo "usage: $0 {manual|service}" >&2
  exit 2
}

[[ "$MODE" == "manual" || "$MODE" == "service" ]] || usage
[[ -f "$PROFILE" ]] || { echo "Missing runtime profile: $PROFILE" >&2; exit 2; }
[[ -f "$ROOT/.env" ]] || { echo "Missing $ROOT/.env. Copy .env.example and add local secrets first." >&2; exit 2; }

if [[ ! -x "$ROOT/backend/.venv/bin/python" ]]; then
  python3 -m venv "$ROOT/backend/.venv"
fi
"$ROOT/backend/.venv/bin/pip" install -e "$ROOT/backend"
(
  cd "$ROOT/backend"
  .venv/bin/alembic upgrade head
)
(
  cd "$ROOT/frontend"
  npm install
  npm run typecheck
  npm run build
)

chmod +x "$ROOT/scripts/raosctl" "$ROOT/scripts/raos-service-macos.sh"

if [[ "$MODE" == "service" ]]; then
  [[ "$(uname -s)" == "Darwin" ]] || { echo "Service install v0.1 currently supports macOS only." >&2; exit 2; }
  "$ROOT/scripts/raos-service-macos.sh" install
  echo "Installed RAOS in service mode."
else
  echo "Installed RAOS in manual mode. Start it with: $ROOT/scripts/raosctl start"
fi
