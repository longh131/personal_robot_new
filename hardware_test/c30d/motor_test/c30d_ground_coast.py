#!/usr/bin/env python3
"""着地短测：REMOTE 前进 ≤1.5s，停发，急停锁存。不是工业级急停。"""

from __future__ import annotations

import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String

QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
)


class GroundCoast(Node):
    def __init__(self) -> None:
        super().__init__('ground_coast')
        self.mode = ''
        self.status = ''
        self.connected: bool | None = None
        self.estop = False
        self.x = 0.0
        self.vx = 0.0
        self.create_subscription(String, '/robot/mode', self._mode, 10)
        self.create_subscription(String, '/c30d/status', self._status, 10)
        self.create_subscription(Bool, '/c30d/connected', self._conn, 10)
        self.create_subscription(Bool, '/robot/estop', self._estop, QOS)
        self.create_subscription(Odometry, '/odom', self._odom, 10)
        self.pub_mode = self.create_publisher(String, '/robot/mode_cmd', 10)
        self.pub_estop = self.create_publisher(Bool, '/robot/estop', QOS)
        self.pub_remote = self.create_publisher(Twist, '/cmd_vel_remote', QOS)

    def _mode(self, m: String) -> None:
        self.mode = m.data

    def _status(self, m: String) -> None:
        self.status = m.data

    def _conn(self, m: Bool) -> None:
        self.connected = bool(m.data)

    def _estop(self, m: Bool) -> None:
        self.estop = bool(m.data)

    def _odom(self, m: Odometry) -> None:
        self.x = m.pose.pose.position.x
        self.vx = m.twist.twist.linear.x

    def spin_s(self, sec: float) -> None:
        t0 = time.monotonic()
        while time.monotonic() - t0 < sec:
            rclpy.spin_once(self, timeout_sec=0.05)

    def wait_mode(self, want: str, sec: float = 4.0) -> bool:
        t0 = time.monotonic()
        while time.monotonic() - t0 < sec:
            rclpy.spin_once(self, timeout_sec=0.05)
            if self.mode == want:
                return True
        return False

    def mode_cmd(self, name: str) -> None:
        msg = String()
        msg.data = name
        for _ in range(8):
            self.pub_mode.publish(msg)
            rclpy.spin_once(self, timeout_sec=0.05)

    def set_estop(self, val: bool) -> None:
        msg = Bool()
        msg.data = val
        for _ in range(8):
            self.pub_estop.publish(msg)
            rclpy.spin_once(self, timeout_sec=0.05)

    def stream_remote(self, sec: float) -> str:
        tw = Twist()
        tw.linear.x = 0.4
        t0 = time.monotonic()
        last = ''
        while time.monotonic() - t0 < sec:
            self.pub_remote.publish(tw)
            rclpy.spin_once(self, timeout_sec=0.04)
            last = self.status
        return last


def fail(msg: str) -> int:
    print(f'FAIL {msg}')
    return 1


def main() -> int:
    print('GROUND TEST: max 1.5s forward. Cut motor power if it does not stop.')
    rclpy.init()
    n = GroundCoast()
    try:
        n.spin_s(1.5)
        if n.connected is not True:
            return fail(f'not connected {n.connected}')
        n.set_estop(False)
        n.mode_cmd('IDLE')
        n.spin_s(0.3)
        n.mode_cmd('REMOTE')
        if not n.wait_mode('REMOTE'):
            return fail(f'not REMOTE mode={n.mode}')
        x0 = n.x
        t_go = time.monotonic()
        st = n.stream_remote(1.5)
        t_stop_send = time.monotonic()
        print(f'GO status={st} mode={n.mode} x={n.x:.4f} vx={n.vx:.4f}')
        if 'STREAM_CMD_VEL_SAFE' not in st:
            return fail(f'no stream {st}')
        n.spin_s(1.2)
        t_halt = time.monotonic()
        print(
            f'STOP_SEND dt={t_stop_send - t_go:.2f}s halt_wait={t_halt - t_stop_send:.2f}s '
            f'status={n.status} x={n.x:.4f} dx={n.x - x0:.4f} vx={n.vx:.4f}'
        )
        n.set_estop(True)
        n.spin_s(0.4)
        n.mode_cmd('REMOTE')
        n.spin_s(0.3)
        st = n.stream_remote(0.8)
        print(f'ESTOP status={st} mode={n.mode} estop={n.estop}')
        if 'STREAM_CMD_VEL_SAFE' in st or n.mode == 'REMOTE':
            return fail('moved or REMOTE while estop')
        n.set_estop(False)
        n.spin_s(0.3)
        st = n.stream_remote(0.6)
        print(f'CLEAR_NO_GRANT status={st} mode={n.mode}')
        if 'STREAM_CMD_VEL_SAFE' in st:
            return fail('stream after clear without REMOTE')
        n.mode_cmd('IDLE')
        n.wait_mode('IDLE')
        print('PASS software ground sequence; confirm visual walk/stop/coast')
        return 0
    finally:
        n.mode_cmd('IDLE')
        n.set_estop(False)
        n.spin_s(0.2)
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
