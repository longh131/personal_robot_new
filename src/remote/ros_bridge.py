# -*- coding: utf-8 -*-
"""Optional ROS 2 pubs. Failures are logged, never open serial."""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
import threading
import time
from pathlib import Path

log = logging.getLogger("remote.ros")

_SETUP = (
    "source /opt/ros/jazzy/setup.bash && "
    "source /opt/personal_robot/ros2_ws/install/setup.bash"
)
_SKILL = Path(__file__).resolve().parent / "skill_pub.py"
_OBS_CACHE = Path("/opt/personal_robot/logs/remote_obstacle.json")
_proc: subprocess.Popen | None = None
_lock = threading.Lock()
_speed_scale = 1.0
_SCALE_MIN = 0.2
_SCALE_MAX = 1.0


def _pub(topic: str, typ: str, yaml_body: str) -> None:
    cmd = f"{_SETUP} && ros2 topic pub --once {topic} {typ} {shlex.quote(yaml_body)}"
    try:
        subprocess.run(
            ["bash", "-lc", cmd],
            check=False,
            capture_output=True,
            text=True,
            timeout=4,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("ros pub failed %s: %s", topic, exc)


def mode_cmd(mode: str) -> None:
    """Ask Safety for mode via ros2 topic pub --once (waits for subscriber)."""
    target = (mode or "IDLE").strip().upper()
    # Also nudge long-lived skill_pub if up; never skip the reliable --once path.
    with _lock:
        proc = _proc
        if proc is not None and proc.poll() is None and proc.stdin is not None:
            try:
                proc.stdin.write(f"MODE {target}\n")
                proc.stdin.flush()
            except OSError as exc:
                log.warning("mode_cmd skill_pub nudge failed: %s", exc)
    _pub("/robot/mode_cmd", "std_msgs/msg/String", "{data: '%s'}" % target)
    time.sleep(0.2)
    log.info("mode_cmd via ros2 pub --once %s", target)


def estop(latched: bool) -> None:
    _pub("/robot/estop", "std_msgs/msg/Bool", "{data: %s}" % ("true" if latched else "false"))


def skill_ping(command_id: str) -> None:
    inner = (
        '{"command_id":"%s","source":"remote","skill_id":"ping"}' % command_id
    )
    _pub("/robot/skill_cmd", "std_msgs/msg/String", "{data: '%s'}" % inner)


def _limits() -> tuple[float, float, float]:
    from settings import robot_get

    vx = abs(float(robot_get("remote", "vx_max", default=0.15) or 0.15))
    vy = abs(float(robot_get("remote", "vy_max", default=0.15) or 0.15))
    wz = abs(float(robot_get("remote", "wz_max", default=0.40) or 0.40))
    return vx, vy, wz


def motion_limits() -> dict:
    vx, vy, wz = _limits()
    return {
        "vx_max": vx,
        "vy_max": vy,
        "wz_max": wz,
        "scale": _speed_scale,
        "scale_min": _SCALE_MIN,
        "scale_max": _SCALE_MAX,
        "vx_eff": round(vx * _speed_scale, 4),
        "vy_eff": round(vy * _speed_scale, 4),
        "wz_eff": round(wz * _speed_scale, 4),
    }


def set_speed_scale(scale: float) -> dict:
    global _speed_scale
    _speed_scale = max(_SCALE_MIN, min(_SCALE_MAX, float(scale)))
    return motion_limits()


def obstacle_status() -> dict | None:
    try:
        if not _OBS_CACHE.is_file():
            return None
        data = json.loads(_OBS_CACHE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        ts = float(data.get("ts") or 0)
        if ts and (time.time() - ts) > 2.0:
            data = dict(data)
            data["stale_ui"] = True
        return data
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _ensure_twist() -> subprocess.Popen | None:
    global _proc
    if _proc is not None and _proc.poll() is None:
        return _proc
    cmd = f"{_SETUP} && exec python3 {shlex.quote(str(_SKILL))}"
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        _proc = subprocess.Popen(
            ["bash", "-lc", cmd],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=env,
        )
        log.info("skill_pub pid=%s", _proc.pid)
        # allow node to create pubs before first MODE/drive
        time.sleep(0.4)
        return _proc
    except OSError as exc:
        log.warning("skill_pub start failed: %s", exc)
        _proc = None
        return None


def drive(vx: float, vy: float, wz: float) -> dict:
    mx, my, mz = _limits()
    scale = _speed_scale
    # UI sends unit fractions in [-1, 1]
    fx = max(-1.0, min(1.0, float(vx)))
    fy = max(-1.0, min(1.0, float(vy)))
    fz = max(-1.0, min(1.0, float(wz)))
    vx = fx * mx * scale
    vy = fy * my * scale
    wz = fz * mz * scale
    with _lock:
        proc = _ensure_twist()
        if proc is None or proc.stdin is None:
            raise RuntimeError("skill_pub unavailable")
        proc.stdin.write(f"{vx:.4f} {vy:.4f} {wz:.4f}\n")
        proc.stdin.flush()
    return {"vx": vx, "vy": vy, "wz": wz, "scale": scale}


def ensure_skill_pub() -> None:
    with _lock:
        _ensure_twist()


def drive_stop() -> None:
    try:
        drive(0.0, 0.0, 0.0)
    except Exception as exc:
        log.warning("drive stop: %s", exc)
