# -*- coding: utf-8 -*-
"""Optional ROS 2 pubs. Failures are logged, never open serial."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import threading
from pathlib import Path

log = logging.getLogger("remote.ros")

_SETUP = "source /opt/ros/jazzy/setup.bash"
_SKILL = Path(__file__).resolve().parent / "skill_pub.py"
_proc: subprocess.Popen | None = None
_lock = threading.Lock()


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
    _pub("/robot/mode_cmd", "std_msgs/msg/String", "{data: %s}" % mode)


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
    return {"vx_max": vx, "vy_max": vy, "wz_max": wz}


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
        return _proc
    except OSError as exc:
        log.warning("skill_pub start failed: %s", exc)
        _proc = None
        return None


def drive(vx: float, vy: float, wz: float) -> dict:
    mx, my, mz = _limits()
    vx = max(-mx, min(mx, float(vx)))
    vy = max(-my, min(my, float(vy)))
    wz = max(-mz, min(mz, float(wz)))
    with _lock:
        proc = _ensure_twist()
        if proc is None or proc.stdin is None:
            raise RuntimeError("skill_pub unavailable")
        proc.stdin.write(f"{vx:.4f} {vy:.4f} {wz:.4f}\n")
        proc.stdin.flush()
    return {"vx": vx, "vy": vy, "wz": wz}


def drive_stop() -> None:
    try:
        drive(0.0, 0.0, 0.0)
    except Exception as exc:
        log.warning("drive stop: %s", exc)
