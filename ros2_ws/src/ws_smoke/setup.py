from setuptools import find_packages, setup

package_name = 'ws_smoke'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='andylong',
    maintainer_email='andylong@todo.todo',
    description='Phase 1 workspace smoke package. No hardware.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [],
    },
)
