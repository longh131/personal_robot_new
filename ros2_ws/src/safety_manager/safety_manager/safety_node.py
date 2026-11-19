"""Safety 节点：唯一向 /cmd_vel_safe 发速度。不打开电机串口。"""

from __future__ import annotations

import json
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String

from .arbiter import SafetyArbiter, SRC_AWAKE, SRC_REMOTE
from .obstacle import apply_motion_stop, direction_mins

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
        self.declare_parameter('obstacle.enabled', True)
        self.declare_parameter('obstacle.stop_m', 0.45)
        self.declare_parameter('obstacle.hard_m', 0.30)
        self.declare_parameter('obstacle.front_deg', 50.0)
        self.declare_parameter('obstacle.ignore_below_m', 0.28)
        self.declare_parameter('obstacle.angle_offset_deg', 0.0)
        self.declare_parameter('obstacle.stale_s', 0.8)
        timeout = float(self.get_parameter('cmd_timeout').value)
        rate = float(self.get_parameter('rate_hz').value)
        self.arbiter = SafetyArbiter(timeout)

        self._obs_enabled = bool(self.get_parameter('obstacle.enabled').value)
        self._stop_m = float(self.get_parameter('obstacle.stop_m').value)
        self._hard_m = float(self.get_parameter('obstacle.hard_m').value)
        self._front_deg = float(self.get_parameter('obstacle.front_deg').value)
        self._ignore_below = float(self.get_parameter('obstacle.ignore_below_m').value)
        self._angle_offset = float(self.get_parameter('obstacle.angle_offset_deg').value)
        self._stale_s = float(self.get_parameter('obstacle.stale_s').value)
        self._mins: dict[str, float | None] = {
            "front": None, "rear": None, "left": None, "right": None,
        }
        self._scan_stamp = 0.0
        self._blocked = False

        self.create_subscription(Twist, '/cmd_vel_remote', self._on_remote, CMD_QOS)
        self.create_subscription(Twist, '/cmd_vel_awake', self._on_awake, CMD_QOS)
        self.create_subscription(String, '/robot/mode_cmd', self._on_mode_cmd, 10)
        self.create_subscription(Bool, '/robot/estop', self._on_estop, CMD_QOS)
        self.create_subscription(Bool, '/c30d/connected', self._on_connected, 10)
        if self._obs_enabled:
            self.create_subscription(LaserScan, '/scan', self._on_scan, qos_profile_sensor_data)

        self.pub_safe = self.create_publisher(Twist, '/cmd_vel_safe', CMD_QOS)
        self.pub_mode = self.create_publisher(String, '/robot/mode', 10)
        self.pub_estop = self.create_publisher(Bool, '/robot/estop', CMD_QOS)
        self.pub_fault = self.create_publisher(String, '/robot/fault', 10)
        self.pub_obs = self.create_publisher(Bool, '/robot/obstacle_stop', 10)
        self.pub_obs_status = self.create_publisher(String, '/robot/obstacle_status', 10)
        self._pub_estop_value: bool | None = None

        self.create_timer(1.0 / max(rate, 1.0), self._on_timer)
        self.get_logger().warn(
            'Safety: no hardware e-stop. Software latch is not industrial. '
            'Does not open C30D serial.'
        )
        if self._obs_enabled:
            self.get_logger().info(
                f'obstacle stop 4-way on /scan stop_m={self._stop_m} hard_m={self._hard_m} '
                f'sector_deg=±{self._front_deg} ignore_below_m={self._ignore_below} '
                f'offset_deg={self._angle_offset}'
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

    def _on_scan(self, msg: LaserScan) -> None:
        self._mins = direction_mins(
            msg.ranges,
            angle_min=float(msg.angle_min),
            angle_increment=float(msg.angle_increment),
            half_deg=self._front_deg,
            range_min=float(msg.range_min),
            range_max=float(msg.range_max),
            ignore_below_m=self._ignore_below,
            angle_offset_deg=self._angle_offset,
        )
        self._scan_stamp = time.monotonic()

    def _on_timer(self) -> None:
        kind, vx, vy, wz = self.arbiter.tick(time.monotonic())
        blocked = False
        fresh = bool(
            self._obs_enabled
            and self._scan_stamp > 0
            and (time.monotonic() - self._scan_stamp) <= self._stale_s
        )
        mins = self._mins if fresh else {
            "front": None, "rear": None, "left": None, "right": None,
        }
        if kind == 'stream' and self._obs_enabled:
            vx, vy, wz, blocked, why = apply_motion_stop(
                vx, vy, wz, mins, stop_m=self._stop_m, hard_m=self._hard_m,
            )
            if blocked and not self._blocked:
                self.get_logger().warn(
                    f'obstacle stop {why} stop_m={self._stop_m} hard_m={self._hard_m}'
                )
        self._blocked = blocked
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
        o = Bool()
        o.data = blocked
        self.pub_obs.publish(o)
        status = String()
        status.data = json.dumps(
            {
                "enabled": self._obs_enabled,
                "blocked": blocked,
                "fresh": fresh,
                "front": mins.get("front"),
                "rear": mins.get("rear"),
                "left": mins.get("left"),
                "right": mins.get("right"),
                "stop_m": self._stop_m,
                "hard_m": self._hard_m,
            },
            separators=(",", ":"),
        )
        self.pub_obs_status.publish(status)


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
