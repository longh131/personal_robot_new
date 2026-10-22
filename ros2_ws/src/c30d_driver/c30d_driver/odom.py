"""轮速积分。不要求导航级精度。"""

from __future__ import annotations

import math


class OdomIntegrator:
    def __init__(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.wz = 0.0
        self._last: float | None = None

    def update(self, vx: float, vy: float, wz: float, now: float) -> None:
        self.vx, self.vy, self.wz = vx, vy, wz
        if self._last is None:
            self._last = now
            return
        dt = now - self._last
        self._last = now
        if dt <= 0.0 or dt > 0.5:
            return
        c = math.cos(self.th)
        s = math.sin(self.th)
        self.x += (vx * c - vy * s) * dt
        self.y += (vx * s + vy * c) * dt
        self.th += wz * dt

    def yaw_quat(self) -> tuple[float, float, float, float]:
        h = self.th * 0.5
        return 0.0, 0.0, math.sin(h), math.cos(h)
