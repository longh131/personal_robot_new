#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stdin: vx vy wz. Publish drive skill JSON. Never opens serial. Never Twist."""

from __future__ import annotations

import json
import select
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SkillPub(Node):
    def __init__(self) -> None:
        super().__init__("remote_skill_pub")
        self.pub = self.create_publisher(String, "/robot/skill_cmd", 10)
        self._n = 0

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
