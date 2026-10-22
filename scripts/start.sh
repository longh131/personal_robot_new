#!/usr/bin/env bash
# Personal AI + optional frpc. No ROS, no motors.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRPC="$ROOT/tools/frp/frpc"
CFG="$ROOT/config/frpc.toml"
pids=()

cleanup() {
  local pid
  for pid in "${pids[@]+"${pids[@]}"}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ -x "$FRPC" && -f "$CFG" ]]; then
  "$FRPC" -c "$CFG" &
  pids+=("$!")
  echo "frpc pid ${pids[-1]}"
else
  echo "frpc skipped (need $FRPC and $CFG)"
fi

PY="$ROOT/.venv/bin/python3"
if [[ ! -x "$PY" ]]; then
  PY=python3
  echo "warn: no $ROOT/.venv, using system python3 (mic wake may be off)"
fi
"$PY" "$ROOT/src/main.py" "$@"
