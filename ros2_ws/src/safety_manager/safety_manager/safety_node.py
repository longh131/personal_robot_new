"""Safety 节点：唯一向 /cmd_vel_safe 发速度。不打开电机串口。"""

from __future__ import annotations

import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String

from .arbiter import SafetyArbiter, SRC_AWAKE, SRC_REMOTE

CMD_QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
)


class SafetyNode(Node):
    def __init__(self) -> None:
        super().__init__('safety_manager')
        self.declare_parameter('cmd_timeout', 0.30)
        self.declare_parameter('rate_hz', 20.0)
        timeout = float(self.get_parameter('cmd_timeout').value)
        rate = float(self.get_parameter('rate_hz').value)
        self.arbiter = SafetyArbiter(timeout)

        self.create_subscription(Twist, '/cmd_vel_remote', self._on_remote, CMD_QOS)
        self.create_subscription(Twist, '/cmd_vel_awake', self._on_awake, CMD_QOS)
        self.create_subscription(String, '/robot/mode_cmd', self._on_mode_cmd, 10)
        self.create_subscription(Bool, '/robot/estop', self._on_estop, CMD_QOS)
        self.create_subscription(Bool, '/c30d/connected', self._on_connected, 10)

        self.pub_safe = self.create_publisher(Twist, '/cmd_vel_safe', CMD_QOS)
        self.pub_mode = self.create_publisher(String, '/robot/mode', 10)
        self.pub_estop = self.create_publisher(Bool, '/robot/estop', CMD_QOS)
        self.pub_fault = self.create_publisher(String, '/robot/fault', 10)
        self._pub_estop_value: bool | None = None

        self.create_timer(1.0 / max(rate, 1.0), self._on_timer)
        self.get_logger().warn(
            'Safety: no hardware e-stop. Software latch is not industrial. '
            'Does not open C30D serial.'
        )

    def _on_remote(self, msg: Twist) -> None:
        self.arbiter.on_twist(
            SRC_REMOTE, msg.linear.x, msg.linear.y, msg.angular.z, time.monotonic(),
        )

    def _on_awake(self, msg: Twist) -> None:
        self.arbiter.on_twist(
            SRC_AWAKE, msg.linear.x, msg.linear.y, msg.angular.z, time.monotonic(),
        )

    def _on_mode_cmd(self, msg: String) -> None:
        reason = self.arbiter.request_mode(msg.data)
        if reason:
            self.get_logger().warn(f'mode_cmd {msg.data!r} rejected: {reason}')

    def _on_estop(self, msg: Bool) -> None:
        self.arbiter.set_estop(bool(msg.data))

    def _on_connected(self, msg: Bool) -> None:
        self.arbiter.on_serial_connected(bool(msg.data))

    def _on_timer(self) -> None:
        kind, vx, vy, wz = self.arbiter.tick(time.monotonic())
        out = Twist()
        if kind == 'stream':
            out.linear.x = vx
            out.linear.y = vy
            out.angular.z = wz
        self.pub_safe.publish(out)
        m = String()
        m.data = self.arbiter.mode
        self.pub_mode.publish(m)
        if self._pub_estop_value is None or self._pub_estop_value != self.arbiter.estop:
            e = Bool()
            e.data = self.arbiter.estop
            self.pub_estop.publish(e)
            self._pub_estop_value = self.arbiter.estop
        f = String()
        f.data = self.arbiter.fault
        self.pub_fault.publish(f)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SafetyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
