# -*- coding: utf-8 -*-
"""BCM16 LED. Worker thread PWM so modes are not all fast blinks."""

from __future__ import annotations

import math
import threading
import time

from .gpio_line import GpioLine

LED_BCM = 16
DENIED_S = 1.2
PWM_S = 0.01


class LedBreath:
    def __init__(self, enabled: bool = True) -> None:
        self._line: GpioLine | None = None
        self.mode = "IDLE"
        self.speaking = False
        self.alarm = False
        self._denied_until = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if enabled:
            try:
                self._line = GpioLine(LED_BCM, b"pr-led")
            except OSError:
                self._line = None
        if self._line is not None:
            self._thread = threading.Thread(target=self._run, name="led-pwm", daemon=True)
            self._thread.start()

    def set_speaking(self, on: bool) -> None:
        self.speaking = bool(on)

    def denied(self) -> None:
        self._denied_until = time.monotonic() + DENIED_S

    def tick(self, mode: str = "IDLE") -> None:
        self.mode = mode
        if mode != "IDLE":
            self.alarm = False

    def _duty(self, now: float) -> float:
        if now < self._denied_until:
            return 1.0 if int(now * 6) % 2 == 0 else 0.0
        if self.speaking:
            return 0.08 + 0.84 * (0.5 + 0.5 * math.sin(2 * math.pi * now / 1.2))
        if self.alarm and self.mode == "IDLE":
            return 1.0 if int(now * 8) % 2 == 0 else 0.0
        if self.mode == "REMOTE":
            return 1.0 if int(now * 5) % 2 == 0 else 0.0
        if self.mode == "AWAKE":
            return 1.0
        return 0.06 + 0.88 * (0.5 + 0.5 * math.sin(2 * math.pi * now / 3.0))

    def _run(self) -> None:
        line = self._line
        if line is None:
            return
        while not self._stop.is_set():
            duty = min(1.0, max(0.0, self._duty(time.monotonic())))
            on_t = PWM_S * duty
            off_t = PWM_S - on_t
            if on_t > 0:
                line.set(True)
                time.sleep(on_t)
            if off_t > 0:
                line.set(False)
                time.sleep(off_t)

    def close(self) -> None:
        self.speaking = False
        self.alarm = False
        self._denied_until = 0.0
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=0.5)
            self._thread = None
        if self._line is not None:
            self._line.close()
            self._line = None
