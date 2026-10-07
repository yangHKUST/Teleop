# Copyright 2026 Enactic, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Real-hardware variant of teleop.launch.py.

Same full VR-teleop stack, but defaults to the physical robot:
``use_fake_hardware:=false`` (real CAN motors) and ``gravity_scale:=1.0``
(gravity compensation ON, so the arms hold their own weight).

Usage:
    ros2 launch openarm_teleop_bridge teleop_real.launch.py

Any of teleop.launch.py's overrides still work (arm_type, robot_controller,
enable_on_start, teleop_python, teleop_delay, ...), plus these two are now
declared with real-hardware defaults so you can override them too.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("use_fake_hardware", default_value="false"),
        DeclareLaunchArgument("gravity_scale", default_value="1.0"),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([
                    get_package_share_directory("openarm_teleop_bridge"),
                    "launch",
                    "teleop.launch.py",
                ])
            ),
            launch_arguments={
                "use_fake_hardware": LaunchConfiguration("use_fake_hardware"),
                "gravity_scale": LaunchConfiguration("gravity_scale"),
            }.items(),
        ),
    ])
