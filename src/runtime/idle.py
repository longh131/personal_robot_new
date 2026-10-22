# -*- coding: utf-8 -*-
"""Main loop: apply ingress events. Do not import awake/remote."""

from __future__ import annotations

import logging
import queue
from collections.abc import Callable

from .events import Event
from .machine import Machine

log = logging.getLogger("idle")


def run(
    machine: Machine,
    events: queue.Queue[Event],
    *,
    on_tick: Callable[[], None] | None = None,
    on_mode: Callable[[str, str], None] | None = None,
    once: bool = False,
    period_s: float = 0.05,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    log.info("mode=%s waiting wake or remote", machine.mode)
    while True:
        if should_stop and should_stop():
            return
        try:
            ev = events.get(timeout=period_s)
        except queue.Empty:
            if on_tick:
                on_tick()
            if once:
                return
            continue
        prev = machine.mode
        machine.apply(ev)
        log.info("event=%s %s -> %s estop=%s", ev.name, prev, machine.mode, machine.estop)
        if on_mode and prev != machine.mode:
            on_mode(prev, machine.mode)
        if once:
            return
