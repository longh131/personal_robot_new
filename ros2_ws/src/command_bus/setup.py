import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'command_bus'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='andylong',
    maintainer_email='andylong@todo.todo',
    description='Skill ID command bus',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'bus_node = command_bus.bus_node:main',
        ],
    },
)
