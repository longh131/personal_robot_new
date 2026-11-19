#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stdin: 'vx vy wz' or 'MODE REMOTE|IDLE|AWAKE'. Never opens serial. Never Twist."""

from __future__ import annotations

import json
import select
import sys
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

OBS_CACHE = Path("/opt/personal_robot/logs/remote_obstacle.json")


class SkillPub(Node):
    def __init__(self) -> None:
        super().__init__("remote_skill_pub")
        self.pub = self.create_publisher(String, "/robot/skill_cmd", 10)
        self.mode_pub = self.create_publisher(String, "/robot/mode_cmd", 10)
        self.create_subscription(String, "/robot/skill_result", self._on_result, 10)
        self.create_subscription(String, "/robot/mode", self._on_mode, 10)
        self.create_subscription(String, "/robot/obstacle_status", self._on_obs, 10)
        self._n = 0
        self.last_result: dict = {}
        self.last_mode = "IDLE"
        OBS_CACHE.parent.mkdir(parents=True, exist_ok=True)

    def _on_obs(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data or "{}")
            if not isinstance(payload, dict):
                return
            payload["ts"] = time.time()
            OBS_CACHE.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    def _on_result(self, msg: String) -> None:
        try:
            body = json.loads(msg.data or "{}")
            if isinstance(body, dict):
                self.last_result = body
        except json.JSONDecodeError:
            pass

    def _on_mode(self, msg: String) -> None:
        self.last_mode = (msg.data or "IDLE").strip().upper() or "IDLE"

    def set_mode(self, mode: str) -> None:
        m = String()
        m.data = mode.strip().upper()
        self.mode_pub.publish(m)
        # Safety may need a second tick to publish /robot/mode
        for _ in range(10):
            rclpy.spin_once(self, timeout_sec=0.05)
            if self.last_mode == m.data:
                break

    def apply(self, vx: float, vy: float, wz: float) -> None:
        self._n += 1
        msg = String()
        msg.data = json.dumps(
            {
                "command_id": f"r{time.monotonic_ns()}_{self._n}",
                "source": "remote",
                "skill_id": "drive",
                "vx": vx,
                "vy": vy,
                "wz": wz,
            },
            separators=(",", ":"),
        )
        self.pub.publish(msg)


def main() -> int:
    rclpy.init()
    node = SkillPub()
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if not ready:
                continue
            line = sys.stdin.readline()
            if line == "":
                break
            parts = line.split()
            if not parts:
                continue
            if parts[0].upper() == "MODE" and len(parts) >= 2:
                try:
                    node.set_mode(parts[1])
                except Exception:
                    pass
                continue
            if len(parts) < 3:
                continue
            try:
                node.apply(float(parts[0]), float(parts[1]), float(parts[2]))
            except ValueError:
                continue
    finally:
        node.apply(0.0, 0.0, 0.0)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
