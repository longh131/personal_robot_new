#!/bin/bash
# 启用 Ubuntu 上的 CSI 相机栈（需 root）。
# 模组：树莓派 Camera Rev 1.3 / OV5647 500万。
# CAM0（ov5647,cam0）已复测：I2C 无 0x36。本次改为 CAM1（dtoverlay=ov5647）。
set -euo pipefail
if [[ $(id -u) -ne 0 ]]; then
  echo "请用: sudo bash $0"
  exit 1
fi

apt-get install -y libcamera-ipa libcamera-tools python3-libcamera
usermod -aG i2c andylong || true

CFG=/boot/firmware/config.txt
BAK=/boot/firmware/config.txt.bak-csi-$(date +%Y%m%d)
if [[ ! -f $BAK ]]; then
  cp -a "$CFG" "$BAK"
fi

python3 - "$CFG" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
lines = []
skip_next_overlay = False
for line in p.read_text().splitlines():
    if "personal_robot_csi" in line:
        continue
    if line.strip().startswith("dtoverlay=imx219") or line.strip().startswith("dtoverlay=ov5647"):
        continue
    if line.strip().startswith("camera_auto_detect="):
        lines.append("camera_auto_detect=0")
        continue
    lines.append(line)
while lines and lines[-1].strip() == "":
    lines.pop()
lines.append("")
lines.append("# personal_robot_csi: OV5647 Camera v1 @ CAM1（Pi5 默认 Unicam1）")
lines.append("dtoverlay=ov5647")
p.write_text("\n".join(lines) + "\n")
print("updated", p)
PY

mkdir -p /opt/personal_robot/hardware_test/camera
echo "完成。请重启。预期 csi@128000 okay，ov5647 出现在 i2c（非 10 号）。"
echo "然后: cam --list"
