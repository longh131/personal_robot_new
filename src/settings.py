# -*- coding: utf-8 -*-
"""Load identity.json and robot.yaml. Secrets stay in cloud.env."""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

CONFIG = Path("/opt/personal_robot/config")
IDENTITY_PATH = CONFIG / "identity.json"
ROBOT_PATH = CONFIG / "robot.yaml"
DEFAULT_TIMEOUT_S = 30.0
MIN_TIMEOUT_S = 5.0
MAX_TIMEOUT_S = 86400.0
DEFAULT_AUDIO = "plughw:Y1076,0"


def load_identity() -> dict:
    return json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))


def load_robot() -> dict:
    data = yaml.safe_load(ROBOT_PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def robot_get(*keys, default=None, robot: dict | None = None):
    cur: object = load_robot() if robot is None else robot
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def load_idle_timeout_s(default: float = DEFAULT_TIMEOUT_S) -> float:
    try:
        value = float(robot_get("idle_timeout_s", default=default))
    except (TypeError, ValueError):
        value = default
    return max(MIN_TIMEOUT_S, min(value, MAX_TIMEOUT_S))


def audio_device(kind: str) -> str:
    if kind == "capture":
        env = os.environ.get("PERSONAL_ROBOT_MIC")
        if env:
            return env
        return str(robot_get("audio", "capture", default=DEFAULT_AUDIO) or DEFAULT_AUDIO)
    return str(robot_get("audio", "playback", default=DEFAULT_AUDIO) or DEFAULT_AUDIO)
