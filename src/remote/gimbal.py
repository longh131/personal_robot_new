# -*- coding: utf-8 -*-
"""MG90S pan/tilt via gpiozero + lgpio (same stack as hardware_test/gimbal).

Pan BCM24 / tilt BCM19. Pulse only while moving; detach when idle to avoid jitter.
"""

from __future__ import annotations

import logging
import threading
import time

from settings import robot_get

log = logging.getLogger("remote.gimbal")

DIRS = ("up", "down", "left", "right", "stop", "home")


def _f(key: str, default: float) -> float:
    return float(robot_get("gimbal", key, default=default) or default)


def _i(key: str, default: int) -> int:
    return int(robot_get("gimbal", key, default=default) or default)


def clamp_pulse(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def step_pulse(current: float, delta: float, lo: float, hi: float) -> float:
    return clamp_pulse(current + delta, lo, hi)


def active_axis(direction: str | None, pan: float, tilt: float, mid: float, step: float) -> str | None:
    if direction in ("left", "right"):
        return "pan"
    if direction in ("up", "down"):
        return "tilt"
    if direction != "home":
        return None
    if abs(pan - mid) > step:
        return "pan"
    if abs(tilt - mid) > step:
        return "tilt"
    return None


def pulse_to_value(pulse_s: float, lo: float, hi: float) -> float:
    half = max((hi - lo) / 2.0, 1e-6)
    mid = (lo + hi) / 2.0
    return max(-1.0, min(1.0, (pulse_s - mid) / half))


class Gimbal:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pan_servo = None
        self._tilt_servo = None
        self._mode = "none"
        self._dir: str | None = None
        self._last_cmd = 0.0
        self._error = ""
        self._pan = 0.0015
        self._tilt = 0.0015
        self._running = False

    def enabled(self) -> bool:
        return bool(robot_get("gimbal", "enabled", default=False))

    def status(self) -> dict:
        with self._lock:
            return {
                "model": str(robot_get("gimbal", "model", default="MG90S") or "MG90S"),
                "connected": self._running and self._error == "",
                "enabled": self.enabled(),
                "dir": self._dir or "stop",
                "error": self._error,
                "pwm_mode": self._mode,
                "hold": False,
                "single_axis_move": True,
                "pan_bcm": _i("pan_bcm", 24),
                "tilt_bcm": _i("tilt_bcm", 19),
                "pan_us": int(self._pan * 1e6),
                "tilt_us": int(self._tilt * 1e6),
            }

    def start(self) -> None:
        if not self.enabled():
            return
        with self._lock:
            if self._running:
                return
            self._error = ""
            mid = _f("pulse_mid_s", 0.0015)
            self._pan = clamp_pulse(mid, _f("pan_min_s", 0.0010), _f("pan_max_s", 0.0020))
            self._tilt = clamp_pulse(mid, _f("tilt_min_s", 0.0010), _f("tilt_max_s", 0.0020))
            self._dir = None
            try:
                from gpiozero import Device, Servo
                from gpiozero.pins.lgpio import LGPIOFactory

                Device.pin_factory = LGPIOFactory()
                pan_bcm = _i("pan_bcm", 24)
                tilt_bcm = _i("tilt_bcm", 19)
                frame = _f("period_s", 0.020)
                pan_lo, pan_hi = _f("pan_min_s", 0.0010), _f("pan_max_s", 0.0020)
                tilt_lo, tilt_hi = _f("tilt_min_s", 0.0010), _f("tilt_max_s", 0.0020)
                self._pan_servo = Servo(
                    pan_bcm,
                    initial_value=None,
                    min_pulse_width=pan_lo,
                    max_pulse_width=pan_hi,
                    frame_width=frame,
                )
                self._tilt_servo = Servo(
                    tilt_bcm,
                    initial_value=None,
                    min_pulse_width=tilt_lo,
                    max_pulse_width=tilt_hi,
                    frame_width=frame,
                )
                self._pan_servo.detach()
                self._tilt_servo.detach()
            except Exception as exc:
                self._error = str(exc)
                log.warning("gimbal gpiozero: %s", exc)
                self._close_servos()
                self._mode = "none"
                return
            self._mode = "lgpio"
            self._stop.clear()
            self._running = True
            self._thread = threading.Thread(target=self._loop, name="gimbal-pwm", daemon=True)
            self._thread.start()
            log.info("gimbal lgpio pan_bcm=%s tilt_bcm=%s", pan_bcm, tilt_bcm)

    def stop_pwm(self) -> None:
        self._stop.set()
        th = self._thread
        if th is not None:
            th.join(timeout=0.8)
        self._thread = None
        with self._lock:
            self._running = False
            self._dir = None
            self._close_servos()
            self._mode = "none"

    def move(self, direction: str) -> dict:
        direction = (direction or "stop").strip().lower()
        if direction not in DIRS:
            return {"ok": False, "error": "bad_dir", **self.status()}
        if not self.enabled():
            return {"ok": False, "error": "disabled", **self.status()}
        if not self._running:
            return {"ok": False, "error": self._error or "not_started", **self.status()}
        with self._lock:
            if direction == "stop":
                self._dir = None
            else:
                self._dir = direction
            self._last_cmd = time.monotonic()
            pan_us, tilt_us = int(self._pan * 1e6), int(self._tilt * 1e6)
        log.info("gimbal cmd=%s pan_us=%s tilt_us=%s", direction, pan_us, tilt_us)
        return {"ok": True, "dir": direction, **self.status()}

    def shutdown(self, *, home: bool, timeout_s: float = 2.5) -> None:
        if home and self._running:
            self.move("home")
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                with self._lock:
                    if self._dir != "home":
                        break
                time.sleep(0.04)
        self.stop_pwm()

    def _close_servos(self) -> None:
        for servo in (self._pan_servo, self._tilt_servo):
            if servo is None:
                continue
            try:
                servo.detach()
                servo.close()
            except Exception:
                pass
        self._pan_servo = None
        self._tilt_servo = None

    def _apply(self, axis: str | None, pan: float, tilt: float) -> None:
        pan_lo, pan_hi = _f("pan_min_s", 0.0010), _f("pan_max_s", 0.0020)
        tilt_lo, tilt_hi = _f("tilt_min_s", 0.0010), _f("tilt_max_s", 0.0020)
        pan_servo, tilt_servo = self._pan_servo, self._tilt_servo
        if axis == "pan" and pan_servo is not None:
            if tilt_servo is not None:
                tilt_servo.detach()
            pan_servo.value = pulse_to_value(pan, pan_lo, pan_hi)
        elif axis == "tilt" and tilt_servo is not None:
            if pan_servo is not None:
                pan_servo.detach()
            tilt_servo.value = pulse_to_value(tilt, tilt_lo, tilt_hi)
        else:
            if pan_servo is not None:
                pan_servo.detach()
            if tilt_servo is not None:
                tilt_servo.detach()

    def _loop(self) -> None:
        period = _f("period_s", 0.020)
        while not self._stop.is_set():
            self._tick_cmd()
            mid = _f("pulse_mid_s", 0.0015)
            step = _f("step_s", 0.000050)
            with self._lock:
                direction = self._dir
                pan, tilt = self._pan, self._tilt
            axis = active_axis(direction, pan, tilt, mid, step)
            try:
                self._apply(axis, pan, tilt)
            except Exception as exc:
                log.warning("gimbal apply: %s", exc)
                break
            self._stop.wait(period)

    def _tick_cmd(self) -> None:
        step = _f("step_s", 0.000050)
        pan_lo, pan_hi = _f("pan_min_s", 0.0010), _f("pan_max_s", 0.0020)
        tilt_lo, tilt_hi = _f("tilt_min_s", 0.0010), _f("tilt_max_s", 0.0020)
        mid = _f("pulse_mid_s", 0.0015)
        timeout = _f("cmd_timeout_s", 8.0)
        with self._lock:
            now = time.monotonic()
            direction = self._dir
            if direction in ("up", "down", "left", "right") and now - self._last_cmd > timeout:
                self._dir = None
                return
            if direction == "left":
                nxt = step_pulse(self._pan, step, pan_lo, pan_hi)
                if nxt == self._pan:
                    self._dir = None
                else:
                    self._pan = nxt
            elif direction == "right":
                nxt = step_pulse(self._pan, -step, pan_lo, pan_hi)
                if nxt == self._pan:
                    self._dir = None
                else:
                    self._pan = nxt
            elif direction == "up":
                nxt = step_pulse(self._tilt, -step, tilt_lo, tilt_hi)
                if nxt == self._tilt:
                    self._dir = None
                else:
                    self._tilt = nxt
            elif direction == "down":
                nxt = step_pulse(self._tilt, step, tilt_lo, tilt_hi)
                if nxt == self._tilt:
                    self._dir = None
                else:
                    self._tilt = nxt
            elif direction == "home":
                pan_mid = clamp_pulse(mid, pan_lo, pan_hi)
                tilt_mid = clamp_pulse(mid, tilt_lo, tilt_hi)
                if abs(self._pan - pan_mid) > step:
                    delta = step if self._pan < pan_mid else -step
                    self._pan = step_pulse(self._pan, delta, pan_lo, pan_hi)
                elif abs(self._tilt - tilt_mid) > step:
                    delta = step if self._tilt < tilt_mid else -step
                    self._tilt = step_pulse(self._tilt, delta, tilt_lo, tilt_hi)
                else:
                    self._dir = None


_gimbal = Gimbal()


def start() -> None:
    _gimbal.start()


def stop_pwm() -> None:
    _gimbal.stop_pwm()


def shutdown(*, home: bool, timeout_s: float = 2.5) -> None:
    _gimbal.shutdown(home=home, timeout_s=timeout_s)


def move(direction: str) -> dict:
    return _gimbal.move(direction)


def status() -> dict:
    return _gimbal.status()
