# Copyright 2026 Enactic, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Launch the teleop_xr -> OpenArm bridge node.

Run the robot bringup (openarm.bimanual.launch.py) and teleop_xr separately;
this only starts the bridge. The bridge starts DISABLED — call the enable
service (or pass ``enable_on_start:=true``) before teleop_xr's IK is engaged.

Usage:
  ros2 launch openarm_teleop_bridge bridge.launch.py
  ros2 launch openarm_teleop_bridge bridge.launch.py enable_on_start:=true
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    enable_on_start = LaunchConfiguration("enable_on_start")
    input_topic = LaunchConfiguration("input_topic")

    bridge = Node(
        package="openarm_teleop_bridge",
        executable="jt_bridge",
        name="jt_bridge",
        output="screen",
        parameters=[{
            "enable_on_start": enable_on_start,
            "input_topic": input_topic,
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument("enable_on_start", default_value="false"),
        DeclareLaunchArgument("input_topic", default_value="/joint_trajectory"),
        bridge,
    ])
