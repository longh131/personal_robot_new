# -*- coding: utf-8 -*-
"""IDLE-only low battery alarm. No motors, no REMOTE."""

from __future__ import annotations

import logging
import time

from awake.tools import read_battery
from runtime.machine import Mode
from settings import load_robot, robot_get

log = logging.getLogger("awake.battery")
POLL_S = 5.0


def _threshold(robot: dict) -> int:
    try:
        value = int(robot_get("low_battery_pct", default=10, robot=robot))
    except (TypeError, ValueError):
        value = 10
    return max(1, min(value, 99))


class BatteryWatch:
    def __init__(self, machine, cues) -> None:
        self.machine = machine
        self.cues = cues
        self._next = 0.0
        self._on = False

    def tick(self) -> None:
        now = time.monotonic()
        if now < self._next:
            if getattr(self.machine, "mode", None) != Mode.IDLE and self._on:
                self._set(False)
            return
        self._next = now + POLL_S
        if getattr(self.machine, "mode", None) != Mode.IDLE:
            self._set(False)
            return
        robot = load_robot()
        thresh = _threshold(robot)
        try:
            pct, state = read_battery()
        except Exception as exc:
            log.warning("battery watch read failed: %s", exc)
            self._set(False)
            return
        low = pct < thresh
        if low and not self._on:
            log.warning("idle low battery pct=%s thresh=%s state=%s", pct, thresh, state)
        if (not low) and self._on:
            log.info("idle battery recovered pct=%s thresh=%s", pct, thresh)
        self._set(low)

    def _set(self, on: bool) -> None:
        self._on = on
        setter = getattr(self.cues, "set_low_battery", None)
        if callable(setter):
            setter(on)

    def close(self) -> None:
        self._set(False)
