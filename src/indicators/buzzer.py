# -*- coding: utf-8 -*-
"""BCM12 passive buzzer, software PWM. GPIO failure is non-fatal."""

from __future__ import annotations

import threading
import time

from .gpio_line import GpioLine

BUZZ_BCM = 12
FREQ_HZ = 2000.0


class Buzzer:
    def __init__(self, enabled: bool = True) -> None:
        self._line: GpioLine | None = None
        self._lock = threading.Lock()
        self._busy = False
        self._alarm = threading.Event()
        self._alarm_thread: threading.Thread | None = None
        if enabled:
            try:
                self._line = GpioLine(BUZZ_BCM, b"pr-buzz")
            except OSError:
                self._line = None

    def set_alarm(self, on: bool) -> None:
        """IDLE low-battery: keep sounding until cleared."""
        if self._line is None:
            return
        if on:
            if self._alarm.is_set():
                return
            self._alarm.set()
            self._alarm_thread = threading.Thread(target=self._alarm_run, name="buzz-alarm", daemon=True)
            self._alarm_thread.start()
            return
        self._alarm.clear()

    def beep_denied(self) -> None:
        """Three short beeps. Non-blocking."""
        if self._line is None:
            return
        with self._lock:
            if self._busy:
                return
            self._busy = True
        threading.Thread(target=self._denied_run, name="buzz-denied", daemon=True).start()

    def beep_chime(self) -> None:
        """Two short beeps for timer due. Non-blocking."""
        if self._line is None:
            return
        with self._lock:
            if self._busy:
                return
            self._busy = True
        threading.Thread(target=self._chime_run, name="buzz-chime", daemon=True).start()

    def _tone(self, seconds: float) -> None:
        line = self._line
        if line is None:
            return
        half = 0.5 / FREQ_HZ
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            line.set(True)
            time.sleep(half)
            line.set(False)
            time.sleep(half)

    def _alarm_run(self) -> None:
        try:
            while self._alarm.is_set() and self._line is not None:
                self._tone(0.2)
                if not self._alarm.is_set():
                    break
                time.sleep(0.08)
        finally:
            if self._line is not None:
                try:
                    self._line.set(False)
                except OSError:
                    pass

    def _denied_run(self) -> None:
        try:
            for i in range(3):
                self._tone(0.08)
                if i < 2:
                    time.sleep(0.08)
        finally:
            if self._line is not None:
                try:
                    self._line.set(False)
                except OSError:
                    pass
            with self._lock:
                self._busy = False

    def _chime_run(self) -> None:
        try:
            for i in range(2):
                self._tone(0.10)
                if i < 1:
                    time.sleep(0.10)
        finally:
            if self._line is not None:
                try:
                    self._line.set(False)
                except OSError:
                    pass
            with self._lock:
                self._busy = False

    def close(self) -> None:
        self._alarm.clear()
        if self._alarm_thread is not None:
            self._alarm_thread.join(timeout=0.6)
            self._alarm_thread = None
        if self._line is not None:
            self._line.close()
            self._line = None
