from setuptools import find_packages, setup

package_name = 'safety_manager'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/safety.launch.py']),
        ('share/' + package_name + '/config', ['config/safety.yaml']),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='andylong',
    maintainer_email='andylong@todo.todo',
    description='Safety layer: mode mutex and estop latch',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'safety_node = safety_manager.safety_node:main',
        ],
    },
)
