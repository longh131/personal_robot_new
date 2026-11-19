import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    cfg = os.path.join(get_package_share_directory('lidar_assist'), 'config', 'follow.yaml')
    return LaunchDescription([
        Node(
            package='lidar_assist',
            executable='follow_node',
            name='lidar_follow',
            output='screen',
            parameters=[cfg],
        ),
    ])
