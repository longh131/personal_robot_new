from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    cfg = os.path.join(
        get_package_share_directory('c30d_driver'),
        'config',
        'c30d.yaml',
    )
    return LaunchDescription([
        Node(
            package='c30d_driver',
            executable='c30d_node',
            name='c30d_driver',
            output='screen',
            parameters=[cfg],
        ),
    ])
