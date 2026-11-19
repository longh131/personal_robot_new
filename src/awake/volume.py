# -*- coding: utf-8 -*-
"""PipeWire sink volume. AWAKE only."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger("awake.volume")


def _wpctl(*args: str) -> str:
    proc = subprocess.run(
        ["wpctl", *args],
        capture_output=True,
        text=True,
        timeout=3,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "音量调节失败")
    return proc.stdout.strip()


def louder() -> str:
    _wpctl("set-mute", "@DEFAULT_AUDIO_SINK@", "0")
    _wpctl("set-volume", "@DEFAULT_AUDIO_SINK@", "0.1+")
    log.info("volume up")
    return "音量调大了"


def quieter() -> str:
    _wpctl("set-volume", "@DEFAULT_AUDIO_SINK@", "0.1-")
    log.info("volume down")
    return "音量调小了"


def mute() -> str:
    _wpctl("set-mute", "@DEFAULT_AUDIO_SINK@", "1")
    log.info("volume mute")
    return "已静音"


def unmute() -> str:
    _wpctl("set-mute", "@DEFAULT_AUDIO_SINK@", "0")
    log.info("volume unmute")
    return "已取消静音"
