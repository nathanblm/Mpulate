#!/usr/bin/env python3
from setuptools import setup, find_packages
import os

package_name = 'hiwonder_servo_controllers'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    data_files=[
        # This marker file indicates that the package is installed.
        (os.path.join('share', 'ament_index', 'resource_index', 'packages'), [os.path.join('resource', package_name)]),
        # Install package.xml in the share directory for your package
        (os.path.join('share', package_name), ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    author='lucas',
    author_email='lucas@todo.todo',
    maintainer='lucas',
    maintainer_email='lucas@todo.todo',
    description='The hiwonder_servo_controllers package',
    license='TODO',
    entry_points={
        'console_scripts': [
            # Define your console scripts here if needed.
        ],
    },
)
