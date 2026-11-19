import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
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
    lidar_cfg = os.path.join(
        get_package_share_directory('lidar_pkg'), 'config', 'lidar_params.yaml',
    )
    follow_cfg = os.path.join(
        get_package_share_directory('lidar_assist'), 'config', 'follow.yaml',
    )
    return LaunchDescription([
        DeclareLaunchArgument('lidar', default_value='true'),
        DeclareLaunchArgument('follow', default_value='true'),
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
        Node(
            package='lidar_pkg',
            executable='lidar_node',
            name='lidar_node',
            output='screen',
            parameters=[lidar_cfg],
            condition=IfCondition(LaunchConfiguration('lidar')),
        ),
        Node(
            package='lidar_assist',
            executable='follow_node',
            name='lidar_follow',
            output='screen',
            parameters=[follow_cfg],
            condition=IfCondition(LaunchConfiguration('follow')),
        ),
    ])
