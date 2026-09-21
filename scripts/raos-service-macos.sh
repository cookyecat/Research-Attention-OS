#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/RAOS"
DOMAIN="gui/$(id -u)"
PROFILE="$ROOT/config/runtime/research-dogfood-v1.yaml"
LABELS=(ai.raos.backend ai.raos.acquisition ai.raos.delivery ai.raos.frontend)

require_macos() {
  [[ "$(uname -s)" == "Darwin" ]] || { echo "macOS launchd service mode is only available on macOS." >&2; exit 2; }
}

require_runtime() {
  [[ -x "$ROOT/backend/.venv/bin/python" ]] || { echo "Backend venv is missing. Run scripts/install-raos.sh first." >&2; exit 2; }
  [[ -x "$ROOT/backend/.venv/bin/uvicorn" ]] || { echo "uvicorn is missing from backend venv." >&2; exit 2; }
  [[ -f "$ROOT/frontend/node_modules/next/dist/bin/next" ]] || { echo "Frontend dependencies are missing." >&2; exit 2; }
  [[ -f "$ROOT/frontend/.next/BUILD_ID" ]] || { echo "Frontend production build is missing." >&2; exit 2; }
  [[ -f "$ROOT/.env" ]] || { echo "$ROOT/.env is missing; refusing background service installation without explicit runtime configuration." >&2; exit 2; }
  [[ -f "$PROFILE" ]] || { echo "Canonical runtime profile missing: $PROFILE" >&2; exit 2; }
}

node_path() {
  command -v node || { echo "node is required for the frontend service." >&2; exit 2; }
}

plist_path() { printf '%s/%s.plist' "$PLIST_DIR" "$1"; }
render_plists() {
  local out_dir="${1:-$PLIST_DIR}"
  local py="$ROOT/backend/.venv/bin/python"
  local uvicorn="$ROOT/backend/.venv/bin/uvicorn"
  local node
  node="$(node_path)"
  mkdir -p "$out_dir" "$LOG_DIR"

  RAOS_ROOT="$ROOT" RAOS_UVICORN="$uvicorn" RAOS_PYTHON="$py" RAOS_NODE="$node" \
  RAOS_LOG_DIR="$LOG_DIR" "$py" - "$out_dir" <<'PY'
import os, plistlib, sys
from pathlib import Path

root = Path(os.environ["RAOS_ROOT"])
out = Path(sys.argv[1])
logs = Path(os.environ["RAOS_LOG_DIR"])
backend, frontend = root / "backend", root / "frontend"
python, uvicorn, node = os.environ["RAOS_PYTHON"], os.environ["RAOS_UVICORN"], os.environ["RAOS_NODE"]
env_file = root / ".env"
next_bin = frontend / "node_modules" / "next" / "dist" / "bin" / "next"

specs = {
    "ai.raos.backend": (backend, [uvicorn, "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--env-file", str(env_file)]),
    "ai.raos.acquisition": (backend, [python, "-m", "app.acquisition_worker", "--env-file", str(env_file), "--interval", "60", "--limit-per-source", "5"]),
    "ai.raos.delivery": (backend, [python, "-m", "app.delivery_worker", "--env-file", str(env_file)]),
    "ai.raos.frontend": (frontend, [node, str(next_bin), "start", "-H", "127.0.0.1", "-p", "3000"]),
}
for label, (cwd, args) in specs.items():
    payload = {
        "Label": label,
        "ProgramArguments": [str(x) for x in args],
        "WorkingDirectory": str(cwd),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 5,
        "ProcessType": "Background",
        "EnvironmentVariables": {
            "RAOS_RUNTIME_INSTALL_MODE": "service",
            "RAOS_RUNTIME_PROFILE": str(root / "config" / "runtime" / "research-dogfood-v1.yaml"),
            "RAOS_EXECUTION_PURPOSE": "CANONICAL",
        },
        "StandardOutPath": str(logs / f"{label}.out.log"),
        "StandardErrorPath": str(logs / f"{label}.err.log"),
    }
    with (out / f"{label}.plist").open("wb") as fh:
        plistlib.dump(payload, fh, sort_keys=False)
PY
}

is_loaded() {
  launchctl print "$DOMAIN/$1" >/dev/null 2>&1
}

unload_label() {
  local label="$1" path
  path="$(plist_path "$label")"
  if is_loaded "$label"; then
    launchctl bootout "$DOMAIN/$label" >/dev/null 2>&1 || launchctl bootout "$DOMAIN" "$path" >/dev/null 2>&1 || true
  fi
}

launchd_pid() {
  local label="$1"
  launchctl print "$DOMAIN/$label" 2>/dev/null | awk '/^[[:space:]]*pid = / {print $3; exit}'
}

pid_cwd() {
  local pid="$1"
  lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1
}

cleanup_orphan_group() {
  local label="$1" expected_cwd="$2" pattern="$3"
  local managed pid cwd
  managed="$(launchd_pid "$label" || true)"
  while read -r pid; do
    [[ -n "$pid" ]] || continue
    [[ -n "$managed" && "$pid" == "$managed" ]] && continue
    cwd="$(pid_cwd "$pid")"
    [[ "$cwd" == "$expected_cwd" ]] || continue
    echo "Stopping orphan RAOS process pid=$pid label=$label cwd=$cwd"
    kill -TERM "$pid" >/dev/null 2>&1 || true
  done < <(pgrep -f "$pattern" 2>/dev/null || true)
}

cleanup_orphan_processes() {
  cleanup_orphan_group "ai.raos.backend" "$ROOT/backend" "uvicorn app.main:app"
  cleanup_orphan_group "ai.raos.acquisition" "$ROOT/backend" "app.acquisition_worker"
  cleanup_orphan_group "ai.raos.delivery" "$ROOT/backend" "app.delivery_worker"
  cleanup_orphan_group "ai.raos.frontend" "$ROOT/frontend" "next-server"
  sleep 0.4
}
install_service() {
  require_runtime
  mkdir -p "$PLIST_DIR" "$LOG_DIR"
  for label in "${LABELS[@]}"; do unload_label "$label"; done
  cleanup_orphan_processes
  render_plists "$PLIST_DIR"
  for label in "${LABELS[@]}"; do
    launchctl bootstrap "$DOMAIN" "$(plist_path "$label")"
    launchctl enable "$DOMAIN/$label" >/dev/null 2>&1 || true
    launchctl kickstart -k "$DOMAIN/$label"
  done
  echo "RAOS service mode installed. It will start automatically after user login."
}

uninstall_service() {
  for label in "${LABELS[@]}"; do
    unload_label "$label"
    rm -f "$(plist_path "$label")"
  done
  echo "RAOS launchd services removed. Repository data and configuration were preserved."
}

start_service() {
  require_runtime
  cleanup_orphan_processes
  render_plists "$PLIST_DIR"
  for label in "${LABELS[@]}"; do
    if ! is_loaded "$label"; then launchctl bootstrap "$DOMAIN" "$(plist_path "$label")"; fi
    launchctl kickstart -k "$DOMAIN/$label"
  done
}

stop_service() {
  for label in "${LABELS[@]}"; do unload_label "$label"; done
  cleanup_orphan_processes
}
status_service() {
  local installed=0
  for label in "${LABELS[@]}"; do
    local path state
    path="$(plist_path "$label")"
    [[ -f "$path" ]] && installed=$((installed + 1))
    if is_loaded "$label"; then state="LOADED"; else state="STOPPED"; fi
    printf '%-24s %-8s %s\n' "$label" "$state" "$path"
  done
  if [[ "$installed" -eq "${#LABELS[@]}" ]]; then
    echo "install_mode=service"
  else
    echo "install_mode=manual-or-partial"
  fi
}

usage() {
  echo "usage: $0 {install|uninstall|start|stop|restart|status|render [DIR]}" >&2
  exit 2
}

require_macos
cmd="${1:-}"
case "$cmd" in
  install) install_service ;;
  uninstall) uninstall_service ;;
  start) start_service ;;
  stop) stop_service ;;
  restart) stop_service; start_service ;;
  status) status_service ;;
  render) require_runtime; render_plists "${2:-$ROOT/.runtime/launchd}"; echo "Rendered launchd plists to ${2:-$ROOT/.runtime/launchd}" ;;
  *) usage ;;
esac
