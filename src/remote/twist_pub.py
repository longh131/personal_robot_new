#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stdin: vx vy wz per line. Publish /cmd_vel_remote. Never opens serial."""

from __future__ import annotations

import select
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
)


class TwistPub(Node):
    def __init__(self) -> None:
        super().__init__("remote_twist_pub")
        self.pub = self.create_publisher(Twist, "/cmd_vel_remote", QOS)
        self.vx = 0.0
        self.vy = 0.0
        self.wz = 0.0
        self.last = time.monotonic()
        self.create_timer(0.05, self._tick)

    def apply(self, vx: float, vy: float, wz: float) -> None:
        self.vx, self.vy, self.wz = vx, vy, wz
        self.last = time.monotonic()

    def _tick(self) -> None:
        if time.monotonic() - self.last > 1.0:
            self.vx = self.vy = self.wz = 0.0
        msg = Twist()
        msg.linear.x = self.vx
        msg.linear.y = self.vy
        msg.angular.z = self.wz
        self.pub.publish(msg)


def main() -> int:
    rclpy.init()
    node = TwistPub()
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
        node._tick()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
