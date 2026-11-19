# -*- coding: utf-8 -*-
"""AWAKE self-check helpers. No remote import, no serial."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path

log = logging.getLogger("awake.status")

OBS_CACHE = Path("/opt/personal_robot/logs/robot_obstacle.json")
ESTOP_CACHE = Path("/opt/personal_robot/logs/robot_estop.json")
RPICAM = Path("/opt/personal_robot/scripts/rpicam.sh")


def camera_report() -> str:
    if not RPICAM.is_file():
        return "相机脚本不在，拍不了照。"
    try:
        proc = subprocess.run(
            [str(RPICAM), "rpicam-hello", "--list-cameras"],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("camera list: %s", exc)
        return "相机检查超时或失败。"
    out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    low = out.lower()
    if "no cameras available" in low:
        return "相机现在不可用，多半是排线或模组没应答。"
    for key in ("ov5647", "imx708", "imx219", "imx477", "imx296"):
        if key in low:
            return f"相机在线，传感器{key}。"
    if "available cameras" in low:
        # listed something but no known sensor name
        for line in out.splitlines():
            s = line.strip()
            if s and not s.lower().startswith("available"):
                return f"相机在线：{s[:50]}"
    return "相机现在不可用，多半是排线或模组没应答。"


def obstacle_snapshot() -> dict | None:
    try:
        if not OBS_CACHE.is_file():
            return None
        data = json.loads(OBS_CACHE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        ts = float(data.get("ts") or 0)
        if ts and (time.time() - ts) > 2.5:
            return None
        return data
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def obstacle_blocked() -> bool:
    data = obstacle_snapshot()
    if not data:
        return False
    return bool(data.get("blocked") or data.get("stop") or data.get("obstacle_stop"))


def estop_latched() -> bool | None:
    try:
        if not ESTOP_CACHE.is_file():
            return None
        data = json.loads(ESTOP_CACHE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        ts = float(data.get("ts") or 0)
        if ts and (time.time() - ts) > 5.0:
            return None
        return bool(data.get("estop"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def estop_report() -> str:
    v = estop_latched()
    if v is None:
        return "急停状态暂时读不到；若刚开机，说声前进前再问一次。"
    return "软件急停已拉住，要网页复位后才能动。" if v else "现在没有软件急停。"
