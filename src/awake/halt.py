# -*- coding: utf-8 -*-
"""Continuous drive via awake skill_pub → Bus → /cmd_vel_awake. No remote import, no serial."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import threading
import time
from pathlib import Path

from settings import robot_get

log = logging.getLogger("awake.halt")

_SETUP = (
    "source /opt/ros/jazzy/setup.bash && "
    "source /opt/personal_robot/ros2_ws/install/setup.bash"
)
_SKILL = Path(__file__).resolve().parent / "skill_pub.py"

_lock = threading.Lock()
_proc: subprocess.Popen | None = None
_hold: tuple[float, float, float] | None = None  # base at scale=1 limits
_dir: tuple[float, float, float] | None = None  # unit direction before scale
_scale = 1.0
_refresh: threading.Thread | None = None
_mode_epoch = 0
_SCALE_MIN = 0.4
_SCALE_MAX = 1.0
_SCALE_STEP = 0.2


def _limits() -> tuple[float, float, float, float]:
    vx = abs(float(robot_get("awake", "vx_max", default=0.12) or 0.12))
    vy = abs(float(robot_get("awake", "vy_max", default=0.12) or 0.12))
    wz = abs(float(robot_get("awake", "wz_max", default=0.35) or 0.35))
    refresh = float(robot_get("awake", "drive_refresh_s", default=0.4) or 0.4)
    refresh = max(0.2, min(0.8, refresh))
    return vx, vy, wz, refresh


def _ensure_pub() -> subprocess.Popen | None:
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
        log.info("awake skill_pub pid=%s", _proc.pid)
        time.sleep(0.4)
        return _proc
    except OSError as exc:
        log.warning("awake skill_pub start failed: %s", exc)
        _proc = None
        return None


def _write_line(line: str) -> None:
    proc = _ensure_pub()
    if proc is None or proc.stdin is None:
        raise RuntimeError("awake skill_pub unavailable")
    proc.stdin.write(line if line.endswith("\n") else line + "\n")
    proc.stdin.flush()


def bump_mode_epoch() -> int:
    """Invalidate in-flight MODE AWAKE (e.g. leave before wake pub finishes)."""
    global _mode_epoch
    with _lock:
        _mode_epoch += 1
        return _mode_epoch


def mode_epoch() -> int:
    with _lock:
        return _mode_epoch


def _ros2_mode_once(target: str) -> None:
    """Reliable path — same idea as remote.ros_bridge.mode_cmd."""
    body = "{data: '%s'}" % target
    cmd = (
        f"{_SETUP} && "
        f"ros2 topic pub --once /robot/mode_cmd std_msgs/msg/String {shlex.quote(body)}"
    )
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
        log.warning("awake mode_cmd ros2 once %s: %s", target, exc)


def mode_cmd(mode: str, *, expect_epoch: int | None = None) -> None:
    """Sync Safety/Bus mode. Required before awake drive or follow."""
    target = (mode or "IDLE").strip().upper()
    with _lock:
        if expect_epoch is not None and expect_epoch != _mode_epoch:
            log.info("awake mode_cmd skip stale %s epoch=%s now=%s", target, expect_epoch, _mode_epoch)
            return
        try:
            _write_line(f"MODE {target}")
        except Exception as exc:
            log.warning("awake mode_cmd skill_pub %s: %s", target, exc)
    # Always pub --once so leave→IDLE is not lost if skill_pub is wedged
    _ros2_mode_once(target)
    log.info("awake mode_cmd %s", target)


def _pub_drive(vx: float, vy: float, wz: float) -> None:
    _write_line(f"{vx:.4f} {vy:.4f} {wz:.4f}")


def _scaled_hold() -> tuple[float, float, float] | None:
    if _dir is None:
        return None
    dx, dy, dz = _dir
    return (dx * _scale, dy * _scale, dz * _scale)


def _refresh_loop(period: float) -> None:
    global _hold
    while True:
        time.sleep(period)
        with _lock:
            hold = _hold
            if hold is None:
                continue
            try:
                _pub_drive(*hold)
            except Exception as exc:
                log.warning("awake drive refresh: %s", exc)
                _hold = None


def _ensure_refresh(period: float) -> None:
    global _refresh
    if _refresh is not None and _refresh.is_alive():
        return
    _refresh = threading.Thread(
        target=_refresh_loop,
        args=(period,),
        name="awake-drive",
        daemon=True,
    )
    _refresh.start()


def is_holding() -> bool:
    with _lock:
        return _hold is not None


def drive_stop() -> None:
    """Zero and clear continuous hold."""
    global _hold, _dir
    with _lock:
        _hold = None
        _dir = None
        try:
            _pub_drive(0.0, 0.0, 0.0)
        except Exception as exc:
            log.warning("awake drive_stop: %s", exc)
    log.info("awake drive_stop")


def drive_hold(vx: float, vy: float, wz: float) -> str:
    """Keep moving until drive_stop / leave AWAKE. Obstacle still via Safety."""
    global _hold, _dir, _scale
    mx, my, mz, period = _limits()
    vx = max(-mx, min(mx, float(vx)))
    vy = max(-my, min(my, float(vy)))
    wz = max(-mz, min(mz, float(wz)))
    if abs(vx) < 1e-6 and abs(vy) < 1e-6 and abs(wz) < 1e-6:
        drive_stop()
        return "好，停下。"
    _scale = 1.0
    with _lock:
        _dir = (vx, vy, wz)
        _hold = (vx, vy, wz)
        try:
            _pub_drive(vx, vy, wz)
        except Exception as exc:
            _hold = None
            _dir = None
            log.warning("awake drive_hold: %s", exc)
            return "运动链路没通，这步没走成。"
    _ensure_refresh(period)
    if abs(vx) >= abs(vy) and abs(vx) >= abs(wz):
        label = "前进" if vx > 0 else "后退"
    elif abs(vy) >= abs(wz):
        label = "左移" if vy > 0 else "右移"
    else:
        label = "左转" if wz > 0 else "右转"
    log.info("awake drive_hold %s vx=%.3f vy=%.3f wz=%.3f", label, vx, vy, wz)
    return f"好，持续{label}，说停下就停。"


def drive_faster() -> str:
    global _scale, _hold
    if not is_holding():
        return "现在没有在走，先说前进或后退。"
    with _lock:
        _scale = min(_SCALE_MAX, _scale + _SCALE_STEP)
        hold = _scaled_hold()
        _hold = hold
        if hold is None:
            return "现在没有在走。"
        try:
            _pub_drive(*hold)
        except Exception as exc:
            log.warning("drive_faster: %s", exc)
            return "调速没发出去。"
    pct = int(round(_scale * 100))
    return f"好，加速到大约{pct}%。"


def drive_slower() -> str:
    global _scale, _hold
    if not is_holding():
        return "现在没有在走，先说前进或后退。"
    with _lock:
        _scale = max(_SCALE_MIN, _scale - _SCALE_STEP)
        hold = _scaled_hold()
        _hold = hold
        if hold is None:
            return "现在没有在走。"
        try:
            _pub_drive(*hold)
        except Exception as exc:
            log.warning("drive_slower: %s", exc)
            return "调速没发出去。"
    pct = int(round(_scale * 100))
    return f"好，减速到大约{pct}%。"


def drive_pulse(vx: float, vy: float, wz: float) -> str:
    return drive_hold(vx, vy, wz)


def parse_drive_cmd(text: str) -> tuple[float, float, float] | None:
    """Map utterance to unit direction; None if unknown."""
    t = "".join((text or "").split())
    mx, my, mz, _ = _limits()
    if any(k in t for k in ("往前", "向前", "前进")):
        return mx, 0.0, 0.0
    if any(k in t for k in ("后退", "向后", "往后")):
        return -mx, 0.0, 0.0
    if any(k in t for k in ("左移", "往左", "向左移")):
        return 0.0, my, 0.0
    if any(k in t for k in ("右移", "往右", "向右移")):
        return 0.0, -my, 0.0
    if "左转" in t or "向左" in t:
        return 0.0, 0.0, mz
    if "右转" in t or "向右" in t:
        return 0.0, 0.0, -mz
    return None
