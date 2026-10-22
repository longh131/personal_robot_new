#!/usr/bin/env python3
"""Phase 4B 离地：REMOTE 短时运动、急停锁存、AWAKE 拒遥控。最多约 2s 非零。"""

from __future__ import annotations

import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String

QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
)


class Phase4B(Node):
    def __init__(self) -> None:
        super().__init__('phase4b')
        self.mode = ''
        self.status = ''
        self.connected: bool | None = None
        self.estop = False
        self.create_subscription(String, '/robot/mode', self._mode, 10)
        self.create_subscription(String, '/c30d/status', self._status, 10)
        self.create_subscription(Bool, '/c30d/connected', self._conn, 10)
        self.create_subscription(Bool, '/robot/estop', self._estop, QOS)
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

    def spin_s(self, sec: float) -> None:
        t0 = time.monotonic()
        while time.monotonic() - t0 < sec:
            rclpy.spin_once(self, timeout_sec=0.05)

    def wait_mode(self, want: str, sec: float = 3.0) -> bool:
        t0 = time.monotonic()
        while time.monotonic() - t0 < sec:
            rclpy.spin_once(self, timeout_sec=0.05)
            if self.mode == want:
                return True
        return False

    def mode_cmd(self, name: str) -> None:
        msg = String()
        msg.data = name
        for _ in range(5):
            self.pub_mode.publish(msg)
            rclpy.spin_once(self, timeout_sec=0.05)

    def set_estop(self, val: bool) -> None:
        msg = Bool()
        msg.data = val
        for _ in range(5):
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
    print('WARNING: wheels-off 4B. Cut motor power if wheels keep moving.')
    rclpy.init()
    n = Phase4B()
    try:
        n.spin_s(1.5)
        if n.connected is not True:
            return fail(f'not connected connected={n.connected}')
        n.mode_cmd('IDLE')
        n.set_estop(False)
        n.spin_s(0.4)

        n.mode_cmd('REMOTE')
        if not n.wait_mode('REMOTE'):
            return fail(f'not REMOTE mode={n.mode}')
        st = n.stream_remote(1.5)
        print(f'REMOTE_STREAM status={st}')
        if 'STREAM_CMD_VEL_SAFE' not in st:
            return fail(f'expected stream got {st}')
        n.spin_s(0.8)
        print(f'REMOTE_AFTER_STOP status={n.status}')
        if 'STREAM_CMD_VEL_SAFE' in n.status:
            return fail('still streaming after stop send')

        n.set_estop(True)
        n.spin_s(0.4)
        if not n.estop:
            return fail('estop not latched')
        n.mode_cmd('REMOTE')
        n.spin_s(0.3)
        st = n.stream_remote(1.0)
        print(f'ESTOP_STREAM status={st} mode={n.mode}')
        if 'STREAM_CMD_VEL_SAFE' in st:
            return fail('streamed while estop')
        if n.mode == 'REMOTE':
            return fail('REMOTE granted while estop')

        n.set_estop(False)
        n.spin_s(0.4)
        st = n.stream_remote(0.8)
        print(f'AFTER_CLEAR_NO_GRANT status={st} mode={n.mode}')
        if 'STREAM_CMD_VEL_SAFE' in st:
            return fail('streamed after estop clear without REMOTE')

        n.mode_cmd('AWAKE')
        if not n.wait_mode('AWAKE'):
            return fail(f'not AWAKE mode={n.mode}')
        st = n.stream_remote(1.0)
        print(f'AWAKE_REMOTE status={st}')
        if 'STREAM_CMD_VEL_SAFE' in st:
            return fail('remote streamed in AWAKE')

        n.mode_cmd('IDLE')
        n.wait_mode('IDLE')
        print('PASS 4B software checks (confirm wheels: move then stop; estop no move)')
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
