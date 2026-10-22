# -*- coding: utf-8 -*-
"""MG90S dual-axis gimbal. Hardware not wired; UI only."""

from __future__ import annotations

import logging

log = logging.getLogger("remote.gimbal")


def move(direction: str) -> dict:
    _ = direction
    log.info("gimbal stub dir=%s (not connected)", direction)
    return {
        "ok": False,
        "error": "not_connected",
        "model": "MG90S",
        "hint": "界面已预留，舵机接入后再做驱动",
    }
