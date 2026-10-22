from setuptools import find_packages, setup

package_name = 'c30d_driver'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/c30d_driver.launch.py']),
        ('share/' + package_name + '/config', ['config/c30d.yaml']),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='andylong',
    maintainer_email='andylong@todo.todo',
    description='C30D serial velocity driver',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'c30d_node = c30d_driver.c30d_node:main',
        ],
    },
)
