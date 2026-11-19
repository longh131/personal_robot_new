#!/usr/bin/env bash
# Personal AI + frpc + ROS Safety/Bus/C30D. Does not send drive/gimbal itself.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRPC="$ROOT/tools/frp/frpc"
CFG="$ROOT/config/frpc.toml"
LOGDIR="$ROOT/logs"
pids=()
pgids=()

cleanup() {
  local pid
  for pid in "${pgids[@]+"${pgids[@]}"}"; do
    kill -- "-$pid" 2>/dev/null || true
  done
  for pid in "${pids[@]+"${pids[@]}"}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

mkdir -p "$LOGDIR"

if [[ -x "$FRPC" && -f "$CFG" ]]; then
  "$FRPC" -c "$CFG" &
  pids+=("$!")
  echo "frpc pid ${pids[-1]}"
else
  echo "frpc skipped (need $FRPC and $CFG)"
fi

if [[ -f /opt/ros/jazzy/setup.bash && -f "$ROOT/ros2_ws/install/setup.bash" ]]; then
  set +u
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
  # shellcheck disable=SC1091
  source "$ROOT/ros2_ws/install/setup.bash"
  set -u
  setsid ros2 launch safety_manager safety.launch.py >>"$LOGDIR/ros_bringup.log" 2>&1 &
  pgids+=("$!")
  echo "ros bringup pid ${pgids[-1]} (safety+bus+c30d+lidar, wait REMOTE cmd)"
  i=0
  while [[ "$i" -lt 25 ]]; do
    if ros2 node list 2>/dev/null | grep -q safety_manager; then
      echo "ros: safety_manager up"
      break
    fi
    i=$((i + 1))
    sleep 0.2
  done
  if ! ros2 node list 2>/dev/null | grep -q safety_manager; then
    echo "warn: safety_manager not up yet, see $LOGDIR/ros_bringup.log"
  fi
else
  echo "warn: ROS bringup skipped (need jazzy and ros2_ws/install)"
fi

PY="$ROOT/.venv/bin/python3"
if [[ ! -x "$PY" ]]; then
  PY=python3
  echo "warn: no $ROOT/.venv, using system python3 (mic wake may be off)"
fi
"$PY" "$ROOT/src/main.py" "$@"
