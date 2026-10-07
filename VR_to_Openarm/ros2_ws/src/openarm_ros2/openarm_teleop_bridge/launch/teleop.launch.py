# Copyright 2026 Enactic, Inc.
# SPDX-License-Identifier: Apache-2.0
"""One-shot launch of the full VR-teleop stack for OpenArm v1.0.

Starts, in order:
  1. openarm_bringup  (v1.0 URDF, forward-position controllers, fake hardware)
  2. jt_bridge        (teleop_xr /joint_trajectory -> forward-position commands)
  3. teleop_xr        (WebXR/viser server + IK, started after the URDF is up)

Usage (VR webpage becomes https://10.200.0.222:4443 once teleop_xr prints
"Server started"):
    ros2 launch openarm_teleop_bridge teleop.launch.py

Overrides: arm_type, robot_controller, use_fake_hardware, enable_on_start,
teleop_python, teleop_delay, gravity_scale, return_to_zero, teaching_mode,
left_can_interface, right_can_interface.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.logging import get_logger
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

_logger = get_logger("teleop.launch")

# Leftover processes that would poison this launch: a stale robot_state_publisher
# keeps a (possibly fake-hardware) URDF latched on /robot_description, and a
# stale controller_manager/jt_bridge/teleop_xr collides on the node names. Kill
# them before any node in this launch starts. The `[x]` bracket in each pattern
# keeps the pattern from matching the pkill command itself.
_STALE_PATTERNS = {
    "robot_state_publisher": r"robot_state_publishe[r]",
    "ros2_control_node": r"ros2_control_nod[e]",
    "controller_manager spawner": r"controller_manager/spawne[r]",
    "jt_bridge": r"jt_bridg[e]",
    "teleop_xr": r"teleop_x[r]",
}


def _preflight_cleanup(context, preflight_cleanup):
    """Synchronously kill stale openarm-teleop nodes before the stack starts."""
    import subprocess
    import time

    if context.perform_substitution(preflight_cleanup).lower() != "true":
        return []

    killed = []
    for label, pattern in _STALE_PATTERNS.items():
        try:
            if subprocess.run(["pkill", "-f", pattern], check=False).returncode == 0:
                killed.append(label)
        except OSError:
            pass

    if killed:
        _logger.info("preflight: killed stale node(s): " + ", ".join(killed))
        # Let DDS drop any latched /robot_description the stale publisher held.
        time.sleep(1.5)
    else:
        _logger.info("preflight: no stale openarm-teleop nodes found")
    return []


def generate_launch_description():
    # Bringup is v1.0 + forward-position by default (teleop_xr hardcodes link7).
    bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                get_package_share_directory("openarm_bringup"),
                "launch",
                "openarm.bimanual.launch.py",
            ])
        ),
        launch_arguments={
            "arm_type": LaunchConfiguration("arm_type"),
            "robot_controller": LaunchConfiguration("robot_controller"),
            "use_fake_hardware": LaunchConfiguration("use_fake_hardware"),
            "gravity_scale": LaunchConfiguration("gravity_scale"),
            "return_to_zero": LaunchConfiguration("return_to_zero"),
            "teaching_mode": LaunchConfiguration("teaching_mode"),
            "left_can_interface": LaunchConfiguration("left_can_interface"),
            "right_can_interface": LaunchConfiguration("right_can_interface"),
        }.items(),
    )

    bridge = Node(
        package="openarm_teleop_bridge",
        executable="jt_bridge",
        name="jt_bridge",
        output="screen",
        parameters=[{
            "enable_on_start": LaunchConfiguration("enable_on_start"),
        }],
    )

    cleanup = OpaqueFunction(
        function=_preflight_cleanup,
        args=[LaunchConfiguration("preflight_cleanup")],
    )

    # teleop_xr fetches the URDF from /robot_description (5 s timeout), so give
    # the bringup a few seconds to publish it before teleop_xr starts.
    teleop = ExecuteProcess(
        cmd=[
            LaunchConfiguration("teleop_python"),
            "-m", "teleop_xr.ros2",
            "--mode", "ik",
            "--robot-class", "openarm",
        ],
        output="screen",
    )
    teleop_delayed = TimerAction(
        period=LaunchConfiguration("teleop_delay"),
        actions=[teleop],
    )

    return LaunchDescription([
        DeclareLaunchArgument("arm_type", default_value="openarm_v1.0"),
        DeclareLaunchArgument(
            "robot_controller", default_value="forward_position_controller"),
        DeclareLaunchArgument("use_fake_hardware", default_value="true"),
        DeclareLaunchArgument("gravity_scale", default_value="0.0"),
        DeclareLaunchArgument("return_to_zero", default_value="false"),
        DeclareLaunchArgument("teaching_mode", default_value="false"),
        DeclareLaunchArgument("left_can_interface", default_value="can1"),
        DeclareLaunchArgument("right_can_interface", default_value="can0"),
        DeclareLaunchArgument("enable_on_start", default_value="true"),
        DeclareLaunchArgument(
            "teleop_python",
            default_value=os.path.expanduser("~/venv-teleop-xr/bin/python"),
        ),
        DeclareLaunchArgument("teleop_delay", default_value="6.0"),
        DeclareLaunchArgument(
            "preflight_cleanup", default_value="true",
            description="Kill leftover openarm-teleop nodes before starting."),
        cleanup,
        bringup,
        bridge,
        teleop_delayed,
    ])
