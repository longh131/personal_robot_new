import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    safety_cfg = os.path.join(
        get_package_share_directory('safety_manager'), 'config', 'safety.yaml',
    )
    driver_cfg = os.path.join(
        get_package_share_directory('c30d_driver'), 'config', 'c30d.yaml',
    )
    bus_cfg = os.path.join(
        get_package_share_directory('command_bus'), 'config', 'command_bus.yaml',
    )
    return LaunchDescription([
        Node(
            package='safety_manager',
            executable='safety_node',
            name='safety_manager',
            output='screen',
            parameters=[safety_cfg],
        ),
        Node(
            package='c30d_driver',
            executable='c30d_node',
            name='c30d_driver',
            output='screen',
            parameters=[driver_cfg],
        ),
        Node(
            package='command_bus',
            executable='bus_node',
            name='command_bus',
            output='screen',
            parameters=[bus_cfg],
        ),
    ])
