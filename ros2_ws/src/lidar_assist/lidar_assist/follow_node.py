# -*- coding: utf-8 -*-
"""Keep front distance from /scan. Publishes /cmd_vel_awake when enabled.

Enable: ros2 topic pub --once /robot/follow_enable std_msgs/Bool '{data: true}'
Requires Safety mode AWAKE (REMOTE teleop does not use this path).
Does not open serial. Obstacle stop remains in safety_manager.
"""

from __future__ import annotations

import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String

# reuse same geometry helper without importing safety package at runtime path issues
def _front_min(ranges, angle_min, angle_increment, front_deg, range_min, range_max):
    if not ranges or angle_increment == 0.0:
        return None
    half = math.radians(max(1.0, front_deg))
    best = None
    for i, raw in enumerate(ranges):
        r = float(raw)
        if not math.isfinite(r) or r < range_min or r > range_max:
            continue
        ang = angle_min + i * angle_increment
        ang = (ang + math.pi) % (2.0 * math.pi) - math.pi
        if abs(ang) > half:
            continue
        if best is None or r < best:
            best = r
    return best


class FollowNode(Node):
    def __init__(self) -> None:
        super().__init__('lidar_follow')
        self.declare_parameter('enabled', False)
        self.declare_parameter('target_m', 0.80)
        self.declare_parameter('band_m', 0.12)
        self.declare_parameter('vx_max', 0.12)
        self.declare_parameter('front_deg', 40.0)
        self.declare_parameter('rate_hz', 10.0)
        self.declare_parameter('stale_s', 0.6)

        self._enabled = bool(self.get_parameter('enabled').value)
        self._target = float(self.get_parameter('target_m').value)
        self._band = float(self.get_parameter('band_m').value)
        self._vx_max = float(self.get_parameter('vx_max').value)
        self._front_deg = float(self.get_parameter('front_deg').value)
        self._stale_s = float(self.get_parameter('stale_s').value)

        self._front: float | None = None
        self._scan_t = 0.0
        self._mode = 'IDLE'

        self.create_subscription(LaserScan, '/scan', self._on_scan, qos_profile_sensor_data)
        self.create_subscription(Bool, '/robot/follow_enable', self._on_enable, 10)
        self.create_subscription(String, '/robot/mode', self._on_mode, 10)
        self.pub = self.create_publisher(Twist, '/cmd_vel_awake', 10)
        rate = float(self.get_parameter('rate_hz').value)
        self.create_timer(1.0 / max(rate, 1.0), self._tick)
        self.get_logger().info(
            f'follow node up enabled={self._enabled} target_m={self._target} -> /cmd_vel_awake'
        )

    def _on_enable(self, msg: Bool) -> None:
        self._enabled = bool(msg.data)
        self.get_logger().info(f'follow_enable={self._enabled}')
        if not self._enabled:
            self.pub.publish(Twist())

    def _on_mode(self, msg: String) -> None:
        self._mode = (msg.data or 'IDLE').strip().upper()

    def _on_scan(self, msg: LaserScan) -> None:
        self._front = _front_min(
            msg.ranges,
            float(msg.angle_min),
            float(msg.angle_increment),
            self._front_deg,
            float(msg.range_min),
            float(msg.range_max),
        )
        self._scan_t = time.monotonic()

    def _tick(self) -> None:
        # Disabled must NOT publish: this topic is shared with Command Bus AWAKE drive.
        # Spamming zeros here cancels voice/follow-ready twists (REMOTE uses /cmd_vel_remote).
        if not self._enabled or self._mode != 'AWAKE':
            return
        out = Twist()
        fresh = (time.monotonic() - self._scan_t) <= self._stale_s
        if not fresh or self._front is None:
            self.pub.publish(out)
            return
        err = self._front - self._target
        if abs(err) <= self._band:
            vx = 0.0
        elif err > 0:
            # too far → forward
            vx = min(self._vx_max, 0.4 * err)
        else:
            # too close → stop (safety hard-stop handles closer); slight reverse optional
            vx = 0.0
        out.linear.x = float(vx)
        self.pub.publish(out)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FollowNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub.publish(Twist())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
