from setuptools import find_packages, setup

package_name = 'lidar_assist'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', ['config/follow.yaml']),
        ('share/' + package_name + '/launch', ['launch/assist.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='andylong',
    maintainer_email='andylong@todo.todo',
    description='Lidar follow assist',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'follow_node = lidar_assist.follow_node:main',
        ],
    },
)
