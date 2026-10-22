# -*- coding: utf-8 -*-
"""Shared LED/buzzer for AWAKE and REMOTE. Not a robot mode."""

from __future__ import annotations

from .buzzer import Buzzer
from .led import LedBreath


class Cues:
    def __init__(self, *, led: bool = True, buzzer: bool = True) -> None:
        self.led = LedBreath(enabled=led)
        self.buzzer = Buzzer(enabled=buzzer)

    def tick(self, mode: str) -> None:
        if mode != "IDLE":
            self.set_low_battery(False)
        self.led.tick(mode)

    def set_low_battery(self, on: bool) -> None:
        self.led.alarm = bool(on) and self.led.mode == "IDLE"
        self.buzzer.set_alarm(bool(on) and self.led.mode == "IDLE")

    def set_speaking(self, on: bool) -> None:
        """Call around TTS playback later: True before play, False after."""
        self.led.set_speaking(on)

    def denied(self) -> None:
        """Wake rejected (REMOTE / FAULT / estop)."""
        self.led.denied()
        self.buzzer.beep_denied()

    def close(self) -> None:
        self.led.close()
        self.buzzer.close()
