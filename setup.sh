#!/usr/bin/env bash
# System packages and tools. Do not apt-install from chat/scripts elsewhere.
# Usage: sudo ./setup.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "setup.sh: personal_robot system helpers"

# 云台：gpiozero + lgpio（venv 需 --system-site-packages）
if command -v apt-get >/dev/null; then
  apt-get install -y python3-gpiozero python3-lgpio libopencv-dev || true
fi
echo "gimbal: BCM24 pan / BCM19 tilt via gpiozero+lgpio"

# 雷达 USB 转接板 STC 34bf:ff0a → /dev/lidar
RULE_SRC="$ROOT/ros2_ws/src/lidar_pkg/scripts/99-lidar.rules"
RULE_DST=/etc/udev/rules.d/99-lidar.rules
if [[ -f "$RULE_SRC" ]]; then
  cp "$RULE_SRC" "$RULE_DST"
  udevadm control --reload-rules || true
  udevadm trigger || true
  echo "installed $RULE_DST"
fi
echo "done."
