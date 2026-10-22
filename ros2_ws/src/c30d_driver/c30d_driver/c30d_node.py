"""C30D ROS 2 驱动：只订 /cmd_vel_safe。超时/退出停发非零并请求零帧。

Mec-S：停发/零帧后离地可停。无硬件急停。halt 不等于工业级停车。
"""

from __future__ import annotations

import time

import rclpy
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String
from tf2_ros import TransformBroadcaster

from .cmd_gate import CmdVelGate
from .odom import OdomIntegrator
from .protocol import FeedbackParser, build_velocity_frame, twist_to_counts
from .serial_link import SerialLink

CMD_QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
)


class C30DDriver(Node):
    def __init__(self) -> None:
        super().__init__('c30d_driver')
        self.declare_parameter('port', '/dev/c30d')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('cmd_timeout', 0.30)
        self.declare_parameter('rate_hz', 20.0)
        self.declare_parameter('scale', 300.0)
        self.declare_parameter('count_limit', 120)
        self.declare_parameter('halt_send_zero', True)
        self.declare_parameter('cmd_topic', '/cmd_vel_safe')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')

        self.port = str(self.get_parameter('port').value)
        self.baud = int(self.get_parameter('baud').value)
        timeout = float(self.get_parameter('cmd_timeout').value)
        rate = float(self.get_parameter('rate_hz').value)
        self.scale = float(self.get_parameter('scale').value)
        self.limit = int(self.get_parameter('count_limit').value)
        self.halt_send_zero = bool(self.get_parameter('halt_send_zero').value)
        self.cmd_topic = str(self.get_parameter('cmd_topic').value)
        if self.cmd_topic != '/cmd_vel_safe':
            raise ValueError('c30d_driver may only subscribe /cmd_vel_safe')

        self.odom_frame = str(self.get_parameter('odom_frame').value)
        self.base_frame = str(self.get_parameter('base_frame').value)
        self.gate = CmdVelGate(timeout)
        self.link = SerialLink(self.port, self.baud)
        self.parser = FeedbackParser()
        self.odom = OdomIntegrator()
        self.tf_broadcaster = TransformBroadcaster(self)
        if self.link.open():
            self.get_logger().info(f'opened {self.port} @ {self.baud}')
        else:
            self.get_logger().error(f'serial open failed: {self.link.last_error}')

        self.create_subscription(Twist, self.cmd_topic, self._on_cmd, CMD_QOS)
        self.pub_halted = self.create_publisher(Bool, '/c30d/halted', 10)
        self.pub_connected = self.create_publisher(Bool, '/c30d/connected', 10)
        self.pub_status = self.create_publisher(String, '/c30d/status', 10)
        self.pub_odom = self.create_publisher(Odometry, '/odom', 10)

        period = 1.0 / max(rate, 1.0)
        self.create_timer(period, self._on_timer)

        self.get_logger().warn(
            'C30D: no hardware e-stop. Mec-S coast-stop is not industrial. '
            'If wheels keep moving, cut motor drive power.'
        )

    def _on_cmd(self, msg: Twist) -> None:
        self.gate.on_cmd(
            time.monotonic(),
            msg.linear.x,
            msg.linear.y,
            msg.angular.z,
        )

    def _write_counts(self, vx: int, vy: int, wz: int) -> bool:
        ok = self.link.write(build_velocity_frame(vx, vy, wz))
        if not ok:
            self.get_logger().error(f'serial write/open failed: {self.link.last_error}')
            self.gate.force_halt('serial_disconnect')
        return ok

    def _on_timer(self) -> None:
        if not self.link.connected:
            self.link.open()
            if not self.link.connected:
                self.gate.force_halt('serial_disconnect')
                self._publish_status()
                return
        self._drain_rx()
        mode = self.gate.tick(time.monotonic())
        if mode == 'idle':
            self._publish_status()
            return
        if mode == 'halt_request':
            if self.halt_send_zero:
                self._write_counts(0, 0, 0)
            self._publish_status()
            return
        vx, vy, wz = twist_to_counts(
            self.gate.vx, self.gate.vy, self.gate.wz, self.scale, self.limit,
        )
        self._write_counts(vx, vy, wz)
        self._publish_status()

    def _publish_status(self) -> None:
        c = Bool()
        c.data = self.link.connected
        self.pub_connected.publish(c)
        h = Bool()
        h.data = self.gate.halted
        self.pub_halted.publish(h)
        s = String()
        if not self.link.connected:
            s.data = f'DISCONNECTED error={self.link.last_error}; cut_power_if_wheels_move'
        elif self.gate.halted:
            s.data = (
                f'HALT_REQUEST reason={self.gate.halt_reason}; '
                'mec_s_coast_stop; not_industrial_estop; cut_power_if_wheels_move'
            )
        else:
            s.data = 'STREAM_CMD_VEL_SAFE'
        self.pub_status.publish(s)

    def _drain_rx(self) -> None:
        frames = self.parser.push(self.link.read())
        now = time.monotonic()
        for fb in frames:
            self.odom.update(fb['vx'], fb['vy'], fb['wz'], now)
        if frames:
            self._publish_odom()

    def _publish_odom(self) -> None:
        stamp = self.get_clock().now().to_msg()
        qx, qy, qz, qw = self.odom.yaw_quat()
        msg = Odometry()
        msg.header.stamp = stamp
        msg.header.frame_id = self.odom_frame
        msg.child_frame_id = self.base_frame
        msg.pose.pose.position.x = self.odom.x
        msg.pose.pose.position.y = self.odom.y
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        msg.twist.twist.linear.x = self.odom.vx
        msg.twist.twist.linear.y = self.odom.vy
        msg.twist.twist.angular.z = self.odom.wz
        self.pub_odom.publish(msg)
        tf = TransformStamped()
        tf.header.stamp = stamp
        tf.header.frame_id = self.odom_frame
        tf.child_frame_id = self.base_frame
        tf.transform.translation.x = self.odom.x
        tf.transform.translation.y = self.odom.y
        tf.transform.rotation.x = qx
        tf.transform.rotation.y = qy
        tf.transform.rotation.z = qz
        tf.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(tf)

    def shutdown(self) -> None:
        self.gate.force_halt('driver_shutdown')
        if self.halt_send_zero:
            try:
                self._write_counts(0, 0, 0)
            except Exception:
                pass
        self.link.close()
        self.get_logger().warn(
            'driver shutdown: sent halt/zero then closed serial. '
            'If motors still run, cut motor drive power.'
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = C30DDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
