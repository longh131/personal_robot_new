# -*- coding: utf-8 -*-
"""Mode arbiter. Not AWAKE, not REMOTE."""

from __future__ import annotations

from .events import Event


class Mode:
    IDLE = "IDLE"
    AWAKE = "AWAKE"
    REMOTE = "REMOTE"
    FAULT = "FAULT"


_FROM_IDLE = {
    Event.WAKE: Mode.AWAKE,
    Event.REMOTE_LOGIN: Mode.REMOTE,
    Event.FAULT: Mode.FAULT,
}

_TO_IDLE = {Event.EXIT_TO_IDLE}


class Machine:
    def __init__(self) -> None:
        self.mode = Mode.IDLE
        self.estop = False

    def apply(self, event: Event) -> str:
        if event is Event.ESTOP:
            self.estop = True
            return self.mode
        if event is Event.CLEAR_ESTOP:
            self.estop = False
            return self.mode
        if event is Event.FAULT:
            self.mode = Mode.FAULT
            return self.mode
        if self.mode == Mode.FAULT:
            if event in _TO_IDLE:
                self.mode = Mode.IDLE
            return self.mode
        if self.mode == Mode.IDLE:
            nxt = _FROM_IDLE.get(event)
            if nxt:
                self.mode = nxt
            return self.mode
        # AWAKE / REMOTE：不能互切，只能回 IDLE
        if event in _TO_IDLE:
            self.mode = Mode.IDLE
        return self.mode
