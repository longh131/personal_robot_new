#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stdin: 'vx vy wz' or 'MODE AWAKE|IDLE'. source=awake. Never opens serial."""

from __future__ import annotations

import json
import select
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class AwakeSkillPub(Node):
    def __init__(self) -> None:
        super().__init__("awake_skill_pub")
        self.pub = self.create_publisher(String, "/robot/skill_cmd", 10)
        self.mode_pub = self.create_publisher(String, "/robot/mode_cmd", 10)
        self.create_subscription(String, "/robot/mode", self._on_mode, 10)
        self._n = 0
        self.last_mode = "IDLE"

    def _on_mode(self, msg: String) -> None:
        self.last_mode = (msg.data or "IDLE").strip().upper() or "IDLE"

    def set_mode(self, mode: str) -> None:
        m = String()
        m.data = mode.strip().upper()
        self.mode_pub.publish(m)
        for _ in range(10):
            rclpy.spin_once(self, timeout_sec=0.05)
            if self.last_mode == m.data:
                break

    def apply(self, vx: float, vy: float, wz: float) -> None:
        self._n += 1
        msg = String()
        msg.data = json.dumps(
            {
                "command_id": f"ah{time.monotonic_ns()}_{self._n}",
                "source": "awake",
                "skill_id": "drive",
                "vx": float(vx),
                "vy": float(vy),
                "wz": float(wz),
            },
            separators=(",", ":"),
        )
        self.pub.publish(msg)


def main() -> int:
    rclpy.init()
    node = AwakeSkillPub()
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
        try:
            node.apply(0.0, 0.0, 0.0)
        except Exception:
            pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
