# -*- coding: utf-8 -*-
"""sysfs hardware PWM (RP1). Falls back raises if chip not exported."""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger("remote.hw_pwm")


class HwPwm:
    def __init__(self, chip: int, channel: int) -> None:
        self.chip = int(chip)
        self.channel = int(channel)
        root = Path(f"/sys/class/pwm/pwmchip{self.chip}")
        if not root.is_dir():
            raise FileNotFoundError(f"missing {root}")
        node = root / f"pwm{self.channel}"
        if not node.is_dir():
            export = root / "export"
            try:
                export.write_text(str(self.channel), encoding="ascii")
            except OSError as exc:
                raise OSError(f"pwmchip{self.chip} export {self.channel}: {exc}") from exc
            node = root / f"pwm{self.channel}"
            if not node.is_dir():
                raise FileNotFoundError(f"export failed {node}")
        self._node = node
        self._enabled = False
        self.disable()

    def set_pulse(self, width_s: float, period_s: float = 0.020) -> None:
        period_ns = max(1, int(round(period_s * 1e9)))
        duty_ns = max(0, min(period_ns, int(round(width_s * 1e9))))
        # duty must be set after period; disable briefly if shrinking period
        en = self._node / "enable"
        if self._enabled:
            en.write_text("0", encoding="ascii")
            self._enabled = False
        (self._node / "period").write_text(str(period_ns), encoding="ascii")
        (self._node / "duty_cycle").write_text(str(duty_ns), encoding="ascii")
        en.write_text("1", encoding="ascii")
        self._enabled = True

    def disable(self) -> None:
        try:
            (self._node / "enable").write_text("0", encoding="ascii")
            (self._node / "duty_cycle").write_text("0", encoding="ascii")
        except OSError as exc:
            log.warning("pwm disable: %s", exc)
        self._enabled = False

    def close(self) -> None:
        self.disable()
        try:
            Path(f"/sys/class/pwm/pwmchip{self.chip}/unexport").write_text(
                str(self.channel), encoding="ascii"
            )
        except OSError:
            pass
