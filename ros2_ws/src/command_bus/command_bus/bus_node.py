"""ROS node: skill JSON in. drive → /cmd_vel_remote or /cmd_vel_awake. Never opens serial."""

from __future__ import annotations

import json
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String

from command_bus.validator import AWAKE, REMOTE, SKILL_DRIVE, CommandBus

CMD_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class BusNode(Node):
    def __init__(self) -> None:
        super().__init__('command_bus')
        self.declare_parameter('motion_enabled', False)
        self.declare_parameter('vx_max', 0.15)
        self.declare_parameter('vy_max', 0.15)
        self.declare_parameter('wz_max', 0.40)
        self.declare_parameter('drive_timeout', 1.0)
        motion = bool(self.get_parameter('motion_enabled').value)
        self.vx_max = abs(float(self.get_parameter('vx_max').value))
        self.vy_max = abs(float(self.get_parameter('vy_max').value))
        self.wz_max = abs(float(self.get_parameter('wz_max').value))
        self.drive_timeout = max(0.3, float(self.get_parameter('drive_timeout').value))
        self.bus = CommandBus(motion_enabled=motion)
        self._last_drive = time.monotonic()
        self.create_subscription(String, '/robot/mode', self._on_mode, 10)
        self.create_subscription(Bool, '/robot/estop', self._on_estop, CMD_QOS)
        self.create_subscription(String, '/robot/skill_cmd', self._on_skill, 10)
        self.create_subscription(String, '/robot/skill_cancel', self._on_cancel, 10)
        self.pub_result = self.create_publisher(String, '/robot/skill_result', 10)
        self.pub_remote = self.create_publisher(Twist, '/cmd_vel_remote', CMD_QOS)
        self.pub_awake = self.create_publisher(Twist, '/cmd_vel_awake', CMD_QOS)
        self.create_timer(0.05, self._on_timer)
        self.get_logger().info(
            f'command_bus up motion_enabled={motion} '
            f'drive REMOTE→/cmd_vel_remote AWAKE→/cmd_vel_awake (no serial)'
        )

    def _on_mode(self, msg: String) -> None:
        self.bus.set_mode(msg.data)

    def _on_estop(self, msg: Bool) -> None:
        self.bus.set_estop(msg.data)
        if msg.data:
            self.bus.zero_drive()

    def _emit(self, command_id: str, decision) -> None:
        out = String()
        out.data = json.dumps(
            {
                'command_id': command_id,
                'accepted': decision.accepted,
                'reason': decision.reason,
                'executed': decision.executed,
            },
            separators=(',', ':'),
        )
        self.pub_result.publish(out)

    def _on_skill(self, msg: String) -> None:
        try:
            body = json.loads(msg.data)
        except json.JSONDecodeError:
            self._emit('', type('D', (), {'accepted': False, 'reason': 'bad_json', 'executed': ''})())
            return
        cid = str(body.get('command_id', ''))
        skill = str(body.get('skill_id', ''))
        d = self.bus.dispatch(
            command_id=cid,
            source=str(body.get('source', '')),
            skill_id=skill,
            vx=float(body.get('vx') or 0),
            vy=float(body.get('vy') or 0),
            wz=float(body.get('wz') or 0),
        )
        if d.accepted and skill == SKILL_DRIVE:
            self.bus.vx = max(-self.vx_max, min(self.vx_max, self.bus.vx))
            self.bus.vy = max(-self.vy_max, min(self.vy_max, self.bus.vy))
            self.bus.wz = max(-self.wz_max, min(self.wz_max, self.bus.wz))
            self._last_drive = time.monotonic()
        self._emit(cid, d)
        if not d.accepted:
            self.get_logger().warn(f'skill rejected id={cid} reason={d.reason}')

    def _on_cancel(self, msg: String) -> None:
        try:
            body = json.loads(msg.data)
            cid = str(body.get('command_id', msg.data))
        except json.JSONDecodeError:
            cid = msg.data.strip()
        self._emit(cid, self.bus.cancel(cid))

    def _on_timer(self) -> None:
        if time.monotonic() - self._last_drive > self.drive_timeout:
            self.bus.zero_drive()
        msg = Twist()
        msg.linear.x = self.bus.vx
        msg.linear.y = self.bus.vy
        msg.angular.z = self.bus.wz
        zero = Twist()
        # Safety only accepts the topic matching current permit source
        if self.bus.mode == AWAKE:
            self.pub_awake.publish(msg)
            self.pub_remote.publish(zero)
        elif self.bus.mode == REMOTE:
            self.pub_remote.publish(msg)
            self.pub_awake.publish(zero)
        else:
            self.pub_remote.publish(zero)
            self.pub_awake.publish(zero)


def main() -> None:
    rclpy.init()
    node = BusNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
